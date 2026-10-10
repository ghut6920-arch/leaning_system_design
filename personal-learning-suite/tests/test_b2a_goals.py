"""B2a 有限行为核查：FIX 目标候选与 B1 接缝，不判内容真伪或学习达成。"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from runtime.learning_goals import INPUT_VERSION, review_goal_package
from runtime.learning_store import LearningStore


def fixture():
    return json.loads((ROOT / "fixtures/b2a-goal-input.json").read_text(encoding="utf-8-sig"))


def canonical_fixture():
    """Explicit fictional AG2 declarations, not an automatic legacy migration."""
    package = fixture()
    for source in package["sources"]:
        recorded = source["verification"]["value"]
        source["read_scope"] = {
            "text": copy.deepcopy(source["read_scope"]),
            "formula": {"status": "unknown", "reason": "本人工文本目标不依赖公式模态；未核公式。"},
            "figure": {"status": "unknown", "reason": "本人工文本目标不依赖图像模态；未核图像。"},
        }
        source["verification"] = {"content": {
            "status": "supported", "checked_revision": source["revision"],
            "scope": recorded["scope"], "method": "source_comparison", "reviewer": "AG2",
            "conditions": ["synthetic-only", "当前已声明文本范围"],
            "required_modalities": ["text"],
            "anchor_refs": [{"id": source["id"], "revision": source["revision"], "locator": "claims"}],
            "unchecked_scope": ["formula", "figure", recorded["limitations"]],
        }}
    return package


def mapping():
    return [{"from_requirement_ids": [rid], "to_requirement_ids": [rid], "relation": "same requirement"} for rid in ("implement", "explain")]


def revision(kind="substantive"):
    package = fixture()
    package["previous_goal"] = copy.deepcopy(package["goal"])
    package["goal"]["revision"] = 2
    package["mode"] = "revise"
    package["change"] = {"kind": kind, "reason": "FIX-version-check", "requirement_mapping": mapping()}
    return package


def pending_codes(result):
    return {item.get("code") for item in result["unresolved_items"]}


def error_codes(result):
    return {item["code"] for item in result["errors"]}


class B2aCandidateTests(unittest.TestCase):
    def test_canonical_source_requires_a_managed_verification_anchor(self):
        package = canonical_fixture()
        package["sources"][1]["verification"]["content"]["anchor_refs"] = [{"label": "模型同意不是锚点"}]
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "partial", result)
        self.assertEqual(result["reliable_requirement_ids"], [])
        self.assertIn("source_verification_pending", pending_codes(result))

    def test_canonical_bad_verification_fields_are_limited_without_crashing(self):
        for key, value in (("status", []), ("method", {}), ("required_modalities", {}),
                           ("checked_revision", True), ("anchor_refs", [None])):
            with self.subTest(key=key):
                package = canonical_fixture()
                package["sources"][1]["verification"]["content"][key] = value
                result = review_goal_package(package)
                self.assertEqual(result["review_state"], "partial", result)
                self.assertEqual(result["reliable_requirement_ids"], [])

    def test_canonical_required_modality_unknown_only_limits_its_requirement_scope(self):
        package = canonical_fixture()
        source = copy.deepcopy(package["sources"][1])
        source["id"] = "FIX-canonical-explanation-only"
        source["source_ref"]["source_id"] = source["id"]
        source["verification"]["content"]["anchor_refs"][0]["id"] = source["id"]
        source["verification"]["content"]["required_modalities"] = ["text", "formula"]
        package["sources"].append(source)
        source_ref = {"id": source["id"], "revision": 1, "locator": "claims"}
        requirement = package["goal"]["requirements"][1]
        requirement["content_basis_refs"].append(copy.deepcopy(source_ref))
        requirement["criterion"]["content_basis_refs"].append(copy.deepcopy(source_ref))
        package["goal"]["content_basis_refs"].append(copy.deepcopy(source_ref))
        package["goal"]["basis_refs"].append(copy.deepcopy(source_ref))
        before = copy.deepcopy(package)
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "partial")
        self.assertEqual(result["reliable_requirement_ids"], ["implement"])
        self.assertIn("source_verification_pending", pending_codes(result))
        self.assertEqual(package, before)

    def test_canonical_missing_modality_scope_or_old_verification_is_not_invented(self):
        for change in ("missing_modalities", "old_verification", "pending_content"):
            with self.subTest(change=change):
                package = canonical_fixture()
                content = package["sources"][1]["verification"]["content"]
                if change == "missing_modalities":
                    content.pop("required_modalities")
                elif change == "old_verification":
                    content["checked_revision"] = 99
                else:
                    content["status"] = "pending"
                before = copy.deepcopy(package)
                result = review_goal_package(package)
                self.assertEqual(result["review_state"], "partial")
                self.assertEqual(result["reliable_requirement_ids"], [])
                self.assertEqual(package, before)

    def test_canonical_boolean_read_flag_does_not_supply_a_locatable_read_scope(self):
        package = canonical_fixture()
        package["sources"][1]["read_scope"]["text"] = {"status": "known", "value": True}
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "partial")
        self.assertEqual(result["reliable_requirement_ids"], [])


    def test_complete_candidate_has_separate_implementation_and_explanation(self):
        package = fixture()
        before = copy.deepcopy(package)
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "complete")
        self.assertEqual(result["status"], "candidate")
        self.assertEqual(result["reliable_requirement_ids"], ["implement", "explain"])
        self.assertEqual(result["goal_candidate"], before["goal"])
        self.assertEqual(package, before, "审阅不修改调用者输入")
        self.assertIn("运行正确不能替代", result["goal_candidate"]["requirements"][1]["criterion"]["text"])
        self.assertEqual(result["boundaries"]["learner_judgment"], "not_executed")
        self.assertEqual(result["boundaries"]["content_verification"], "not_executed")
        self.assertEqual(result["boundaries"]["new_test"], "not_proposed")
        json.dumps(result, ensure_ascii=False)

    def test_only_course_map_preserves_topics_without_inventing_criteria(self):
        package = fixture()
        package["goal"] = None
        package["sources"] = []
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "map_only")
        self.assertEqual(result["course_map_candidate"], package["course_map"])
        self.assertIsNone(result["goal_candidate"])
        self.assertEqual(result["reliable_requirement_ids"], [])
        self.assertIn("recent_goal_missing", pending_codes(result))
        self.assertEqual(result["boundaries"]["new_test"], "not_proposed")

    def test_dual_sources_missing_only_blocks_affected_requirement(self):
        package = fixture()
        package["goal"]["requirements"][1]["criterion"]["content_basis_refs"] = []
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "partial")
        self.assertEqual(result["reliable_requirement_ids"], ["implement"])
        self.assertIn("dual_source_missing", pending_codes(result))

    def test_missing_current_content_reference_is_pending_not_verification(self):
        package = fixture()
        package["goal"]["requirements"][0]["content_basis_refs"][0]["revision"] = 99
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "partial")
        self.assertIn("source_reference", pending_codes(result))
        self.assertEqual(result["boundaries"]["content_verification"], "not_executed")

    def test_opened_source_with_unknown_verification_is_not_reliable(self):
        package = fixture()
        package["sources"][1]["verification"] = {"status": "unknown", "reason": "FIX仅打开，未核验"}
        result = review_goal_package(package)
        self.assertEqual(result["reliable_requirement_ids"], [])
        self.assertIn("source_verification_pending", pending_codes(result))

    def test_distinct_read_and_verification_scopes_with_text_conditions_remain_candidate(self):
        package = fixture()
        for source in package["sources"]:
            source["read_scope"]["value"] = "FIX已读该来源所给任务说明和规则全文，包括边界文字"
            source["verification"]["value"]["scope"] = "FIX既有核验仅支持当前有限阈值实现与解释用途"
            self.assertNotEqual(source["read_scope"]["value"], source["verification"]["value"]["scope"])
        package["goal"]["context_conditions"]["value"] = "FIX x和t均为有限数值；只处理当前任务范围"
        package["goal"]["allowed_resources"]["value"] = "FIX可查语法文档并运行自己编写的程序，关键操作由学习者完成"
        for evidence in package["goal"]["evidence_requirements"]:
            evidence["allowed_help"]["value"] = "FIX可查明示规则或语法，不提供正在评价的关键分支或理由链"
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "complete")
        self.assertEqual(result["status"], "candidate")
        self.assertEqual(result["reliable_requirement_ids"], ["implement", "explain"])
        self.assertEqual(result["boundaries"]["content_verification"], "not_executed")
        self.assertEqual(result["boundaries"]["professional_adoption"], "not_executed")

    def test_far_future_unknown_does_not_block_current_reliable_subscope(self):
        package = fixture()
        package["unresolved_items"] = [{"decision_needed": "FIX训练目标待取得材料", "owner": "AG1", "next_trigger": "FIX用途扩展", "scope_requirement_ids": []}]
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "partial")
        self.assertEqual(result["reliable_requirement_ids"], ["implement", "explain"])

    def test_current_unknown_keeps_other_reliable_requirement(self):
        package = fixture()
        package["unresolved_items"] = [{"decision_needed": "FIX解释官方评分待确认", "owner": "AG1", "next_trigger": "FIX评分规则到达", "scope_requirement_ids": ["explain"]}]
        result = review_goal_package(package)
        self.assertEqual(result["reliable_requirement_ids"], ["implement"])
        self.assertEqual(result["unresolved_items"][0]["owner"], "AG1")

    def test_unknown_requirement_scope_is_rejected_or_conservatively_limited(self):
        package = fixture()
        package["unresolved_items"] = [{"decision_needed": "FIX作用域拼写待澄清", "owner": "AG1", "next_trigger": "FIX核对稳定要求标识", "scope_requirement_ids": ["nonexistent"]}]
        result = review_goal_package(package)
        self.assertTrue(result["review_state"] == "invalid" or not result["reliable_requirement_ids"], result)
        issues = result["errors"] + result["unresolved_items"]
        scoped = [item for item in issues if "scope_requirement_ids" in item.get("path", "")]
        self.assertTrue(scoped, "无效作用域需明确报告，不能当作不影响当前要求的远期未知")
        self.assertTrue(any(item.get("detail") or item.get("decision_needed") for item in scoped))

    def test_aggregate_explanation_source_does_not_block_implementation(self):
        package = fixture()
        source = copy.deepcopy(package["sources"][1])
        source["id"] = "FIX-b2a-explanation-only"
        source["source_ref"]["source_id"] = source["id"]
        source["verification"] = {"status": "unknown", "reason": "FIX解释专属来源尚未核验"}
        package["sources"].append(source)
        ref = {"id": source["id"], "revision": 1, "locator": "claims"}
        explanation = package["goal"]["requirements"][1]
        explanation["content_basis_refs"].append(copy.deepcopy(ref))
        explanation["criterion"]["content_basis_refs"].append(copy.deepcopy(ref))
        package["goal"]["content_basis_refs"].append(copy.deepcopy(ref))
        package["goal"]["basis_refs"].append(copy.deepcopy(ref))
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "partial")
        self.assertEqual(result["reliable_requirement_ids"], ["implement"])
        self.assertIn("source_verification_pending", pending_codes(result))

    def test_no_delay_requirement_is_not_a_gap(self):
        result = review_goal_package(fixture())
        self.assertEqual(result["review_state"], "complete")
        self.assertEqual(result["goal_candidate"]["time_requirements"]["status"], "not_required")
        self.assertNotIn("time_requirements", pending_codes(result))

    def test_unknown_help_is_not_zero_help(self):
        package = fixture()
        package["goal"]["evidence_requirements"][1]["allowed_help"] = {"status": "unknown", "reason": "FIX帮助条件待定"}
        result = review_goal_package(package)
        self.assertEqual(result["reliable_requirement_ids"], ["implement"])
        self.assertIn("evidence_help_pending", pending_codes(result))

    def test_missing_observable_evidence_stays_unresolved(self):
        package = fixture()
        package["goal"]["evidence_requirements"] = package["goal"]["evidence_requirements"][:1]
        result = review_goal_package(package)
        self.assertEqual(result["reliable_requirement_ids"], ["implement"])
        self.assertIn("evidence_missing", pending_codes(result))

    def test_prerequisite_unknown_is_not_learner_failure(self):
        result = review_goal_package(fixture())
        prerequisite = result["goal_candidate"]["prerequisites"][0]
        self.assertEqual(prerequisite["dependency_kind"], "companion")
        self.assertEqual(prerequisite["learner_state"]["status"], "unknown")
        self.assertEqual(result["review_state"], "complete")
        self.assertEqual(result["boundaries"]["learner_judgment"], "not_executed")

    def test_single_failure_does_not_establish_necessary_prerequisite(self):
        package = fixture()
        package["goal"]["prerequisites"][0].update(dependency_kind="necessary", necessity_basis="single_failure")
        result = review_goal_package(package)
        self.assertEqual(result["reliable_requirement_ids"], [])
        self.assertIn("single_failure_dependency", pending_codes(result))

    def test_background_dependency_does_not_become_a_gate(self):
        package = fixture()
        package["goal"]["prerequisites"][0]["dependency_kind"] = "background"
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "complete")
        self.assertEqual(result["goal_candidate"]["prerequisites"][0]["dependency_kind"], "background")
        self.assertEqual(result["boundaries"]["new_test"], "not_proposed")

    def test_synthetic_protocol_and_shape_are_enforced(self):
        cases = [None, {}, {**fixture(), "synthetic_only": False}, {**fixture(), "input_version": "future"}, {**fixture(), "mode": "adopt"}]
        for package in cases:
            with self.subTest(package_type=type(package).__name__):
                self.assertEqual(review_goal_package(package)["review_state"], "invalid")

    def test_real_source_identity_is_rejected(self):
        package = fixture()
        package["sources"][0]["source_ref"]["identity_kind"] = "real_course"
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "invalid")
        self.assertIn("synthetic_source", error_codes(result))

    def test_false_adoption_cannot_be_announced(self):
        package = fixture()
        package["goal"]["adoption"] = {"status": "adopted"}
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "invalid")
        self.assertIn("adoption_not_supported", error_codes(result))

    def test_unknown_fact_cannot_carry_guessed_value(self):
        package = fixture()
        package["goal"]["prerequisites"][0]["learner_state"]["value"] = "不会"
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "invalid")
        self.assertIn("fact_shape", error_codes(result))

    def test_known_null_is_invalid_instead_of_known_information(self):
        package = fixture()
        package["goal"]["context_conditions"] = {"status": "known", "value": None}
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "invalid")
        self.assertEqual(result["reliable_requirement_ids"], [])
        self.assertIn("fact_shape", error_codes(result))

    def test_malformed_verification_lists_do_not_crash_or_claim_reliability(self):
        for value in ([], ["FIX不是核验对象"], {"status": "known", "value": []}):
            with self.subTest(verification=value):
                package = fixture()
                package["sources"][1]["verification"] = value
                result = review_goal_package(package)
                self.assertNotEqual(result["review_state"], "complete")
                self.assertEqual(result["reliable_requirement_ids"], [])
                self.assertIn("source_verification_pending", pending_codes(result))

    def test_malformed_unresolved_integer_is_invalid_without_crashing(self):
        for value in (1, [1]):
            with self.subTest(unresolved=value):
                package = fixture()
                package["unresolved_items"] = value
                result = review_goal_package(package)
                self.assertEqual(result["review_state"], "invalid")
                self.assertEqual(result["reliable_requirement_ids"], [])
                self.assertTrue({"unresolved_shape", "unresolved_owner"} & error_codes(result))

    def test_cli_only_emits_preview_without_creating_records(self):
        with tempfile.TemporaryDirectory(prefix="pl-b2a-cli-") as directory:
            temp_root = Path(directory)
            input_path = temp_root / "FIX-input.json"
            input_path.write_text(json.dumps(fixture(), ensure_ascii=False), encoding="utf-8")
            before = set(temp_root.iterdir())
            run = subprocess.run([sys.executable, "-B", str(ROOT / "src/runtime/learning_goals.py"), "--input", str(input_path)], cwd=temp_root, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)["status"], "candidate")
            self.assertEqual(set(temp_root.iterdir()), before)


class B2aVersionTests(unittest.TestCase):
    def test_session_budget_reduction_leaves_exact_goal_and_routes_plan(self):
        package = revision("session_budget_only")
        package["goal"] = copy.deepcopy(package["previous_goal"])
        result = review_goal_package(package)
        self.assertEqual(result["review_state"], "complete")
        self.assertEqual(result["goal_candidate"]["revision"], 1)
        self.assertEqual(result["compatibility"]["status"], "preserve")
        self.assertFalse(result["planning_handoff"]["goal_revision_changed"])
        self.assertEqual(result["planning_handoff"]["valid_commitment"], "not_created")

    def test_budget_convenience_cannot_change_goal(self):
        result = review_goal_package(revision("session_budget_only"))
        self.assertIn("budget_changed_goal", error_codes(result))
        self.assertEqual(result["review_state"], "invalid")

    def test_exact_reuse_keeps_revision_but_does_not_copy_judgment(self):
        package = fixture()
        package["previous_goal"] = copy.deepcopy(package["goal"])
        package["mode"] = "reuse"
        result = review_goal_package(package)
        self.assertEqual(result["compatibility"]["status"], "preserve")
        self.assertEqual(result["compatibility"]["judgment_transfer"], "not_executed")
        self.assertNotIn("judgments", result)

    def test_locator_equivalence_requires_rationale_and_mapping(self):
        package = revision("equivalent")
        package["goal"]["requirements"][0]["content_basis_refs"][0]["locator"] = "FIX-relocated-claim"
        result = review_goal_package(package)
        self.assertEqual(result["compatibility"]["status"], "recheck")
        package["change"]["equivalence_reason"] = "FIX仅来源定位调整，规则和任务不变；AG1仍需确认。"
        result = review_goal_package(package)
        self.assertEqual(result["compatibility"]["status"], "preserve")
        self.assertEqual(result["compatibility"]["preserve_requirement_ids"], ["implement", "explain"])

    def test_swapping_requirement_mapping_cannot_preserve_equivalence(self):
        package = revision("equivalent")
        package["change"]["equivalence_reason"] = "FIX规则文字未变但映射交换能力"
        package["change"]["requirement_mapping"] = [
            {"from_requirement_ids": ["implement"], "to_requirement_ids": ["explain"], "relation": "FIX swapped"},
            {"from_requirement_ids": ["explain"], "to_requirement_ids": ["implement"], "relation": "FIX swapped"},
        ]
        result = review_goal_package(package)
        self.assertEqual(result["compatibility"]["status"], "recheck")
        self.assertEqual(result["compatibility"]["preserve_requirement_ids"], [])
        self.assertIn("equivalence_mapping", pending_codes(result))
        self.assertEqual(result["compatibility"]["judgment_transfer"], "not_executed")

    def test_revised_candidate_carries_current_compatibility_without_mutating_input(self):
        for kind in ("equivalent", "substantive", "correction"):
            with self.subTest(kind=kind):
                package = revision(kind)
                package["change"]["equivalence_reason"] = "FIX仅描述变化"
                before = copy.deepcopy(package)
                result = review_goal_package(package)
                self.assertEqual(result["goal_candidate"]["version_compatibility"], {"status": "known", "value": result["compatibility"]})
                self.assertEqual(package, before)
                self.assertEqual(package["previous_goal"]["version_compatibility"]["status"], "not_applicable")

    def test_operations_resources_scope_and_formal_time_change_are_recheck(self):
        for field in ("scope", "allowed_resources", "time_requirements", "key_operations"):
            with self.subTest(field=field):
                package = revision("equivalent")
                package["change"]["equivalence_reason"] = "FIX声明等价不足以覆盖实质差异"
                if field == "key_operations":
                    package["goal"]["requirements"][0][field].append("FIX新增自主选法")
                elif field == "scope":
                    package["goal"][field].append("FIX新范围")
                else:
                    package["goal"][field] = {"status": "known", "value": ["FIX改变条件"]}
                result = review_goal_package(package)
                self.assertEqual(result["compatibility"]["status"], "recheck")
                self.assertEqual(result["compatibility"]["preserve_requirement_ids"], [])

    def test_changed_criterion_requires_increased_content_revision(self):
        package = revision("correction")
        package["goal"]["requirements"][0]["criterion"]["text"] = "FIX更正后的标准"
        result = review_goal_package(package)
        self.assertIn("criterion_revision_change", error_codes(result))
        package["goal"]["requirements"][0]["criterion_revision"] = 2
        result = review_goal_package(package)
        self.assertNotIn("criterion_revision_change", error_codes(result))
        self.assertEqual(result["compatibility"]["status"], "recheck")

    def test_revision_cannot_jump_or_decrease(self):
        for value in (1, 3, 0):
            with self.subTest(value=value):
                package = revision()
                package["goal"]["revision"] = value
                self.assertEqual(review_goal_package(package)["review_state"], "invalid")

    def test_missing_mapping_prevents_equivalence_or_automatic_split_transfer(self):
        for kind in ("equivalent", "split", "merge"):
            with self.subTest(kind=kind):
                package = revision(kind)
                package["change"]["requirement_mapping"] = []
                package["change"]["equivalence_reason"] = "FIX仅措辞"
                result = review_goal_package(package)
                self.assertIn("requirement_mapping", pending_codes(result))
                self.assertEqual(result["compatibility"]["status"], "recheck")
                self.assertEqual(result["compatibility"]["judgment_transfer"], "not_executed")

    def test_corrective_notice_proposes_restrictions_but_never_claims_executed(self):
        package = revision("correction")
        result = review_goal_package(package)
        notice = result["change_notice_candidate"]
        self.assertEqual(notice["status"], "candidate")
        self.assertEqual(notice["restriction_execution"], "not_executed")
        self.assertEqual(notice["unchecked_scope"]["status"], "unknown")
        self.assertEqual(notice["new_test"], "not_proposed")
        self.assertTrue(any("原答" in condition for condition in notice["restoration_conditions"]))

    def test_final_purpose_change_remains_pending_authorization(self):
        result = review_goal_package(revision("purpose_change"))
        self.assertEqual(result["status"], "candidate")
        self.assertIn("purpose_authorization", pending_codes(result))
        self.assertEqual(result["boundaries"]["professional_adoption"], "not_executed")

    def test_malformed_mapping_does_not_crash_or_transfer(self):
        package = revision("split")
        package["change"]["requirement_mapping"] = [{"from_requirement_ids": [{}], "to_requirement_ids": ["implement"], "relation": "FIX-malformed"}]
        result = review_goal_package(package)
        self.assertEqual(result["compatibility"]["status"], "recheck")
        self.assertIn("requirement_mapping", pending_codes(result))


class B2aStoreSeamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pl-b2a-store-FIX-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "FIX-store"
        self.package = fixture()
        self.store = LearningStore(self.root, entry_actor="AG1")
        self.store.init_workspace()
        grant = {"type": "AuthorizationGrant", "id": "FIX-b2a-goal-grant", "revision": 1, "owner": "USER", "schema_version": "pl-contracts/0.1.0", "basis_refs": [], "issuer": "USER", "grantee": "AG1", "decision_types": ["goal_design"], "object_scope": ["FIX-b2a-*"], "criterion_refs": [], "permitted_conclusions": ["FIX-目标专业候选提交"], "escalation_signals": ["FIX超出用途或任务范围"], "budget_ref": {"status": "not_required", "reason": "FIX有限提交测试，不涉及真实资源授权"}, "delegable": False, "validity": {"status": "known", "value": "FIX仅隔离测试"}, "binding_status": "verified_for_fixture"}
        self.grant_ref = {"id": grant["id"], "revision": 1}
        grant["validity"] = {"status": "known", "value": {"active": True}}
        self.assertEqual(self.store.import_fixture({"synthetic_only": True, "objects": self.package["sources"] + [grant]})["status"], "committed")

    def commit(self, goal, store=None, operation="FIX-b2a-authorized-commit"):
        target = store or self.store
        state = target.read_context()["state_revision"]
        return target.commit(state, operation, [goal], authorization_refs=[self.grant_ref], adoption_refs=[self.grant_ref])

    def manually_adopted_fixture_goal(self):
        """模拟 FIX AG1 已人工核对；不是预览函数或真实宿主的采用能力。"""
        result = review_goal_package(self.package)
        self.assertEqual(result["review_state"], "complete")
        self.assertEqual(result["boundaries"]["professional_adoption"], "not_executed")
        goal = copy.deepcopy(result["goal_candidate"])
        goal["adoption"] = {"status": "adopted", "by": "AG1", "basis_refs": [copy.deepcopy(self.grant_ref)], "reason": "FIX测试人工核对用途、来源与目标；角色仅为夹具配置"}
        return goal

    def test_preview_success_without_explicit_authorization_cannot_write(self):
        result = review_goal_package(self.package)
        before = self.store.read_context()
        self.assertEqual(result["review_state"], "complete")
        self.assertEqual(result["status"], "candidate")
        self.assertEqual(result["work_result_view"]["adoption"], {"status": "candidate"})
        rejected = self.store.commit(before["state_revision"], "FIX-b2a-no-authority", [result["goal_candidate"]])
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(self.store.read_context(), before)

    def test_manually_adopted_goal_round_trips_exact_and_old_revision_stays(self):
        goal = self.manually_adopted_fixture_goal()
        self.assertEqual(self.commit(goal)["status"], "committed")
        self.assertEqual(self.store.read_refs([{"id": goal["id"], "revision": 1}])["objects"], [goal])
        updated = copy.deepcopy(goal)
        updated["revision"] = 2
        updated["description"] = "FIX保存接缝：补充说明"
        self.assertEqual(self.commit(updated, operation="FIX-b2a-authorized-revision")["status"], "committed")
        export = self.store.export_scope([goal["id"]])
        versions = [record for record in export["objects"] if record["id"] == goal["id"]]
        self.assertEqual(versions, [goal, updated])
        reopened = LearningStore(self.root, entry_actor="AG1")
        self.assertEqual(reopened.read_refs([{"id": goal["id"], "revision": 2}])["objects"], [updated])
        self.assertEqual(reopened.check_integrity()["status"], "ok")

    def test_ag0_cannot_commit_ag1_goal_despite_preview_complete(self):
        goal = self.manually_adopted_fixture_goal()
        ag0 = LearningStore(self.root, entry_actor="AG0")
        self.assertEqual(self.commit(goal, store=ag0)["status"], "rejected")
        self.assertNotIn(goal["id"], {record["id"] for record in self.store.read_context()["objects"]})

    def test_paused_source_rejects_candidate_commit(self):
        goal = self.manually_adopted_fixture_goal()
        state = self.store.read_context()["state_revision"]
        result = self.store.pause(state, "FIX-b2a-pause", ["FIX-b2a-rule"], "FIX用户暂停来源相关活动")
        self.assertEqual(result["status"], "committed")
        self.assertEqual(self.commit(goal)["status"], "rejected")

    def test_restricted_source_rejects_candidate_commit(self):
        goal = self.manually_adopted_fixture_goal()
        state = self.store.read_context()["state_revision"]
        result = self.store.restrict(state, "FIX-b2a-restrict", ["FIX-b2a-rule"], "FIX内容待核", ["commit"])
        self.assertEqual(result["status"], "committed")
        self.assertEqual(self.commit(goal)["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
