"""Legitimate candidate readback and bounded, receiver-checked read transport."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
sys.path.insert(0, str(SUITE / "scripts"))
from coordinator.agent_api import AgentCoordinator
from coordinator.control_projection import diagnose, replace_projection
from coordinator.delivery import bounded_output, body_nodes, verify_delivery
from coordinator.reading import text_page
from coordinator.workspace import FileControlGate, GateError, sha
from read_learning_batch import run_batch
from test_coordinator_complete import CompleteWorkflow


class CandidateReadbackTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.control = {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []}
        self.w = CompleteWorkflow(self.root, lambda: deepcopy(self.control))
        self.c, self.api = self.w.coordinator, AgentCoordinator(self.w.coordinator)
        self.w.register("source", "material", review=True)
        self.w.op("AG2", "start", task_id="source")
        self.ref = self.w.submit("source")["ref"]

    def intent(self, **extra):
        return {"action": "assign_readback", "task": "functional-readback", "from_task": "source",
                "output": {"id": "functional-report", "type": "ActivitySpec", "validation": "utf8"},
                "scope": ["whole"], "use": "teaching", "review_required": False,
                "provisional_conditions": "Fabricated functional readback; candidate is not adopted.", **extra}

    def run_intent(self, role, intent):
        prepared = self.api.prepare(self.w.sessions[role], intent)
        result = self.api.apply(self.w.sessions[role], prepared["ticket"])
        self.assertEqual(result["status"], "committed", result)
        return result

    def start_readback(self):
        self.run_intent("AG0", self.intent())
        self.run_intent("AG1", {"action": "begin", "task": "functional-readback"})

    def test_candidate_readback_pins_source_without_review_or_copy_and_cannot_adopt(self):
        files = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*.md"))
        prepared = self.api.prepare(self.w.sessions["AG0"], self.intent())
        self.assertEqual(prepared["preview"]["inputs"][0]["revision"], self.ref["revision"])
        self.api.apply(self.w.sessions["AG0"], prepared["ticket"])
        self.run_intent("AG1", {"action": "begin", "task": "functional-readback"})
        item = self.c.read_snapshot(self.w.sessions["AG1"], "functional-readback")[0]
        self.assertEqual(item["ref"], self.ref)
        self.assertEqual(sha(item["content"]), item["sha256"])
        state = self.c.status(self.w.sessions["AG0"])
        self.assertFalse(any(t["task_kind"] == "review" for t in state["tasks"]))
        self.assertEqual(files, sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*.md")))
        with self.assertRaises(GateError):
            self.api.prepare(self.w.sessions["AG0"], {"action": "adopt", "tasks": ["source"]})

    def test_readback_authorization_use_scope_and_provisional_fields_are_explicit(self):
        for role, changes in (("AG1", {}), ("AG0", {"use": "another-use"}),
                              ("AG0", {"scope": ["other"]}), ("AG0", {"provisional_conditions": ""}),
                              ("AG0", {"to": "AG2"})):
            with self.subTest(role=role, changes=changes), self.assertRaises(GateError):
                self.api.prepare(self.w.sessions[role], self.intent(**changes))

    def test_readback_begin_and_owner_are_required(self):
        self.run_intent("AG0", self.intent())
        with self.assertRaises(GateError):
            self.c.read_snapshot(self.w.sessions["AG1"], "functional-readback")
        self.run_intent("AG1", {"action": "begin", "task": "functional-readback"})
        with self.assertRaises(GateError):
            self.c.read_snapshot(self.w.sessions["AG2"], "functional-readback")

    def test_later_candidate_does_not_replace_fixed_readback(self):
        self.start_readback()
        newer = self.w.candidate("material", review=True)["ref"]
        self.assertNotEqual(newer, self.ref)
        self.assertEqual(self.c.read_snapshot(self.w.sessions["AG1"], "functional-readback")[0]["ref"], self.ref)

    def test_paused_deleted_restricted_or_changed_bytes_block_readback(self):
        self.start_readback()
        for field in ("paused_ids", "deleted_ids"):
            self.control[field] = ["material"]
            with self.subTest(field=field), self.assertRaises(GateError):
                self.c.read_snapshot(self.w.sessions["AG1"], "functional-readback")
            self.control[field] = []
        self.control["restrictions"] = [{"scope_ids": ["material"], "intended_uses": ["teaching"]}]
        with self.assertRaises(GateError):
            self.c.read_snapshot(self.w.sessions["AG1"], "functional-readback")
        self.control["restrictions"] = []
        item = self.c.read_snapshot(self.w.sessions["AG1"], "functional-readback")[0]
        (self.root / item["path"]).write_bytes(b"changed")
        with self.assertRaises(GateError):
            self.c.read_snapshot(self.w.sessions["AG1"], "functional-readback")

    def test_owner_provisional_confirmation_is_explicit_and_does_not_allow_adoption(self):
        self.w.register("dependent", "dependent-material", inputs=[{**self.ref, "policy": "exact", "scope": ["whole"],
                        "intended_use": "teaching", "provisional_conditions": "Candidate dependency only."}], review=True)
        self.w.op("AG2", "start", task_id="dependent")
        self.w.submit("dependent")
        opinion = {"action": "opinion", "task": "dependent", "outcome": "supported", "rationale": "Fabricated actual check."}
        with self.assertRaises(GateError):
            self.api.prepare(self.w.sessions["AG2"], opinion)
        with self.assertRaises(GateError):
            self.api.prepare(self.w.sessions["AG2"], {**opinion, "allow_provisional": "true"})
        self.run_intent("AG2", {**opinion, "allow_provisional": True})
        with self.assertRaises(GateError):
            self.api.prepare(self.w.sessions["AG0"], {"action": "adopt", "tasks": ["dependent"]})


class ControlProjectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=SUITE / "tests", prefix="control-projection-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "coordination").mkdir()
        self.source = self.root / "control.md"
        self.source.write_bytes(b"Fabricated control: pause material.")
        self.destination = self.root / "coordination/control.json"
        self.old = {"state_revision": 1, "paused_ids": ["material"], "deleted_ids": ["deleted"],
                    "restrictions": [{"scope_ids": ["restricted"], "intended_uses": ["teaching"]}],
                    "source_refs": [{"path": "control.md", "sha256": sha(self.source.read_bytes())}]}
        self.destination.write_text(json.dumps(self.old), encoding="utf-8")
        self.gate = FileControlGate(self.root, self.destination)
        self.expected = sha(self.destination.read_bytes())
        self.candidate = self.root / "interpreted.json"

    def proposed(self, **extra):
        new = {**deepcopy(self.old), "state_revision": 2, "interpretation_rationale": "Actual changed source interpreted; constraints retained.", **extra}
        new["source_refs"][0]["sha256"] = sha(self.source.read_bytes())
        self.candidate.write_text(json.dumps(new), encoding="utf-8")

    def test_stale_diagnosis_and_explicit_update_retain_restrictions(self):
        self.source.write_bytes(b"Fabricated changed control; same explicit restrictions.")
        status = diagnose(self.gate)
        self.assertFalse(status["current"])
        self.assertEqual(status["source_refs"][0]["actual_sha256"], sha(self.source.read_bytes()))
        with self.assertRaises(GateError):
            self.gate()
        self.proposed()
        replace_projection(self.gate, self.candidate, expected_projection_sha256=self.expected)
        current = self.gate()
        for field in ("paused_ids", "deleted_ids", "restrictions"):
            self.assertEqual(current[field], self.old[field])

    def test_no_hash_only_omitted_controls_source_swap_or_stale_overwrite(self):
        for change in ({"interpretation_rationale": ""}, {"state_revision": 1}, {"restrictions": None}):
            self.proposed(**change)
            with self.subTest(change=change), self.assertRaises(GateError):
                replace_projection(self.gate, self.candidate, expected_projection_sha256=self.expected)
        self.proposed()
        with self.assertRaises(GateError):
            replace_projection(self.gate, self.candidate, expected_projection_sha256="0" * 64)
        (self.root / "other.md").write_bytes(b"other")
        self.proposed(source_refs=[{"path": "other.md", "sha256": sha(b"other")}])
        with self.assertRaises(GateError):
            replace_projection(self.gate, self.candidate, expected_projection_sha256=self.expected)
        self.assertEqual(sha(self.destination.read_bytes()), self.expected)

    def test_source_changed_at_write_boundary_does_not_replace_projection(self):
        self.proposed()
        import coordinator.control_projection as module
        original = module.source_rows
        calls = []
        def change(gate, data):
            calls.append(1)
            if len(calls) == 3:
                self.source.write_bytes(b"concurrent source change")
            return original(gate, data)
        with patch.object(module, "source_rows", side_effect=change), self.assertRaises(GateError):
            replace_projection(self.gate, self.candidate, expected_projection_sha256=self.expected)
        self.assertEqual(sha(self.destination.read_bytes()), self.expected)
        self.assertFalse(list(self.destination.parent.glob(".control-*.tmp")))

    def test_cli_diagnosis_works_without_database_and_wrong_role_cannot_update(self):
        prefix = [sys.executable, "-B", str(SUITE / "scripts/coordinate_agents.py"), "--workspace", str(self.root)]
        process = subprocess.run(prefix + ["--role", "AG0", "control-status"], capture_output=True, timeout=20)
        self.assertEqual(process.returncode, 0, process.stdout)
        self.assertTrue(verify_delivery(process.stdout)["current"])
        self.proposed()
        process = subprocess.run(prefix + ["--role", "AG1", "control-update", "--projection-file", str(self.candidate),
                                          "--expect-projection-sha256", self.expected], capture_output=True, timeout=20)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(json.loads(process.stdout)["problem"], "ag0_control_projection_required")
        self.assertEqual(sha(self.destination.read_bytes()), self.expected)

    def test_parallel_update_lock_is_not_stolen(self):
        self.proposed()
        lock = self.destination.with_name("." + self.destination.name + ".update-lock")
        lock.write_text("other live writer", encoding="utf-8")
        with self.assertRaises(GateError) as error:
            replace_projection(self.gate, self.candidate, expected_projection_sha256=self.expected)
        self.assertEqual(error.exception.code, "control_projection_busy")
        self.assertEqual(lock.read_text(encoding="utf-8"), "other live writer")
        self.assertEqual(sha(self.destination.read_bytes()), self.expected)


class ReadDeliveryTests(unittest.TestCase):
    def test_total_serialized_budget_and_unicode_resume_preserve_all_text(self):
        text = ('中文🙂\r\n"\\条件\n' * 800)
        for plain in (False, True):
            offset, joined, requests = 0, "", 0
            while offset < len(text):
                output = bounded_output({"status": "ok", **text_page(text, offset=offset, max_chars=None)}, budget=1800, plain_text=plain)
                self.assertLessEqual(len(output.encode()), 1800)
                payload = verify_delivery(output)
                self.assertGreater(payload["coverage"]["end"], offset)
                self.assertFalse(payload["coverage"]["complete"])
                joined += payload["text"]
                offset = payload["coverage"]["end"]
                requests += 1
            self.assertGreater(requests, 1)
            self.assertEqual(joined, text)

    def test_outer_truncation_and_changed_text_are_detected_in_both_formats(self):
        for plain in (False, True):
            output = bounded_output({"status": "ok", **text_page("first\n中文🙂\nlast")}, plain_text=plain)
            self.assertEqual(verify_delivery(output)["text"], "first\n中文🙂\nlast")
            for broken in (output[:-10], output.replace("first", "other"), "Warning: truncated output\n" + output):
                with self.subTest(plain=plain), self.assertRaises(GateError):
                    verify_delivery(broken)

    def test_metadata_is_never_silently_dropped_to_claim_success(self):
        with self.assertRaises(GateError):
            bounded_output({"status": "ok", "entries": ["very long metadata" * 1000]}, budget=1024)

    def test_combined_jobs_share_budget_with_each_missing_range_visible(self):
        result = {"status": "ok", "jobs": [{"id": str(i), "result": text_page("文" * 3000)} for i in range(2)]}
        output = bounded_output(result, budget=2048)
        payload = verify_delivery(output)
        self.assertLessEqual(len(output.encode()), 2048)
        self.assertEqual(len(payload["jobs"]), 2)
        self.assertTrue(all(r["coverage"]["has_more"] for r in body_nodes(payload)))
        self.assertEqual(payload["jobs"][1]["result"]["coverage"]["next_offset"], 0)

    def test_real_strategy_batch_reconstructs_same_frozen_view_without_overlap(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        from read_learning_resource import strategy_document
        paths = [SUITE / "resources/strategies" / p for p in ("encoding/S05.json", "encoding/R04.json", "post/retrieve-relation.json", "post/select-method.json")]
        text, _ = strategy_document(paths)
        # Same two-page batch shape as the incident, with an explicit shared budget.
        path = root / "request.json"
        path.write_text(json.dumps({"version": "read-batch/0.1.0", "jobs": [
            {"id": "strategy", "kind": "resource", "files": [str(p) for p in paths], "view": "strategy", "max_chars": 15000}]}), encoding="utf-8")
        first = run_batch(path, budget=4096)
        payload = verify_delivery(bounded_output(first, budget=4096))
        page = payload["jobs"][0]["result"]
        self.assertTrue(page["coverage"]["has_more"])
        joined, offset, expected = page["text"], page["coverage"]["end"], page["coverage"]["view_sha256"]
        # Pure renderer replay avoids repeated subprocess starts; all remaining
        # characters of the real required view are checked, not a short mock.
        while offset < len(text):
            page = verify_delivery(bounded_output({"status": "ok", **text_page(text, offset=offset, max_chars=15000)}, budget=4096))
            self.assertEqual(page["coverage"]["view_sha256"], expected)
            joined += page["text"]
            offset = page["coverage"]["end"]
        self.assertEqual(joined, text)

    def test_batch_rejects_mutations_before_any_subprocess_runs(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "request.json"
        path.write_text(json.dumps({"version": "read-batch/0.1.0", "jobs": [
            {"id": "bad", "kind": "coordinator", "workspace": ".", "role": "AG0", "command": "do"}]}), encoding="utf-8")
        with patch("read_learning_batch.subprocess.run") as run, self.assertRaises(GateError):
            run_batch(path)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
