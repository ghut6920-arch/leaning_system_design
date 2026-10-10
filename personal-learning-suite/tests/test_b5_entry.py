"""Public B5 orchestration on isolated, explicitly fictional records.

Professional findings are supplied declarations. These checks establish ordered
handoffs and preservation, never answer truth or authenticated host authority.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from runtime.entry_b5 import SingleEntryService
from runtime.learning_assessment import AssessmentService
from runtime.learning_goals import review_goal_package
from runtime.learning_materials import fact, ref
from runtime.learning_store import LearningStore
from runtime.learning_strategies import StrategyCatalog
from runtime.personal_learning import PersonalLearningEntry
from test_b2a_goals import fixture as goal_fixture, canonical_fixture
from test_b3a_assessment import fixture as assessment_fixture
from test_b4_planning import request as planning_request, decision
from test_b4_teaching import fixture as teaching_fixture, initial_request, EVENT_ID, GRANT_ID
from test_b3c_strategies import fixture as strategy_fixture, configured

VERSION = "pl-entry/0.1.0"
CHECKPOINT = "FIX-b5-checkpoint"
JUDGMENT = "FIX-b5-judgment"


def fixture():
    snapshot, artifacts, context = teaching_fixture()
    assessment_snapshot, _, judgment, assessment_context, _, _ = assessment_fixture()
    originals = {o["id"]: o for o in assessment_snapshot["objects"]}
    objects = {o["id"]: o for o in snapshot["objects"]}
    snapshot["fixture_id"] = "B5-synthetic-single-entry"
    snapshot["description"] = "虚构单入口交接；评分、采用、时间和权限均为显式人工声明。"
    objects["FIX-activity"]["parent_task"] = fact("not_applicable", "人工独立活动；不隐去真实父任务帮助。")
    for identifier in ("FIX-evidence-grant", "FIX-scoring-grant"):
        objects[identifier]["permitted_conclusions"] = copy.deepcopy(originals[identifier]["permitted_conclusions"])
        objects[identifier]["criterion_refs"] = copy.deepcopy(originals[identifier]["criterion_refs"])
    objects["FIX-need"]["acceptance"] = {"status": "proposed", "by": "AG0", "scope": "原有人工需求", "next_trigger": "由 AG1 接责后处理"}
    objects["FIX-need"]["disposition"] = {"status": "pending", "reason": "尚未处理原有需求", "commitment_refs": []}
    snapshot["objects"].extend(copy.deepcopy(goal_fixture()["sources"]))
    strategy_snapshot, _ = strategy_fixture()
    strategy_objects = [copy.deepcopy(o) for o in strategy_snapshot["objects"] if o["id"] in {"FIX-b3c-grant", "FIX-b3c-work"}]
    for obj in strategy_objects:
        if obj["type"] == "AuthorizationGrant":
            obj["validity"] = fact("known", value={"active": True})
    snapshot["objects"].extend(strategy_objects)
    judgment.update(id=JUDGMENT)
    assessment_context["material_context"] = copy.deepcopy(context)
    return snapshot, artifacts, context, judgment, assessment_context


def envelope(state_revision, steps):
    return {"entry_version": VERSION, "synthetic_only": True,
            "expected_state_revision": state_revision, "steps": steps}


def step(identifier, operation, request, bindings=None):
    result = {"id": identifier, "operation": operation, "request": copy.deepcopy(request)}
    if bindings:
        result["bindings"] = copy.deepcopy(bindings)
    return result


def teach(action, context, **fields):
    return {"synthetic_only": True, "action": action,
            "activity_ref": {"id": "FIX-activity", "revision": 1},
            "authorization_refs": [{"id": GRANT_ID, "revision": 1}],
            "context": copy.deepcopy(context), **fields}


def initial(context):
    request = initial_request(operation_id="FIX-b5-initial")
    request.pop("expected_state_revision")
    request.update(context=copy.deepcopy(context), prior_exposures=[],
                   timeline_completeness=fact("known", value=True), active_minutes=.5,
                   actual_resources=fact("known", value=["题面给定前提"]),
                   initial_response={"content": "P 成立且 P→Q，所以 Q。", "visibility": "displayed",
                       "target_operations": ["connect-P-to-Q"], "substituted_operations": [],
                       "time": fact("unknown", "人工演示没有真实答题时间。")})
    artifact_path = request["original_response"]["path"]
    request["artifacts"][artifact_path] = "# B4-initial\nP 成立且 P→Q，所以 Q。\n"
    return request


def judgment_packet(judgment, context):
    candidate = copy.deepcopy(judgment)
    candidate["event_refs"] = [None]
    candidate["basis_refs"] = [r for r in candidate["basis_refs"] if r.get("id") != "FIX-event"] + [None]
    candidate["conditions"]["response_points"] = [{"event_ref": None, "sequence": None}]
    return candidate, copy.deepcopy(context)


def event_bindings(prefix, candidate):
    return {prefix + "/event_refs/0": {"step": "initial", "path": "/event_ref"},
            prefix + f"/basis_refs/{len(candidate['basis_refs']) - 1}": {"step": "initial", "path": "/event_ref"},
            prefix + "/conditions/response_points/0/event_ref": {"step": "initial", "path": "/assessment_handoff/event_ref"},
            prefix + "/conditions/response_points/0/sequence": {"step": "initial", "path": "/assessment_handoff/response_point/sequence"}}


def flow_request(state_revision=1):
    snapshot, _, context, judgment, assessment_context = fixture()
    goal = next(o for o in snapshot["objects"] if o["id"] == "FIX-goal")
    first = initial(context)
    first["actual_resources"] = fact("known", value=list(goal["allowed_resources"]))
    candidate, assessment_context = judgment_packet(judgment, assessment_context)
    inspect = {"judgment": candidate, "context": assessment_context}
    grant = candidate["authorization_ref"]
    submit = {"operation_id": "FIX-b5-judgment-save", "changes": [copy.deepcopy(candidate)],
              "contexts": {candidate["id"]: copy.deepcopy(assessment_context)},
              "authorization_refs": [grant], "adoption_refs": [grant], "artifacts": {}}
    close = teach("close", context, operation_id="FIX-b5-close", event_ref=None,
        checkpoint_id=CHECKPOINT, stop_reason="人工会话收束，专业采用和需求处置仍单独记录。",
        next_connection="原有需求由 AG1 明确处置；不自动追加学习工作。", pending_owners=["AG1", "AG3"],
        unrecorded_actions=fact("unknown", "未保存动作不推断。"), active_minutes=.75,
        unfinished_requirement_ids=["infer-Q"], closure={"status": "unfinished", "reason": "当前判断候选尚未专业采用。"},
        existing_need_ref={"id": "FIX-need", "revision": 1})
    accept = planning_request(operation_id="FIX-b5-accept", action="accept",
        decisions=[decision(status="pending")], checkpoint_ref=None,
        spent_minutes=fact("known", value={"minutes": .75, "basis": "observed", "source": "人工声明累计投入。"}))
    accept.pop("expected_state_revision")
    dispose = copy.deepcopy(accept)
    dispose.update(operation_id="FIX-b5-dispose", action="dispose", decisions=[decision(revision=2, status="deferred")])
    dispose["decisions"][0]["need_ref"] = None
    resume = teach("resume", context, checkpoint_ref=None)
    return envelope(state_revision, [
        step("initial", "teaching.run", first),
        step("review", "assessment.inspect", inspect, event_bindings("/judgment", candidate)),
        step("judgment", "assessment.submit", submit, event_bindings("/changes/0", candidate)),
        step("close", "teaching.run", close, {"/event_ref": {"step": "initial", "path": "/event_ref"}}),
        step("accept", "planning.run", accept, {"/checkpoint_ref": {"step": "close", "path": "/checkpoint_ref"}}),
        step("dispose", "planning.run", dispose, {"/decisions/0/need_ref": {"step": "accept", "path": "/output_refs/0"},
             "/checkpoint_ref": {"step": "close", "path": "/checkpoint_ref"}}),
        step("resume", "teaching.run", resume, {"/checkpoint_ref": {"step": "close", "path": "/checkpoint_ref"}}),
    ])


def new_goal_fixture():
    """Bootstrap permissions only; sources and the goal must cross the entry."""
    base, *_ = fixture()
    original = next(o for o in base["objects"] if o["id"] == "FIX-user-grant")
    design_grant = copy.deepcopy(original)
    design_grant.update(id="FIX-b5-new-goal-grant", decision_types=["goal_design"], criterion_refs=[],
        budget_ref=fact("not_applicable", "这里只保存人工目标声明，没有教学投入承诺。"))
    material_grant = copy.deepcopy(design_grant)
    material_grant.update(id="FIX-b5-new-source-grant", grantee="AG2", decision_types=["material_read"])
    snapshot = {"synthetic_only": True, "fixture_id": "B5-new-goal-permissions-only",
        "description": "只引导两项人工授权；来源与目标不能通过bootstrap预存。",
        "objects": [design_grant, material_grant]}
    package = goal_fixture()
    source_request = {"operation_id": "FIX-b5-new-goal-sources", "package": copy.deepcopy(package),
        "changes": copy.deepcopy(package["sources"]), "authorization_refs": [ref(material_grant)],
        "adoption_refs": [ref(material_grant)]}
    goal = copy.deepcopy(package["goal"])
    goal.update(decision_type="goal_design", authorization_ref=ref(design_grant),
        adoption={"status": "adopted", "by": "AG1", "scope": "人工近期目标", "basis_refs": [ref(design_grant)],
            "limitations": ["显式人工采用声明；未认证真实来源或学习效果。"],
            "time": fact("not_executed", "虚构记录没有真实采用时间。")})
    goal_request = {"operation_id": "FIX-b5-new-goal-save", "package": copy.deepcopy(package),
        "changes": [goal], "authorization_refs": [ref(design_grant)], "adoption_refs": [ref(design_grant)]}
    return snapshot, package, source_request, goal_request


class B5EntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pl-b5-entry-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "workspace"
        self.snapshot, self.artifacts, self.context, self.judgment, self.assessment_context = fixture()
        self.store = LearningStore(self.workspace, entry_actor="AG0")
        self.assertEqual(self.store.init_workspace()["status"], "committed")
        self.assertEqual(self.store.import_fixture(self.snapshot, self.artifacts)["status"], "committed")
        self.entry = PersonalLearningEntry(self.store)

    def state(self):
        return self.store.read_context()

    def objects(self):
        return {o["id"]: o for o in self.state()["objects"]}

    def execute(self, steps):
        return self.entry.execute(envelope(self.state()["state_revision"], steps))

    def completed(self, result):
        self.assertEqual(result["status"], "completed", result)
        return result

    def unchanged(self, packet):
        before = self.state()
        result = self.entry.execute(packet)
        self.assertNotEqual(result["status"], "completed", result)
        self.assertFalse(result.get("mutated", False), result)
        self.assertEqual(self.state(), before)
        return result

    def test_public_single_entry_saves_judgment_checkpoint_need_disposition_and_reopens(self):
        before = self.objects()
        result = self.completed(self.entry.execute(flow_request(self.state()["state_revision"])))
        objects = self.objects()
        self.assertTrue(result["mutated"])
        self.assertEqual([r["id"] for r in result["steps"]], ["initial", "review", "judgment", "close", "accept", "dispose", "resume"])
        self.assertEqual(objects[EVENT_ID]["independent_sample_id"], "FIX-b4-sample")
        self.assertEqual(len([o for o in objects.values() if o["type"] == "PerformanceEvent"]),
                         len([o for o in before.values() if o["type"] == "PerformanceEvent"]) + 1)
        self.assertEqual(objects[JUDGMENT]["support"], "supported")
        self.assertEqual(objects[JUDGMENT]["adoption"]["status"], "candidate")
        self.assertEqual(objects["FIX-need"]["acceptance"]["status"], "accepted")
        self.assertEqual(objects["FIX-need"]["disposition"]["status"], "deferred")
        self.assertEqual(objects["FIX-goal"], before["FIX-goal"])
        self.assertEqual(objects["FIX-budget"], before["FIX-budget"])
        self.assertEqual(objects[CHECKPOINT]["last_trusted_event_ref"], ref(objects[EVENT_ID]))
        self.assertTrue(any(item["event_ref"] == ref(objects[EVENT_ID]) for item in result["user_view"]["activity_facts"]))
        self.assertTrue(any(item["judgment_ref"] == ref(objects[JUDGMENT]) for item in result["user_view"]["conditional_support"]))
        reopened = PersonalLearningEntry(LearningStore(self.workspace, entry_actor="AG0"))
        saved_revision = self.state()["state_revision"]
        again = reopened.execute(envelope(saved_revision, [step("resume", "teaching.run", teach("resume", self.context,
            checkpoint_ref=ref(objects[CHECKPOINT])))]))
        self.completed(again)
        recovery = again["steps"][0]["result"]["recovery"]
        self.assertEqual(recovery["last_trusted_event_ref"], ref(objects[EVENT_ID]))
        self.assertEqual(recovery["unrecorded_actions"]["status"], "unknown")
        self.assertFalse(again["mutated"])
        self.assertEqual(self.state()["state_revision"], saved_revision)
        self.assertEqual(self.store.check_integrity()["status"], "ok")

    def test_read_only_open_exposes_only_learner_packet_and_preserves_state(self):
        before = self.state()
        result = self.completed(self.execute([step("open", "teaching.run", teach("open", self.context))]))
        self.assertFalse(result["mutated"])
        self.assertEqual(self.state(), before)
        serialized = json.dumps(result["user_view"], ensure_ascii=False)
        self.assertNotIn("B3B-TEACHER-SECRET", serialized)
        self.assertNotIn("B3B-BACKUP-SECRET", serialized)
        self.assertNotIn("teacher_reference", serialized)

    def test_supported_candidate_is_visible_without_becoming_adopted_or_mastery(self):
        result = self.completed(self.entry.execute(flow_request(self.state()["state_revision"])))
        view = json.dumps(result["user_view"], ensure_ascii=False)
        self.assertIn("supported", view)
        self.assertIn("candidate", view)
        self.assertIn("deferred", view)
        self.assertNotIn("mastery", view)

    def test_same_need_pending_is_removed_only_after_real_disposition(self):
        packet = flow_request(self.state()["state_revision"])
        packet["steps"] = packet["steps"][:5]
        accepted = self.completed(self.entry.execute(packet))
        pending = [item for item in accepted["pending"] if item.get("existing_need_ref", {}).get("id") == "FIX-need"]
        self.assertEqual(len(pending), 1, accepted)
        self.assertEqual(pending[0]["owner"], "AG1")
        self.assertTrue(pending[0]["next_trigger"])
        self.assertEqual(self.objects()["FIX-need"]["disposition"]["status"], "pending")
        workspace = Path(self.temp.name) / "fully-disposed"
        store = LearningStore(workspace, entry_actor="AG0")
        self.assertEqual(store.init_workspace()["status"], "committed")
        self.assertEqual(store.import_fixture(self.snapshot, self.artifacts)["status"], "committed")
        disposed = self.completed(PersonalLearningEntry(store).execute(flow_request(store.read_context()["state_revision"])))
        self.assertFalse(any(item.get("existing_need_ref", {}).get("id") == "FIX-need" for item in disposed["pending"]), disposed)
        need = next(item for item in disposed["user_view"]["learning_needs"] if item["need_ref"]["id"] == "FIX-need")
        self.assertEqual(need["disposition"]["status"], "deferred")

    def test_new_goal_review_user_view_does_not_include_unrelated_existing_need(self):
        result = self.completed(self.execute([step("new-goal", "goal.review", {"package": goal_fixture()})]))
        self.assertEqual(result["user_view"]["learning_needs"], [])
        self.assertNotIn("FIX-need", json.dumps(result["user_view"]))
        self.assertIn("FIX-need", self.objects())

    def test_failure_preserves_saved_prefix_and_returns_responsibility_without_payload(self):
        packet = flow_request(self.state()["state_revision"])
        packet["steps"][1]["request"]["judgment"]["conditions"]["operation_findings"][0]["operation"] = "INVALID-PROFESSIONAL-SECRET"
        result = self.entry.execute(packet)
        self.assertEqual(result["status"], "partial", result)
        self.assertTrue(result["mutated"])
        self.assertIn(EVENT_ID, self.objects())
        self.assertNotIn(JUDGMENT, self.objects())
        self.assertNotIn(CHECKPOINT, self.objects())
        self.assertEqual(len(result["steps"]), 2)
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("INVALID-PROFESSIONAL-SECRET", serialized)
        self.assertIn("AG3", serialized)
        self.assertIn("next_trigger", serialized)

    def test_stale_root_cas_rejects_before_first_write(self):
        self.unchanged(flow_request(self.state()["state_revision"] - 1))

    def test_pause_blocks_entry_and_does_not_lift_control(self):
        self.assertEqual(self.store.pause(self.state()["state_revision"], "FIX-b5-pause", ["FIX-activity"], "人工暂停")["status"], "committed")
        self.unchanged(flow_request(self.state()["state_revision"]))
        self.assertIn("FIX-activity", self.state()["controls"]["paused_ids"])

    def test_deleted_material_cannot_be_revived_by_single_entry(self):
        self.assertEqual(self.store.delete_scope(self.state()["state_revision"], "FIX-b5-delete", ["FIX-material"])["status"], "committed")
        self.unchanged(flow_request(self.state()["state_revision"]))
        self.assertNotIn("FIX-material", self.objects())

    def test_restriction_blocks_new_teaching_without_erasing_history(self):
        self.assertEqual(self.store.restrict(self.state()["state_revision"], "FIX-b5-restrict", ["FIX-material"], "人工参考复核", ["teaching_execution"])["status"], "committed")
        self.unchanged(flow_request(self.state()["state_revision"]))
        self.assertIn("FIX-event", self.objects())

    def test_structural_errors_preflight_all_steps_before_mutation(self):
        for mutate in (
            lambda p: p["steps"][1].update(operation="execute_arbitrary_code"),
            lambda p: p["steps"][1]["request"].update(actor="AG1"),
            lambda p: p["steps"][1]["request"].update(expected_state_revision=1),
            lambda p: p["steps"][1].update(id="initial"),
            lambda p: p["steps"][0]["request"].pop("operation_id"),
        ):
            with self.subTest(mutation=mutate):
                packet = flow_request(self.state()["state_revision"])
                mutate(packet)
                self.unchanged(packet)

    def test_forward_missing_and_forbidden_bindings_are_preflight_rejected(self):
        for target, source in (
            ("/judgment/event_refs/0", {"step": "close", "path": "/event_ref"}),
            ("/does_not_exist", {"step": "initial", "path": "/event_ref"}),
            ("/operation_id", {"step": "initial", "path": "/event_ref"}),
        ):
            with self.subTest(target=target, source=source):
                packet = flow_request(self.state()["state_revision"])
                packet["steps"][1]["bindings"][target] = source
                self.unchanged(packet)

    def test_missing_result_binding_stops_after_successful_prefix(self):
        packet = flow_request(self.state()["state_revision"])
        packet["steps"][1]["bindings"]["/judgment/event_refs/0"]["path"] = "/not_a_saved_result"
        result = self.entry.execute(packet)
        self.assertEqual(result["status"], "partial", result)
        self.assertIn(EVENT_ID, self.objects())
        self.assertNotIn(JUDGMENT, self.objects())

    def test_failed_transaction_never_produces_unsaved_handoff(self):
        before = self.state()
        with patch.object(LearningStore, "commit", return_value={"status": "not_saved", "reasons": [{"code": "fixture_save_failure"}]}):
            result = self.entry.execute(flow_request(before["state_revision"]))
        self.assertNotEqual(result["status"], "completed", result)
        self.assertFalse(result["mutated"])
        self.assertEqual(self.state(), before)
        self.assertNotIn("event_ref", result["steps"][0]["result"])
        self.assertEqual(len(result["steps"]), 1)

    def test_ag0_routine_path_cannot_make_important_professional_judgment(self):
        candidate = copy.deepcopy(self.judgment)
        candidate.update(owner="AG0", decision_type="routine_scoring",
                         authorization_ref={"id": "FIX-scoring-grant", "revision": 1})
        context = copy.deepcopy(self.assessment_context)
        context["review_triggers"] = ["complex_product"]
        result = self.execute([step("routine", "assessment.routine_inspect", {"judgment": candidate, "context": context})])
        self.assertNotEqual(result["status"], "completed", result)
        self.assertIn("important_review_required", json.dumps(result))
        self.assertNotIn(JUDGMENT, self.objects())

    def test_displayed_prior_help_limits_judgment_and_preserves_same_sample(self):
        packet = flow_request(self.state()["state_revision"])
        packet["steps"] = packet["steps"][:3]
        packet["steps"][0]["request"]["prior_exposures"] = [{"content": "人工先前帮助给出了 P 到 Q 的连接。", "visibility": "displayed",
            "target_operations": ["connect-P-to-Q"], "substituted_operations": ["connect-P-to-Q"],
            "time": fact("unknown", "人工帮助顺序没有真实时间。")}]
        for item, path in ((packet["steps"][1], "judgment"), (packet["steps"][2], "changes")):
            candidate = item["request"][path] if path == "judgment" else item["request"][path][0]
            candidate.update(support="unknown", eligibility="pending_review", conclusion="local-unknown")
        result = self.entry.execute(packet)
        # A limited professional result is either retained as limited or stops
        # for explicit review; it must never upgrade to independent support.
        self.assertIn(result["status"], {"completed", "partial"}, result)
        reviewed = result["steps"][1]["result"]
        self.assertEqual(reviewed["expected_support"], "unknown")
        event = self.objects()[EVENT_ID]
        self.assertEqual(len(event["timeline"]), 2)
        self.assertEqual(event["independent_sample_id"], "FIX-b4-sample")
        self.assertEqual(len([o for o in self.objects().values() if o["id"] == EVENT_ID]), 1)
        if JUDGMENT in self.objects():
            self.assertEqual(self.objects()[JUDGMENT]["support"], "unknown")

    def test_accepting_existing_need_keeps_pending_and_does_not_create_plan(self):
        request = planning_request(action="accept", operation_id="FIX-b5-accept-only", decisions=[decision(status="pending")], checkpoint_ref=None)
        request.pop("expected_state_revision")
        before = self.objects()
        self.completed(self.execute([step("accept", "planning.run", request)]))
        after = self.objects()
        self.assertEqual(after["FIX-need"]["acceptance"]["status"], "accepted")
        self.assertEqual(after["FIX-need"]["disposition"]["status"], "pending")
        self.assertTrue(after["FIX-need"]["acceptance"]["next_trigger"])
        self.assertEqual(set(after), set(before))

    def test_candidate_goal_review_does_not_save_or_adopt(self):
        before = self.state()
        package = goal_fixture()
        result = self.completed(self.execute([step("goal", "goal.review", {"package": package})]))
        reviewed = result["steps"][0]["result"]
        self.assertEqual(reviewed["review_state"], "complete")
        self.assertEqual(self.state(), before)
        self.assertNotIn(package["goal"]["id"], self.objects())

    def test_same_canonical_sources_cross_goal_and_material_public_entry(self):
        snapshot, _legacy, source_request, goal_request = new_goal_fixture()
        package = canonical_fixture()
        source_request.update(package=copy.deepcopy(package), changes=copy.deepcopy(package["sources"]))
        goal_request["package"] = copy.deepcopy(package)
        workspace = Path(self.temp.name) / "canonical-source-pipeline"
        store = LearningStore(workspace, entry_actor="AG0")
        self.assertEqual(store.init_workspace()["status"], "committed")
        self.assertEqual(store.import_fixture(snapshot, {})["status"], "committed")
        entry = PersonalLearningEntry(store)
        result = entry.execute(envelope(1, [
            step("sources", "goal.sources_submit", source_request),
            step("goal", "goal.submit", goal_request),
        ]))
        self.assertEqual(result["status"], "completed", result)
        # A material-stage source revision retains the same explicit modalities.
        material_request = copy.deepcopy(source_request)
        material_request.pop("package")
        material_request["operation_id"] = "FIX-b5-canonical-material-source"
        for source in material_request["changes"]:
            source["revision"] = 2
            source["verification"]["content"]["checked_revision"] = 2
            source["verification"]["content"]["anchor_refs"][0]["revision"] = 2
        result = entry.execute(envelope(store.read_context()["state_revision"], [
            step("prepare-sources", "materials.submit", material_request),
        ]))
        self.assertEqual(result["status"], "completed", result)
        for original in package["sources"]:
            saved = store.read_refs([{ "id": original["id"], "revision": 2}])["objects"][0]
            self.assertEqual(saved["read_scope"], original["read_scope"])
            self.assertEqual(saved["read_scope"]["formula"]["status"], "unknown")
            self.assertEqual(saved["read_scope"]["figure"]["status"], "unknown")

    def test_canonical_goal_sources_support_material_use_without_rewriting_source_facts(self):
        snapshot, _legacy, source_request, goal_request = new_goal_fixture()
        package = canonical_fixture()
        design_grant, material_grant = snapshot["objects"]
        design_grant["decision_types"].append("teaching_design")
        material_grant["decision_types"].extend(["material_review", "material_use"])
        budget = copy.deepcopy(next(o for o in self.snapshot["objects"] if o["id"] == "FIX-budget"))
        budget.update(basis_refs=[ref(design_grant)], authorization_ref=ref(design_grant))
        snapshot["objects"].append(budget)
        source_request.update(package=copy.deepcopy(package), changes=copy.deepcopy(package["sources"]))
        goal_request["package"] = copy.deepcopy(package)
        workspace = Path(self.temp.name) / "canonical-material-use"
        store = LearningStore(workspace, entry_actor="AG0")
        self.assertEqual(store.init_workspace()["status"], "committed")
        self.assertEqual(store.import_fixture(snapshot, {})["status"], "committed")
        entry = PersonalLearningEntry(store)
        prepared = entry.execute(envelope(1, [
            step("sources", "goal.sources_submit", source_request),
            step("goal", "goal.submit", goal_request),
        ]))
        self.assertEqual(prepared["status"], "completed", prepared)
        goal_ref = ref(package["goal"])
        source_ref = ref(package["sources"][1])
        activity = copy.deepcopy(next(o for o in self.snapshot["objects"] if o["id"] == "FIX-activity"))
        # This is a material-preparation candidate, not an executable teaching
        # task: task/criterion authority will be bound in the teaching workflow.
        activity.update(id="FIX-canonical-activity", basis_refs=[goal_ref, source_ref],
            goal_refs=[goal_ref], criterion_refs=[], material_refs=[], reference_refs=[source_ref],
            learner_operations=list(package["goal"]["requirements"][0]["key_operations"]),
            branches=[], authority_refs=[ref(design_grant)],
            prompt="人工阈值规则：自行实现当前规则，保留等于边界。",
            adoption={"status": "candidate"}, metadata={})
        store.entry_actor = "AG1"
        saved_activity = store.commit(store.read_context()["state_revision"], "FIX-canonical-activity-save", [activity],
            authorization_refs=[ref(design_grant)], adoption_refs=[ref(design_grant)])
        self.assertEqual(saved_activity["status"], "committed", saved_activity)
        store.entry_actor = "AG0"
        material = copy.deepcopy(next(o for o in self.snapshot["objects"] if o["id"] == "FIX-material"))
        context = {"goal_refs": [goal_ref], "activity_ref": ref(activity), "intended_use": "independent_check",
            "purpose": "independent", "required_modalities": ["text"],
            "conditions": ["人工有限阈值规则；关键分支由学习者完成"]}
        material.update(id="FIX-canonical-material", basis_refs=[source_ref], goal_refs=[goal_ref],
            fragment_refs=[source_ref], visible_input=[{"content": "人工任务说明与允许资源。",
                "provided_operations": [], "channel": "body"}], backup_help=[], teacher_reference=[])
        material["verification"]["content"].update(scope="人工文本阈值规则的材料候选", domain="general",
            conditions=list(context["conditions"]), anchor_refs=[source_ref],
            domain_checks={key: fact("known", value="人工显式有限文本核验声明")
                for key in ("source_fidelity", "conditions", "scope")})
        material["verification"]["use"].update(conditions=list(context["conditions"]), binding=copy.deepcopy(context))
        result = entry.execute(envelope(store.read_context()["state_revision"], [
            step("inspect", "materials.inspect", {"material": material, "context": context}),
            step("material", "materials.submit", {"operation_id": "FIX-canonical-material-save",
                "changes": [material], "context": context,
                "authorization_refs": [ref(material_grant)], "adoption_refs": [ref(material_grant)]}),
        ]))
        self.assertEqual(result["status"], "completed", result)
        self.assertEqual(result["steps"][0]["result"]["status"], "compatible")
        self.assertEqual(result["steps"][1]["result"]["status"], "committed")
        for source in package["sources"]:
            saved = store.read_refs([ref(source)])["objects"][0]
            self.assertEqual(saved, source, "目标与材料检查不得悄悄改写来源事实")
        persisted = store.read_refs([ref(material)])["objects"][0]
        self.assertEqual(persisted["verification"]["use"]["binding"], context)
        self.assertEqual(persisted["actual_exposure"]["status"], "unknown")

    def test_legacy_goal_source_requires_explicit_material_modality_completion(self):
        store, package, source_request, goal_request = self.new_goal_store("legacy-source-boundary")
        entry = PersonalLearningEntry(store)
        result = entry.execute(envelope(1, [
            step("sources", "goal.sources_submit", source_request),
            step("goal", "goal.submit", goal_request),
        ]))
        self.assertEqual(result["status"], "completed", result)
        before = store.read_context()
        request = copy.deepcopy(source_request)
        request.pop("package")
        request["operation_id"] = "FIX-legacy-material-source"
        request["changes"] = [{**source, "revision": 2} for source in request["changes"]]
        result = entry.execute(envelope(before["state_revision"], [step("materials", "materials.submit", request)]))
        self.assertEqual(result["status"], "rejected", result)
        self.assertIn("modality_facts_required", {item["code"] for item in result["steps"][0]["result"]["reasons"]})
        self.assertEqual(store.read_context(), before)
        for source in package["sources"]:
            self.assertEqual(store.read_refs([ref(source)])["objects"][0], source)

    def test_goal_submit_rejects_changed_criterion_without_saving_candidate(self):
        package = goal_fixture()
        changed = copy.deepcopy(package["goal"])
        changed["requirements"][0]["criterion"]["text"] = "TAMPERED-CRITERION"
        packet = envelope(self.state()["state_revision"], [step("goal", "goal.submit", {"package": package,
            "operation_id": "FIX-b5-goal-tamper", "changes": [*package["sources"], changed],
            "authorization_refs": [{"id": "FIX-user-grant", "revision": 1}], "adoption_refs": []})])
        self.unchanged(packet)

    def test_goal_submit_saves_legacy_candidate_without_manufacturing_adoption(self):
        package = goal_fixture()
        candidate = copy.deepcopy(package["goal"])
        grant = {"id": "FIX-user-grant", "revision": 1}
        result = self.completed(self.execute([step("goal", "goal.submit", {"package": package,
            "operation_id": "FIX-b5-goal-legacy", "changes": [candidate],
            "authorization_refs": [grant], "adoption_refs": [grant]})]))
        self.assertTrue(result["mutated"])
        saved = self.objects()[candidate["id"]]
        self.assertEqual(saved, candidate)
        self.assertNotIn("adoption", saved)
        self.assertEqual(review_goal_package(package)["boundaries"]["professional_adoption"], "not_executed")

    def test_goal_submit_preserves_explicit_authorized_adoption(self):
        package = goal_fixture()
        adopted = copy.deepcopy(package["goal"])
        grant = {"id": "FIX-user-grant", "revision": 1}
        adopted.update(decision_type="goal_design", authorization_ref=grant,
            adoption={"status": "adopted", "by": "AG1", "scope": "人工近期目标", "basis_refs": [grant],
                "limitations": ["人工采用声明；非真实认证。"], "time": fact("not_executed", "人工记录没有真实采用时间。")})
        self.completed(self.execute([step("goal", "goal.submit", {"package": package,
            "operation_id": "FIX-b5-goal-adopted", "changes": [adopted],
            "authorization_refs": [grant], "adoption_refs": [grant]})]))
        self.assertEqual(self.objects()[adopted["id"]], adopted)

    def test_planning_only_grant_cannot_create_goal_by_declaring_planning_decision(self):
        snapshot = copy.deepcopy(self.snapshot)
        grant = copy.deepcopy(next(o for o in snapshot["objects"] if o["id"] == "FIX-user-grant"))
        grant.update(id="FIX-b5-planning-only-grant", decision_types=["planning"])
        snapshot["objects"].append(grant)
        workspace = Path(self.temp.name) / "planning-only"
        store = LearningStore(workspace, entry_actor="AG0")
        self.assertEqual(store.init_workspace()["status"], "committed")
        self.assertEqual(store.import_fixture(snapshot, self.artifacts)["status"], "committed")
        package = goal_fixture()
        candidate = copy.deepcopy(package["goal"])
        candidate["decision_type"] = "planning"
        grant_ref = ref(grant)
        before = store.read_context()
        result = PersonalLearningEntry(store).execute(envelope(before["state_revision"], [step("goal", "goal.submit", {
            "package": package, "operation_id": "FIX-b5-goal-wrong-decision", "changes": [candidate],
            "authorization_refs": [grant_ref], "adoption_refs": [grant_ref]})]))
        self.assertNotEqual(result["status"], "completed", result)
        self.assertIn("professional_decision_type_mismatch", json.dumps(result))
        self.assertEqual(store.read_context(), before)
        self.assertNotIn(candidate["id"], {o["id"] for o in store.read_context()["objects"]})

    def test_unhashable_operation_and_teaching_action_return_rejected_json(self):
        for invalid in ("operation", "action"):
            with self.subTest(field=invalid):
                packet = flow_request(self.state()["state_revision"])
                if invalid == "operation":
                    packet["steps"][0]["operation"] = []
                else:
                    packet["steps"][0]["request"]["action"] = []
                result = self.unchanged(packet)
                self.assertEqual(result["status"], "rejected", result)
                json.dumps(result, ensure_ascii=False)

    def test_goal_review_cannot_replace_saved_source_with_changed_declaration(self):
        package = goal_fixture()
        package["sources"][0]["verification"]["value"]["scope"] = "FORGED-SAVED-SOURCE-CLAIM"
        result = self.unchanged(envelope(self.state()["state_revision"], [step("goal", "goal.review", {"package": package})]))
        self.assertIn("candidate_definition_differs_from_saved", json.dumps(result))
        self.assertNotIn("FORGED-SAVED-SOURCE-CLAIM", json.dumps(result))

    def new_goal_store(self, name):
        snapshot, package, source_request, goal_request = new_goal_fixture()
        store = LearningStore(Path(self.temp.name) / name, entry_actor="AG0")
        self.assertEqual(store.init_workspace()["status"], "committed")
        self.assertEqual(store.import_fixture(snapshot, {})["status"], "committed")
        self.assertEqual(len(store.read_context()["objects"]), 2)
        self.assertTrue(all(o["type"] == "AuthorizationGrant" for o in store.read_context()["objects"]))
        return store, package, source_request, goal_request

    def test_new_goal_sources_and_adopted_goal_are_both_saved_through_entry(self):
        store, package, source_request, goal_request = self.new_goal_store("new-goal-positive")
        entry = PersonalLearningEntry(store)
        before = store.read_context()
        result = self.completed(entry.execute(envelope(before["state_revision"], [
            step("review", "goal.review", {"package": package}),
            step("sources", "goal.sources_submit", source_request),
            step("goal", "goal.submit", goal_request),
        ])))
        self.assertEqual([item["owner"] for item in result["steps"]], ["AG1", "AG2", "AG1"])
        self.assertEqual([item["stage"] for item in result["steps"]], ["candidate", "saved", "saved"])
        self.assertEqual(result["state_revision"], before["state_revision"] + 2)
        self.assertEqual(result["steps"][0]["result"]["boundaries"]["content_verification"], "not_executed")
        objects = {o["id"]: o for o in store.read_context()["objects"]}
        for source in package["sources"]:
            self.assertEqual(objects[source["id"]], source)
            self.assertIn(ref(source), result["steps"][1]["result"]["output_refs"])
        self.assertEqual(objects[package["goal"]["id"]], goal_request["changes"][0])
        self.assertIn(ref(goal_request["changes"][0]), result["steps"][2]["result"]["output_refs"])
        self.assertEqual(store.check_integrity()["status"], "ok")

    def test_goal_source_bridge_rejects_changed_source_or_goal_payload(self):
        for invalid in ("source", "goal"):
            with self.subTest(payload=invalid):
                store, package, source_request, _ = self.new_goal_store("new-source-invalid-" + invalid)
                if invalid == "source":
                    source_request["changes"][0]["claims"] = ["FORGED-BRIDGE-SOURCE"]
                else:
                    source_request["changes"].append(copy.deepcopy(package["goal"]))
                before = store.read_context()
                result = PersonalLearningEntry(store).execute(envelope(before["state_revision"], [
                    step("sources", "goal.sources_submit", source_request)]))
                self.assertNotEqual(result["status"], "completed", result)
                self.assertIn("reviewed_goal_sources_only", json.dumps(result))
                self.assertNotIn("FORGED-BRIDGE-SOURCE", json.dumps(result))
                self.assertEqual(store.read_context(), before)

    def test_goal_source_bridge_requires_ag2_authorization(self):
        store, _package, source_request, goal_request = self.new_goal_store("new-source-no-auth")
        source_request["authorization_refs"] = goal_request["authorization_refs"]
        source_request["adoption_refs"] = goal_request["adoption_refs"]
        before = store.read_context()
        result = PersonalLearningEntry(store).execute(envelope(before["state_revision"], [
            step("sources", "goal.sources_submit", source_request)]))
        self.assertNotEqual(result["status"], "completed", result)
        self.assertIn("authorization_scope", json.dumps(result))
        self.assertEqual(store.read_context(), before)

    def test_deleted_goal_source_cannot_be_reintroduced_by_old_bridge_request(self):
        store, package, source_request, _ = self.new_goal_store("new-source-delete")
        entry = PersonalLearningEntry(store)
        self.completed(entry.execute(envelope(store.read_context()["state_revision"], [
            step("sources", "goal.sources_submit", source_request)])))
        source = package["sources"][0]
        self.assertEqual(store.delete_scope(store.read_context()["state_revision"], "FIX-b5-new-source-delete", [source["id"]])["status"], "committed")
        before = store.read_context()
        result = entry.execute(envelope(before["state_revision"], [step("sources", "goal.sources_submit", source_request)]))
        self.assertNotEqual(result["status"], "completed", result)
        self.assertFalse(result["mutated"])
        self.assertEqual(store.read_context(), before)
        self.assertIn(source["id"], before["controls"]["deleted_ids"])
        self.assertNotIn(source["id"], {o["id"] for o in store.read_context()["objects"]})

    def test_need_submit_keeps_proposed_pending_and_uses_shared_record_only(self):
        candidate = copy.deepcopy(self.objects()["FIX-need"])
        candidate.update(id="FIX-b5-new-need", revision=1, owner="AG1")
        grant = {"id": "FIX-user-grant", "revision": 1}
        self.completed(self.execute([step("need", "need.submit", {"operation_id": "FIX-b5-new-need-save",
            "changes": [candidate], "authorization_refs": [grant], "adoption_refs": [grant]})]))
        saved = self.objects()[candidate["id"]]
        self.assertEqual(saved["acceptance"]["status"], "proposed")
        self.assertEqual(saved["disposition"]["status"], "pending")
        self.assertEqual(saved["assignee"], "AG1")
        self.assertFalse(any(o["type"] == "PlanCommitment" and o.get("status") == "active" for o in self.objects().values()))

    def test_need_submit_rejects_automatic_acceptance_or_scheduling(self):
        candidate = copy.deepcopy(self.objects()["FIX-need"])
        candidate.update(id="FIX-b5-invalid-need", revision=1, owner="AG1")
        candidate["acceptance"]["status"] = "accepted"
        self.unchanged(envelope(self.state()["state_revision"], [step("need", "need.submit", {
            "operation_id": "FIX-b5-invalid-need-save", "changes": [candidate],
            "authorization_refs": [], "adoption_refs": []})]))

    def test_need_submit_cannot_reset_existing_accepted_or_scheduled_need(self):
        for action, disposition in (("accept", "pending"), ("schedule", "scheduled")):
            with self.subTest(action=action):
                workspace = Path(self.temp.name) / ("need-reset-" + action)
                store = LearningStore(workspace, entry_actor="AG0")
                self.assertEqual(store.init_workspace()["status"], "committed")
                self.assertEqual(store.import_fixture(self.snapshot, self.artifacts)["status"], "committed")
                entry = PersonalLearningEntry(store)
                request = planning_request(action=action, operation_id="FIX-b5-establish-" + action,
                    decisions=[decision(status=disposition)], checkpoint_ref=None)
                request.pop("expected_state_revision")
                self.completed(entry.execute(envelope(store.read_context()["state_revision"], [step("establish", "planning.run", request)])))
                before = store.read_context()
                candidate = copy.deepcopy(next(o for o in before["objects"] if o["id"] == "FIX-need"))
                self.assertEqual(candidate["acceptance"]["status"], "accepted")
                self.assertEqual(candidate["disposition"]["status"], disposition)
                candidate["revision"] += 1
                candidate["acceptance"] = {"status": "proposed", "by": "AG0", "scope": "尝试回退同一已接责需求", "next_trigger": "重新接责"}
                candidate["disposition"] = {"status": "pending", "reason": "尝试丢弃实际处置", "commitment_refs": []}
                grant = {"id": "FIX-user-grant", "revision": 1}
                result = entry.execute(envelope(before["state_revision"], [step("reset", "need.submit", {
                    "operation_id": "FIX-b5-reset-" + action, "changes": [candidate],
                    "authorization_refs": [grant], "adoption_refs": [grant]})]))
                self.assertNotEqual(result["status"], "completed", result)
                self.assertIn("existing_need_requires_planning_disposition", json.dumps(result))
                self.assertEqual(store.read_context(), before)

    def test_material_read_and_inspect_remain_candidates_without_truth_upgrade(self):
        read = {"fragment_id": "FIX-b5-extracted", "source_ref": {"source_id": "FIX-B2B-REFERENCE",
            "declared_revision": "fixture/1", "locator": "b2b-reference.md#核验范围", "identity_kind": "synthetic"},
            "artifact_ref": {"path": "b2b-reference.md", "locator": "核验范围", "revision": 1, "origin": "synthetic_fixture"},
            "start_line": 3, "end_line": 4}
        before = self.state()
        result = self.completed(self.execute([step("read", "materials.read", read),
            step("material", "materials.inspect", {"material": self.objects()["FIX-material"], "context": self.context})]))
        self.assertEqual(result["steps"][0]["owner"], "AG2")
        self.assertEqual(result["steps"][0]["result"]["semantic_verification"], "not_executed")
        self.assertNotIn("OUTSIDE-BEFORE-MARKER", result["steps"][0]["result"]["text"])
        self.assertEqual(self.state(), before)
        self.assertNotIn("FIX-b5-extracted", self.objects())

    def test_adopted_method_handoff_uses_same_teaching_event(self):
        config, strategy_context = configured(StrategyCatalog())
        grant = {"id": "FIX-b3c-grant", "revision": 1}
        submit = {"operation_id": "FIX-b5-config-submit", "changes": [config], "context": strategy_context,
            "authorization_refs": [grant], "adoption_refs": config["adoption"]["basis_refs"]}
        packet = flow_request(self.state()["state_revision"])
        first = packet["steps"][0]
        first["request"].update(method_config_refs=[None], strategy_context=strategy_context)
        first["bindings"] = {"/method_config_refs/0": {"step": "method", "path": "/output_refs/0"}}
        packet["steps"] = [step("method", "strategies.submit", submit), first]
        result = self.completed(self.entry.execute(packet))
        self.assertEqual(result["steps"][0]["owner"], "AG1")
        self.assertEqual(self.objects()[EVENT_ID]["method_config_refs"], [ref(config)])
        self.assertEqual(self.objects()[config["id"]]["adoption"]["status"], "adopted")

    def test_direct_service_uses_same_public_entry_contract(self):
        before = self.state()
        packet = envelope(before["state_revision"], [step("open", "teaching.run", teach("open", self.context))])
        self.completed(SingleEntryService(self.store).execute(packet))
        self.assertEqual(self.state(), before)

    def test_saved_request_fixture_runs_the_same_explicit_handoff_chain(self):
        packet = json.loads((ROOT / "fixtures/b5-entry-request.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(packet, flow_request(1))
        self.completed(self.entry.execute(packet))
        self.assertIn(CHECKPOINT, self.objects())
        self.assertEqual(self.objects()["FIX-need"]["disposition"]["status"], "deferred")

    def test_demo_existing_workspace_is_read_only_without_reseeding_or_replay(self):
        workspace = Path(self.temp.name) / "demo-workspace"
        report = Path(self.temp.name) / "demo-first.json"
        command = [sys.executable, "-X", "utf8", str(ROOT / "scripts/demo_b5.py"),
            "--workspace", str(workspace), "--report", str(report)]
        first = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        saved_report = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(saved_report["execution"]["status"], "completed")
        saved_store = LearningStore(workspace, entry_actor="AG0")
        before = saved_store.read_context()
        second = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        repeated_report = json.loads(report.read_text(encoding="utf-8"))
        self.assertTrue(repeated_report["existing_workspace"])
        self.assertEqual(repeated_report["initialization"], [])
        self.assertIsNone(repeated_report["execution"])
        self.assertTrue(repeated_report["reopen_read_only"])
        self.assertEqual(saved_store.read_context(), before)

    def test_intent_only_returns_candidate_without_professional_work(self):
        before = self.state()
        result = self.entry.execute({"entry_version": VERSION, "synthetic_only": True,
            "expected_state_revision": before["state_revision"], "intent": "规划"})
        self.assertIn(result["status"], {"candidate", "needs_input"})
        self.assertEqual(self.state(), before)

    def test_cli_execute_emits_json_and_open_is_read_only(self):
        packet = envelope(self.state()["state_revision"], [step("open", "teaching.run", teach("open", self.context))])
        path = Path(self.temp.name) / "request.json"
        path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
        before = self.state()
        result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "src/runtime/personal_learning.py"),
            "--workspace", str(self.workspace), "execute", "--request", str(path)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)["status"], "completed")
        self.assertEqual(self.state(), before)


if __name__ == "__main__":
    unittest.main()
