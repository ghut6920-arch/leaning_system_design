"""The normal preparation boundary: one project ledger, automatic chat routing.

The human requests preparation. AG0 records a bounded professional plan, and
this entry installs once, saves that plan and obtains a real companion receipt.
It never takes over unrelated historical tasks or falls back to model polling.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path

from .agent_api import AgentCoordinator
from .hosts import CLIResumeHost, DesktopMCPHost
from .preparation_graph import compile_preparation
from .runtime_companion import ensure_companion
from .runtime_store import RUNTIME_VERSION, RuntimeStore, installed
from .workspace import GateError, encode, sha


def _save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


@contextmanager
def _startup_lock(root):
    """OS lock releases on process death; no stale lock file means ownership."""
    path = root / "preparation-start.lock"
    with path.open("a+b") as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise GateError("preparation_start_in_progress") from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def preflight_hosts(coordinator, thread_id):
    cli = CLIResumeHost(coordinator.meta_root / "host-runs")
    desktop = DesktopMCPHost(coordinator.meta_root / "host-runs")
    try:
        if not cli.cli_path:
            raise GateError("preparation_cli_unavailable")
        observed = desktop.inspect({"thread_id": thread_id, "host_id": "local"})
        if observed["state"] not in {"idle", "active", "needs_user"}:
            raise GateError("preparation_desktop_unavailable")
        return {"status": "ok", "cli_available": True, "desktop_state": observed["state"],
                "thread_id": observed["thread_id"]}
    finally:
        cli.close()
        desktop.close()


def _authorization(coordinator, request):
    value = request.get("authorization_ref")
    if not isinstance(value, str) or not value:
        raise GateError("preparation_authorization_source_required")
    source = (coordinator.root / value).resolve()
    if (not source.is_relative_to(coordinator.root) or source.is_relative_to(coordinator.meta_root)
            or not source.is_file() or not source.read_bytes().strip()):
        raise GateError("preparation_authorization_source_required")
    return {"path": source.relative_to(coordinator.root).as_posix(), "sha256": sha(source.read_bytes())}


def _explicitly_disabled(db, workflow):
    return any(json.loads(row[0]).get("workflow_id") == workflow
               and json.loads(row[0]).get("enabled") is False
               for row in db.execute("SELECT body FROM runtime_audit WHERE kind='plan_enabled'"))


def _activate(store, session, workflow, readiness, receipt):
    # Activating and recording takeover are one database commit. No host call or
    # fallible file write follows an enabled plan before its durable receipt.
    with store.transaction() as db:
        store.c.controls(db)
        supervisor = store.get(db, "runtime_supervisor", "local")
        if (supervisor.get("instance_id") != readiness.get("instance_id")
                or supervisor.get("pid") != readiness.get("pid")
                or supervisor.get("lease_until_ms", 0) <= store.c.clock_ms()):
            raise GateError("preparation_listener_not_ready")
        plan = store.get(db, "runtime_plans", workflow)
        previous = [json.loads(row[0]) for row in db.execute("SELECT body FROM runtime_audit WHERE kind='preparation_takeover'")
                    if json.loads(row[0]).get("workflow_id") == workflow]
        if not plan["enabled"] and _explicitly_disabled(db, workflow):
            raise GateError("preparation_plan_disabled")
        if plan["enabled"] and not previous:
            raise GateError("preparation_activation_unknown")
        plan["enabled"] = True
        store.put(db, "runtime_plans", workflow, plan)
        store.audit(db, "preparation_takeover", receipt)
        sequence = db.execute("SELECT MAX(sequence) FROM runtime_audit").fetchone()[0]
    return {**receipt, "takeover_audit_sequence": sequence}


def start_preparation(coordinator, request, *, thread_id=None, companion=None, host_preflight=None):
    """Idempotent startup. Dependencies are injectable for tests, never CLI flags."""
    actual_thread = os.environ.get("CODEX_THREAD_ID", "").strip()
    thread_id = thread_id or actual_thread
    if not actual_thread or thread_id != actual_thread:
        raise GateError("actual_preparation_thread_required")
    if not isinstance(request, dict):
        raise GateError("invalid_preparation_request")
    # Compilation and authorization validation precede any database mutation.
    compiled = compile_preparation(request, thread_id=thread_id, workspace=coordinator.root)
    authorization = _authorization(coordinator, request)
    with coordinator.connect() as db:
        coordinator.controls(db)
    run_root = coordinator.meta_root / "preparations" / sha(compiled["workflow_id"].encode())[:24]
    run_root.mkdir(parents=True, exist_ok=True)
    expected = {"request": request, "thread_id": thread_id, "authorization": authorization}
    with _startup_lock(coordinator.meta_root):
        request_path = run_root / "request.json"
        if request_path.exists():
            if json.loads(request_path.read_text(encoding="utf-8")) != expected:
                raise GateError("preparation_request_changed_use_new_workflow")
        else:
            _save(request_path, expected)
        compiled_path = run_root / "compiled.json"
        if compiled_path.exists():
            compiled = json.loads(compiled_path.read_text(encoding="utf-8"))
        else:
            # Fix absolute deadlines once, so retries cannot extend them.
            deadline = request.get("deadline_ms", coordinator.clock_ms() + 4 * 60 * 60 * 1000)
            for node in compiled["plan"]["nodes"]:
                node.setdefault("deadline_ms", deadline)
            _save(compiled_path, compiled)
        preflight = (host_preflight or preflight_hosts)(coordinator, thread_id)
        if preflight.get("status") != "ok":
            raise GateError("preparation_host_preflight_failed")
        store = RuntimeStore(coordinator)
        session = coordinator.bind_local_operator("AG0")
        with coordinator.connect() as db:
            present = installed(db)
            marker = db.execute("SELECT value FROM meta WHERE key='runtime_version'").fetchone()
        migration = None
        if not present:
            migration = store.migrate(session)
        elif not marker or marker[0] != RUNTIME_VERSION:
            raise GateError("unsupported_runtime_version")
        api = AgentCoordinator(coordinator)
        with coordinator.connect() as db:
            plan_row = db.execute("SELECT body FROM runtime_plans WHERE id=?", (compiled["workflow_id"],)).fetchone()
        if plan_row is None:
            for binding in compiled["bindings"]:
                with coordinator.connect() as db:
                    row = db.execute("SELECT body FROM runtime_bindings WHERE id=?", (binding["id"],)).fetchone()
                if row:
                    existing = json.loads(row[0])
                    if any(existing.get(key) != binding.get(key) for key in ("role", "host_kind", "host_id", "cwd", "authorization_ref")):
                        raise GateError("preparation_binding_changed")
                    if binding["role"] == "AG0" and existing.get("thread_id") != thread_id:
                        raise GateError("preparation_binding_changed")
                else:
                    store.bind(session, binding)
            for assignment in compiled["assignments"]:
                key = compiled["workflow_id"] + ":setup:" + assignment["task"]
                prior = api.saved_intent(session, assignment, request_key=key)
                receipt = prior if prior["status"] == "committed" else api.do(session, assignment, request_key=key)
                if receipt["status"] != "committed":
                    raise GateError(receipt.get("problem", "preparation_assignment_failed"))
            plan = {**compiled["plan"], "enabled": False}
            store.register_plan(session, plan)
        else:
            persisted = json.loads(plan_row[0])
            frozen = {key: value for key, value in persisted.items() if key not in {"enabled", "registered_at_ms"}}
            desired = {key: value for key, value in compiled["plan"].items() if key != "enabled"}
            if frozen != desired:
                raise GateError("preparation_plan_changed")
            with coordinator.connect() as db:
                if not persisted["enabled"] and _explicitly_disabled(db, compiled["workflow_id"]):
                    raise GateError("preparation_plan_disabled")
        readiness = (companion or ensure_companion)(coordinator, max_seconds=14400, stop_when_done=False)
        if readiness.get("status") != "ready" or readiness.get("mode") != "live":
            raise GateError("preparation_listener_not_ready")
        receipt = {"status": "committed", "runtime_takeover": True, "workflow_id": compiled["workflow_id"],
                   "thread_id": thread_id, "request_sha256": sha(encode(expected).encode()),
                   "request_path": str(request_path), "plan_path": str(compiled_path),
                   "listener": readiness, "host_preflight": preflight,
                   "initialized_now": migration is not None, "migration_backup": migration.get("backup") if migration else None,
                   "meaning": "python_owns_waiting_agents_must_end_turn", "next_action": "结束当前轮；由Python等待并按计划唤醒原聊天。"}
        _save(run_root / "handoff.json", {**receipt, "status": "staged", "runtime_takeover": False,
                                         "meaning": "pending_atomic_activation_in_runtime_audit"})
        return _activate(store, session, compiled["workflow_id"], readiness, receipt)
