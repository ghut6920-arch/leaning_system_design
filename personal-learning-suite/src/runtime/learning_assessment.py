"""B3a declared evidence checks; professional grading stays with SK04/AG3.

Synthetic-only. This service creates no tasks, samples, needs, or schedules.
LearningStore remains the sole controlled persistence component.
"""
from __future__ import annotations

import argparse
import copy
from fnmatch import fnmatchcase
import json
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.contract_rules import PROTOCOL, load_definition, object_refs
from runtime.b3_semantics import active_grant, task_checks, timestamp
from runtime.learning_store import LearningStore

VERSION = "pl-assessment/0.1.0"
SUPPORT = {"unknown", "supported", "observed_not_met", "mixed_or_conflicting"}
IMPORTANT = {"important_skip", "complex_product", "nonstandard_solution", "scoring_dispute",
             "counterevidence", "deletion_impact", "conclusion_extension"}


def fact(status, reason=None, value=None):
    return {"status": status, "value": value} if status == "known" else {"status": status, "reason": reason}


def ref(record):
    return {"id": record["id"], "revision": record["revision"]}


def issue(code):
    return {"code": code}


def known(value):
    return isinstance(value, dict) and value.get("status") == "known" and "value" in value


def valid_fact(value):
    return isinstance(value, dict) and (known(value) or (
        value.get("status") in {"unknown", "not_required", "not_applicable", "not_executed"}
        and bool(value.get("reason")) and "value" not in value))


def nonempty_strings(value):
    return isinstance(value, list) and bool(value) and all(isinstance(s, str) and s.strip() for s in value)


def valid_ref(value):
    return isinstance(value, dict) and isinstance(value.get("id"), str) and type(value.get("revision")) is int and value["revision"] > 0


def aggregate(values):
    unique = set(values)
    if unique == {"supported"}:
        return "supported"
    if unique == {"observed_not_met"}:
        return "observed_not_met"
    if unique == {"unknown"} or not unique:
        return "unknown"
    return "mixed_or_conflicting"


