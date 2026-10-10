"""B4 finite planning decisions on synthetic, shared LearningStore records.

AG1 decides the scope; the service checks declared feasibility and accounting.
It does not pick priorities, grade answers, run calendars or bind real actors.
"""
from __future__ import annotations

import argparse
import copy
from fnmatch import fnmatchcase
import hashlib
import json
import math
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.b3_semantics import active_grant, known_bool, task_checks
from runtime.contract_rules import PROTOCOL, object_refs, walk
from runtime.learning_assessment import AssessmentService
from runtime.learning_materials import MaterialsService
from runtime.learning_store import LearningStore

VERSION = "pl-planning/0.1.0"
ACTIVE_COMPONENTS = (
    "preparation_verification", "context_recovery", "learning",
    "feedback_check", "closure_switch", "maintenance_correction",
)
OUTCOMES = {"scheduled", "partially_scheduled", "merged", "deferred",
            "no_further_investment", "closed", "returned"}
FINAL = {"closed", "merged", "no_further_investment"}


def ref(record):
    return {"id": record["id"], "revision": record["revision"]}


def fact(status, reason=None, value=None):
    return {"status": "known", "value": value} if status == "known" else {"status": status, "reason": reason}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def exact(value):
    return isinstance(value, dict) and text(value.get("id")) and type(value.get("revision")) is int and value["revision"] > 0


def strings(value):
    return isinstance(value, list) and bool(value) and all(text(v) for v in value) and len(set(value)) == len(value)


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def exceeds(value, limit):
    return value > limit and not math.isclose(value, limit, rel_tol=1e-12, abs_tol=1e-9)


def amount(value, unit="minutes"):
    if not isinstance(value, dict) or value.get("status") != "known" or not isinstance(value.get("value"), dict):
        return None
    result = value["value"].get(unit)
    return result if number(result) else None


