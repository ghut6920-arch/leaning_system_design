"""B2b controlled material behavior on isolated, developer-made fixtures.

Passing these tests establishes structural coverage, never professional truth,
host identity, hidden clue detection, or an actual learner's exposure.
"""
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
from runtime.learning_materials import DOMAIN_CHECKS, MaterialsService, fact, ref
from runtime.learning_store import LearningStore


def objects_by_id(context):
    return {obj["id"]: obj for obj in context["objects"]}


def fixture():
    """Return snapshot, artifacts, material, context for tests and B2b demo.

    All changes below are in-memory fixture construction. The existing B0/B1
    originals and any demo workspace are neither overwritten nor reused.
    """
    snapshot = json.loads((ROOT / "fixtures/synthetic-baseline.json").read_text(encoding="utf-8-sig"))
    snapshot["synthetic_only"] = True
    snapshot["fixture_id"] = "B2b-synthetic-materials"
    snapshot["description"] = "人工虚构材料包；授权、检查声明和接受仅供隔离验收。"
    objects = objects_by_id(snapshot)
    artifacts = {
        "originals.md": (ROOT / "fixtures/originals.md").read_text(encoding="utf-8-sig"),
        "b2b-reference.md": (
            "# B2b 人工虚构核验原件\n"
            "OUTSIDE-BEFORE-MARKER：本行不属于受控读取范围。\n"
            "## 核验范围\n"
            "人工构造：给定 P→Q 且 P，可以按假言推理得到 Q；只核对这一步条件连接。\n"
            "OUTSIDE-AFTER-MARKER：本行也不属于受控读取范围。\n"
            "## 专业边界\n"
            "这是开发夹具，没有真实教材、学习表现或专家正确性认证。\n"
        ),
    }
    anchor = {
        "path": "b2b-reference.md", "locator": "核验范围", "revision": 1,
        "origin": "synthetic_fixture", "start_line": 3, "end_line": 4,
    }
    for identifier in ("FIX-requirement-source", "FIX-content-source"):
        source = objects[identifier]
        source["read_scope"] = {
            "text": fact("known", value="人工夹具显式片段"),
            "formula": fact("known", value="P→Q 与 P 的条件连接") if identifier == "FIX-content-source" else fact("not_required", "该要求片段仅为文字。"),
            "figure": fact("unknown", "夹具未检查图形，不能据文本提取声称已经读图。"),
        }
        source["verification"] = {
            "content": {"status": "pending", "checked_revision": 1, "scope": "人工声明的片段", "conditions": ["synthetic-only"], "anchor_refs": [], "unchecked_scope": ["专业正确性"]}
        }
        source["unread_parts"] = fact("known", value=["图形语义未核查", "片段之外未读"])
    objects["FIX-content-source"]["artifact_ref"] = copy.deepcopy(anchor)

    context = {
        "goal_refs": [ref(objects["FIX-goal"])],
        "activity_ref": ref(objects["FIX-activity"]),
        "intended_use": "independent_check", "purpose": "independent",
        "required_modalities": ["text", "formula"],
        "conditions": ["人工虚构给定前提", "初答前不给连接理由"],
    }
    material = objects["FIX-material"]
    material["intended_use"] = context["intended_use"]
    material["visible_input"] = [{"content": "P→Q；P", "provided_operations": [], "channel": "body"}]
    material["backup_help"] = [{"content": "前提 P 使 P→Q 可推出 Q。", "provided_operations": ["connect-P-to-Q"], "channel": "help_on_request"}]
    material["teacher_reference"] = [{"content": "人工教师参考：使用假言推理连接前提。", "provided_operations": ["connect-P-to-Q"], "channel": "backend_reference", "artifact_ref": copy.deepcopy(anchor)}]
    material["verification"] = {
        "content": {
            "status": "supported", "checked_revision": 1, "scope": "P 与 P→Q 到 Q 的一步人工参考",
            "conditions": copy.deepcopy(context["conditions"]), "unchecked_scope": ["figure", "复杂父任务整体", "专业正确性证明"],
            "method": "source_comparison", "reviewer": "AG2", "anchor_refs": [copy.deepcopy(anchor)], "domain": "math",
            "domain_checks": {
                "domain": fact("known", value="仅命题假言推理，前提作为给定输入。"),
                "inference": fact("known", value="该人工参考显式声明检查 P→Q 与 P 到 Q 的连接。"),
                "boundaries": fact("known", value="不覆盖逆命题、父任务整体或延迟迁移。"),
                "completeness": fact("known", value="只声明一步局部参考的条件与理由，不声称整体完成。"),
            },
        },
        "use": {
            "status": "supported", "checked_revision": 1, "scope": "当前活动独立初答用途",
            "conditions": copy.deepcopy(context["conditions"]), "unchecked_scope": ["未注释的语义线索", "实际展示"],
            "reviewer": "AG2", "binding": copy.deepcopy(context),
        },
    }
    material["leakage_risk"] = "帮助和教师参考均含关键操作，展示后需要另记真实接触。"
    material["limitations"] = ["人工虚构声明；受控锚点存在不证明专业正确性。", "未读图形保留为未知。"]
    material["actual_exposure"] = fact("unknown", "准备材料不能证明向学习者展示。")

    grant = copy.deepcopy(objects["FIX-user-grant"])
    grant.update(id="FIX-b2b-material-grant", grantee="AG2", decision_types=["material_read", "material_verification", "material_review", "material_use"], permitted_conclusions=["虚构材料包结构兼容性"], validity="隔离 B2b 夹具检查期间")
    order = copy.deepcopy(objects["FIX-work-order"])
    order.update(
        id="FIX-b2b-material-work", operation_id="FIX-b2b-material-work-operation", assignee="AG2",
        decision_needed="核对人工虚构片段和特定用途的材料包", decision_type="material_review",
        scope="当前人工虚构独立初答材料", output_contract="P-Material",
        authorization_refs=[ref(grant)], current_restrictions=[], event_refs=[],
        material_refs=[ref(material)], basis_revisions=[ref(objects["FIX-content-source"])],
        acceptance={"status": "accepted", "by": "AG2", "scope": "仅人工材料检查", "next_trigger": "收到人工材料修订"},
        next_trigger="手动人工夹具调用",
    )
    snapshot["objects"].extend([grant, order])
    return snapshot, artifacts, copy.deepcopy(material), context


