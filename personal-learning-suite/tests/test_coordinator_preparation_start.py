"""Formal-entry guarantees with real SQLite; no model or desktop messages."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
from coordinator.complete import TaskArtifactCoordinator
from coordinator.preparation_start import start_preparation
from coordinator.runtime_store import RuntimeStore, installed
from coordinator.workspace import GateError


class PreparationStartTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=SUITE / "tests", prefix="prep-start-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.c = TaskArtifactCoordinator(self.root)
        self.c.initialize(evidence_kind="synthetic_demo")
        (self.root / "user-request.txt").write_text("Fabricated authorization for this fixture only.", encoding="utf-8")
        self.env = patch.dict(os.environ, {"CODEX_THREAD_ID": "fixture-chat-a"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.launches = 0

    def request(self, workflow="prep-a"):
        return {"workflow_id": workflow, "authorization_ref": "user-request.txt", "purpose": "Fabricated entry validation only.",
                "stages": [{"id": "material", "role": "AG2", "output": {"id": workflow + "-material", "type": "MaterialUse"},
                            "prompt": "Write a tiny fabricated note.", "scope": ["fixture"], "use": "teaching", "review_required": True, "inputs": []},
                           {"id": "design", "role": "AG1", "output": {"id": workflow + "-design", "type": "ActivitySpec"},
                            "prompt": "Design from the exact adopted note.", "scope": ["fixture"], "use": "teaching", "review_required": False,
                            "after": ["material"], "inputs": [{"artifact": workflow + "-material", "after_task": "material", "scope": ["fixture"], "use": "teaching"}]}]}

    def preflight(self, coordinator, thread_id):
        return {"status": "ok", "thread_id": thread_id, "desktop_state": "active", "cli_available": True}

    def companion(self, coordinator, **options):
        self.launches += 1
        value = RuntimeStore(coordinator).acquire_supervisor("fixture-listener")
        return {"status": "ready", "mode": "live", "instance_id": value["instance_id"], "pid": value["pid"]}

    def start(self, request=None, **options):
        return start_preparation(self.c, request or self.request(), companion=options.pop("companion", self.companion),
                                 host_preflight=options.pop("host_preflight", self.preflight), **options)

    def test_first_start_initializes_and_takes_over_original_chat(self):
        result = self.start()
        self.assertTrue(result["runtime_takeover"])
        self.assertTrue(result["initialized_now"])
        self.assertTrue(Path(result["migration_backup"]).is_file())
        state = RuntimeStore(self.c).status()
        self.assertTrue(state["plans"][0]["enabled"])
        self.assertTrue(result["takeover_audit_sequence"])
        self.assertEqual(next(b["thread_id"] for b in state["bindings"] if b["role"] == "AG0"), "fixture-chat-a")

    def test_same_request_reuses_tables_plan_bindings_and_deadlines(self):
        first = self.start()
        before = RuntimeStore(self.c).status()
        second = self.start()
        after = RuntimeStore(self.c).status()
        self.assertFalse(second["initialized_now"])
        self.assertEqual(first["request_sha256"], second["request_sha256"])
        self.assertEqual(before["plans"], after["plans"])
        self.assertEqual(before["bindings"], after["bindings"])
        self.assertEqual(len(list((self.c.meta_root / "backups").glob("*.sqlite3"))), 1)

    def test_new_chat_adds_records_without_rebuilding_database(self):
        self.start()
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "fixture-chat-b"}):
            result = self.start(self.request("prep-b"))
        self.assertFalse(result["initialized_now"])
        state = RuntimeStore(self.c).status()
        self.assertEqual(len(state["plans"]), 2)
        self.assertEqual({b["thread_id"] for b in state["bindings"] if b["role"] == "AG0"}, {"fixture-chat-a", "fixture-chat-b"})
        self.assertEqual(len(list((self.c.meta_root / "backups").glob("*.sqlite3"))), 1)

    def test_changed_request_and_different_chat_cannot_hijack_run(self):
        self.start()
        changed = deepcopy(self.request())
        changed["purpose"] = "Changed professional scope"
        with self.assertRaisesRegex(GateError, "preparation_request_changed"):
            self.start(changed)
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "fixture-chat-b"}):
            with self.assertRaisesRegex(GateError, "preparation_request_changed"):
                self.start()

    def test_missing_actual_chat_fails_before_migration(self):
        with patch.dict(os.environ, {"CODEX_THREAD_ID": ""}):
            with self.assertRaisesRegex(GateError, "actual_preparation_thread_required"):
                self.start()
        with self.c.connect() as db:
            self.assertFalse(installed(db))

    def test_host_failure_does_not_enable_or_install(self):
        def fail(*args):
            raise GateError("preparation_desktop_unavailable")
        with self.assertRaisesRegex(GateError, "preparation_desktop_unavailable"):
            self.start(host_preflight=fail)
        with self.c.connect() as db:
            self.assertFalse(installed(db))
        self.assertEqual(self.launches, 0)

    def test_listener_failure_preserves_disabled_recoverable_plan(self):
        def fail(*args, **kwargs):
            raise GateError("companion_start_unknown")
        with self.assertRaisesRegex(GateError, "companion_start_unknown"):
            self.start(companion=fail)
        state = RuntimeStore(self.c).status()
        self.assertFalse(state["plans"][0]["enabled"])
        self.assertFalse(state["works"])
        self.assertTrue(self.start()["runtime_takeover"])

    def test_false_or_shadow_readiness_cannot_enable_plan(self):
        def shadow(*args, **kwargs):
            return {"status": "ready", "mode": "shadow"}
        with self.assertRaisesRegex(GateError, "preparation_listener_not_ready"):
            self.start(companion=shadow)
        self.assertFalse(RuntimeStore(self.c).status()["plans"][0]["enabled"])

    def test_user_disabled_plan_is_not_reenabled_by_duplicate_start(self):
        self.start()

    def test_explicit_disable_of_pending_start_is_preserved(self):
        def fail(*args, **kwargs):
            raise GateError("listener_start_failed")
        with self.assertRaises(GateError):
            self.start(companion=fail)
        RuntimeStore(self.c).set_enabled(self.c.bind_local_operator("AG0"), "prep-a", False)
        with self.assertRaisesRegex(GateError, "preparation_plan_disabled"):
            self.start()

    def test_handoff_file_failure_does_not_enable_plan(self):
        import coordinator.preparation_start as entry
        original = entry._save
        def fail_handoff(path, value):
            if path.name == "handoff.json":
                raise OSError("fabricated file persistence failure")
            return original(path, value)
        with patch.object(entry, "_save", fail_handoff), self.assertRaises(OSError):
            self.start()
        self.assertFalse(RuntimeStore(self.c).status()["plans"][0]["enabled"])

    def test_activation_and_takeover_receipt_are_atomic(self):
        original = RuntimeStore.audit
        def fail_receipt(store, db, kind, value):
            if kind == "preparation_takeover":
                raise GateError("fabricated_takeover_commit_failure")
            return original(store, db, kind, value)
        with patch.object(RuntimeStore, "audit", fail_receipt), self.assertRaisesRegex(GateError, "fabricated_takeover_commit_failure"):
            self.start()
        self.assertFalse(RuntimeStore(self.c).status()["plans"][0]["enabled"])
        RuntimeStore(self.c).set_enabled(self.c.bind_local_operator("AG0"), "prep-a", False)
        with self.assertRaisesRegex(GateError, "preparation_plan_disabled"):
            self.start()

    def test_changed_authorization_source_cannot_reuse_plan(self):
        self.start()
        (self.root / "user-request.txt").write_text("changed user authorization", encoding="utf-8")
        with self.assertRaisesRegex(GateError, "preparation_request_changed"):
            self.start()

    def test_unrelated_existing_tasks_are_not_adopted_by_runtime(self):
        from coordinator.agent_api import AgentCoordinator
        receipt = AgentCoordinator(self.c).do(self.c.bind_local_operator("AG0"),
            {"action": "assign", "task": "historical", "output": {"id": "historical-output", "type": "MaterialUse"},
             "to": "AG2", "scope": ["history"], "use": "teaching", "review_required": False, "inputs": []}, request_key="history")
        self.assertEqual(receipt["status"], "committed")
        self.start()
        with self.c.connect() as db:
            self.assertIsNone(db.execute("SELECT 1 FROM runtime_tasks WHERE task_id='historical'").fetchone())


if __name__ == "__main__":
    unittest.main()
