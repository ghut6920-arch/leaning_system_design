"""Behavior tests for B4's finite, artificial planning slice."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from runtime.learning_planning import PlanningService, ACTIVE_COMPONENTS, fact, ref
from runtime.learning_store import LearningStore
from test_b3a_assessment import fixture as assessment_fixture, objects_by_id

PLAN = "FIX-b4-plan"
CLOSURE = "FIX-b4-supported-judgment"
ADJUST = "FIX-b4-adjustment-grant"
DUPLICATE = "FIX-b4-duplicate"


def fixture():
    snapshot, artifacts, judgment, _, _, _ = assessment_fixture()
    snapshot["fixture_id"] = "B4-synthetic-planning"
    objects = objects_by_id(snapshot)
    grant = copy.deepcopy(objects["FIX-user-grant"])
    grant.update(id=ADJUST, grantee="AG0", decision_types=["plan_adjustment"],
                 permitted_conclusions=["有限缩时和收束；不得改变目标或关键教学工作。"])
    snapshot["objects"].append(grant)
    execute = copy.deepcopy(grant)
    execute.update(id="FIX-b4-execution-grant", decision_types=["teaching_execution"])
    snapshot["objects"].append(execute)
    objects["FIX-activity"]["authority_refs"].append(ref(execute))
    objects["FIX-need"].update(
        disposition={"status": "pending", "reason": "人工候选，尚未实质处置", "commitment_refs": []},
        acceptance={"status": "proposed", "by": "AG0", "scope": "人工缺项", "next_trigger": "相关计划前处理"},
    )
    duplicate = copy.deepcopy(objects["FIX-need"])
    duplicate.update(id=DUPLICATE, requester="AG3", needed_work="同一连接的策略建议，须归并原需求")
    snapshot["objects"].append(duplicate)
    judgment.update(id=CLOSURE, intended_uses=["planning_closure", "independent_check"],
                    adoption={"status": "adopted", "by": "AG3", "scope": "infer-Q：目标条件下的原始连接",
                              "basis_refs": [ref(objects["FIX-evidence-grant"])],
                              "limitations": ["仅人工声明，未判断真实答案"], "time": fact("not_executed", "夹具采用")})
    snapshot["objects"].append(judgment)
    return snapshot, artifacts


def cost(minutes=5, basis="bounded_trial"):
    # Six categories always remain explicit, even when a category is inapplicable.
    components = dict(zip(ACTIVE_COMPONENTS, (minutes * .1, minutes * .1, minutes * .4,
                                             minutes * .2, minutes * .2, 0)))
    return {"user_active": {k: fact("known", value={"minutes": v, "basis": basis,
                                                  "source": "人工教学方确认的有限可收束方案"}) for k, v in components.items()},
            "blocked_wait": fact("not_required", "材料已准备，无额外等待"),
            "system_effort": fact("not_required", "本例不承诺额外后台准备"),
            "fees": fact("not_required", "本例不承诺收费操作")}


def decision(need_id="FIX-need", revision=1, status="scheduled", minutes=5):
    result = {"need_ref": {"id": need_id, "revision": revision}, "status": status,
              "reason": "当前有效目标需要有限条件连接；本次不增加整章工作",
              "uncovered_impact": "安排并非独立掌握；父任务整体仍未支持",
              "next_trigger": "实际证据、预算或相关使用条件变化时重看"}
    if status in {"scheduled", "partially_scheduled"}:
        result.update(activity_ref={"id": "FIX-activity", "revision": 1}, requirement_ids=["infer-Q"],
                      operations=["connect-P-to-Q"], scope="有限推进条件连接并反馈、收束到同一父产物",
                      cost=cost(minutes), readiness={k: fact("known", value=True)
                                                    for k in ("necessary_conditions", "feasible_stop", "scope_confirmed")},
                      material_context={"goal_refs": [{"id": "FIX-goal", "revision": 1}],
                                        "activity_ref": {"id": "FIX-activity", "revision": 1},
                                        "intended_use": "independent_check", "purpose": "independent",
                                        "required_modalities": ["text", "formula"],
                                        "conditions": ["人工虚构给定前提", "初答前不给连接理由"]})
    if status == "closed":
        result["evidence_refs"] = [{"id": CLOSURE, "revision": 1}]
        result["material_context"] = decision()["material_context"]
    if status == "merged":
        result.update(merge_target_ref={"id": "FIX-need", "revision": 1},
                      requirement_mapping={"infer-Q": ["infer-Q"]})
    return result


def request(state_revision=1, operation_id="FIX-b4-schedule", **fields):
    return {"synthetic_only": True, "action": "schedule", "expected_state_revision": state_revision,
            "operation_id": operation_id, "budget_ref": {"id": "FIX-budget", "revision": 1},
            "authorization_refs": [{"id": "FIX-user-grant", "revision": 1}], "plan_id": PLAN,
            "spent_minutes": fact("known", value={"minutes": 0, "basis": "observed", "source": "人工场景尚未投入"}),
            "reserve_minutes": 0, "decisions": [decision()],
            "checkpoint_ref": {"id": "FIX-checkpoint", "revision": 1},
            "allowed_adjustments": {"actions": ["shrink", "stop"], "need_ids": ["FIX-need", DUPLICATE],
                                    "preserve_conditions": "不改变目标、判据、材料用途与必要反馈；不扩大资源"},
            **fields}


class B4PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pl-b4-planning-")
        self.addCleanup(self.temp.cleanup)
        self.snapshot, self.artifacts = fixture()
        self.counter = 0
        self.seed()

    def seed(self, snapshot=None):
        self.counter += 1
        self.workspace = Path(self.temp.name) / str(self.counter)
        self.store = LearningStore(self.workspace, entry_actor="AG1")
        self.assertEqual(self.store.init_workspace()["status"], "committed")
        result = self.store.import_fixture(snapshot or self.snapshot, self.artifacts)
        self.assertEqual(result["status"], "committed", result)
        self.service = PlanningService(self.store)

    def revision(self):
        return self.store.read_context()["state_revision"]

    def objects(self):
        return objects_by_id(self.store.read_context())

    def codes(self, result):
        return {p["code"] for p in result.get("reasons", [])}

    def commit(self, packet):
        result = self.service.run(packet)
        self.assertEqual(result["status"], "committed", result)
        return result

    def reject(self, packet, code):
        before = self.revision()
        result = self.service.run(packet)
        self.assertNotEqual(result["status"], "committed", result)
        self.assertIn(code, self.codes(result), result)
        self.assertEqual(self.revision(), before)
        return result

    def test_acceptance_is_pending_and_has_owner_trigger_without_plan(self):
        self.commit(request(action="accept", decisions=[decision(status="pending")], checkpoint_ref=None))
        need = self.objects()["FIX-need"]
        self.assertEqual(need["acceptance"]["status"], "accepted")
        self.assertEqual(need["disposition"]["status"], "pending")
        self.assertTrue(need["acceptance"]["next_trigger"])
        self.assertNotIn(PLAN, self.objects())

    def test_full_cost_shared_budget_and_single_current_arrangement(self):
        self.commit(request())
        objects = self.objects()
        plan = objects[PLAN]
        self.assertEqual(plan["budget_ref"], {"id": "FIX-budget", "revision": 1})
        self.assertEqual(plan["metadata"]["planning"]["allocation_ceiling_minutes"], 5)
        self.assertEqual(plan["metadata"]["planning"]["unallocated_minutes"], 0)
        self.assertEqual(len([o for o in objects.values() if o["type"] == "BudgetEnvelope"]), 1)
        self.assertEqual(objects["FIX-need"]["disposition"]["commitment_refs"], [ref(plan)])
        self.assertEqual(plan["need_refs"], [ref(objects["FIX-need"])])
        self.reject(request(self.revision(), "FIX-b4-second", plan_id="FIX-b4-second-plan", decisions=[decision(DUPLICATE)]), "unique_effective_arrangement_required")

    def test_combined_demands_do_not_each_receive_full_shared_budget(self):
        self.reject(request(decisions=[decision(), decision(DUPLICATE)],
                            alternatives=[{"scope": "先仅推进一个连接", "consequence": "另一需求未安排"}]), "shared_budget_exceeded")

    def test_missing_feedback_closure_and_unknown_cost_do_not_become_scheduled(self):
        for component in ("feedback_check", "closure_switch", "context_recovery", "preparation_verification"):
            with self.subTest(component=component):
                packet = request()
                packet["decisions"][0]["cost"]["user_active"][component] = fact("unknown", "没有可信成本")
                self.reject(packet, "bounded_or_observed_cost_required")
        packet = request()
        packet["decisions"][0]["cost"]["user_active"]["closure_switch"] = fact("not_required", "试图省略收束")
        self.reject(packet, "closure_cost_required")

    def test_unknown_non_user_cost_and_estimated_full_allocation_are_not_zero(self):
        packet = request()
        packet["decisions"][0]["cost"]["fees"] = fact("unknown", "尚未核对费用")
        self.reject(packet, "non_user_cost_unbounded")
        packet = request()
        packet["decisions"][0]["cost"] = cost(5, "estimate")
        self.reject(packet, "estimated_cost_needs_reserve")
        packet["reserve_minutes"] = 1
        packet["uncertainty_reason"] = "人工估计留反馈偏差余量"
        self.reject(packet, "shared_budget_exceeded")
        packet["decisions"][0]["cost"] = cost(4, "estimate")
        self.commit(packet)

    def test_duplicate_is_merged_to_same_need_with_one_allocation_and_mapping(self):
        packet = request(decisions=[decision(), decision(DUPLICATE, status="merged")],
                         alternatives=[{"scope": "分别安排两次检查", "consequence": "重复占时且不增加独立样本"}])
        self.commit(packet)
        objects = self.objects()
        self.assertEqual(len(objects[PLAN]["metadata"]["planning"]["allocations"]), 1)
        merged = objects[DUPLICATE]["disposition"]
        self.assertEqual(merged["merge_target_ref"], ref(objects["FIX-need"]))
        self.assertEqual(merged["requirement_mapping"], {"infer-Q": ["infer-Q"]})
        self.assertEqual(len([o for o in objects.values() if o["type"] == "PerformanceEvent"]), 1)

    def test_distinct_evidence_conditions_are_not_merged_by_name(self):
        snapshot = copy.deepcopy(self.snapshot)
        objects_by_id(snapshot)[DUPLICATE]["conditions"] = "必须无相关接触七天；其余只是即时条件"
        self.seed(snapshot)
        self.reject(request(action="dispose", decisions=[decision(DUPLICATE, status="merged")]), "merge_must_preserve_requirement_conditions")

    def test_merge_cannot_replace_whole_requirement_with_narrower_requirement(self):
        snapshot = copy.deepcopy(self.snapshot)
        objects = objects_by_id(snapshot)
        objects[DUPLICATE]["requirement_ids"] = ["infer-Q", "complete-chain"]
        self.seed(snapshot)
        merged = decision(DUPLICATE, status="merged")
        merged["requirement_mapping"] = {"infer-Q": ["infer-Q"], "complete-chain": ["infer-Q"]}
        self.reject(request(action="dispose", decisions=[merged]), "merge_must_preserve_requirement_conditions")
        self.assertEqual(self.objects()[DUPLICATE]["disposition"]["status"], "pending")

    def test_merged_duplicate_does_not_block_later_authorized_shrink(self):
        self.commit(request(decisions=[decision(), decision(DUPLICATE, status="merged")],
            alternatives=[{"scope": "分别安排重复需求", "consequence": "重复占用同一额度"}]))
        plan = self.objects()[PLAN]
        self.assertEqual(plan["need_refs"], [{"id": "FIX-need", "revision": 2}])
        shrink = request(self.revision(), "FIX-b4-merge-then-shrink", action="shrink", available_minutes=3,
            commitment_ref=ref(plan), authorization_refs=[{"id": ADJUST, "revision": 1}],
            decisions=[decision(revision=2, status="partially_scheduled", minutes=3)],
            alternatives=[{"scope": "原五分钟范围", "consequence": "本次只能可靠完成三分钟子范围"}])
        result = PlanningService(LearningStore(self.workspace, entry_actor="AG0")).run(shrink)
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.objects()[DUPLICATE]["disposition"]["status"], "merged")

    def test_deferred_and_no_investment_keep_uncovered_goal_and_trigger(self):
        original_goal = copy.deepcopy(self.objects()["FIX-goal"])
        for status in ("deferred", "no_further_investment", "returned"):
            with self.subTest(status=status):
                self.seed()
                self.commit(request(action="dispose", decisions=[decision(status=status)]))
                need = self.objects()["FIX-need"]
                self.assertEqual(need["disposition"]["status"], status)
                self.assertTrue(need["uncovered_impact"])
                self.assertTrue(need["next_trigger"])
                self.assertEqual(self.objects()["FIX-goal"], original_goal)
                self.assertNotIn(PLAN, self.objects())

    def test_read_only_candidate_and_missing_authority_create_no_arrangement(self):
        packet = request(authorization_refs=[])
        before = self.revision()
        result = self.service.inspect(packet)
        self.assertEqual(result["status"], "candidate", result)
        self.assertFalse(result["authorized"])
        self.reject(packet, "planning_authorization_required")
        self.assertEqual(self.revision(), before)
        self.assertNotIn(PLAN, self.objects())

    def test_unsupported_natural_evidence_does_not_close_need(self):
        packet = request(action="dispose", decisions=[decision(status="closed")])
        packet["decisions"][0]["evidence_refs"] = [{"id": "FIX-judgment", "revision": 1}]
        self.reject(packet, "adopted_closure_scope_required")

    def test_natural_evidence_closes_simple_need_without_new_check_or_mastery_object(self):
        before = self.objects()
        self.commit(request(action="dispose", decisions=[decision(status="closed")]))
        objects = self.objects()
        self.assertEqual(objects["FIX-need"]["disposition"]["status"], "closed")
        self.assertEqual(objects["FIX-need"]["judgment_refs"], [{"id": CLOSURE, "revision": 1}])
        self.assertEqual(set(objects), set(before))
        self.assertEqual(objects["FIX-goal"], before["FIX-goal"])
        self.assertEqual(objects[CLOSURE], before[CLOSURE])
        self.reject(request(self.revision(), "FIX-b4-late-card", decisions=[decision(revision=2)]), "terminal_need_requires_new_professional_basis")

    def test_closing_scheduled_need_supersedes_old_commitment_atomically(self):
        self.commit(request())
        self.reject(request(self.revision(), "FIX-b4-close-without-plan", action="dispose", decisions=[decision(revision=2, status="closed")]), "active_commitment_replacement_required")
        self.commit(request(self.revision(), "FIX-b4-close", action="dispose", decisions=[decision(revision=2, status="closed")],
                            replace_commitment_refs=[{"id": PLAN, "revision": 1}],
                            alternatives=[{"scope": "继续专项检查", "consequence": "自然证据已够用，额外投入无必要"}]))
        objects = self.objects()
        self.assertEqual(objects[PLAN]["status"], "superseded")
        self.assertEqual(objects["FIX-need"]["disposition"]["status"], "closed")
        self.assertEqual(objects[PLAN]["need_refs"], [ref(objects["FIX-need"])])

    def test_ag0_shrink_changes_only_current_scope_not_goal_or_budget(self):
        self.commit(request())
        objects = self.objects()
        ag0 = PlanningService(LearningStore(self.workspace, entry_actor="AG0"))
        packet = request(self.revision(), "FIX-b4-shrink", action="shrink", available_minutes=3,
                         commitment_ref=ref(objects[PLAN]), authorization_refs=[{"id": ADJUST, "revision": 1}],
                         decisions=[decision(revision=2, status="partially_scheduled", minutes=3)],
                         alternatives=[{"scope": "完整五分钟范围", "consequence": "当前不足，未做的推进保留"}])
        result = ag0.run(packet)
        self.assertEqual(result["status"], "committed", result)
        now = self.objects()
        self.assertEqual(now[PLAN]["revision"], 2)
        self.assertEqual(now[PLAN]["metadata"]["planning"]["allocation_ceiling_minutes"], 3)
        self.assertEqual(now["FIX-need"]["disposition"]["status"], "partially_scheduled")
        self.assertEqual(now["FIX-goal"], objects["FIX-goal"])
        self.assertEqual(now["FIX-budget"], objects["FIX-budget"])

    def test_ag0_cannot_formal_plan_expand_or_change_design(self):
        self.commit(request())
        ag0 = PlanningService(LearningStore(self.workspace, entry_actor="AG0"))
        result = ag0.run(request(self.revision(), "FIX-b4-ag0-formal", decisions=[decision(revision=2)]))
        self.assertIn("ag1_formal_planning_required", self.codes(result))
        packet = request(self.revision(), "FIX-b4-ag0-expand", action="shrink", available_minutes=5,
                         commitment_ref={"id": PLAN, "revision": 1}, authorization_refs=[{"id": ADJUST, "revision": 1}],
                         decisions=[decision(revision=2, minutes=6)],
                         alternatives=[{"scope": "原活动", "consequence": "不得伪造压缩方案"}])
        result = ag0.run(packet)
        self.assertIn("local_shrink_must_preserve_design", self.codes(result))
        packet["decisions"][0]["cost"] = cost(3)
        packet["decisions"][0]["material_context"]["purpose"] = "assisted"
        result = ag0.run(packet)
        self.assertNotEqual(result["status"], "committed", result)

    def test_authorized_shrink_cannot_increase_fees_wait_or_system_effort(self):
        snapshot = copy.deepcopy(self.snapshot)
        budget = objects_by_id(snapshot)["FIX-budget"]
        for key in ("fees", "blocked_wait", "system_effort"):
            budget[key] = fact("known", value={"amount" if key == "fees" else "minutes": 100})
        for key in ("fees", "blocked_wait", "system_effort"):
            with self.subTest(resource=key):
                self.seed(snapshot)
                self.commit(request())
                before = self.objects()
                ag0 = PlanningService(LearningStore(self.workspace, entry_actor="AG0"))
                d = decision(revision=2, status="partially_scheduled", minutes=4)
                d["cost"][key] = fact("known", value={"amount" if key == "fees" else "minutes": 50})
                packet = request(self.revision(), "FIX-b4-resource-shrink-" + key, action="shrink",
                    available_minutes=4, commitment_ref=ref(before[PLAN]),
                    authorization_refs=[{"id": ADJUST, "revision": 1}], decisions=[d],
                    alternatives=[{"scope": "原五分钟工作", "consequence": "新预算仅授权缩时，未授权更多其他资源"}])
                result = ag0.run(packet)
                self.assertNotEqual(result["status"], "committed", result)
                self.assertIn("local_shrink_must_preserve_design", self.codes(result), result)
                self.assertEqual(self.objects(), before)

    def test_only_closure_time_can_stop_without_moving_all_work_to_tomorrow(self):
        self.commit(request())
        ag0 = PlanningService(LearningStore(self.workspace, entry_actor="AG0"))
        packet = request(self.revision(), "FIX-b4-stop", action="shrink", available_minutes=0,
                         commitment_ref={"id": PLAN, "revision": 1}, authorization_refs=[{"id": ADJUST, "revision": 1}],
                         decisions=[decision(revision=2, status="deferred")],
                         alternatives=[{"scope": "启动新证明段", "consequence": "无法保留反馈和收束，原要求继续未完成"}])
        result = ag0.run(packet)
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.objects()[PLAN]["status"], "stopped")
        self.assertEqual(self.objects()["FIX-need"]["disposition"]["status"], "deferred")
        self.assertNotIn("tomorrow", json.dumps(self.objects()[PLAN]))

    def test_cas_and_exact_retry_preserve_single_need_revision_and_plan(self):
        packet = request()
        first = self.commit(packet)
        state = self.revision()
        retry = self.service.run(packet)
        self.assertEqual(retry["status"], "committed", retry)
        self.assertTrue(retry["replayed"])
        self.assertEqual(retry["state_revision"], first["state_revision"])
        self.assertEqual(self.revision(), state)
        altered = copy.deepcopy(packet)
        altered["decisions"][0]["reason"] = "另一个决定不能沿用同一操作"
        self.reject(altered, "operation_id_reused")
        self.reject(request(1, "FIX-b4-stale", decisions=[decision(revision=2)]), "state_revision_conflict")

    def test_reopen_resume_preserves_parent_original_help_and_no_replanning(self):
        self.commit(request())
        before = self.revision()
        service = PlanningService(LearningStore(self.workspace, entry_actor="AG1"))
        result = service.resume({"id": PLAN, "revision": 1})
        self.assertEqual(result["status"], "ready", result)
        self.assertFalse(result["replanned"])
        self.assertEqual(result["new_required_checks"], 0)
        self.assertEqual(result["recovery"]["last_trusted_event_ref"], {"id": "FIX-event", "revision": 1})
        self.assertEqual(result["recovery"]["help_history_refs"], [{"id": "FIX-event", "revision": 1}])
        self.assertEqual(result["recovery"]["parent_artifact"]["path"], "originals.md")
        self.assertEqual(result["recovery"]["unrecorded_actions"]["status"], "unknown")
        self.assertEqual(self.revision(), before)

    def test_missing_summary_resume_does_not_invent_success_or_require_whole_restart(self):
        self.commit(request(checkpoint_ref=None))
        result = self.service.resume({"id": PLAN, "revision": 1})
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(result["recovery"]["unrecorded_actions"]["status"], "unknown")
        self.assertEqual(result["new_required_checks"], 0)

    def test_pause_and_use_restriction_prevent_commit_and_resume_immediately(self):
        self.commit(request())
        result = self.store.pause(self.revision(), "FIX-b4-pause", ["FIX-activity"], "人工暂停")
        self.assertEqual(result["status"], "committed", result)
        resumed = self.service.resume({"id": PLAN, "revision": 1})
        self.assertEqual(resumed["status"], "blocked", resumed)
        retry = self.service.run(request())
        self.assertNotEqual(retry["status"], "committed", retry)
        self.assertFalse(retry["mutated"])

    def test_deleted_evidence_blocks_late_retry_and_no_shadow_receipt_revives_it(self):
        packet = request()
        self.commit(packet)
        deletion = self.store.delete_scope(self.revision(), "FIX-b4-delete", ["FIX-event"])
        self.assertEqual(deletion["status"], "committed", deletion)
        before = self.revision()
        retry = self.service.run(packet)
        self.assertNotEqual(retry["status"], "committed", retry)
        resumed = self.service.resume({"id": PLAN, "revision": 1})
        self.assertNotEqual(resumed["status"], "ready", resumed)
        self.assertEqual(self.revision(), before)
        exported = self.store.export_scope(["FIX-event"])
        self.assertNotEqual(exported["status"], "ok", exported)

    def test_authorized_routine_judgment_can_close_without_extra_review(self):
        snapshot = copy.deepcopy(self.snapshot)
        objects = objects_by_id(snapshot)
        judgment = objects[CLOSURE]
        judgment.update(owner="AG0", decision_type="routine_scoring", authorization_ref=ref(objects["FIX-scoring-grant"]))
        judgment["adoption"].update(by="AG0", basis_refs=[ref(objects["FIX-scoring-grant"])])
        self.seed(snapshot)
        self.commit(request(action="dispose", decisions=[decision(status="closed")]))
        self.assertEqual(self.objects()["FIX-need"]["disposition"]["status"], "closed")
        self.assertEqual(self.objects()[CLOSURE]["owner"], "AG0")

    def test_saved_c0_spending_cannot_be_reset_by_a_new_plan(self):
        snapshot = copy.deepcopy(self.snapshot)
        objects = objects_by_id(snapshot)
        objects["FIX-event"]["c0"] = {"budget_ref": {"id": "FIX-budget", "revision": 1},
            "declared_active_minutes": fact("known", value={"minutes": 5, "measurement": "caller_declaration"})}
        self.seed(snapshot)
        self.reject(request(), "spent_time_below_saved_execution")
        packet = request(spent_minutes=fact("known", value={"minutes": 5}))
        self.reject(packet, "shared_budget_exceeded")

    def test_legacy_checkpoint_spending_cannot_be_reset_by_a_new_plan(self):
        snapshot = copy.deepcopy(self.snapshot)
        objects = objects_by_id(snapshot)
        objects["FIX-event"]["c0"] = {"budget_ref": ref(objects["FIX-budget"]),
            "declared_active_minutes": fact("known", value={"minutes": 1, "measurement": "caller_declaration"})}
        objects["FIX-checkpoint"]["declared_active_minutes"] = fact("known", value={"minutes": 5, "measurement": "caller_declaration"})
        self.seed(snapshot)
        self.reject(request(checkpoint_ref=None, decisions=[decision(minutes=4)], spent_minutes=fact("known", value={"minutes": 1})),
                    "spent_time_below_saved_execution")
        self.reject(request(checkpoint_ref=None, spent_minutes=fact("known", value={"minutes": 5})),
                    "shared_budget_exceeded")

    def test_restricted_budget_checkpoint_does_not_allow_a_new_plan_or_disclose_time(self):
        snapshot = copy.deepcopy(self.snapshot)
        objects = objects_by_id(snapshot)
        objects["FIX-event"]["c0"] = {"budget_ref": ref(objects["FIX-budget"]),
            "declared_active_minutes": fact("known", value={"minutes": 1, "measurement": "caller_declaration"})}
        objects["FIX-checkpoint"]["declared_active_minutes"] = fact("known", value={"minutes": 5, "measurement": "caller_declaration"})
        self.seed(snapshot)
        restricted = self.store.restrict(self.revision(), "FIX-budget-cp-planning-restrict", ["FIX-checkpoint"],
                                         "人工计划用途待重审", ["planning"])
        self.assertEqual(restricted["status"], "committed", restricted)
        before = self.revision()
        result = self.service.run(request(state_revision=before, checkpoint_ref=None, decisions=[decision(minutes=4)],
                                         spent_minutes=fact("known", value={"minutes": 1})))
        self.assertEqual(result["status"], "blocked", result)
        self.assertIn("restricted_use", self.codes(result))
        self.assertNotIn("changes", result)
        self.assertNotIn("total_active_minutes", result)
        self.assertEqual(self.revision(), before)

    def test_other_budget_checkpoint_does_not_contaminate_current_consumption(self):
        snapshot = copy.deepcopy(self.snapshot)
        objects = objects_by_id(snapshot)
        objects["FIX-event"]["c0"] = {"budget_ref": ref(objects["FIX-budget"]),
            "declared_active_minutes": fact("known", value={"minutes": 1, "measurement": "caller_declaration"})}
        another = copy.deepcopy(objects["FIX-budget"])
        another["id"] = "FIX-other-budget"
        snapshot["objects"].append(another)
        objects["FIX-checkpoint"].update(budget_ref=ref(another),
            declared_active_minutes=fact("known", value={"minutes": 100, "measurement": "caller_declaration"}))
        self.seed(snapshot)
        self.commit(request(checkpoint_ref=None, decisions=[decision(minutes=4)],
                            spent_minutes=fact("known", value={"minutes": 1})))

    def test_specialist_whole_gate_is_preserved_by_planning(self):
        from test_b4_teaching import whole_fixture
        snapshot, artifacts, context = whole_fixture(coverage=False)
        objects = objects_by_id(snapshot)
        objects["FIX-need"]["requirement_ids"] = ["complete-chain"]
        self.artifacts = artifacts
        self.seed(snapshot)
        d = decision()
        d.update(requirement_ids=["complete-chain"], operations=["connect-P-to-Q", "connect-Q-to-R"], material_context=context)
        self.reject(request(decisions=[d], checkpoint_ref=None), "whole_reference_coverage_required")

    def test_future_temporal_conditions_do_not_close_by_calendar(self):
        snapshot = copy.deepcopy(self.snapshot)
        objects_by_id(snapshot)["FIX-goal"]["time_requirements"] = fact("known", value={
            "requirement_ids": ["infer-Q"], "minimum_delay_seconds": 86400, "require_no_contact": True})
        self.seed(snapshot)
        self.reject(request(action="dispose", decisions=[decision(status="closed")]), "closure_conditions_not_supported")

    def test_failed_save_returns_no_arrangement_and_keeps_original_need(self):
        before = self.objects()
        with patch.object(self.store, "commit", return_value={"status": "not_saved", "reasons": [{"code": "synthetic_save_failure"}]}):
            result = self.service.run(request())
        self.assertEqual(result["status"], "not_saved", result)
        self.assertFalse(result["mutated"])
        self.assertEqual(result["output_refs"], [])
        self.assertEqual(self.objects(), before)

    def test_cli_inspection_and_missing_request_return_json(self):
        path = Path(self.temp.name) / "request.json"
        path.write_text(json.dumps(request(), ensure_ascii=False), encoding="utf-8")
        command = [sys.executable, "-X", "utf8", str(ROOT / "src/runtime/learning_planning.py"), "--workspace", str(self.workspace), "--request", str(path), "--inspect"]
        process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["status"], "candidate")
        path.unlink()
        process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, 1)
        self.assertEqual(json.loads(process.stdout)["status"], "rejected")
        self.assertEqual(self.revision(), 1)


if __name__ == "__main__":
    unittest.main()
