"""Task, version, professional receipt and adoption boundaries, using fabricated files."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from demo_coordinator_workspace import Workflow, run_scenario
from coordinator.workspace import Coordinator, FileControlGate, GateError, Session, sha


class CoordinatorWorkspaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tac-workspace-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.control = {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []}
        self.w = Workflow(self.root, lambda: deepcopy(self.control))
        self.c = self.w.coordinator

    def pointers(self):
        return self.c.status(self.w.sessions["AG0"])["adopted_pointers"]

    def seed(self, name="source", scope=None, review=False):
        target = self.w.candidate(name, scope=scope, review=review)["ref"]
        owner = self.w.confirm(target, scope=scope)
        receipts = [owner]
        if review:
            receipts.append(self.w.review(target, scope=scope))
        self.w.adopt(target, receipts, scope=scope)
        return target, receipts

    def consumer(self, source, *, scope=None, task_id="consumer"):
        scope = scope or ["whole"]
        self.w.register(task_id, task_id + "-output", role="AG1", kind="ActivitySpec", scope=scope,
                        inputs=[{"id": source["id"], "policy": "adopted", "scope": scope, "intended_use": "teaching"}])
        self.w.op("AG1", "start", task_id=task_id)
        return task_id

    def test_full_demo_covers_old_review_refusal_supplement_and_local_recheck(self):
        scenario = run_scenario(self.root / "other")
        self.assertEqual(scenario["results"]["old_review_rejected"], ["receipt_version_mismatch"])
        self.assertEqual(scenario["results"]["pinned_snapshots_after_update"]["M1"], [{"id": "material", "revision": 1}])
        self.assertEqual(scenario["results"]["unaffected_input_issues"], [])
        self.assertEqual(scenario["results"]["affected_input_issues"][0]["scope"], "M3")

    def test_draft_and_candidate_leave_old_adopted_pointer_available(self):
        first, _ = self.seed()
        old = self.pointers()
        self.w.register("draft", "source")
        self.w.op("AG2", "start", task_id="draft")
        self.consumer(first)
        second = self.w.submit("draft")["ref"]
        self.assertEqual(second["revision"], 2)
        self.assertEqual(self.pointers(), old)

    def test_task_snapshot_never_silently_tracks_new_pointer(self):
        first, _ = self.seed()
        task_id = self.consumer(first)
        second = self.w.candidate("source")["ref"]
        owner = self.w.confirm(second)
        self.w.adopt(second, [owner])
        snapshot = self.c.read_snapshot(self.w.sessions["AG1"], task_id)
        self.assertEqual(snapshot[0]["ref"], first)
        self.assertIn(b"Fabricated", snapshot[0]["content"])
        result = self.w.submit(task_id, role="AG1")
        self.assertEqual(result["input_issues"][0]["code"], "upstream_changed")

    def test_unknown_change_scope_conservatively_marks_downstream(self):
        first, _ = self.seed(scope=["M1", "M3"])
        task = self.consumer(first, scope=["M1"])
        second = self.w.candidate("source", scope=["M1", "M3"])["ref"]
        owner = self.w.confirm(second, scope=["M1", "M3"])
        self.w.adopt(second, [owner], scope=["M1", "M3"])
        result = self.w.submit(task, role="AG1")
        self.assertTrue(result["input_issues"])

    def test_unrelated_declared_scope_can_continue_without_recheck(self):
        first, _ = self.seed(scope=["M1", "M3"])
        task = self.consumer(first, scope=["M1"])
        second = self.w.candidate("source", scope=["M1", "M3"], changed_scope=["M3"])["ref"]
        owner = self.w.confirm(second, scope=["M1", "M3"])
        self.w.adopt(second, [owner], scope=["M1", "M3"])
        self.assertEqual(self.w.submit(task, role="AG1")["input_issues"], [])

    def test_exact_unadopted_input_is_provisional_not_default_ready(self):
        first = self.w.candidate("source")["ref"]
        self.w.register("provisional", "activity", role="AG1", kind="ActivitySpec",
                        inputs=[{**first, "policy": "exact", "scope": ["whole"], "intended_use": "teaching"}])
        self.w.op("AG1", "start", task_id="provisional")
        result = self.w.submit("provisional", role="AG1")
        self.assertEqual(result["input_issues"][0]["code"], "input_not_adopted")
        refusal = self.w.op("AG1", "confirm", expect="rejected", ref=result["ref"], receipt_id="reject-provisional",
                            scope=["whole"], intended_use="teaching", outcome="supported", rationale="Fabricated")
        self.assertEqual(refusal["reasons"], ["input_recheck_required"])

    def test_old_review_cannot_cover_new_content_even_with_same_scopes(self):
        first, receipts = self.seed(review=True)
        second = self.w.candidate("source", review=True)["ref"]
        owner = self.w.confirm(second)
        before = self.pointers()
        result = self.w.adopt(second, [owner, receipts[1]], expect="rejected")
        self.assertEqual(result["reasons"], ["receipt_version_mismatch"])
        self.assertEqual(self.pointers(), before)

    def test_missing_ag3_review_is_blocked_but_optional_review_not_required(self):
        target = self.w.candidate("reviewed", review=True)["ref"]
        owner = self.w.confirm(target)
        result = self.w.adopt(target, [owner], expect="rejected")
        self.assertEqual(result["reasons"], ["ag3_review_required"])
        self.seed("ordinary", review=False)

    def test_program_does_not_adopt_without_owner_confirmation(self):
        target = self.w.candidate("material", review=True)["ref"]
        review = self.w.review(target)
        result = self.w.adopt(target, [review], expect="rejected")
        self.assertEqual(result["reasons"], ["professional_confirmation_required"])

    def test_receipt_for_wrong_use_is_not_transferable(self):
        target = self.w.candidate("source")["ref"]
        result = self.w.op("AG2", "confirm", expect="rejected", ref=target, receipt_id="wrong-use",
                           intended_use="assessment", scope=["whole"], outcome="supported", rationale="Fabricated")
        self.assertEqual(result["reasons"], ["receipt_scope_expansion"])

    def test_partial_professional_conclusion_is_not_full_support(self):
        target = self.w.candidate("source")["ref"]
        self.w.op("AG2", "confirm", ref=target, receipt_id="partial", intended_use="teaching", scope=["whole"],
                  outcome="partial", rationale="Fabricated partial check")
        result = self.w.adopt(target, ["partial"], expect="rejected")
        self.assertEqual(result["reasons"], ["conflicting_professional_receipts"])

    def test_review_scope_does_not_expand_the_registered_task(self):
        target = self.w.candidate("source", scope=["M1", "M3"], review=True)["ref"]
        self.w.op("AG0", "register", id="review-task", assignee="AG3", task_kind="review", scope=["M1"],
                  intended_use="teaching", target_ref=target)
        self.w.op("AG3", "start", task_id="review-task")
        result = self.w.op("AG3", "review", expect="rejected", task_id="review-task", receipt_id="expanded",
                           scope=["M1", "M3"], intended_use="teaching", outcome="supported", rationale="Fabricated")
        self.assertEqual(result["reasons"], ["review_scope_expansion"])

    def test_review_target_cannot_change_while_working(self):
        first = self.w.candidate("source", review=True)["ref"]
        self.w.op("AG0", "register", id="review-task", assignee="AG3", task_kind="review", scope=["whole"],
                  intended_use="teaching", target_ref=first)
        self.w.op("AG3", "start", task_id="review-task")
        second = self.w.candidate("source", review=True)["ref"]
        result = self.w.op("AG3", "review", expect="rejected", task_id="review-task", ref=second,
                           receipt_id="wrong-target", scope=["whole"], intended_use="teaching", outcome="supported", rationale="Fabricated")
        self.assertEqual(result["reasons"], ["review_target_changed"])

    def test_supplement_keeps_direct_and_inherited_checks_separate(self):
        first, receipts = self.seed(scope=["M1", "M3"], review=True)
        second = self.w.candidate("source", scope=["M1", "M3"], review=True, changed_scope=["M3"])["ref"]
        review_id = self.w.review(second, scope=["M1", "M3"], base=receipts[1], checked=["M3"], inherited=["M1"])
        with self.c.connect() as db:
            receipt = self.c.get(db, "receipts", review_id)
        self.assertEqual(receipt["directly_checked_scope"], ["M3"])
        self.assertEqual(receipt["inherited_scope"], ["M1"])
        self.assertEqual(receipt["target_ref"], second)

    def test_changed_upstream_blocks_previously_confirmed_downstream(self):
        first, _ = self.seed()
        task = self.consumer(first)
        child = self.w.submit(task, role="AG1")["ref"]
        owner = self.w.confirm(child, role="AG1")
        second = self.w.candidate("source")["ref"]
        new_owner = self.w.confirm(second)
        self.w.adopt(second, [new_owner])
        result = self.w.adopt(child, [owner], expect="rejected")
        self.assertEqual(result["reasons"], ["input_recheck_required"])

    def test_recheck_bound_to_exact_new_version_and_stales_previous_receipts(self):
        first, _ = self.seed()
        task = self.consumer(first)
        child = self.w.submit(task, role="AG1")["ref"]
        old_owner = self.w.confirm(child, role="AG1")
        second = self.w.candidate("source")["ref"]
        second_owner = self.w.confirm(second)
        self.w.adopt(second, [second_owner])
        self.w.op("AG1", "recheck", ref=child, recheck_id="recheck-2", old_ref=first, new_ref=second,
                  scope=["whole"], intended_use="teaching", rationale="Fabricated local compatibility")
        refusal = self.w.adopt(child, [old_owner], expect="rejected")
        self.assertEqual(refusal["reasons"], ["receipt_basis_or_use_mismatch"])
        current_owner = self.w.confirm(child, role="AG1")
        self.w.adopt(child, [current_owner])
        third = self.w.candidate("source")["ref"]
        third_owner = self.w.confirm(third)
        self.w.adopt(third, [third_owner])
        refusal = self.w.adopt(child, [current_owner], expect="rejected")
        self.assertEqual(refusal["reasons"], ["input_recheck_required"])

    def test_transitive_dependency_change_is_detected(self):
        first, _ = self.seed()
        middle_task = self.consumer(first, task_id="middle")
        middle = self.w.submit(middle_task, role="AG1")["ref"]
        middle_owner = self.w.confirm(middle, role="AG1")
        self.w.adopt(middle, [middle_owner])
        tail_task = self.consumer(middle, task_id="tail")
        changed = self.w.candidate("source")["ref"]
        changed_owner = self.w.confirm(changed)
        self.w.adopt(changed, [changed_owner])
        tail = self.w.submit(tail_task, role="AG1")
        self.assertTrue(any(i.get("old_ref", {}).get("id") == "source" for i in tail["input_issues"]))

    def test_failed_bundle_does_not_publish_any_member(self):
        target1 = self.w.candidate("one")["ref"]
        owner1 = self.w.confirm(target1)
        target2 = self.w.candidate("two", review=True)["ref"]
        owner2 = self.w.confirm(target2)
        before = self.pointers()
        result = self.w.op("AG0", "adopt", expect="rejected", bundle_id="bad-bundle", members=[
            {"ref": target1, "scope": ["whole"], "intended_use": "teaching", "receipt_ids": [owner1]},
            {"ref": target2, "scope": ["whole"], "intended_use": "teaching", "receipt_ids": [owner2]}])
        self.assertEqual(result["reasons"], ["ag3_review_required"])
        self.assertEqual(self.pointers(), before)

    def test_interdependent_candidates_can_be_adopted_in_one_validated_bundle(self):
        source = self.w.candidate("source")["ref"]
        owner_source = self.w.confirm(source)
        self.w.register("child", "activity", role="AG1", kind="ActivitySpec",
                        inputs=[{**source, "policy": "exact", "scope": ["whole"], "intended_use": "teaching"}])
        self.w.op("AG1", "start", task_id="child")
        child = self.w.submit("child", role="AG1")["ref"]
        self.w.op("AG1", "confirm", ref=child, receipt_id="conditional", intended_use="teaching", scope=["whole"],
                  outcome="supported", rationale="Fabricated confirmation conditional on the pinned input", allow_provisional=True)
        self.w.op("AG0", "adopt", bundle_id="both", members=[
            {"ref": child, "scope": ["whole"], "intended_use": "teaching", "receipt_ids": ["conditional"]},
            {"ref": source, "scope": ["whole"], "intended_use": "teaching", "receipt_ids": [owner_source]}])
        self.assertEqual(len(self.pointers()), 2)

    def test_partial_adoption_is_scoped_and_does_not_cover_other_sections(self):
        target = self.w.candidate("source", scope=["M1", "M3"])["ref"]
        owner = self.w.confirm(target, scope=["M1"])
        self.w.adopt(target, [owner], scope=["M1"])
        self.assertEqual([p["scope"] for p in self.pointers()], ["M1"])
        artifact = self.c.status(self.w.sessions["AG0"])["artifacts"][0]
        self.assertEqual(artifact["adoption"]["status"], "partially_adopted")

    def test_ag0_cannot_impersonate_owner_confirmation(self):
        target = self.w.candidate("source")["ref"]
        result = self.w.op("AG0", "confirm", expect="rejected", ref=target, receipt_id="impersonated",
                           scope=["whole"], intended_use="teaching", outcome="supported", rationale="Fabricated")
        self.assertEqual(result["reasons"], ["professional_owner_required"])

    def test_payload_identity_and_unbound_session_are_rejected(self):
        result = self.w.op("AG0", "finish", expect="rejected", actor="AG2", task_id="absent", phase="cancelled", reason="Fabricated")
        self.assertEqual(result["reasons"], ["caller_identity_not_request_data"])
        result = self.c.execute(Session("AG0", object()), "finish", self.w.request(task_id="absent"))
        self.assertEqual(result["reasons"], ["unbound_session"])

    def test_cas_conflict_preserves_state_and_task(self):
        self.w.register("task", "output")
        request = self.w.request(task_id="task")
        self.w.register("other", "other-output")
        result = self.c.execute(self.w.sessions["AG2"], "start", request)
        self.assertEqual(result["status"], "conflict")
        task = next(t for t in self.c.status(self.w.sessions["AG0"])["tasks"] if t["id"] == "task")
        self.assertEqual(task["phase"], "registered")

    def test_successful_retry_is_idempotent_and_changed_payload_is_rejected(self):
        self.w.register("task", "output")
        request = self.w.request(task_id="task")
        result = self.c.execute(self.w.sessions["AG2"], "start", request)
        revision = result["state_revision"]
        self.assertEqual(self.c.execute(self.w.sessions["AG2"], "start", request), result)
        self.assertEqual(self.c.status(self.w.sessions["AG0"])["state_revision"], revision)
        altered = {**request, "task_id": "task", "extra": "changed"}
        self.assertEqual(self.c.execute(self.w.sessions["AG2"], "start", altered)["reasons"], ["operation_id_reused"])

    def test_pause_restriction_and_deletion_gate_idempotent_retries(self):
        self.w.register("task", "output")
        request = self.w.request(task_id="task")
        self.assertEqual(self.c.execute(self.w.sessions["AG2"], "start", request)["status"], "committed")
        self.control["paused_ids"] = ["output"]
        self.assertEqual(self.c.execute(self.w.sessions["AG2"], "start", request)["reasons"], ["paused_scope"])
        self.control["paused_ids"] = []
        self.control["restrictions"] = [{"scope_ids": ["output"], "intended_uses": ["teaching"]}]
        self.assertEqual(self.c.execute(self.w.sessions["AG2"], "start", request)["reasons"], ["restricted_use"])
        self.control["restrictions"] = []
        self.control["deleted_ids"] = ["output"]
        self.assertEqual(self.c.execute(self.w.sessions["AG2"], "start", request)["reasons"], ["deleted_scope"])

    def test_tampered_file_blocks_snapshot_review_and_adoption(self):
        target, receipts = self.seed()
        task = self.consumer(target)
        artifact = self.c.status(self.w.sessions["AG0"])["artifacts"][0]
        (self.root / artifact["path"]).write_text("Tampered", encoding="utf-8")
        with self.assertRaisesRegex(GateError, "artifact_fingerprint_changed"):
            self.c.read_snapshot(self.w.sessions["AG1"], task)
        result = self.w.adopt(target, receipts, expect="rejected")
        self.assertEqual(result["reasons"], ["artifact_fingerprint_changed"])

    def test_original_path_cannot_be_reused_for_new_version(self):
        target, _ = self.seed()
        artifact = self.c.status(self.w.sessions["AG0"])["artifacts"][0]
        self.w.register("new-task", "source")
        self.w.op("AG2", "start", task_id="new-task")
        before = self.c.status(self.w.sessions["AG0"])
        self.w.op("AG2", "submit", expect="not_saved", task_id="new-task", path=artifact["path"], changed_scope=None)
        self.assertEqual(self.c.status(self.w.sessions["AG0"]), before)

    def test_stopping_failed_task_does_not_drop_previous_adoption(self):
        self.seed()
        before = self.pointers()
        self.w.register("failed-task", "source")
        self.w.op("AG2", "start", task_id="failed-task")
        self.w.op("AG2", "finish", task_id="failed-task", phase="failed", reason="Fabricated execution failure")
        self.assertEqual(self.pointers(), before)

    def test_external_control_projection_invalidates_on_source_change(self):
        root = self.root / "real-mode"
        root.mkdir()
        source = root / "control.md"
        source.write_text("Fabricated source used to test real-mode boundary only", encoding="utf-8")
        projection = root / "projection.json"
        value = {**self.control, "source_refs": [{"path": "control.md", "sha256": sha(source.read_bytes())}]}
        projection.write_text(json.dumps(value), encoding="utf-8")
        c = Coordinator(root, FileControlGate(root, projection))
        c.initialize(evidence_kind="real_file_metadata")
        source.write_text("Changed controls", encoding="utf-8")
        with self.assertRaisesRegex(GateError, "control_projection_stale"):
            c.status(c.bind_local_operator("AG0"))

    def test_real_mode_requires_explicit_external_control_source(self):
        root = self.root / "unbound-real"
        with self.assertRaisesRegex(GateError, "external_control_gate_required"):
            Coordinator(root).initialize(evidence_kind="real_file_metadata")
        self.assertFalse((root / ".coordinator").exists())

    def test_deleted_inputs_are_rejected_before_any_body_read(self):
        target, _ = self.seed()
        task = self.consumer(target)
        self.control["deleted_ids"] = [target["id"]]
        original = self.c.file_info
        self.c.file_info = lambda path: (_ for _ in ()).throw(AssertionError("Deleted body read"))
        try:
            with self.assertRaisesRegex(GateError, "deleted_scope"):
                self.c.read_snapshot(self.w.sessions["AG1"], task)
            result = self.c.execute(self.w.sessions["AG1"], "submit", self.w.request(task_id=task, path="never-read.txt"))
            self.assertEqual(result["reasons"], ["deleted_scope"])
        finally:
            self.c.file_info = original

    def test_contradictory_receipts_require_explicit_professional_resolution(self):
        target = self.w.candidate("source")["ref"]
        positive = self.w.confirm(target)
        self.w.op("AG2", "confirm", ref=target, receipt_id="negative", intended_use="teaching", scope=["whole"],
                  outcome="rejected", rationale="Fabricated later discovered defect")
        refusal = self.w.adopt(target, [positive], expect="rejected")
        self.assertEqual(refusal["reasons"], ["conflicting_professional_receipts"])
        self.w.op("AG2", "confirm", ref=target, receipt_id="resolution", intended_use="teaching", scope=["whole"],
                  outcome="supported", rationale="Fabricated explicit resolution of the negative opinion", supersedes_receipt_ids=["negative"])
        self.w.adopt(target, ["resolution"])

    def test_review_snapshot_includes_current_sources_of_local_input_recheck(self):
        first, _ = self.seed()
        self.w.register("child", "child-output", role="AG1", kind="ActivitySpec", review=True,
                        inputs=[{**first, "policy": "adopted", "scope": ["whole"], "intended_use": "teaching"}])
        self.w.op("AG1", "start", task_id="child")
        child = self.w.submit("child", role="AG1")["ref"]
        second = self.w.candidate("source")["ref"]
        owner = self.w.confirm(second)
        self.w.adopt(second, [owner])
        self.w.op("AG1", "recheck", ref=child, recheck_id="compatible-update", old_ref=first, new_ref=second,
                  scope=["whole"], intended_use="teaching", rationale="Fabricated compatibility")
        self.w.op("AG0", "register", id="review-rechecked", assignee="AG3", task_kind="review", scope=["whole"],
                  intended_use="teaching", target_ref=child)
        self.w.op("AG3", "start", task_id="review-rechecked")
        refs = [item["ref"] for item in self.c.read_snapshot(self.w.sessions["AG3"], "review-rechecked")]
        self.assertIn(first, refs)
        self.assertIn(second, refs)

    def test_rechecked_new_sources_keep_their_transitive_dependency_constraints(self):
        x1, _ = self.seed("external")
        first, _ = self.seed("source")
        child_task = self.consumer(first)
        child = self.w.submit(child_task, role="AG1")["ref"]
        second = self.w.candidate("source", inputs=[{**x1, "policy": "adopted", "scope": ["whole"], "intended_use": "teaching"}])["ref"]
        owner2 = self.w.confirm(second)
        self.w.adopt(second, [owner2])
        self.w.op("AG1", "recheck", ref=child, recheck_id="new-source", old_ref=first, new_ref=second,
                  scope=["whole"], intended_use="teaching", rationale="Fabricated compatibility")
        child_owner = self.w.confirm(child, role="AG1")
        x2 = self.w.candidate("external")["ref"]
        owner_x2 = self.w.confirm(x2)
        self.w.adopt(x2, [owner_x2])
        refusal = self.w.adopt(child, [child_owner], expect="rejected")
        self.assertEqual(refusal["reasons"], ["input_recheck_required"])

    def test_use_restriction_on_transitive_new_source_precedes_body_read(self):
        x1, _ = self.seed("external")
        first, _ = self.seed("source")
        child_task = self.consumer(first)
        child = self.w.submit(child_task, role="AG1")["ref"]
        second = self.w.candidate("source", inputs=[{**x1, "policy": "adopted", "scope": ["whole"], "intended_use": "teaching"}])["ref"]
        owner2 = self.w.confirm(second)
        self.w.adopt(second, [owner2])
        self.control["deleted_ids"] = ["external"]
        original = self.c.file_info
        self.c.file_info = lambda path: (_ for _ in ()).throw(AssertionError("Body read before deletion gate"))
        try:
            refusal = self.w.adopt(child, [], expect="rejected")
            self.assertEqual(refusal["reasons"], ["deleted_scope"])
            with self.assertRaisesRegex(GateError, "deleted_scope"):
                self.c.read_snapshot(self.w.sessions["AG1"], child_task)
        finally:
            self.c.file_info = original

    def test_negative_professional_receipt_restricts_existing_snapshot_use(self):
        first, _ = self.seed()
        task = self.consumer(first)
        self.w.op("AG2", "confirm", ref=first, receipt_id="withdrawal", intended_use="teaching", scope=["whole"],
                  outcome="rejected", rationale="Fabricated withdrawn content qualification")
        with self.assertRaisesRegex(GateError, "conflicting_professional_receipts"):
            self.c.read_snapshot(self.w.sessions["AG1"], task)
        self.w.op("AG2", "confirm", ref=first, receipt_id="restoration", intended_use="teaching", scope=["whole"],
                  outcome="supported", rationale="Fabricated explicit restoration", supersedes_receipt_ids=["withdrawal"])
        self.assertEqual(self.c.read_snapshot(self.w.sessions["AG1"], task)[0]["ref"], first)


if __name__ == "__main__":
    unittest.main(verbosity=2)
