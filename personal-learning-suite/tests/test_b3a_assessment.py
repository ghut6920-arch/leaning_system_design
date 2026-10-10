"""Independent B3a behavior checks on isolated, artificial evidence records.

Professional operation findings are inputs, not inferred by these tests or by
the service. Passing establishes the finite contract slice, never answer truth,
real identity, learning efficacy, or a bound multi-agent teaching system.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from runtime.learning_assessment import AssessmentService, VERSION, fact, ref
from runtime.learning_store import LearningStore
from test_b2b_materials import fixture as material_fixture


def objects_by_id(context):
    return {obj["id"]: obj for obj in context["objects"]}


def fixture():
    """Extend the B2b fixture in memory; never rewrite earlier batch files."""
    snapshot, artifacts, _material, _context = material_fixture()
    snapshot["fixture_id"] = "B3a-synthetic-assessment"
    snapshot["description"] = "人工虚构原答、操作评分声明和授权；仅供隔离行为验收。"
    objects = objects_by_id(snapshot)
    for grant in (obj for obj in snapshot["objects"] if obj["type"] == "AuthorizationGrant"):
        grant["validity"] = fact("known", value={"active": True})
    conclusions = ["local-supported", "local-not-met", "local-unknown", "local-conflicting", "local-diagnostic", "full-chain"]
    for identifier in ("FIX-scoring-grant", "FIX-evidence-grant"):
        objects[identifier]["permitted_conclusions"] = list(conclusions)
    objects["FIX-evidence-grant"]["criterion_refs"] = [
        {"id": "FIX-goal", "revision": 1, "locator": "requirements/infer-Q"},
        {"id": "FIX-goal", "revision": 1, "locator": "requirements/complete-chain"},
    ]
    # Explicit source declarations remain B2b metadata, not proof of truth.
    for activity_id in ("FIX-activity", "FIX-parent-activity"):
        activity = objects[activity_id]
        activity["task_qualification"] = fact("known", value={
            "target_operations": list(activity["learner_operations"]),
            "prerequisite_fit": fact("known", value=True),
            "not_substituted": fact("known", value=True),
            "reference_scorable": fact("known", value=True),
            "evidence_conditions": fact("known", value=True),
        })
    artifacts["b3a-responses.md"] = (
        "# B3a 人工虚构原答\n"
        "OUTSIDE-B3A-BEFORE：这行不属于选定原答。\n"
        "## B3A-INITIAL-ANCHOR\n"
        "FIX-B3A-ORIGINAL：由给定 P 与 P→Q 连接得到 Q；这是人工原答，不是真实学习证据。\n"
        "OUTSIDE-B3A-MIDDLE：本行位于两个响应点之间。\n"
        "## B3A-REVISION-ANCHOR\n"
        "FIX-B3A-REVISION：帮助后保留同一任务的连接理由；不新增独立样本。\n"
        "OUTSIDE-B3A-AFTER：这行不属于选定修订。\n"
    )
    event = objects["FIX-event"]
    event["original_response"] = {
        "path": "b3a-responses.md", "locator": "B3A-INITIAL-ANCHOR", "revision": 1,
        "origin": "synthetic_fixture", "start_line": 3, "end_line": 4,
    }
    event["revisions"] = [{
        "path": "b3a-responses.md", "locator": "B3A-REVISION-ANCHOR", "revision": 1,
        "origin": "synthetic_fixture", "start_line": 6, "end_line": 7, "sequence": 3,
    }]
    event["timeline_completeness"] = fact("known", value=True)
    # This positive fixture explicitly records the resources allowed by its goal;
    # the B0 fixture's earlier prose descriptions are not treated as synonyms.
    event["actual_resources"] = fact("known", value=list(objects["FIX-goal"]["allowed_resources"]))
    event["timeline"][0]["content"] = "人工原答保留条件连接；评分仍由专业声明提供。"
    legacy = objects["FIX-judgment"]
    legacy["conditions"] = {
        "purpose": "assisted", "response_points": [{"event_ref": ref(event), "sequence": 3}],
        "operation_findings": [{"operation": "connect-P-to-Q", "support": "supported", "rationale": "人工声明帮助后可使用连接。"}],
    }
    legacy["conclusion"] = "local-supported"
    judgment = copy.deepcopy(legacy)
    judgment.update(id="FIX-b3a-judgment", owner="AG3", decision_type="professional_review",
                    authorization_ref=ref(objects["FIX-evidence-grant"]), intended_uses=["independent_check"],
                    conditions={"purpose": "independent", "response_points": [{"event_ref": ref(event), "sequence": 1}],
                                "operation_findings": [{"operation": "connect-P-to-Q", "support": "supported", "rationale": "人工专业方声明当前原答调用条件连接；程序不判断答案真伪。"}]},
                    rationale="回查同一原答、操作声明、实际帮助顺序与当前判据。",
                    unsupported_scope=["父任务完整链", "延迟迁移", "真实学习效果"],
                    adoption={"status": "candidate", "by": "AG3", "scope": "人工判断候选", "basis_refs": [],
                              "limitations": ["仅隔离夹具；检查不自动采用。"], "time": fact("not_executed", "无真实采用。")})
    judgment["basis_refs"] += [ref(objects["FIX-material"]), ref(objects["FIX-activity"])]
    note = copy.deepcopy(objects["FIX-diagnostic"])
    note.update(id="FIX-b3a-diagnostic", goal_refs=[{"id": "FIX-goal", "revision": 1, "locator": "requirements/infer-Q"}],
                decision_question="是否需要额外的连接观察才会改变当前安排？",
                alternatives=["可能只是表达省略", "可能尚未能自主连接"],
                counterevidence=["现有合法原答足够时直接复用"],
                next_observation=fact("not_required", "现有原答足以返回当前有限决定，不追加观察。"),
                stop_condition="原答足够，或新观察不能改变安排，即停止。",
                stop_reason="人工原答够用，不追加检查。", reopen_condition="出现会改变安排的合法反证。")
    context = {"intended_use": "independent_check", "review_triggers": []}
    diagnostic_context = {"intended_use": "assessment", "conclusion": "local-diagnostic"}
    return snapshot, artifacts, judgment, context, note, diagnostic_context


class B3aAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pl-b3a-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.snapshot, self.artifacts, self.judgment, self.context, self.note, self.diagnostic_context = fixture()
        self.variant_number = 0
        self.open_snapshot(self.snapshot)

    def open_snapshot(self, snapshot):
        self.variant_number += 1
        self.root = Path(self.temp.name) / f"workspace-{self.variant_number}"
        self.store = LearningStore(self.root, entry_actor="AG3")
        self.assertEqual(self.store.init_workspace()["status"], "committed")
        seeded = self.store.import_fixture(snapshot, self.artifacts)
        self.assertEqual(seeded["status"], "committed", seeded)
        self.service = AssessmentService(self.store)

    def variation(self, mutate):
        snapshot = copy.deepcopy(self.snapshot)
        mutate(objects_by_id(snapshot), snapshot)
        self.open_snapshot(snapshot)

    def revision(self):
        return self.store.read_context()["state_revision"]

    def inspect(self, judgment=None, context=None):
        return self.service.inspect_judgment(self.judgment if judgment is None else judgment, self.context if context is None else context)

    def diagnose(self, note=None, context=None):
        return self.service.inspect_diagnostic(self.note if note is None else note, self.diagnostic_context if context is None else context)

    def codes(self, result):
        return {problem["code"] for problem in result.get("reasons", [])}

    def assert_unusable(self, result):
        self.assertIn(result["status"], {"limited", "rejected", "blocked"}, result)
        self.assertTrue(result.get("reasons"), result)
        self.assertFalse(result.get("mutated", False), result)

    def assert_limited(self, result, support="unknown"):
        self.assertEqual(result["status"], "limited", result)
        self.assertEqual(result["expected_support"], support, result)
        self.assertTrue(result["unsupported_scope"], result)
        self.assertTrue(result["next_action"], result)
        self.assertFalse(result["mutated"])

    def response(self, sequence, purpose="independent"):
        candidate = copy.deepcopy(self.judgment)
        candidate["conditions"]["purpose"] = purpose
        candidate["conditions"]["response_points"][0]["sequence"] = sequence
        return candidate

    def submission(self, operation="FIX-b3a-submit", judgment=None):
        candidate = copy.deepcopy(self.judgment if judgment is None else judgment)
        grant_ref = candidate["authorization_ref"]
        return {"expected_state_revision": self.revision(), "operation_id": operation,
                "changes": [candidate], "artifacts": {}, "authorization_refs": [grant_ref],
                "adoption_refs": [grant_ref], "contexts": {candidate["id"]: copy.deepcopy(self.context)}}

    def database_dump(self):
        connection = sqlite3.connect(self.store.db_path)
        try:
            return "\n".join(connection.iterdump())
        finally:
            connection.close()

    def two_operations(self, objects, _snapshot):
        activity = objects["FIX-activity"]
        activity["learner_operations"] = ["connect-P-to-Q", "connect-Q-to-R"]
        activity["criterion_refs"] = [{"id": "FIX-goal", "revision": 1, "locator": "requirements/complete-chain"}]
        activity["task_qualification"]["value"]["target_operations"] = list(activity["learner_operations"])

    def full_chain(self):
        candidate = copy.deepcopy(self.judgment)
        candidate.update(requirement_id="complete-chain", conclusion="full-chain")
        candidate["conditions"]["operation_findings"].append({"operation": "connect-Q-to-R", "support": "supported", "rationale": "另一操作的人工评分声明。"})
        return candidate

    def time_fixture(self, objects, _snapshot, *, elapsed=True, no_contact=False, contacted=False):
        objects["FIX-goal"]["time_requirements"] = fact("known", value={
            "requirement_ids": ["infer-Q"], "minimum_delay_seconds": 3600, "require_no_contact": no_contact})
        objects["FIX-event"]["occurred_at"] = fact("known", value="2026-01-02T12:00:00+08:00")
        objects["FIX-event"]["timeline"][0]["time"] = fact("known", value="2026-01-02T12:00:00+08:00")
        objects["FIX-event"]["contact_history"] = fact("known", value={
            "last_relevant_at": "2026-01-02T10:00:00+08:00" if elapsed else "2026-01-02T11:59:00+08:00",
            "intervening_contact": fact("known", value=contacted) if no_contact else fact("unknown", "目标未要求严格无接触。")})

    def test_explicit_initial_finding_is_read_only_and_uses_one_sample(self):
        before = self.store.read_context()
        candidate, context = copy.deepcopy(self.judgment), copy.deepcopy(self.context)
        result = self.inspect(candidate, context)
        self.assertEqual(VERSION, "pl-assessment/0.1.0")
        self.assertEqual(result["status"], "compatible", result)
        self.assertEqual(result["expected_support"], "supported")
        self.assertTrue(result["operation_conditions"])
        self.assertEqual(result["samples"], ["FIX-sample-1"])
        self.assertFalse(result["mutated"])
        self.assertEqual(self.store.read_context(), before)
        self.assertEqual(candidate, self.judgment)
        self.assertEqual(context, self.context)
        self.assertNotIn("FIX-B3A-ORIGINAL", json.dumps(result, ensure_ascii=False))

    def test_professional_findings_are_not_generated_by_content_guessing(self):
        candidate = copy.deepcopy(self.judgment)
        candidate["conditions"]["operation_findings"][0].update(support="observed_not_met", rationale="人工声明未满足；程序不覆盖这项专业评分。")
        candidate.update(support="observed_not_met", conclusion="local-not-met")
        result = self.inspect(candidate)
        self.assertEqual(result["expected_support"], "observed_not_met", result)
        self.assertEqual(candidate["support"], "observed_not_met")

    def test_help_after_initial_response_does_not_contaminate_initial_point(self):
        self.assertEqual(self.inspect()["status"], "compatible")
        self.assert_limited(self.inspect(self.response(3)))

    def test_assisted_revision_can_support_only_assisted_scope_and_same_sample(self):
        candidate = self.response(3, "assisted")
        result = self.inspect(candidate)
        self.assertEqual(result["status"], "compatible", result)
        self.assertEqual(result["expected_support"], "supported")
        self.assertEqual(result["samples"], self.inspect()["samples"])
        self.assertTrue(result["unsupported_scope"])
        self.assertEqual(candidate["event_refs"], self.judgment["event_refs"])

    def test_planned_requested_and_backend_help_are_not_actual_exposure(self):
        for visibility in ("planned", "requested", "backend_reference"):
            with self.subTest(visibility=visibility):
                self.variation(lambda objects, _: objects["FIX-event"]["timeline"][1].update(visibility=visibility))
                result = self.inspect(self.response(3))
                self.assertEqual(result["status"], "compatible", result)
                self.assertEqual(result["expected_support"], "supported")

    def test_unknown_display_limits_target_operation_without_asserting_help(self):
        self.variation(lambda objects, _: objects["FIX-event"]["timeline"][1].update(visibility="unknown", substituted_operations=[]))
        self.assert_limited(self.inspect(self.response(3)))

    def test_unknown_exposure_with_no_operation_scope_keeps_all_tested_operations_unknown(self):
        self.variation(lambda objects, _: objects["FIX-event"]["timeline"][1].update(visibility="unknown", target_operations=[], substituted_operations=[]))
        self.assert_limited(self.inspect(self.response(3)))

    def test_unknown_exposure_on_other_operation_does_not_blanket_contaminate(self):
        self.variation(lambda objects, _: objects["FIX-event"]["timeline"][1].update(visibility="unknown", target_operations=["unrelated-operation"], substituted_operations=[]))
        result = self.inspect(self.response(3))
        self.assertEqual(result["status"], "compatible", result)
        self.assertEqual(result["expected_support"], "supported")

    def test_missing_completeness_is_unknown_independence_not_zero_help(self):
        for missing in (True, False):
            with self.subTest(missing=missing):
                def mutate(objects, _):
                    if missing:
                        del objects["FIX-event"]["timeline_completeness"]
                    else:
                        objects["FIX-event"]["timeline_completeness"] = fact("unknown", "宿主未确认展示是否完整。")
                self.variation(mutate)
                self.assert_limited(self.inspect())

    def test_only_substituted_operation_is_limited_and_axis_aggregates_mixed(self):
        self.variation(self.two_operations)
        candidate = self.full_chain()
        candidate["conditions"]["response_points"][0]["sequence"] = 3
        result = self.inspect(candidate)
        self.assert_limited(result, "mixed_or_conflicting")
        self.assertEqual(len(result["operation_conditions"]), 2)

    def test_operation_findings_must_exactly_cover_requirement(self):
        for findings in ([], [{"operation": "unrelated-operation", "support": "supported", "rationale": "错误操作范围。"}],
                         [self.judgment["conditions"]["operation_findings"][0]] * 2):
            with self.subTest(findings=findings):
                candidate = copy.deepcopy(self.judgment)
                candidate["conditions"]["operation_findings"] = copy.deepcopy(findings)
                self.assert_unusable(self.inspect(candidate))

    def test_missing_explicit_professional_rationale_is_not_invented(self):
        candidate = copy.deepcopy(self.judgment)
        candidate["conditions"]["operation_findings"][0]["rationale"] = ""
        self.assert_unusable(self.inspect(candidate))

    def test_top_level_support_cannot_disagree_with_operation_aggregation(self):
        candidate = copy.deepcopy(self.judgment)
        candidate["support"] = "observed_not_met"
        self.assert_unusable(self.inspect(candidate))
        result = self.service.submit_assessment(self.submission(judgment=candidate))
        self.assertEqual(result["status"], "rejected", result)
        self.assertEqual(self.revision(), 1)

    def test_response_point_missing_duplicate_or_nonresponse_sequence_is_rejected(self):
        for points in ([], self.judgment["conditions"]["response_points"] * 2,
                       [{"event_ref": {"id": "FIX-event", "revision": 1}, "sequence": 2}],
                       [{"event_ref": {"id": "FIX-event", "revision": 1}, "sequence": 99}]):
            with self.subTest(points=points):
                candidate = copy.deepcopy(self.judgment)
                candidate["conditions"]["response_points"] = copy.deepcopy(points)
                self.assert_unusable(self.inspect(candidate))

    def test_duplicate_event_reference_does_not_inflate_samples(self):
        candidate = copy.deepcopy(self.judgment)
        candidate["event_refs"] *= 2
        self.assert_unusable(self.inspect(candidate))

    def test_two_distinct_events_retain_two_independent_sample_ids(self):
        def mutate(objects, snapshot):
            event = copy.deepcopy(objects["FIX-event"])
            event.update(id="FIX-b3a-second-event", independent_sample_id="FIX-b3a-second-sample")
            snapshot["objects"].append(event)
        self.variation(mutate)
        candidate = copy.deepcopy(self.judgment)
        second = {"id": "FIX-b3a-second-event", "revision": 1}
        candidate["event_refs"].append(second)
        candidate["basis_refs"].append(second)
        candidate["conditions"]["response_points"].append({"event_ref": second, "sequence": 1})
        result = self.inspect(candidate)
        self.assertEqual(result["status"], "compatible", result)
        self.assertEqual(set(result["samples"]), {"FIX-sample-1", "FIX-b3a-second-sample"})

    def test_time_not_required_does_not_generate_missing_delay_evidence(self):
        self.assertEqual(self.inspect()["status"], "compatible")
        event = objects_by_id(self.snapshot)["FIX-event"]
        self.assertEqual(event["occurred_at"]["status"], "not_executed")
        self.assertEqual(event["contact_history"]["status"], "unknown")

    def test_elapsed_time_uses_last_relevant_contact_and_strict_no_contact_only_when_required(self):
        self.variation(lambda objects, snapshot: self.time_fixture(objects, snapshot))
        self.assertEqual(self.inspect()["status"], "compatible")
        self.variation(lambda objects, snapshot: self.time_fixture(objects, snapshot, elapsed=False))
        self.assert_limited(self.inspect())

    def test_unknown_last_contact_is_not_inferred_from_current_calendar(self):
        def mutate(objects, snapshot):
            self.time_fixture(objects, snapshot)
            objects["FIX-event"]["contact_history"] = fact("unknown", "最近相关接触无合法记录。")
        self.variation(mutate)
        self.assert_limited(self.inspect())

    def test_required_no_contact_has_its_own_evidence_axis(self):
        self.variation(lambda objects, snapshot: self.time_fixture(objects, snapshot, no_contact=True, contacted=False))
        self.assertEqual(self.inspect()["status"], "compatible")
        self.variation(lambda objects, snapshot: self.time_fixture(objects, snapshot, no_contact=True, contacted=True))
        self.assert_limited(self.inspect())

    def test_task_must_call_target_operation_and_fit_prerequisites_and_reference(self):
        for field in ("target_operations", "prerequisite_fit", "reference_scorable", "evidence_conditions"):
            with self.subTest(field=field):
                def mutate(objects, _):
                    qualification = objects["FIX-activity"]["task_qualification"]["value"]
                    qualification[field] = ["unrelated-operation"] if field == "target_operations" else fact("known", value=False)
                self.variation(mutate)
                self.assert_limited(self.inspect())

    def test_material_content_and_use_and_exact_binding_remain_separate(self):
        for case in ("content_pending", "use_pending", "stale_content", "stale_use", "wrong_activity", "wrong_goal"):
            with self.subTest(case=case):
                def mutate(objects, _):
                    verification = objects["FIX-material"]["verification"]
                    if case.endswith("pending"):
                        verification[case.split("_")[0]]["status"] = "pending"
                    elif case.startswith("stale"):
                        verification[case.split("_")[1]]["checked_revision"] = 2
                    elif case == "wrong_activity":
                        verification["use"]["binding"]["activity_ref"] = ref(objects["FIX-parent-activity"])
                    else:
                        verification["use"]["binding"]["goal_refs"] = []
                self.variation(mutate)
                self.assert_unusable(self.inspect())

    def test_missing_original_line_segment_locator_does_not_prove_reading(self):
        def mutate(objects, _):
            original = objects["FIX-event"]["original_response"]
            original.update(start_line=1, end_line=2)
        self.variation(mutate)
        result = self.inspect()
        self.assert_unusable(result)
        self.assertNotIn("FIX-B3A-ORIGINAL", json.dumps(result, ensure_ascii=False))

    def test_without_line_segment_reference_check_does_not_copy_original_body(self):
        def mutate(objects, _):
            original = objects["FIX-event"]["original_response"]
            original.pop("start_line")
            original.pop("end_line")
        self.variation(mutate)
        result = self.inspect()
        self.assertEqual(result["status"], "compatible", result)
        self.assertNotIn("FIX-B3A-ORIGINAL", json.dumps(result, ensure_ascii=False))

    def test_review_triggers_are_explicit_and_ag0_cannot_promote_its_own_review(self):
        self.assert_unusable(self.inspect(context={"intended_use": "independent_check"}))
        candidate = copy.deepcopy(self.judgment)
        candidate.update(owner="AG0", decision_type="routine_scoring", authorization_ref={"id": "FIX-scoring-grant", "revision": 1})
        local = AssessmentService(LearningStore(self.root, entry_actor="AG0"))
        self.assertEqual(local.inspect_judgment(candidate, self.context)["status"], "compatible")
        for trigger in ("important_skip", "whole_product", "nonstandard_solution", "scoring_dispute", "counterevidence", "deletion_impact", "conclusion_extension"):
            with self.subTest(trigger=trigger):
                result = local.inspect_judgment(candidate, {**self.context, "review_triggers": [trigger]})
                self.assert_unusable(result)
                self.assertTrue(result.get("next_action"), result)

    def test_important_review_requires_ag3_and_its_professional_grant(self):
        context = {**self.context, "review_triggers": ["important_skip"]}
        self.assertEqual(self.inspect(context=context)["status"], "compatible")
        candidate = copy.deepcopy(self.judgment)
        candidate["decision_type"] = "routine_scoring"
        self.assert_unusable(self.inspect(candidate, context))

    def test_conflicting_prior_judgment_requires_original_review_not_arrival_order(self):
        def mutate(_objects, snapshot):
            contrary = copy.deepcopy(self.judgment)
            contrary.update(id="FIX-b3a-contrary", support="observed_not_met", conclusion="local-not-met")
            contrary["conditions"]["operation_findings"][0].update(support="observed_not_met", rationale="相反人工评分声明。")
            contrary["adoption"] = {"status": "adopted", "by": "AG3", "scope": "人工相反评分", "basis_refs": [contrary["authorization_ref"]]}
            snapshot["objects"].append(contrary)
        self.variation(mutate)
        result = self.inspect()
        self.assert_unusable(result)
        context = {**self.context, "review_resolution": {"rationale": "已回原答与同一判据，说明相反声明为何不再采用。", "reviewed_refs": [{"id": "FIX-b3a-contrary", "revision": 1}]}}
        resolved = self.inspect(context=context)
        self.assertEqual(resolved["status"], "compatible", resolved)
        self.assertEqual(resolved["expected_support"], "supported")

    def test_review_resolution_must_cover_conflicting_reference(self):
        def mutate(_objects, snapshot):
            contrary = copy.deepcopy(self.judgment)
            contrary.update(id="FIX-b3a-contrary", support="observed_not_met", conclusion="local-not-met")
            contrary["conditions"]["operation_findings"][0]["support"] = "observed_not_met"
            contrary["adoption"] = {"status": "adopted", "by": "AG3", "scope": "人工相反评分", "basis_refs": [contrary["authorization_ref"]]}
            snapshot["objects"].append(contrary)
        self.variation(mutate)
        context = {**self.context, "review_resolution": {"rationale": "没有覆盖真正相反判断。", "reviewed_refs": [{"id": "FIX-judgment", "revision": 1}]}}
        self.assert_unusable(self.inspect(context=context))

    def test_authority_checks_subject_decision_object_criterion_conclusion_validity_and_budget(self):
        for case in ("grantee", "decision", "objects", "criterion", "conclusion", "validity", "budget"):
            with self.subTest(case=case):
                def mutate(objects, snapshot):
                    grant = copy.deepcopy(objects["FIX-evidence-grant"])
                    grant["id"] = "FIX-b3a-wrong-grant"
                    if case == "grantee":
                        grant["grantee"] = "AG1"
                    elif case == "decision":
                        grant["decision_types"] = ["limited_diagnosis"]
                    elif case == "objects":
                        grant["object_scope"] = ["FIX-unrelated-*"]
                    elif case == "criterion":
                        grant["criterion_refs"] = [{"id": "FIX-goal", "revision": 1, "locator": "requirements/complete-chain"}]
                    elif case == "conclusion":
                        grant["permitted_conclusions"] = ["unrelated-conclusion"]
                    elif case == "validity":
                        grant["validity"] = fact("known", value={"active": False})
                    else:
                        budget = copy.deepcopy(objects["FIX-budget"])
                        budget["id"] = "FIX-b3a-other-budget"
                        snapshot["objects"].append(budget)
                        grant["budget_ref"] = ref(budget)
                    snapshot["objects"].append(grant)
                self.variation(mutate)
                candidate = copy.deepcopy(self.judgment)
                candidate["authorization_ref"] = {"id": "FIX-b3a-wrong-grant", "revision": 1}
                self.assert_unusable(self.inspect(candidate))
                self.assertEqual(self.service.submit_assessment(self.submission(judgment=candidate))["status"], "rejected")
                self.assertEqual(self.revision(), 1)

    def test_diagnostic_is_tentative_read_only_and_does_not_add_observation(self):
        before = self.store.read_context()
        result = self.diagnose()
        self.assertEqual(result["status"], "compatible", result)
        self.assertFalse(result["mutated"])
        self.assertTrue(result["next_action"])
        self.assertEqual(self.store.read_context(), before)
        for status in ("not_required", "not_executed"):
            note = copy.deepcopy(self.note)
            note["next_observation"] = fact(status, "不追加测试。")
            self.assertEqual(self.diagnose(note)["status"], "compatible")

    def test_diagnostic_requires_alternatives_counterevidence_distinct_actions_and_stop_conditions(self):
        for field, value in (("alternatives", []), ("counterevidence", None), ("decision_branches", []),
                             ("stop_condition", ""), ("stop_reason", ""), ("reopen_condition", "")):
            with self.subTest(field=field):
                note = copy.deepcopy(self.note)
                note[field] = value
                self.assert_unusable(self.diagnose(note))
        note = copy.deepcopy(self.note)
        note["decision_branches"] = [{"observation": "有原答", "plan_action": "继续"}, {"observation": "无原答", "plan_action": "继续"}]
        self.assert_unusable(self.diagnose(note))

    def test_diagnostic_context_and_budget_and_observations_are_explicit(self):
        self.assert_unusable(self.diagnose(context={"intended_use": "assessment"}))
        note = copy.deepcopy(self.note)
        note["observations"] = []
        self.assert_unusable(self.diagnose(note))
        note = copy.deepcopy(self.note)
        note["authorization_ref"] = {"id": "FIX-scoring-grant", "revision": 1}
        self.assert_unusable(self.diagnose(note))

    def test_submit_persists_after_reopen_preserves_events_originals_and_plan_without_adopting(self):
        before = objects_by_id(self.store.read_context())
        request = self.submission()
        result = self.service.submit_assessment(request)
        self.assertEqual(result["status"], "committed", result)
        reopened = LearningStore(self.root, entry_actor="AG3")
        after = objects_by_id(reopened.read_context())
        self.assertEqual(after["FIX-b3a-judgment"], request["changes"][0])
        self.assertEqual(after["FIX-b3a-judgment"]["adoption"]["status"], "candidate")
        for identifier in ("FIX-event", "FIX-plan", "FIX-goal", "FIX-activity", "FIX-material", "FIX-judgment"):
            self.assertEqual(after[identifier], before[identifier])
        exported = reopened.export_scope(["FIX-b3a-judgment"], include_artifacts=True)
        self.assertEqual(exported["artifacts"]["b3a-responses.md"], self.artifacts["b3a-responses.md"])
        self.assertEqual(reopened.check_integrity()["status"], "ok")

    def test_limited_unknown_pending_review_can_save_without_inventing_new_test(self):
        candidate = self.response(3)
        candidate.update(support="unknown", eligibility="pending_review", conclusion="local-unknown")
        result = self.service.submit_assessment(self.submission(judgment=candidate))
        self.assertEqual(result["status"], "committed", result)
        objects = objects_by_id(self.store.read_context())
        self.assertEqual(objects["FIX-b3a-judgment"]["support"], "unknown")
        self.assertEqual(objects["FIX-b3a-judgment"]["eligibility"], "pending_review")
        self.assertEqual(sum(obj["type"] == "PerformanceEvent" for obj in objects.values()), 1)
        self.assertEqual(sum(obj["type"] == "LearningNeed" for obj in objects.values()), 1)

    def test_limited_result_cannot_save_usable_or_unrestricted_supported_claim(self):
        for support, eligibility in (("supported", "usable"), ("unknown", "usable"), ("supported", "pending_review")):
            with self.subTest(support=support, eligibility=eligibility):
                candidate = self.response(3)
                candidate.update(support=support, eligibility=eligibility)
                result = self.service.submit_assessment(self.submission(judgment=candidate))
                self.assertEqual(result["status"], "rejected", result)
                self.assertEqual(self.revision(), 1)

    def test_submit_requires_explicit_authority_adoption_and_per_object_context(self):
        for field in ("authorization_refs", "adoption_refs", "contexts"):
            with self.subTest(field=field):
                request = self.submission("FIX-b3a-missing-" + field)
                request[field] = {} if field == "contexts" else []
                result = self.service.submit_assessment(request)
                self.assertEqual(result["status"], "rejected", result)
                self.assertEqual(self.revision(), 1)

    def test_assessment_submit_cannot_create_other_professional_or_execution_objects(self):
        objects = objects_by_id(self.snapshot)
        for identifier in ("FIX-event", "FIX-need", "FIX-evidence-grant", "FIX-material", "FIX-plan"):
            with self.subTest(identifier=identifier):
                request = self.submission("FIX-b3a-clandestine-" + identifier)
                hidden = copy.deepcopy(objects[identifier])
                hidden["revision"] += 1
                request["changes"].append(hidden)
                self.assertEqual(self.service.submit_assessment(request)["status"], "rejected")
                self.assertEqual(self.revision(), 1)
        local = AssessmentService(LearningStore(self.root, entry_actor="AG0"))
        self.assertEqual(local.submit_assessment(self.submission())["status"], "rejected")

    def test_diagnostic_submit_uses_same_store_gate_without_scheduling(self):
        note = copy.deepcopy(self.note)
        request = {"expected_state_revision": 1, "operation_id": "FIX-b3a-diagnostic-submit", "changes": [note],
                   "authorization_refs": [note["authorization_ref"]], "adoption_refs": [note["authorization_ref"]],
                   "contexts": {note["id"]: self.diagnostic_context}}
        before = objects_by_id(self.store.read_context())
        result = self.service.submit_assessment(request)
        self.assertEqual(result["status"], "committed", result)
        after = objects_by_id(self.store.read_context())
        self.assertEqual(after["FIX-b3a-diagnostic"], note)
        self.assertEqual(after["FIX-plan"], before["FIX-plan"])
        self.assertEqual(after["FIX-event"], before["FIX-event"])

    def test_same_operation_same_bytes_is_idempotent_changed_bytes_rejected(self):
        request = self.submission("FIX-b3a-idempotent")
        first = self.service.submit_assessment(request)
        second = self.service.submit_assessment(copy.deepcopy(request))
        self.assertEqual(first["status"], "committed", first)
        self.assertEqual(second, first)
        changed = copy.deepcopy(request)
        changed["changes"][0]["rationale"] += " FIX-B3A-RETRY-CHANGED"
        result = self.service.submit_assessment(changed)
        self.assertEqual(result["status"], "rejected", result)
        self.assertNotIn("FIX-B3A-RETRY-CHANGED", self.database_dump())
        self.assertEqual(self.revision(), first["state_revision"])

    def test_stale_state_and_stale_event_basis_are_rejected_without_writing(self):
        request = self.submission("FIX-b3a-stale-state")
        self.assertEqual(self.store.pause(1, "FIX-b3a-unrelated-pause", ["FIX-method"], "无关暂停")["status"], "committed")
        self.assertEqual(self.service.submit_assessment(request)["status"], "conflict")
        event = copy.deepcopy(objects_by_id(self.store.read_context())["FIX-event"])
        event["revision"] += 1
        ag0 = LearningStore(self.root, entry_actor="AG0")
        saved = ag0.commit(self.revision(), "FIX-b3a-new-event-revision", [event])
        self.assertEqual(saved["status"], "committed", saved)
        self.assert_unusable(self.inspect())
        result = self.service.submit_assessment(self.submission("FIX-b3a-stale-basis"))
        self.assertEqual(result["status"], "rejected", result)
        self.assertNotIn("FIX-b3a-judgment", objects_by_id(self.store.read_context()))

    def test_controls_precede_inspection_and_success_receipt_and_resume_cannot_restore(self):
        request = self.submission("FIX-b3a-before-restriction")
        self.assertEqual(self.service.submit_assessment(request)["status"], "committed")
        gate = self.store.restrict(self.revision(), "FIX-b3a-limit", ["FIX-event"], "人工专业待复核", ["assessment", "independent_check"])
        self.assertEqual(gate["status"], "committed")
        self.assertEqual(self.inspect()["status"], "blocked")
        self.assertEqual(self.service.submit_assessment(request)["status"], "rejected")
        resumed = self.store.resume(self.revision(), "FIX-b3a-resume", ["FIX-event"])
        self.assertEqual(resumed["status"], "committed")
        self.assertEqual(self.inspect()["status"], "blocked")

    def test_pause_blocks_assessment_but_canonical_read_is_still_allowed(self):
        gate = self.store.pause(self.revision(), "FIX-b3a-pause", ["FIX-activity"], "人工用户暂停")
        self.assertEqual(gate["status"], "committed")
        self.assertEqual(self.store.read_context()["status"], "ok")
        self.assertEqual(self.inspect()["status"], "blocked")
        self.assertEqual(self.service.submit_assessment(self.submission())["status"], "rejected")

    def test_late_deleted_result_cannot_reintroduce_payload_or_original(self):
        request = self.submission("FIX-b3a-deleted-late")
        request["changes"][0]["rationale"] = "FIX-B3A-LATE-DELETED-PAYLOAD"
        deleted = self.store.delete_scope(1, "FIX-b3a-delete", ["FIX-event"])
        self.assertEqual(deleted["status"], "committed", deleted)
        request["expected_state_revision"] = self.revision()
        result = self.service.submit_assessment(request)
        self.assertEqual(result["status"], "rejected", result)
        self.assertNotIn("FIX-B3A-LATE-DELETED-PAYLOAD", self.database_dump())
        self.assertNotIn("FIX-B3A-LATE-DELETED-PAYLOAD", json.dumps(result))
        inspected = self.inspect()
        self.assertEqual(inspected["status"], "blocked", inspected)
        self.assertNotIn("FIX-B3A-ORIGINAL", json.dumps(inspected))
        self.assertNotIn("FIX-b3a-judgment", objects_by_id(self.store.read_context()))

    def test_transaction_failure_has_no_partial_judgment_or_receipt_after_reopen(self):
        def fail(stage):
            if stage == "after_write":
                raise RuntimeError("artificial failure")
        self.store.failpoint = fail
        result = self.service.submit_assessment(self.submission("FIX-b3a-failure"))
        self.assertEqual(result["status"], "not_saved", result)
        reopened = LearningStore(self.root, entry_actor="AG3")
        state = reopened.read_context()
        self.assertEqual(state["state_revision"], 1)
        self.assertNotIn("FIX-b3a-judgment", objects_by_id(state))
        self.assertNotIn("FIX-b3a-failure", self.database_dump())

    def test_cli_inspect_and_diagnose_are_read_only_and_use_real_stored_records(self):
        for command, request in (("inspect", {"judgment": self.judgment, "context": self.context}),
                                 ("diagnose", {"diagnostic": self.note, "context": self.diagnostic_context})):
            with self.subTest(command=command):
                request_path = Path(self.temp.name) / (command + ".json")
                request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
                result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "src/runtime/learning_assessment.py"),
                                         "--workspace", str(self.root), "--request", str(request_path), "--actor", "AG3", command],
                                        capture_output=True, text=True, encoding="utf-8", cwd=self.temp.name)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                output = json.loads(result.stdout)
                self.assertEqual(output["status"], "compatible", output)
                self.assertNotIn("FIX-B3A-ORIGINAL", result.stdout)
                self.assertEqual(self.revision(), 1)

    def test_demo_new_space_saves_once_then_existing_space_is_read_only(self):
        workspace = Path(self.temp.name) / "demo"
        report = Path(self.temp.name) / "demo-report.json"
        command = [sys.executable, "-X", "utf8", str(ROOT / "scripts/demo_b3a.py"),
                   "--workspace", str(workspace), "--report", str(report)]
        first = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", cwd=self.temp.name)
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        store = LearningStore(workspace, entry_actor="AG3")
        before = store.read_context()
        second = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", cwd=self.temp.name)
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        self.assertEqual(store.read_context(), before)
        observed = json.loads(report.read_text(encoding="utf-8"))
        self.assertTrue(observed["existing_workspace"])
        self.assertEqual(observed["save_receipt"]["status"], "not_executed")
        self.assertFalse(observed["new_performance_created"])

    def test_ag0_cannot_hide_important_use_counterevidence_or_grant_signal(self):
        candidate = copy.deepcopy(self.judgment)
        candidate.update(owner="AG0", decision_type="routine_scoring", authorization_ref={"id": "FIX-scoring-grant", "revision": 1})
        local = AssessmentService(LearningStore(self.root, entry_actor="AG0"))
        contrary = copy.deepcopy(candidate)
        contrary["counterevidence"] = ["人工原答中存在尚未处理的相反依据。"]
        self.assertEqual(local.inspect_judgment(contrary, self.context)["status"], "rejected")
        important = copy.deepcopy(candidate)
        important["intended_uses"] = ["important_skip"]
        self.assertEqual(local.inspect_judgment(important, {"intended_use": "important_skip", "review_triggers": []})["status"], "rejected")
        def mutate(objects, _):
            objects["FIX-scoring-grant"]["escalation_signals"].append("independent_check")
        self.variation(mutate)
        local = AssessmentService(LearningStore(self.root, entry_actor="AG0"))
        self.assertEqual(local.inspect_judgment(candidate, self.context)["status"], "rejected")

    def test_teaching_material_binding_cannot_be_used_as_independent_material(self):
        def mutate(objects, _):
            binding = objects["FIX-material"]["verification"]["use"]["binding"]
            binding.update(intended_use="teaching", purpose="teaching")
        self.variation(mutate)
        self.assert_unusable(self.inspect())
        result = self.service.submit_assessment(self.submission())
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.revision(), 1)

    def test_same_id_revision_cannot_overwrite_conflicting_adopted_judgment(self):
        def mutate(_objects, snapshot):
            old = copy.deepcopy(self.judgment)
            old["adoption"] = {"status": "adopted", "by": "AG3", "scope": "人工旧评分", "basis_refs": [old["authorization_ref"]]}
            snapshot["objects"].append(old)
        self.variation(mutate)
        contrary = copy.deepcopy(self.judgment)
        contrary.update(revision=2, support="observed_not_met", conclusion="local-not-met")
        contrary["conditions"]["operation_findings"][0]["support"] = "observed_not_met"
        result = self.inspect(contrary)
        self.assertIn({"id": contrary["id"], "revision": 1}, result["conflicting_refs"])
        self.assertFalse(result["submission_ready"])
        self.assertEqual(self.service.submit_assessment(self.submission(judgment=contrary))["status"], "rejected")
        self.assertEqual(self.revision(), 1)

    def test_recursive_old_material_after_error_revision_is_not_usable(self):
        ag2 = LearningStore(self.root, entry_actor="AG2")
        material = copy.deepcopy(objects_by_id(self.store.read_context())["FIX-material"])
        material["revision"] = 2
        material["verification"]["content"]["status"] = "error"
        material["verification"]["content"]["checked_revision"] = 2
        material["verification"]["use"]["checked_revision"] = 2
        material["decision_type"] = "material_verification"
        grant_ref = {"id": "FIX-b2b-material-grant", "revision": 1}
        result = ag2.commit(1, "FIX-b3a-material-error", [material], authorization_refs=[grant_ref], adoption_refs=[grant_ref])
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.inspect()["status"], "rejected")
        self.assertIn("stale_assessment_dependency", self.codes(self.inspect()))
        self.assertEqual(self.service.submit_assessment(self.submission())["status"], "rejected")

    def test_invalid_grant_is_rejected_before_loading_performance_or_context(self):
        def mutate(objects, snapshot):
            grant = copy.deepcopy(objects["FIX-evidence-grant"])
            grant.update(id="FIX-b3a-unauthorized-grant", grantee="AG1")
            snapshot["objects"].append(grant)
        self.variation(mutate)
        candidate = copy.deepcopy(self.judgment)
        candidate["authorization_ref"] = {"id": "FIX-b3a-unauthorized-grant", "revision": 1}
        reads = []
        original = self.store.read_refs
        def tracked(refs, intended_use="read"):
            reads.append(copy.deepcopy(refs))
            return original(refs, intended_use)
        def forbidden_context():
            self.fail("Unauthorized inspection read the full performance context.")
        self.store.read_refs = tracked
        self.store.read_context = forbidden_context
        result = self.inspect(candidate)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(reads, [[candidate["authorization_ref"]]])

    def test_zero_budget_or_stop_signal_does_not_request_more_observation(self):
        self.variation(lambda objects, _: objects["FIX-budget"].update(user_active_time=fact("known", value={"minutes": 0, "measurement": "synthetic_limit"})))
        note = copy.deepcopy(self.note)
        note["next_observation"] = fact("known", value="下一项有价值但不能在零预算下安排的观察。")
        result = self.diagnose(note)
        self.assertEqual(result["status"], "compatible", result)
        self.assertEqual(result["next_action"], "no_additional_observation")
        self.assertEqual(result["new_tasks"], 0)
        self.open_snapshot(self.snapshot)
        result = self.diagnose(note, {**self.diagnostic_context, "stop_signal": "no_progress"})
        self.assertEqual(result["next_action"], "no_additional_observation")

    def test_temporal_gap_preserves_current_positive_operation_observation(self):
        self.variation(lambda objects, snapshot: self.time_fixture(objects, snapshot, elapsed=False))
        result = self.inspect()
        self.assertEqual(result["expected_support"], "unknown")
        self.assertEqual(result["operation_conditions"][0]["support"], "supported")
        self.assertTrue(result["unsupported_scope"])

    def test_known_empty_diagnostic_counterevidence_is_not_invented(self):
        note = copy.deepcopy(self.note)
        note["counterevidence"] = []
        result = self.diagnose(note)
        self.assertEqual(result["status"], "compatible", result)
        self.assertEqual(note["counterevidence"], [])

    def test_explicit_legacy_teaching_qualification_is_read_without_rewriting(self):
        def mutate(objects, _):
            objects["FIX-activity"]["task_qualification"] = fact("known", value={
                key: fact("known", value=True) for key in (
                    "target_operation_call", "prerequisite_burden", "not_substituted",
                    "reference_scorable", "evidence_conditions")})
        self.variation(mutate)
        before = self.store.read_context()
        self.assertEqual(self.inspect()["status"], "compatible")
        self.assertEqual(self.store.read_context(), before)

    def test_conflicting_parallel_task_declarations_are_rejected(self):
        for key in ("target_operation_call", "prerequisite_burden"):
            with self.subTest(key=key):
                self.variation(lambda objects, _: objects["FIX-activity"]["task_qualification"]["value"].update(
                    {key: fact("known", value=False)}))
                self.assertEqual(self.inspect()["status"], "rejected")

    def test_independent_actual_resource_must_be_in_exact_goal_scope(self):
        def mutate(objects, _):
            objects["FIX-event"]["actual_resources"]["value"].append("unapproved-solution-sheet")
        self.variation(mutate)
        before = self.store.read_context()
        result = self.inspect()
        self.assert_limited(result)
        self.assertIn("actual_resources_outside_allowed_scope", self.codes(result))
        self.assertEqual(self.store.read_context(), before)
        self.assertIn("unapproved-solution-sheet", objects_by_id(before)["FIX-event"]["actual_resources"]["value"])

    def test_known_allowed_resource_fact_matches_list_shape_without_inference(self):
        self.variation(lambda objects, _: objects["FIX-goal"].update(
            allowed_resources=fact("known", value=list(objects["FIX-goal"]["allowed_resources"]))))
        self.assertEqual(self.inspect()["status"], "compatible")

    def test_unknown_allowed_resources_limit_only_independent_claim(self):
        self.variation(lambda objects, _: objects["FIX-goal"].update(
            allowed_resources=fact("unknown", "No resource boundary was supplied.")))
        self.assertIn("allowed_resources_unknown", self.codes(self.inspect()))
        self.assertEqual(self.inspect(self.response(3, "assisted"))["status"], "compatible")

    def test_known_empty_resource_scope_is_distinct_from_unknown(self):
        def mutate(objects, _):
            objects["FIX-goal"]["allowed_resources"] = []
            objects["FIX-event"]["actual_resources"] = fact("known", value=[])
        self.variation(mutate)
        self.assertEqual(self.inspect()["status"], "compatible")

    def test_known_timestamp_object_is_accepted_by_assessment(self):
        def mutate(objects, snapshot):
            self.time_fixture(objects, snapshot)
            objects["FIX-event"]["timeline"][0]["time"] = fact("known", value={"timestamp": "2026-01-02T12:00:00+08:00"})
            objects["FIX-event"]["occurred_at"] = fact("unknown", "Selected response carries its own time.")
        self.variation(mutate)
        self.assertEqual(self.inspect()["status"], "compatible")

    def test_unknown_revision_time_never_falls_back_to_original_time(self):
        self.variation(lambda objects, snapshot: self.time_fixture(objects, snapshot))
        result = self.inspect(self.response(3, "assisted"))
        self.assert_limited(result)
        self.assertIn("relevant_times_unknown", self.codes(result))
        self.assertEqual(result["operation_conditions"][0]["support"], "supported")

    def test_latest_displayed_help_restarts_required_delay(self):
        def mutate(objects, snapshot):
            self.time_fixture(objects, snapshot)
            timeline = objects["FIX-event"]["timeline"]
            timeline[1].update(time=fact("known", value="2026-01-02T13:30:00+08:00"), substituted_operations=[])
            timeline[2]["time"] = fact("known", value="2026-01-02T14:00:00+08:00")
        self.variation(mutate)
        result = self.inspect(self.response(3))
        self.assert_limited(result)
        self.assertIn("required_delay_not_observed", self.codes(result))
        self.assertEqual(result["operation_conditions"][0]["support"], "supported")

    def test_unrelated_displayed_help_does_not_restart_target_delay(self):
        def mutate(objects, snapshot):
            self.time_fixture(objects, snapshot)
            timeline = objects["FIX-event"]["timeline"]
            timeline[1].update(target_operations=["unrelated-operation"], substituted_operations=[])
            timeline[2]["time"] = fact("known", value="2026-01-02T14:00:00+08:00")
        self.variation(mutate)
        self.assertEqual(self.inspect(self.response(3))["status"], "compatible")

    def test_unknown_relevant_help_time_prevents_delayed_claim(self):
        def mutate(objects, snapshot):
            self.time_fixture(objects, snapshot)
            timeline = objects["FIX-event"]["timeline"]
            timeline[1]["substituted_operations"] = []
            timeline[2]["time"] = fact("known", value="2026-01-02T14:00:00+08:00")
        self.variation(mutate)
        self.assertIn("relevant_times_unknown", self.codes(self.inspect(self.response(3))))

    def inherited_fixture(self, objects, snapshot, *, operation="connect-P-to-Q", visibility="displayed", complete=True, recursive=False):
        child = objects["FIX-event"]
        parent = copy.deepcopy(child)
        parent.update(id="FIX-b3a-parent-event", independent_sample_id="FIX-parent-sample")
        parent["timeline"] = copy.deepcopy(child["timeline"][:2])
        parent["timeline"][1].update(target_operations=[operation], substituted_operations=[operation], visibility=visibility)
        parent["timeline_completeness"] = fact("known", value=True) if complete else fact("unknown", "Ancestor history is incomplete.")
        child["c0"] = {"inherited_event_refs": [ref(parent)]}
        snapshot["objects"].append(parent)
        if recursive:
            ancestor = copy.deepcopy(parent)
            ancestor.update(id="FIX-b3a-grandparent-event", independent_sample_id="FIX-grandparent-sample")
            parent["timeline"] = parent["timeline"][:1]
            parent["c0"] = {"inherited_event_refs": [ref(ancestor)]}
            snapshot["objects"].append(ancestor)
        return parent

    def test_exact_parent_help_is_retained_without_adding_response_samples(self):
        self.variation(self.inherited_fixture)
        result = self.inspect()
        self.assert_limited(result)
        self.assertEqual(result["samples"], ["FIX-sample-1"])
        self.assertEqual(result["operation_conditions"][0]["displayed_substitution_refs"], [
            {"event_ref": {"id": "FIX-b3a-parent-event", "revision": 1}, "sequence": 2}])
        self.assertEqual(result["operation_conditions"][0]["displayed_substitution_sequences"], [])

    def test_recursive_ancestor_help_is_retained_and_duplicate_refs_do_not_count_twice(self):
        def mutate(objects, snapshot):
            parent = self.inherited_fixture(objects, snapshot, recursive=True)
            objects["FIX-event"]["c0"]["inherited_event_refs"].append(ref(parent))
        self.variation(mutate)
        result = self.inspect()
        self.assert_limited(result)
        self.assertEqual(len(result["operation_conditions"][0]["displayed_substitution_refs"]), 1)
        self.assertEqual(result["operation_conditions"][0]["displayed_substitution_refs"][0]["event_ref"]["id"], "FIX-b3a-grandparent-event")
        self.assertEqual(result["samples"], ["FIX-sample-1"])

    def test_parent_help_on_another_operation_does_not_blanket_limit_child(self):
        self.variation(lambda objects, snapshot: self.inherited_fixture(objects, snapshot, operation="unrelated-operation"))
        self.assertEqual(self.inspect()["status"], "compatible")

    def test_unknown_parent_visibility_limits_its_operation(self):
        self.variation(lambda objects, snapshot: self.inherited_fixture(objects, snapshot, visibility="unknown"))
        self.assertIn("exposure_visibility_unknown", self.codes(self.inspect()))

    def test_incomplete_ancestor_history_is_not_treated_as_zero_exposure(self):
        self.variation(lambda objects, snapshot: self.inherited_fixture(objects, snapshot, operation="unrelated-operation", complete=False))
        self.assertIn("inherited_exposure_completeness_unknown", self.codes(self.inspect()))

    def test_help_summary_without_exact_ancestor_is_not_a_help_fact(self):
        self.variation(lambda objects, _: objects["FIX-event"].update(c0={
            "inherited_event_refs": [], "inherited_help_conditions": [{"substituted_operations": ["connect-P-to-Q"]}]}))
        result = self.inspect()
        self.assertIn("inherited_exposure_completeness_unknown", self.codes(result))
        self.assertEqual(result["operation_conditions"][0]["displayed_substitution_refs"], [])

    def test_inherited_cycle_is_rejected_without_recursion_or_sample_inflation(self):
        def mutate(objects, snapshot):
            parent = self.inherited_fixture(objects, snapshot)
            parent["c0"] = {"inherited_event_refs": [ref(objects["FIX-event"])]}
        self.variation(mutate)
        result = self.inspect()
        self.assertEqual(result["status"], "rejected")
        self.assertIn("inherited_event_cycle", self.codes(result))

    def test_parent_displayed_contact_is_included_in_the_target_delay(self):
        def mutate(objects, snapshot):
            self.time_fixture(objects, snapshot)
            parent = self.inherited_fixture(objects, snapshot)
            parent["timeline"][1].update(time=fact("known", value="2026-01-02T11:30:00+08:00"), substituted_operations=[])
        self.variation(mutate)
        result = self.inspect()
        self.assertIn("required_delay_not_observed", self.codes(result))
        self.assertEqual(result["operation_conditions"][0]["support"], "supported")

    def test_displayed_contact_cannot_be_erased_by_declared_no_contact(self):
        def mutate(objects, snapshot):
            self.time_fixture(objects, snapshot, no_contact=True, contacted=False)
            timeline = objects["FIX-event"]["timeline"]
            timeline[1].update(time=fact("known", value="2026-01-02T12:00:00+08:00"), substituted_operations=[])
            timeline[2]["time"] = fact("known", value="2026-01-02T14:00:00+08:00")
        self.variation(mutate)
        result = self.inspect(self.response(3))
        self.assertIn("required_no_contact_unconfirmed", self.codes(result))
        self.assertNotIn("required_delay_not_observed", self.codes(result))

    def practice_fixture(self, objects, snapshot, *, prior_time="2026-01-02T12:00:00+08:00", prior_operation="connect-P-to-Q", response_time="2026-01-02T12:30:00+08:00"):
        self.time_fixture(objects, snapshot)
        event = objects["FIX-event"]
        event["timeline"] = [event["timeline"][0], event["timeline"][2]]
        event["timeline"][0].update(target_operations=[prior_operation],
            time=fact("known", value=prior_time) if prior_time else fact("unknown", "Earlier learner practice time was not measured."))
        event["timeline"][1].update(sequence=2, time=fact("known", value=response_time))
        event["revisions"][0]["sequence"] = 2

    def test_prior_learner_practice_restarts_delay_without_teacher_help(self):
        self.variation(self.practice_fixture)
        result = self.inspect(self.response(2, "assisted"))
        self.assert_limited(result)
        self.assertIn("required_delay_not_observed", self.codes(result))
        self.assertEqual(result["operation_conditions"][0]["support"], "supported")
        self.assertEqual(result["operation_conditions"][0]["displayed_substitution_refs"], [])
        self.assertEqual(result["samples"], ["FIX-sample-1"])

    def test_unknown_prior_practice_time_is_not_filled_from_event_start(self):
        self.variation(lambda objects, snapshot: self.practice_fixture(objects, snapshot,
            prior_time=None, response_time="2026-01-02T14:00:00+08:00"))
        result = self.inspect(self.response(2))
        self.assert_limited(result)
        self.assertIn("relevant_times_unknown", self.codes(result))
        self.assertEqual(result["operation_conditions"][0]["displayed_substitution_refs"], [])

    def test_prior_practice_on_other_operation_does_not_reset_target_delay(self):
        self.variation(lambda objects, snapshot: self.practice_fixture(objects, snapshot,
            prior_time=None, prior_operation="unrelated-operation"))
        self.assertEqual(self.inspect(self.response(2))["status"], "compatible")

    def test_delay_can_pass_after_sufficient_gap_from_prior_practice(self):
        self.variation(lambda objects, snapshot: self.practice_fixture(objects, snapshot,
            response_time="2026-01-02T14:00:00+08:00"))
        self.assertEqual(self.inspect(self.response(2))["status"], "compatible")

    def test_unknown_parent_practice_time_limits_required_delay(self):
        def mutate(objects, snapshot):
            self.time_fixture(objects, snapshot)
            parent = self.inherited_fixture(objects, snapshot)
            parent["timeline"] = parent["timeline"][:1]
            parent["timeline"][0]["time"] = fact("unknown", "Parent practice time is unknown.")
        self.variation(mutate)
        result = self.inspect()
        self.assert_limited(result)
        self.assertIn("relevant_times_unknown", self.codes(result))
        self.assertEqual(result["operation_conditions"][0]["displayed_substitution_refs"], [])

    def test_unknown_unrelated_parent_practice_does_not_reset_target_delay(self):
        def mutate(objects, snapshot):
            self.time_fixture(objects, snapshot)
            parent = self.inherited_fixture(objects, snapshot)
            parent["timeline"] = parent["timeline"][:1]
            parent["timeline"][0].update(target_operations=["unrelated-operation"], time=fact("unknown", "Unrelated practice time is unknown."))
        self.variation(mutate)
        self.assertEqual(self.inspect()["status"], "compatible")

    def test_assisted_teaching_material_has_explicit_distinct_use_context(self):
        def mutate(objects, _):
            material = objects["FIX-material"]
            material["intended_use"] = "teaching"
            material["verification"]["use"]["binding"].update(intended_use="teaching", purpose="teaching")
        self.variation(mutate)
        material_context = copy.deepcopy(objects_by_id(self.store.read_context())["FIX-material"]["verification"]["use"]["binding"])
        context = {**self.context, "material_context": material_context}
        self.assertEqual(self.inspect(self.response(3, "assisted"), context)["status"], "compatible")
        self.assertIn("reference_use_unconfirmed", self.codes(self.inspect(self.response(3), context)))
        self.assertIn("reference_use_unconfirmed", self.codes(self.inspect(self.response(3), {**context, "material_purpose": "teaching"})))
        self.assertIn("reference_use_unconfirmed", self.codes(self.inspect(self.response(3, "assisted"))))

    def test_material_context_requires_every_exact_b2b_binding_field(self):
        material_context = objects_by_id(self.snapshot)["FIX-material"]["verification"]["use"]["binding"]
        for key in ("activity_ref", "goal_refs", "intended_use", "required_modalities", "conditions", "purpose"):
            with self.subTest(key=key):
                context = {**self.context, "material_context": copy.deepcopy(material_context)}
                del context["material_context"][key]
                self.assertIn("reference_use_unconfirmed", self.codes(self.inspect(context=context)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
