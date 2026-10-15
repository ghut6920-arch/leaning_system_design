"""CLI boundaries against synthetic databases; no external host or model."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
sys.path.insert(0, str(SUITE / "scripts"))
from coordinator.complete import TaskArtifactCoordinator
from coordinator.runtime_scheduler import RuntimeScheduler
from coordinator.runtime_store import RuntimeStore
from coordinator.workspace import GateError
from coordinate_runtime import run_once

ENTRY = SUITE / "scripts/coordinate_runtime.py"


class CoordinatorRuntimeEntryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tre-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.c = TaskArtifactCoordinator(self.root)
        self.c.initialize(evidence_kind="synthetic_demo")
        self.ag0 = self.c.bind_local_operator("AG0")
        self.store = RuntimeStore(self.c)

    def invoke(self, *parts, thread=None, root=None):
        env = dict(os.environ)
        env.pop("CODEX_THREAD_ID", None)
        if thread is not None:
            env["CODEX_THREAD_ID"] = thread
        response = subprocess.run([sys.executable, str(ENTRY), "--workspace", str(root or self.root), *parts],
                                  env=env, encoding="utf-8", capture_output=True, timeout=20)
        self.assertEqual(response.stderr, "", response.stderr)
        value = json.loads(response.stdout)
        self.assertLessEqual(len(response.stdout.encode("utf-8")), 8192)
        return response.returncode, value

    def json_file(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return str(path)

    def install(self):
        return self.store.migrate(self.ag0)

    def ready_dispatch(self):
        self.install()
        self.store.bind(self.ag0, {"id": "worker", "role": "AG0", "host_kind": "desktop",
                                  "thread_id": "fabricated-original-thread", "authorized": True,
                                  "authorization_ref": "fabricated-user-authorization"})
        self.store.register_plan(self.ag0, {"id": "fabricated-workflow", "revision": 1,
                                           "authorization_ref": "fabricated-user-authorization", "nodes": [{
                                               "id": "decision", "binding": "worker", "prompt": "Fabricated finite decision.",
                                               "allowed_tasks": ["fabricated-task"], "allowed_actions": ["start"],
                                               "conditions": [], "completion": "result"}]})
        self.store.reconcile(self.ag0)
        self.store.acquire_supervisor("fabricated-instance")
        work = self.store.status()["works"][0]
        attempt = self.store.claim(work["id"], "fabricated-instance")
        self.store.update_attempt(attempt["dispatch_id"], "dispatching", instance_id="fabricated-instance")
        return attempt

    def test_missing_workspace_is_not_initialized_by_any_runtime_entry(self):
        missing = self.root / "untouched"
        for command in ("status", "migrate", "run"):
            code, result = self.invoke(command, root=missing)
            self.assertEqual(code, 1)
            self.assertEqual(result["problem"], "workspace_not_initialized")
            self.assertFalse(missing.exists())

    def test_status_does_not_migrate_and_explicit_migration_backs_up(self):
        code, rejected = self.invoke("status")
        self.assertEqual((code, rejected["problem"]), (1, "runtime_upgrade_required"))
        self.assertFalse((self.c.meta_root / "backups").exists())
        code, migrated = self.invoke("migrate")
        self.assertEqual((code, migrated["status"]), (0, "committed"))
        self.assertTrue(Path(migrated["backup"]).is_file())
        code, state = self.invoke("status")
        self.assertEqual((code, state["counts"]["works"]), (0, 0))
        self.assertEqual(state["state_revision"], 0)

    def test_invalid_budget_is_rejected_before_migration(self):
        code, result = self.invoke("--max-return-bytes", "1", "migrate")
        self.assertEqual((code, result["problem"]), (1, "invalid_return_budget"))
        self.assertFalse((self.c.meta_root / "backups").exists())

    def test_bind_plan_shadow_and_controls_require_explicit_authorization(self):
        self.install()
        binding = {"id": "worker", "role": "AG2", "host_kind": "cli", "thread_id": None,
                   "authorized": True}
        code, result = self.invoke("bind", "--binding-file", self.json_file("binding.json", binding))
        self.assertEqual((code, result["problem"]), (1, "explicit_runtime_authorization_required"))
        binding["authorization_ref"] = "fabricated-user-authorization"
        code, result = self.invoke("bind", "--binding-file", self.json_file("binding.json", binding))
        self.assertEqual((code, result["status"]), (0, "committed"))
        plan = {"id": "fabricated-workflow", "revision": 1, "enabled": True,
                "authorization_ref": binding["authorization_ref"], "nodes": [{
                    "id": "wait", "binding": "worker", "allowed_tasks": ["missing-task"],
                    "allowed_actions": ["start"], "prompt": "No waiting model turn.",
                    "conditions": [{"kind": "submitted", "task": "missing-task"}]}]}
        code, result = self.invoke("plan", "--plan-file", self.json_file("plan.json", plan))
        self.assertEqual((code, result["status"]), (0, "committed"))
        code, result = self.invoke("shadow", "--once")
        self.assertEqual(code, 0)
        self.assertEqual(result["outcome"]["dispatches"], 0)
        self.assertEqual(result["runtime"]["works"][0]["state"], "blocked")
        self.assertEqual(result["runtime"]["works"][0]["reason"], "waiting_for_task_registration")
        self.assertFalse((self.c.meta_root / "host-runs").exists())
        self.assertNotIn("prompt", result["runtime"]["works"][0])
        self.assertEqual(self.store.status()["supervisor"][0]["lease_until_ms"], 0)
        for command, enabled in (("disable", False), ("enable", True)):
            code, result = self.invoke(command, "--workflow", "fabricated-workflow")
            self.assertEqual((code, result["enabled"]), (0, enabled))

    def test_run_once_releases_supervisor_and_writes_readiness(self):
        self.install()
        ready = self.root / "ready.json"
        code, result = self.invoke("run", "--once", "--ready-file", str(ready))
        self.assertEqual((code, result["outcome"]["dispatches"]), (0, 0))
        readiness = json.loads(ready.read_text(encoding="utf-8"))
        record = self.store.status()["supervisor"][0]
        self.assertEqual(readiness["instance_id"], record["instance_id"])
        self.assertEqual(record["lease_until_ms"], 0)

    def test_once_releases_supervisor_and_closes_host_after_tick_error(self):
        self.install()

        class Host:
            closed = False

            def close(self):
                self.closed = True

        host = Host()
        scheduler = RuntimeScheduler(self.c, {"fake": host})

        def fail_tick():
            raise GateError("fabricated_tick_error")

        scheduler.tick = fail_tick
        with self.assertRaisesRegex(GateError, "fabricated_tick_error"):
            run_once(scheduler)
        self.assertTrue(host.closed)
        self.assertEqual(self.store.status()["supervisor"][0]["lease_until_ms"], 0)

    def test_continuous_shadow_supports_launcher_options_without_host_runs(self):
        self.install()
        ready = self.root / "shadow-ready.json"
        code, result = self.invoke("shadow", "--max-seconds", ".01", "--ready-file", str(ready), "--stop-when-done")
        self.assertEqual((code, result["status"]), (0, "ok"))
        self.assertTrue(ready.is_file())
        self.assertFalse((self.c.meta_root / "host-runs").exists())
        self.assertEqual(self.store.status()["supervisor"][0]["lease_until_ms"], 0)

    def test_begin_dispatch_uses_actual_environment_and_rejects_repeated_receive(self):
        attempt = self.ready_dispatch()
        parts = ("begin-dispatch", "--dispatch-id", attempt["dispatch_id"],
                 "--claim-epoch", str(attempt["claim_epoch"]), "--role", "AG0")
        code, result = self.invoke(*parts)
        self.assertEqual((code, result["problem"]), (1, "actual_dispatch_context_required"))
        code, result = self.invoke(*parts, thread="different-thread")
        self.assertEqual((code, result["problem"]), (1, "dispatch_thread_mismatch"))
        code, result = self.invoke(*parts, "--thread-id", "fabricated-original-thread", thread="different-thread")
        self.assertEqual((code, result["problem"]), (1, "invalid_command_arguments"))
        code, result = self.invoke(*parts, thread="fabricated-original-thread")
        self.assertEqual((code, result["status"]), (0, "committed"))
        code, result = self.invoke(*parts, thread="fabricated-original-thread")
        self.assertEqual((code, result["problem"]), (1, "dispatch_already_received"))
        self.assertEqual(self.store.status()["state_revision"], 0)

    def test_result_requires_receive_and_pins_correlated_result_bytes(self):
        attempt = self.ready_dispatch()
        value = {"dispatch_id": attempt["dispatch_id"], "output": "Fabricated finite decision.", "intents": []}
        path = self.json_file("result.json", value)
        parts = ("result", "--dispatch-id", attempt["dispatch_id"], "--claim-epoch", str(attempt["claim_epoch"]),
                 "--role", "AG0", "--result-file", path)
        code, result = self.invoke(*parts, thread="fabricated-original-thread")
        self.assertEqual((code, result["problem"]), (1, "dispatch_not_received"))
        self.store.begin_dispatch({"dispatch_id": attempt["dispatch_id"], "claim_epoch": attempt["claim_epoch"],
                                   "thread_id": "fabricated-original-thread"}, "AG0")
        code, result = self.invoke(*parts, thread="different-thread")
        self.assertEqual((code, result["problem"]), (1, "dispatch_thread_mismatch"))
        code, result = self.invoke(*parts, thread="fabricated-original-thread")
        self.assertEqual((code, result["status"]), (0, "committed"))
        digest = result["result_sha256"]
        code, result = self.invoke(*parts, thread="fabricated-original-thread")
        self.assertEqual((code, result["result_sha256"]), (0, digest))
        value["output"] = "Changed decision."
        self.json_file("result.json", value)
        code, result = self.invoke(*parts, thread="fabricated-original-thread")
        self.assertEqual((code, result["problem"]), (1, "runtime_result_changed"))
        self.assertEqual(self.store.status()["state_revision"], 0)


if __name__ == "__main__":
    unittest.main()
