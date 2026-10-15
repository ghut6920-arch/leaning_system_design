"""Original-proposal acceptance; all test business files are fabricated."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
from demo_coordinator_workspace import Workflow
from coordinator.complete import TaskArtifactCoordinator
from coordinator.workspace import GateError, sha
from coordinator.publication import publish_file
from coordinator.reliability import ReliableCoordinator


class CompleteWorkflow(Workflow):
    def __init__(self, root, control_gate=None):
        super().__init__(root, control_gate, coordinator_class=TaskArtifactCoordinator)

    def register(self, task_id, artifact_id, **kwargs):
        state = self.coordinator.status(self.sessions["AG0"])
        existing = [a for a in state["artifacts"] if a["id"] == artifact_id]
        base = max(existing, key=lambda a: a["revision"]) if existing else None
        inputs = deepcopy(kwargs.get("inputs") or [])
        for item in inputs:
            if item["policy"] == "exact":
                item.setdefault("provisional_conditions", "Fabricated explicit provisional condition; not a default adopted input")
        return self.op("AG0", "register", id=task_id, assignee=kwargs.get("role", "AG2"), task_kind="production",
                       intended_use="teaching", scope=kwargs.get("scope") or ["whole"], inputs=inputs,
                       base_ref={"id": base["id"], "revision": base["revision"]} if base else None,
                       output={"id": artifact_id, "type": kwargs.get("kind", "MaterialUse"), "requires_ag3_review": kwargs.get("review", False), "validation_profile": "utf8"})

    def adopt(self, target, receipts, *, scope=None, expect="committed"):
        parts = scope or ["whole"]
        pointers = self.coordinator.status(self.sessions["AG0"])["adopted_pointers"]
        expected = [{"id": target["id"], "intended_use": "teaching", "scope": s,
                     "revision": next((p["revision"] for p in pointers if p["id"] == target["id"] and p["scope"] == s), None)} for s in parts]
        return self.op("AG0", "adopt", expect=expect, bundle_id=f"bundle-{self.sequence + 1}", expected_pointers=expected,
                       members=[{"ref": target, "scope": parts, "intended_use": "teaching", "receipt_ids": receipts}])


class CoordinatorCompleteTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tac-complete-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.control = {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []}
        self.w = CompleteWorkflow(self.root, lambda: deepcopy(self.control))
        self.c = self.w.coordinator

    def state(self):
        return self.c.status(self.w.sessions["AG0"])

    def seed(self, *, scope=None, review=False):
        target = self.w.candidate("material", scope=scope, review=review)["ref"]
        receipts = [self.w.confirm(target, scope=scope)]
        if review:
            receipts.append(self.w.review(target, scope=scope))
        self.w.adopt(target, receipts, scope=scope)
        return target, receipts

    def child(self, source, *, scope=None, name="child"):
        self.w.register(name, name + "-output", role="AG1", kind="ActivitySpec", scope=scope,
                        inputs=[{**source, "policy": "adopted", "scope": scope or ["whole"], "intended_use": "teaching"}])
        self.w.op("AG1", "start", task_id=name)

    def test_all_five_states_and_superseded_never_returns_as_candidate(self):
        self.w.register("first", "material", review=True)
        self.assertEqual(self.state()["drafts"][0]["state"], "Draft")
        self.w.op("AG2", "start", task_id="first")
        first = self.w.submit("first")["ref"]
        self.assertEqual(self.state()["artifacts"][0]["state"], "Candidate")
        owner = self.w.confirm(first)
        self.assertEqual(self.state()["artifacts"][0]["state"], "Candidate")
        reviewed = self.w.review(first)
        self.assertEqual(self.state()["artifacts"][0]["state"], "Verified")
        self.w.adopt(first, [owner, reviewed])
        self.assertEqual(self.state()["artifacts"][0]["state"], "Adopted")
        second = self.w.candidate("material", review=True)["ref"]
        receipts = [self.w.confirm(second), self.w.review(second)]
        self.w.adopt(second, receipts)
        self.assertEqual([a["state"] for a in self.state()["artifacts"]], ["Superseded", "Adopted"])

    def test_parallel_drafts_have_distinct_versions_and_cancelled_gaps_work(self):
        first, _ = self.seed()
        a = self.w.register("draft-a", "material")
        b = self.w.register("draft-b", "material")
        self.assertEqual([a["draft_ref"]["revision"], b["draft_ref"]["revision"]], [2, 3])
        self.w.op("AG2", "finish", task_id="draft-a", phase="cancelled", reason="Fabricated cancelled revision")
        self.w.op("AG2", "start", task_id="draft-b")
        third = self.w.submit("draft-b")["ref"]
        owner = self.w.confirm(third)
        self.w.adopt(third, [owner])
        self.assertEqual(self.c.diff(self.w.sessions["AG0"], first, third)["changed_scope"], None)

    def test_draft_path_keeps_running_until_actual_submission(self):
        self.seed()
        self.w.register("revision", "material")
        self.w.op("AG2", "draft", task_id="revision", draft_path="drafts/revision.md", planned_changed_scope=["whole"])
        self.w.op("AG2", "start", task_id="revision")
        self.assertEqual(len(self.state()["artifacts"]), 1)
        self.assertEqual(next(t for t in self.state()["tasks"] if t["id"] == "revision")["phase"], "running")
        self.assertIsNone(next(t for t in self.state()["tasks"] if t["id"] == "revision")["output_receipt"])
        original = self.state()["artifacts"][0]["path"]
        refusal = self.w.op("AG2", "draft", expect="rejected", task_id="revision", draft_path=original)
        self.assertEqual(refusal["reasons"], ["draft_cannot_overwrite_version"])

    def test_existing_output_requires_explicit_base(self):
        self.seed()
        refusal = self.w.op("AG0", "register", expect="rejected", id="missing-base", assignee="AG2", task_kind="production",
                            intended_use="teaching", scope=["whole"], inputs=[], output={"id": "material", "type": "MaterialUse", "requires_ag3_review": False})
        self.assertEqual(refusal["reasons"], ["explicit_revision_base_required"])

    def test_candidate_warning_then_adoption_recheck_and_unrelated_scope_continues(self):
        first, _ = self.seed(scope=["M1", "M3"])
        self.child(first, scope=["M1"], name="m1")
        self.child(first, scope=["M3"], name="m3")
        second = self.w.candidate("material", scope=["M1", "M3"], changed_scope=["M3"])["ref"]
        impacts = self.state()["impacts"]
        self.assertEqual({i["target_id"] for i in impacts}, {"m3"})
        self.assertEqual({i["severity"] for i in impacts}, {"candidate_warning"})
        self.assertEqual(self.state()["adopted_pointers"][0]["revision"], 1)
        owner = self.w.confirm(second, scope=["M1", "M3"])
        self.w.adopt(second, [owner], scope=["M1", "M3"])
        self.assertEqual({i["severity"] for i in self.state()["impacts"]}, {"recheck_required"})
        self.assertEqual(self.c.read_snapshot(self.w.sessions["AG1"], "m3")[0]["ref"], first)

    def test_submitted_downstream_recheck_resolves_impact_but_next_update_reopens(self):
        first, _ = self.seed()
        self.child(first)
        child = self.w.submit("child", role="AG1")["ref"]
        second = self.w.candidate("material")["ref"]
        self.w.adopt(second, [self.w.confirm(second)])
        self.assertTrue(self.state()["impacts"])
        self.w.op("AG1", "recheck", ref=child, recheck_id="local", old_ref=first, new_ref=second,
                  scope=["whole"], intended_use="teaching", rationale="Fabricated local compatibility judgment")
        self.assertFalse(self.state()["impacts"])
        third = self.w.candidate("material")["ref"]
        self.w.adopt(third, [self.w.confirm(third)])
        self.assertTrue(self.state()["impacts"])

    def test_summary_and_boundary_expose_responsibility_without_body(self):
        first, _ = self.seed()
        self.child(first)
        brief = self.c.brief(self.w.sessions["AG0"])
        self.assertIn("material v1", brief)
        self.assertIn("AG1", brief)
        boundary = self.c.boundary(self.w.sessions["AG1"], "child")
        self.assertEqual(boundary["task"]["snapshot"][0]["revision"], 1)
        self.assertNotIn("content", encode_safe(boundary))

    def test_exact_candidate_requires_explicit_provisional_conditions(self):
        candidate = self.w.candidate("material")["ref"]
        self.w.op("AG0", "register", id="provisional", assignee="AG1", task_kind="production", scope=["whole"], intended_use="teaching",
                  inputs=[{**candidate, "policy": "exact", "scope": ["whole"], "intended_use": "teaching"}],
                  output={"id": "provisional-output", "type": "ActivitySpec", "requires_ag3_review": False})
        refusal = self.w.op("AG1", "start", expect="rejected", task_id="provisional")
        self.assertEqual(refusal["reasons"], ["explicit_provisional_conditions_required"])

    def test_validation_failure_never_publishes_and_receipts_do_not_prove_semantics(self):
        self.w.register("broken", "material")
        self.w.op("AG2", "start", task_id="broken")
        (self.root / "bad.bin").write_bytes(b"\xff")
        refusal = self.w.op("AG2", "submit", expect="rejected", task_id="broken", path="bad.bin", changed_scope=None)
        self.assertEqual(refusal["reasons"], ["invalid_utf8"])
        self.assertFalse(self.state()["artifacts"])
        self.assertEqual(self.state()["drafts"][0]["state"], "Draft")

    def test_adoption_requires_pointer_intent_and_old_reviews_cannot_cover_new(self):
        first, receipts = self.seed(review=True)
        second = self.w.candidate("material", review=True)["ref"]
        owner = self.w.confirm(second)
        refusal = self.w.adopt(second, [owner, receipts[1]], expect="rejected")
        self.assertEqual(refusal["reasons"], ["receipt_version_mismatch"])
        refusal = self.w.op("AG0", "adopt", expect="rejected", bundle_id="no-intent", members=[{"ref": second, "scope": ["whole"], "intended_use": "teaching", "receipt_ids": [owner]}])
        self.assertEqual(refusal["reasons"], ["explicit_pointer_preconditions_required"])

    def test_scope_use_mismatch_rejected_before_snapshot(self):
        first, _ = self.seed()
        self.w.register("consumer", "child", role="AG1", kind="ActivitySpec", inputs=[{**first, "policy": "adopted", "scope": ["missing"], "intended_use": "teaching"}])
        self.w.op("AG1", "start", expect="rejected", task_id="consumer")

    def test_paused_deleted_and_restricted_views_do_not_read_hidden_bodies(self):
        first, _ = self.seed()
        self.child(first)
        for key, value in (("paused_ids", ["material"]), ("deleted_ids", ["material"]), ("restrictions", [{"scope_ids": ["material"], "intended_uses": ["teaching"]}])):
            self.control[key] = value
            original = self.c.file_info
            self.c.file_info = lambda path: (_ for _ in ()).throw(AssertionError("Hidden content read"))
            try:
                self.assertFalse(self.state()["artifacts"])
                self.assertFalse(self.state()["impacts"])
                self.assertFalse(self.c.events(self.w.sessions["AG0"])["events"][-1:] if key == "deleted_ids" else [])
            finally:
                self.c.file_info = original
                self.control[key] = []

    def test_file_diff_preserves_exact_hashes_and_reports_scope(self):
        first, _ = self.seed()
        second = self.w.candidate("material", changed_scope=["whole"])["ref"]
        difference = self.c.diff(self.w.sessions["AG0"], first, second)
        self.assertNotEqual(difference["old_sha256"], difference["new_sha256"])
        self.assertEqual(difference["changed_scope"], ["whole"])
        self.assertIn("@@", difference["text_diff"])

    def test_bootstrap_is_atomic_explicit_and_preserves_historical_adoption_evidence(self):
        (self.root / "source.md").write_text("Fabricated historical source", encoding="utf-8")
        (self.root / "adoption.md").write_text("Fabricated AG0 formerly adopted source revision 2 for teaching", encoding="utf-8")
        entry = {"id": "source", "revision": 2, "type": "SourceFragment", "scope": ["whole"], "intended_use": "teaching", "path": "source.md", "sha256": sha((self.root / "source.md").read_bytes()),
                 "basis_refs": [], "requires_ag3_review": True, "adopted": True, "adoption_rationale": "Fabricated migration of existing decision, not a fresh review",
                 "adoption_evidence": [{"path": "adoption.md", "sha256": sha((self.root / "adoption.md").read_bytes()), "anchor": "formerly adopted source revision 2"}]}
        missing = deepcopy(entry)
        missing["adoption_evidence"] = []
        self.w.op("AG0", "bootstrap", expect="rejected", entries=[missing])
        self.assertFalse(self.state()["artifacts"])
        self.w.op("AG0", "bootstrap", entries=[entry])
        self.assertEqual(self.state()["artifacts"][0]["state"], "Adopted")
        self.assertTrue(self.state()["artifacts"][0]["historical_adoption"])
        self.assertFalse(self.state()["artifacts"][0]["verified_scope"])
        self.w.op("AG0", "bootstrap", expect="rejected", entries=[entry])

    def test_unknown_candidate_change_warns_transitive_consumers(self):
        first, _ = self.seed()
        self.child(first, name="middle")
        middle = self.w.submit("middle", role="AG1")["ref"]
        self.w.adopt(middle, [self.w.confirm(middle, role="AG1")])
        self.child(middle, name="tail")
        self.w.candidate("material")
        self.assertIn("tail", {i["target_id"] for i in self.state()["impacts"]})

    def test_parallel_branch_scope_follows_actual_base_not_revision_numbers(self):
        first, _ = self.seed(scope=["M1", "M3"])
        self.w.register("branch-a", "material", scope=["M1", "M3"])
        self.w.register("branch-b", "material", scope=["M1", "M3"])
        for name in ("branch-a", "branch-b"):
            self.w.op("AG2", "start", task_id=name)
        second = self.w.submit("branch-a", changed_scope=["M3"])["ref"]
        third = self.w.submit("branch-b", changed_scope=["M1"])["ref"]
        self.assertEqual(self.c.diff(self.w.sessions["AG0"], first, third)["changed_scope"], ["M1"])
        self.assertEqual(self.c.diff(self.w.sessions["AG0"], second, third)["changed_scope"], ["M1", "M3"])

    def test_new_consumer_pins_reconciled_inputs_without_rewriting_older_basis(self):
        first, _ = self.seed()
        self.child(first, name="middle")
        middle = self.w.submit("middle", role="AG1")["ref"]
        second = self.w.candidate("material")["ref"]
        self.w.adopt(second, [self.w.confirm(second)])
        self.w.op("AG1", "recheck", ref=middle, recheck_id="middle-recheck", old_ref=first, new_ref=second,
                  scope=["whole"], intended_use="teaching", rationale="Fabricated source comparison")
        self.w.adopt(middle, [self.w.confirm(middle, role="AG1")])
        self.child(middle, name="tail")
        boundary = self.c.boundary(self.w.sessions["AG1"], "tail")
        self.assertIn(second, [{"id": i["id"], "revision": i["revision"]} for i in boundary["task"]["snapshot"]])
        tail = self.w.submit("tail", role="AG1")["ref"]
        self.w.adopt(tail, [self.w.confirm(tail, role="AG1")])
        original = next(a for a in self.state()["artifacts"] if a["id"] == middle["id"])
        self.assertEqual(original["basis_refs"][0]["revision"], 1)

    def test_event_inbox_is_durable_ack_does_not_notify_itself(self):
        self.seed()
        inbox = self.c.inbox(self.w.sessions["AG0"], "test-host")
        self.assertTrue(inbox["events"])
        self.w.op("AG0", "ack_events", consumer_id="test-host", through_sequence=inbox["next_sequence"])
        self.assertFalse(self.c.inbox(self.w.sessions["AG0"], "test-host")["events"])
        self.assertTrue(self.c.inbox(self.w.sessions["AG1"], "test-host")["events"])
        reopened = TaskArtifactCoordinator(self.root, lambda: deepcopy(self.control))
        self.assertFalse(reopened.inbox(reopened.bind_local_operator("AG0"), "test-host")["events"])

    def test_atomic_file_publish_and_identical_retry_create_one_candidate(self):
        self.w.register("publish", "material")
        self.w.op("AG2", "start", task_id="publish")
        (self.root / "draft.md").write_text("Fabricated complete candidate bytes", encoding="utf-8")
        request = self.w.request(task_id="publish", changed_scope=None)
        first = publish_file(self.c, self.w.sessions["AG2"], source_path="draft.md", version_path="versions/material-v1.md", request=request)
        again = publish_file(self.c, self.w.sessions["AG2"], source_path="draft.md", version_path="versions/material-v1.md", request=request)
        self.assertEqual(first, again)
        self.assertEqual(len(self.state()["artifacts"]), 1)
        (self.root / "draft.md").write_text("Fabricated later edit", encoding="utf-8")
        with self.assertRaisesRegex(GateError, "published_path_content_conflict"):
            publish_file(self.c, self.w.sessions["AG2"], source_path="draft.md", version_path="versions/material-v1.md", request=request)

    def test_hard_exit_after_file_install_reports_orphan_without_adopting_it(self):
        # Real child process against fabricated local business data.
        w = CompleteWorkflow(self.root / "process-workspace")
        w.register("publish", "material")
        w.op("AG2", "start", task_id="publish")
        (w.root / "draft.md").write_text("Fabricated publication fault bytes", encoding="utf-8")
        request = w.request(task_id="publish", changed_scope=None)
        path = w.root / "request.json"
        path.write_text(json.dumps(request), encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SUITE / "scripts/coordinator_complete_fault_worker.py"),
                                 "--workspace", str(w.root), "--role", "AG2", "--request", str(path), "--source-path", "draft.md",
                                 "--version-path", "versions/material-v1.md", "--failpoint", "after_file_install"], capture_output=True, timeout=20,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.assertEqual(result.returncode, 92, result.stderr)
        state = w.coordinator.status(w.sessions["AG0"])
        self.assertFalse(state["artifacts"])
        self.assertFalse(state["adopted_pointers"])
        recovery = w.coordinator.recover(w.sessions["AG0"], scan_roots=["versions"])
        self.assertIn("versions/material-v1.md", recovery["unregistered_files"])
        retried = publish_file(w.coordinator, w.sessions["AG2"], source_path="draft.md", version_path="versions/material-v1.md", request=request)
        self.assertEqual(retried["status"], "committed")

    def test_explicit_upgrade_preserves_old_pointer_and_reserves_existing_task(self):
        root = self.root / "legacy"
        w = Workflow(root, coordinator_class=ReliableCoordinator)
        first = w.candidate("source")["ref"]
        w.adopt(first, [w.confirm(first)])
        w.register("ongoing", "source")
        c = TaskArtifactCoordinator(root)
        session = c.bind_local_operator("AG0")
        self.assertTrue(c.status(session)["complete_upgrade_required"])
        result = c.execute(session, "upgrade", {"operation_id": "upgrade-full", "expected_state_revision": c.status(session)["state_revision"]})
        self.assertEqual(result["status"], "committed")
        self.assertEqual(c.status(session)["adopted_pointers"][0]["revision"], 1)
        self.assertEqual(c.status(session)["drafts"][0]["revision"], 2)

    def test_current_control_cannot_be_imported_as_second_managed_truth(self):
        (self.root / "state").mkdir()
        (self.root / "state/control.md").write_text("Fabricated external control", encoding="utf-8")
        entry = {"id": "wrong", "revision": 1, "type": "SourceFragment", "scope": ["whole"], "intended_use": "teaching", "path": "state/control.md", "sha256": sha((self.root / "state/control.md").read_bytes()), "basis_refs": [], "requires_ag3_review": False, "adopted": False}
        result = self.w.op("AG0", "bootstrap", expect="rejected", entries=[entry])
        self.assertEqual(result["reasons"], ["external_authority_cannot_be_managed_artifact"])

    def test_partial_adoption_keeps_per_scope_states_and_does_not_expand_input(self):
        first = self.w.candidate("material", scope=["M1", "M3"])["ref"]
        owner = self.w.confirm(first, scope=["M1"])
        self.w.adopt(first, [owner], scope=["M1"])
        a = self.state()["artifacts"][0]
        self.assertEqual(a["scope_states"], {"M1": "Adopted", "M3": "Candidate"})
        self.assertEqual(self.state()["summary"][0]["scope"], ["M1"])

    def test_complete_wait_policy_retains_independent_old_input(self):
        first, _ = self.seed()
        self.child(first, name="independent")
        self.w.register("producer", "material")
        self.w.op("AG2", "start", task_id="producer")
        self.w.op("AG0", "register", id="waiter", assignee="AG1", task_kind="production", scope=["whole"], intended_use="teaching",
                  output={"id": "wait-result", "type": "ActivitySpec", "requires_ag3_review": False},
                  inputs=[{"id": "material", "policy": "after_task", "producer_task_id": "producer", "scope": ["whole"], "intended_use": "teaching"}], wait_timeout_ms=300000)
        self.assertEqual(self.w.op("AG1", "start", task_id="waiter")["phase"], "waiting")
        self.assertEqual(self.c.read_snapshot(self.w.sessions["AG1"], "independent")[0]["ref"], first)
        second = self.w.submit("producer")["ref"]
        self.w.adopt(second, [self.w.confirm(second)])
        self.assertEqual(self.w.op("AG1", "start", task_id="waiter")["snapshot"][0]["revision"], 2)

    def test_review_in_progress_warns_about_new_candidate_and_keeps_old_target(self):
        first, _ = self.seed(review=True)
        self.w.op("AG0", "register", id="review-running", assignee="AG3", task_kind="review", scope=["whole"], intended_use="teaching", target_ref=first)
        self.w.op("AG3", "start", task_id="review-running")
        second = self.w.candidate("material", review=True)["ref"]
        warnings = [i for i in self.state()["impacts"] if i["target_id"] == "review-running"]
        self.assertEqual(warnings[0]["severity"], "review_target_warning")
        self.assertEqual(self.c.boundary(self.w.sessions["AG3"], "review-running")["task"]["target_ref"], first)

    def test_shared_contract_fields_are_checked_and_optional_review_is_respected(self):
        self.w.op("AG0", "register", id="native-json", assignee="AG2", task_kind="production", scope=["whole"], intended_use="teaching", inputs=[],
                  output={"id": "native-source", "type": "SourceFragment", "requires_ag3_review": False, "validation_profile": "contract_fields"})
        self.w.op("AG2", "start", task_id="native-json")
        path = self.root / "source.json"
        path.write_text("{}", encoding="utf-8")
        result = self.w.op("AG2", "submit", expect="rejected", task_id="native-json", path="source.json", changed_scope=None)
        self.assertEqual(result["reasons"], ["contract_fields_missing"])
        required = self.c.definition["base_required"] + self.c.definition["objects"]["SourceFragment"]["required"]
        value = {name: None for name in required}
        value.update(type="SourceFragment", id="native-source", revision=1, owner="AG2", schema_version=self.c.definition["protocol_version"], basis_refs=[])
        path.write_text(json.dumps(value), encoding="utf-8")
        target = self.w.op("AG2", "submit", task_id="native-json", path="source.json", changed_scope=None)["ref"]
        owner = self.w.confirm(target)
        self.assertEqual(self.state()["artifacts"][0]["state"], "Verified")
        self.w.adopt(target, [owner])
        self.assertEqual(self.state()["artifacts"][0]["state"], "Adopted")

    def test_percentage_reporting_is_removed_and_legacy_fields_are_not_reported(self):
        self.w.register("explicit", "material")
        self.w.op("AG2", "start", task_id="explicit")
        result = self.w.op("AG0", "progress", expect="rejected", task_id="explicit", percent=100, note="Fabricated other role claim")
        self.assertEqual(result["reasons"], ["unknown_action"])
        with self.c.connect() as db:
            task = self.c.get(db, "tasks", "explicit")
            task["progress"] = {"percent": 100, "note": "Fabricated legacy field"}
            db.execute("UPDATE tasks SET body=? WHERE id=?", (json.dumps(task), task["id"]))
        state = self.state()
        self.assertNotIn("progress", next(t for t in state["tasks"] if t["id"] == "explicit"))
        self.assertNotIn("percent", json.dumps(state))

    def test_work_status_and_actual_artifact_review_receipts_are_separate_from_adoption(self):
        self.w.register("status-task", "material", review=True)
        self.w.op("AG2", "start", task_id="status-task")
        task = next(t for t in self.state()["tasks"] if t["id"] == "status-task")
        self.assertEqual(task["work_status"], "running")
        self.assertIsNone(task["output_receipt"])
        target = self.w.submit("status-task")["ref"]
        task = next(t for t in self.state()["tasks"] if t["id"] == "status-task")
        self.assertEqual(task["work_status"], "submitted")
        self.assertEqual(task["output_receipt"]["ref"], target)
        self.assertEqual(task["output_receipt"]["adoption_state"], "Candidate")
        self.assertTrue(task["output_receipt"]["path"])
        self.assertTrue(task["output_receipt"]["sha256"])
        self.assertTrue(task["output_receipt"]["operation_id"])
        reviewed = self.w.review(target)
        review_task = next(t for t in self.state()["tasks"] if t.get("receipt_id") == reviewed)
        self.assertEqual(review_task["output_receipt"]["receipt_id"], reviewed)
        self.assertEqual(review_task["output_receipt"]["target_ref"], target)
        self.assertIn("status-task", self.c.brief(self.w.sessions["AG0"]))

    def test_waiting_and_failed_tasks_report_blocked_with_actual_reason(self):
        self.w.register("producer", "material")
        self.w.op("AG0", "register", id="consumer", assignee="AG1", task_kind="production", scope=["whole"], intended_use="teaching", wait_timeout_ms=300000,
                  inputs=[{"id": "material", "policy": "after_task", "producer_task_id": "producer", "scope": ["whole"], "intended_use": "teaching"}],
                  output={"id": "consumer-result", "type": "ActivitySpec", "requires_ag3_review": False})
        self.w.op("AG1", "start", task_id="consumer")
        waiting = next(t for t in self.state()["tasks"] if t["id"] == "consumer")
        self.assertEqual(waiting["phase"], "waiting")
        self.assertEqual(waiting["work_status"], "blocked")
        self.assertEqual(waiting["blocked_reason"], "waiting_for_dependency")
        self.assertIsNone(waiting["output_receipt"])
        self.w.op("AG2", "finish", task_id="producer", phase="failed", reason="Fabricated producer failure")
        blocked = next(t for t in self.state()["tasks"] if t["id"] == "consumer")
        self.assertEqual(blocked["work_status"], "blocked")
        self.assertEqual(blocked["blocked_reason"], "upstream_failed")

    def test_formal_current_reads_adopted_version_and_rejects_stale_basis(self):
        first, _ = self.seed()
        second = self.w.candidate("material")["ref"]
        resolved = self.c.resolve(self.w.sessions["AG1"], "material", "teaching", ["whole"])
        self.assertEqual(resolved["ref"], first)
        self.assertIsInstance(resolved["content"], bytes)
        self.child(first)
        child = self.w.submit("child", role="AG1")["ref"]
        self.w.adopt(child, [self.w.confirm(child, role="AG1")])
        self.w.adopt(second, [self.w.confirm(second)])
        with self.assertRaisesRegex(GateError, "adopted_input_requires_recheck"):
            self.c.resolve(self.w.sessions["AG0"], child["id"], "teaching", ["whole"])

    def test_superseded_history_does_not_appear_as_pending_downstream_work(self):
        upstream = self.w.candidate("upstream")["ref"]
        self.w.adopt(upstream, [self.w.confirm(upstream)])
        first = self.w.candidate("material", inputs=[{**upstream, "policy": "adopted", "scope": ["whole"], "intended_use": "teaching"}])["ref"]
        self.w.adopt(first, [self.w.confirm(first)])
        second = self.w.candidate("material")["ref"]
        self.w.adopt(second, [self.w.confirm(second)])
        changed = self.w.candidate("upstream")["ref"]
        self.w.adopt(changed, [self.w.confirm(changed)])
        self.assertFalse(self.state()["impacts"])

    def test_receipt_query_returns_exact_target_scope_and_scope_inheritance(self):
        first, receipts = self.seed(scope=["M1", "M3"], review=True)
        second = self.w.candidate("material", scope=["M1", "M3"], review=True, changed_scope=["M3"])["ref"]
        reviewed = self.w.review(second, scope=["M1", "M3"], base=receipts[1], checked=["M3"], inherited=["M1"])
        query = self.c.receipt(self.w.sessions["AG0"], reviewed)
        self.assertEqual(query["receipt"]["target_ref"], second)
        self.assertEqual(query["receipt"]["directly_checked_scope"], ["M3"])
        self.assertEqual(query["receipt"]["inherited_scope"], ["M1"])
        self.assertTrue(query["currently_applicable_to_exact_target"])
        self.assertTrue(self.state()["receipts"])

    def test_registered_unstarted_dependencies_warn_without_silently_pin_or_wait(self):
        first, _ = self.seed()
        self.w.register("unstarted", "unstarted-output", role="AG1", kind="ActivitySpec",
                        inputs=[{**first, "policy": "adopted", "scope": ["whole"], "intended_use": "teaching"}])
        self.w.candidate("material")
        warnings = [i for i in self.state()["impacts"] if i["target_id"] == "unstarted"]
        self.assertEqual(warnings[0]["severity"], "candidate_warning")
        task = next(t for t in self.state()["tasks"] if t["id"] == "unstarted")
        self.assertEqual(task["phase"], "registered")
        self.assertFalse(task["snapshot"])
        self.assertTrue(self.state()["dependency_edges"])

    def test_actual_parallel_complete_candidates_keep_reserved_versions_and_old_pointer(self):
        first, _ = self.seed()
        self.w.register("parallel-a", "material")
        self.w.register("parallel-b", "material")
        for name in ("parallel-a", "parallel-b"):
            self.w.op("AG2", "start", task_id=name)
        revision = self.state()["state_revision"]
        requests, processes = [], []
        for name in ("parallel-a", "parallel-b"):
            artifact_path = name + ".md"
            (self.root / artifact_path).write_text("Fabricated real-process candidate " + name, encoding="utf-8")
            request = {"operation_id": "submit-" + name, "expected_state_revision": revision, "task_id": name, "path": artifact_path, "changed_scope": None}
            path = self.root / (name + ".json")
            path.write_text(json.dumps(request), encoding="utf-8")
            requests.append(request)
            processes.append(subprocess.Popen([sys.executable, "-B", "-X", "utf8", str(SUITE / "scripts/coordinator_complete_fault_worker.py"),
                                               "--workspace", str(self.root), "--role", "AG2", "--request", str(path)],
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)))
        responses = []
        for process in processes:
            out, error = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 0, error)
            responses.append(json.loads(out))
        self.assertEqual(sorted(r["status"] for r in responses), ["committed", "conflict"])
        loser = next(i for i, r in enumerate(responses) if r["status"] == "conflict")
        request = {**requests[loser], "expected_state_revision": self.state()["state_revision"]}
        self.assertEqual(self.c.execute(self.w.sessions["AG2"], "submit", request)["status"], "committed")
        self.assertEqual([a["revision"] for a in self.state()["artifacts"]], [1, 2, 3])
        self.assertEqual(self.state()["adopted_pointers"][0]["revision"], first["revision"])


def encode_safe(value):
    return json.dumps(value, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
