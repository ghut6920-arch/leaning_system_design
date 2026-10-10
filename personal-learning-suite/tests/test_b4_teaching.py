"""Independent B4 behavior checks on isolated artificial teaching records.

Content findings, visibility and authority below are explicit developer-made
declarations. Passing establishes controlled behavior, not professional truth,
host authority, authenticated display or an actual learner's progress.
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
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from runtime.learning_materials import fact, ref
from runtime.learning_store import LearningStore
from runtime.learning_teaching_b4 import SpecializedTeachingService, VERSION
from test_b2b_materials import objects_by_id
from test_b3b_teaching import GRANT_ID, anchor, fixture as c0_fixture, initial_request as c0_initial_request
from test_b3a_assessment import fixture as assessment_fixture

EVENT_ID = "FIX-b4-event"
SAMPLE_ID = "FIX-b4-sample"
INITIAL_PATH = "b4-initial.md"
INITIAL_TEXT = "# B4-initial\nQ。\n"
SUPPLIED_PATH = "b4-supplied-revision.md"
SUPPLIED_TEXT = "# B4-supplied-revision\n已看到前提，仍只写 Q。\n"
LOCAL_PATH = "b4-local-revision.md"
LOCAL_TEXT = "# B4-local-revision\nP 成立且 P→Q，所以 Q。\n"
WHOLE_PATH = "b4-whole-proof.md"
WHOLE_TEXT = "# B4-whole-proof\nP 与 P→Q 推出 Q；由 Q 与 Q→R 推出 R。\n"


def specialist_metadata(module="post", whole=False):
    value = {
        "version": VERSION, "module": module,
        "work": "连接给定前提并返回同一父论证",
        "needed_structure": "前提与结论之间的合法连接",
        "change_and_hold": {"change": ["理由表达"], "hold": ["给定前提"], "allowed_additions": []},
        "acceptable_products": ["带合法连接理由的不同等价表达"],
        "whole_required": whole, "whole_reference_refs": [], "whole_obligations": [],
        "interfaces": [], "branch_routes": ["enter_encoding", "end"],
    }
    if module == "post":
        value["post_function"] = "integration"
    return value


def fixture(module="post"):
    snapshot, artifacts, context = c0_fixture()
    snapshot["fixture_id"] = "B4-synthetic-specialist"
    snapshot["description"] = "隔离人工专项教学；没有真实学习、授权、接触或学科认证。"
    objects = objects_by_id(snapshot)
    for grant in (obj for obj in snapshot["objects"] if obj["type"] == "AuthorizationGrant"):
        grant["validity"] = fact("known", value={"active": True})
    activity = objects["FIX-activity"]
    for requirement in objects["FIX-goal"]["requirements"]:
        requirement["teaching_scope"] = {"whole_required": False, "whole_obligations": []}
    activity["metadata"] = {"b4": specialist_metadata(module)}
    activity["adoption"] = {
        "status": "adopted", "by": "AG1", "scope": "人工局部教学规格",
        "basis_refs": [{"id": "FIX-user-grant", "revision": 1}],
        "limitations": ["仅夹具"], "time": fact("not_executed", "无真实采用"),
    }
    activity["decision_type"] = "teaching_design"
    activity["branches"].append({
        "observation": "原答已保留当前连接，相关判断可复用",
        "action": "结束目标内已经够用的局部工作",
        "next_observation": "出现目标内新条件或有价值的反证时再打开",
        "counterevidence": "若判断用途或条件未覆盖，不宣称够用",
        "stop": "当前活动结束，不新增证明或复习债务",
        "reference_refs": copy.deepcopy(activity["branches"][0]["reference_refs"]),
        "learner_next_work": "当前局部结束",
    })
    return snapshot, artifacts, context


def initial_request(state_revision=1, operation_id="FIX-b4-initial"):
    request = c0_initial_request(state_revision, operation_id)
    request.update(event_id=EVENT_ID, independent_sample_id=SAMPLE_ID,
                   original_response=anchor(INITIAL_PATH, "B4-initial"),
                   artifacts={INITIAL_PATH: INITIAL_TEXT})
    return request


def whole_fixture(coverage=True):
    snapshot, artifacts, context = fixture("encoding")
    objects = objects_by_id(snapshot)
    activity, material = objects["FIX-activity"], objects["FIX-material"]
    operations = ["connect-P-to-Q", "connect-Q-to-R"]
    obligations = ["保留给定前提", "合法连接 P 到 Q", "合法连接 Q 到 R"]
    activity["criterion_refs"] = [{"id": "FIX-goal", "revision": 1, "locator": "requirements/complete-chain"}]
    activity["learner_operations"] = operations
    activity["prompt"] = "由给定 P、P→Q、Q→R 形成完整合法理由链。"
    activity["task_qualification"]["value"]["target_operations"] = operations
    spec = activity["metadata"]["b4"]
    requirement = next(r for r in objects["FIX-goal"]["requirements"] if r["requirement_id"] == "complete-chain")
    requirement["teaching_scope"] = {"whole_required": True, "whole_obligations": obligations}
    spec.update(whole_required=True, whole_reference_refs=[ref(material)], whole_obligations=obligations,
                branch_routes=["whole", "end"])
    material["visible_input"] = [{"content": "P；P→Q；Q→R", "provided_operations": [], "channel": "body"}]
    whole_anchor = anchor("b4-whole-reference.md", "B4-whole-reference")
    if coverage:
        artifacts["b4-whole-reference.md"] = "# B4-whole-reference\nP 与 P→Q 推出 Q；Q 与 Q→R 推出 R。\n"
        material["verification"]["content"]["whole_coverage"] = {
            "status": "supported", "target_operations": operations,
            "goal_refs": copy.deepcopy(activity["goal_refs"]), "criterion_refs": copy.deepcopy(activity["criterion_refs"]),
            "obligations": obligations, "anchor_refs": [whole_anchor],
            "goal_refs": copy.deepcopy(activity["goal_refs"]),
            "criterion_refs": copy.deepcopy(activity["criterion_refs"]),
        }
        material["verification"]["content"]["scope"] = "人工完整两步论证的明确整体覆盖声明"
        material["verification"]["content"]["unchecked_scope"] = ["真实专业认证", "目标外证明"]
    return snapshot, artifacts, context


def evidence_fixture():
    snapshot, artifacts, judgment, _context, _note, _diagnostic_context = assessment_fixture()
    judgment["adoption"] = {
        "status": "adopted", "by": "AG3", "scope": "人工当前局部独立连接判断",
        "basis_refs": [copy.deepcopy(judgment["authorization_ref"])],
        "limitations": ["仅人工夹具声明"], "time": fact("not_executed", "无真实采用"),
    }
    snapshot["objects"].append(judgment)
    return snapshot, artifacts, judgment


class B4TeachingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pl-b4-artificial-")
        self.addCleanup(self.temp.cleanup)
        self.snapshot, self.artifacts, self.binding = fixture()
        self.store = self.seed(self.snapshot, self.artifacts)
        self.root = self.store.root
        self.service = SpecializedTeachingService(self.store)

    def seed(self, snapshot, artifacts, name="workspace", actor="AG0"):
        store = LearningStore(Path(self.temp.name) / name, entry_actor=actor)
        self.assertEqual(store.init_workspace()["status"], "committed")
        seeded = store.import_fixture(snapshot, artifacts)
        self.assertEqual(seeded["status"], "committed", seeded)
        return store

    def state(self, store=None):
        state = (store or self.store).read_context()
        self.assertEqual(state["status"], "ok", state)
        return state

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
        if action not in {"open", "resume", "design", "select_branch", "review_whole", "reuse_evidence"}:
            request.update(expected_state_revision=self.revision(), operation_id="FIX-b4-" + action)
        request.update(fields)
        return request

    def execute(self, action, **fields):
        return self.service.run(self.request(action, **fields))

    def assert_unsaved(self, result):
        self.assertIn(result["status"], {"rejected", "blocked", "limited", "conflict", "stopped", "not_ready", "not_saved", "needs_work"}, result)
        self.assertFalse(result.get("mutated", False), result)

    def initial(self, **fields):
        request = initial_request(self.revision())
        request.update(fields)
        result = self.service.run(request)
        self.assertEqual(result["status"], "committed", result)
        return result

    def help(self, visibility="displayed", **fields):
        return self.execute("record_help", event_ref=ref(self.event()), help={
            "content": "人工支持：P 与 P→Q 已明确给定。", "visibility": visibility,
            "target_operations": ["connect-P-to-Q"], "substituted_operations": [],
            "time": fact("unknown", "人工顺序，没有真实展示时间"),
        }, **fields)

    def revise(self, path=SUPPLIED_PATH, text=SUPPLIED_TEXT, locator="B4-supplied-revision", **fields):
        return self.execute("record_revision", event_ref=ref(self.event()),
            revision_response=anchor(path, locator), artifacts={path: text}, revision={
                "content": text.splitlines()[-1], "visibility": "displayed",
                "target_operations": ["connect-P-to-Q"], "substituted_operations": [],
                "time": fact("unknown", "人工顺序，没有真实作答时间"),
            }, operation_id="FIX-b4-revision-" + path, **fields)

    def supplied(self):
        self.initial()
        self.assertEqual(self.help()["status"], "committed")
        self.assertEqual(self.revise()["status"], "committed")

    def local(self, module="encoding", path=SUPPLIED_PATH, locator="B4-supplied-revision", quote="已看到前提，仍只写 Q。"):
        return {
            "module": module, "operations": ["connect-P-to-Q"],
            "reason": "供给可用前提后仍未连接理由，需要局部关系支持",
            "blocker": "在本人工修订中未写出连接",
            "local_sufficiency": "能将给定前提合法连接为 Q 并实际使用",
            "return_connection": "返回同一父产物的当前连接，保留整体未完成",
            "alternative_explanations": ["可能只省略了表达", "可能尚未建立当前连接"],
            "preserved_support_refs": [{"id": "FIX-judgment", "revision": 1}],
            "observation": {"artifact_ref": anchor(path, locator), "quote": quote},
            "premises_supplied": fact("known", value=True),
        }

    def test_open_and_initial_preserve_c0_privacy_and_same_event_identity(self):
        before = self.state()
        opened = self.execute("open")
        self.assertEqual(opened["status"], "ready", opened)
        for secret in ("B3B-BACKUP-SECRET", "B3B-TEACHER-SECRET", "teacher_reference", "backup_help"):
            self.assertNotIn(secret, json.dumps(opened, ensure_ascii=False))
        self.assertEqual(self.state(), before)
        result = self.initial()
        event = self.event()
        self.assertEqual(event["metadata"]["b4"]["module"], "post")
        self.assertEqual(event["metadata"]["b4"]["stack"], [])
        self.assertEqual(event["metadata"]["b4"]["transition_history"], [])
        self.assertEqual(event["independent_sample_id"], SAMPLE_ID)
        self.assertEqual(result["assessment_handoff"]["event_ref"], ref(event))
        self.assertEqual(event["timeline_completeness"]["status"], "unknown")
        self.assertEqual(event["contact_history"]["status"], "unknown")
        self.assertEqual(result["scoring"], "not_executed")
        self.assertFalse(result["judgment_created"])

    def test_unknown_or_unadopted_specialist_design_never_starts_execution(self):
        for mode in ("candidate", "recheck", "missing_metadata", "wrong_version", "invalid_post_function"):
            with self.subTest(mode=mode):
                snapshot = copy.deepcopy(self.snapshot)
                activity = objects_by_id(snapshot)["FIX-activity"]
                if mode in {"candidate", "recheck"}:
                    activity["adoption"]["status"] = mode
                elif mode == "missing_metadata":
                    activity.pop("metadata")
                elif mode == "wrong_version":
                    activity["metadata"]["b4"]["version"] = "pl-teaching-b4/future"
                else:
                    activity["metadata"]["b4"]["post_function"] = "universal-cycle"
                store = self.seed(snapshot, self.artifacts, name=mode)
                before = self.state(store)
                service = SpecializedTeachingService(store)
                for request in (self.request("open"), initial_request()):
                    result = service.run(request)
                    self.assert_unsaved(result)
                    self.assertNotIn("learner_packet", result)
                    self.assertNotIn("event_ref", result)
                    self.assertEqual(self.state(store), before)

    def test_post_to_encoding_needs_actual_supplied_premises_and_following_response(self):
        self.initial()
        before = self.state()
        local = self.local(path=INITIAL_PATH, locator="B4-initial", quote="Q。")
        result = self.execute("enter_local", event_ref=ref(self.event()), local=local)
        self.assert_unsaved(result)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.help(visibility="planned")["status"], "committed")
        self.assertEqual(self.revise()["status"], "committed")
        before = self.state()
        result = self.execute("enter_local", event_ref=ref(self.event()), local=self.local())
        self.assert_unsaved(result)
        self.assertEqual(self.state(), before)

    def test_local_declaration_rejects_unknown_premises_and_scope_expansion(self):
        self.supplied()
        for mutate in (
            lambda local: local.update(premises_supplied=fact("unknown", "没有足够前提事实")),
            lambda local: local.update(operations=["outside-goal-operation"]),
            lambda local: local.update(module="post"),
            lambda local: local.update(alternative_explanations=[]),
            lambda local: local["observation"].update(quote="原件中不存在的诊断句"),
        ):
            with self.subTest(mutate=mutate):
                local = self.local()
                mutate(local)
                before = self.state()
                result = self.execute("enter_local", event_ref=ref(self.event()), local=local)
                self.assert_unsaved(result)
                self.assertEqual(self.state(), before)

    def test_nested_local_entry_requires_a_new_response_not_another_reason(self):
        self.supplied()
        saved = self.execute("enter_local", event_ref=ref(self.event()), local=self.local())
        self.assertEqual(saved["status"], "committed", saved)
        before = self.state()
        repeated = self.local(module="post")
        repeated["reason"] = "换一个理由仍引用同一次旧修订"
        result = self.execute("enter_local", event_ref=ref(self.event()), local=repeated,
                              operation_id="FIX-b4-repeated-old-observation")
        self.assert_unsaved(result)
        self.assertIn("new_local_observation_required", {r["code"] for r in result["reasons"]})
        self.assertEqual(self.state(), before)

    def test_returned_local_scope_requires_new_parent_work_before_reentry(self):
        self.supplied()
        local = self.local()
        self.assertEqual(self.execute("enter_local", event_ref=ref(self.event()), local=local)["status"], "committed")
        self.assertEqual(self.revise(LOCAL_PATH, LOCAL_TEXT, "B4-local-revision")["status"], "committed")
        observation = {"artifact_ref": anchor(LOCAL_PATH, "B4-local-revision"), "quote": "P 成立且 P→Q，所以 Q。"}
        returned = self.execute("return_local", event_ref=ref(self.event()), return_connection=local["return_connection"],
            local_observation=observation, local_outcome="sufficient", parent_outcome="not_observed")
        self.assertEqual(returned["status"], "committed", returned)
        reopened = SpecializedTeachingService(LearningStore(self.root))
        before = self.state()
        repeated = self.local(path=LOCAL_PATH, locator="B4-local-revision", quote=observation["quote"])
        result = reopened.run(self.request("enter_local", event_ref=ref(self.event()), local=repeated,
                                           operation_id="FIX-b4-old-return-reentry"))
        self.assert_unsaved(result)
        self.assertIn("new_local_observation_required", {r["code"] for r in result["reasons"]})
        self.assertEqual(self.state(), before)

    def test_new_responses_allow_nested_local_work_without_a_depth_limit(self):
        self.supplied()
        self.assertEqual(self.execute("enter_local", event_ref=ref(self.event()), local=self.local())["status"], "committed")
        for index in range(3):
            path, locator = f"b4-progress-{index}.md", f"B4-progress-{index}"
            quote = f"新的人工响应 {index}：当前父连接仍未完成。"
            self.assertEqual(self.revise(path, f"# {locator}\n{quote}\n", locator)["status"], "committed")
            current_module = self.event()["metadata"]["b4"]["module"]
            local = self.local(module="post" if current_module == "encoding" else "encoding",
                               path=path, locator=locator, quote=quote)
            result = self.execute("enter_local", event_ref=ref(self.event()), local=local,
                                  operation_id=f"FIX-b4-new-local-{index}")
            self.assertEqual(result["status"], "committed", result)
        self.assertEqual(len(self.event()["metadata"]["b4"]["stack"]), 4)
        self.assertEqual(self.event()["independent_sample_id"], SAMPLE_ID)
        self.assertFalse(result["judgment_created"])

    def test_local_same_request_is_idempotent_and_changed_payload_is_rejected(self):
        self.supplied()
        request = self.request("enter_local", event_ref=ref(self.event()), local=self.local())
        saved = self.service.run(request)
        self.assertEqual(saved["status"], "committed", saved)
        before = self.state()
        retry = self.service.run(copy.deepcopy(request))
        self.assertEqual(retry, saved)
        self.assertEqual(self.state(), before)
        changed = copy.deepcopy(request)
        changed["local"]["reason"] = "相同 operation_id 的不同理由"
        self.assert_unsaved(self.service.run(changed))
        self.assertEqual(self.state(), before)

    def test_stale_cas_rejects_local_entry_without_candidate_receipt(self):
        self.supplied()
        request = self.request("enter_local", event_ref=ref(self.event()), local=self.local())
        controlled = self.store.pause(self.revision(), "FIX-b4-unrelated-pause", ["FIX-method"], "仅人工无关状态变化")
        self.assertEqual(controlled["status"], "committed", controlled)
        before = self.state()
        result = self.service.run(request)
        self.assertEqual(result["status"], "conflict", result)
        self.assertFalse(result["mutated"])
        for field in ("event_ref", "checkpoint_ref", "next_action", "learner_next_work", "assessment_handoff"):
            self.assertNotIn(field, result)
        self.assertEqual(self.state(), before)

    def test_failed_initial_transaction_has_no_saved_event_or_artifact(self):
        before = self.state()
        def fail(stage):
            if stage == "after_write":
                raise RuntimeError("人工事务失败")
        self.store.failpoint = fail
        result = self.service.run(initial_request())
        self.store.failpoint = None
        self.assertEqual(result["status"], "not_saved", result)
        self.assertFalse(result["mutated"])
        self.assertNotIn("event_ref", result)
        self.assertNotIn("assessment_handoff", result)
        self.assertEqual(self.state(), before)
        self.assertNotIn(EVENT_ID, self.objects())
        self.assertNotIn(INITIAL_PATH, self.store.export_scope([EVENT_ID], include_artifacts=True).get("artifacts", {}))

    def test_failed_transition_transaction_preserves_module_stack_and_help(self):
        self.supplied()
        before = self.state()
        def fail(stage):
            if stage == "after_write":
                raise RuntimeError("人工专项事务失败")
        self.store.failpoint = fail
        result = self.execute("enter_local", event_ref=ref(self.event()), local=self.local())
        self.store.failpoint = None
        self.assertEqual(result["status"], "not_saved", result)
        self.assertFalse(result["mutated"])
        for field in ("event_ref", "next_action", "checkpoint_ref"):
            self.assertNotIn(field, result)
        self.assertEqual(self.state(), before)

    def test_pause_restrict_and_delete_gate_specialist_actions_and_old_replay(self):
        for control in ("pause", "restrict", "delete"):
            with self.subTest(control=control):
                store = self.seed(self.snapshot, self.artifacts, name="control-" + control)
                service = SpecializedTeachingService(store)
                original = initial_request()
                self.assertEqual(service.run(original)["status"], "committed")
                state = self.state(store)
                if control == "pause":
                    receipt = store.pause(state["state_revision"], "FIX-b4-control-pause", [EVENT_ID], "人工暂停")
                elif control == "restrict":
                    receipt = store.restrict(state["state_revision"], "FIX-b4-control-restrict", [EVENT_ID], "人工用途待核", ["teaching_execution"])
                else:
                    receipt = store.delete_scope(state["state_revision"], "FIX-b4-control-delete", [EVENT_ID])
                self.assertEqual(receipt["status"], "committed", receipt)
                before = self.state(store)
                replay = service.run(copy.deepcopy(original))
                self.assert_unsaved(replay)
                self.assertNotIn("event_ref", replay)
                old_ref = {"id": EVENT_ID, "revision": 1}
                resumed = service.run(self.request("resume", event_ref=old_ref))
                self.assert_unsaved(resumed)
                self.assertNotIn("recovery", resumed)
                self.assertEqual(self.state(store), before)

    def test_budget_exhaustion_stops_new_expansion_and_keeps_original_goal(self):
        self.initial(active_minutes=4)
        self.assertEqual(self.help(active_minutes=4)["status"], "committed")
        self.assertEqual(self.revise(active_minutes=4)["status"], "committed")
        before = self.state()
        result = self.execute("enter_local", event_ref=ref(self.event()), local=self.local(), active_minutes=5)
        self.assert_unsaved(result)
        self.assertEqual(self.state(), before)
        saved = self.execute("checkpoint", event_ref=ref(self.event()), checkpoint_id="FIX-b4-budget-checkpoint",
            stop_reason="人工共用预算已到", next_connection="返回同一父论证的当前连接",
            pending_owners=["AG1"], unrecorded_actions=fact("unknown", "未保存期间无法核查"), active_minutes=5)
        self.assertEqual(saved["status"], "committed", saved)
        self.assertEqual(self.objects()["FIX-goal"], objects_by_id(before)["FIX-goal"])
        self.assertEqual(self.objects()["FIX-plan"], objects_by_id(before)["FIX-plan"])

    def test_cli_open_and_unknown_action_emit_json_without_writes(self):
        before = self.state()
        request_path = Path(self.temp.name) / "caller-owned-b4-request.json"
        for action, code, status in (("open", 0, "ready"), ("invented_cycle", 1, "rejected")):
            with self.subTest(action=action):
                request_path.write_text(json.dumps(self.request(action), ensure_ascii=False), encoding="utf-8")
                completed = subprocess.run([
                    sys.executable, str(ROOT / "src/runtime/learning_teaching_b4.py"),
                    "--workspace", str(self.root), "--request", str(request_path),
                ], capture_output=True, text=True, encoding="utf-8", timeout=30)
                self.assertEqual(completed.returncode, code, completed.stdout + completed.stderr)
                output = json.loads(completed.stdout)
                self.assertEqual(output["status"], status, output)
                self.assertEqual(output["scoring"], "not_executed")
                self.assertEqual(self.state(), before)
        self.assertTrue(request_path.exists())

    def test_ag1_design_returns_candidate_and_formal_commit_requires_adoption(self):
        store = LearningStore(self.root, entry_actor="AG1")
        service = SpecializedTeachingService(store)
        activity = copy.deepcopy(self.objects()["FIX-activity"])
        activity["revision"] = 2
        context = copy.deepcopy(self.binding)
        context["activity_ref"] = ref(activity)
        before = self.state()
        request = {"synthetic_only": True, "action": "design", "activity": activity, "context": context}
        result = service.run(request)
        self.assertEqual(result["status"], "candidate", result)
        self.assertEqual(result["activity_candidate"]["adoption"]["status"], "candidate")
        self.assertEqual(self.state(), before)
        candidate = copy.deepcopy(result["activity_candidate"])
        commit = {**request, "action": "commit_design", "activity": candidate,
            "expected_state_revision": self.revision(), "operation_id": "FIX-b4-design-adopt",
            "authorization_refs": [{"id": "FIX-user-grant", "revision": 1}],
            "adoption_refs": [{"id": "FIX-user-grant", "revision": 1}]}
        self.assert_unsaved(service.run(commit))
        self.assertEqual(self.state(), before)
        commit["activity"] = activity
        saved = service.run(commit)
        self.assertEqual(saved["status"], "committed", saved)
        self.assertEqual(self.objects()["FIX-activity"], activity)
        self.assertNotIn(EVENT_ID, self.objects())
        # Design adoption alone cannot reuse the old material-use binding.
        opened = self.service.run(self.request("open", activity_ref=ref(activity), context=context))
        self.assert_unsaved(opened)
        self.assertNotIn("learner_packet", opened)

    def test_design_rejects_missing_whole_reference_and_local_only_coverage(self):
        for mode in ("missing", "local_only", "partial_operations", "missing_obligation", "unverified", "other_goal", "missing_criterion"):
            with self.subTest(mode=mode):
                snapshot, artifacts, context = whole_fixture(coverage=mode != "local_only")
                objects = objects_by_id(snapshot)
                activity = objects["FIX-activity"]
                content = objects["FIX-material"]["verification"]["content"]
                if mode == "missing":
                    activity["metadata"]["b4"]["whole_reference_refs"] = []
                elif mode == "partial_operations":
                    content["whole_coverage"]["target_operations"] = ["connect-P-to-Q"]
                elif mode == "missing_obligation":
                    content["whole_coverage"]["obligations"] = ["保留给定前提"]
                elif mode == "unverified":
                    content["status"] = "pending"
                elif mode == "other_goal":
                    content["whole_coverage"]["goal_refs"] = [{"id": "FIX-parent-activity", "revision": 1}]
                elif mode == "missing_criterion":
                    content["whole_coverage"]["criterion_refs"] = []
                store = self.seed(snapshot, artifacts, name="whole-" + mode, actor="AG1")
                before = self.state(store)
                result = SpecializedTeachingService(store).run({"synthetic_only": True, "action": "design", "activity": activity, "context": context})
                self.assert_unsaved(result)
                self.assertEqual(self.state(store), before)
                self.assertEqual(activity["criterion_refs"][0]["locator"], "requirements/complete-chain")

    def test_select_branch_changes_only_prepared_candidate_and_preserves_record(self):
        self.initial()
        before = self.state()
        observation = {"artifact_ref": anchor(INITIAL_PATH, "B4-initial"), "quote": "Q。"}
        first = self.execute("select_branch", event_ref=ref(self.event()), branch_index=0, observation=observation)
        second = self.execute("select_branch", event_ref=ref(self.event()), branch_index=1, observation=observation)
        self.assertEqual(first["status"], "candidate", first)
        self.assertEqual(first["route"], "enter_encoding")
        self.assertEqual(second["status"], "candidate", second)
        self.assertEqual(second["route"], "end")
        self.assertEqual(first["branch"], self.objects()["FIX-activity"]["branches"][0])
        self.assertEqual(second["branch"], self.objects()["FIX-activity"]["branches"][1])
        self.assertEqual(first["diagnostic_status"], "not_created")
        self.assertFalse(first["next_action_adopted"])
        for index in (2, -1, True):
            self.assert_unsaved(self.execute("select_branch", event_ref=ref(self.event()), branch_index=index, observation=observation))
        self.assertEqual(self.state(), before)

    def test_branch_cannot_use_another_event_or_reference_as_learner_observation(self):
        self.initial()
        before = self.state()
        for observation in (
            {"artifact_ref": self.objects()["FIX-event"]["original_response"], "quote": "Q"},
            {"artifact_ref": anchor("b2b-reference.md", "核验范围"), "quote": "人工构造"},
            {"artifact_ref": anchor(INITIAL_PATH, "B4-initial"), "quote": "不存在的原答"},
        ):
            result = self.execute("select_branch", event_ref=ref(self.event()), branch_index=0, observation=observation)
            self.assert_unsaved(result)
            self.assertNotIn("branch", result)
        self.assertEqual(self.state(), before)

    def test_post_encoding_return_uses_same_event_parent_budget_and_actual_help(self):
        self.supplied()
        parent_before = copy.deepcopy(self.objects()["FIX-parent-activity"])
        initial_before = copy.deepcopy(self.event()["original_response"])
        help_before = copy.deepcopy(self.event()["timeline"][1])
        entered = self.execute("enter_local", event_ref=ref(self.event()), local=self.local())
        self.assertEqual(entered["status"], "committed", entered)
        event = self.event()
        frame = event["metadata"]["b4"]["stack"][0]
        self.assertEqual(frame["parent_activity_ref"], event["activity_ref"])
        self.assertEqual(frame["parent_artifact"], anchor(SUPPLIED_PATH, "B4-supplied-revision"))
        self.assertEqual(frame["budget_ref"], {"id": "FIX-budget", "revision": 1})
        self.assertEqual(frame["parent_task"], self.objects()["FIX-activity"]["parent_task"])
        self.assertEqual(event["metadata"]["b4"]["module"], "encoding")
        self.assertEqual(self.revise(LOCAL_PATH, LOCAL_TEXT, "B4-local-revision")["status"], "committed")
        returned = self.execute("return_local", event_ref=ref(self.event()),
            return_connection=frame["return_connection"],
            local_observation={"artifact_ref": anchor(LOCAL_PATH, "B4-local-revision"), "quote": "P 成立且 P→Q，所以 Q。"},
            local_outcome="sufficient", parent_outcome="still_blocked")
        self.assertEqual(returned["status"], "committed", returned)
        self.assertEqual(returned["next_action"], "review_interfaces_or_close")
        self.assertEqual(returned["overall_support"], "not_assessed")
        event = self.event()
        self.assertEqual(event["metadata"]["b4"]["module"], "post")
        self.assertEqual(event["metadata"]["b4"]["stack"], [])
        self.assertEqual([change["kind"] for change in event["metadata"]["b4"]["transition_history"]], ["enter_local", "return_local"])
        self.assertEqual(event["independent_sample_id"], SAMPLE_ID)
        self.assertEqual(event["original_response"], initial_before)
        self.assertEqual(event["timeline"][1], help_before)
        self.assertEqual(self.objects()["FIX-parent-activity"], parent_before)
        self.assertEqual(event["contact_history"]["status"], "unknown")
        self.assertEqual(len([obj for obj in self.objects().values() if obj["id"] == EVENT_ID]), 1)

    def test_encoding_can_enter_post_and_return_without_forced_recovery_first(self):
        snapshot, artifacts, _context = fixture("encoding")
        store = self.seed(snapshot, artifacts, name="encoding-post")
        self.store, self.service = store, SpecializedTeachingService(store)
        self.initial()
        local = self.local("post", INITIAL_PATH, "B4-initial", "Q。")
        local["premises_supplied"] = fact("known", value=False)
        entered = self.execute("enter_local", event_ref=ref(self.event()), local=local)
        self.assertEqual(entered["status"], "committed", entered)
        self.assertEqual(self.event()["metadata"]["b4"]["module"], "post")
        self.assertEqual(self.revise(LOCAL_PATH, LOCAL_TEXT, "B4-local-revision")["status"], "committed")
        returned = self.execute("return_local", event_ref=ref(self.event()), return_connection=local["return_connection"],
            local_observation={"artifact_ref": anchor(LOCAL_PATH, "B4-local-revision"), "quote": "P 成立且 P→Q，所以 Q。"},
            local_outcome="sufficient", parent_outcome="not_observed")
        self.assertEqual(returned["status"], "committed", returned)
        self.assertEqual(self.event()["metadata"]["b4"]["module"], "encoding")
        self.assertEqual(returned["next_action"], "resume_same_parent_work")
        self.assertEqual(returned["overall_support"], "not_assessed")

    def test_return_requires_new_response_and_preserves_declared_parent_connection(self):
        self.supplied()
        self.assertEqual(self.execute("enter_local", event_ref=ref(self.event()), local=self.local())["status"], "committed")
        before = self.state()
        request = self.request("return_local", event_ref=ref(self.event()), return_connection=self.local()["return_connection"],
            local_observation=self.local()["observation"], local_outcome="sufficient", parent_outcome="not_observed")
        self.assert_unsaved(self.service.run(request))
        request["return_connection"] = "擅自返回另一个任务"
        self.assert_unsaved(self.service.run(request))
        self.assertEqual(self.state(), before)

    def test_checkpoint_reopen_restores_module_stack_and_help_without_resetting_unknowns(self):
        self.supplied()
        entered = self.execute("enter_local", event_ref=ref(self.event()), local=self.local())
        self.assertEqual(entered["status"], "committed", entered)
        saved = self.execute("checkpoint", event_ref=ref(self.event()), checkpoint_id="FIX-b4-local-checkpoint",
            stop_reason="人工会话结束，局部工作尚未完成", next_connection=self.local()["return_connection"],
            pending_owners=["AG0", "AG1"], unrecorded_actions=fact("unknown", "断点之后没有可靠动作记录"))
        self.assertEqual(saved["status"], "committed", saved)
        before = self.state()
        reopened = LearningStore(self.root, entry_actor="AG0")
        result = SpecializedTeachingService(reopened).run(self.request("resume", checkpoint_ref=saved["checkpoint_ref"]))
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(result["recovery"]["specialization"], self.event()["metadata"]["b4"])
        self.assertEqual(result["recovery"]["specialization"]["module"], "encoding")
        self.assertEqual(result["recovery"]["unrecorded_actions"]["status"], "unknown")
        self.assertEqual(result["recovery"]["parent_help_history_refs"], [{"id": "FIX-event", "revision": 1}])
        self.assertEqual(self.state(reopened), before)
        self.assertEqual(reopened.check_integrity()["status"], "ok")

    def test_whole_review_preserves_continuous_product_actual_help_and_declared_obligations(self):
        snapshot, artifacts, context = whole_fixture()
        store = self.seed(snapshot, artifacts, name="whole-review")
        self.store, self.binding, self.service = store, context, SpecializedTeachingService(store)
        self.initial()
        self.assertEqual(self.help()["status"], "committed")
        self.assertEqual(self.revise(WHOLE_PATH, WHOLE_TEXT, "B4-whole-proof")["status"], "committed")
        before = self.state()
        result = self.execute("review_whole", event_ref=ref(self.event()), product_ref=anchor(WHOLE_PATH, "B4-whole-proof"),
            requirement_ids=["complete-chain"], intended_use="independent_check")
        self.assertEqual(result["status"], "ready_for_review", result)
        self.assertEqual(result["continuous_product"], WHOLE_TEXT)
        self.assertEqual(result["whole_obligations"], objects_by_id(snapshot)["FIX-activity"]["metadata"]["b4"]["whole_obligations"])
        self.assertEqual(result["overall_support"], "not_assessed")
        self.assertEqual(result["assessment_handoff"]["event_ref"], ref(self.event()))
        self.assertEqual(result["assessment_handoff"]["response_point"]["sequence"], 3)
        self.assertEqual(result["assessment_handoff"]["decision_type"], "complex_product")
        self.assertEqual(result["assessment_handoff"]["requirement_ids"], ["complete-chain"])
        self.assertEqual(result["next_owner"], "AG3")
        self.assertFalse(result["assessment_handoff"]["assessment_called"])
        self.assertEqual(self.state(), before)

    def test_whole_review_does_not_stitch_fragments_or_accept_parent_copy(self):
        snapshot, artifacts, context = whole_fixture()
        store = self.seed(snapshot, artifacts, name="whole-fragments")
        self.store, self.binding, self.service = store, context, SpecializedTeachingService(store)
        self.initial()
        before = self.state()
        parent = self.objects()["FIX-activity"]["parent_task"]["value"]["parent_artifact"]
        for product in ([anchor(INITIAL_PATH, "B4-initial"), parent], parent):
            result = self.execute("review_whole", event_ref=ref(self.event()), product_ref=product,
                requirement_ids=["complete-chain"], intended_use="independent_check")
            self.assert_unsaved(result)
            self.assertNotIn("continuous_product", result)
        self.assertEqual(self.state(), before)

    def test_closed_whole_product_remains_reviewable_after_budget_end(self):
        snapshot, artifacts, context = whole_fixture()
        store = self.seed(snapshot, artifacts, name="closed-whole")
        self.store, self.binding, self.service = store, context, SpecializedTeachingService(store)
        self.initial(active_minutes=4)
        self.assertEqual(self.revise(WHOLE_PATH, WHOLE_TEXT, "B4-whole-proof", active_minutes=4)["status"], "committed")
        result = self.execute("close", event_ref=ref(self.event()), checkpoint_id="FIX-b4-closed-whole-checkpoint",
            stop_reason="人工预算结束，产物待整体复核", next_connection="交 AG3 审查完整论证",
            pending_owners=["AG3"], unrecorded_actions=fact("unknown", "期间动作无法推断"),
            unfinished_requirement_ids=[], closure={"status": "budget_end", "reason": "预算结束不是目标通过"}, active_minutes=5)
        self.assertEqual(result["status"], "committed", result)
        before = self.state()
        reviewed = self.execute("review_whole", event_ref=ref(self.event()), product_ref=anchor(WHOLE_PATH, "B4-whole-proof"),
            requirement_ids=["complete-chain"], intended_use="independent_check")
        self.assertEqual(reviewed["status"], "ready_for_review", reviewed)
        self.assertEqual(reviewed["continuous_product"], WHOLE_TEXT)
        self.assertEqual(reviewed["overall_support"], "not_assessed")
        self.assertEqual(self.state(), before)

    def test_nested_local_work_cannot_expand_the_current_local_scope(self):
        snapshot, artifacts, context = whole_fixture()
        store = self.seed(snapshot, artifacts, name="bounded-nested")
        self.store, self.binding, self.service = store, context, SpecializedTeachingService(store)
        self.initial()
        local = self.local("post", INITIAL_PATH, "B4-initial", "Q。")
        local["premises_supplied"] = fact("known", value=False)
        self.assertEqual(self.execute("enter_local", event_ref=ref(self.event()), local=local)["status"], "committed")
        self.assertEqual(self.help()["status"], "committed")
        self.assertEqual(self.revise()["status"], "committed")
        expanded = self.local("encoding")
        expanded["operations"] = ["connect-P-to-Q", "connect-Q-to-R"]
        before = self.state()
        result = self.execute("enter_local", event_ref=ref(self.event()), local=expanded)
        self.assert_unsaved(result)
        self.assertEqual(self.state(), before)

    def reuse_request(self, judgment, **fields):
        request = {
            "synthetic_only": True, "action": "reuse_evidence", "goal_ref": {"id": "FIX-goal", "revision": 1},
            "requirement_ids": ["infer-Q"], "judgment_refs": [ref(judgment)], "intended_use": "independent_check",
        }
        request.update(fields)
        return request

    def test_reuse_existing_adopted_judgment_can_end_simple_scope_without_new_work(self):
        snapshot, artifacts, judgment = evidence_fixture()
        store = self.seed(snapshot, artifacts, name="reuse-evidence")
        before = self.state(store)
        result = SpecializedTeachingService(store).run(self.reuse_request(judgment))
        self.assertEqual(result["status"], "sufficient_for_declared_use", result)
        self.assertEqual(result["unmet_requirement_ids"], [])
        self.assertEqual(result["reused_judgments"][0]["conditions"], judgment["conditions"])
        self.assertEqual(result["permanent_mastery"], "not_claimed")
        self.assertFalse(result["judgment_created"])
        self.assertFalse(result["new_test_created"])
        self.assertEqual(self.state(store), before)

    def test_reuse_cannot_expand_conditions_requirements_or_unadopted_evidence(self):
        for mode in ("other_requirement", "other_use", "candidate", "counterevidence", "delay_unknown"):
            with self.subTest(mode=mode):
                snapshot, artifacts, judgment = evidence_fixture()
                request = self.reuse_request(judgment)
                if mode == "other_requirement":
                    request["requirement_ids"] = ["infer-Q", "complete-chain"]
                elif mode == "other_use":
                    request["intended_use"] = "unknown-transfer"
                elif mode == "candidate":
                    judgment["adoption"]["status"] = "candidate"
                elif mode == "counterevidence":
                    judgment["counterevidence"] = ["人工相关反证尚未处置"]
                else:
                    objects_by_id(snapshot)["FIX-goal"]["time_requirements"] = fact("known", value={
                        "requirement_ids": ["infer-Q"], "minimum_delay_seconds": 86400, "require_no_contact": True,
                    })
                store = self.seed(snapshot, artifacts, name="reuse-" + mode)
                before = self.state(store)
                result = SpecializedTeachingService(store).run(request)
                self.assertIn(result["status"], {"needs_work", "blocked"}, result)
                self.assertNotEqual(result["status"], "sufficient_for_declared_use")
                self.assertEqual(self.state(store), before)

    def test_candidate_goal_cannot_authorize_evidence_reuse(self):
        snapshot, artifacts, judgment = evidence_fixture()
        objects_by_id(snapshot)["FIX-goal"]["adoption"] = {"status": "candidate"}
        store = self.seed(snapshot, artifacts, name="candidate-goal-reuse")
        result = SpecializedTeachingService(store).run(self.reuse_request(judgment))
        self.assertEqual(result["status"], "not_ready", result)
        self.assertFalse(result["mutated"])

    def test_activity_cannot_opt_out_of_goal_whole_requirements(self):
        snapshot, artifacts, context = whole_fixture(coverage=False)
        objects_by_id(snapshot)["FIX-activity"]["metadata"]["b4"].update(whole_required=False, whole_reference_refs=[], whole_obligations=[])
        store = self.seed(snapshot, artifacts, name="whole-opt-out")
        request = self.request("open", context=context)
        result = SpecializedTeachingService(store).run(request)
        self.assertEqual(result["status"], "not_ready", result)
        self.assertIn("goal_whole_scope_cannot_be_lowered", {p["code"] for p in result["reasons"]})

    def test_twenty_eight_calendar_days_do_not_override_yesterdays_relevant_help(self):
        snapshot, artifacts, judgment = evidence_fixture()
        objects = objects_by_id(snapshot)
        goal, event = objects["FIX-goal"], objects["FIX-event"]
        goal["time_requirements"] = fact("known", value={
            "requirement_ids": ["infer-Q"], "minimum_delay_seconds": 604800, "require_no_contact": True,
        })
        event["occurred_at"] = fact("known", value="2026-10-03T09:00:00+08:00")
        event["contact_history"] = fact("known", value={
            "last_relevant_at": "2026-09-05T09:00:00+08:00",
            "intervening_contact": fact("known", value=False),
        })
        response = copy.deepcopy(event["timeline"][0])
        response.update(sequence=2, time=fact("known", value="2026-10-03T09:00:00+08:00"))
        response["artifact_ref"] = copy.deepcopy(event["original_response"])
        prior = {
            "kind": "help", "sequence": 1, "visibility": "displayed", "content": "人工前一天重新展示相关前提",
            "target_operations": ["connect-P-to-Q"], "substituted_operations": [],
            "time": fact("known", value="2026-10-02T09:00:00+08:00"),
        }
        event["timeline"] = [prior, response]
        event["revisions"] = []
        judgment["conditions"]["response_points"] = [{"event_ref": ref(event), "sequence": 2}]
        store = self.seed(snapshot, artifacts, name="calendar-is-not-contact")
        before = self.state(store)
        result = SpecializedTeachingService(store).run(self.reuse_request(judgment))
        self.assertEqual(result["status"], "needs_work", result)
        self.assertEqual(result["unmet_requirement_ids"], ["infer-Q"])
        self.assertEqual(self.state(store), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
