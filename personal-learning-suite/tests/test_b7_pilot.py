"""Independent B7 checks using artificial canonical objects and original artifacts.

Real-mode probes are in-memory fabricated boundary cases, not personal facts.
No test creates a real fixture, personal learning store or efficacy result.
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
from runtime.pilot_b7 import PilotService, VERSION
from runtime.personal_learning import PersonalLearningEntry
from test_b5_entry import fixture as entry_fixture


def fact(status, value=None, reason="Artificial boundary declaration only."):
    return {"status": status, "value": value} if status == "known" else {"status": status, "reason": reason}


def ref(obj):
    return {"id": obj["id"], "revision": obj["revision"]}


def objects_by_id(request):
    return {obj["id"]: obj for obj in request["objects"]}


def template():
    return json.loads((ROOT / "templates/b7-pilot-input.json").read_text(encoding="utf-8-sig"))


def fixture():
    """Reuse B5/B1 canonical objects entirely in memory; never mutate old fixtures."""
    snapshot, artifacts, _context, judgment, _assessment = entry_fixture()
    request = template()
    request.update(data_kind="synthetic", objects=copy.deepcopy(snapshot["objects"]),
        artifacts=copy.deepcopy(artifacts), instance_ref={"id": "FIX-instance", "revision": 1},
        current_goal_refs=[{"id": "FIX-goal", "revision": 1, "locator": "requirements/infer-Q"}],
        budget_ref={"id": "FIX-budget", "revision": 1},
        controls={"known": True, "deleted_ids": [], "paused_ids": [], "restrictions": []},
        followup={"status": "not_required", "goal_refs": [], "purpose": "Finite artificial current-use boundary only."})
    judgment["adoption"]["status"] = "adopted"
    request["objects"].append(copy.deepcopy(judgment))
    objects = objects_by_id(request)
    instance = objects["FIX-instance"]
    instance["actor_bindings"] = fact("known", {role: "Artificial single responsible actor" for role in ("AG0", "AG1", "AG2", "AG3")})
    instance["record_root"] = fact("known", str(Path(tempfile.gettempdir()) / "pl-b7-artificial-record-root-not-created"))
    instance["record_control_scope"] = fact("known", ["records", "originals", "reports"])
    for identifier in ("FIX-requirement-source", "FIX-content-source"):
        objects[identifier]["verification"] = fact("known", {"recorded_status": "supported_for_fixture",
            "method": "Artificial reviewer declaration", "scope": "Artificial finite criterion only"})
    budget = objects["FIX-budget"]
    budget["allocation_scope"].append("FIX-goal")
    for axis in ("blocked_wait", "system_effort"):
        budget[axis] = fact("known", {"minutes": 1, "measurement": "synthetic_limit"})
    budget["fees"] = fact("known", {"amount": 1, "unit": "USD", "measurement": "synthetic_limit"})
    return request


def validation(request, layer, claim=None):
    """Build a full canonical ValidationDecision, including its artificial original."""
    objects = objects_by_id(request)
    review = copy.deepcopy(objects["FIX-validation"])
    identifier = "FIX-b7-review-" + layer
    artifact = "b7-review-" + layer + ".md"
    review.update(id=identifier, validation_layer=layer, case_id="B7-artificial-" + layer,
        host="Artificial in-memory declaration", versions={"protocol": "pl-contracts/0.1.0", "pilot": VERSION},
        executor="Artificial executor", checker="Artificial reviewer", status="passed",
        raw_output_ref={"path": artifact, "locator": identifier, "revision": 1, "origin": "synthetic_fixture"},
        cost={axis: fact("unknown") for axis in ("user_active_time", "blocked_wait", "system_effort", "fees")},
        decision="Artificial software boundary review only", limitations=["Not a real V1–V4 result."])
    pilot = {"goal_refs": [ref(objects["FIX-goal"])],
        "event_refs": [ref(objects["FIX-event"])] if layer in {"V2", "V3"} else [],
        "judgment_refs": [ref(objects["FIX-b5-judgment"])] if layer == "V3" else [],
        "claim": claim or {"V1": "configuration", "V2": "software_behavior", "V3": "current_support", "V4": "collaboration_gain"}[layer]}
    review["metadata"] = {"pilot": pilot}
    review["basis_refs"] = pilot["goal_refs"] + pilot["event_refs"] + pilot["judgment_refs"]
    request["objects"].append(review)
    request["artifacts"][artifact] = "# " + identifier + "\nPRIVATE-B7-VALIDATION-ORIGINAL\n"
    request["validation_refs"].append(ref(review))
    return review


def cost_axes(amount=1):
    return {axis: fact("known", {"amount": amount, "unit": "minutes" if axis != "fees" else "USD"})
        for axis in ("user_active_time", "blocked_wait", "system_effort", "fees")}


def artificial_real_declarations():
    """Fabricated non-fixture labels used only in memory to probe real-mode gates.

    These declared bindings, origins and controls are not personal facts. No caller
    may persist this result as a real dataset or treat it as authenticated input.
    """
    request = fixture()

    def relabel(value):
        if isinstance(value, str):
            return (value.replace("FIX-", "DECL-").replace("synthetic_fixture", "supplied_original")
                .replace("supported_for_fixture", "supported").replace("verified_for_fixture", "host_verified")
                .replace("synthetic", "artificial_declaration"))
        if isinstance(value, list):
            return [relabel(item) for item in value]
        if isinstance(value, dict):
            return {key: relabel(item) for key, item in value.items()}
        return value

    request = relabel(request)
    request["data_kind"] = "real"
    return request


class B7PilotTests(unittest.TestCase):
    def setUp(self):
        self.service = PilotService()

    def codes(self, result):
        return {reason.get("code") for reason in result.get("reasons", [])}

    def assert_readonly(self, result):
        self.assertFalse(result.get("mutated", False))
        self.assertFalse(result.get("can_start_automated", False))
        self.assertNotEqual(result.get("live_execution_status"), "enabled")

    def test_unconfigured_needs_input_without_constructing_store(self):
        with patch("runtime.personal_learning.LearningStore", side_effect=AssertionError("No pilot store may be constructed")):
            result = PersonalLearningEntry.inspect_pilot(template())
        self.assertIn(result["status"], {"needs_input", "not_ready", "unconfigured"})
        self.assertTrue(result.get("needed_inputs") or result.get("reasons"))
        self.assert_readonly(result)

    def test_preflight_does_not_mutate_supplied_objects_or_artifacts(self):
        request = fixture()
        before = copy.deepcopy(request)
        result = self.service.preflight(request)
        self.assertEqual(request, before)
        self.assertEqual(result["status"], "prepared", result)
        self.assertTrue(result["inputs_ready"], result)
        self.assert_readonly(result)

    def test_real_cannot_accept_fixture_ids_or_synthetic_provenance(self):
        request = fixture()
        request["data_kind"] = "real"
        result = self.service.preflight(request)
        self.assertEqual(result["status"], "rejected")
        self.assertFalse(result["inputs_ready"])
        self.assertTrue(result.get("reasons") or result.get("needed_inputs"))
        self.assertEqual(request["objects"][0]["id"], "FIX-instance")
        self.assert_readonly(result)

    def test_unmarked_artificial_real_declarations_do_not_authenticate_or_execute(self):
        request = artificial_real_declarations()
        result = self.service.preflight(request)
        self.assertEqual(result["status"], "prepared", result)
        self.assertTrue(result["inputs_ready"])
        self.assertIn("source_authenticity_not_proven", result["limits"])
        self.assertIn("host_identity_not_authenticated", result["limits"])
        self.assert_readonly(result)

    def test_real_mode_refuses_explicit_synthetic_snapshot_marker(self):
        request = artificial_real_declarations()
        request["synthetic_only"] = True
        result = self.service.preflight(request)
        self.assertEqual(result["status"], "rejected", result)
        self.assertFalse(result["inputs_ready"])

    def test_absent_v1_v4_are_separate_and_not_real_effect(self):
        result = self.service.report(template())
        self.assertEqual(set(result["reviews"]), {"V1", "V2", "V3", "V4"})
        for layer in result["reviews"].values():
            self.assertNotIn(layer["reported_status"], {"passed", "supported", "effect_proven"})
        self.assert_readonly(result)

    def test_malformed_payloads_fail_conservatively_without_body_echo(self):
        marker = "PRIVATE-B7-BODY-DO-NOT-ECHO"
        requests = [None, [], marker, 7, {"pilot_version": VERSION, "data_kind": marker},
            dict(template(), objects=marker), dict(template(), objects=[marker]),
            dict(template(), controls=marker), dict(template(), current_goal_refs=[marker]),
            dict(template(), artifacts={"body.md": marker}, instance_ref={"id": marker, "revision": "bad"})]
        for request in requests:
            for action in ("preflight", "report"):
                with self.subTest(action=action, shape=type(request).__name__):
                    result = getattr(self.service, action)(request)
                    self.assertIsInstance(result, dict)
                    self.assertFalse(result.get("inputs_ready", False))
                    self.assertNotIn(marker, json.dumps(result, ensure_ascii=False))
                    self.assert_readonly(result)

    def test_missing_version_and_unknown_controls_cannot_be_inputs_ready(self):
        for field, value in (("pilot_version", "pl-pilot/future"), ("controls", {"known": False}),
                ("budget_ref", None), ("instance_ref", None), ("current_goal_refs", [])):
            request = fixture()
            request[field] = value
            with self.subTest(field=field):
                result = self.service.preflight(request)
                self.assertFalse(result["inputs_ready"])
                self.assert_readonly(result)

    def test_missing_personal_configuration_and_external_root_need_input(self):
        for field, value in (("actor_bindings", fact("unknown")), ("record_root", fact("unknown")),
                ("record_root", fact("known", "relative-personal-root")),
                ("record_root", fact("known", str(ROOT / "personal-records"))),
                ("record_control_scope", fact("unknown")), ("purpose", fact("unknown")),
                ("user_constraints", fact("unknown"))):
            request = fixture()
            objects_by_id(request)["FIX-instance"][field] = value
            with self.subTest(field=field, value=value):
                result = self.service.preflight(request)
                self.assertFalse(result["inputs_ready"], result)
                self.assertTrue(result["reasons"])

    def test_unverified_current_reference_and_incomplete_whole_goal_keep_unknown(self):
        request = fixture()
        objects = objects_by_id(request)
        objects["FIX-content-source"]["verification"] = fact("unknown")
        result = self.service.preflight(request)
        self.assertFalse(result["inputs_ready"])
        self.assertIn("current_reliable_source_required", self.codes(result))
        request = fixture()
        requirement = objects_by_id(request)["FIX-goal"]["requirements"][0]
        requirement["teaching_scope"] = {"whole_required": True, "whole_obligations": ["Complete parent chain"]}
        result = self.service.preflight(request)
        self.assertFalse(result["inputs_ready"])
        self.assertIn("whole_goal_reference_or_scope_missing", self.codes(result))

    def test_nonexistent_current_requirement_locator_cannot_prepare_scope(self):
        request = fixture()
        request["current_goal_refs"][0]["locator"] = "requirements/does-not-exist"
        result = self.service.preflight(request)
        self.assertFalse(result["inputs_ready"], result)
        self.assertNotEqual(result["status"], "prepared", result)

    def test_whole_coverage_label_cannot_override_pending_content_review(self):
        request = fixture()
        objects = objects_by_id(request)
        goal = objects["FIX-goal"]
        requirement = goal["requirements"][0]
        obligations = ["Complete global proof"]
        requirement["teaching_scope"] = {"whole_required": True, "whole_obligations": obligations}
        content = objects["FIX-material"]["verification"]["content"]
        content["status"] = "pending_review"
        content["whole_coverage"] = {"status": "supported", "goal_refs": [ref(goal)],
            "criterion_refs": [dict(ref(goal), locator="requirements/" + requirement["requirement_id"])],
            "target_operations": copy.deepcopy(requirement["key_operations"]),
            "obligations": obligations, "anchor_refs": copy.deepcopy(content["anchor_refs"])}
        result = self.service.preflight(request)
        self.assertFalse(result["inputs_ready"], result)
        self.assertNotEqual(result["status"], "prepared", result)

    def test_canonical_v1_v2_v3_reviews_remain_fictional_and_separate(self):
        request = fixture()
        for layer in ("V1", "V2", "V3"):
            validation(request, layer)
        result = self.service.report(request)
        self.assertEqual(set(result["reviews"]), {"V1", "V2", "V3", "V4"})
        for layer in ("V1", "V2", "V3"):
            self.assertEqual(result["reviews"][layer]["reported_status"], "passed", result)
        self.assertEqual(result["reviews"]["V4"]["reported_status"], "not_executed")
        self.assertEqual(result["real_results"], {layer: "not_executed" for layer in ("V1", "V2", "V3", "V4")})

    def test_v1_v2_require_original_output_and_original_event(self):
        for layer, remove in (("V1", "raw"), ("V2", "raw"), ("V2", "event"), ("V3", "event")):
            request = fixture()
            review = validation(request, layer)
            if remove == "raw":
                request["artifacts"].pop(review["raw_output_ref"]["path"])
            else:
                path = objects_by_id(request)["FIX-event"]["original_response"]["path"]
                request["artifacts"].pop(path)
            with self.subTest(layer=layer, remove=remove):
                result = self.service.report(request)
                self.assertEqual(result["reviews"][layer]["reported_status"], "unknown", result)

    def test_current_controls_deletion_pause_and_restriction_override_old_pass(self):
        for control in ("delete", "pause", "restrict", "unknown"):
            request = fixture()
            validation(request, "V3")
            if control == "delete":
                request["controls"]["deleted_ids"] = ["FIX-event"]
            elif control == "pause":
                request["controls"]["paused_ids"] = ["FIX-event"]
            elif control == "restrict":
                request["controls"]["restrictions"] = [{"scope_id": "FIX-event", "intended_uses": ["V3"]}]
            else:
                request["controls"]["known"] = False
            with self.subTest(control=control):
                result = self.service.report(request)
                self.assertEqual(result["reviews"]["V3"]["reported_status"], "unknown", result)
                for assessment in result["reviews"]["V3"]["assessments"]:
                    self.assertFalse(assessment.get("judgments"), "Blocked dependencies cannot keep old support in a derived view")

    def test_deleted_event_does_not_wipe_independent_reliable_v1_configuration(self):
        request = fixture()
        validation(request, "V1")
        validation(request, "V3")
        request["controls"]["deleted_ids"] = ["FIX-event"]
        result = self.service.report(request)
        self.assertEqual(result["reviews"]["V1"]["reported_status"], "passed", result)
        self.assertEqual(result["reviews"]["V3"]["reported_status"], "unknown", result)

    def test_missing_dependency_and_stale_goal_cannot_continue_old_pass(self):
        for variant in ("missing", "stale"):
            request = fixture()
            validation(request, "V1")
            if variant == "missing":
                request["objects"] = [obj for obj in request["objects"] if obj["id"] != "FIX-content-source"]
            else:
                new = copy.deepcopy(objects_by_id(request)["FIX-goal"])
                new["revision"] = 2
                request["objects"].append(new)
            result = self.service.report(request)
            self.assertEqual(result["reviews"]["V1"]["reported_status"], "unknown", result)

    def test_v3_same_sample_revision_and_missing_baseline_do_not_prove_gain(self):
        for same_sample in (False, True):
            request = fixture()
            review = validation(request, "V3", "learning_gain")
            if same_sample:
                review["metadata"]["pilot"].update(baseline_event_refs=[{"id": "FIX-event", "revision": 1}],
                    baseline_comparable=fact("known", True))
            result = self.service.report(request)
            assessment = result["reviews"]["V3"]
            self.assertEqual(assessment["reported_status"], "unknown", result)
            codes = self.codes(assessment)
            self.assertIn("same_sample_cannot_establish_gain" if same_sample else "comparable_baseline_required", codes)

    def test_v3_unknown_baseline_is_not_gain_from_supported_current_answer(self):
        request = fixture()
        objects = objects_by_id(request)
        baseline = copy.deepcopy(objects["FIX-event"])
        baseline.update(id="FIX-b7-baseline", independent_sample_id="FIX-b7-baseline-sample")
        request["objects"].append(baseline)
        baseline_judgment = copy.deepcopy(objects["FIX-b5-judgment"])
        baseline_judgment.update(id="FIX-b7-baseline-judgment", event_refs=[ref(baseline)],
            support="unknown", eligibility="pending_review", conclusion="local-unknown")
        baseline_judgment["conditions"]["response_points"] = [{"event_ref": ref(baseline), "sequence": 1}]
        request["objects"].append(baseline_judgment)
        review = validation(request, "V3", "learning_gain")
        review["metadata"]["pilot"].update(baseline_event_refs=[ref(baseline)],
            baseline_judgment_refs=[ref(baseline_judgment)], baseline_comparable=fact("known", True))
        result = self.service.report(request)
        self.assertEqual(result["reviews"]["V3"]["reported_status"], "unknown", result)

    def test_v3_identical_original_with_new_event_and_sample_cannot_prove_gain(self):
        request = fixture()
        objects = objects_by_id(request)
        baseline = copy.deepcopy(objects["FIX-event"])
        baseline.update(id="FIX-b7-relabelled-baseline", independent_sample_id="FIX-b7-relabelled-baseline-sample")
        self.assertEqual(baseline["original_response"], objects["FIX-event"]["original_response"])
        request["objects"].append(baseline)
        judgment = copy.deepcopy(objects["FIX-b5-judgment"])
        judgment.update(id="FIX-b7-relabelled-baseline-judgment", event_refs=[ref(baseline)],
            support="observed_not_met", eligibility="usable", conclusion="local-not-met")
        judgment["basis_refs"] = [ref(baseline) if item["id"] == "FIX-event" else item for item in judgment["basis_refs"]]
        judgment["conditions"]["response_points"] = [{"event_ref": ref(baseline), "sequence": 1}]
        judgment["conditions"]["operation_findings"][0]["support"] = "observed_not_met"
        request["objects"].append(judgment)
        review = validation(request, "V3", "learning_gain")
        review["metadata"]["pilot"].update(baseline_event_refs=[ref(baseline)],
            baseline_judgment_refs=[ref(judgment)], baseline_comparable=fact("known", True))
        result = self.service.report(request)
        self.assertEqual(result["reviews"]["V3"]["reported_status"], "unknown", result)

    def test_required_retention_delay_and_contact_unknown_cannot_support(self):
        for condition, expected in (("time_unknown", "retention_selected_time_unknown"),
                ("contact_unknown", "relevant_contact_unknown"), ("too_soon", "required_delay_not_observed")):
            request = fixture()
            objects = objects_by_id(request)
            event = objects["FIX-event"]
            baseline = copy.deepcopy(event)
            baseline.update(id="FIX-b7-retention-baseline", independent_sample_id="FIX-b7-retention-start")
            request["objects"].append(baseline)
            objects["FIX-goal"]["time_requirements"] = fact("known", {"minimum_delay_seconds": 86400,
                "requirement_ids": ["infer-Q"], "require_no_contact": True})
            if condition != "time_unknown":
                event["timeline"][0]["time"] = fact("known", "2026-10-04T10:00:00+08:00")
            if condition == "too_soon":
                event["contact_history"] = fact("known", {"last_relevant_at": "2026-10-04T09:59:00+08:00",
                    "intervening_contact": fact("known", False)})
            review = validation(request, "V3", "retention")
            review["metadata"]["pilot"].update(baseline_event_refs=[ref(baseline)], baseline_comparable=fact("known", True))
            result = self.service.report(request)
            with self.subTest(condition=condition):
                self.assertEqual(result["reviews"]["V3"]["reported_status"], "unknown", result)
                self.assertIn(expected, self.codes(result["reviews"]["V3"]), result)

    def test_v4_unrequested_comparison_is_not_executed(self):
        request = fixture()
        validation(request, "V4")
        result = self.service.report(request)
        self.assertEqual(result["reviews"]["V4"]["reported_status"], "not_executed", result)

    def test_v4_same_content_second_learning_cannot_establish_increment(self):
        request = fixture()
        objects = objects_by_id(request)
        duplicate_activity = copy.deepcopy(objects["FIX-activity"])
        duplicate_activity["id"] = "FIX-b7-renamed-same-task"
        duplicate_event = copy.deepcopy(objects["FIX-event"])
        duplicate_event.update(id="FIX-b7-repeated-event", independent_sample_id="FIX-b7-repeated-sample",
            activity_ref=ref(duplicate_activity))
        request["objects"].extend([duplicate_activity, duplicate_event])
        review = validation(request, "V4")
        review["metadata"]["pilot"]["comparison"] = {"status": "requested", "question": "Artificial organizational increment?",
            "decision_needed": "Artificial merge-or-keep decision", "planned": fact("known", True),
            "comparable": fact("known", True), "matching_basis": fact("known", ["Artificial declared equal demands and capabilities"]), "arms": [
                {"unit_ref": ref(activity), "event_refs": [ref(event)], "quality": fact("known", {"support": "supported"}),
                    "conditions": fact("known", ["Artificial same task learned twice"]),
                    "prior_learning": fact("known", "unlearned"), "cost": cost_axes()}
                for activity, event in ((objects["FIX-activity"], objects["FIX-event"]), (duplicate_activity, duplicate_event))]}
        result = self.service.report(request)
        self.assertEqual(result["reviews"]["V4"]["reported_status"], "unknown", result)

    def test_v4_same_original_under_different_units_and_samples_is_not_increment(self):
        request = fixture()
        objects = objects_by_id(request)
        activity = copy.deepcopy(objects["FIX-activity"])
        activity.update(id="FIX-b7-distinct-apparent-unit", prompt="Artificial different apparent task surface.")
        event = copy.deepcopy(objects["FIX-event"])
        event.update(id="FIX-b7-relabeled-original-event", independent_sample_id="FIX-b7-relabeled-original-sample",
            activity_ref=ref(activity), basis_refs=[ref(activity)])
        self.assertEqual(event["original_response"], objects["FIX-event"]["original_response"])
        request["objects"].extend([activity, event])
        review = validation(request, "V4")
        review["metadata"]["pilot"]["comparison"] = {"status": "requested", "question": "Artificial organizational increment?",
            "decision_needed": "Artificial bounded keep-or-merge decision", "planned": fact("known", True),
            "comparable": fact("known", True), "matching_basis": fact("known", ["Artificial equal task demands"]),
            "arms": [{"unit_ref": ref(unit), "event_refs": [ref(sample)], "quality": fact("known", {"support": "supported"}),
                "conditions": fact("known", ["Artificial declared equivalent conditions"]),
                "prior_learning": fact("known", "unlearned"), "cost": cost_axes()}
                for unit, sample in ((objects["FIX-activity"], objects["FIX-event"]), (activity, event))]}
        result = self.service.report(request)
        self.assertEqual(result["reviews"]["V4"]["reported_status"], "unknown", result)

    def test_top_level_v4_matching_reference_is_gated_after_deletion_pause_or_restriction(self):
        request = fixture()
        objects = objects_by_id(request)
        matching = copy.deepcopy(objects["FIX-content-source"])
        matching.update(id="FIX-b7-independent-matching-basis", claims=["Artificial task matching basis for the bounded comparison."])
        activity = copy.deepcopy(objects["FIX-activity"])
        activity.update(id="FIX-b7-comparison-second-unit", prompt="Artificial distinct second unit with comparable demand.")
        event = copy.deepcopy(objects["FIX-event"])
        event.update(id="FIX-b7-comparison-second-event", independent_sample_id="FIX-b7-comparison-second-sample",
            activity_ref=ref(activity), basis_refs=[ref(activity)],
            original_response={"path": "b7-second-original.md", "locator": "B7-SECOND-ORIGINAL",
                "revision": 1, "origin": "synthetic_fixture", "start_line": 1, "end_line": 2})
        event["timeline"][0]["content"] = "Artificial original response for the distinct second unit."
        request["artifacts"]["b7-second-original.md"] = "# B7-SECOND-ORIGINAL\nArtificial distinct original response.\n"
        request["objects"].extend([matching, activity, event])
        review = validation(request, "V4")
        self.assertNotIn("comparison", review["metadata"]["pilot"])
        request["comparison"] = {"status": "requested", "question": "Artificial organizational increment?",
            "decision_needed": "Artificial bounded keep-or-merge decision", "planned": fact("known", True),
            "comparable": fact("known", True), "matching_basis_refs": [ref(matching)],
            "arms": [{"unit_ref": ref(unit), "event_refs": [ref(sample)], "quality": fact("known", {"support": "supported"}),
                "conditions": fact("known", ["Artificial declared equivalent conditions"]),
                "prior_learning": fact("known", "unlearned"), "cost": cost_axes()}
                for unit, sample in ((objects["FIX-activity"], objects["FIX-event"]), (activity, event))]}
        positive = self.service.report(request)
        self.assertEqual(positive["reviews"]["V4"]["reported_status"], "passed", positive)
        for control in ("delete", "pause", "restrict"):
            variant = copy.deepcopy(request)
            if control == "delete":
                variant["controls"]["deleted_ids"] = [matching["id"]]
            elif control == "pause":
                variant["controls"]["paused_ids"] = [matching["id"]]
            else:
                variant["controls"]["restrictions"] = [{"scope_id": matching["id"], "intended_uses": ["V4"]}]
            with self.subTest(control=control):
                result = self.service.report(variant)
                self.assertEqual(result["reviews"]["V4"]["reported_status"], "unknown", result)

    def test_unknown_cost_axes_are_not_zero_and_subdivisions_are_not_added(self):
        request = fixture()
        for layer in ("V1", "V2"):
            review = validation(request, layer)
            review["cost"]["user_active_time"] = fact("known", {"minutes": 3, "parts": [{"minutes": 1}, {"minutes": 2}]})
        result = self.service.report(request)
        self.assertFalse(result["costs"]["unknown_is_zero"])
        self.assertEqual(result["costs"]["aggregation"], "not_added")
        self.assertEqual(len(result["costs"]["records"]), 2)
        for record in result["costs"]["records"]:
            self.assertEqual(record["axes"]["fees"], {"status": "unknown"})
            self.assertEqual(record["axes"]["user_active_time"]["amount"], 3)

    def test_metadata_reports_do_not_echo_prompt_original_help_or_teacher_reference(self):
        request = fixture()
        marker = "PRIVATE-B7-INPUT-BODY-NO-ECHO"
        objects = objects_by_id(request)
        objects["FIX-activity"]["prompt"] += marker
        objects["FIX-event"]["timeline"][0]["content"] += marker
        path = objects["FIX-event"]["original_response"]["path"]
        request["artifacts"][path] += "\n" + marker
        for layer in ("V1", "V2", "V3"):
            validation(request, layer)
        before = copy.deepcopy(request)
        for result in (self.service.preflight(request), self.service.report(request)):
            output = json.dumps(result, ensure_ascii=False)
            self.assertNotIn(marker, output)
            self.assertNotIn("PRIVATE-B7-VALIDATION-ORIGINAL", output)
            self.assertNotIn(objects["FIX-activity"]["prompt"], output)
            self.assert_readonly(result)
        self.assertEqual(before, request)

    def test_cli_unconfigured_is_metadata_only_and_creates_no_store(self):
        with tempfile.TemporaryDirectory(prefix="pl-b7-cli-") as directory:
            workspace = Path(directory)
            request = workspace / "input.json"
            request.write_text(json.dumps(template()), encoding="utf-8")
            before = sorted(path.name for path in workspace.iterdir())
            process = subprocess.run([sys.executable, str(ROOT / "src/runtime/personal_learning.py"),
                "pilot", "--action", "preflight", "--request", str(request)],
                cwd=workspace, capture_output=True, text=True, encoding="utf-8")
            self.assertIn(process.returncode, (0, 1, 2))
            result = json.loads(process.stdout)
            self.assert_readonly(result)
            self.assertEqual(sorted(path.name for path in workspace.iterdir()), before)
            self.assertFalse(list(workspace.rglob("*.sqlite3")))
            self.assertNotIn("Traceback", process.stderr)

    def test_cli_invalid_json_does_not_echo_input_or_traceback(self):
        with tempfile.TemporaryDirectory(prefix="pl-b7-malformed-") as directory:
            request = Path(directory) / "invalid.json"
            request.write_text('{"private":"PRIVATE-B7-BAD-JSON",BROKEN}', encoding="utf-8")
            process = subprocess.run([sys.executable, str(ROOT / "src/runtime/personal_learning.py"),
                "pilot", "--request", str(request)], capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(process.returncode, 0)
            result = json.loads(process.stdout)
            self.assertEqual(result["status"], "rejected")
            self.assertNotIn("PRIVATE-B7-BAD-JSON", process.stdout + process.stderr)
            self.assertNotIn("Traceback", process.stderr)

    def test_module_cli_metadata_report_omits_raw_body(self):
        with tempfile.TemporaryDirectory(prefix="pl-b7-module-cli-") as directory:
            request = fixture()
            validation(request, "V2")
            path = Path(directory) / "synthetic-input.json"
            path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
            process = subprocess.run([sys.executable, str(ROOT / "src/runtime/pilot_b7.py"),
                "report", "--request", str(path)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(process.returncode, 0, process.stderr)
            result = json.loads(process.stdout)
            self.assertEqual(result["reviews"]["V2"]["reported_status"], "passed")
            self.assertNotIn("PRIVATE-B7-VALIDATION-ORIGINAL", process.stdout + process.stderr)
            self.assertNotIn("Traceback", process.stderr)
            self.assertFalse(list(Path(directory).rglob("*.sqlite3")))

    def test_demo_is_metadata_only_repeatable_and_does_not_create_store(self):
        with tempfile.TemporaryDirectory(prefix="pl-b7-demo-") as directory:
            path = Path(directory) / "report.json"
            for repeated in (False, True):
                process = subprocess.run([sys.executable, str(ROOT / "scripts/demo_b7.py"),
                    "--report", str(path)], cwd=directory, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(process.returncode, 0, process.stderr)
                report = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(report["synthetic_only"])
                self.assertEqual(report["existing_report"], repeated)
                self.assertFalse(report["store_created"])
                self.assertFalse(report["learning_executed"])
                self.assertFalse(report["replay_existing_workspace"])
                self.assertEqual(report["real_validation"], {layer: "not_executed" for layer in ("V1", "V2", "V3", "V4")})
                self.assertNotIn("PRIVATE-B7-VALIDATION-ORIGINAL", path.read_text(encoding="utf-8") + process.stdout)
                self.assertEqual(sorted(item.name for item in Path(directory).iterdir()), ["report.json"])

    def test_nonpilot_cli_still_requires_workspace(self):
        process = subprocess.run([sys.executable, str(ROOT / "src/runtime/personal_learning.py"), "status"],
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, 2)
        self.assertIn("--workspace", process.stderr)

    def test_checker_rejects_historical_destinations_before_running_tests(self):
        for option, name in (("--report", "b2a-runtime-report.json"), ("--output", "b3b_runtime-output.txt")):
            with tempfile.TemporaryDirectory(prefix="pl-b7-history-") as directory:
                path = Path(directory) / name
                path.write_text("HISTORICAL-KEEP", encoding="utf-8")
                process = subprocess.run([sys.executable, str(ROOT / "scripts/check_b7.py"),
                    option, str(path)], capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(process.returncode, 2)
                self.assertEqual(path.read_text(encoding="utf-8"), "HISTORICAL-KEEP")
                self.assertNotIn("B7 pilot:", process.stdout)


if __name__ == "__main__":
    unittest.main()
