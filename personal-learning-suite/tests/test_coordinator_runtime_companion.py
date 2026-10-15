"""Detached startup boundaries; synthetic ledgers and no model dispatch."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
from coordinator.complete import TaskArtifactCoordinator
from coordinator import runtime_companion as companion
from coordinator.runtime_store import RuntimeStore
from coordinator.workspace import GateError, encode


class FakeProcess:
    pid = 123456

    def __init__(self, exit_code=None):
        self.exit_code = exit_code

    def poll(self):
        return self.exit_code


class CompanionTests(unittest.TestCase):
    def setUp(self):
        # The desktop sandbox's redirected TEMP denies rename; use the writable
        # workspace so atomic production writes are exercised without a mock.
        temporary = tempfile.TemporaryDirectory(prefix="companion-", dir=SUITE / "tests")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.c = TaskArtifactCoordinator(self.root)
        self.c.initialize(evidence_kind="synthetic_demo")
        self.store = RuntimeStore(self.c)
        self.store.migrate(self.c.bind_local_operator("AG0"))
        self.directory = self.c.meta_root / "runtime-companion"
        self.calls = []
        self.alive = patch.object(companion, "_pid_alive", return_value=True)
        self.alive.start()
        self.addCleanup(self.alive.stop)

    def lease(self, *, pid=123456, instance="fabricated-listener", until=None):
        value = {"pid": pid, "instance_id": instance, "started_at_ms": self.c.clock_ms(),
                 "lease_until_ms": self.c.clock_ms() + 60000 if until is None else until}
        with self.c.connect() as db:
            self.store.put(db, "runtime_supervisor", "local", value)
        return value

    def previous(self, *, shadow=False, ready_pid=123456, ready_instance="fabricated-listener", status="spawned"):
        self.directory.mkdir(exist_ok=True)
        marker = {"launch_id": "a" * 32, "status": status, "pid": 123456}
        paths = companion._paths(self.directory, marker["launch_id"])
        companion._write_json(Path(paths["startup_file"]), marker)
        companion._write_json(Path(paths["ready_file"]), {"status": "ready", "shadow": shadow,
                              "pid": ready_pid, "instance_id": ready_instance})
        return marker, paths

    def launcher(self, command, **options):
        self.calls.append((command, options))
        ready = Path(command[command.index("--ready-file") + 1])
        self.lease()
        companion._write_json(ready, {"status": "ready", "shadow": False,
                                      "pid": 123456, "instance_id": "fabricated-listener"})
        return FakeProcess()

    def expect_gate(self, code, **kwargs):
        with self.assertRaises(GateError) as caught:
            companion.ensure_companion(self.c, **kwargs)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.receipt["problem"], code)
        return caught.exception.receipt

    def test_spawn_is_file_backed_live_and_inherits_environment_without_logging_it(self):
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "actual-inherited-caller", "SECRET_TEST_VALUE": "do-not-log-this"}):
            receipt = companion.ensure_companion(self.c, launcher=self.launcher, max_seconds=30, stop_when_done=True)
        command, options = self.calls[0]
        self.assertEqual(command[:4], [sys.executable, "-B", "-X", "utf8"])
        self.assertEqual(command[4], str(SUITE / "scripts/coordinate_runtime.py"))
        self.assertEqual(command[5:10], ["--workspace", str(self.root), "run", "--max-seconds", "30"])
        self.assertIn("--stop-when-done", command)
        self.assertEqual(options["env"]["CODEX_THREAD_ID"], "actual-inherited-caller")
        self.assertEqual(options["env"]["SECRET_TEST_VALUE"], "do-not-log-this")
        self.assertIs(options["stdin"], subprocess.DEVNULL)
        self.assertTrue(options["close_fds"])
        self.assertEqual((receipt["status"], receipt["mode"], receipt["reused"]), ("ready", "live", False))
        for field in ("ready_file", "stdout_file", "stderr_file", "startup_file"):
            self.assertTrue(Path(receipt[field]).is_file())
        for path in self.directory.iterdir():
            self.assertNotIn("do-not-log-this", path.read_text(encoding="utf-8"))
        self.assertEqual(self.store.status()["state_revision"], 0)

    def test_reuse_requires_matching_live_ready_receipt_and_current_lease(self):
        self.previous()
        self.lease()
        receipt = companion.ensure_companion(self.c, launcher=self.launcher)
        self.assertTrue(receipt["reused"])
        self.assertEqual(receipt["pid"], 123456)
        self.assertEqual(self.calls, [])

    def test_shadow_is_explicitly_rejected_without_starting_another_runtime(self):
        self.previous(shadow=True)
        self.lease()
        receipt = self.expect_gate("runtime_shadow_supervisor_active", launcher=self.launcher)
        self.assertFalse(receipt["startup_unknown"])
        self.assertEqual(self.calls, [])

    def test_active_lease_without_known_receipt_is_not_reported_as_ready(self):
        self.lease()
        receipt = self.expect_gate("runtime_supervisor_unverified", launcher=self.launcher)
        self.assertTrue(receipt["startup_unknown"])
        self.assertEqual(self.calls, [])

    def test_expired_external_lease_with_a_live_pid_does_not_start_a_competitor(self):
        self.lease(until=0)
        receipt = self.expect_gate("runtime_supervisor_unverified", launcher=self.launcher)
        self.assertTrue(receipt["startup_unknown"])
        self.assertEqual(self.calls, [])

    def test_receipt_with_stale_instance_cannot_prove_readiness_or_trigger_resend(self):
        self.previous(ready_instance="old-instance")
        self.lease()
        receipt = self.expect_gate("runtime_companion_readiness_timeout", launcher=self.launcher, ready_timeout=.01)
        self.assertTrue(receipt["startup_unknown"])
        self.assertEqual(self.calls, [])

    def test_old_receipt_without_explicit_live_mode_cannot_prove_readiness(self):
        _, paths = self.previous()
        self.lease()
        readiness = companion._read_json(Path(paths["ready_file"]))
        readiness.pop("shadow")
        companion._write_json(Path(paths["ready_file"]), readiness)
        self.expect_gate("runtime_companion_readiness_timeout", launcher=self.launcher, ready_timeout=.01)
        self.assertEqual(self.calls, [])

    def test_expired_lease_and_live_pid_cannot_be_reused_or_replaced(self):
        self.previous()
        self.lease(until=0)
        self.expect_gate("runtime_companion_readiness_timeout", launcher=self.launcher, ready_timeout=.01)
        self.assertEqual(self.calls, [])

    def test_expired_lease_and_dead_process_can_start_a_new_runtime(self):
        self.previous()
        self.lease(until=0)
        with patch.object(companion, "_pid_alive", side_effect=[False, True]):
            receipt = companion.ensure_companion(self.c, launcher=self.launcher)
        self.assertFalse(receipt["reused"])
        self.assertEqual(len(self.calls), 1)

    def test_dead_pid_with_unexpired_lease_is_not_reused_or_replaced(self):
        self.previous()
        self.lease()
        with patch.object(companion, "_pid_alive", return_value=False):
            self.expect_gate("runtime_supervisor_unverified", launcher=self.launcher)
        self.assertEqual(self.calls, [])

    def test_unknown_prior_launch_is_not_retried(self):
        self.directory.mkdir()
        companion._write_json(self.directory / "startup.json", {"launch_id": "b" * 32, "status": "launching"})
        receipt = self.expect_gate("runtime_companion_startup_unknown", launcher=self.launcher)
        self.assertTrue(receipt["startup_unknown"])
        self.assertEqual(self.calls, [])

    def test_ambiguous_launcher_exception_cannot_trigger_another_attempt(self):
        calls = []

        def fail(*args, **kwargs):
            calls.append(1)
            raise RuntimeError("sensitive launcher diagnostics")

        first = self.expect_gate("runtime_companion_startup_unknown", launcher=fail)
        second = self.expect_gate("runtime_companion_startup_unknown", launcher=fail)
        self.assertTrue(first["startup_unknown"])
        self.assertNotIn("sensitive", encode(first))
        self.assertEqual(first["startup_file"], second["startup_file"])
        self.assertEqual(len(calls), 1)

    def test_timeout_keeps_child_and_diagnostics_for_inspection_without_retry(self):
        calls = []

        def launch(command, **options):
            calls.append(command)
            return FakeProcess()

        first = self.expect_gate("runtime_companion_readiness_timeout", launcher=launch, ready_timeout=.01)
        second = self.expect_gate("runtime_companion_readiness_timeout", launcher=launch, ready_timeout=.01)
        self.assertTrue(first["startup_unknown"])
        self.assertEqual(first["ready_file"], second["ready_file"])
        self.assertEqual(len(calls), 1)

    def test_known_launch_failure_can_be_inspected_and_followed_by_a_new_start(self):
        def fail(*args, **kwargs):
            raise OSError("secret diagnostics")

        receipt = self.expect_gate("runtime_companion_launch_failed", launcher=fail)
        self.assertFalse(receipt["startup_unknown"])
        self.assertNotIn("secret diagnostics", encode(receipt))
        self.assertEqual(companion.ensure_companion(self.c, launcher=self.launcher)["status"], "ready")

    def test_child_exiting_before_ready_is_a_known_failure(self):
        receipt = self.expect_gate("runtime_companion_exited_before_ready", launcher=lambda *a, **k: FakeProcess(1))
        self.assertFalse(receipt["startup_unknown"])

    def test_simultaneous_starters_launch_only_one_child(self):
        entered = threading.Event()

        def launch(command, **options):
            entered.set()
            time.sleep(.03)
            return self.launcher(command, **options)

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(companion.ensure_companion, self.c, launcher=launch)
            self.assertTrue(entered.wait(1))
            second = pool.submit(companion.ensure_companion, self.c, launcher=launch)
            receipts = [first.result(timeout=3), second.result(timeout=3)]
        self.assertEqual(len(self.calls), 1)
        self.assertEqual({receipt["instance_id"] for receipt in receipts}, {"fabricated-listener"})
        self.assertEqual(sorted(receipt["reused"] for receipt in receipts), [False, True])

    def test_windows_child_is_detached_hidden_and_has_its_own_process_group(self):
        flags = companion._background_options(windows=True)["creationflags"]
        self.assertTrue(flags & 0x08000000)  # CREATE_NO_WINDOW
        self.assertTrue(flags & 0x00000200)  # CREATE_NEW_PROCESS_GROUP
        self.assertTrue(flags & 0x00000008)  # DETACHED_PROCESS

    def test_uninitialized_workspace_and_missing_upgrade_do_not_create_startup_files(self):
        missing = TaskArtifactCoordinator(self.root / "missing")
        with self.assertRaisesRegex(GateError, "workspace_not_initialized"):
            companion.ensure_companion(missing, launcher=self.launcher)
        self.assertFalse(missing.root.exists())
        with self.c.connect() as db:
            db.execute("DROP TABLE runtime_supervisor")
        with self.assertRaisesRegex(GateError, "runtime_upgrade_required"):
            companion.ensure_companion(self.c, launcher=self.launcher)
        self.assertFalse(self.directory.exists())

    def test_real_child_remains_live_after_its_starter_exits(self):
        self.alive.stop()
        parent = self.root / "starter.py"
        parent.write_text("\n".join([
            "import json, sys", "from pathlib import Path",
            "sys.path.insert(0, " + repr(str(SUITE / "src")) + ")",
            "from coordinator.complete import TaskArtifactCoordinator",
            "from coordinator.runtime_companion import ensure_companion",
            "print(json.dumps(ensure_companion(TaskArtifactCoordinator(sys.argv[1]), max_seconds=.5)))",
        ]), encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(parent), str(self.root)],
                                capture_output=True, encoding="utf-8", timeout=20)
        self.assertEqual((result.returncode, result.stderr), (0, ""), result.stdout)
        receipt = json.loads(result.stdout)
        self.assertTrue(companion._pid_alive(receipt["pid"]))
        self.assertGreater(self.store.status()["supervisor"][0]["lease_until_ms"], self.c.clock_ms())
        deadline = time.monotonic() + 5
        while companion._pid_alive(receipt["pid"]) is True and time.monotonic() < deadline:
            time.sleep(.05)
        self.assertIs(companion._pid_alive(receipt["pid"]), False)
        self.assertEqual(self.store.status()["supervisor"][0]["lease_until_ms"], 0)


if __name__ == "__main__":
    unittest.main()