def digest(request):
    return hashlib.sha256(json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class PlanningService:
    """Explicit finite allocations; no scheduling algorithm or separate queue."""

    def __init__(self, store):
        self.store = store

    @staticmethod
    def _result(status, codes=(), **fields):
        return {"status": status, "synthetic_only": True, "mutated": False,
                "reasons": [{"code": code} for code in codes], "judgment_created": False,
                "new_test_created": False, "automatic_reminder": False, **fields}

    def _read(self, refs, revision, kind=None, current=None, use="planning"):
        result = self.store.read_refs(refs, use)
        if result.get("status") != "ok" or result.get("state_revision") != revision:
            return None, self._result("blocked", [p["code"] for p in result.get("reasons", [])] or ["context_changed"])
        objects = result["objects"]
        if len(objects) != len(refs) or (kind and any(o.get("type") != kind for o in objects)):
            return None, self._result("rejected", ["planning_reference_type"])
        if current is not None and any(current.get(o["id"]) != o["revision"] for o in objects):
            return None, self._result("rejected", ["stale_planning_reference"])
        return objects, None

    def _graph(self, roots, revision, current):
        """Controls cover every referenced fact and original, before use."""
        pending, seen, objects = list(roots), set(), {}
        current_types = {"GoalSpec", "ActivitySpec", "MaterialUse", "SourceFragment", "MethodConfig",
                         "Judgment", "AuthorizationGrant", "BudgetEnvelope", "SessionCheckpoint"}
        while pending:
            item = pending.pop()
            key = (item.get("id"), item.get("revision"))
            if key in seen:
                continue
            seen.add(key)
            records, problem = self._read([item], revision)
            if problem:
                return None, problem
            record = records[0]
            if record["type"] in current_types and current.get(record["id"]) != record["revision"]:
                return None, self._result("rejected", ["stale_professional_basis"])
            objects[key] = record
            pending.extend(object_refs(record))
            anchors = [v for v in walk(record) if isinstance(v, dict) and "path" in v and "origin" in v]
            gate = self.store.validate_refs(anchors, "planning")
            if gate.get("status") != "ok" or gate.get("state_revision") != revision:
                return None, self._result("blocked", [p["code"] for p in gate.get("reasons", [])] or ["context_changed"])
        return objects, None

    def _retry(self, request, revision):
        """Only surviving canonical receipts permit replay; no shadow payload log."""
        candidates = [dict(d["need_ref"], revision=d["need_ref"]["revision"] + 1)
                      for d in request.get("decisions", []) if isinstance(d, dict) and exact(d.get("need_ref"))]
        if not candidates:
            return None
        result = self.store.read_refs(candidates, "planning")
        if result.get("status") != "ok" or result.get("state_revision") != revision:
            return None
        receipts = [o.get("metadata", {}).get("planning", {}) for o in result["objects"]]
        matches = [r.get("operation_id") == request.get("operation_id") for r in receipts]
        if not any(matches):
            return None
        if not all(matches) or any(r.get("request_digest") != digest(request) for r in receipts):
            return self._result("rejected", ["operation_id_reused"])
        output_refs = receipts[0].get("output_refs", [])
        gate = self.store.validate_refs(output_refs + list(object_refs(request)), "planning")
        if gate.get("status") != "ok" or gate.get("state_revision") != revision:
            return self._result("blocked", [p["code"] for p in gate.get("reasons", [])] or ["context_changed"])
        return self._result("committed", state_revision=receipts[0]["committed_state_revision"],
                            output_refs=output_refs, replayed=True)

    def _recorded_spent(self, objects, budget_ref):
        # C0 declares cumulative time within a run. The maximum is a lower
        # bound; adding several runs could double count the same declaration.
        values = []
        for obj in objects:
            c0 = obj.get("c0", {})
            if obj.get("type") == "PerformanceEvent" and c0.get("budget_ref") == budget_ref:
                minutes = amount(c0.get("declared_active_minutes"))
                if minutes is not None:
                    values.append(minutes)
        # Pre-fix checkpoints may have a later cumulative declaration than
        # their event. Use only legal, exactly bound time evidence; this does
        # not adopt their historical teaching decisions as current plans.
        from runtime.learning_teaching import checkpoint_minutes
        events = {obj["id"]: obj for obj in objects if obj.get("type") == "PerformanceEvent"}
        for checkpoint in objects:
            trusted = checkpoint.get("last_trusted_event_ref", {})
            event = events.get(trusted.get("id")) if isinstance(trusted, dict) else None
            minutes = checkpoint_minutes(checkpoint, event, budget_ref) if event else None
            if minutes is not None:
                gate = self.store.validate_refs([ref(checkpoint), *object_refs(checkpoint)], "planning")
                if gate.get("status") != "ok":
                    return None, self._result("blocked", [p["code"] for p in gate.get("reasons", [])] or ["budget_checkpoint_unavailable"])
                values.append(minutes)
        return (max(values) if values else None), None

    def _authority(self, request, revision, current, criteria, scope, budget_ref):
        auth_refs = request.get("authorization_refs", [])
        if not isinstance(auth_refs, list) or not auth_refs or not all(exact(r) for r in auth_refs):
            return self._result("candidate", ["planning_authorization_required"])
        grants, problem = self._read(auth_refs, revision, "AuthorizationGrant", current)
        if problem:
            return problem
        decision = "plan_adjustment" if request["action"] == "shrink" else "planning"
        for grant in grants:
            patterns = grant.get("object_scope", [])
            if (grant.get("grantee") != self.store.entry_actor or grant.get("binding_status") != "verified_for_fixture"
                    or decision not in grant.get("decision_types", []) or grant.get("budget_ref") != budget_ref
                    or not active_grant(grant.get("validity"), allow_legacy=True) or not grant.get("permitted_conclusions")
                    or not isinstance(patterns, list) or not patterns
                    or not all(any(isinstance(p, str) and fnmatchcase(i, p) for p in patterns) for i in scope)
                    or any(c not in grant.get("criterion_refs", []) for c in criteria)):
                continue
            return None
        return self._result("candidate", ["planning_authorization_scope"])

    @staticmethod
    def _cost(cost):
        if not isinstance(cost, dict) or set(cost) != {"user_active", "blocked_wait", "system_effort", "fees"}:
            return None, "complete_cost_required"
        components = cost["user_active"]
        if not isinstance(components, dict) or set(components) != set(ACTIVE_COMPONENTS):
            return None, "complete_active_cost_required"
        total, estimates = 0, False
        for key in ACTIVE_COMPONENTS:
            declaration = components[key]
            if isinstance(declaration, dict) and declaration.get("status") == "not_required" and text(declaration.get("reason")):
                continue
            minutes = amount(declaration)
            value = declaration.get("value", {}) if isinstance(declaration, dict) else {}
            if minutes is None or value.get("basis") not in {"observed", "estimate", "bounded_trial"} or not text(value.get("source")):
                return None, "bounded_or_observed_cost_required"
            total += minutes
            estimates |= value["basis"] == "estimate"
        for key in ("blocked_wait", "system_effort", "fees"):
            d = cost[key]
            if isinstance(d, dict) and d.get("status") == "not_required" and text(d.get("reason")):
                continue
            if amount(d, "amount" if key == "fees" else "minutes") is None:
                return None, "non_user_cost_unbounded"
        if amount(components["closure_switch"]) is None or amount(components["closure_switch"]) <= 0:
            return None, "closure_cost_required"
        # Declared minute estimates are normalized below the comparison
        # tolerance, keeping a fully allocated envelope from displaying debt.
        return {"minutes": round(total, 12), "estimated": estimates}, None

    def _activity(self, decision, need, budget, revision, current):
        activity_ref = decision.get("activity_ref")
        operations = decision.get("operations")
        if not exact(activity_ref) or not strings(operations) or not text(decision.get("scope")):
            return None, self._result("not_ready", ["finite_activity_scope_required"])
        graph, problem = self._graph([activity_ref, need["goal_ref"]], revision, current)
        if problem:
            return None, problem
        activity = graph[(activity_ref["id"], activity_ref["revision"])]
        if (activity.get("type") != "ActivitySpec" or need["goal_ref"] not in activity.get("goal_refs", [])
                or activity.get("budget_ref") != ref(budget) or activity["id"] not in budget.get("allocation_scope", [])
                or not set(operations).issubset(activity.get("learner_operations", []))):
            return None, self._result("not_ready", ["activity_need_budget_binding"])
        coverage = decision.get("requirement_ids")
        if (not strings(coverage) or not set(coverage).issubset(need["requirement_ids"])
                or any(dict(need["goal_ref"], locator="requirements/" + rid) not in activity.get("criterion_refs", []) for rid in coverage)):
            return None, self._result("not_ready", ["activity_requirement_binding"])
        readiness = decision.get("readiness", {})
        if any(not known_bool(readiness.get(k)) for k in ("necessary_conditions", "feasible_stop", "scope_confirmed")):
            return None, self._result("not_ready", ["professional_feasibility_required"])
        checks = task_checks(activity)
        if checks["conflicts"] or any(not known_bool(checks.get(k)) for k in ("not_substituted", "prerequisite_fit", "reference_scorable", "evidence_conditions")):
            return None, self._result("not_ready", ["qualified_activity_required"])
        context = decision.get("material_context")
        if (not isinstance(context, dict) or context.get("activity_ref") != activity_ref
                or context.get("goal_refs") != activity.get("goal_refs")):
            return None, self._result("not_ready", ["material_context_required"])
        for material_ref in activity.get("material_refs", []):
            material = graph.get((material_ref["id"], material_ref["revision"]))
            if not material or MaterialsService(self.store).inspect_material(material, context).get("status") != "compatible":
                return None, self._result("not_ready", ["reviewed_material_use_required"])
        if not activity.get("material_refs") or not activity.get("reference_refs"):
            return None, self._result("not_ready", ["scorable_material_required"])
        configs = activity.get("method_config_refs", [])
        if configs:
            from runtime.learning_strategies import StrategiesService
            strategy_context = decision.get("strategy_context")
            if not isinstance(strategy_context, dict) or strategy_context.get("activity_ref") != activity_ref:
                return None, self._result("not_ready", ["method_reuse_context_required"])
            for config_ref in configs:
                if StrategiesService(self.store).reuse_config(config_ref, strategy_context).get("status") != "reusable":
                    return None, self._result("not_ready", ["adopted_method_required"])
        # Scheduling must preserve the execution gates, including B4 whole
        # scope; a plan cannot make a candidate or incomplete activity valid.
        from runtime.learning_teaching import TeachingService
        service = TeachingService(self.store)
        if isinstance(activity.get("metadata", {}).get("b4"), dict):
            from runtime.learning_teaching_b4 import SpecializedTeachingService
            service = SpecializedTeachingService(self.store)
        execution_request = {"action": "resume", "activity_ref": activity_ref, "context": context}
        if configs:
            execution_request["strategy_context"] = decision.get("strategy_context")
        _, problem = service._prepare(execution_request)
        if problem:
            return None, self._result("not_ready", [p["code"] for p in problem.get("reasons", [])] or ["activity_not_executable"])
        return activity, None

    def _close(self, decision, need, revision, current):
        evidence = decision.get("evidence_refs")
        if not isinstance(evidence, list) or not evidence or not all(exact(r) for r in evidence):
            return self._result("not_ready", ["professional_closure_evidence_required"])
        judgments, problem = self._read(evidence, revision, "Judgment", current)
        if problem:
            return problem
        supported = set()
        for judgment in judgments:
            if (judgment.get("owner") not in {"AG0", "AG3"} or judgment.get("goal_ref") != need["goal_ref"]
                    or judgment.get("support") != "supported" or judgment.get("eligibility") != "usable"
                    or judgment.get("adoption", {}).get("status") != "adopted"
                    or judgment.get("adoption", {}).get("by") != judgment.get("owner")
                    or "planning_closure" not in judgment.get("intended_uses", [])):
                return self._result("not_ready", ["adopted_closure_scope_required"])
            context = {"intended_use": "planning_closure", "review_triggers": []}
            if isinstance(decision.get("material_context"), dict):
                context["material_context"] = decision["material_context"]
            result = AssessmentService(self.store).inspect_judgment(judgment, context)
            if result.get("status") != "compatible" or result.get("expected_support") != "supported":
                return self._result("not_ready", ["closure_conditions_not_supported"])
            supported.add(judgment["requirement_id"])
        if not set(need["requirement_ids"]).issubset(supported):
            return self._result("not_ready", ["closure_requirement_coverage"])
        return None

    def _prepare(self, request, require_authority):
        if (not isinstance(request, dict) or request.get("synthetic_only") is not True
                or request.get("action") not in {"accept", "dispose", "schedule", "shrink"}
                or not isinstance(request.get("decisions"), list) or not request["decisions"]
                or not all(isinstance(d, dict) and exact(d.get("need_ref")) for d in request["decisions"])):
            return None, self._result("rejected", ["finite_planning_request_required"])
        state = self.store.read_context()
        if state.get("status") != "ok":
            return None, self._result("blocked", ["planning_context_unavailable"])
        revision = state["state_revision"]
        initial_gate = self.store.validate_refs(list(object_refs(request)), "planning")
        if initial_gate.get("status") != "ok" or initial_gate.get("state_revision") != revision:
            return None, self._result("blocked", [p["code"] for p in initial_gate.get("reasons", [])] or ["context_changed"])
        if require_authority:
            problem = LearningStore._request_problems(request.get("expected_state_revision"), request.get("operation_id"))
            if problem:
                return None, self._result("rejected", [p["code"] for p in problem])
            retry = self._retry(request, revision)
            if retry:
                return None, retry
            if request["expected_state_revision"] != revision:
                return None, self._result("conflict", ["state_revision_conflict"], state_revision=revision)
        current = {o["id"]: o["revision"] for o in state["objects"]}
        decision_refs = [d["need_ref"] for d in request["decisions"]]
        if len({r["id"] for r in decision_refs}) != len(decision_refs):
            return None, self._result("rejected", ["one_decision_per_shared_need"])
        needs, problem = self._read(decision_refs, revision, "LearningNeed", current)
        if problem:
            return None, problem
        budget_ref = request.get("budget_ref")
        if not exact(budget_ref):
            return None, self._result("not_ready", ["one_shared_budget_required"])
        budgets, problem = self._read([budget_ref], revision, "BudgetEnvelope", current)
        if problem:
            return None, problem
        budget = budgets[0]
        capacity = amount(budget.get("user_active_time"))
        if capacity is None:
            return None, self._result("not_ready", ["known_active_budget_required"])
        if self.store.entry_actor != "AG1" and not (request["action"] == "shrink" and self.store.entry_actor == "AG0"):
            return None, self._result("candidate", ["ag1_formal_planning_required"])
        criteria, scope = [], {n["id"] for n in needs}
        for need in needs:
            goals, problem = self._read([need["goal_ref"]], revision, "GoalSpec", current)
            if problem:
                return None, problem
            valid = {r["requirement_id"] for r in goals[0].get("requirements", [])}
            if not strings(need.get("requirement_ids")) or not set(need["requirement_ids"]).issubset(valid):
                return None, self._result("not_ready", ["current_goal_need_required"])
            criteria.extend(dict(need["goal_ref"], locator="requirements/" + rid) for rid in need["requirement_ids"])
            scope.add(need["goal_ref"]["id"])
            if need.get("disposition", {}).get("status") in FINAL:
                return None, self._result("rejected", ["terminal_need_requires_new_professional_basis"])
        replacements = request.get("replace_commitment_refs", [])
        if not isinstance(replacements, list) or any(not exact(r) for r in replacements):
            return None, self._result("rejected", ["exact_replacement_refs_required"])
        previous = None
        if request["action"] == "shrink":
            records, problem = self._read([request.get("commitment_ref", {})], revision, "PlanCommitment", current)
            if problem:
                return None, problem
            previous = records[0]
            allowed = previous.get("allowed_adjustments", {})
            if (previous.get("status") != "active" or previous.get("budget_ref") != budget_ref
                    or not isinstance(allowed, dict) or "shrink" not in allowed.get("actions", [])
                    or not {n["id"] for n in needs}.issubset(allowed.get("need_ids", []))
                    or {n["id"] for n in needs} != {r["id"] for r in previous.get("need_refs", [])}
                    or not number(request.get("available_minutes"))):
                return None, self._result("candidate", ["authorized_local_shrink_required"])
            capacity = min(capacity, request["available_minutes"])
            replacements = [ref(previous)]
        active = [o for o in state["objects"] if o.get("type") == "PlanCommitment" and o.get("status") == "active" and o.get("budget_ref", {}).get("id") == budget["id"]]
        if any(ref(o) not in replacements for o in active) and request["action"] in {"schedule", "shrink"}:
            return None, self._result("rejected", ["unique_effective_arrangement_required"])
        old_plans = []
        if replacements:
            old_plans, problem = self._read(replacements, revision, "PlanCommitment", current)
            if problem:
                return None, problem
            if any(p.get("status") != "active" or p.get("budget_ref") != budget_ref or not {r["id"] for r in p.get("need_refs", [])}.issubset({n["id"] for n in needs}) for p in old_plans):
                return None, self._result("rejected", ["replacement_must_dispose_all_affected_needs"])
        if request["action"] == "dispose" and any(n.get("disposition", {}).get("status") in {"scheduled", "partially_scheduled"} for n in needs) and not replacements:
            return None, self._result("rejected", ["active_commitment_replacement_required"])
        spent = amount(request.get("spent_minutes"))
        reserve = request.get("reserve_minutes", 0)
        if request["action"] in {"schedule", "shrink"} and (spent is None or not number(reserve)):
            return None, self._result("not_ready", ["spent_and_reserve_declaration_required"])
        spent = 0 if spent is None else spent
        recorded_spent, problem = self._recorded_spent(state["objects"], budget_ref)
        if problem:
            return None, problem
        if request["action"] in {"schedule", "shrink"} and recorded_spent is not None and spent < recorded_spent:
            return None, self._result("not_ready", ["spent_time_below_saved_execution"])
        if old_plans and any(spent < p.get("metadata", {}).get("planning", {}).get("spent_minutes", 0) for p in old_plans):
            return None, self._result("rejected", ["spent_time_cannot_regress"])
        allocations, updates, all_basis, cost_total, estimated = [], [], [budget_ref], 0, False
        non_user = {k: 0 for k in ("blocked_wait", "system_effort", "fees")}
        for decision, original in zip(request["decisions"], needs):
            status = "pending" if request["action"] == "accept" else decision.get("status")
            if ((request["action"] != "accept" and status not in OUTCOMES)
                    or not all(text(decision.get(k)) for k in ("reason", "uncovered_impact", "next_trigger"))):
                return None, self._result("rejected", ["substantive_disposition_required"])
            if request["action"] == "accept" and original.get("disposition", {}).get("status") != "pending":
                return None, self._result("rejected", ["acceptance_is_not_a_new_disposition"])
            need = copy.deepcopy(original)
            need.update(revision=original["revision"] + 1, owner=self.store.entry_actor,
                        acceptance={"status": "accepted", "by": self.store.entry_actor, "scope": decision["reason"], "next_trigger": decision["next_trigger"]},
                        disposition={"status": status, "reason": decision["reason"], "commitment_refs": []},
                        uncovered_impact=decision["uncovered_impact"], next_trigger=decision["next_trigger"])
            if status in {"scheduled", "partially_scheduled"}:
                if request["action"] not in {"schedule", "shrink"}:
                    return None, self._result("rejected", ["schedule_action_required"])
                activity, problem = self._activity(decision, original, budget, revision, current)
                if problem:
                    return None, problem
                costing, code = self._cost(decision.get("cost"))
                if code:
                    return None, self._result("not_ready", [code])
                if status == "scheduled" and set(decision["requirement_ids"]) != set(original["requirement_ids"]):
                    return None, self._result("rejected", ["full_schedule_coverage_required"])
                if previous:
                    prior = next((a for a in previous.get("metadata", {}).get("planning", {}).get("allocations", []) if a["need_ref"]["id"] == original["id"]), None)
                    if (not prior or prior["activity_ref"] != decision["activity_ref"]
                            or not set(decision["operations"]).issubset(prior["operations"])
                            or not set(decision["requirement_ids"]).issubset(prior["requirement_ids"])
                            or exceeds(costing["minutes"], prior["active_minutes"])
                            or decision.get("material_context") != prior["material_context"]):
                        return None, self._result("candidate", ["local_shrink_must_preserve_design"])
                    if any(exceeds(amount(decision["cost"][key], "amount" if key == "fees" else "minutes") or 0,
                                   amount(prior["cost"][key], "amount" if key == "fees" else "minutes") or 0)
                           for key in non_user):
                        return None, self._result("candidate", ["local_shrink_must_preserve_design"])
                for key in non_user:
                    non_user[key] += amount(decision["cost"][key], "amount" if key == "fees" else "minutes") or 0
                cost_total += costing["minutes"]
                estimated |= costing["estimated"]
                allocations.append({"need_ref": ref(need), "activity_ref": ref(activity),
                                    "requirement_ids": decision["requirement_ids"], "operations": decision["operations"],
                                    "scope": decision["scope"], "cost": copy.deepcopy(decision["cost"]),
                                    "active_minutes": costing["minutes"], "material_context": copy.deepcopy(decision["material_context"]),
                                    "readiness": copy.deepcopy(decision["readiness"]),
                                    "strategy_context": copy.deepcopy(decision.get("strategy_context"))})
                all_basis.extend([ref(activity), *activity.get("material_refs", [])])
            elif previous and status not in {"deferred", "returned"}:
                return None, self._result("candidate", ["local_shrink_cannot_close_or_merge_need"])
            elif status == "closed":
                problem = self._close(decision, original, revision, current)
                if problem:
                    return None, problem
                need["basis_refs"] += decision["evidence_refs"]
                need["judgment_refs"] = copy.deepcopy(decision["evidence_refs"])
                all_basis += decision["evidence_refs"]
            elif status == "merged":
                target_ref, mapping = decision.get("merge_target_ref"), decision.get("requirement_mapping")
                targets, problem = self._read([target_ref or {}], revision, "LearningNeed", current)
                if problem:
                    return None, problem
                target = targets[0]
                if (target["id"] == original["id"] or target.get("disposition", {}).get("status") in FINAL
                        or target["goal_ref"] != original["goal_ref"] or target["conditions"] != original["conditions"]
                        or target["parent_task"] != original["parent_task"] or not isinstance(mapping, dict)
                        or set(mapping) != set(original["requirement_ids"])
                        or not set(original["requirement_ids"]).issubset(target["requirement_ids"])
                        or any(mapping[rid] != [rid] for rid in original["requirement_ids"])):
                    return None, self._result("not_ready", ["merge_must_preserve_requirement_conditions"])
                if any(d["need_ref"]["id"] == target["id"] and d.get("status") in {"merged", "closed", "no_further_investment"} for d in request["decisions"]):
                    return None, self._result("rejected", ["merge_target_must_remain_live"])
                updated_target = next((dict(r, revision=r["revision"] + 1) for r in decision_refs if r["id"] == target["id"]), target_ref)
                need["disposition"].update(merge_target_ref=updated_target, requirement_mapping=copy.deepcopy(mapping))
            updates.append(need)
            all_basis.extend([need["goal_ref"], *need.get("judgment_refs", [])])
        if request["action"] == "schedule" and not allocations:
            return None, self._result("rejected", ["finite_allocation_required"])
        if estimated and (reserve <= 0 or not text(request.get("uncertainty_reason"))):
            return None, self._result("not_ready", ["estimated_cost_needs_reserve"])
        if exceeds(spent + cost_total + reserve, capacity):
            return None, self._result("not_ready", ["shared_budget_exceeded"])
        for key, used in non_user.items():
            if used > 0 and ((limit := amount(budget.get(key), "amount" if key == "fees" else "minutes")) is None or used > limit):
                return None, self._result("not_ready", ["shared_non_user_budget_exceeded"])
        if previous and exceeds(spent + cost_total + reserve, previous.get("metadata", {}).get("planning", {}).get("allocation_ceiling_minutes", -1)):
            return None, self._result("candidate", ["local_shrink_cannot_expand_budget"])
        alternatives = request.get("alternatives", [])
        if (len(request["decisions"]) > 1 or replacements) and (not isinstance(alternatives, list) or not alternatives or any(not isinstance(a, dict) or not text(a.get("scope")) or not text(a.get("consequence")) for a in alternatives)):
            return None, self._result("not_ready", ["real_alternative_consequence_required"])
        changes = updates[:]
        checkpoint = request.get("checkpoint_ref")
        if checkpoint is not None:
            graph, problem = self._graph([checkpoint], revision, current)
            if problem:
                return None, problem
            cp = graph[(checkpoint["id"], checkpoint["revision"])]
            if cp.get("type") != "SessionCheckpoint" or cp.get("budget_ref") != budget_ref or (allocations and cp.get("activity_ref") not in [a["activity_ref"] for a in allocations]):
                return None, self._result("not_ready", ["checkpoint_scope_budget_mismatch"])
            all_basis.append(checkpoint)
        plan = None
        if request["action"] in {"schedule", "shrink"}:
            identifier = previous["id"] if previous else request.get("plan_id")
            if not text(identifier) or not identifier.startswith("FIX-") or (not previous and identifier in current):
                return None, self._result("rejected", ["new_fixture_plan_id_required"])
            scope.add(identifier)
            scope.update(a["activity_ref"]["id"] for a in allocations)
            basis = list({(r["id"], r["revision"]): r for r in all_basis}.values())
            plan = {"type": "PlanCommitment", "id": identifier, "revision": previous["revision"] + 1 if previous else 1,
                    "owner": self.store.entry_actor, "schema_version": PROTOCOL, "basis_refs": basis,
                    "goal_refs": list({n["goal_ref"]["id"]: n["goal_ref"] for n in updates}.values()),
                    "need_refs": [ref(n) for n in updates if n["disposition"]["status"] in {"scheduled", "partially_scheduled"}]
                                 if allocations else [ref(n) for n in updates if n["disposition"]["status"] not in FINAL],
                    "executable_scope": [a["scope"] for a in allocations],
                    "adopted_basis_refs": basis, "budget_ref": budget_ref,
                    "authorization_refs": copy.deepcopy(request.get("authorization_refs", [])),
                    "allowed_adjustments": copy.deepcopy(previous["allowed_adjustments"] if previous else request.get("allowed_adjustments", {})),
                    "unselected_consequences": [{"scope": n["needed_work"], "consequence": n["uncovered_impact"]} for n in updates] + copy.deepcopy(alternatives),
                    "checkpoint_ref": checkpoint if checkpoint is not None else fact("unknown", "Only saved events may establish a recovery point."),
                    "next_trigger": request.get("next_trigger", updates[0]["next_trigger"]),
                    "status": "active" if allocations else "stopped", "decision_type": "plan_adjustment" if previous else "planning",
                    "criterion_refs": list({json.dumps(c, sort_keys=True): c for c in criteria}.values()),
                    "metadata": {"planning": {"version": VERSION, "formal_owner": "AG1", "allocations": allocations,
                                               "spent_minutes": spent, "reserved_minutes": reserve,
                                               "allocation_ceiling_minutes": spent + cost_total + reserve,
                                               "unallocated_minutes": capacity - spent - cost_total - reserve,
                                               "non_user_totals": non_user,
                                               "uncertainty_reason": request.get("uncertainty_reason", "bounded work"),
                                               "effect": "not_verified", "calendar_conditions": "not_inferred"}}}
            changes.append(plan)
            for n in updates:
                if n["disposition"]["status"] in {"scheduled", "partially_scheduled"}:
                    n["disposition"]["commitment_refs"] = [ref(plan)]
        for old in old_plans:
            if previous and old["id"] == previous["id"]:
                continue
            old = copy.deepcopy(old)
            old.update(revision=old["revision"] + 1, owner=self.store.entry_actor, status="superseded",
                       decision_type="planning", need_refs=[ref(n) for n in updates if n["id"] in {r["id"] for r in old["need_refs"]}])
            old["basis_refs"] = [budget_ref, *[n["goal_ref"] for n in updates]]
            old["adopted_basis_refs"] = old["basis_refs"]
            old["authorization_refs"] = copy.deepcopy(request.get("authorization_refs", []))
            old["metadata"] = {"planning": {"superseded": True, "next_owner": "AG1", "next_trigger": updates[0]["next_trigger"]}}
            changes.append(old)
        authority = self._authority(request, revision, current, criteria, scope, budget_ref)
        if require_authority and authority:
            return None, authority
        return {"changes": changes, "revision": revision, "plan": plan, "authority": authority,
                "total_minutes": spent + cost_total + reserve, "budget_ref": budget_ref}, None

    def inspect(self, request):
        try:
            prepared, problem = self._prepare(request, False)
            if problem:
                return problem
            return self._result("candidate", changes=prepared["changes"],
                                total_active_minutes=prepared["total_minutes"],
                                authorized=prepared["authority"] is None,
                                next_action="explicit_planning_submit")
        except (TypeError, ValueError, KeyError, AttributeError, IndexError):
            return self._result("rejected", ["invalid_planning_packet"])

    def run(self, request):
        try:
            prepared, problem = self._prepare(request, True)
            if problem:
                return problem
            changes = prepared["changes"]
            output_refs = [ref(o) for o in changes]
            receipt = {"operation_id": request["operation_id"], "request_digest": digest(request),
                       "output_refs": output_refs, "committed_state_revision": prepared["revision"] + 1}
            for record in changes:
                record.setdefault("metadata", {}).setdefault("planning", {}).update(receipt)
            result = self.store.commit(request["expected_state_revision"], request["operation_id"], changes,
                                       authorization_refs=request.get("authorization_refs", []),
                                       adoption_refs=request.get("authorization_refs", []))
            return self._result(result["status"], state_revision=result.get("state_revision"),
                                reasons=result.get("reasons", []), mutated=result["status"] == "committed",
                                output_refs=output_refs if result["status"] == "committed" else [], replayed=False)
        except (TypeError, ValueError, KeyError, AttributeError, IndexError):
            return self._result("rejected", ["invalid_planning_packet"])

    def resume(self, commitment_ref):
        """Read the current arrangement and trusted checkpoint without replanning."""
        try:
            state = self.store.read_context()
            if state.get("status") != "ok" or not exact(commitment_ref):
                return self._result("blocked", ["current_commitment_required"])
            current = {o["id"]: o["revision"] for o in state["objects"]}
            records, problem = self._read([commitment_ref], state["state_revision"], "PlanCommitment", current)
            if problem:
                return problem
            plan = records[0]
            graph, problem = self._graph([commitment_ref], state["state_revision"], current)
            if problem:
                return problem
            if plan.get("status") != "active":
                return self._result("stopped", ["commitment_not_active"])
            active = [o for o in state["objects"] if o.get("type") == "PlanCommitment" and o.get("status") == "active" and o.get("budget_ref", {}).get("id") == plan["budget_ref"]["id"]]
            if len(active) != 1:
                return self._result("blocked", ["unique_effective_arrangement_required"])
            saved = plan.get("metadata", {}).get("planning", {})
            budget = graph.get((plan["budget_ref"]["id"], plan["budget_ref"]["revision"]))
            if amount(budget.get("user_active_time")) is None or saved.get("allocation_ceiling_minutes", math.inf) > amount(budget["user_active_time"]):
                return self._result("not_ready", ["current_budget_requires_reconsideration"])
            recorded_spent, problem = self._recorded_spent(state["objects"], plan["budget_ref"])
            if problem:
                return problem
            if recorded_spent is not None and recorded_spent > saved.get("spent_minutes", 0):
                return self._result("not_ready", ["saved_execution_requires_plan_reconsideration"])
            for allocation in saved.get("allocations", []):
                need = graph.get((allocation["need_ref"]["id"], allocation["need_ref"]["revision"]))
                if not need:
                    return self._result("not_ready", ["current_need_required"])
                _, problem = self._activity(allocation, need, budget, state["state_revision"], current)
                if problem:
                    return problem
            cp_ref = plan.get("checkpoint_ref")
            cp = graph.get((cp_ref["id"], cp_ref["revision"])) if exact(cp_ref) else None
            # No summary manufactures success or unseen help; confirmed originals stay canonical.
            recovery = ({"checkpoint_ref": cp_ref, "parent_artifact": cp["parent_artifact"],
                         "last_trusted_event_ref": cp["last_trusted_event_ref"], "help_history_refs": cp["help_history_refs"],
                         "next_connection": cp["next_connection"], "unrecorded_actions": cp["unrecorded_actions"]} if cp else
                        {"status": "limited", "unrecorded_actions": fact("unknown", "No confirmed checkpoint supplied."),
                         "next_connection": "Use only saved activity and performance events; confirm only a consequential unknown."})
            return self._result("ready", state_revision=state["state_revision"], commitment_ref=commitment_ref,
                                allocations=copy.deepcopy(saved.get("allocations", [])), recovery=recovery,
                                budget_ref=plan["budget_ref"], replanned=False, new_required_checks=0)
        except (TypeError, ValueError, KeyError, AttributeError, IndexError):
            return self._result("rejected", ["invalid_resume_packet"])


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--actor", choices=("AG1", "AG0"), default="AG1")
    parser.add_argument("--request", required=True)
    parser.add_argument("--inspect", action="store_true")
    args = parser.parse_args()
    try:
        request = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
        service = PlanningService(LearningStore(args.workspace, entry_actor=args.actor))
        result = service.inspect(request) if args.inspect else service.run(request)
    except (OSError, ValueError):
        result = PlanningService._result("rejected", ["request_file_unavailable"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"candidate", "committed", "ready"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
