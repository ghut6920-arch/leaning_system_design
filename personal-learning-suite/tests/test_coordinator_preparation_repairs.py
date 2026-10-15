"""Isolation-only acceptance of batch recovery and canonical preparation sources."""
from copy import deepcopy
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
from coordinator.control_batch import run_batch, VERSION as BATCH_VERSION
from coordinator.delivery import verify_delivery
from coordinator.preparation_sources import build_map, validate_map, VERSION as MAP_VERSION
from coordinator.workspace import GateError, sha
from test_coordinator_complete import CompleteWorkflow
from read_learning_resource import outline_view


class PreparationRepairsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="preparation-repairs-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.control = {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []}
        self.w = CompleteWorkflow(self.root, lambda: deepcopy(self.control))
        self.c = self.w.coordinator
        self.api = AgentCoordinator(self.c)

    def call(self, role, intent, key=None):
        result = self.api.do(self.w.sessions[role], intent, request_key=key or "test:" + json.dumps(intent, sort_keys=True))
        self.assertEqual(result["status"], "committed", result)
        return result

    def assignment(self, task="material", *, sources=False, review=False):
        return {"action": "assign", "task": task, "output": {"id": task + "-output", "type": "MaterialUse",
                "validation": "preparation_sources" if sources else "utf8"}, "scope": ["whole"],
                "use": "teaching", "inputs": [], "review_required": review}

    def batch(self, steps):
        path = self.root / "explicit-batch.json"
        path.write_text(json.dumps({"version": BATCH_VERSION, "steps": [{"id": key, "intent": intent} for key, intent in steps]}), encoding="utf-8")
        return path

    def business(self):
        with self.c.connect() as db:
            return {t: [tuple(r) for r in db.execute('SELECT * FROM "' + t + '" ORDER BY 1')]
                    for t in ("tasks", "artifacts", "receipts", "adopted", "bundles", "events")}

    def test_batch_one_return_registers_three_tasks_and_replay_has_no_duplicate_events(self):
        plan = self.batch([(str(i), self.assignment("task" + str(i))) for i in range(3)])
        result = run_batch(self.api, self.w.sessions["AG0"], plan)
        self.assertEqual(result["committed_steps"], 3)
        baseline = self.business()
        again = run_batch(self.api, self.w.sessions["AG0"], plan)
        self.assertEqual(again["status"], "committed")
        self.assertEqual(self.business(), baseline)
        journal = json.loads(Path(again["receipts_path"]).read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(len(journal["results"]), 3)
        self.assertTrue(all(r["result"]["ticket"].startswith("request-") for r in journal["results"]))

    def test_all_batch_required_fields_checked_before_any_business_mutation(self):
        for bad in ({"action": "shell", "cmd": "anything"}, {"action": "opinion", "task": "missing"}):
            plan = self.batch([("valid", self.assignment()), ("bad", bad)])
            before = self.business()
            with self.assertRaises(GateError):
                run_batch(self.api, self.w.sessions["AG0"], plan)
            self.assertEqual(self.business(), before)

    def test_no_batch_role_switch_and_failstop_does_not_execute_later_steps(self):
        plan = self.batch([("assign", self.assignment()), ("wrong-owner", {"action": "begin", "task": "material"}),
                           ("later", self.assignment("later"))])
        result = run_batch(self.api, self.w.sessions["AG0"], plan)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["committed_steps"], 1)
        self.assertEqual(result["not_started"], ["later"])
        baseline = self.business()
        run_batch(self.api, self.w.sessions["AG0"], plan, retry_stopped=True)
        self.assertEqual(self.business(), baseline)

    def test_batch_loss_after_commit_recovers_original_alias_not_new_transition(self):
        plan = self.batch([("assign", self.assignment()), ("next", self.assignment("next"))])
        original = self.api.do
        def lost(*args, **kwargs):
            original(*args, **kwargs)
            raise KeyboardInterrupt("Simulated whole CLI loss after commit")
        with patch.object(self.api, "do", side_effect=lost):
            with self.assertRaises(KeyboardInterrupt):
                run_batch(self.api, self.w.sessions["AG0"], plan)
        result = run_batch(self.api, self.w.sessions["AG0"], plan)
        self.assertEqual(result["status"], "committed")
        self.assertEqual(len(self.c.status(self.w.sessions["AG0"])["tasks"]), 2)

    def test_batch_unknown_commit_halts_then_recovers_saved_original(self):
        plan = self.batch([("assign", self.assignment()), ("later", self.assignment("later"))])
        original = self.api.do
        def unknown(*args, **kwargs):
            result = original(*args, **kwargs)
            return {"status": "commit_status_unknown", "ticket": result["ticket"]}
        with patch.object(self.api, "do", side_effect=unknown):
            result = run_batch(self.api, self.w.sessions["AG0"], plan)
        self.assertEqual(result["not_started"], ["later"])
        result = run_batch(self.api, self.w.sessions["AG0"], plan)
        self.assertEqual(result["status"], "committed")
        self.assertEqual(len(self.c.status(self.w.sessions["AG0"])["tasks"]), 2)

    def test_changed_batch_at_same_path_and_corrupt_journal_fail_closed(self):
        plan = self.batch([("assign", self.assignment())])
        result = run_batch(self.api, self.w.sessions["AG0"], plan)
        baseline = self.business()
        self.batch([("assign", self.assignment("different"))])
        with self.assertRaisesRegex(GateError, "control_batch_changed_or_corrupt"):
            run_batch(self.api, self.w.sessions["AG0"], plan)
        self.batch([("assign", self.assignment())])
        journal = Path(result["receipts_path"])
        journal.write_text(journal.read_text(encoding="utf-8").replace('"committed"', '"not_started"'), encoding="utf-8")
        with self.assertRaisesRegex(GateError, "control_batch_changed_or_corrupt"):
            run_batch(self.api, self.w.sessions["AG0"], plan)
        self.assertEqual(self.business(), baseline)

    def test_batch_lock_and_small_budget_reject_before_business_changes(self):
        plan = self.batch([("assign", self.assignment())])
        before = self.business()
        with self.assertRaises(GateError):
            run_batch(self.api, self.w.sessions["AG0"], plan, budget=1024)
        result = run_batch(self.api, self.w.sessions["AG0"], plan)
        lock = Path(result["receipts_path"]).with_suffix(".lock")
        lock.write_text("old executor must be checked", encoding="utf-8")
        before = self.business()
        with self.assertRaisesRegex(GateError, "control_batch_busy"):
            run_batch(self.api, self.w.sessions["AG0"], plan)
        self.assertEqual(self.business(), before)
        self.assertTrue(lock.exists())

    def test_partial_log_tail_rejects_without_repeating_business_mutations(self):
        plan = self.batch([("assign", self.assignment())])
        result = run_batch(self.api, self.w.sessions["AG0"], plan)
        before = self.business()
        with Path(result["receipts_path"]).open("ab") as stream:
            stream.write(b'{"partial":')
        with self.assertRaisesRegex(GateError, "control_batch_changed_or_corrupt"):
            run_batch(self.api, self.w.sessions["AG0"], plan)
        self.assertEqual(self.business(), before)

    def test_rejected_frozen_ticket_is_never_recompiled_on_batch_resume(self):
        plan = self.batch([("assign", self.assignment()), ("later", self.assignment("later"))])
        original = self.api.prepare
        def change_control(*args, **kwargs):
            result = original(*args, **kwargs)
            self.control["state_revision"] += 1
            return result
        with patch.object(self.api, "prepare", side_effect=change_control):
            result = run_batch(self.api, self.w.sessions["AG0"], plan)
        self.assertEqual(result["stopped"]["problem"], "prepared_controls_changed")
        ticket = result["stopped"]["ticket"]
        with patch.object(self.api, "prepare", side_effect=AssertionError("Must not prepare a new decision")):
            retried = run_batch(self.api, self.w.sessions["AG0"], plan, retry_stopped=True)
        self.assertEqual(retried["stopped"]["ticket"], ticket)
        self.assertEqual(retried["committed_steps"], 0)

    def test_source_builder_rejects_forbidden_paths_before_reading_them(self):
        _, members, _ = self.source_setup()
        members[0]["path"] = "state/current.md"
        before = self.business()
        with patch.object(self.c, "file_info", side_effect=AssertionError("Forbidden body must not be read")):
            with self.assertRaisesRegex(GateError, "unsafe_preparation_source_path"):
                build_map(self.c, self.w.sessions["AG2"], "material", members)
        self.assertEqual(self.business(), before)

    def test_independently_registered_member_must_use_fixed_input_gates(self):
        value, _, path = self.source_setup()
        self.call("AG0", self.assignment("separate"))
        self.call("AG2", {"action": "begin", "task": "separate"})
        self.call("AG2", {"action": "deliver", "task": "separate", "path": "questions/visible/task-v1.md"})
        with self.assertRaisesRegex(GateError, "registered_source_requires_fixed_input"):
            self.api.prepare(self.w.sessions["AG2"], {"action": "deliver", "task": "material", "path": "artifacts/sources-v1.json"})

    def test_preparation_profile_not_available_to_design_type(self):
        intent = self.assignment()
        intent["output"].update(type="ActivitySpec", validation="preparation_sources")
        before = self.business()
        with self.assertRaisesRegex(GateError, "ag2_material_sources_required"):
            self.api.prepare(self.w.sessions["AG0"], intent)
        self.assertEqual(self.business(), before)

    def test_outline_has_no_body_and_exact_parent_ranges_ignore_code_headings(self):
        path = self.root / "mixed-state.md"
        text = "说明\r\n## 当前有效状态 / revision22\r\n实际原段。\r\n### 子项\r\n必要条件。\r\n```python\r\n## 假标题\r\n```\r\n## 前一状态\r\n很长旧史。\r\n"
        path.write_bytes(text.encode("utf-8"))
        value = outline_view(path, limit=1)
        self.assertEqual(value["heading_total"], 3)
        self.assertNotIn("text", value)
        self.assertEqual(value["preface_end"], len("说明\r\n"))
        row = value["headings"][0]
        self.assertEqual(text[row["start"]:row["end"]], text[text.index("## 当前"):text.index("## 前一")])
        self.assertNotIn("很长旧史", text[row["start"]:row["end"]])
        continuation = outline_view(path, start=1, expected=value["source"]["view_sha256"])
        self.assertEqual(continuation["headings"][0]["heading"], "### 子项")
        path.write_bytes((text + "改动").encode("utf-8"))
        with self.assertRaisesRegex(GateError, "read_version_changed"):
            outline_view(path, expected=value["source"]["view_sha256"])

    def test_outline_unclosed_code_and_invalid_window_reject(self):
        path = self.root / "mixed-state.md"
        path.write_text("## 原段\n```\n未闭合\n", encoding="utf-8")
        with self.assertRaisesRegex(GateError, "unclosed_markdown_fence_use_text"):
            outline_view(path)
        with self.assertRaisesRegex(GateError, "invalid_heading_window"):
            outline_view(path, limit=25)

    def test_outline_batch_cli_is_bounded_and_body_not_returned(self):
        path = self.root / "mixed-state.md"
        path.write_text("## 当前原段\n当前必要正文。\n## 旧史\n" + "巨大旧史" * 10000, encoding="utf-8")
        request = self.root / "read-plan.json"
        request.write_text(json.dumps({"version": "read-batch/0.1.0", "jobs": [{"id": "state", "kind": "resource",
             "files": [str(path)], "view": "outline", "heading_limit": 1}]}), encoding="utf-8")
        process = subprocess.run([sys.executable, "-B", str(SUITE / "scripts/read_learning_batch.py"),
                                  "--request-file", str(request)], capture_output=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        value = verify_delivery(process.stdout)["jobs"][0]["result"]
        self.assertEqual(len(value["headings"]), 1)
        self.assertNotIn("text", value)
        self.assertLessEqual(len(process.stdout), 8192)

    def test_batch_existing_control_gate_stops_all_paused_steps(self):
        plan = self.batch([("assign", self.assignment()), ("later", self.assignment("later"))])
        self.control["paused_ids"] = ["material-output"]
        result = run_batch(self.api, self.w.sessions["AG0"], plan)
        self.assertEqual(result["committed_steps"], 0)
        self.assertEqual(result["not_started"], ["later"])
        self.assertEqual(result["stopped"]["problem"], "paused_scope")

    def test_cli_batch_returns_complete_bounded_control_summary(self):
        plan = self.batch([("assign", self.assignment()), ("second", self.assignment("second"))])
        process = subprocess.run([sys.executable, "-B", str(SUITE / "scripts/coordinate_agents.py"),
            "--workspace", str(self.root), "--role", "AG0", "batch", "--plan-file", str(plan)],
            capture_output=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        result = verify_delivery(process.stdout)
        self.assertEqual(result["committed_steps"], 2)
        self.assertLessEqual(len(process.stdout), 8192)

    def source_setup(self, *, review=False):
        self.call("AG0", self.assignment(sources=True, review=review))
        self.call("AG2", {"action": "begin", "task": "material"})
        members = []
        for key, kind, path, text in [
            ("task", "formal_task", "questions/visible/task-v1.md", "Fabricated one continuous task with actual conditions.\n"),
            ("lesson", "mainline", "questions/visible/lesson-v1.md", "Fabricated full teaching bridge and example.\n"),
            ("reference", "teacher_reference", "questions/teacher-reference/reference-v1.md", "Full legal reasoning, all cases and scoring limits.\n" * 900),
            ("check", "material_report", "artifacts/material-check-v1.md", "Checked specific connections. Pending effect; see task/reference.\n"),
        ]:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            members.append({"id": key, "kind": kind, "path": path})
        value = build_map(self.c, self.w.sessions["AG2"], "material", members)
        map_path = self.root / "artifacts/sources-v1.json"
        map_path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return value, members, map_path

    def publish_map(self, *, review=False):
        value, members, path = self.source_setup(review=review)
        delivered = self.call("AG2", {"action": "deliver", "task": "material", "path": "artifacts/sources-v1.json"})
        self.call("AG2", {"action": "opinion", "task": "material", "outcome": "supported", "rationale": "Fabricated explicit professional findings."})
        return value, members, path, delivered

    def test_one_canonical_task_with_full_reference_and_no_embedded_copies(self):
        value, _, path = self.source_setup()
        self.assertEqual(value["version"], MAP_VERSION)
        self.assertEqual(sum(e["kind"] == "formal_task" for e in value["entries"]), 1)
        self.assertNotIn("Full legal reasoning", path.read_text(encoding="utf-8"))
        reference = next(e for e in value["entries"] if e["kind"] == "teacher_reference")
        self.assertEqual(reference["sha256"], sha((self.root / reference["path"]).read_bytes()))
        self.assertGreater(reference["bytes"], 40000)

    def test_incomplete_map_duplicate_task_paths_bytes_and_extra_body_reject(self):
        value, _, _ = self.source_setup()
        cases = []
        incomplete = deepcopy(value); incomplete["entries"] = incomplete["entries"][:3]; cases.append(incomplete)
        duplicate = deepcopy(value); duplicate["entries"].append(deepcopy(duplicate["entries"][0])); cases.append(duplicate)
        second_task = deepcopy(value); second_task["entries"][1]["kind"] = "formal_task"; cases.append(second_task)
        copied = deepcopy(value); copied["entries"][1]["sha256"] = copied["entries"][0]["sha256"]; cases.append(copied)
        body = deepcopy(value); body["entries"][0]["text"] = "Repeated body"; cases.append(body)
        for bad in cases:
            with self.assertRaises(GateError):
                validate_map(bad)

    def test_map_wrong_identity_use_scope_and_control_paths_cannot_submit(self):
        value, _, path = self.source_setup()
        for key, wrong in [("artifact_ref", {"id": "other", "revision": 1}), ("intended_use", "independent"), ("scope", ["other"])]:
            changed = {**value, key: wrong}
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(GateError, "preparation_sources_identity_mismatch"):
                self.api.prepare(self.w.sessions["AG2"], {"action": "deliver", "task": "material", "path": "artifacts/sources-v1.json"})
        value["entries"][0]["path"] = "state/current.md"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(GateError, "unsafe_preparation_source_path"):
            self.api.prepare(self.w.sessions["AG2"], {"action": "deliver", "task": "material", "path": "artifacts/sources-v1.json"})

    def test_member_tamper_after_prepare_rejects_original_frozen_ticket(self):
        _, members, _ = self.source_setup()
        ticket = self.api.prepare(self.w.sessions["AG2"], {"action": "deliver", "task": "material", "path": "artifacts/sources-v1.json"})["ticket"]
        (self.root / members[0]["path"]).write_text("Changed after preparing original decision", encoding="utf-8")
        result = self.api.apply(self.w.sessions["AG2"], ticket)
        self.assertNotEqual(result["status"], "committed")
        self.assertFalse(self.c.status(self.w.sessions["AG0"])["artifacts"])

    def test_source_map_adoption_still_requires_ag3_and_member_changes_block_current(self):
        _, members, _, delivered = self.publish_map(review=True)
        with self.assertRaisesRegex(GateError, "ag3_review_required"):
            self.api.prepare(self.w.sessions["AG0"], {"action": "adopt", "tasks": ["material"]})
        self.call("AG0", {"action": "assign_review", "task": "review", "from_task": "material"})
        self.call("AG3", {"action": "begin", "task": "review"})
        self.call("AG3", {"action": "opinion", "task": "review", "outcome": "supported", "rationale": "Fabricated scoped review, no real assessment."})
        self.call("AG0", {"action": "adopt", "tasks": ["material"]})
        self.assertEqual(self.c.resolve(self.w.sessions["AG0"], "material-output", "teaching", ["whole"])["ref"], delivered["ref"])
        (self.root / members[2]["path"]).write_text("Reference tampered", encoding="utf-8")
        with self.assertRaisesRegex(GateError, "preparation_source_fingerprint_changed"):
            self.c.resolve(self.w.sessions["AG0"], "material-output", "teaching", ["whole"])

    def test_authorized_readback_reads_exact_full_reference_without_copying(self):
        _, _, _, _ = self.publish_map()
        self.call("AG0", {"action": "assign_readback", "task": "readback", "from_task": "material",
            "output": {"id": "readback-output", "type": "ActivitySpec", "validation": "utf8"},
            "scope": ["whole"], "use": "teaching", "review_required": False, "provisional_conditions": "Candidate reference for functional readback only."})
        self.call("AG1", {"action": "begin", "task": "readback"})
        item = self.c.preparation_source(self.w.sessions["AG1"], "reference", task_id="readback", input_index=0)
        self.assertEqual(item["content"], (self.root / "questions/teacher-reference/reference-v1.md").read_bytes())
        with self.assertRaises(GateError):
            self.c.preparation_source(self.w.sessions["AG3"], "reference", task_id="readback", input_index=0)
        with self.assertRaisesRegex(GateError, "preparation_source_not_found"):
            self.c.preparation_source(self.w.sessions["AG1"], "unknown", task_id="readback", input_index=0)
        self.control["paused_ids"] = ["material-output"]
        with self.assertRaisesRegex(GateError, "paused_scope"):
            self.c.preparation_source(self.w.sessions["AG1"], "reference", task_id="readback", input_index=0)

    def test_canonical_builder_does_not_submit_and_never_overwrites_map(self):
        _, members, _ = self.source_setup()
        members_file = self.root / "members.json"
        members_file.write_text(json.dumps(members), encoding="utf-8")
        args = [sys.executable, "-B", str(SUITE / "scripts/build_preparation_sources.py"),
                "--workspace", str(self.root), "--task", "material", "--members-file", str(members_file),
                "--output", "artifacts/new-sources-v1.json"]
        process = subprocess.run(args, capture_output=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        data = (self.root / "artifacts/new-sources-v1.json").read_bytes()
        process = subprocess.run(args, capture_output=True, timeout=30)
        self.assertEqual(process.returncode, 1)
        self.assertEqual((self.root / "artifacts/new-sources-v1.json").read_bytes(), data)
        state = self.c.status(self.w.sessions["AG0"])
        self.assertFalse(state["artifacts"])
        self.assertFalse(state["receipts"])

    def test_current_source_cli_returns_bound_window_and_full_delivery_marker(self):
        _, _, _, _ = self.publish_map()
        self.call("AG0", {"action": "adopt", "tasks": ["material"]})
        process = subprocess.run([sys.executable, "-B", str(SUITE / "scripts/coordinate_agents.py"),
            "--workspace", str(self.root), "--role", "AG0", "current", "--artifact-id", "material-output",
            "--intended-use", "teaching", "--scope", "whole", "--source", "reference", "--view", "text"],
            capture_output=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = verify_delivery(process.stdout)
        self.assertEqual(result["source_id"], "reference")
        self.assertTrue(result["coverage"]["has_more"])
        self.assertLessEqual(len(process.stdout), 8192)

    def test_readback_cancel_between_snapshot_and_member_read_is_rechecked(self):
        self.publish_map()
        self.call("AG0", {"action": "assign_readback", "task": "readback", "from_task": "material",
            "output": {"id": "readback-output", "type": "ActivitySpec", "validation": "utf8"},
            "scope": ["whole"], "use": "teaching", "review_required": False, "provisional_conditions": "Candidate readback only."})
        self.call("AG1", {"action": "begin", "task": "readback"})
        original = self.c.read_snapshot
        def cancel(*args, **kwargs):
            result = original(*args, **kwargs)
            self.call("AG0", {"action": "stop", "task": "readback", "outcome": "cancelled", "reason": "Fabricated cancellation during read."})
            return result
        with patch.object(self.c, "read_snapshot", side_effect=cancel):
            with self.assertRaisesRegex(GateError, "task_snapshot_not_available"):
                self.c.preparation_source(self.w.sessions["AG1"], "reference", task_id="readback", input_index=0)

    def test_current_opinion_change_between_parent_and_member_read_is_rechecked(self):
        self.publish_map()
        self.call("AG0", {"action": "adopt", "tasks": ["material"]})
        original = self.c.resolve
        def conflict(*args, **kwargs):
            result = original(*args, **kwargs)
            self.call("AG2", {"action": "opinion", "task": "material", "outcome": "partial", "rationale": "Fabricated conflicting new finding."})
            return result
        with patch.object(self.c, "resolve", side_effect=conflict):
            with self.assertRaises(GateError):
                self.c.preparation_source(self.w.sessions["AG0"], "reference", artifact_id="material-output", intended_use="teaching", scope=["whole"])


if __name__ == "__main__":
    unittest.main()