class B2bMaterialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pl-b2b-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        self.snapshot, self.artifacts, self.material, self.context = fixture()
        self.store = LearningStore(self.root, entry_actor="AG2")
        self.assertEqual(self.store.init_workspace()["status"], "committed")
        seeded = self.store.import_fixture(self.snapshot, self.artifacts)
        self.assertEqual(seeded["status"], "committed", seeded)
        self.service = MaterialsService(self.store)

    def revision(self):
        return self.store.read_context()["state_revision"]

    def source(self):
        return copy.deepcopy(objects_by_id(self.snapshot)["FIX-content-source"])

    def inspect(self, material=None, context=None, incoming=None):
        return self.service.inspect_material(material or self.material, context or self.context, incoming)

    def codes(self, result):
        return {item["code"] for item in result.get("reasons", [])}

    def assert_limited(self, result, code):
        self.assertEqual(result["status"], "limited", result)
        self.assertIn(code, self.codes(result), result)
        self.assertFalse(result["mutated"])

    def rebind(self, material, context):
        material["intended_use"] = context["intended_use"]
        material["verification"]["use"]["binding"] = copy.deepcopy(context)

    def read_request(self):
        return {
            "fragment_id": "FIX-b2b-extracted",
            "source_ref": {"source_id": "FIX-B2B-REFERENCE", "declared_revision": "fixture/1", "locator": "b2b-reference.md#核验范围", "identity_kind": "synthetic"},
            "artifact_ref": {"path": "b2b-reference.md", "locator": "核验范围", "revision": 1, "origin": "synthetic_fixture"},
            "start_line": 3, "end_line": 4,
        }

    def submission(self, operation="FIX-b2b-submit", material=None):
        candidate = copy.deepcopy(material or self.material)
        candidate["revision"] += 1
        for verification in candidate["verification"].values():
            verification["checked_revision"] = candidate["revision"]
        grant_ref = {"id": "FIX-b2b-material-grant", "revision": 1}
        work_ref = {"id": "FIX-b2b-material-work", "revision": 1}
        candidate["basis_refs"].append(work_ref)
        result = {
            "type": "WorkResult", "id": "FIX-b2b-material-result", "revision": 1,
            "owner": "AG2", "schema_version": candidate["schema_version"], "basis_refs": [work_ref],
            "work_order_ref": work_ref, "decision_type": "material_review",
            "handled_scope": "人工材料当前修订的结构检查", "unhandled_scope": "专业正确性与实际展示",
            "result_refs": [ref(candidate)], "limitations": ["仅人工夹具"], "adoption_needed": True,
            "next_owner": "AG0", "next_trigger": "用户明确调用教学入口", "compatibility": fact("known", value="人工包结构兼容"),
            "adoption": {"status": "adopted", "by": "AG2", "scope": "人工材料包", "basis_refs": [work_ref], "limitations": ["未部署真实 AG2"], "time": fact("not_executed", "无真实采用时间。")},
        }
        return {
            "expected_state_revision": self.revision(), "operation_id": operation,
            "changes": [candidate, result], "artifacts": {}, "context": copy.deepcopy(self.context),
            "authorization_refs": [grant_ref], "adoption_refs": [work_ref],
        }

    def test_controlled_read_returns_only_selected_lines_and_no_semantic_upgrade(self):
        before = self.store.read_context()
        result = self.service.read_fragment(self.read_request())
        self.assertEqual(result["status"], "candidate", result)
        self.assertEqual(result["text"], "".join(self.artifacts["b2b-reference.md"].splitlines(keepends=True)[2:4]))
        self.assertNotIn("OUTSIDE-BEFORE-MARKER", json.dumps(result))
        self.assertNotIn("OUTSIDE-AFTER-MARKER", json.dumps(result))
        self.assertEqual(result["fragment"]["read_scope"]["text"]["value"]["start_line"], 3)
        for modality in ("formula", "figure"):
            self.assertEqual(result["fragment"]["read_scope"][modality]["status"], "unknown")
        self.assertEqual(result["fragment"]["verification"]["content"]["status"], "pending")
        self.assertEqual(result["semantic_verification"], "not_executed")
        self.assertEqual(before, self.store.read_context())

    def test_goal_source_modality_scope_does_not_supply_material_required_modality(self):
        source = self.source()
        source["read_scope"]["formula"] = fact("unknown", "只有文本核验声明，未读清本材料用途所需公式。")
        source["verification"]["content"].update(status="supported", reviewer="AG2",
            method="source_comparison", required_modalities=["text"],
            anchor_refs=[copy.deepcopy(source["artifact_ref"])])
        before = self.store.read_context()
        result = self.inspect(incoming=[source])
        self.assert_limited(result, "required_modality_unread")
        self.assertEqual(source["read_scope"]["formula"]["status"], "unknown")
        self.assertEqual(self.store.read_context(), before)

    def test_read_rejects_bad_ranges_external_paths_and_locator_outside_segment(self):
        for start, end in ((0, 4), (4, 3), (True, 4), (3, 999)):
            with self.subTest(start=start, end=end):
                request = self.read_request()
                request.update(start_line=start, end_line=end)
                result = self.service.read_fragment(request)
                self.assertEqual(result["status"], "rejected")
                self.assertNotIn("text", result)
                self.assertNotIn("fragment", result)
        for path in ("../b2b-reference.md", "C:/private.md", "unknown.md"):
            with self.subTest(path=path):
                request = self.read_request()
                request["artifact_ref"]["path"] = path
                self.assertEqual(self.service.read_fragment(request)["status"], "rejected")
        request = self.read_request()
        request.update(start_line=6, end_line=7)
        self.assertIn("artifact_locator_outside_segment", self.codes(self.service.read_fragment(request)))

    def test_read_real_identity_is_rejected_before_extraction(self):
        request = self.read_request()
        request["source_ref"]["identity_kind"] = "real"
        result = self.service.read_fragment(request)
        self.assertEqual(result["status"], "rejected")
        self.assertIn("synthetic_source_required", self.codes(result))
        self.assertNotIn("text", result)

    def test_read_honors_current_restriction_pause_and_delete_controls(self):
        for control in ("restrict", "pause", "delete"):
            with self.subTest(control=control):
                root = Path(self.temp.name) / control
                store = LearningStore(root, entry_actor="AG2")
                store.init_workspace()
                self.assertEqual(store.import_fixture(self.snapshot, self.artifacts)["status"], "committed")
                if control == "restrict":
                    gate = store.restrict(1, "FIX-read-restrict", ["FIX-content-source"], "人工读取限制", ["material_read"])
                elif control == "pause":
                    gate = store.pause(1, "FIX-read-pause", ["FIX-content-source"], "人工暂停")
                else:
                    gate = store.delete_scope(1, "FIX-read-delete", ["FIX-content-source"])
                self.assertEqual(gate["status"], "committed", gate)
                result = MaterialsService(store).read_fragment(self.read_request())
                self.assertNotEqual(result["status"], "candidate")
                self.assertNotIn("text", result)
                self.assertNotIn("fragment", result)

    def test_explicit_modalities_and_complete_math_declarations_form_compatible_packet(self):
        result = self.inspect()
        self.assertEqual(result["status"], "compatible", result)
        self.assertFalse(result["mutated"])
        self.assertEqual(result["substituted_operations"], [])
        self.assertEqual(result["potential_help_operations"], ["connect-P-to-Q"])
        self.assertEqual(self.revision(), 1)
        self.assertTrue(result["limitations"])
        self.assertIn("not truth", result["limitations"][0])

    def test_every_modality_must_be_explicit_even_when_not_required(self):
        for modality in ("text", "formula", "figure"):
            with self.subTest(modality=modality):
                source = self.source()
                del source["read_scope"][modality]
                self.assert_limited(self.inspect(incoming=[source]), "modality_facts_required")
        source = self.source()
        source["read_scope"]["figure"] = "没有图"
        self.assert_limited(self.inspect(incoming=[source]), "modality_facts_required")

    def test_unread_required_formula_or_figure_limits_and_unknown_nonrequired_is_preserved(self):
        source = self.source()
        source["read_scope"]["formula"] = fact("unknown", "尚未读公式。")
        self.assert_limited(self.inspect(incoming=[source]), "required_modality_unread")
        context = copy.deepcopy(self.context)
        context["required_modalities"] = ["text", "formula", "figure"]
        material = copy.deepcopy(self.material)
        self.rebind(material, context)
        self.assert_limited(self.inspect(material, context), "required_modality_unread")
        original = copy.deepcopy(source)
        context["required_modalities"] = ["text"]
        self.rebind(material, context)
        self.assertEqual(self.inspect(material, context, [source])["status"], "compatible")
        self.assertEqual(source, original)
        self.assertEqual(source["read_scope"]["formula"]["status"], "unknown")

    def test_missing_unread_scope_and_unspecified_required_modalities_are_rejected(self):
        source = self.source()
        del source["unread_parts"]
        self.assert_limited(self.inspect(incoming=[source]), "unread_scope_required")
        for modalities in (None, [], ["video"]):
            with self.subTest(modalities=modalities):
                context = copy.deepcopy(self.context)
                context["required_modalities"] = modalities
                result = self.inspect(context=context)
                self.assertEqual(result["status"], "rejected")
                self.assertIn("required_modalities_required", self.codes(result))

    def test_math_reference_anchor_must_exist_be_usable_and_cover_a_real_segment(self):
        for change in ("missing", "unavailable", "outside"):
            with self.subTest(change=change):
                material = copy.deepcopy(self.material)
                content = material["verification"]["content"]
                if change == "missing":
                    content["anchor_refs"] = []
                    code = "verification_anchor_required"
                elif change == "unavailable":
                    content["anchor_refs"][0]["path"] = "nonexistent-reference.md"
                    code = "verification_anchor_unavailable"
                else:
                    content["anchor_refs"][0]["end_line"] = 999
                    code = "verification_anchor_unavailable"
                self.assert_limited(self.inspect(material), code)

    def test_each_math_domain_check_is_required_and_unknown_cannot_be_supported(self):
        for key in ("domain", "inference", "boundaries", "completeness"):
            for mode in ("missing", "unknown"):
                with self.subTest(key=key, mode=mode):
                    material = copy.deepcopy(self.material)
                    checks = material["verification"]["content"]["domain_checks"]
                    if mode == "missing":
                        del checks[key]
                    else:
                        checks[key] = fact("unknown", "此项尚未核验。")
                    self.assert_limited(self.inspect(material), "domain_checks_incomplete")

    def test_domain_packets_have_distinct_required_checks_and_no_truth_certificate(self):
        expected = {
            "ai": ("specification", "environment", "normal_cases", "edge_cases", "interpretation"),
            "finance": ("assumptions", "units", "data_time", "scenario"),
            "politics": ("sources", "fact_interpretation_values", "competing_explanations", "causal_limits"),
        }
        declarations = {
            "ai": {
                "specification": "人工代码行为规格，未执行代码。", "environment": "仅声明 Python 夹具版本和依赖。",
                "normal_cases": "普通输入只作结构性例示。", "edge_cases": "空输入和边界输入声明待专业核验。", "interpretation": "声明用途和概念解释覆盖，运行成功不等于教学正确。",
            },
            "finance": {
                "assumptions": "虚构利率假设，不作收益承诺。", "units": "金额与比例单位仅人工声明。",
                "data_time": "人工数据版本 fixture/1，无真实行情。", "scenario": "虚构涨跌情景，不作投资建议。",
            },
            "politics": {
                "sources": "仅人工虚构引用来源。", "fact_interpretation_values": "声明区分事实描述、解释与价值选择。",
                "competing_explanations": "人工构造替代解释。", "causal_limits": "列举相关性不证明因果。",
            },
        }
        for domain, keys in expected.items():
            with self.subTest(domain=domain):
                self.assertEqual(DOMAIN_CHECKS[domain], keys)
                material = copy.deepcopy(self.material)
                content = material["verification"]["content"]
                content["domain"] = domain
                content["domain_checks"] = {key: fact("known", value=declarations[domain][key]) for key in keys}
                result = self.inspect(material)
                self.assertEqual(result["status"], "compatible", result)
                self.assertEqual(result["semantic_verification"], "agent_declaration_with_managed_anchors")
                self.assertTrue(result["limitations"])
                for key in keys:
                    omitted = copy.deepcopy(material)
                    del omitted["verification"]["content"]["domain_checks"][key]
                    self.assert_limited(self.inspect(omitted), "domain_checks_incomplete")

    def test_supported_text_with_pending_correctness_or_use_does_not_pass(self):
        for part in ("content", "use"):
            for status in ("partial", "pending", "error"):
                with self.subTest(part=part, status=status):
                    material = copy.deepcopy(self.material)
                    material["verification"][part]["status"] = status
                    self.assert_limited(self.inspect(material), "limited_or_pending_verification")

    def test_content_and_use_reviews_must_match_current_material_revision(self):
        for part in ("content", "use"):
            with self.subTest(part=part):
                material = copy.deepcopy(self.material)
                material["revision"] = 2
                material["verification"][part]["checked_revision"] = 2
                self.assert_limited(self.inspect(material), "verification_scope_required")

    def test_teaching_example_requires_a_fresh_exact_binding_for_independent_check(self):
        context = copy.deepcopy(self.context)
        context.update(purpose="teaching", intended_use="teaching")
        material = copy.deepcopy(self.material)
        material["visible_input"].append({"content": "由 P 和 P→Q 连接得到 Q。", "provided_operations": ["connect-P-to-Q"], "channel": "worked_example"})
        self.rebind(material, context)
        self.assertEqual(self.inspect(material, context)["status"], "compatible")
        independent = copy.deepcopy(self.context)
        result = self.inspect(material, independent)
        self.assert_limited(result, "use_binding_mismatch")
        self.assertIn("target_operation_provided", self.codes(result))
        self.rebind(material, independent)
        self.assert_limited(self.inspect(material, independent), "target_operation_provided")
        material["visible_input"] = copy.deepcopy(self.material["visible_input"])
        self.assertEqual(self.inspect(material, independent)["status"], "compatible")

    def test_binding_checks_activity_conditions_goals_modalities_and_purpose(self):
        changes = {
            "activity_ref": {"id": "FIX-parent-activity", "revision": 1},
            "conditions": ["不同虚构条件"], "required_modalities": ["text"],
            "purpose": "comparison", "intended_use": "comparison",
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                context = copy.deepcopy(self.context)
                context[field] = value
                self.assert_limited(self.inspect(context=context), "use_binding_mismatch")
        material = copy.deepcopy(self.material)
        material["verification"]["use"]["binding"]["goal_refs"] = []
        self.assert_limited(self.inspect(material), "use_binding_mismatch")

    def test_annotated_title_layout_and_body_cannot_supply_independent_target_operation(self):
        for channel in ("title", "layout", "body"):
            with self.subTest(channel=channel):
                material = copy.deepcopy(self.material)
                material["visible_input"].append({"content": "人工注释：排列或标题已给连接理由。", "provided_operations": ["connect-P-to-Q"], "channel": channel})
                result = self.inspect(material)
                self.assert_limited(result, "target_operation_provided")
                self.assertEqual(result["substituted_operations"], ["connect-P-to-Q"])

    def test_backup_help_and_teacher_reference_are_potential_help_not_actual_exposure(self):
        before = copy.deepcopy(self.material)
        result = self.inspect()
        self.assertEqual(result["status"], "compatible")
        self.assertEqual(result["substituted_operations"], [])
        self.assertEqual(result["potential_help_operations"], ["connect-P-to-Q"])
        self.assertEqual(self.material["actual_exposure"]["status"], "unknown")
        self.assertEqual(self.material, before)
        material = copy.deepcopy(self.material)
        material["actual_exposure"] = fact("known", value=["材料已被展示"])
        self.assert_limited(self.inspect(material), "preparation_cannot_record_exposure")

    def test_partition_entries_need_content_channel_and_provided_operation_annotation(self):
        for partition in ("visible_input", "backup_help", "teacher_reference"):
            for missing in ("content", "channel", "provided_operations"):
                with self.subTest(partition=partition, missing=missing):
                    material = copy.deepcopy(self.material)
                    del material[partition][0][missing]
                    self.assert_limited(self.inspect(material), "presentation_annotation_required")

    def test_submission_is_persistent_after_reopen_and_preserves_original_event_and_plan(self):
        before = objects_by_id(self.store.read_context())
        request = self.submission()
        result = self.service.submit_material(request)
        self.assertEqual(result["status"], "committed", result)
        reopened = LearningStore(self.root, entry_actor="AG2")
        after = objects_by_id(reopened.read_context())
        self.assertEqual(after["FIX-material"], request["changes"][0])
        self.assertEqual(after["FIX-b2b-material-result"], request["changes"][1])
        for identifier in ("FIX-event", "FIX-plan", "FIX-goal", "FIX-activity"):
            self.assertEqual(after[identifier], before[identifier])
        exported = reopened.export_scope(["FIX-material"], include_artifacts=True)
        self.assertEqual(exported["status"], "ok")
        self.assertEqual(exported["artifacts"]["b2b-reference.md"], self.artifacts["b2b-reference.md"])
        self.assertEqual(reopened.check_integrity()["status"], "ok")

    def test_submit_uses_explicit_authority_and_adoption_and_ag2_actor(self):
        for field in ("authorization_refs", "adoption_refs"):
            with self.subTest(field=field):
                request = self.submission("FIX-missing-" + field)
                request[field] = []
                result = self.service.submit_material(request)
                self.assertEqual(result["status"], "rejected", result)
                self.assertIn("professional_receipt_required", self.codes(result))
                self.assertEqual(self.revision(), 1)
        result = MaterialsService(LearningStore(self.root, entry_actor="AG0")).submit_material(self.submission())
        self.assertEqual(result["status"], "rejected")
        self.assertIn("ag2_fixture_actor_required", self.codes(result))

    def test_source_fragment_cannot_bypass_professional_grant_via_read_only_origin(self):
        source = self.source()
        source["revision"] = 2
        source["verification"]["content"]["checked_revision"] = 2
        result = self.service.submit_material({
            "expected_state_revision": 1, "operation_id": "FIX-source-without-grant",
            "changes": [source], "artifacts": {}, "authorization_refs": [],
            "adoption_refs": [{"id": "FIX-b2b-material-work", "revision": 1}],
        })
        self.assertEqual(result["status"], "rejected", result)
        self.assertIn("professional_receipt_required", self.codes(result))
        self.assertEqual(objects_by_id(self.store.read_context())["FIX-content-source"]["revision"], 1)
        self.assertEqual(self.revision(), 1)

    def test_submit_permission_and_work_order_acceptance_are_not_inferred(self):
        request = self.submission("FIX-wrong-grant")
        request["authorization_refs"] = [{"id": "FIX-user-grant", "revision": 1}]
        result = self.service.submit_material(request)
        self.assertEqual(result["status"], "rejected")
        self.assertIn("authorization_scope", self.codes(result))
        request = self.submission("FIX-wrong-work")
        request["changes"][1]["work_order_ref"] = {"id": "FIX-work-order", "revision": 1}
        result = self.service.submit_material(request)
        self.assertEqual(result["status"], "rejected")
        self.assertIn("accepted_material_work_required", self.codes(result))
        self.assertEqual(self.revision(), 1)

    def test_submission_same_operation_and_bytes_is_idempotent_but_changed_bytes_rejected(self):
        request = self.submission("FIX-b2b-idempotent")
        first = self.service.submit_material(request)
        second = self.service.submit_material(copy.deepcopy(request))
        self.assertEqual(first["status"], "committed", first)
        self.assertEqual(second, first)
        self.assertEqual(self.revision(), first["state_revision"])
        modified = copy.deepcopy(request)
        modified["changes"][0]["limitations"].append("FIX-CHANGED-RETRY-PAYLOAD")
        result = self.service.submit_material(modified)
        self.assertEqual(result["status"], "rejected")
        self.assertIn("operation_id_reused", self.codes(result))
        saved = objects_by_id(self.store.read_context())["FIX-material"]
        self.assertNotIn("FIX-CHANGED-RETRY-PAYLOAD", saved["limitations"])

    def test_submit_rejects_stale_state_and_stale_source_basis_without_writing(self):
        stale = self.submission("FIX-stale-state")
        gate = self.store.pause(1, "FIX-unrelated-pause", ["FIX-method"], "人工无关暂停")
        self.assertEqual(gate["status"], "committed")
        result = self.service.submit_material(stale)
        self.assertEqual(result["status"], "conflict", result)
        self.assertEqual(objects_by_id(self.store.read_context())["FIX-material"]["revision"], 1)
        source = self.source()
        source["revision"] = 2
        source["verification"]["content"]["checked_revision"] = 2
        grant = {"id": "FIX-b2b-material-grant", "revision": 1}
        work = {"id": "FIX-b2b-material-work", "revision": 1}
        committed = self.store.commit(self.revision(), "FIX-source-second-revision", [source], authorization_refs=[grant], adoption_refs=[work])
        self.assertEqual(committed["status"], "committed", committed)
        self.assert_limited(self.inspect(), "stale_basis_reference")
        result = self.service.submit_material(self.submission("FIX-stale-source"))
        self.assertEqual(result["status"], "rejected", result)
        self.assertIn("stale_basis_reference", self.codes(result))
        self.assertEqual(objects_by_id(self.store.read_context())["FIX-material"]["revision"], 1)

    def test_late_submission_after_delete_cannot_reintroduce_objects_or_artifacts(self):
        request = self.submission("FIX-b2b-late-result")
        deleted = self.store.delete_scope(1, "FIX-b2b-delete", ["FIX-content-source"])
        self.assertEqual(deleted["status"], "committed", deleted)
        request["expected_state_revision"] = self.revision()
        result = self.service.submit_material(request)
        self.assertEqual(result["status"], "rejected", result)
        ids = objects_by_id(self.store.read_context())
        self.assertNotIn("FIX-material", ids)
        self.assertNotIn("FIX-b2b-material-result", ids)
        reread = self.service.read_fragment(self.read_request())
        self.assertNotEqual(reread["status"], "candidate")
        self.assertNotIn("text", reread)

    def test_material_restriction_beats_success_receipt_and_user_resume_does_not_restore(self):
        request = self.submission("FIX-material-first")
        self.assertEqual(self.service.submit_material(request)["status"], "committed")
        gate = self.store.restrict(self.revision(), "FIX-material-stop", ["FIX-content-source"], "人工内容待复查", ["material_review", "independent_check"])
        self.assertEqual(gate["status"], "committed")
        result = self.service.submit_material(request)
        self.assertEqual(result["status"], "rejected", result)
        result = self.inspect()
        self.assertEqual(result["status"], "blocked", result)
        resumed = self.store.resume(self.revision(), "FIX-material-resume", ["FIX-content-source"])
        self.assertEqual(resumed["status"], "committed")
        self.assertEqual(self.inspect()["status"], "blocked")

    def test_two_source_chains_trace_separately_and_four_recoveries_stay_pending(self):
        before = self.store.read_context()
        traced = self.service.trace_change({"changed_refs": [{"id": "FIX-requirement-source", "revision": 1}, {"id": "FIX-content-source", "revision": 1}]})
        self.assertEqual(traced["status"], "candidate", traced)
        edges = traced["direct_dependencies"]
        self.assertTrue(any(edge["from_ref"]["id"] == "FIX-requirement-source" and edge["to_ref"]["id"] == "FIX-goal" and edge["relation"] == "requirement_source_refs" and edge["chain"] == "requirement" for edge in edges))
        self.assertTrue(any(edge["from_ref"]["id"] == "FIX-content-source" and edge["to_ref"]["id"] == "FIX-goal" and edge["relation"] == "content_basis_refs" and edge["chain"] == "content" for edge in edges))
        nested_content = [edge for edge in edges if edge["to_ref"]["id"] == "FIX-goal" and edge["relation"] == "requirements" and "content_basis_refs" in edge["locator"]]
        self.assertTrue(nested_content)
        self.assertTrue(all(edge["chain"] == "content" for edge in nested_content))
        affected = {item["id"] for item in traced["affected_refs"]}
        self.assertTrue({"FIX-goal", "FIX-material", "FIX-event", "FIX-plan", "FIX-judgment"}.issubset(affected))
        self.assertEqual(traced["unknown_dependencies"]["status"], "unknown")
        self.assertTrue(traced["unknown_dependencies"]["reason"])
        recovery = traced["recovery"]
        owners = {"material_recovery": "AG2", "judgment_recovery": "AG3", "teaching_recovery": "AG0", "planning_recovery": "AG1"}
        self.assertEqual(set(recovery), set(owners))
        for name, owner in owners.items():
            self.assertEqual(recovery[name]["owner"], owner)
            self.assertEqual(recovery[name]["status"], "pending")
            self.assertTrue(recovery[name]["action"])
        self.assertFalse(traced["professional_restrictions_lifted"])
        self.assertFalse(traced["mutated"])
        self.assertEqual(self.store.read_context(), before)

    def test_unknown_semantic_dependencies_and_sufficient_original_do_not_create_extra_work(self):
        before = self.store.read_context()
        before_export = self.store.export_scope(["FIX-event", "FIX-plan", "FIX-material"], include_artifacts=True)
        for _ in range(2):
            inspection = self.inspect()
            self.assertEqual(inspection["status"], "compatible")
            traced = self.service.trace_change({"changed_refs": [{"id": "FIX-content-source", "revision": 1}]})
            self.assertEqual(traced["unknown_dependencies"]["status"], "unknown")
            self.assertIn("sufficient original responses", traced["recovery"]["judgment_recovery"]["action"])
            self.assertIn("without automatically adding a test", traced["recovery"]["judgment_recovery"]["action"])
        self.assertEqual(self.store.read_context(), before)
        self.assertEqual(self.store.export_scope(["FIX-event", "FIX-plan", "FIX-material"], include_artifacts=True), before_export)
        self.assertEqual(self.revision(), 1)

    def test_trace_after_restriction_preserves_all_originals_and_plan_and_keeps_gate(self):
        before = objects_by_id(self.store.read_context())
        gate = self.store.restrict(1, "FIX-trace-stop", ["FIX-content-source"], "人工内容纠错先限制使用", ["material_review", "independent_check", "teaching", "assessment"])
        self.assertEqual(gate["status"], "committed")
        traced = self.service.trace_change({"changed_refs": [{"id": "FIX-content-source", "revision": 1}]})
        self.assertEqual(traced["status"], "candidate", traced)
        self.assertTrue(all(recovery["status"] == "pending" for recovery in traced["recovery"].values()))
        self.assertFalse(traced["professional_restrictions_lifted"])
        after = objects_by_id(self.store.read_context())
        for identifier in ("FIX-event", "FIX-plan", "FIX-goal", "FIX-judgment", "FIX-material"):
            self.assertEqual(after[identifier], before[identifier])
        self.assertEqual(self.store.validate_refs([{"id": "FIX-content-source", "revision": 1}], "independent_check")["status"], "rejected")

    def test_real_cli_change_restrict_commits_gate_before_read_only_recovery_trace(self):
        before = objects_by_id(self.store.read_context())
        request_path = Path(self.temp.name) / "caller-owned-cli-request.json"
        request_path.write_text(json.dumps({
            "changed_refs": [{"id": "FIX-content-source", "revision": 1}],
            "expected_state_revision": 1, "operation_id": "FIX-cli-change-restrict",
            "reason": "人工内容纠错先限制使用",
            "intended_uses": ["material_review", "independent_check", "teaching", "assessment"],
        }, ensure_ascii=False), encoding="utf-8")
        completed = subprocess.run([
            sys.executable, str(ROOT / "src/runtime/learning_materials.py"),
            "--workspace", str(self.root), "--request", str(request_path), "change", "--restrict",
        ], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        traced = json.loads(completed.stdout)
        self.assertEqual(traced["status"], "candidate", traced)
        self.assertTrue(traced["mutated"])
        self.assertEqual(traced["control_receipt"]["status"], "committed")
        self.assertEqual(traced["state_revision"], traced["control_receipt"]["state_revision"])
        self.assertEqual(traced["state_revision"], 2)
        self.assertTrue(all(item["status"] == "pending" for item in traced["recovery"].values()))
        self.assertFalse(traced["professional_restrictions_lifted"])
        self.assertEqual(self.inspect()["status"], "blocked")
        after = objects_by_id(self.store.read_context())
        for identifier in ("FIX-event", "FIX-plan", "FIX-goal", "FIX-judgment", "FIX-material"):
            self.assertEqual(after[identifier], before[identifier])
        self.assertTrue(request_path.exists(), "调用方请求文件不属于受控删除范围。")


if __name__ == "__main__":
    unittest.main(verbosity=2)
