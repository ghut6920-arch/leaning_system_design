"""B3b synthetic C0 teaching recorder; declarations are not learning judgments.

All canonical reads and writes use LearningStore. No supplied code executes,
no semantic grading runs, and no assessment, plan, or extra test is created.
The AG0 actor is a fixture configuration, not a host identity binding.
"""
from __future__ import annotations

import argparse
import copy
import fnmatch
import json
import math
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.contract_rules import PROTOCOL, object_refs
from runtime.b3_semantics import active_grant, known_bool, task_checks, timestamp
from runtime.learning_materials import MaterialsService, valid_fact
from runtime.learning_store import LearningStore

VERSION = "pl-teaching/0.1.0"
QUALIFICATIONS = ("not_substituted", "prerequisite_fit", "reference_scorable", "evidence_conditions")
EXECUTION_DECISIONS = {"teaching_execution", "teaching_execute", "execute_activity", "teaching", "execute"}
VISIBILITIES = {"planned", "requested", "displayed", "backend_reference", "unknown"}
READ_ACTIONS = {"open", "resume"}
WRITE_ACTIONS = {"record_initial", "record_help", "record_revision", "record_feedback", "checkpoint", "close", "return_parent"}


def fact(status, reason=None, value=None):
    return {"status": "known", "value": value} if status == "known" else {"status": status, "reason": reason}


def ref(record):
    return {"id": record["id"], "revision": record["revision"]}


def issue(code):
    return {"code": code}


def exact_ref(value):
    return isinstance(value, dict) and isinstance(value.get("id"), str) and type(value.get("revision")) is int and value["revision"] > 0


def strings(value, nonempty=False):
    return isinstance(value, list) and (bool(value) or not nonempty) and all(isinstance(v, str) and bool(v.strip()) for v in value)


def declared_minutes(request, event=None):
    """Caller declarations are neither a measured timer nor an inferred zero."""
    previous = (event or {}).get("c0", {}).get("declared_active_minutes")
    if "active_minutes" in request:
        return fact("known", value={"minutes": request["active_minutes"], "measurement": "caller_declaration"})
    return copy.deepcopy(previous) if valid_fact(previous) else fact("unknown", "No active-time declaration was supplied.")


def minute_value(declaration):
    value = declaration.get("value") if isinstance(declaration, dict) and declaration.get("status") == "known" else None
    return value.get("minutes") if isinstance(value, dict) else None


def checkpoint_minutes(checkpoint, event, budget_ref):
    """A checkpoint can bound this run's time, not a different run or budget."""
    trusted = checkpoint.get("last_trusted_event_ref")
    if (checkpoint.get("type") != "SessionCheckpoint" or event.get("type") != "PerformanceEvent"
            or not exact_ref(trusted) or trusted["id"] != event.get("id")
            or trusted["revision"] > event.get("revision", 0)
            or checkpoint.get("activity_ref") != event.get("activity_ref")
            or checkpoint.get("budget_ref") != budget_ref
            or event.get("c0", {}).get("budget_ref") != budget_ref):
        return None
    minutes = minute_value(checkpoint.get("declared_active_minutes", {}))
    return minutes if type(minutes) in (int, float) and math.isfinite(minutes) and minutes >= 0 else None