class AssessmentService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _result(status, codes=(), **extra):
        if status in {"rejected", "blocked"} and "next_action" not in extra:
            extra["next_action"] = "resolve_current_controls" if status == "blocked" else "return_for_review"
        return {"status": status, "reasons": [issue(c) for c in dict.fromkeys(codes)], "mutated": False, **extra}

    def _graph(self, refs, use):
        """Check control before reading exact records, including recorded dependencies."""
        context = self.store.read_context()
        if context.get("status") != "ok" or not context.get("synthetic_only"):
            return None, self._result("blocked", ["workspace_unavailable"])
        index, checked = {}, set()
        pending = list(refs)
        while pending:
            batch = []
            for value in pending:
                if not valid_ref(value):
                    return None, self._result("rejected", ["exact_reference_required"])
                key = value["id"], value["revision"]
                if key not in checked:
                    checked.add(key)
                    batch.append(value)
            if not batch:
                break
            for gate_use in dict.fromkeys(["assessment", use]):
                gate = self.store.validate_refs(batch, gate_use)
                if gate.get("status") != "ok":
                    return None, self._result("blocked", [p["code"] for p in gate.get("reasons", [])] or ["references_unavailable"])
            read = self.store.read_refs(batch, "assessment")
            if read.get("status") != "ok":
                return None, self._result("blocked", ["references_unavailable"])
            if read.get("state_revision") != context["state_revision"]:
                return None, self._result("blocked", ["state_changed_during_review"])
            pending = []
            for obj in read["objects"]:
                index[(obj["id"], obj["revision"])] = obj
                pending.extend(object_refs(obj))
        return (index, context), None

    @staticmethod
    def _shape(record, kind):
        if not isinstance(record, dict) or record.get("type") != kind:
            return ["assessment_contract"]
        definition = load_definition()
        required = definition["base_required"] + definition["objects"][kind]["required"]
        if any(key not in record for key in required) or record.get("schema_version") != PROTOCOL:
            return ["assessment_contract"]
        if not isinstance(record.get("id"), str) or not record["id"].startswith("FIX-") or type(record.get("revision")) is not int or record["revision"] < 1:
            return ["synthetic_result_required"]
        if record.get("owner") not in {"AG0", "AG3"} or not isinstance(record.get("basis_refs"), list):
            return ["assessment_owner"]
        return []

    def _authority(self, record, grant, conclusion, scopes, criteria, budgets):
        if not grant or grant.get("type") != "AuthorizationGrant":
            return ["assessment_authorization_required"]
        if grant.get("binding_status") != "verified_for_fixture" or grant.get("issuer") != grant.get("owner"):
            return ["fixture_binding_required"]
        if grant.get("grantee") != record.get("owner") or record.get("decision_type") not in grant.get("decision_types", []):
            return ["assessment_authority_scope"]
        allowed = grant.get("object_scope")
        if not nonempty_strings(allowed) or not all(any(fnmatchcase(s["id"], pattern) for pattern in allowed) for s in scopes):
            return ["assessment_object_scope"]
        if any(not any(c.get("id") == allowed.get("id") and c.get("revision") == allowed.get("revision")
                       and (not c.get("locator") or c.get("locator") == allowed.get("locator"))
                       for allowed in grant.get("criterion_refs", []) if isinstance(allowed, dict)) for c in criteria):
            return ["assessment_criterion_scope"]
        if not isinstance(conclusion, str) or conclusion not in grant.get("permitted_conclusions", []):
            return ["assessment_conclusion_scope"]
        if not active_grant(grant.get("validity")):
            return ["assessment_grant_inactive_or_unknown"]
        if not budgets or any(b != grant.get("budget_ref") for b in budgets):
            return ["assessment_budget_scope"]
        return []

    def _preauthority(self, record, conclusion, scopes, criteria, use, review_triggers=()):
        """Reject unsupported actors/decisions before loading performance records."""
        grant_ref = record.get("authorization_ref")
        if not valid_ref(grant_ref):
            return self._result("rejected", ["assessment_authorization_required"])
        for gate_use in dict.fromkeys(["assessment", use]):
            gate = self.store.validate_refs([grant_ref], gate_use)
            if gate.get("status") != "ok":
                return self._result("blocked", [p["code"] for p in gate.get("reasons", [])] or ["authorization_unavailable"])
        read = self.store.read_refs([grant_ref], "assessment")
        if read.get("status") != "ok" or len(read.get("objects", [])) != 1:
            return self._result("blocked", ["authorization_unavailable"])
        grant = read["objects"][0]
        errors = self._authority(record, grant, conclusion, scopes, criteria, [grant.get("budget_ref")])
        signals = set(review_triggers) | set(record.get("intended_uses", [])) | {use, conclusion}
        if record.get("owner") == "AG0" and signals.intersection(grant.get("escalation_signals", [])):
            errors.append("grant_escalation_required")
        return self._result("rejected", errors) if errors else None

    @staticmethod
    def _stale_dependencies(index, state):
        latest = {o["id"]: o["revision"] for o in state["objects"]}
        decision_bases = {"GoalSpec", "ActivitySpec", "MaterialUse", "SourceFragment", "AuthorizationGrant", "BudgetEnvelope"}
        return any(o.get("type") in decision_bases and latest.get(o["id"]) != o["revision"] for o in index.values())

    def _artifact(self, artifact, use):
        if not isinstance(artifact, dict) or not all(artifact.get(k) for k in ("path", "locator", "revision", "origin")):
            return ["original_artifact_required"]
        if artifact.get("origin") != "synthetic_fixture" or artifact.get("revision") != 1:
            return ["synthetic_original_required"]
        for gate_use in dict.fromkeys(["assessment", use]):
            gate = self.store.validate_refs([artifact], gate_use)
            if gate.get("status") != "ok":
                return ["original_artifact_unavailable"]
        if "start_line" in artifact or "end_line" in artifact:
            segment = self.store.read_artifact_segment(artifact, artifact.get("start_line"), artifact.get("end_line"), "assessment")
            if segment.get("status") != "ok":
                return ["original_segment_unavailable"]
        return []

    def inspect_judgment(self, judgment, context):
        try:
            return self._inspect_judgment(judgment, context)
        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            return self._result("rejected", ["invalid_assessment_packet"])

    def _inspect_judgment(self, judgment, context):
        errors = self._shape(judgment, "Judgment")
        if errors or not isinstance(context, dict):
            return self._result("rejected", errors or ["assessment_context_required"])
        use = context.get("intended_use")
        triggers = context.get("review_triggers")
        if not isinstance(use, str) or not use or not nonempty_strings(judgment.get("intended_uses")) or use not in judgment["intended_uses"] or not isinstance(triggers, list) or any(not isinstance(t, str) for t in triggers):
            return self._result("rejected", ["assessment_use_context"])
        events = judgment.get("event_refs")
        if not isinstance(events, list) or not events or not all(valid_ref(e) for e in events) or len({(e["id"], e["revision"]) for e in events}) != len(events):
            return self._result("rejected", ["assessment_events_required"])
        for own_use in dict.fromkeys(["assessment", use]):
            own_gate = self.store.validate_refs([ref(judgment)], own_use)
            blockers = [p["code"] for p in own_gate.get("reasons", []) if p["code"] != "missing_reference"]
            if blockers or own_gate.get("status") == "not_saved":
                return self._result("blocked", blockers or ["result_control_unavailable"])
            gate = self.store.validate_refs(list(object_refs(judgment)), own_use)
            if gate.get("status") != "ok":
                return self._result("blocked", [p["code"] for p in gate.get("reasons", [])] or ["references_unavailable"])
        decision = judgment.get("decision_type")
        if (judgment["owner"] == "AG0" and decision != "routine_scoring") or (judgment["owner"] == "AG3" and decision not in {"professional_review", "routine_scoring"}):
            return self._result("rejected", ["important_review_authority"])
        inferred_triggers = IMPORTANT.intersection(judgment["intended_uses"] + [use, judgment.get("conclusion", "")])
        if (triggers or inferred_triggers or judgment.get("counterevidence")) and (judgment["owner"] != "AG3" or decision != "professional_review"):
            return self._result("rejected", ["important_review_required"])
        criterion = dict(judgment.get("goal_ref", {}), locator=f"requirements/{judgment.get('requirement_id', '')}")
        preliminary = self._preauthority(judgment, judgment.get("conclusion"), events, [criterion], use, triggers)
        if preliminary:
            return preliminary
        graph, blocked = self._graph(list(object_refs(judgment)), use)
        if blocked:
            return blocked
        index, state = graph
        if self._stale_dependencies(index, state):
            return self._result("rejected", ["stale_assessment_dependency"])
        resolve = lambda r: index.get((r["id"], r["revision"]))
        goal = resolve(judgment["goal_ref"])
        if not goal or goal.get("type") != "GoalSpec":
            return self._result("rejected", ["assessment_goal_required"])
        requirement = next((r for r in goal["requirements"] if r["requirement_id"] == judgment.get("requirement_id")), None)
        if not requirement or judgment.get("criterion_revision") != requirement.get("criterion_revision"):
            return self._result("rejected", ["assessment_criterion_revision"])
        conditions = judgment.get("conditions")
        if not isinstance(conditions, dict) or conditions.get("purpose") not in {"independent", "assisted"}:
            return self._result("rejected", ["response_conditions_required"])
        purpose = conditions["purpose"]
        points = conditions.get("response_points")
        if not isinstance(points, list) or len(points) != len(events) or any(not isinstance(p, dict) or p.get("event_ref") not in events or type(p.get("sequence")) is not int for p in points) or len({(p["event_ref"]["id"], p["event_ref"]["revision"]) for p in points}) != len(events):
            return self._result("rejected", ["response_points_required"])
        findings = conditions.get("operation_findings")
        operations = requirement.get("key_operations")
        if not nonempty_strings(operations) or not isinstance(findings, list) or len(findings) != len(operations) or {f.get("operation") for f in findings if isinstance(f, dict)} != set(operations) or any(not isinstance(f, dict) or f.get("support") not in SUPPORT or not isinstance(f.get("rationale"), str) or not f["rationale"].strip() for f in findings):
            return self._result("rejected", ["operation_findings_required"])
        if judgment.get("support") not in SUPPORT or judgment.get("eligibility") not in {"usable", "pending_review", "withdrawn"} or not judgment.get("rationale") or not isinstance(judgment.get("unsupported_scope"), list) or not isinstance(judgment.get("counterevidence"), list):
            return self._result("rejected", ["judgment_axes_and_reasons_required"])
        event_objects = [resolve(e) for e in events]
        if any(not e or e.get("type") != "PerformanceEvent" for e in event_objects):
            return self._result("rejected", ["performance_reference_type"])
        activities = [resolve(e["activity_ref"]) for e in event_objects]
        if any(not a or a.get("type") != "ActivitySpec" for a in activities):
            return self._result("rejected", ["activity_reference_type"])
        if any(judgment["goal_ref"] not in e.get("goal_refs", []) for e in event_objects) or any(judgment["goal_ref"] not in a.get("goal_refs", []) for a in activities):
            return self._result("rejected", ["performance_goal_binding"])
        criterion = dict(judgment["goal_ref"], locator=f"requirements/{judgment['requirement_id']}")
        if any(criterion not in a.get("criterion_refs", []) for a in activities):
            return self._result("rejected", ["activity_criterion_binding"])
        grant = resolve(judgment["authorization_ref"])
        authority = self._authority(judgment, grant, judgment.get("conclusion"), events + [e["activity_ref"] for e in event_objects], [criterion], [a.get("budget_ref") for a in activities])
        if authority:
            return self._result("rejected", authority)
        latest = {o["id"]: o["revision"] for o in state["objects"]}
        if any(latest.get(r["id"]) != r["revision"] for r in object_refs(judgment)):
            return self._result("rejected", ["stale_assessment_basis"])
        limits, operation_limits, exposures = [], {op: [] for op in operations}, {op: set() for op in operations}
        exposure_refs = {op: [] for op in operations}
        temporal_limits = []
        unsupported = []
        for event, activity, point in zip(event_objects, activities, [next(p for p in points if p["event_ref"] == er) for er in events]):
            timeline = event.get("timeline")
            if not isinstance(timeline, list) or not timeline or any(not isinstance(t, dict) or type(t.get("sequence")) is not int for t in timeline) or [t["sequence"] for t in timeline] != sorted({t["sequence"] for t in timeline}):
                return self._result("rejected", ["assessment_timeline_invalid"])
            response = next((t for t in timeline if t["sequence"] == point["sequence"] and t.get("kind") in {"initial_response", "revision"}), None)
            if not response:
                return self._result("rejected", ["selected_response_missing"])
            if response["kind"] == "initial_response":
                artifact = event.get("original_response")
            else:
                artifact = next((r for r in event.get("revisions", []) if r.get("sequence") == point["sequence"]), None)
            artifact_errors = self._artifact(artifact, use)
            if artifact_errors:
                return self._result("blocked", artifact_errors)
            value = task_checks(activity)
            if value["conflicts"]:
                return self._result("rejected", value["conflicts"])
            for op in operations:
                if op not in activity.get("learner_operations", []) or op not in value.get("target_operations", []):
                    operation_limits[op].append("target_operation_not_invoked")
                for gate in ("prerequisite_fit", "not_substituted", "reference_scorable", "evidence_conditions"):
                    if not known(value.get(gate)) or value[gate]["value"] is not True:
                        operation_limits[op].append("task_" + gate + "_unconfirmed")
            actual = event.get("actual_resources")
            if not known(actual) or not isinstance(actual["value"], list) or any(not isinstance(item, str) for item in actual["value"]):
                for op in operations:
                    operation_limits[op].append("actual_resources_unknown")
            if purpose == "independent":
                allowed = goal.get("allowed_resources")
                allowed = allowed["value"] if known(allowed) else allowed
                if not isinstance(allowed, list) or any(not isinstance(item, str) for item in allowed):
                    for op in operations:
                        operation_limits[op].append("allowed_resources_unknown")
                elif known(actual) and isinstance(actual["value"], list) and any(item not in allowed for item in actual["value"]):
                    for op in operations:
                        operation_limits[op].append("actual_resources_outside_allowed_scope")
            if purpose == "independent" and (not known(event.get("timeline_completeness")) or event["timeline_completeness"]["value"] is not True):
                for op in operations:
                    operation_limits[op].append("exposure_completeness_unknown")
            contact_records, inheritance_errors, inheritance_incomplete = self._exposure_records(event, point["sequence"], index, include_responses=True)
            exposure_records = [(source_ref, entry) for source_ref, entry in contact_records
                                if entry.get("kind") not in {"initial_response", "revision"}]
            if inheritance_errors:
                return self._result("rejected", inheritance_errors)
            if purpose == "independent" and inheritance_incomplete:
                for op in operations:
                    operation_limits[op].append("inherited_exposure_completeness_unknown")
            for source_ref, exposure in exposure_records:
                visibility = exposure.get("visibility")
                if visibility not in {"planned", "requested", "displayed", "backend_reference", "unknown"}:
                    return self._result("rejected", ["exposure_visibility_required"])
                if visibility == "displayed":
                    substituted = exposure.get("substituted_operations")
                    if not isinstance(substituted, list):
                        return self._result("rejected", ["exposure_operation_scope_required"])
                    for op in set(operations).intersection(substituted):
                        exposure_refs[op].append({"event_ref": source_ref, "sequence": exposure["sequence"]})
                        if source_ref == ref(event):
                            exposures[op].add(exposure["sequence"])
                        if purpose == "independent":
                            operation_limits[op].append("operation_substituted_before_response")
                        else:
                            unsupported.append("Independent execution of " + op)
                elif visibility == "unknown" and purpose == "independent":
                    targets = exposure.get("target_operations")
                    if not isinstance(targets, list):
                        return self._result("rejected", ["exposure_operation_scope_required"])
                    for op in set(operations).intersection(targets or operations):
                        operation_limits[op].append("exposure_visibility_unknown")
            for material_ref in activity.get("material_refs", []):
                material = resolve(material_ref)
                verification = material.get("verification", {}) if material and material.get("type") == "MaterialUse" else {}
                content, use_check = verification.get("content", {}), verification.get("use", {})
                binding = use_check.get("binding", {}) if isinstance(use_check, dict) else {}
                expected_context = context.get("material_context")
                material_use = expected_context.get("intended_use") if isinstance(expected_context, dict) else use
                expected_purpose = context.get("material_purpose", "independent" if purpose == "independent" else None)
                binding_keys = ("activity_ref", "goal_refs", "intended_use", "required_modalities", "conditions", "purpose")
                explicit_binding_valid = (expected_context is None or (
                    isinstance(expected_context, dict) and all(key in expected_context for key in binding_keys)
                    and expected_context.get("activity_ref") == event["activity_ref"]
                    and expected_context.get("goal_refs") == activity.get("goal_refs")
                    and expected_context.get("purpose") in {"teaching", "independent", "comparison"}
                    and nonempty_strings(expected_context.get("conditions"))
                    and isinstance(expected_context.get("required_modalities"), list)
                    and all(binding.get(key) == expected_context[key] for key in binding_keys)))
                if not isinstance(content, dict) or not isinstance(use_check, dict) or content.get("status") != "supported" or use_check.get("status") != "supported" or any(v.get("checked_revision") != material_ref["revision"] for v in (content, use_check)) or binding.get("activity_ref") != event["activity_ref"] or binding.get("goal_refs") != activity.get("goal_refs") or material.get("intended_use") != material_use or binding.get("intended_use") != material_use or not explicit_binding_valid or (purpose == "independent" and binding.get("purpose") != "independent") or (expected_purpose is not None and binding.get("purpose") != expected_purpose) or not nonempty_strings(binding.get("conditions")) or use_check.get("conditions") != binding.get("conditions"):
                    for op in operations:
                        operation_limits[op].append("reference_use_unconfirmed")
            temporal_limits.extend(self._time_limits(goal, judgment["requirement_id"], event, response, operations, contact_records))
        limits.extend(temporal_limits)
        if temporal_limits:
            unsupported.append("Required temporal conditions are unconfirmed; current operation findings remain recorded.")
        analysis = []
        for finding in findings:
            op = finding["operation"]
            codes = list(dict.fromkeys(operation_limits[op]))
            analysis.append({"operation": op, "declared_support": finding["support"],
                             "support": "unknown" if codes else finding["support"],
                             "limits": codes, "displayed_substitution_sequences": sorted(exposures[op]),
                             "displayed_substitution_refs": exposure_refs[op]})
            if codes:
                unsupported.append("Unconfirmed " + purpose + " evidence for " + op)
                limits.extend(codes)
        expected = aggregate([item["support"] for item in analysis])
        if temporal_limits:
            expected = "unknown"
        conflicts = self._conflicts(judgment, state["objects"])
        if conflicts:
            resolution = context.get("review_resolution", {})
            if judgment["owner"] != "AG3" or decision != "professional_review" or not isinstance(resolution, dict) or not resolution.get("rationale") or any(r not in resolution.get("reviewed_refs", []) for r in conflicts):
                limits.append("same_conditions_scoring_conflict")
            else:
                for r in conflicts:
                    gate = self.store.validate_refs([r], "assessment")
                    if gate.get("status") != "ok":
                        return self._result("blocked", ["conflicting_judgment_unavailable"])
        if judgment["support"] != expected:
            errors.append("support_exceeds_declared_conditions")
        if limits and judgment["eligibility"] == "usable":
            errors.append("limited_evidence_requires_pending_review")
        if unsupported and not judgment["unsupported_scope"]:
            errors.append("unsupported_scope_required")
        adoption = judgment.get("adoption")
        if not isinstance(adoption, dict) or adoption.get("status") not in {"candidate", "adopted", "partially_adopted", "recheck", "rejected"}:
            errors.append("judgment_adoption_required")
        return self._result("limited" if errors or limits else "compatible", errors + limits,
                            state_revision=state["state_revision"], expected_support=expected,
                            submission_ready=not errors,
                            operation_conditions=analysis, samples=sorted({e["independent_sample_id"] for e in event_objects}),
                            unsupported_scope=list(dict.fromkeys(unsupported)), conflicting_refs=conflicts,
                            next_action="revise_candidate" if errors else "return_limited_scope" if limits else "no_additional_check",
                            semantic_grading="agent_declared_not_verified", new_tasks=0, new_samples=0)

    @staticmethod
    def _exposure_records(event, response_sequence, index, include_responses=False):
        """Use exact ancestor events as history; summaries never establish facts.

        Sequence numbers are local to each event. Inheritance records the parent
        revision available on entry, so its recorded exposure history is retained
        without creating another response sample or comparing unrelated sequences.
        Earlier learner responses can be requested for temporal contact checks;
        they never become teacher substitution or another scored response point.
        """
        records, errors, incomplete = [], [], False
        visited, active = set(), set()

        def visit(current, own=False):
            nonlocal incomplete
            key = (current["id"], current["revision"])
            if key in active:
                errors.append("inherited_event_cycle")
                return
            if key in visited:
                return
            active.add(key)
            visited.add(key)
            timeline = current.get("timeline")
            if not isinstance(timeline, list) or not timeline or any(not isinstance(entry, dict) or type(entry.get("sequence")) is not int for entry in timeline) or [entry["sequence"] for entry in timeline] != sorted({entry["sequence"] for entry in timeline}):
                errors.append("inherited_event_timeline_invalid")
                active.remove(key)
                return
            if not own and (not known(current.get("timeline_completeness")) or current["timeline_completeness"]["value"] is not True):
                incomplete = True
            records.extend((ref(current), entry) for entry in timeline
                           if (include_responses or entry.get("kind") not in {"initial_response", "revision"})
                           and (not own or entry["sequence"] < response_sequence))
            c0 = current.get("c0", {})
            if not isinstance(c0, dict):
                errors.append("inherited_event_context_invalid")
                active.remove(key)
                return
            inherited = c0.get("inherited_event_refs", [])
            if not isinstance(inherited, list) or not all(valid_ref(parent) for parent in inherited):
                errors.append("inherited_event_refs_invalid")
                active.remove(key)
                return
            if not inherited and c0.get("inherited_help_conditions"):
                incomplete = True
            for parent in inherited:
                record = index.get((parent["id"], parent["revision"]))
                if not record or record.get("type") != "PerformanceEvent":
                    errors.append("inherited_event_reference_type")
                    continue
                visit(record)
            active.remove(key)

        visit(event, own=True)
        return records, list(dict.fromkeys(errors)), incomplete

    @staticmethod
    def _time_limits(goal, requirement_id, event, response, operations=(), contact_records=()):
        requirement = goal.get("time_requirements")
        if isinstance(requirement, dict) and requirement.get("status") in {"not_required", "not_applicable"}:
            return []
        if not known(requirement) or not isinstance(requirement["value"], dict):
            return ["goal_time_requirements_unknown"]
        spec = requirement["value"]
        if not isinstance(spec.get("requirement_ids"), list):
            return ["time_scope_required"]
        if requirement_id not in spec["requirement_ids"]:
            return []
        delay, strict = spec.get("minimum_delay_seconds"), spec.get("require_no_contact")
        if type(delay) not in {int, float} or delay < 0 or type(strict) is not bool:
            return ["time_requirements_invalid"]
        contact = event.get("contact_history")
        if not known(contact) or not isinstance(contact["value"], dict):
            return ["relevant_contact_unknown"]
        happened = timestamp(response.get("time"))
        if happened is None and response.get("kind") == "initial_response":
            happened = timestamp(event.get("occurred_at"))
        last_value = contact["value"].get("last_relevant_at")
        last = timestamp(fact("known", value=last_value) if isinstance(last_value, str) else last_value)
        if happened is None or last is None:
            return ["relevant_times_unknown"]
        codes, displayed_contact = [], False
        for _source_ref, exposure in contact_records:
            learner_practice = exposure.get("kind") in {"initial_response", "revision"}
            if not learner_practice and (exposure.get("kind") not in {"exposure", "help", "feedback"} or exposure.get("visibility") not in {"displayed", "unknown"}):
                continue
            targets = exposure.get("target_operations")
            substituted = [] if learner_practice else exposure.get("substituted_operations")
            if not isinstance(targets, list) or not isinstance(substituted, list):
                codes.append("relevant_contact_scope_unknown")
                continue
            scope = set(targets + substituted)
            if scope and not scope.intersection(operations):
                continue
            if exposure.get("visibility") == "unknown" or (learner_practice and exposure.get("visibility") not in {"displayed", "backend_reference"}):
                codes.append("relevant_contact_unknown")
                continue
            exposure_at = timestamp(exposure.get("time"))
            if exposure_at is None:
                codes.append("relevant_times_unknown")
                continue
            if exposure_at > happened:
                codes.append("relevant_contact_order_invalid")
                continue
            if exposure_at > last:
                displayed_contact = True
                last = exposure_at
        if (happened - last).total_seconds() < delay:
            codes.append("required_delay_not_observed")
        contact_status = contact["value"].get("intervening_contact")
        if strict and (displayed_contact or not known(contact_status) or contact_status["value"] is not False):
            codes.append("required_no_contact_unconfirmed")
        return list(dict.fromkeys(codes))

    @staticmethod
    def _conflicts(judgment, objects):
        conditions = judgment["conditions"]
        refs = []
        for old in objects:
            if old.get("type") != "Judgment" or old.get("adoption", {}).get("status") not in {"adopted", "partially_adopted"}:
                continue
            old_conditions = old.get("conditions")
            if not isinstance(old_conditions, dict):
                continue
            same = all(old.get(k) == judgment.get(k) for k in ("goal_ref", "requirement_id", "criterion_revision", "event_refs")) and old_conditions.get("purpose") == conditions["purpose"] and old_conditions.get("response_points") == conditions["response_points"]
            if same and {old.get("support"), judgment["support"]} == {"supported", "observed_not_met"}:
                refs.append(ref(old))
        return refs

    def inspect_diagnostic(self, note, context):
        try:
            return self._inspect_diagnostic(note, context)
        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            return self._result("rejected", ["invalid_diagnostic_packet"])

    def _inspect_diagnostic(self, note, context):
        errors = self._shape(note, "DiagnosticNote")
        if errors or not isinstance(context, dict) or not isinstance(context.get("intended_use"), str) or not context["intended_use"]:
            return self._result("rejected", errors or ["diagnostic_context_required"])
        for own_use in dict.fromkeys(["assessment", context["intended_use"]]):
            gate = self.store.validate_refs([ref(note)], own_use)
            blockers = [p["code"] for p in gate.get("reasons", []) if p["code"] != "missing_reference"]
            if blockers or gate.get("status") == "not_saved":
                return self._result("blocked", blockers or ["result_control_unavailable"])
            dependencies = self.store.validate_refs(list(object_refs(note)), own_use)
            if dependencies.get("status") != "ok":
                return self._result("blocked", [p["code"] for p in dependencies.get("reasons", [])] or ["references_unavailable"])
        if not isinstance(note.get("observations"), list) or not isinstance(note.get("goal_refs"), list):
            return self._result("rejected", ["limited_diagnosis_scope_required"])
        preliminary = self._preauthority(note, context.get("conclusion"), note["observations"], note["goal_refs"], context["intended_use"])
        if preliminary:
            return preliminary
        graph, blocked = self._graph(list(object_refs(note)), context["intended_use"])
        if blocked:
            return blocked
        index, state = graph
        if self._stale_dependencies(index, state):
            return self._result("rejected", ["stale_assessment_dependency"])
        resolve = lambda r: index.get((r["id"], r["revision"]))
        observations = note.get("observations")
        goals = note.get("goal_refs")
        if note.get("decision_type") != "limited_diagnosis" or not isinstance(observations, list) or not observations or not isinstance(goals, list) or not goals:
            return self._result("rejected", ["limited_diagnosis_scope_required"])
        if any(not resolve(r) or resolve(r).get("type") != "PerformanceEvent" for r in observations) or any(not resolve(r) or resolve(r).get("type") != "GoalSpec" for r in goals):
            return self._result("rejected", ["diagnostic_reference_type"])
        grant = resolve(note["authorization_ref"])
        # Diagnostic goal refs may carry a requirements locator, as in a bounded grant.
        errors.extend(self._authority(note, grant, context.get("conclusion"), observations, goals, [note.get("budget_ref")]))
        budget = resolve(note["budget_ref"])
        if not budget or budget.get("type") != "BudgetEnvelope":
            errors.append("diagnostic_budget_required")
        if any(resolve(resolve(r)["activity_ref"]).get("budget_ref") != note["budget_ref"] for r in observations):
            errors.append("diagnostic_budget_scope")
        for r in observations:
            event = resolve(r)
            errors.extend(self._artifact(event.get("original_response"), context["intended_use"]))
        if not nonempty_strings(note.get("alternatives")) or not isinstance(note.get("counterevidence"), list) or not note.get("decision_question") or not note.get("explanation"):
            errors.append("diagnostic_alternatives_required")
        branches = note.get("decision_branches")
        if not isinstance(branches, list) or len(branches) < 2 or any(not isinstance(b, dict) or not b.get("observation") or not b.get("plan_action") for b in branches):
            errors.append("diagnostic_branches_required")
        elif len({b["plan_action"] for b in branches}) < 2:
            errors.append("diagnostic_cannot_change_decision")
        if any(not isinstance(note.get(k), str) or not note[k].strip() for k in ("stop_condition", "stop_reason", "reopen_condition")) or not valid_fact(note.get("next_observation")):
            errors.append("diagnostic_stop_required")
        if known(note.get("next_observation")) and not note["next_observation"]["value"]:
            errors.append("diagnostic_observation_required")
        latest = {o["id"]: o["revision"] for o in state["objects"]}
        if any(latest.get(r["id"]) != r["revision"] for r in object_refs(note)):
            errors.append("stale_assessment_basis")
        active = budget.get("user_active_time") if budget else None
        amount = active["value"].get("minutes") if known(active) and isinstance(active["value"], dict) else None
        stopped = (type(amount) in {int, float} and amount <= 0) or context.get("stop_signal") in {"budget_exhausted", "no_progress", "no_decision_value", "user_pause"}
        return self._result("rejected" if errors else "compatible", errors, state_revision=state["state_revision"],
                            next_action="no_additional_observation" if stopped or note.get("next_observation", {}).get("status") in {"not_required", "not_executed"} else "candidate_observation_for_planning",
                            diagnosis_status="tentative", new_tasks=0, new_samples=0)

    def submit_assessment(self, request):
        try:
            return self._submit_assessment(request)
        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            return self._result("rejected", ["invalid_assessment_submission"])

    def _submit_assessment(self, request):
        if not isinstance(request, dict) or self.store.entry_actor not in {"AG0", "AG3"}:
            return self._result("rejected", ["assessment_fixture_actor_required"])
        changes = request.get("changes")
        if not isinstance(changes, list) or not changes or any(not isinstance(o, dict) or o.get("type") not in {"Judgment", "DiagnosticNote"} or o.get("owner") != self.store.entry_actor for o in changes):
            return self._result("rejected", ["assessment_objects_only"])
        if request.get("artifacts"):
            return self._result("rejected", ["assessment_cannot_write_originals"])
        contexts = request.get("contexts")
        if not isinstance(contexts, dict):
            return self._result("rejected", ["assessment_contexts_required"])
        external = list(object_refs(changes)) + request.get("authorization_refs", []) + request.get("adoption_refs", [])
        gate = self.store.validate_refs(external, "assessment")
        if gate.get("status") != "ok":
            return self._result("rejected", [p["code"] for p in gate.get("reasons", [])] or ["assessment_controls_unavailable"])
        for record in changes:
            context = contexts.get(record.get("id"))
            result = self.inspect_judgment(record, context) if record["type"] == "Judgment" else self.inspect_diagnostic(record, context)
            if result["status"] not in {"compatible", "limited"} or result.get("submission_ready") is False:
                return {**result, "status": "rejected"}
        # Recheck controls, versions, authorization and CAS atomically in the store.
        return self.store.commit(expected_state_revision=request.get("expected_state_revision"),
                                 operation_id=request.get("operation_id"), changes=changes,
                                 authorization_refs=request.get("authorization_refs", []),
                                 adoption_refs=request.get("adoption_refs", []))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--actor", choices=("AG0", "AG3"), default="AG3", help="Fixture configuration, not host authentication.")
    parser.add_argument("command", choices=("inspect", "diagnose", "submit"))
    args = parser.parse_args()
    try:
        request = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
        service = AssessmentService(LearningStore(args.workspace, entry_actor=args.actor))
        if args.command == "inspect":
            result = service.inspect_judgment(request.get("judgment"), request.get("context"))
        elif args.command == "diagnose":
            result = service.inspect_diagnostic(request.get("diagnostic"), request.get("context"))
        else:
            result = service.submit_assessment(request)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        result = {"status": "rejected", "reasons": [issue("invalid_or_unavailable_request")]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"compatible", "limited", "committed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
