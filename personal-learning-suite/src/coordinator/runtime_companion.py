"""Start one detached runtime, and prove readiness against its durable lease.

The startup file is a recovery record, not authority to run work. SQLite's
supervisor lease remains authoritative. An ambiguous start is never retried or
terminated here; a later caller must first establish what happened.
"""
from __future__ import annotations

from contextlib import contextmanager
import errno
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from .workspace import GateError, encode


DEFAULT_MAX_SECONDS = 4 * 60 * 60


def _write_json(path, value):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="") as stream:
            stream.write(encode(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, UnicodeError, ValueError):
        return None


def _paths(directory, launch_id=None):
    paths = {"startup_file": str(directory / "startup.json"),
             "lock_file": str(directory / "startup.lock")}
    if launch_id:
        paths.update(ready_file=str(directory / (launch_id + ".ready.json")),
                     stdout_file=str(directory / (launch_id + ".stdout.log")),
                     stderr_file=str(directory / (launch_id + ".stderr.log")))
    return paths


def _failure(code, paths, *, startup_unknown, **facts):
    receipt = {"status": "rejected", "problem": code, "startup_unknown": startup_unknown,
               **paths, **facts, "next_action": "inspect_runtime_status_before_retry"}
    error = GateError(code, encode(receipt))
    error.receipt = receipt
    return error


def _supervisor(coordinator):
    # This read must not migrate, recover, renew, or otherwise mutate the ledger.
    with coordinator.connect() as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_supervisor'").fetchone():
            raise GateError("runtime_upgrade_required")
        row = db.execute("SELECT body FROM runtime_supervisor WHERE id='local'").fetchone()
    return json.loads(row[0]) if row else {}


def _pid_alive(pid):
    """True/False when observable; None means do not assume the process died."""
    if type(pid) is not int or pid <= 0:
        return None
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only.
        if not handle:
            return False if ctypes.get_last_error() == 87 else None
        try:
            result = kernel.WaitForSingleObject(handle, 0)
            return True if result == 258 else False if result == 0 else None
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return None
    # A zombie cannot renew a lease, even though kill(pid, 0) still succeeds.
    try:
        state = Path("/proc") / str(pid) / "stat"
        if state.is_file() and state.read_text().rsplit(")", 1)[1].split()[0] == "Z":
            return False
    except (OSError, IndexError, UnicodeError):
        pass
    return True


def _background_options(*, windows=None):
    windows = os.name == "nt" if windows is None else windows
    if windows:
        # No console or inherited input/pipe can tie this process to its caller.
        # Values are stable Win32 constants; keep tests portable to other OSes.
        return {"creationflags": 0x08000000 | 0x00000200 | 0x00000008}
    return {"start_new_session": True}


@contextmanager
def _startup_lock(path, deadline, paths):
    with path.open("a+b") as stream:
        if stream.seek(0, os.SEEK_END) == 0:
            stream.write(b"0")
            stream.flush()
        while True:
            stream.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if time.monotonic() >= deadline:
                    raise _failure("runtime_companion_startup_busy", paths, startup_unknown=True) from None
                time.sleep(min(.05, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _active(supervisor, coordinator):
    return supervisor.get("lease_until_ms", 0) > coordinator.clock_ms()


def _verified(coordinator, supervisor, readiness, paths, *, expected_pid=None, reused):
    if not readiness or not _active(supervisor, coordinator):
        return None
    pid = readiness.get("pid")
    if (type(pid) is not int or pid <= 0 or readiness.get("status") != "ready"
            or not readiness.get("instance_id")
            or readiness.get("instance_id") != supervisor.get("instance_id")
            or pid != supervisor.get("pid") or (expected_pid is not None and pid != expected_pid)):
        return None
    if readiness.get("shadow") is True or readiness.get("mode") == "shadow":
        raise _failure("runtime_shadow_supervisor_active", paths, startup_unknown=False,
                       pid=pid, instance_id=readiness["instance_id"])
    # Receipts predating the explicit mode field cannot prove a live listener.
    if readiness.get("shadow") is not False or readiness.get("mode", "live") != "live":
        return None
    if _pid_alive(pid) is not True:
        return None
    return {"status": "ready", "mode": "live", "shadow": False, "pid": pid,
            "instance_id": readiness["instance_id"], "lease_until_ms": supervisor["lease_until_ms"],
            "verified_at_ms": coordinator.clock_ms(), "reused": reused, **paths,
            "meaning": "listener_ready_plan_must_also_be_saved"}


def ensure_companion(coordinator, *, max_seconds=DEFAULT_MAX_SECONDS, stop_when_done=False,
                     ready_timeout=15, launcher=None):
    """Return a file-backed live readiness receipt, or a structured ``GateError``.

    ``launcher`` has the ``subprocess.Popen`` signature and is an execution seam
    for tests. Failures expose safe diagnostics in ``error.receipt``. No child
    is terminated and no ambiguous launch is automatically retried.
    """
    for value in (max_seconds, ready_timeout):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise GateError("invalid_runtime_companion_seconds")
    if type(stop_when_done) is not bool:
        raise GateError("invalid_runtime_companion_stop_when_done")
    _supervisor(coordinator)  # Missing workspaces/upgrades have no side effects.
    directory = coordinator.meta_root / "runtime-companion"
    directory.mkdir(exist_ok=True)
    paths = _paths(directory)
    deadline = time.monotonic() + ready_timeout
    process = None
    spawned = False
    with _startup_lock(Path(paths["lock_file"]), deadline, paths):
        marker_path = Path(paths["startup_file"])
        marker = _read_json(marker_path)
        if marker_path.exists() and (not marker or not re.fullmatch(r"[a-f0-9]{32}", str(marker.get("launch_id", "")))):
            raise _failure("runtime_companion_startup_unknown", paths, startup_unknown=True)
        if marker:
            paths = _paths(directory, marker["launch_id"])
        supervisor = _supervisor(coordinator)
        readiness = _read_json(Path(paths["ready_file"])) if marker else None
        ready = _verified(coordinator, supervisor, readiness, paths,
                          expected_pid=marker.get("pid") if marker else None, reused=True)
        if ready:
            return ready
        if _active(supervisor, coordinator) and (not marker or supervisor.get("pid") != marker.get("pid")):
            raise _failure("runtime_supervisor_unverified", paths, startup_unknown=True,
                           pid=supervisor.get("pid"), instance_id=supervisor.get("instance_id"))
        if (supervisor.get("pid") and not _active(supervisor, coordinator)
                and (not marker or supervisor.get("pid") != marker.get("pid"))
                and _pid_alive(supervisor["pid"]) is not False):
            raise _failure("runtime_supervisor_unverified", paths, startup_unknown=True,
                           pid=supervisor["pid"], instance_id=supervisor.get("instance_id"))
        pid_state = _pid_alive(marker.get("pid")) if marker else False
        if marker and marker.get("status") != "launch_failed" and pid_state is not False:
            if marker.get("pid") is None:
                raise _failure("runtime_companion_startup_unknown", paths, startup_unknown=True)
            # A live process without a lease may still be starting; wait outside
            # the short lock. Never start a competitor on an expired lease.
        elif _active(supervisor, coordinator):
            raise _failure("runtime_supervisor_unverified", paths, startup_unknown=True,
                           pid=supervisor.get("pid"), instance_id=supervisor.get("instance_id"))
        else:
            launch_id = uuid.uuid4().hex
            paths = _paths(directory, launch_id)
            marker = {"launch_id": launch_id, "status": "launching", "created_at_ms": coordinator.clock_ms(),
                      "max_seconds": max_seconds, "stop_when_done": stop_when_done}
            try:
                _write_json(marker_path, marker)
            except OSError:
                raise _failure("runtime_companion_startup_record_failed", paths, startup_unknown=False) from None
            suite = Path(__file__).resolve().parents[2]
            command = [sys.executable, "-B", "-X", "utf8", str(suite / "scripts/coordinate_runtime.py"),
                       "--workspace", str(coordinator.root), "run", "--max-seconds", str(max_seconds),
                       "--ready-file", paths["ready_file"]]
            if stop_when_done:
                command.append("--stop-when-done")
            launcher = subprocess.Popen if launcher is None else launcher
            try:
                with Path(paths["stdout_file"]).open("xb") as stdout, Path(paths["stderr_file"]).open("xb") as stderr:
                    process = launcher(command, cwd=str(suite), stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, env=dict(os.environ), close_fds=True,
                                       **_background_options())
            except OSError:
                marker["status"] = "launch_failed"
                _write_json(marker_path, marker)
                raise _failure("runtime_companion_launch_failed", paths, startup_unknown=False) from None
            except Exception:
                raise _failure("runtime_companion_startup_unknown", paths, startup_unknown=True) from None
            if type(getattr(process, "pid", None)) is not int or process.pid <= 0:
                raise _failure("runtime_companion_startup_unknown", paths, startup_unknown=True)
            marker.update(status="spawned", pid=process.pid)
            try:
                _write_json(marker_path, marker)
            except OSError:
                raise _failure("runtime_companion_startup_unknown", paths, startup_unknown=True, pid=process.pid) from None
            spawned = True

    while True:
        supervisor = _supervisor(coordinator)
        readiness = _read_json(Path(paths["ready_file"]))
        ready = _verified(coordinator, supervisor, readiness, paths, expected_pid=marker.get("pid"), reused=not spawned)
        if ready:
            return ready
        if _active(supervisor, coordinator) and supervisor.get("pid") != marker.get("pid"):
            raise _failure("runtime_supervisor_unverified", paths, startup_unknown=True,
                           pid=supervisor.get("pid"), instance_id=supervisor.get("instance_id"))
        exited = process.poll() is not None if process is not None else _pid_alive(marker.get("pid")) is False
        if exited:
            raise _failure("runtime_companion_exited_before_ready", paths, startup_unknown=False, pid=marker.get("pid"))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _failure("runtime_companion_readiness_timeout", paths, startup_unknown=True, pid=marker.get("pid"))
        time.sleep(min(.05, remaining))