class TeachingService:
    """Finite C0 actions on already designed activities and reviewed materials."""

    def __init__(self, store):
        self.store = store

    @staticmethod
    def _result(status, **extra):
        return {"status": status, "synthetic_only": True, "mutated": False,
                "scoring": "not_executed", "judgment_created": False,
                "new_test_created": False, "reasons": [], **extra}

    def _reject(self, code, status="rejected", **extra):
        return self._result(status, reasons=[issue(code)], **extra)

    def _read(self, refs, state, use="teaching_execution"):
        result = self.store.read_refs(refs, use)
        if result.get("status") != "ok":
            return None, self._result("blocked", reasons=result.get("reasons", [issue("references_unavailable")]), state_revision=result.get("state_revision"))
        if result.get("state_revision") != state:
            return None, self._reject("context_changed", "blocked", state_revision=result.get("state_revision"))
        return result["objects"], None

    def _guard(self, refs, state, use="teaching_execution"):
        result = self.store.validate_refs(refs, use)
        if result.get("status") != "ok" or result.get("state_revision") != state:
            return self._result("blocked", reasons=result.get("reasons") or [issue("context_changed")], state_revision=result.get("state_revision"))
        return None

    def _budget_declarations(self, state, activity, budget):
        """Preserve legal old checkpoints without revising historical answers."""
        events = {o["id"]: o for o in state["objects"] if o.get("type") == "PerformanceEvent"
                  and o.get("activity_ref") == ref(activity) and o.get("c0", {}).get("budget_ref") == ref(budget)}
        declarations = {identifier: declared_minutes({}, event) for identifier, event in events.items()}
        for checkpoint in state["objects"]:
            trusted = checkpoint.get("last_trusted_event_ref", {})
            event = events.get(trusted.get("id")) if isinstance(trusted, dict) else None
            minutes = checkpoint_minutes(checkpoint, event, ref(budget)) if event else None
            if minutes is None:
                continue
            gate = self.store.validate_refs([ref(checkpoint), *object_refs(checkpoint)], "teaching_execution")
            if gate.get("state_revision") != state["state_revision"]:
                return None, self._reject("context_changed", "blocked")
            if gate.get("status") != "ok":
                return None, self._result("blocked", reasons=gate.get("reasons") or [issue("budget_checkpoint_unavailable")],
                                          state_revision=state["state_revision"])
            previous = minute_value(declarations[event["id"]])
            if previous is None or minutes > previous:
                declarations[event["id"]] = copy.deepcopy(checkpoint["declared_active_minutes"])
        return declarations, None

    def _adoption_problem(self, record, activity, context):
        # Older B0 fixture records have no adoption field. Explicit modern
        # candidate/recheck records cannot become execution basis by omission.
        if "adoption" not in record:
            return None
        adoption = record["adoption"]
        if not isinstance(adoption, dict) or adoption.get("status") not in {"adopted", "partially_adopted"}:
            return self._reject("unadopted_professional_basis", "not_ready")
        scope = adoption.get("scope")
        if not isinstance(context, dict):
            return self._reject("adoption_scope_unavailable", "not_ready")
        # Full adoption keeps the shared contract's declared prose scope.
        # Actual activity/criterion/material binding remains checked separately.
        full = isinstance(scope, (str, list, dict)) and bool(scope)
        if isinstance(scope, dict):
            criteria = [c for c in activity.get("criterion_refs", []) if record.get("type") != "GoalSpec" or c.get("id") == record["id"]]
            declared_criteria = scope.get("criterion_refs", [])
            covered = isinstance(declared_criteria, list) and bool(criteria) and all(c in declared_criteria for c in criteria)
            usage = scope.get("activity_ref") == ref(activity) and scope.get("intended_use") == context.get("intended_use") and covered
            if "activity_ref" in scope and scope["activity_ref"] != ref(activity):
                full = False
            if "intended_use" in scope and scope["intended_use"] != context.get("intended_use"):
                full = False
            if "criterion_refs" in scope and not covered:
                full = False
            if adoption["status"] == "partially_adopted":
                full = usage
        elif adoption["status"] == "partially_adopted":
            full = False
        if not full:
            return self._reject("adoption_scope_unavailable", "not_ready")
        return None

    def _execution_methods(self, request, activity, material_refs, state):
        """Bind used configurations to a run without revising its ActivitySpec.

        Continuation recovers the exact saved references and context. An explicit
        request cannot silently replace the configuration used by that event.
        """
        event_ref = request.get("event_ref")
        if request.get("action") == "resume" and request.get("checkpoint_ref") is not None:
            checkpoint_ref = request["checkpoint_ref"]
            if not exact_ref(checkpoint_ref):
                return None, self._reject("checkpoint_reference_required")
            checkpoints, problem = self._read([checkpoint_ref], state)
            if problem:
                return None, problem
            checkpoint = checkpoints[0]
            if checkpoint.get("type") != "SessionCheckpoint" or checkpoint.get("activity_ref") != ref(activity):
                return None, self._reject("checkpoint_activity_mismatch")
            event_ref = checkpoint.get("last_trusted_event_ref")
        event = None
        if event_ref is not None:
            if not exact_ref(event_ref):
                return None, self._reject("event_reference_required")
            events, problem = self._read([event_ref], state)
            if problem:
                return None, problem
            event = events[0]
            if event.get("type") != "PerformanceEvent" or event.get("activity_ref") != ref(activity):
                return None, self._reject("event_activity_mismatch")
        declared = activity.get("method_config_refs", [])
        incoming = request.get("method_config_refs")
        saved = event.get("method_config_refs", []) if event is not None else None
        for refs in (declared, incoming, saved):
            if refs is not None and (not isinstance(refs, list) or any(not exact_ref(r) for r in refs) or len({(r["id"], r["revision"]) for r in refs}) != len(refs)):
                return None, self._reject("exact_method_config_references_required")
        used = copy.deepcopy(saved if saved is not None and incoming is None else declared)
        if incoming is not None:
            for config_ref in incoming:
                if config_ref not in used:
                    used.append(copy.deepcopy(config_ref))
        if any(r not in used for r in declared):
            return None, self._reject("activity_method_configuration_mismatch")
        if saved is not None and used != saved:
            return None, self._reject("event_method_configuration_mismatch")
        strategy_context = request.get("strategy_context")
        saved_context = event.get("c0", {}).get("strategy_context") if event is not None else None
        if saved_context is not None:
            if strategy_context is not None and strategy_context != saved_context:
                return None, self._reject("event_strategy_context_mismatch")
            strategy_context = copy.deepcopy(saved_context)
        if used:
            expected = {"activity_ref": ref(activity), "goal_refs": activity["goal_refs"],
                        "material_refs": material_refs, "budget_ref": activity["budget_ref"],
                        "material_context": request.get("context")}
            if not isinstance(strategy_context, dict) or any(strategy_context.get(key) != value for key, value in expected.items()):
                return None, self._reject("strategy_execution_context_required", "not_ready")
            # Keep the B3c gate authoritative for adoption, current revisions,
            # resource conditions and strategy-specific controls.
            from runtime.learning_strategies import StrategiesService
            service = StrategiesService(self.store)
            for config_ref in used:
                result = service.reuse_config(config_ref, strategy_context)
                if result.get("status") != "reusable":
                    return None, self._result("blocked", reasons=result.get("reasons") or [issue("method_configuration_not_reusable")], state_revision=state)
                problem = self._guard([config_ref], state)
                if problem:
                    return None, problem
        elif strategy_context is not None:
            return None, self._reject("strategy_context_without_configuration")
        return {"method_config_refs": used, "strategy_context": copy.deepcopy(strategy_context)}, None

    @staticmethod
    def _completeness(request, event=None):
        declaration = request.get("timeline_completeness", (event or {}).get("timeline_completeness"))
        if declaration is None:
            return fact("unknown", "The caller has not declared a complete contact and help timeline.")
        if not valid_fact(declaration) or (declaration.get("status") != "unknown" and not known_bool(declaration) and not known_bool(declaration, False)):
            return None
        return copy.deepcopy(declaration)

    @staticmethod
    def _assessment_handoff(event, entry, material_context):
        return {"status": "ready_for_inspection", "event_ref": ref(event),
                "response_point": {"event_ref": ref(event), "kind": entry["kind"], "sequence": entry["sequence"]},
                "material_context": copy.deepcopy(material_context),
                "timeline_completeness": copy.deepcopy(event["timeline_completeness"]),
                "assessment_called": False, "judgment_created": False}

    def _prepare(self, request):
        state = self.store.read_context()
        if state.get("status") != "ok" or not state.get("synthetic_only"):
            return None, self._reject("synthetic_workspace_unavailable", "blocked")
        revision = state["state_revision"]
        activity_ref = request.get("activity_ref")
        if not exact_ref(activity_ref):
            return None, self._reject("activity_reference_required")
        objects, problem = self._read([activity_ref], revision)
        if problem:
            return None, problem
        activity = objects[0]
        latest = {obj["id"]: obj["revision"] for obj in state["objects"]}
        if activity.get("type") != "ActivitySpec" or latest.get(activity["id"]) != activity["revision"]:
            return None, self._reject("current_activity_required")
        problem = self._adoption_problem(activity, activity, request.get("context"))
        if problem:
            return None, problem
        operations = activity.get("learner_operations")
        checks = task_checks(activity)
        if not strings(operations, True) or not strings(checks["target_operations"], True) or not set(operations).issubset(checks["target_operations"]) or checks["conflicts"] or any(not known_bool(checks.get(k)) for k in QUALIFICATIONS):
            return None, self._reject("task_qualification_required", "not_ready")
        goal_refs, criteria = activity.get("goal_refs"), activity.get("criterion_refs")
        if not isinstance(goal_refs, list) or not goal_refs or not all(exact_ref(r) for r in goal_refs) or not isinstance(criteria, list) or not criteria or not all(exact_ref(r) and isinstance(r.get("locator"), str) and r["locator"].startswith("requirements/") for r in criteria):
            return None, self._reject("goal_and_criteria_required")
        goals, problem = self._read(goal_refs, revision)
        if problem:
            return None, problem
        goal_index = {(o["id"], o["revision"]): o for o in goals}
        if any(g.get("type") != "GoalSpec" or latest.get(g["id"]) != g["revision"] for g in goals):
            return None, self._reject("current_goal_required")
        for goal in goals:
            problem = self._adoption_problem(goal, activity, request.get("context"))
            if problem:
                return None, problem
        requirement_ids = set()
        for criterion in criteria:
            goal = goal_index.get((criterion["id"], criterion["revision"]))
            requirement_id = criterion["locator"].split("/", 1)[1]
            if not goal or not any(r.get("requirement_id") == requirement_id for r in goal.get("requirements", [])):
                return None, self._reject("criterion_binding_mismatch")
            requirement_ids.add(requirement_id)
        budget_ref = activity.get("budget_ref")
        if not exact_ref(budget_ref):
            return None, self._reject("shared_budget_required", "not_ready")
        budgets, problem = self._read([budget_ref], revision)
        if problem:
            return None, problem
        budget = budgets[0]
        active_time = budget.get("user_active_time", {})
        minutes = active_time.get("value", {}).get("minutes") if isinstance(active_time.get("value"), dict) else None
        stopping = request.get("action") in {"checkpoint", "close", "resume"}
        if budget.get("type") != "BudgetEnvelope" or latest.get(budget["id"]) != budget["revision"] or active_time.get("status") != "known" or type(minutes) not in (int, float) or not math.isfinite(minutes) or minutes < 0 or (minutes == 0 and not stopping) or activity["id"] not in budget.get("allocation_scope", []):
            return None, self._reject("current_active_time_budget_required", "not_ready")
        budget_declarations, problem = self._budget_declarations(state, activity, budget)
        if problem:
            return None, problem
        if "active_minutes" in request:
            used = request["active_minutes"]
            if type(used) not in (int, float) or not math.isfinite(used) or used < 0:
                return None, self._reject("finite_active_time_required")
            # record_initial preserves an answer received exactly at the limit;
            # opening or extending the teaching work then stops.
            if not stopping and (used > minutes or (used == minutes and request.get("action") != "record_initial")):
                return None, self._reject("shared_budget_exceeded", "stopped")
        if request.get("action") == "open":
            # Opening another packet must not forget the current run's
            # persisted cumulative declaration merely because a field is absent.
            if any((used := minute_value(declaration)) is not None and used >= minutes for declaration in budget_declarations.values()):
                return None, self._reject("shared_budget_exceeded", "stopped")
        authority_refs = activity.get("authority_refs", [])
        if not isinstance(authority_refs, list) or not authority_refs or not all(exact_ref(r) for r in authority_refs):
            return None, self._reject("execution_authorization_required", "not_ready")
        grants, problem = self._read(authority_refs, revision)
        if problem:
            return None, problem
        permitted = []
        for grant in grants:
            if grant.get("type") != "AuthorizationGrant" or grant.get("grantee") != "AG0" or grant.get("binding_status") != "verified_for_fixture" or grant.get("budget_ref") != budget_ref or not EXECUTION_DECISIONS.intersection(grant.get("decision_types", [])):
                continue
            scope = grant.get("object_scope", [])
            allowed = grant.get("criterion_refs", [])
            if not any(isinstance(p, str) and fnmatch.fnmatchcase(activity["id"], p) for p in scope):
                continue
            if any(not any(c.get("id") == a.get("id") and c.get("revision") == a.get("revision") and c.get("locator") == a.get("locator") for a in allowed if isinstance(a, dict)) for c in criteria):
                continue
            if not grant.get("permitted_conclusions") or not active_grant(grant.get("validity"), allow_legacy=True):
                continue
            permitted.append(ref(grant))
        if not permitted:
            return None, self._reject("execution_authorization_required", "not_ready")
        if request.get("action") in WRITE_ACTIONS and not any(r in request.get("authorization_refs", []) for r in permitted):
            return None, self._reject("explicit_execution_authorization_required")
        context = request.get("context")
        if not isinstance(context, dict) or context.get("activity_ref") != activity_ref or context.get("goal_refs") != goal_refs:
            return None, self._reject("material_use_context_required")
        material_refs = activity.get("material_refs", [])
        if not isinstance(material_refs, list) or not material_refs or not all(exact_ref(r) for r in material_refs):
            return None, self._reject("reviewed_materials_required", "not_ready")
        materials, problem = self._read(material_refs, revision)
        if problem:
            return None, problem
        visible = []
        feedback_reference_refs = []
        for material in materials:
            if latest.get(material["id"]) != material["revision"]:
                return None, self._reject("stale_basis_reference")
            problem = self._adoption_problem(material, activity, context)
            if problem:
                return None, problem
            result = MaterialsService(self.store).inspect_material(material, context)
            if result.get("status") != "compatible":
                return None, self._result("blocked", reasons=result.get("reasons") or [issue("material_not_compatible")], state_revision=revision)
            visible.extend(copy.deepcopy(material["visible_input"]))
            feedback_reference_refs.extend(copy.deepcopy(material["verification"]["content"]["anchor_refs"]))
        methods, problem = self._execution_methods(request, activity, material_refs, revision)
        if problem:
            return None, problem
        reference_refs = activity.get("reference_refs", [])
        if not isinstance(reference_refs, list) or not reference_refs:
            return None, self._reject("scorable_reference_required", "not_ready")
        branch_refs = []
        for branch in activity.get("branches", []):
            if isinstance(branch, dict) and isinstance(branch.get("reference_refs"), list):
                branch_refs.extend(branch["reference_refs"])
        current_reference_refs = reference_refs + branch_refs
        if any(isinstance(r, dict) and "id" in r and (not exact_ref(r) or latest.get(r["id"]) != r["revision"]) for r in current_reference_refs):
            return None, self._reject("stale_basis_reference", "not_ready")
        problem = self._guard(current_reference_refs, revision)
        if problem:
            return None, problem
        parent_task = activity.get("parent_task", {})
        parent = parent_task.get("value") if isinstance(parent_task, dict) and parent_task.get("status") == "known" else None
        parent_events = []
        if parent:
            if not isinstance(parent, dict) or parent.get("budget_ref") != budget_ref or not exact_ref(parent.get("parent_activity_ref")) or not parent.get("return_connection") or not parent.get("local_sufficiency") or not parent.get("alternative_explanations") or not parent.get("entry_basis_refs"):
                return None, self._reject("parent_repair_context_required")
            parent_objects, problem = self._read([parent["parent_activity_ref"]], revision)
            if problem:
                return None, problem
            parent_activity = parent_objects[0]
            if parent_activity.get("type") != "ActivitySpec" or parent_activity.get("budget_ref") != budget_ref or parent_activity["id"] not in budget.get("allocation_scope", []):
                return None, self._reject("shared_parent_budget_required")
            problem = self._adoption_problem(parent_activity, parent_activity, context)
            if problem:
                return None, problem
            problem = self._guard([parent.get("parent_artifact", {})] + parent["entry_basis_refs"], revision)
            if problem:
                return None, problem
            bases, problem = self._read(parent["entry_basis_refs"], revision)
            if problem:
                return None, problem
            parent_events = [o for o in bases if o.get("type") == "PerformanceEvent"]
        elif not valid_fact(parent_task) or parent_task.get("status") not in {"not_applicable", "not_required"}:
            return None, self._reject("parent_task_scope_required")
        problem = self._guard([activity_ref], revision)
        if problem:
            return None, problem
        return {"state_revision": revision, "activity": activity, "budget": budget, "budget_declarations": budget_declarations,
                "execution_authorization_refs": permitted,
                "context": context, "parent": parent, "requirements": requirement_ids,
                **methods,
                "feedback_reference_refs": feedback_reference_refs,
                "parent_help_history_refs": [ref(o) for o in parent_events],
                "parent_help_conditions": [{"event_ref": ref(o), "conditions": self._help_conditions(o)} for o in parent_events],
                "learner_packet": {"prompt": copy.deepcopy(activity.get("prompt")), "visible_input": visible}}, None

    def _event(self, request, prepared):
        event_ref = request.get("event_ref")
        if not exact_ref(event_ref):
            return None, self._reject("event_reference_required")
        objects, problem = self._read([event_ref], prepared["state_revision"])
        if problem:
            return None, problem
        event = objects[0]
        if event.get("type") != "PerformanceEvent" or event.get("owner") != "AG0" or event.get("activity_ref") != ref(prepared["activity"]):
            return None, self._reject("event_activity_mismatch")
        if event.get("c0", {}).get("status") in {"closed", "returned"}:
            return None, self._reject("event_already_closed")
        event = copy.deepcopy(event)
        event.setdefault("c0", {})["declared_active_minutes"] = copy.deepcopy(prepared["budget_declarations"].get(event["id"], declared_minutes({}, event)))
        previous = minute_value(declared_minutes({}, event))
        used = minute_value(declared_minutes(request, event))
        if previous is not None and used is not None and used < previous:
            return None, self._reject("active_time_cannot_decrease")
        limit = prepared["budget"]["user_active_time"]["value"]["minutes"]
        if used is not None and used >= limit and request.get("action") not in {"checkpoint", "close"}:
            return None, self._reject("shared_budget_exceeded", "stopped")
        event["timeline_completeness"] = self._completeness(request, event)
        if event["timeline_completeness"] is None:
            return None, self._reject("explicit_timeline_completeness_required")
        return event, None

    def _timeline_entry(self, value, kind, prepared, sequence):
        if not isinstance(value, dict) or not isinstance(value.get("content"), str) or not value["content"].strip() or value.get("visibility") not in VISIBILITIES or not valid_fact(value.get("time")) or not strings(value.get("target_operations")) or not strings(value.get("substituted_operations")):
            return None, self._reject("explicit_timeline_conditions_required")
        operations = set(prepared["activity"]["learner_operations"])
        if not set(value["target_operations"]).issubset(operations) or not set(value["substituted_operations"]).issubset(operations):
            return None, self._reject("timeline_operation_scope")
        entry = {k: copy.deepcopy(value[k]) for k in ("content", "visibility", "target_operations", "substituted_operations", "time")}
        entry.update(kind=kind, sequence=sequence)
        return entry, None

    def _timeline_order(self, timeline):
        previous = None
        for entry in timeline:
            declared = entry.get("time", {})
            if declared.get("status") != "known":
                continue
            parsed = timestamp(declared)
            if parsed is None:
                return self._reject("known_timeline_timestamp_required")
            if previous is not None and parsed < previous:
                return self._reject("timeline_time_order_conflict")
            previous = parsed
        return None

    def _artifact(self, artifact_ref, artifacts, state):
        if not isinstance(artifact_ref, dict) or not isinstance(artifact_ref.get("path"), str) or artifact_ref.get("revision") != 1 or artifact_ref.get("origin") != "synthetic_fixture" or not isinstance(artifact_ref.get("locator"), str) or not artifact_ref["locator"]:
            return None, self._reject("immutable_response_artifact_required")
        if artifact_ref["path"] in artifacts:
            content = artifacts[artifact_ref["path"]]
            if not isinstance(content, str) or artifact_ref["locator"] not in content:
                return None, self._reject("artifact_locator_required")
            # validate_refs also checks path safety when an artifact is incoming;
            # the commit gate will perform canonical immutable/path validation.
            if "\\" in artifact_ref["path"] or ":" in artifact_ref["path"] or any(p in {"", ".", ".."} for p in artifact_ref["path"].split("/")):
                return None, self._reject("invalid_artifact_ref")
            return content, None
        problem = self._guard([artifact_ref], state)
        if problem:
            return None, problem
        start, end = artifact_ref.get("start_line"), artifact_ref.get("end_line")
        if type(start) is not int or type(end) is not int:
            return None, self._reject("existing_artifact_line_range_required")
        result = self.store.read_artifact_segment(artifact_ref, start, end, "teaching_execution")
        if result.get("status") != "ok" or result.get("state_revision") != state:
            return None, self._result("blocked", reasons=result.get("reasons") or [issue("context_changed")])
        return result["text"], None

    @staticmethod
    def _help_conditions(event):
        entries = [e for e in event["timeline"] if e.get("kind") in {"help", "feedback", "exposure"}]
        displayed = [{"sequence": e["sequence"], "kind": e["kind"], "target_operations": e["target_operations"],
                      "substituted_operations": e["substituted_operations"], "artifact_ref": e.get("artifact_ref")}
                     for e in entries if e.get("visibility") == "displayed"]
        unknown = any(e.get("visibility") == "unknown" for e in entries)
        return {"displayed_help": fact("known", value=displayed),
                "unrecorded_help": fact("unknown", "Unrecorded help and contact are not inferred from the record."),
                "unknown_visibility": unknown,
                "substituted_operations": sorted({op for e in displayed for op in e["substituted_operations"]}),
                "independent_support": "not_assessed"}

    def _commit(self, request, changes, artifacts=None, **extra):
        result = self.store.commit(request.get("expected_state_revision"), request.get("operation_id"), changes,
                                   artifacts=artifacts or {}, authorization_refs=request.get("authorization_refs", []), adoption_refs=request.get("adoption_refs", []))
        receipt = dict(result)
        status = receipt.pop("status")
        response = self._result(status, **receipt)
        response["mutated"] = result.get("status") == "committed"
        if response["mutated"]:
            response.update(extra)
        return response

    def _initial(self, request, prepared):
        identifier, sample = request.get("event_id"), request.get("independent_sample_id")
        if not isinstance(identifier, str) or not identifier.startswith("FIX-") or not isinstance(sample, str) or not sample.startswith("FIX-"):
            return self._reject("synthetic_event_and_sample_required")
        state = self.store.read_context()
        if state.get("state_revision") != prepared["state_revision"]:
            return self._reject("context_changed", "blocked")
        # An ongoing C0 response remains the same Event. Legacy fixture events
        # without a C0 lifecycle are historical inputs, not claimed active runs.
        if any(o.get("type") == "PerformanceEvent" and o["id"] != identifier and o.get("activity_ref") == ref(prepared["activity"]) and o.get("c0", {}).get("status") == "active" for o in state["objects"]):
            return self._reject("existing_event_requires_revision")
        existing_initial = any(o.get("type") == "PerformanceEvent" and o["id"] == identifier for o in state["objects"])
        exposures = request.get("prior_exposures", [])
        if not isinstance(exposures, list):
            return self._reject("prior_exposures_list_required")
        timeline = []
        exposure_artifacts = {}
        for exposure in exposures:
            kind = exposure.get("kind", "exposure") if isinstance(exposure, dict) else "exposure"
            if kind not in {"exposure", "help"}:
                return self._reject("prior_exposure_kind_required")
            prior, problem = self._timeline_entry(exposure, kind, prepared, len(timeline) + 1)
            if problem:
                return problem
            artifact = exposure.get("artifact_ref")
            if artifact is None:
                path, locator = f"c0/{identifier}/prior-{prior['sequence']}.md", f"C0-prior-{prior['sequence']}"
                artifact = {"path": path, "locator": locator, "revision": 1, "origin": "synthetic_fixture"}
                exposure_artifacts[path] = f"# {locator}\n{prior['content']}\n"
            prior["artifact_ref"] = copy.deepcopy(artifact)
            timeline.append(prior)
        entry, problem = self._timeline_entry(request.get("initial_response"), "initial_response", prepared, len(timeline) + 1)
        if problem:
            return problem
        if entry["visibility"] not in {"displayed", "unknown"} or entry["substituted_operations"]:
            return self._reject("initial_response_conditions_required")
        artifacts = copy.deepcopy(request.get("artifacts", {}))
        if not isinstance(artifacts, dict):
            return self._reject("artifacts_required")
        artifacts.update(exposure_artifacts)
        for prior in timeline:
            text, problem = self._artifact(prior["artifact_ref"], artifacts, prepared["state_revision"])
            if problem:
                return problem
            if prior["content"] not in text:
                return self._reject("prior_exposure_not_locatable")
        original = request.get("original_response")
        content, problem = self._artifact(original, artifacts, prepared["state_revision"])
        if problem:
            return problem
        if entry["content"] not in content:
            return self._reject("operation_id_reused" if existing_initial else "response_content_not_locatable")
        if any(not valid_fact(request.get(k)) for k in ("actual_resources", "contact_history", "occurred_at")) or not isinstance(request.get("contributors"), list):
            return self._reject("explicit_event_facts_required")
        activity = prepared["activity"]
        entry["artifact_ref"] = copy.deepcopy(original)
        problem = self._timeline_order(timeline + [entry])
        if problem:
            return problem
        event = {"type": "PerformanceEvent", "id": identifier, "revision": 1, "owner": "AG0", "schema_version": PROTOCOL,
                 "basis_refs": [ref(activity)], "activity_ref": ref(activity), "goal_refs": copy.deepcopy(activity["goal_refs"]),
                 "original_response": copy.deepcopy(original), "revisions": [], "contributors": copy.deepcopy(request["contributors"]),
                 "timeline": timeline + [entry], "actual_resources": copy.deepcopy(request["actual_resources"]),
                 "contact_history": copy.deepcopy(request["contact_history"]), "occurred_at": copy.deepcopy(request["occurred_at"]),
                 "independent_sample_id": sample, "method_config_refs": copy.deepcopy(prepared["method_config_refs"]),
                 "timeline_completeness": self._completeness(request),
                 "intended_use": prepared["context"]["intended_use"],
                 "c0": {"version": VERSION, "status": "active", "parent_artifact": copy.deepcopy(prepared["parent"]["parent_artifact"]) if prepared["parent"] else fact("not_applicable", "Top-level activity."),
                        "budget_ref": ref(prepared["budget"]), "declared_active_minutes": declared_minutes(request),
                        "material_context": copy.deepcopy(prepared["context"]), "strategy_context": copy.deepcopy(prepared["strategy_context"]),
                        "prior_exposure_report": fact("known", value="Only the explicitly supplied prior exposures are recorded.") if "prior_exposures" in request else fact("unknown", "No prior exposure report was supplied."),
                        "inherited_event_refs": prepared["parent_help_history_refs"], "inherited_help_conditions": prepared["parent_help_conditions"],
                        "execution_authorization_refs": prepared["execution_authorization_refs"]}}
        return self._commit(request, [event], artifacts, event_ref=ref(event), factual_conditions=self._help_conditions(event), parent_help_history_refs=prepared["parent_help_history_refs"], parent_help_conditions=prepared["parent_help_conditions"], assessment_handoff=self._assessment_handoff(event, entry, prepared["context"]))

    def _append(self, request, prepared, action):
        event, problem = self._event(request, prepared)
        if problem:
            return problem
        kinds = {"record_help": ("help", "help"), "record_revision": ("revision", "revision"), "record_feedback": ("feedback", "feedback")}
        field, kind = kinds[action]
        sequence = event["timeline"][-1]["sequence"] + 1
        entry, problem = self._timeline_entry(request.get(field), kind, prepared, sequence)
        if problem:
            return problem
        problem = self._timeline_order(event["timeline"] + [entry])
        if problem:
            return problem
        artifacts = copy.deepcopy(request.get("artifacts", {}))
        if not isinstance(artifacts, dict):
            return self._reject("artifacts_required")
        if action == "record_feedback":
            index = request.get("branch_index")
            branches = prepared["activity"].get("branches", [])
            if type(index) is not int or index < 0 or index >= len(branches):
                return self._reject("existing_feedback_branch_required")
            branch = branches[index]
            if not isinstance(branch, dict) or not branch.get("action") or not branch.get("next_observation") or not branch.get("learner_next_work") or not isinstance(branch.get("reference_refs"), list) or not branch["reference_refs"]:
                return self._reject("usable_feedback_branch_required")
            if any(not any(all(r.get(k) == a.get(k) for k in ("id", "revision", "path", "locator", "origin", "start_line", "end_line")) for a in prepared["feedback_reference_refs"]) for r in branch["reference_refs"] if isinstance(r, dict)) or any(not isinstance(r, dict) for r in branch["reference_refs"]):
                return self._reject("verified_feedback_reference_required")
            problem = self._guard(branch["reference_refs"], prepared["state_revision"])
            if problem:
                return problem
            observation = request.get("observation")
            allowed = [event["original_response"]] + event["revisions"]
            if not isinstance(observation, dict) or not isinstance(observation.get("quote"), str) or not observation["quote"] or not isinstance(observation.get("artifact_ref"), dict) or not any(all(observation["artifact_ref"].get(k) == a.get(k) for k in ("path", "locator", "revision", "origin")) for a in allowed):
                return self._reject("original_observation_required")
            text, problem = self._artifact(observation["artifact_ref"], {}, prepared["state_revision"])
            if problem:
                return problem
            if observation["quote"] not in text:
                return self._reject("observation_not_locatable")
            entry.update(branch_index=index, observation=copy.deepcopy(observation), reference_refs=copy.deepcopy(branch["reference_refs"]), learner_next_work=branch["learner_next_work"], basis="declared_branch_and_locatable_response")
        artifact = request.get("revision_response") if action == "record_revision" else request.get(field, {}).get("artifact_ref")
        if artifact is None and action != "record_revision":
            path, locator = f"c0/{event['id']}/{kind}-{sequence}.md", f"C0-{kind}-{sequence}"
            artifact = {"path": path, "locator": locator, "revision": 1, "origin": "synthetic_fixture"}
            artifacts[path] = f"# {locator}\n{entry['content']}\n"
        text, problem = self._artifact(artifact, artifacts, prepared["state_revision"])
        if problem:
            return problem
        if entry["content"] not in text:
            return self._reject("response_content_not_locatable")
        if action == "record_revision":
            if any(artifact["path"] == a["path"] for a in [event["original_response"]] + event["revisions"]):
                return self._reject("revision_requires_new_artifact_path")
            if entry["visibility"] not in {"displayed", "unknown"} or entry["substituted_operations"]:
                return self._reject("revision_conditions_required")
            event["revisions"].append(dict(copy.deepcopy(artifact), sequence=sequence))
        entry["artifact_ref"] = copy.deepcopy(artifact)
        event["timeline"].append(entry)
        event["revision"] += 1
        event.setdefault("c0", {"version": VERSION, "status": "active"})["declared_active_minutes"] = declared_minutes(request, event)
        event["c0"]["actual_help_conditions"] = self._help_conditions(event)
        extra = {"event_ref": ref(event), "factual_conditions": self._help_conditions(event)}
        if action == "record_revision":
            extra["assessment_handoff"] = self._assessment_handoff(event, entry, prepared["context"])
        if action == "record_feedback" and entry["visibility"] == "displayed":
            extra["learner_next_work"] = entry["learner_next_work"]
        return self._commit(request, [event], artifacts, **extra)

    def _checkpoint(self, request, prepared, close=False):
        event, problem = self._event(request, prepared)
        if problem:
            return problem
        identifier = request.get("checkpoint_id")
        if not isinstance(identifier, str) or not identifier.startswith("FIX-") or not isinstance(request.get("stop_reason"), str) or not request["stop_reason"] or not isinstance(request.get("next_connection"), str) or not request["next_connection"] or not strings(request.get("pending_owners")) or not valid_fact(request.get("unrecorded_actions")):
            return self._reject("explicit_checkpoint_required")
        state = self.store.read_context()
        if state.get("state_revision") != prepared["state_revision"]:
            return self._reject("context_changed", "blocked")
        previous = next((o for o in state["objects"] if o["id"] == identifier), None)
        if previous and (previous.get("type") != "SessionCheckpoint" or previous.get("activity_ref") != ref(prepared["activity"])):
            return self._reject("checkpoint_identity_conflict")
        checkpoint_basis = request.get("checkpoint_ref")
        if checkpoint_basis is not None and (not exact_ref(checkpoint_basis) or checkpoint_basis["id"] != identifier or not previous or checkpoint_basis["revision"] != previous["revision"]):
            return self._reject("current_checkpoint_reference_required")
        # New checkpoints always begin at revision 1; this makes reconstructing
        # a byte-identical retry deterministic. Updating one names its exact
        # predecessor explicitly rather than inferring revision from arrival.
        checkpoint_revision = checkpoint_basis["revision"] + 1 if checkpoint_basis else 1
        controls = [o for o in state["objects"] if o.get("type") == "ControlState"]
        control_ref = request.get("control_ref") or (ref(controls[0]) if len(controls) == 1 else None)
        if not exact_ref(control_ref):
            return self._reject("control_reference_required")
        problem = self._guard([control_ref], prepared["state_revision"])
        if problem:
            return problem
        changes = []
        unfinished = request.get("unfinished_requirement_ids", [])
        closure = request.get("closure", {})
        if close:
            if not strings(unfinished) or not set(unfinished).issubset(prepared["requirements"]) or not isinstance(closure, dict) or closure.get("status") not in {"local_sufficient", "budget_end", "no_feasible_branch", "unfinished"} or not isinstance(closure.get("reason"), str) or not closure["reason"]:
                return self._reject("explicit_closure_required")
            event["revision"] += 1
            event.setdefault("c0", {"version": VERSION}).update(status="closed", closure=copy.deepcopy(closure), stop_reason=request["stop_reason"], unfinished_requirement_ids=copy.deepcopy(unfinished))
            event["c0"]["declared_active_minutes"] = declared_minutes(request, event)
            changes.append(event)
        elif "timeline_completeness" in request or "active_minutes" in request:
            event["revision"] += 1
            event["c0"]["declared_active_minutes"] = declared_minutes(request, event)
            changes.append(event)
        parent = prepared["parent"]
        checkpoint = {"type": "SessionCheckpoint", "id": identifier, "revision": checkpoint_revision, "owner": "AG0", "schema_version": PROTOCOL,
                      "basis_refs": [ref(event)], "activity_ref": ref(prepared["activity"]),
                      "parent_artifact": copy.deepcopy(parent["parent_artifact"]) if parent else fact("not_applicable", "Top-level activity."),
                      "last_trusted_event_ref": ref(event), "help_history_refs": [ref(event)], "next_connection": request["next_connection"],
                      "stop_reason": request["stop_reason"], "pending_owners": copy.deepcopy(request["pending_owners"]),
                      "budget_ref": ref(prepared["budget"]), "control_ref": copy.deepcopy(control_ref), "unrecorded_actions": copy.deepcopy(request["unrecorded_actions"]),
                      "intended_use": prepared["context"]["intended_use"], "unfinished_requirement_ids": copy.deepcopy(unfinished), "declared_active_minutes": declared_minutes(request, event)}
        changes.append(checkpoint)
        extra = {"event_ref": ref(event), "checkpoint_ref": ref(checkpoint), "parent_artifact": checkpoint["parent_artifact"], "return_connection": parent["return_connection"] if parent else checkpoint["next_connection"], "unfinished_requirement_ids": copy.deepcopy(unfinished)}
        if close:
            need = request.get("existing_need_ref")
            if need is not None:
                if not exact_ref(need):
                    return self._reject("existing_need_reference_required")
                needs, problem = self._read([need], prepared["state_revision"])
                if problem:
                    return problem
                original = needs[0]
                if original.get("type") != "LearningNeed" or original.get("goal_ref") not in prepared["activity"]["goal_refs"] or not set(unfinished).issubset(set(original.get("requirement_ids", []))):
                    return self._reject("same_need_scope_required")
                extra["learning_need_candidate"] = {"existing_need_ref": need, "status": "candidate", "additional_event_ref": ref(event), "unfinished_requirement_ids": unfinished, "acceptance_changed": False, "disposition_changed": False}
                extra["existing_need_ref"] = need
            elif unfinished:
                extra["learning_need_candidate"] = {"status": "candidate", "goal_refs": prepared["activity"]["goal_refs"], "requirement_ids": unfinished, "event_ref": ref(event), "parent_task": ref(prepared["activity"]), "requester": "AG0", "assignee": "AG1", "acceptance": {"status": "proposed"}, "disposition": {"status": "pending"}, "reason": closure["reason"]}
        return self._commit(request, changes, **extra)

    def _return_parent(self, request, prepared):
        parent = prepared["parent"]
        if not parent:
            return self._reject("parent_repair_required")
        if request.get("parent_ref") != parent["parent_activity_ref"] or request.get("parent_artifact") != parent["parent_artifact"] or request.get("return_connection") != parent["return_connection"]:
            return self._reject("same_parent_return_required")
        event, problem = self._event(request, prepared)
        if problem:
            return problem
        sequence = event["timeline"][-1]["sequence"] + 1
        # Returning records a control connection; it does not claim display,
        # independent operation, or completion of the entire parent task.
        event["timeline"].append({"kind": "return_parent", "sequence": sequence, "visibility": "backend_reference", "content": parent["return_connection"], "target_operations": [], "substituted_operations": [], "time": fact("unknown", "The caller has not supplied a measured return time."), "parent_activity_ref": parent["parent_activity_ref"], "parent_artifact": parent["parent_artifact"]})
        event["revision"] += 1
        event.setdefault("c0", {"version": VERSION}).update(status="returned", return_connection=parent["return_connection"], parent_artifact=parent["parent_artifact"], overall_assessment="not_executed")
        event["c0"]["declared_active_minutes"] = declared_minutes(request, event)
        return self._commit(request, [event], event_ref=ref(event), parent_ref=parent["parent_activity_ref"], parent_artifact=parent["parent_artifact"], return_connection=parent["return_connection"], inherited_help=self._help_conditions(event), parent_help_history_refs=prepared["parent_help_history_refs"], parent_help_conditions=prepared["parent_help_conditions"], overall_assessment="not_executed")

    def _resume(self, request, prepared):
        checkpoint_ref = request.get("checkpoint_ref")
        if checkpoint_ref is not None:
            if not exact_ref(checkpoint_ref):
                return self._reject("checkpoint_reference_required")
            objects, problem = self._read([checkpoint_ref], prepared["state_revision"])
            if problem:
                return problem
            checkpoint = objects[0]
            if checkpoint.get("type") != "SessionCheckpoint" or checkpoint.get("activity_ref") != ref(prepared["activity"]):
                return self._reject("checkpoint_activity_mismatch")
            event_ref = checkpoint["last_trusted_event_ref"]
        else:
            checkpoint = None
            event_ref = request.get("event_ref")
        if not exact_ref(event_ref):
            return self._reject("trusted_event_or_checkpoint_required", "needs_input")
        objects, problem = self._read([event_ref], prepared["state_revision"])
        if problem:
            return problem
        event = objects[0]
        if event.get("type") != "PerformanceEvent" or event.get("activity_ref") != ref(prepared["activity"]):
            return self._reject("event_activity_mismatch")
        problem = self._guard([event["original_response"]] + event.get("revisions", []), prepared["state_revision"])
        if problem:
            return problem
        parent = prepared["parent"]
        budget_declaration = prepared["budget_declarations"].get(event["id"], declared_minutes({}, event))
        return self._result("ready", state_revision=prepared["state_revision"], recovery={"source": "checkpoint" if checkpoint else "last_trusted_event", "checkpoint_ref": checkpoint_ref, "activity_ref": ref(prepared["activity"]), "last_trusted_event_ref": event_ref, "original_response": event["original_response"], "revisions": event.get("revisions", []), "help_history": copy.deepcopy(event["timeline"]), "factual_conditions": self._help_conditions(event), "parent_help_history_refs": prepared["parent_help_history_refs"], "parent_help_conditions": prepared["parent_help_conditions"], "declared_active_minutes": copy.deepcopy(budget_declaration), "parent_artifact": checkpoint["parent_artifact"] if checkpoint else parent["parent_artifact"] if parent else fact("not_applicable", "Top-level activity."), "next_connection": checkpoint["next_connection"] if checkpoint else parent["return_connection"] if parent else fact("unknown", "No recorded return connection."), "unrecorded_actions": checkpoint["unrecorded_actions"] if checkpoint else fact("unknown", "No checkpoint records additional actions.")})

    def run(self, request):
        if not isinstance(request, dict) or request.get("synthetic_only") is not True:
            return self._reject("synthetic_request_required")
        if self.store.entry_actor != "AG0":
            return self._reject("ag0_fixture_actor_required")
        action = request.get("action")
        if action not in READ_ACTIONS | WRITE_ACTIONS:
            return self._reject("unknown_teaching_action")
        if action in WRITE_ACTIONS and (type(request.get("expected_state_revision")) is not int or request["expected_state_revision"] < 0 or not isinstance(request.get("operation_id"), str) or not request["operation_id"]):
            return self._reject("explicit_cas_operation_required")
        if "timeline_completeness" in request and (action in READ_ACTIONS or self._completeness(request) is None):
            return self._reject("explicit_timeline_completeness_required")
        try:
            prepared, problem = self._prepare(request)
            if problem:
                return problem
            if action == "open":
                return self._result("ready", state_revision=prepared["state_revision"], activity_ref=ref(prepared["activity"]), execution_authorization_refs=prepared["execution_authorization_refs"], learner_packet=prepared["learner_packet"], evidence_conditions="declared_activity_and_material_conditions", parent_help_history_refs=prepared["parent_help_history_refs"], parent_help_conditions=prepared["parent_help_conditions"], assessment_dependency="explicit_response_handoff", method_config_refs=prepared["method_config_refs"], budget_ref=ref(prepared["budget"]))
            if action == "resume":
                return self._resume(request, prepared)
            if action == "record_initial":
                return self._initial(request, prepared)
            if action in {"record_help", "record_revision", "record_feedback"}:
                return self._append(request, prepared, action)
            if action in {"checkpoint", "close"}:
                return self._checkpoint(request, prepared, action == "close")
            return self._return_parent(request, prepared)
        except (KeyError, TypeError, ValueError, AttributeError, IndexError):
            return self._reject("invalid_teaching_request")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--request", required=True, help="UTF-8 JSON request file")
    args = parser.parse_args(argv)
    try:
        request = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
        result = TeachingService(LearningStore(args.workspace, entry_actor="AG0")).run(request)
    except (OSError, ValueError):
        result = TeachingService._result("rejected", reasons=[issue("request_file_unavailable")])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"ready", "candidate", "committed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
