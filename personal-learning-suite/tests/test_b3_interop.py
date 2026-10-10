"""Public B3c -> B3b -> B3a handoffs on one isolated synthetic store."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from runtime.b3_semantics import known_bool, task_checks, timestamp
from runtime.learning_assessment import AssessmentService
from runtime.learning_store import LearningStore
from runtime.learning_strategies import StrategyCatalog, StrategiesService
from runtime.learning_teaching import TeachingService
from test_b3a_assessment import fixture as assessment_fixture
from test_b3b_teaching import (EVENT_ID, GRANT_ID, INITIAL_TEXT, REVISION_PATH,
                              REVISION_TEXT, anchor, fixture as teaching_fixture,
                              initial_request)
from test_b3c_strategies import configured, fact, fixture as strategy_fixture, ref


class B3InteropTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pl-b3-interop-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        self.snapshot, self.artifacts, self.material_context = teaching_fixture()
        activity = next(o for o in self.snapshot["objects"] if o["id"] == "FIX-activity")
        self.parent_task = copy.deepcopy(activity["parent_task"])
        # Positive standalone case has no parent contact. A separate case below
        # retains the real fixture's inherited help and checks its limitation.
        activity["parent_task"] = fact("not_applicable", reason="Artificial standalone activity; no parent task.")
        strategy_snapshot, _ = strategy_fixture()
        self.snapshot["objects"].extend(copy.deepcopy(o) for o in strategy_snapshot["objects"]
                                        if o["id"] in {"FIX-b3c-grant", "FIX-b3c-work"})
        assessment_snapshot, _, self.judgment, self.assessment_context, _, _ = assessment_fixture()
        by_id = {o["id"]: o for o in assessment_snapshot["objects"]}
        for obj in self.snapshot["objects"]:
            if obj["type"] == "AuthorizationGrant":
                obj["validity"] = fact("known", {"active": True})
                if obj["id"] in {"FIX-evidence-grant", "FIX-scoring-grant"}:
                    obj["permitted_conclusions"] = copy.deepcopy(by_id[obj["id"]]["permitted_conclusions"])
        self.store = LearningStore(self.root, "AG1")
        self.assertEqual(self.store.init_workspace()["status"], "committed")
        result = self.store.import_fixture(self.snapshot, self.artifacts)
        self.assertEqual(result["status"], "committed", result)
        self.config, self.strategy_context = configured(StrategyCatalog())
        self.strategies = StrategiesService(self.store)
        self.teaching = TeachingService(LearningStore(self.root, "AG0"))
        self.assessment = AssessmentService(LearningStore(self.root, "AG3"))

    def state(self):
        return self.store.read_context()

    def objects(self):
        return {obj["id"]: obj for obj in self.state()["objects"]}

    def config_request(self, config=None):
        return {"expected_state_revision": self.state()["state_revision"], "operation_id": "FIX-interop-config",
                "changes": [config or self.config], "context": self.strategy_context,
                "authorization_refs": [{"id": "FIX-b3c-grant", "revision": 1}],
                "adoption_refs": [{"id": "FIX-b3c-work", "revision": 1}]}

    def adopt(self):
        result = self.strategies.submit_config(self.config_request())
        self.assertEqual(result["status"], "committed", result)

    def initial(self, complete=True, use_config=True):
        request = initial_request(self.state()["state_revision"], "FIX-interop-initial")
        request["prior_exposures"] = []
        if complete is not None:
            request["timeline_completeness"] = fact("known", complete)
        if use_config:
            request.update(method_config_refs=[ref(self.config)], strategy_context=self.strategy_context)
        result = self.teaching.run(request)
        self.assertEqual(result["status"], "committed", result)
        return result

    def candidate(self, sequence=1, purpose="independent", support="supported"):
        candidate = copy.deepcopy(self.judgment)
        event = self.objects()[EVENT_ID]
        candidate["event_refs"] = [ref(event)]
        candidate["basis_refs"] = [r for r in candidate["basis_refs"] if r.get("id") != "FIX-event"] + [ref(event)]
        candidate["conditions"]["response_points"] = [{"event_ref": ref(event), "sequence": sequence}]
        candidate["conditions"]["purpose"] = purpose
        candidate["support"] = support
        if support == "unknown":
            candidate["eligibility"] = "pending_review"
            candidate["conclusion"] = "local-unknown"
        context = {**self.assessment_context, "material_context": copy.deepcopy(self.material_context)}
        return candidate, context

    def test_adopted_configuration_teaching_evidence_and_judgment_share_one_store(self):
        before_activity = copy.deepcopy(self.objects()["FIX-activity"])
        self.adopt()
        result = self.initial()
        event = self.objects()[EVENT_ID]
        self.assertEqual(event["method_config_refs"], [ref(self.config)])
        self.assertEqual(result["assessment_handoff"]["event_ref"], ref(event))
        self.assertEqual(result["assessment_handoff"]["material_context"], self.material_context)
        self.assertEqual(self.objects()["FIX-activity"], before_activity)
        candidate, context = self.candidate()
        inspected = self.assessment.inspect_judgment(candidate, context)
        self.assertEqual(inspected["status"], "compatible", inspected)
        self.assertEqual(inspected["expected_support"], "supported", inspected)
        saved = self.assessment.submit_assessment({
            "expected_state_revision": self.state()["state_revision"], "operation_id": "FIX-interop-judgment",
            "changes": [candidate], "artifacts": {}, "authorization_refs": [candidate["authorization_ref"]],
            "adoption_refs": [candidate["authorization_ref"]], "contexts": {candidate["id"]: context}})
        self.assertEqual(saved["status"], "committed", saved)
        reopened = LearningStore(self.root, "AG3")
        self.assertEqual(reopened.read_refs([ref(event)], "assessment")["objects"][0], event)
        self.assertEqual(reopened.check_integrity()["status"], "ok")

    def test_empty_report_does_not_claim_complete_exposure(self):
        self.initial(complete=None, use_config=False)
        self.assertEqual(self.objects()[EVENT_ID]["timeline_completeness"]["status"], "unknown")
        candidate, context = self.candidate(support="unknown")
        inspected = self.assessment.inspect_judgment(candidate, context)
        self.assertEqual(inspected["status"], "limited", inspected)
        self.assertEqual(inspected["expected_support"], "unknown")
        self.assertTrue(inspected["submission_ready"], inspected)

    def test_same_event_initial_and_helped_revision_keep_distinct_support(self):
        self.adopt()
        self.initial()
        base = {"synthetic_only": True, "activity_ref": self.material_context["activity_ref"],
                "context": self.material_context, "authorization_refs": [{"id": GRANT_ID, "revision": 1}]}
        help_request = {**base, "action": "record_help", "event_ref": ref(self.objects()[EVENT_ID]),
                        "expected_state_revision": self.state()["state_revision"], "operation_id": "FIX-interop-help",
                        "help": {"content": "前提 P 使 P→Q 可推出 Q。", "visibility": "displayed",
                                 "target_operations": ["connect-P-to-Q"], "substituted_operations": ["connect-P-to-Q"],
                                 "time": fact("unknown")}}
        self.assertEqual(self.teaching.run(help_request)["status"], "committed")
        revised = self.teaching.run({**base, "action": "record_revision", "event_ref": ref(self.objects()[EVENT_ID]),
                                    "expected_state_revision": self.state()["state_revision"], "operation_id": "FIX-interop-revision",
                                    "revision_response": anchor(REVISION_PATH, "B3b-revision"),
                                    "artifacts": {REVISION_PATH: REVISION_TEXT},
                                    "revision": {"content": "P 成立且 P→Q，所以 Q。", "visibility": "displayed",
                                                 "target_operations": ["connect-P-to-Q"], "substituted_operations": [], "time": fact("unknown")}})
        self.assertEqual(revised["status"], "committed", revised)
        initial = self.assessment.inspect_judgment(*self.candidate())
        assisted = self.assessment.inspect_judgment(*self.candidate(3, "assisted"))
        independent = self.assessment.inspect_judgment(*self.candidate(3, support="unknown"))
        self.assertEqual(initial["status"], "compatible", initial)
        self.assertEqual(assisted["status"], "compatible", assisted)
        self.assertEqual(independent["expected_support"], "unknown", independent)
        self.assertEqual(initial["samples"], assisted["samples"])
        self.assertEqual(self.objects()[EVENT_ID]["method_config_refs"], [ref(self.config)])
        self.assertEqual(revised["assessment_handoff"]["response_point"]["sequence"], 3)

    def test_candidate_method_cannot_be_used_by_teaching(self):
        config = copy.deepcopy(self.config)
        config["adoption"]["status"] = "candidate"
        config["adoption"]["basis_refs"] = []
        bootstrap = self.store.commit(self.state()["state_revision"], "FIX-interop-candidate", [config],
                                      authorization_refs=[{"id": "FIX-b3c-grant", "revision": 1}],
                                      adoption_refs=[{"id": "FIX-b3c-work", "revision": 1}])
        self.assertEqual(bootstrap["status"], "committed", bootstrap)
        result = self.teaching.run({"synthetic_only": True, "action": "open", "activity_ref": self.material_context["activity_ref"],
                                    "context": self.material_context, "method_config_refs": [ref(config)], "strategy_context": self.strategy_context})
        self.assertIn(result["status"], {"blocked", "not_ready"}, result)
        self.assertNotIn(EVENT_ID, self.objects())

    def test_strategy_restriction_blocks_new_execution_but_preserves_assessment_history(self):
        self.adopt()
        self.initial()
        control = LearningStore(self.root, "USER")
        receipt = control.restrict(self.state()["state_revision"], "FIX-interop-restrict", [self.config["id"]],
                                   "人工配置待复核", ["strategy_configuration"])
        self.assertEqual(receipt["status"], "committed", receipt)
        result = self.teaching.run({"synthetic_only": True, "action": "resume", "activity_ref": self.material_context["activity_ref"],
                                    "context": self.material_context, "event_ref": ref(self.objects()[EVENT_ID])})
        self.assertEqual(result["status"], "blocked", result)
        inspected = self.assessment.inspect_judgment(*self.candidate())
        self.assertEqual(inspected["status"], "compatible", inspected)

    def test_later_config_dependencies_do_not_change_old_exact_evidence(self):
        self.adopt()
        self.initial()
        event = self.objects()[EVENT_ID]
        updated = copy.deepcopy(self.config)
        updated.update(revision=2, previous_config=ref(self.config))
        updated["basis_refs"].append({"id": "FIX-evidence-grant", "revision": 1})
        request = self.config_request(updated)
        request["operation_id"] = "FIX-interop-config-two"
        self.assertEqual(self.strategies.submit_config(request)["status"], "committed")
        control = LearningStore(self.root, "USER")
        self.assertEqual(control.restrict(self.state()["state_revision"], "FIX-interop-new-dependency", ["FIX-evidence-grant"],
                                         "只限制新版配置新依赖", ["teaching_execution"])["status"], "committed")
        self.assertEqual(self.store.validate_refs([ref(event)], "teaching_execution")["status"], "ok")
        self.assertEqual(self.store.validate_refs([ref(updated)], "teaching_execution")["status"], "rejected")
        self.assertEqual(self.store.validate_refs([event["original_response"]], "teaching_execution")["status"], "ok")
        self.assertEqual(self.store.read_refs([ref(self.config)], "read")["objects"][0], self.config)

    def test_configuration_requires_exact_material_binding_not_only_supported_labels(self):
        self.assertEqual(self.strategies.inspect_config(self.config, self.strategy_context)["status"], "compatible")
        context = copy.deepcopy(self.strategy_context)
        context["material_context"]["conditions"] = ["其他未经复核的材料条件"]
        result = self.strategies.inspect_config(self.config, context)
        self.assertEqual(result["status"], "blocked", result)
        missing = copy.deepcopy(self.strategy_context)
        del missing["material_context"]
        self.assertEqual(self.strategies.inspect_config(self.config, missing)["status"], "blocked")

    def test_modern_inactive_grant_cannot_adopt_method_through_store(self):
        snapshot = copy.deepcopy(self.snapshot)
        next(o for o in snapshot["objects"] if o["id"] == "FIX-b3c-grant")["validity"] = fact("known", {"active": False})
        self.store = LearningStore(Path(self.temp.name) / "inactive", "AG1")
        self.assertEqual(self.store.init_workspace()["status"], "committed")
        self.assertEqual(self.store.import_fixture(snapshot, self.artifacts)["status"], "committed")
        self.strategies = StrategiesService(self.store)
        request = self.config_request()
        result = self.strategies.submit_config(request)
        self.assertEqual(result["status"], "rejected", result)
        self.assertNotIn(self.config["id"], self.objects())

    def test_parent_help_retained_by_teaching_limits_child_independent_evidence(self):
        snapshot = copy.deepcopy(self.snapshot)
        next(o for o in snapshot["objects"] if o["id"] == "FIX-activity")["parent_task"] = copy.deepcopy(self.parent_task)
        self.root = Path(self.temp.name) / "parent-help"
        self.store = LearningStore(self.root, "AG1")
        self.assertEqual(self.store.init_workspace()["status"], "committed")
        self.assertEqual(self.store.import_fixture(snapshot, self.artifacts)["status"], "committed")
        self.strategies = StrategiesService(self.store)
        self.teaching = TeachingService(LearningStore(self.root, "AG0"))
        self.assessment = AssessmentService(LearningStore(self.root, "AG3"))
        self.adopt()
        self.initial()
        result = self.assessment.inspect_judgment(*self.candidate(support="unknown"))
        self.assertEqual(result["expected_support"], "unknown", result)
        inherited = result["operation_conditions"][0]["displayed_substitution_refs"]
        self.assertTrue(any(item["event_ref"]["id"] == "FIX-event" for item in inherited), result)


class B3DeclarationTests(unittest.TestCase):
    def test_legacy_boolean_qualification_is_read_only_and_conflicts_do_not_disappear(self):
        activity = {"learner_operations": ["op"], "task_qualification": fact("known", {
            "target_operation_call": fact("known", True), "prerequisite_burden": fact("known", True),
            "not_substituted": fact("known", True), "reference_scorable": fact("known", True), "evidence_conditions": fact("known", True)})}
        original = copy.deepcopy(activity)
        checks = task_checks(activity)
        self.assertEqual(checks["target_operations"], ["op"])
        self.assertTrue(known_bool(checks["prerequisite_fit"]))
        self.assertEqual(activity, original)
        activity["task_qualification"]["value"]["prerequisite_fit"] = fact("known", False)
        self.assertTrue(task_checks(activity)["conflicts"])

    def test_timestamps_share_one_explicit_timezone_representation(self):
        raw = "2026-10-03T12:00:00+08:00"
        self.assertEqual(timestamp(fact("known", raw)), timestamp(fact("known", {"timestamp": raw})))
        self.assertIsNone(timestamp(fact("known", "2026-10-03T12:00:00")))
        self.assertIsNone(timestamp(fact("unknown")))


if __name__ == "__main__":
    unittest.main()
