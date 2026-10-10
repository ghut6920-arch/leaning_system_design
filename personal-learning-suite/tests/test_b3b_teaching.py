"""C0 behavior on isolated developer-made tasks, never learner evaluation.

The material declarations, permissions, answers and times below are synthetic.
Passing establishes preservation and control behavior, not semantic scoring,
professional correctness, authenticated authority or real learning effects.
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
sys.path.insert(0, str(ROOT / "tests"))
from runtime.learning_materials import fact, ref
from runtime.learning_store import LearningStore
from runtime.learning_teaching import TeachingService
from test_b2b_materials import fixture as material_fixture, objects_by_id


EVENT_ID = "FIX-b3b-event"
SAMPLE_ID = "FIX-b3b-sample"
GRANT_ID = "FIX-b3b-teaching-grant"
INITIAL_PATH = "b3b-initial.md"
REVISION_PATH = "b3b-revision.md"
INITIAL_TEXT = "# B3b-initial\nQ。\n"
REVISION_TEXT = "# B3b-revision\nP 成立且 P→Q，所以 Q。\n"


def anchor(path, locator):
    return {"path": path, "locator": locator, "revision": 1, "origin": "synthetic_fixture",
            "start_line": 1, "end_line": 2}


def fixture():
    """Extend the B2b fixture only in memory, preserving all baseline files."""
    snapshot, artifacts, material, context = material_fixture()
    snapshot["fixture_id"] = "B3b-synthetic-C0"
    snapshot["description"] = "人工虚构 C0 活动；不是真实课程、执行授权或学习结果。"
    objects = objects_by_id(snapshot)
    grant = copy.deepcopy(objects["FIX-user-grant"])
    grant.update(
        id=GRANT_ID, grantee="AG0", decision_types=["teaching_execution"],
        permitted_conclusions=["仅保存人工 C0 表现及按预定分支交接，不作掌握判断"],
        validity="隔离 B3b 夹具运行期间",
    )
    snapshot["objects"].append(grant)
    activity = objects["FIX-activity"]
    activity["authority_refs"].append(ref(grant))
    activity["task_qualification"] = fact("known", value={
        "target_operations": ["connect-P-to-Q"],
        "not_substituted": fact("known", value=True),
        "prerequisite_fit": fact("known", value=True),
        "reference_scorable": fact("known", value=True),
        "evidence_conditions": fact("known", value=True),
    })
    activity["branches"] = [{
        "observation": "初答只有结论，未写出前提连接理由",
        "action": "使用已核验的一步参考反馈，并要求学习者写出连接理由",
        "next_observation": "学习者能否将参考支持用于同一题的修订",
        "counterevidence": "如果原件已有完整理由，则直接复用，不追加纠错",
        "stop": "局部够用返回父任务；预算结束或暂停立即停止",
        "reference_refs": copy.deepcopy(material["verification"]["content"]["anchor_refs"]),
        "learner_next_work": "在同一题原有事件中写出 P 与 P→Q 的连接理由",
    }]
    material["backup_help"][0]["content"] = "B3B-BACKUP-SECRET：前提 P 使 P→Q 可推出 Q。"
    material["teacher_reference"][0]["content"] = "B3B-TEACHER-SECRET：人工参考的假言推理连接。"
    objects["FIX-material"].update(material)
    return snapshot, artifacts, context


def initial_request(state_revision=1, operation_id="FIX-b3b-initial"):
    """Concrete synthetic initial answer request, shared with the demo."""
    _, _, context = fixture()
    return {
        "synthetic_only": True, "action": "record_initial",
        "activity_ref": {"id": "FIX-activity", "revision": 1},
        "context": context, "expected_state_revision": state_revision,
        "operation_id": operation_id,
        "authorization_refs": [{"id": GRANT_ID, "revision": 1}],
        "event_id": EVENT_ID, "independent_sample_id": SAMPLE_ID,
        "original_response": anchor(INITIAL_PATH, "B3b-initial"),
        "artifacts": {INITIAL_PATH: INITIAL_TEXT},
        "initial_response": {
            "content": "Q。", "visibility": "displayed",
            "target_operations": ["connect-P-to-Q"], "substituted_operations": [],
            "time": fact("unknown", "人工顺序，不虚构实际发生时间"),
        },
        "occurred_at": fact("not_executed", "人工夹具没有真实事件时间"),
        "contact_history": fact("unknown", "人工人物无可靠先前接触资料"),
        "actual_resources": fact("known", value=["题面给定前提"]),
        "contributors": [{"actor": "synthetic_learner", "operations": ["写出结论 Q"]}],
    }


class B3bTeachingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pl-b3b-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        self.snapshot, self.artifacts, self.binding = fixture()
        self.store = self.seed(self.snapshot, self.artifacts)
        self.service = TeachingService(self.store)

    def seed(self, snapshot, artifacts, name="workspace", actor="AG0"):
        store = LearningStore(Path(self.temp.name) / name, entry_actor=actor)
        self.assertEqual(store.init_workspace()["status"], "committed")
        result = store.import_fixture(snapshot, artifacts)
        self.assertEqual(result["status"], "committed", result)
        return store

    def state(self, store=None):
        result = (store or self.store).read_context()
        self.assertEqual(result["status"], "ok", result)
        return result

    def revision(self, store=None):
        return self.state(store)["state_revision"]

    def objects(self, store=None):
        return objects_by_id(self.state(store))

    def event(self, store=None):
        return self.objects(store)[EVENT_ID]

    def request(self, action, **fields):
        request = {
            "synthetic_only": True, "action": action,
            "activity_ref": {"id": "FIX-activity", "revision": 1},
            "context": copy.deepcopy(self.binding),
            "authorization_refs": [{"id": GRANT_ID, "revision": 1}],
        }
        if action not in ("open", "resume"):
            request.update(expected_state_revision=self.revision(), operation_id="FIX-b3b-" + action)
        request.update(fields)
        return request

    def execute(self, action, **fields):
        return self.service.run(self.request(action, **fields))

    def codes(self, result):
        return {reason["code"] for reason in result.get("reasons", [])}

    def assert_unsaved(self, result):
        self.assertIn(result["status"], ("rejected", "blocked", "limited", "conflict", "stopped", "not_ready"), result)
        self.assertFalse(result.get("mutated", False), result)

    def initial(self, **fields):
        request = initial_request(self.revision())
        request.update(fields)
        result = self.service.run(request)
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(result["event_ref"], ref(self.event()))
        return result

    def help(self, visibility="displayed", **fields):
        help_value = {
            "content": "前提 P 使 P→Q 可推出 Q。", "visibility": visibility,
            "target_operations": ["connect-P-to-Q"],
            "substituted_operations": ["connect-P-to-Q"],
            "time": fact("unknown", "人工帮助顺序，无真实时间"),
        }
        request = self.request("record_help", event_ref=ref(self.event()), help=help_value)
        request.update(fields)
        return self.service.run(request)

    def revise(self, **fields):
        return self.execute("record_revision", event_ref=ref(self.event()),
                        revision_response=anchor(REVISION_PATH, "B3b-revision"),
                        artifacts={REVISION_PATH: REVISION_TEXT}, revision={
                            "content": "P 成立且 P→Q，所以 Q。", "visibility": "displayed",
                            "target_operations": ["connect-P-to-Q"], "substituted_operations": [],
                            "time": fact("unknown", "人工修订顺序，无真实时间"),
                        }, **fields)

    def feedback_request(self, **fields):
        event_ref = fields.pop("event_ref", None) or ref(self.event())
        request = self.request("record_feedback", event_ref=event_ref, branch_index=0,
                               observation={"artifact_ref": anchor(INITIAL_PATH, "B3b-initial"), "quote": "Q。"},
                               feedback={
                                   "content": "原答写出了 Q，请将给定前提连接写成理由。",
                                   "visibility": "displayed", "target_operations": ["connect-P-to-Q"],
                                   "substituted_operations": [],
                                   "time": fact("unknown", "人工反馈顺序，无真实时间"),
                               })
        request.update(fields)
        return request

    def close_request(self, **fields):
        request = self.request("close", event_ref=ref(self.event()), checkpoint_id="FIX-b3b-checkpoint",
                               stop_reason="当前局部支持够用", next_connection="返回同一父产物的第二步连接",
                               pending_owners=["AG3", "AG1"],
                               unrecorded_actions=fact("unknown", "不声称未保存期间无额外接触"),
                               unfinished_requirement_ids=[],
                               closure={"status": "local_sufficient", "reason": "按给定人工范围收束，不评估掌握"})
        request.update(fields)
        return request

    def test_open_is_read_only_and_separates_backup_and_teacher_reference(self):
        before = self.state()
        result = self.execute("open")
        self.assertEqual(result["status"], "ready", result)
        packet = result["learner_packet"]
        self.assertEqual(packet["prompt"], self.objects()["FIX-activity"]["prompt"])
        self.assertEqual(packet["visible_input"], self.objects()["FIX-material"]["visible_input"])
        for secret in ("B3B-BACKUP-SECRET", "B3B-TEACHER-SECRET", "backup_help", "teacher_reference"):
            self.assertNotIn(secret, json.dumps(result, ensure_ascii=False))
        self.assertEqual(result["scoring"], "not_executed")
        self.assertEqual(self.state(), before)

    def test_canonical_qualification_and_explicit_legacy_boolean_adapter(self):
        self.assertEqual(self.execute("open")["status"], "ready")
        snapshot = copy.deepcopy(self.snapshot)
        qualification = objects_by_id(snapshot)["FIX-activity"]["task_qualification"]["value"]
        qualification.pop("target_operations")
        qualification["target_operation_call"] = fact("known", value=True)
        qualification["prerequisite_burden"] = qualification.pop("prerequisite_fit")
        store = self.seed(snapshot, self.artifacts, name="legacy-qualification")
        self.assertEqual(TeachingService(store).run(self.request("open"))["status"], "ready")

    def test_conflicting_and_nonboolean_qualification_declarations_cannot_authorize_teaching(self):
        for mode in ("target_conflict", "prerequisite_conflict", "prose_assertion"):
            with self.subTest(mode=mode):
                snapshot = copy.deepcopy(self.snapshot)
                qualification = objects_by_id(snapshot)["FIX-activity"]["task_qualification"]["value"]
                if mode == "target_conflict":
                    qualification["target_operation_call"] = fact("known", value=False)
                elif mode == "prerequisite_conflict":
                    qualification["prerequisite_burden"] = fact("known", value=False)
                else:
                    qualification["reference_scorable"] = fact("known", value="未声明布尔核查结果")
                store = self.seed(snapshot, self.artifacts, name=mode)
                self.assert_unsaved(TeachingService(store).run(self.request("open")))
                self.assertEqual(self.revision(store), 1)

    def test_modern_unknown_and_inactive_grants_do_not_authorize_execution(self):
        for label, validity in (("unknown", fact("unknown", "尚未核查授权是否生效")),
                                ("inactive", fact("known", value={"active": False})),
                                ("missing_active", fact("known", value={"reason": "说明存在，但无生效声明"}))):
            with self.subTest(validity=validity):
                snapshot = copy.deepcopy(self.snapshot)
                objects_by_id(snapshot)[GRANT_ID]["validity"] = validity
                store = self.seed(snapshot, self.artifacts, name="grant-" + label)
                self.assert_unsaved(TeachingService(store).run(initial_request()))
                self.assertEqual(self.revision(store), 1)
        snapshot = copy.deepcopy(self.snapshot)
        objects_by_id(snapshot)[GRANT_ID]["validity"] = fact("known", value={"active": True})
        store = self.seed(snapshot, self.artifacts, name="grant-active")
        self.assertEqual(TeachingService(store).run(initial_request())["status"], "committed")

    def test_completeness_is_an_explicit_declaration_preserved_or_updated(self):
        result = self.initial(prior_exposures=[])
        self.assertEqual(self.event()["timeline_completeness"]["status"], "unknown")
        handoff = result["assessment_handoff"]
        self.assertEqual(handoff["response_point"], {"event_ref": ref(self.event()), "kind": "initial_response", "sequence": 1})
        self.assertEqual(handoff["material_context"], self.binding)
        self.assertFalse(handoff["assessment_called"])
        complete = fact("known", value=True)
        self.assertEqual(self.help(timeline_completeness=complete)["status"], "committed")
        self.assertEqual(self.event()["timeline_completeness"], complete)
        result = self.revise()
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.event()["timeline_completeness"], complete)
        self.assertEqual(result["assessment_handoff"]["response_point"]["sequence"], 3)
        self.assertEqual(result["assessment_handoff"]["response_point"]["kind"], "revision")
        self.assertEqual(len([o for o in self.objects().values() if o["type"] == "Judgment"]), 1)

    def test_invalid_completeness_cannot_be_saved_or_inferred(self):
        for declaration in (True, fact("known", value="完整"), fact("pending", "待核查")):
            with self.subTest(declaration=declaration):
                request = initial_request()
                request["timeline_completeness"] = declaration
                self.assert_unsaved(self.service.run(request))
                self.assertEqual(self.revision(), 1)
        self.initial(timeline_completeness=fact("known", value=False))
        self.assertEqual(self.event()["timeline_completeness"], fact("known", value=False))
        before = self.state()
        self.assert_unsaved(self.help(timeline_completeness=fact("not_required", "不能声明未要求即完整")))
        self.assertEqual(self.state(), before)

    def strategy_fixture(self, name="with-strategy", adoption="adopted"):
        from runtime.learning_strategies import BINDING_FIELDS, StrategyCatalog
        from test_b3c_strategies import configured, fixture as strategy_fixture
        snapshot = copy.deepcopy(self.snapshot)
        strategy_snapshot, _ = strategy_fixture()
        known_ids = set(objects_by_id(snapshot))
        snapshot["objects"].extend(copy.deepcopy(o) for o in strategy_snapshot["objects"] if o["id"] not in known_ids)
        config, context = configured(StrategyCatalog())
        context["material_context"] = copy.deepcopy(self.binding)
        config["review_status"]["binding"] = {key: copy.deepcopy(context[key]) for key in BINDING_FIELDS}
        config["adoption"]["status"] = adoption
        snapshot["objects"].append(config)
        return self.seed(snapshot, self.artifacts, name=name), config, context

    def test_used_strategy_is_saved_without_activity_revision_and_recovers_on_continuation(self):
        store, config, context = self.strategy_fixture()
        service = TeachingService(store)
        initial = initial_request()
        initial.update(method_config_refs=[ref(config)], strategy_context=context)
        result = service.run(initial)
        self.assertEqual(result["status"], "committed", result)
        event = self.event(store)
        self.assertEqual(event["method_config_refs"], [ref(config)])
        self.assertEqual(event["c0"]["strategy_context"], context)
        self.assertEqual(self.objects(store)["FIX-activity"], objects_by_id(self.snapshot)["FIX-activity"])
        help_request = self.request("record_help", event_ref=ref(event), expected_state_revision=self.revision(store), help={
            "content": "按当前配置显式提供人工帮助", "visibility": "displayed",
            "target_operations": ["connect-P-to-Q"], "substituted_operations": ["connect-P-to-Q"],
            "time": fact("unknown", "人工顺序，无真实时间"),
        })
        self.assertNotIn("method_config_refs", help_request)
        self.assertNotIn("strategy_context", help_request)
        result = service.run(help_request)
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.event(store)["method_config_refs"], [ref(config)])
        self.assertEqual(self.event(store)["independent_sample_id"], SAMPLE_ID)
        request = self.request("resume", event_ref=ref(self.event(store)))
        self.assertEqual(service.run(request)["status"], "ready")

    def test_strategy_requires_exact_context_adoption_and_its_own_control_gate(self):
        for mode in ("missing_context", "candidate", "restricted"):
            with self.subTest(mode=mode):
                store, config, context = self.strategy_fixture(name="strategy-" + mode, adoption="candidate" if mode == "candidate" else "adopted")
                request = initial_request()
                request["method_config_refs"] = [ref(config)]
                if mode != "missing_context":
                    request["strategy_context"] = context
                if mode == "restricted":
                    self.assertEqual(store.restrict(1, "FIX-block-config", [config["id"]], "配置需要重新审查", ["strategy_configuration"])["status"], "committed")
                    request["expected_state_revision"] = self.revision(store)
                before = self.state(store)
                self.assert_unsaved(TeachingService(store).run(request))
                self.assertEqual(self.state(store), before)
                self.assertNotIn(EVENT_ID, self.objects(store))

    def test_continuation_cannot_silently_replace_used_strategy_or_its_context(self):
        store, config, context = self.strategy_fixture(name="strategy-substitution")
        service = TeachingService(store)
        request = initial_request()
        request.update(method_config_refs=[ref(config)], strategy_context=context)
        self.assertEqual(service.run(request)["status"], "committed")
        before = self.state(store)
        for replacement in ({"method_config_refs": []}, {"method_config_refs": [{"id": "FIX-method", "revision": 1}]},
                            {"strategy_context": {**context, "intended_work": "改成另一个工作"}}):
            request = self.request("record_help", event_ref=ref(self.event(store)), expected_state_revision=self.revision(store),
                help={"content": "不应保存的替换", "visibility": "displayed", "target_operations": [], "substituted_operations": [], "time": fact("unknown", "人工顺序")}, **replacement)
            result = service.run(request)
            self.assert_unsaved(result)
            self.assertEqual(self.state(store), before)

    def test_initial_help_revision_originals_survive_reopen_with_one_event_and_sample(self):
        before = self.objects()
        self.initial()
        self.assertEqual(self.help()["status"], "committed")
        revised = self.revise()
        self.assertEqual(revised["status"], "committed", revised)
        reopened = LearningStore(self.root, entry_actor="AG0")
        event = self.event(reopened)
        self.assertEqual(event["id"], EVENT_ID)
        self.assertEqual(event["independent_sample_id"], SAMPLE_ID)
        self.assertEqual([entry["kind"] for entry in event["timeline"]], ["initial_response", "help", "revision"])
        self.assertEqual([entry["sequence"] for entry in event["timeline"]], [1, 2, 3])
        exported = reopened.export_scope([EVENT_ID], include_artifacts=True)
        self.assertEqual(exported["status"], "ok", exported)
        self.assertEqual(exported["artifacts"][INITIAL_PATH], INITIAL_TEXT)
        self.assertEqual(exported["artifacts"][REVISION_PATH], REVISION_TEXT)
        help_ref = event["timeline"][1]["artifact_ref"]
        self.assertIn(event["timeline"][1]["content"], exported["artifacts"][help_ref["path"]])
        self.assertEqual(event["original_response"], anchor(INITIAL_PATH, "B3b-initial"))
        self.assertEqual(event["revisions"], [dict(anchor(REVISION_PATH, "B3b-revision"), sequence=3)])
        for identifier in ("FIX-plan", "FIX-goal", "FIX-judgment", "FIX-activity", "FIX-event"):
            self.assertEqual(self.objects(reopened)[identifier], before[identifier])
        self.assertEqual(len([o for o in self.objects().values() if o["type"] == "PerformanceEvent"]), 2)
        self.assertEqual(reopened.check_integrity()["status"], "ok")

    def test_unknown_help_visibility_and_contact_are_preserved_without_no_help_claim(self):
        self.initial()
        result = self.help(visibility="unknown")
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.event()["contact_history"]["status"], "unknown")
        self.assertEqual(self.event()["timeline"][1]["visibility"], "unknown")
        self.assertEqual(self.event()["timeline"][1]["substituted_operations"], ["connect-P-to-Q"])
        self.assertEqual(self.execute("resume", event_ref=ref(self.event()))["scoring"], "not_executed")
        self.assertNotIn("no_help", json.dumps(self.event()))

    def test_planned_requested_and_backend_help_remain_non_displayed(self):
        for visibility in ("planned", "requested", "backend_reference"):
            with self.subTest(visibility=visibility):
                store = self.seed(self.snapshot, self.artifacts, name=visibility)
                service = TeachingService(store)
                self.assertEqual(service.run(initial_request())["status"], "committed")
                request = self.request("record_help", event_ref=ref(self.event(store)), expected_state_revision=self.revision(store),
                                       help={"content": "PRIVATE-HELP-" + visibility, "visibility": visibility,
                                             "target_operations": ["connect-P-to-Q"], "substituted_operations": ["connect-P-to-Q"],
                                             "time": fact("unknown", "人工帮助顺序")})
                result = service.run(request)
                self.assertEqual(result["status"], "committed", result)
                self.assertEqual(self.event(store)["timeline"][-1]["visibility"], visibility)
                self.assertNotIn("learner_packet", result)

    def test_feedback_uses_original_observation_reliable_branch_and_next_learner_work(self):
        self.initial()
        result = self.service.run(self.feedback_request())
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(result["learner_next_work"], self.objects()["FIX-activity"]["branches"][0]["learner_next_work"])
        entry = self.event()["timeline"][-1]
        self.assertEqual(entry["kind"], "feedback")
        self.assertEqual(entry["observation"]["artifact_ref"], self.event()["original_response"])
        self.assertEqual(entry["observation"]["quote"], "Q。")
        self.assertTrue(entry["reference_refs"])
        self.assertEqual(self.objects()["FIX-judgment"]["revision"], 1)

    def test_feedback_rejects_unlocatable_or_unrelated_observation_without_writing(self):
        self.initial()
        before = self.state()
        for observation in ({"artifact_ref": anchor(INITIAL_PATH, "B3b-initial"), "quote": "从未出现在原答的理由"},
                            {"artifact_ref": anchor("originals.md", "虚构初答"), "quote": "Q。"}):
            with self.subTest(observation=observation):
                result = self.service.run(self.feedback_request(observation=observation))
                self.assert_unsaved(result)
                self.assertEqual(self.state(), before)
        result = self.service.run(self.feedback_request(branch_index=999))
        self.assert_unsaved(result)
        self.assertEqual(self.state(), before)

    def test_feedback_branch_requires_usable_reference_and_actual_next_work(self):
        for missing in ("reference_refs", "learner_next_work"):
            with self.subTest(missing=missing):
                snapshot = copy.deepcopy(self.snapshot)
                del objects_by_id(snapshot)["FIX-activity"]["branches"][0][missing]
                store = self.seed(snapshot, self.artifacts, name="missing-" + missing)
                service = TeachingService(store)
                initialized = service.run(initial_request())
                self.assertEqual(initialized["status"], "committed", initialized)
                request = self.feedback_request(event_ref=ref(self.event(store)), expected_state_revision=self.revision(store))
                before = self.state(store)
                result = service.run(request)
                self.assert_unsaved(result)
                self.assertEqual(self.state(store), before)
                self.assertFalse(any(entry["kind"] == "feedback" for entry in self.objects(store).get(EVENT_ID, {}).get("timeline", [])))

    def test_existing_sufficient_evidence_can_close_without_new_task_judgment_or_plan(self):
        self.initial()
        before = self.objects()
        result = self.service.run(self.close_request())
        self.assertEqual(result["status"], "committed", result)
        after = self.objects()
        self.assertEqual(set(after) - set(before), {"FIX-b3b-checkpoint"})
        for identifier in ("FIX-activity", "FIX-parent-activity", "FIX-event", "FIX-plan", "FIX-judgment", "FIX-need"):
            self.assertEqual(after[identifier], before[identifier])
        for field in ("original_response", "revisions", "timeline", "independent_sample_id"):
            self.assertEqual(after[EVENT_ID][field], before[EVENT_ID][field])
        self.assertEqual(after[EVENT_ID]["c0"]["status"], "closed")
        self.assertEqual(result["scoring"], "not_executed")
        self.assertEqual(result["checkpoint_ref"], ref(after["FIX-b3b-checkpoint"]))

    def test_parent_return_preserves_same_artifact_connection_and_help(self):
        self.initial()
        self.assertEqual(self.help()["status"], "committed")
        self.assertEqual(self.revise()["status"], "committed")
        parent = self.objects()["FIX-activity"]["parent_task"]["value"]
        result = self.execute("return_parent", event_ref=ref(self.event()), parent_ref=parent["parent_activity_ref"],
                          parent_artifact=parent["parent_artifact"], return_connection=parent["return_connection"])
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(result["parent_artifact"], parent["parent_artifact"])
        self.assertEqual(result["return_connection"], parent["return_connection"])
        self.assertTrue(result["inherited_help"])
        self.assertEqual(self.event()["independent_sample_id"], SAMPLE_ID)
        self.assertEqual(self.event()["timeline"][-1]["kind"], "return_parent")
        self.assertEqual(result["scoring"], "not_executed")
        exported = self.store.export_scope(["FIX-parent-activity"], include_artifacts=True)
        self.assertEqual(exported["artifacts"]["originals.md"], self.artifacts["originals.md"])

    def test_parent_return_rejects_different_artifact_or_connection(self):
        self.initial()
        parent = self.objects()["FIX-activity"]["parent_task"]["value"]
        before = self.state()
        for fields in ({"parent_artifact": anchor(INITIAL_PATH, "B3b-initial")},
                       {"return_connection": "绕过规范父产物并改目标"},
                       {"parent_ref": {"id": "FIX-activity", "revision": 1}}):
            request = self.request("return_parent", event_ref=ref(self.event()), parent_ref=parent["parent_activity_ref"],
                                   parent_artifact=parent["parent_artifact"], return_connection=parent["return_connection"])
            request.update(fields)
            result = self.service.run(request)
            self.assert_unsaved(result)
            self.assertEqual(self.state(), before)

    def test_pause_and_purpose_restriction_stop_before_originals_or_output(self):
        for control in ("pause", "restrict"):
            with self.subTest(control=control):
                store = self.seed(self.snapshot, self.artifacts, name=control)
                if control == "pause":
                    stopped = store.pause(1, "FIX-b3b-pause", ["FIX-activity"], "人工用户暂停")
                else:
                    stopped = store.restrict(1, "FIX-b3b-restrict", ["FIX-content-source"], "人工用途争议", ["teaching", "teaching_execution", "independent_check"])
                self.assertEqual(stopped["status"], "committed", stopped)
                service = TeachingService(store)
                before = self.state(store)
                result = service.run(self.request("open"))
                self.assert_unsaved(result)
                self.assertNotIn("learner_packet", result)
                request = initial_request(self.revision(store))
                result = service.run(request)
                self.assert_unsaved(result)
                self.assertEqual(self.state(store), before)
                self.assertNotIn(EVENT_ID, self.objects(store))

    def test_budget_exhaustion_stops_before_creating_new_event(self):
        snapshot = copy.deepcopy(self.snapshot)
        objects_by_id(snapshot)["FIX-budget"]["user_active_time"] = fact("known", value={"minutes": 0, "measurement": "synthetic_limit"})
        store = self.seed(snapshot, self.artifacts, name="budget-ended")
        service = TeachingService(store)
        before = self.state(store)
        result = service.run(self.request("open"))
        self.assert_unsaved(result)
        self.assertNotIn("learner_packet", result)
        self.assert_unsaved(service.run(initial_request()))
        self.assertEqual(self.state(store), before)

    def test_unfinished_close_reuses_existing_need_without_creating_duplicate_or_schedule(self):
        self.initial()
        before = self.objects()
        request = self.close_request(
            unfinished_requirement_ids=["infer-Q"], existing_need_ref={"id": "FIX-need", "revision": 1},
            closure={"status": "unfinished", "reason": "独立连接仍未知，复用现有需求"},
        )
        result = self.service.run(request)
        self.assertEqual(result["status"], "committed", result)
        after = self.objects()
        self.assertEqual(after["FIX-need"], before["FIX-need"])
        self.assertEqual(after["FIX-plan"], before["FIX-plan"])
        self.assertEqual([o["id"] for o in after.values() if o["type"] == "LearningNeed"], ["FIX-need"])
        self.assertEqual(result["learning_need_candidate"]["existing_need_ref"], {"id": "FIX-need", "revision": 1})
        self.assertFalse(result["learning_need_candidate"]["acceptance_changed"])
        self.assertFalse(result["learning_need_candidate"]["disposition_changed"])

    def test_stale_state_and_stale_event_do_not_append_or_recount(self):
        self.initial()
        request = self.request("record_help", event_ref=ref(self.event()), help={
            "content": "STALE-MUST-NOT-PERSIST", "visibility": "displayed", "target_operations": [],
            "substituted_operations": [], "time": fact("unknown", "人工顺序"),
        })
        self.assertEqual(self.store.pause(self.revision(), "FIX-b3b-unrelated-pause", ["FIX-method"], "人工无关暂停")["status"], "committed")
        result = self.service.run(request)
        self.assertEqual(result["status"], "conflict", result)
        self.assertEqual(self.event()["revision"], 1)
        request["expected_state_revision"] = self.revision()
        request["operation_id"] = "FIX-b3b-late-old-event"
        self.assertEqual(self.help()["status"], "committed")
        request["expected_state_revision"] = self.revision()
        result = self.service.run(request)
        self.assert_unsaved(result)
        self.assertEqual(len(self.event()["timeline"]), 2)
        self.assertNotIn("STALE-MUST-NOT-PERSIST", json.dumps(self.event()))

    def test_same_operation_and_bytes_is_idempotent_changed_retry_is_rejected(self):
        request = initial_request()
        first = self.service.run(request)
        self.assertEqual(first["status"], "committed", first)
        second = self.service.run(copy.deepcopy(request))
        self.assertEqual(second, first)
        self.assertEqual(self.revision(), first["state_revision"])
        changed = copy.deepcopy(request)
        changed["initial_response"]["content"] = "CHANGED-RETRY-PAYLOAD"
        changed["artifacts"][INITIAL_PATH] = "# B3b-initial\nCHANGED-RETRY-PAYLOAD\n"
        result = self.service.run(changed)
        self.assertEqual(result["status"], "rejected", result)
        self.assertIn("operation_id_reused", self.codes(result))
        self.assertEqual(self.event()["timeline"][0]["content"], "Q。")

    def test_help_retry_is_idempotent_after_event_revision_advanced(self):
        self.initial()
        request = self.request("record_help", event_ref=ref(self.event()), help={
            "content": "人工一次帮助", "visibility": "displayed", "target_operations": ["connect-P-to-Q"],
            "substituted_operations": ["connect-P-to-Q"], "time": fact("unknown", "人工顺序"),
        })
        first = self.service.run(request)
        self.assertEqual(first["status"], "committed", first)
        self.assertEqual(self.revise()["status"], "committed")
        revision = self.revision()
        self.assertEqual(self.service.run(copy.deepcopy(request)), first)
        self.assertEqual(self.revision(), revision)
        self.assertEqual(len(self.event()["timeline"]), 3)

    def test_late_initial_after_delete_cannot_restore_records_or_originals(self):
        request = initial_request()
        deleted = self.store.delete_scope(1, "FIX-b3b-delete", ["FIX-content-source"])
        self.assertEqual(deleted["status"], "committed", deleted)
        request["expected_state_revision"] = self.revision()
        result = self.service.run(request)
        self.assert_unsaved(result)
        self.assertNotIn(EVENT_ID, self.objects())
        self.assertNotEqual(self.execute("open")["status"], "ready")
        exported = self.store.export_scope([EVENT_ID], include_artifacts=True)
        self.assertNotIn(INITIAL_PATH, exported.get("artifacts", {}))

    def test_explicit_authorization_and_ag0_actor_are_required(self):
        for mode in ("missing", "wrong_grantee", "wrong_scope"):
            with self.subTest(mode=mode):
                snapshot = copy.deepcopy(self.snapshot)
                objects = objects_by_id(snapshot)
                if mode == "missing":
                    objects["FIX-activity"]["authority_refs"] = [{"id": "FIX-user-grant", "revision": 1}]
                elif mode == "wrong_grantee":
                    objects[GRANT_ID]["grantee"] = "AG1"
                else:
                    objects[GRANT_ID]["object_scope"] = ["FIX-parent-activity"]
                store = self.seed(snapshot, self.artifacts, name=mode)
                result = TeachingService(store).run(initial_request())
                self.assert_unsaved(result)
                self.assertEqual(self.revision(store), 1)
        wrong_actor = LearningStore(self.root, entry_actor="AG2")
        self.assert_unsaved(TeachingService(wrong_actor).run(self.request("open")))

    def test_unknown_task_qualification_unverified_material_and_changed_binding_limit_use(self):
        for mode in ("qualification", "content_reference", "use_reference"):
            with self.subTest(mode=mode):
                snapshot = copy.deepcopy(self.snapshot)
                objects = objects_by_id(snapshot)
                if mode == "qualification":
                    objects["FIX-activity"]["task_qualification"]["value"]["not_substituted"] = fact("unknown", "未核查")
                elif mode == "content_reference":
                    objects["FIX-material"]["verification"]["content"]["status"] = "pending"
                else:
                    objects["FIX-material"]["verification"]["use"]["status"] = "pending"
                store = self.seed(snapshot, self.artifacts, name=mode)
                self.assert_unsaved(TeachingService(store).run(self.request("open")))
                self.assertEqual(self.revision(store), 1)
        request = self.request("open")
        request["context"]["purpose"] = "comparison"
        self.assert_unsaved(self.service.run(request))
        self.assertEqual(self.revision(), 1)

    def test_resume_is_read_only_keeps_pause_and_restriction_and_does_not_add_check(self):
        self.initial()
        self.assertEqual(self.help(visibility="unknown")["status"], "committed")
        close = self.service.run(self.close_request())
        self.assertEqual(close["status"], "committed", close)
        self.assertEqual(self.store.pause(self.revision(), "FIX-b3b-resume-pause", ["FIX-activity"], "人工暂停")["status"], "committed")
        before = self.state()
        resumed = self.execute("resume", checkpoint_ref=close["checkpoint_ref"], event_ref=ref(self.event()))
        self.assertNotIn("learner_packet", resumed)
        self.assertEqual(self.state(), before)
        self.assertIn("FIX-activity", self.state()["controls"]["paused_ids"])
        self.assertEqual(self.event()["contact_history"]["status"], "unknown")
        self.assertEqual(len(self.event()["timeline"]), 2)
        self.assertEqual(len([o for o in self.objects().values() if o["type"] == "Judgment"]), 1)

    def test_real_identity_and_missing_synthetic_marker_are_rejected_before_recording(self):
        for marker in (False, None):
            request = initial_request()
            if marker is None:
                del request["synthetic_only"]
            else:
                request["synthetic_only"] = marker
            self.assert_unsaved(self.service.run(request))
            self.assertEqual(self.revision(), 1)
        request = initial_request()
        request["original_response"]["origin"] = "real_learner"
        self.assert_unsaved(self.service.run(request))
        self.assertNotIn(EVENT_ID, self.objects())

    def test_exposure_before_initial_and_help_after_initial_keep_distinct_sequences(self):
        before_store = self.seed(self.snapshot, self.artifacts, name="prior-exposure")
        before_service = TeachingService(before_store)
        exposure = {
            "kind": "exposure", "content": "初答前已经展示 P 与 P→Q 的连接理由",
            "visibility": "displayed", "target_operations": ["connect-P-to-Q"],
            "substituted_operations": ["connect-P-to-Q"],
            "time": fact("unknown", "人工夹具只给先后，不虚构展示时间"),
        }
        request = initial_request()
        request["prior_exposures"] = [exposure]
        early = before_service.run(request)
        self.assertEqual(early["status"], "committed", early)
        early_event = self.event(before_store)
        self.assertEqual([entry["kind"] for entry in early_event["timeline"]], ["exposure", "initial_response"])
        self.assertEqual([entry["sequence"] for entry in early_event["timeline"]], [1, 2])
        self.assertEqual(early_event["timeline"][0]["substituted_operations"], ["connect-P-to-Q"])
        exported = before_store.export_scope([EVENT_ID], include_artifacts=True)
        exposure_ref = early_event["timeline"][0]["artifact_ref"]
        self.assertIn(exposure["content"], exported["artifacts"][exposure_ref["path"]])
        self.assertEqual(early_event["contact_history"]["status"], "unknown")
        self.initial()
        late = self.help()
        self.assertEqual(late["status"], "committed", late)
        self.assertEqual([entry["kind"] for entry in self.event()["timeline"]], ["initial_response", "help"])
        self.assertEqual([entry["sequence"] for entry in self.event()["timeline"]], [1, 2])
        self.assertEqual(self.event()["timeline"][0]["substituted_operations"], [])
        self.assertEqual(self.event()["independent_sample_id"], early_event["independent_sample_id"])
        self.assertEqual(early["factual_conditions"]["independent_support"], "not_assessed")
        self.assertEqual(late["factual_conditions"]["independent_support"], "not_assessed")

    def test_active_same_activity_cannot_create_second_initial_or_sample(self):
        self.initial()
        before = self.state()
        duplicate = initial_request(self.revision(), "FIX-b3b-second-initial")
        duplicate.update(event_id="FIX-b3b-second-event", independent_sample_id="FIX-b3b-second-sample")
        result = self.service.run(duplicate)
        self.assert_unsaved(result)
        self.assertIn("existing_event_requires_revision", self.codes(result))
        self.assertEqual(self.state(), before)
        self.assertNotIn("FIX-b3b-second-event", self.objects())

    def test_recorded_budget_limit_stops_omitted_usage_help_but_allows_budget_close(self):
        self.initial(active_minutes=5)
        self.assertEqual(self.event()["c0"]["declared_active_minutes"]["value"]["minutes"], 5)
        before = self.state()
        result = self.help()
        self.assert_unsaved(result)
        self.assertEqual(self.state(), before)
        result = self.service.run(self.close_request(
            closure={"status": "budget_end", "reason": "已用完人工共用五分钟预算"},
            stop_reason="人工预算结束", unfinished_requirement_ids=["infer-Q"],
            existing_need_ref={"id": "FIX-need", "revision": 1},
        ))
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.event()["c0"]["declared_active_minutes"]["value"]["minutes"], 5)
        self.assertEqual(self.event()["c0"]["closure"]["status"], "budget_end")
        self.assertEqual(len(self.event()["timeline"]), 1)
        self.assertEqual(self.objects()["FIX-plan"], objects_by_id(before)["FIX-plan"])

    def test_budget_checkpoint_recovers_consumption_and_stops_more_teaching(self):
        self.initial(active_minutes=1)
        saved = self.service.run(self.close_request(
            action="checkpoint", active_minutes=5, stop_reason="人工预算已经耗尽",
        ))
        self.assertEqual(saved["status"], "committed", saved)
        reopened = TeachingService(LearningStore(self.root))
        resumed = reopened.run(self.request("resume", checkpoint_ref=saved["checkpoint_ref"]))
        self.assertEqual(resumed["status"], "ready", resumed)
        self.assertEqual(resumed["recovery"]["declared_active_minutes"]["value"]["minutes"], 5)
        self.assertEqual(saved["event_ref"], resumed["recovery"]["last_trusted_event_ref"])
        before = self.state()
        for action in ("open", "record_help"):
            result = reopened.run(self.request(action, **({"event_ref": ref(self.event()), "help": {
                "content": "预算之后的人工提示", "visibility": "displayed",
                "target_operations": ["connect-P-to-Q"], "substituted_operations": [],
                "time": fact("unknown", "仅夹具"),
            }} if action == "record_help" else {})))
            self.assertEqual(result["status"], "stopped", result)
            self.assertIn("shared_budget_exceeded", self.codes(result))
            self.assertEqual(self.state(), before)

    def test_budget_close_cannot_reopen_activity_with_the_old_shared_budget(self):
        self.initial(active_minutes=1)
        saved = self.service.run(self.close_request(active_minutes=5,
            closure={"status": "budget_end", "reason": "人工预算结束"}))
        self.assertEqual(saved["status"], "committed", saved)
        before = self.state()
        opened = self.execute("open")
        self.assertEqual(opened["status"], "stopped", opened)
        self.assertIn("shared_budget_exceeded", self.codes(opened))
        self.assertEqual(self.state(), before)

    def test_lower_reported_budget_cannot_reset_persisted_consumption(self):
        self.initial(active_minutes=4)
        before = self.state()
        result = self.help(active_minutes=1)
        self.assert_unsaved(result)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.event()["c0"]["declared_active_minutes"]["value"]["minutes"], 4)

    def test_legacy_checkpoint_consumption_is_a_bound_without_rewriting_originals(self):
        self.initial(active_minutes=1)
        saved = self.service.run(self.close_request(action="checkpoint", active_minutes=5))
        self.assertEqual(saved["status"], "committed", saved)
        snapshot = self.state()
        event = objects_by_id(snapshot)[EVENT_ID]
        event["revision"] = 1
        event["c0"]["declared_active_minutes"] = fact("known", value={"minutes": 1, "measurement": "caller_declaration"})
        checkpoint = objects_by_id(snapshot)[saved["checkpoint_ref"]["id"]]
        checkpoint.update(basis_refs=[ref(event)], last_trusted_event_ref=ref(event), help_history_refs=[ref(event)])
        legacy = self.seed(snapshot, {**self.artifacts, INITIAL_PATH: INITIAL_TEXT}, name="legacy-budget-checkpoint")
        service = TeachingService(legacy)
        before = self.state(legacy)
        recovered = service.run(self.request("resume", checkpoint_ref=saved["checkpoint_ref"]))
        self.assertEqual(recovered["status"], "ready", recovered)
        self.assertEqual(recovered["recovery"]["declared_active_minutes"]["value"]["minutes"], 5)
        self.assertEqual(self.state(legacy), before)
        result = service.run(self.request("open"))
        self.assertEqual(result["status"], "stopped", result)
        lower = service.run(self.request("checkpoint", event_ref=ref(event), active_minutes=2,
            expected_state_revision=before["state_revision"], checkpoint_id="FIX-legacy-lower-cp",
            stop_reason="人工旧断点", next_connection="原父任务", pending_owners=[],
            unrecorded_actions=fact("unknown", "夹具")))
        self.assertIn("active_time_cannot_decrease", self.codes(lower), lower)
        self.assertEqual(self.state(legacy), before)

    def test_checkpoint_time_is_atomic_and_history_retains_its_original_help(self):
        self.initial(active_minutes=1)
        before = self.state()
        checkpoint_request = self.close_request(action="checkpoint", active_minutes=3)
        def fail(stage):
            if stage == "after_write":
                raise RuntimeError("人工检查点事务失败")
        self.store.failpoint = fail
        failed = self.service.run(checkpoint_request)
        self.store.failpoint = None
        self.assertEqual(failed["status"], "not_saved", failed)
        self.assertEqual(self.state(), before)
        self.assertNotIn("checkpoint_ref", failed)
        saved = self.service.run(checkpoint_request)
        self.assertEqual(saved["status"], "committed", saved)
        self.assertEqual(self.event()["c0"]["declared_active_minutes"]["value"]["minutes"], 3)
        self.assertEqual(self.help(active_minutes=4)["status"], "committed")
        recovered = self.execute("resume", checkpoint_ref=saved["checkpoint_ref"])
        self.assertEqual(recovered["status"], "ready", recovered)
        self.assertEqual(recovered["recovery"]["last_trusted_event_ref"], saved["event_ref"])
        self.assertEqual(recovered["recovery"]["declared_active_minutes"]["value"]["minutes"], 4)
        self.assertEqual([e["kind"] for e in recovered["recovery"]["help_history"]], ["initial_response"])
        self.assertEqual(len(self.event()["timeline"]), 2)

    def test_restricted_legacy_checkpoint_cannot_be_silently_skipped_for_more_work(self):
        self.initial(active_minutes=1)
        saved = self.service.run(self.close_request(action="checkpoint", active_minutes=5))
        self.assertEqual(saved["status"], "committed", saved)
        snapshot = self.state()
        objects = objects_by_id(snapshot)
        event, checkpoint = objects[EVENT_ID], objects[saved["checkpoint_ref"]["id"]]
        event["revision"] = 1
        event["c0"]["declared_active_minutes"] = fact("known", value={"minutes": 1, "measurement": "caller_declaration"})
        checkpoint.update(basis_refs=[ref(event)], last_trusted_event_ref=ref(event), help_history_refs=[ref(event)])
        legacy = self.seed(snapshot, {**self.artifacts, INITIAL_PATH: INITIAL_TEXT}, name="restricted-legacy-checkpoint")
        restricted = legacy.restrict(self.revision(legacy), "FIX-budget-checkpoint-restrict", [checkpoint["id"]],
                                     "人工用途待重审", ["teaching_execution"])
        self.assertEqual(restricted["status"], "committed", restricted)
        before = self.state(legacy)
        service = TeachingService(legacy)
        opened = service.run(self.request("open"))
        self.assertEqual(opened["status"], "blocked", opened)
        self.assertNotIn("learner_packet", opened)
        resumed = service.run(self.request("resume", checkpoint_ref=ref(checkpoint)))
        self.assertEqual(resumed["status"], "blocked", resumed)
        self.assertNotIn("recovery", resumed)
        self.assertEqual(self.state(legacy), before)

    def test_unrelated_legal_ref_cannot_stand_in_for_verified_feedback_reference(self):
        snapshot = copy.deepcopy(self.snapshot)
        objects_by_id(snapshot)["FIX-activity"]["branches"][0]["reference_refs"] = [{"id": "FIX-plan", "revision": 1}]
        store = self.seed(snapshot, self.artifacts, name="unrelated-reference")
        service = TeachingService(store)
        initialized = service.run(initial_request())
        self.assertEqual(initialized["status"], "committed", initialized)
        before = self.state(store)
        result = service.run(self.feedback_request(event_ref=ref(self.event(store)), expected_state_revision=self.revision(store)))
        self.assert_unsaved(result)
        self.assertEqual(self.state(store), before)

    def test_cli_emits_valid_json_for_open_and_rejection_without_mutating(self):
        before = self.state()
        request_path = Path(self.temp.name) / "caller-owned-b3b-request.json"
        for request, expected_code, expected_status in ((self.request("open"), 0, "ready"),
                                                       (self.request("unsupported_action"), 1, "rejected")):
            with self.subTest(expected_status=expected_status):
                request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
                completed = subprocess.run([
                    sys.executable, str(ROOT / "src/runtime/learning_teaching.py"),
                    "--workspace", str(self.root), "--request", str(request_path),
                ], capture_output=True, text=True, encoding="utf-8", timeout=30)
                self.assertEqual(completed.returncode, expected_code, completed.stdout + completed.stderr)
                output = json.loads(completed.stdout)
                self.assertEqual(output["status"], expected_status, output)
                self.assertEqual(output["scoring"], "not_executed")
                self.assertEqual(self.state(), before)
        self.assertTrue(request_path.exists(), "调用方 JSON 请求不属于受控删除范围")

    def test_saved_initial_retry_after_delete_never_restores_old_receipt_or_original(self):
        request = initial_request()
        result = self.service.run(request)
        self.assertEqual(result["status"], "committed", result)
        deleted = self.store.delete_scope(self.revision(), "FIX-b3b-delete-saved-event", [EVENT_ID])
        self.assertEqual(deleted["status"], "committed", deleted)
        before = self.state()
        result = self.service.run(copy.deepcopy(request))
        self.assert_unsaved(result)
        self.assertEqual(self.state(), before)
        self.assertNotIn(EVENT_ID, self.objects())
        self.assertNotIn(INITIAL_PATH, self.store.export_scope([EVENT_ID], include_artifacts=True).get("artifacts", {}))

    def test_write_requires_cas_and_safe_original_artifact_and_preserves_state_on_rejection(self):
        for missing in ("expected_state_revision", "operation_id"):
            with self.subTest(missing=missing):
                request = initial_request()
                del request[missing]
                before = self.state()
                self.assert_unsaved(self.service.run(request))
                self.assertEqual(self.state(), before)
        request = initial_request()
        request["original_response"]["path"] = "../b3b-initial.md"
        request["artifacts"] = {"../b3b-initial.md": INITIAL_TEXT}
        before = self.state()
        self.assert_unsaved(self.service.run(request))
        self.assertEqual(self.state(), before)

    def test_parent_entry_help_is_inherited_at_open_record_resume_and_return(self):
        expected_ref = {"id": "FIX-event", "revision": 1}
        original_parent = copy.deepcopy(self.objects()["FIX-event"])
        opened = self.execute("open")
        self.assertEqual(opened["status"], "ready", opened)
        self.assertEqual(opened["parent_help_history_refs"], [expected_ref])
        conditions = opened["parent_help_conditions"][0]
        self.assertEqual(conditions["event_ref"], expected_ref)
        self.assertEqual(conditions["conditions"]["substituted_operations"], ["connect-P-to-Q"])
        self.assertEqual(conditions["conditions"]["independent_support"], "not_assessed")
        self.assertEqual(conditions["conditions"]["unrecorded_help"]["status"], "unknown")
        recorded = self.initial()
        self.assertEqual(recorded["parent_help_history_refs"], [expected_ref])
        self.assertEqual(self.event()["c0"]["inherited_event_refs"], [expected_ref])
        self.assertEqual(self.event()["c0"]["inherited_help_conditions"], opened["parent_help_conditions"])
        resumed = self.execute("resume", event_ref=ref(self.event()))
        self.assertEqual(resumed["status"], "ready", resumed)
        self.assertEqual(resumed["recovery"]["parent_help_history_refs"], [expected_ref])
        self.assertEqual(resumed["recovery"]["parent_help_conditions"], opened["parent_help_conditions"])
        parent = self.objects()["FIX-activity"]["parent_task"]["value"]
        returned = self.execute("return_parent", event_ref=ref(self.event()), parent_ref=parent["parent_activity_ref"],
                                parent_artifact=parent["parent_artifact"], return_connection=parent["return_connection"])
        self.assertEqual(returned["status"], "committed", returned)
        self.assertEqual(returned["parent_help_history_refs"], [expected_ref])
        self.assertEqual(returned["parent_help_conditions"], opened["parent_help_conditions"])
        self.assertEqual(self.objects()["FIX-event"], original_parent)
        self.assertEqual(self.event()["contact_history"]["status"], "unknown")

    def test_unreported_active_time_stays_unknown_across_help_and_resume(self):
        self.initial()
        self.assertEqual(self.event()["c0"]["declared_active_minutes"]["status"], "unknown")
        self.assertEqual(self.help()["status"], "committed")
        self.assertEqual(self.event()["c0"]["declared_active_minutes"]["status"], "unknown")
        before = self.state()
        resumed = self.execute("resume", event_ref=ref(self.event()))
        self.assertEqual(resumed["status"], "ready", resumed)
        self.assertEqual(resumed["recovery"]["declared_active_minutes"]["status"], "unknown")
        self.assertEqual(self.state(), before)

    def test_known_help_time_cannot_precede_initial_and_timezone_order_is_respected(self):
        request = initial_request()
        request["initial_response"]["time"] = fact("known", value="2026-10-03T09:00:00+08:00")
        initial = self.service.run(request)
        self.assertEqual(initial["status"], "committed", initial)
        request = self.request("record_help", event_ref=ref(self.event()), help={
            "content": "人工显示帮助，仅核验记录时间顺序", "visibility": "displayed",
            "target_operations": ["connect-P-to-Q"], "substituted_operations": ["connect-P-to-Q"],
            "time": fact("known", value="2026-10-03T08:59:00+08:00"),
        })
        before = self.state()
        result = self.service.run(request)
        self.assert_unsaved(result)
        self.assertEqual(self.state(), before)
        self.assertEqual(len(self.event()["timeline"]), 1)
        request["operation_id"] = "FIX-b3b-chronological-help"
        request["help"]["time"] = fact("known", value="2026-10-03T01:01:00Z")
        result = self.service.run(request)
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.event()["timeline"][-1]["time"]["value"], "2026-10-03T01:01:00Z")
        self.assertEqual([entry["sequence"] for entry in self.event()["timeline"]], [1, 2])

    def test_known_prior_exposure_time_cannot_follow_initial_and_unknown_is_preserved(self):
        request = initial_request()
        request["initial_response"]["time"] = fact("known", value="2026-10-03T09:00:00+08:00")
        request["prior_exposures"] = [{
            "kind": "exposure", "content": "人工初答前暴露", "visibility": "displayed",
            "target_operations": ["connect-P-to-Q"], "substituted_operations": ["connect-P-to-Q"],
            "time": fact("known", value="2026-10-03T09:01:00+08:00"),
        }]
        before = self.state()
        result = self.service.run(request)
        self.assert_unsaved(result)
        self.assertEqual(self.state(), before)
        self.assertNotIn(EVENT_ID, self.objects())
        request["operation_id"] = "FIX-b3b-unknown-prior-time"
        request["prior_exposures"][0]["time"] = fact("unknown", "只知发生于初答前，没有可靠钟表时间")
        result = self.service.run(request)
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.event()["timeline"][0]["time"]["status"], "unknown")
        self.assertEqual(self.event()["timeline"][1]["time"]["value"], "2026-10-03T09:00:00+08:00")
        self.assertEqual([entry["sequence"] for entry in self.event()["timeline"]], [1, 2])

    def test_failed_initial_cas_returns_no_unsaved_event_or_factual_conditions(self):
        request = initial_request()
        gate = self.store.pause(self.revision(), "FIX-b3b-cas-unrelated-pause", ["FIX-method"], "人工无关状态变更")
        self.assertEqual(gate["status"], "committed", gate)
        before = self.state()
        result = self.service.run(request)
        self.assertEqual(result["status"], "conflict", result)
        self.assertFalse(result["mutated"])
        for field in ("event_ref", "factual_conditions", "learner_next_work", "checkpoint_ref"):
            self.assertNotIn(field, result)
        self.assertEqual(self.state(), before)
        self.assertNotIn(EVENT_ID, self.objects())

    def test_failed_feedback_cas_returns_no_uncommitted_next_work_or_event_ref(self):
        self.initial()
        request = self.feedback_request()
        gate = self.store.pause(self.revision(), "FIX-b3b-feedback-cas-unrelated-pause", ["FIX-method"], "人工无关状态变更")
        self.assertEqual(gate["status"], "committed", gate)
        before = self.state()
        result = self.service.run(request)
        self.assertEqual(result["status"], "conflict", result)
        self.assertFalse(result["mutated"])
        for field in ("event_ref", "factual_conditions", "learner_next_work", "checkpoint_ref"):
            self.assertNotIn(field, result)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.event()["revision"], 1)
        self.assertEqual([entry["kind"] for entry in self.event()["timeline"]], ["initial_response"])

    def test_explicit_candidate_recheck_and_rejected_bases_cannot_start_execution(self):
        for identifier in ("FIX-activity", "FIX-goal", "FIX-material"):
            for adoption_status in ("candidate", "recheck", "rejected"):
                with self.subTest(identifier=identifier, adoption_status=adoption_status):
                    snapshot = copy.deepcopy(self.snapshot)
                    objects_by_id(snapshot)[identifier]["adoption"] = {
                        "status": adoption_status, "limitations": ["人工候选仍未被负责方正式采用"],
                    }
                    store = self.seed(snapshot, self.artifacts, name=identifier + "-" + adoption_status)
                    service = TeachingService(store)
                    before = self.state(store)
                    opened = service.run(self.request("open"))
                    self.assert_unsaved(opened)
                    self.assertNotIn("learner_packet", opened)
                    recorded = service.run(initial_request())
                    self.assert_unsaved(recorded)
                    self.assertNotIn("event_ref", recorded)
                    self.assertEqual(self.state(store), before)
                    self.assertNotIn(EVENT_ID, self.objects(store))
        # Existing B2b full-adoption prose retains its fixture compatibility;
        # a partial-adoption declaration must identify its usable scope.
        snapshot = copy.deepcopy(self.snapshot)
        objects_by_id(snapshot)["FIX-material"]["adoption"] = {
            "status": "adopted", "scope": "Only synthetic material metadata and reference compatibility.",
            "limitations": ["Not a real professional conclusion."],
        }
        store = self.seed(snapshot, self.artifacts, name="full-adoption-prose")
        self.assertEqual(TeachingService(store).run(self.request("open"))["status"], "ready")
        snapshot = copy.deepcopy(self.snapshot)
        objects_by_id(snapshot)["FIX-material"]["adoption"] = {
            "status": "partially_adopted", "scope": "未定位的人工部分采用范围",
        }
        store = self.seed(snapshot, self.artifacts, name="partial-adoption-unknown-scope")
        before = self.state(store)
        result = TeachingService(store).run(self.request("open"))
        self.assert_unsaved(result)
        self.assertEqual(self.state(store), before)

    def test_known_timeline_time_requires_parseable_timezone(self):
        for value in ("2026-10-03T09:00:00", "不是可解析时间"):
            with self.subTest(value=value):
                request = initial_request()
                request["initial_response"]["time"] = fact("known", value=value)
                before = self.state()
                result = self.service.run(request)
                self.assert_unsaved(result)
                self.assertIn("known_timeline_timestamp_required", self.codes(result))
                self.assertEqual(self.state(), before)
                self.assertNotIn(EVENT_ID, self.objects())

    def test_checkpoint_and_close_same_payload_retries_do_not_advance_state(self):
        self.initial()
        checkpoint = self.close_request(action="checkpoint", operation_id="FIX-b3b-save-checkpoint")
        saved = self.service.run(checkpoint)
        self.assertEqual(saved["status"], "committed", saved)
        before_retry = self.state()
        self.assertEqual(self.service.run(copy.deepcopy(checkpoint)), saved)
        self.assertEqual(self.state(), before_retry)
        self.assertEqual(self.event()["revision"], 1)
        close = self.close_request(checkpoint_id="FIX-b3b-final-checkpoint")
        closed = self.service.run(close)
        self.assertEqual(closed["status"], "committed", closed)
        before_retry = self.state()
        self.assertEqual(self.service.run(copy.deepcopy(close)), closed)
        self.assertEqual(self.state(), before_retry)
        self.assertEqual(self.event()["revision"], 2)

    def test_extra_object_reference_revision_change_blocks_current_execution_not_historical_reads(self):
        snapshot = copy.deepcopy(self.snapshot)
        objects = objects_by_id(snapshot)
        extra = copy.deepcopy(objects["FIX-content-source"])
        extra["id"] = "FIX-b3b-extra-reference"
        extra["verification"]["content"] = copy.deepcopy(objects["FIX-material"]["verification"]["content"])
        snapshot["objects"].append(extra)
        extra_ref = ref(extra)
        activity = objects["FIX-activity"]
        activity["reference_refs"].append(extra_ref)
        activity["branches"][0]["reference_refs"].append(extra_ref)
        store = self.seed(snapshot, self.artifacts, name="extra-reference-revisions")
        service = TeachingService(store)
        opened = service.run(self.request("open"))
        self.assertEqual(opened["status"], "ready", opened)
        initialized = service.run(initial_request())
        self.assertEqual(initialized["status"], "committed", initialized)
        changed = copy.deepcopy(extra)
        changed["revision"] = 2
        changed["verification"]["content"]["checked_revision"] = 2
        changed["claims"] = ["人工参考发生修订，旧执行用途需要复核"]
        source_store = LearningStore(store.root, entry_actor="AG2")
        updated = source_store.commit(self.revision(store), "FIX-b3b-extra-reference-updated", [changed],
                                      authorization_refs=[{"id": "FIX-b2b-material-grant", "revision": 1}],
                                      adoption_refs=[{"id": "FIX-b2b-material-work", "revision": 1}])
        self.assertEqual(updated["status"], "committed", updated)
        before = self.state(store)
        feedback = self.feedback_request(event_ref=ref(self.event(store)), expected_state_revision=self.revision(store))
        for request in (self.request("open"), initial_request(self.revision(store)), feedback):
            with self.subTest(action=request["action"]):
                result = service.run(request)
                self.assert_unsaved(result)
                self.assertIn("stale_basis_reference", self.codes(result))
                self.assertNotIn("learner_packet", result)
                self.assertNotIn("learner_next_work", result)
                self.assertEqual(self.state(store), before)
        historical = store.read_refs([extra_ref], "read")
        self.assertEqual(historical["status"], "ok", historical)
        self.assertEqual(historical["objects"], [extra])
        original = store.read_refs([{"id": EVENT_ID, "revision": 1}], "read")
        self.assertEqual(original["status"], "ok", original)
        self.assertEqual(original["objects"][0]["original_response"], anchor(INITIAL_PATH, "B3b-initial"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

