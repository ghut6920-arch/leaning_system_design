"""Finite Encoding/Post declarations on the existing C0 event and store.

The model designs and reviews content. This layer checks references and scope,
preserves actual support, and never turns module progress into a Judgment.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.b3_semantics import known_bool, task_checks
from runtime.contract_rules import load_definition, object_refs, walk
from runtime.learning_store import LearningStore
from runtime.learning_teaching import (
    TeachingService, READ_ACTIONS, WRITE_ACTIONS, QUALIFICATIONS,
    exact_ref, fact, ref, issue, strings, declared_minutes,
)

VERSION = "pl-teaching-b4/0.1.0"
MODULES = {"encoding", "post"}
ROUTES = {"explain", "goal_work", "withdraw_help", "conditions", "whole",
          "enter_encoding", "enter_post", "end", "change_route",
          "return_local", "hold_for_review"}
LOCAL_ACTIONS = {"enter_local", "return_local"}


def text_present(value):
    return isinstance(value, str) and bool(value.strip())


class SpecializedTeachingService(TeachingService):
    """Same serial fixture entry as C0, with explicit design and module scopes."""

    @staticmethod
    def _result(status, **extra):
        return TeachingService._result(status, specialization_version=VERSION, **extra)

    def _spec(self, activity):
        spec = activity.get("metadata", {}).get("b4")
        if not isinstance(spec, dict) or spec.get("version") != VERSION or spec.get("module") not in MODULES:
            return None, self._reject("specialized_activity_required", "not_ready")
        if not all(text_present(spec.get(k)) for k in ("work", "needed_structure")) or not strings(spec.get("acceptable_products"), True):
            return None, self._reject("content_work_description_required")
        transform = spec.get("change_and_hold")
        if not isinstance(transform, dict) or any(not strings(transform.get(k)) for k in ("change", "hold", "allowed_additions")):
            return None, self._reject("legal_change_and_hold_required")
        if spec["module"] == "post" and spec.get("post_function") not in {"recovery", "integration", "selection", "update"}:
            return None, self._reject("post_function_required")
        branches, routes = activity.get("branches"), spec.get("branch_routes")
        if not isinstance(branches, list) or not branches or not isinstance(routes, list) or len(routes) != len(branches) or any(r not in ROUTES for r in routes):
            return None, self._reject("prepared_branch_routes_required")
        if any(not isinstance(b, dict) or not all(text_present(b.get(k)) for k in ("observation", "action", "next_observation", "counterevidence", "stop")) for b in branches):
            return None, self._reject("content_branch_required")
        if type(spec.get("whole_required")) is not bool:
            return None, self._reject("explicit_whole_scope_required")
        references, obligations = spec.get("whole_reference_refs"), spec.get("whole_obligations")
        if not isinstance(references, list) or any(not exact_ref(r) for r in references) or not strings(obligations):
            return None, self._reject("whole_review_scope_required")
        if spec["whole_required"] and (not references or not obligations):
            return None, self._reject("whole_reference_unavailable", "not_ready", next_owner="AG2")
        interfaces = spec.get("interfaces", [])
        if not isinstance(interfaces, list) or any(not isinstance(i, dict) or not all(text_present(i.get(k)) for k in ("input", "output", "conditions", "reliable_properties", "internal_unknown")) for i in interfaces):
            return None, self._reject("bounded_interface_required")
        return copy.deepcopy(spec), None

    def _prepare(self, request):
        prepared, problem = super()._prepare(request)
        if problem:
            return None, problem
        spec, problem = self._spec(prepared["activity"])
        if problem:
            return None, problem
        problem = self._goal_scope(prepared["activity"], spec, prepared["state_revision"])
        if problem:
            return None, problem
        problem = self._whole_basis(prepared["activity"], spec, prepared["state_revision"])
        if problem:
            return None, problem
        prepared["specialization"] = spec
        return prepared, None

    def _goal_scope(self, activity, spec, state, use="teaching_execution"):
        goals, problem = self._read(activity["goal_refs"], state, use)
        if problem:
            return problem
        index = {g["id"]: g for g in goals}
        whole_ops, whole_obligations = set(), set()
        for criterion in activity["criterion_refs"]:
            goal = index.get(criterion.get("id"))
            requirement = next((r for r in goal.get("requirements", []) if r.get("requirement_id") == criterion.get("locator", "").split("/", 1)[-1]), None) if goal else None
            scope = requirement.get("teaching_scope") if requirement else None
            if not isinstance(scope, dict) or type(scope.get("whole_required")) is not bool or not strings(scope.get("whole_obligations")):
                return self._reject("goal_teaching_scope_required", "not_ready", next_owner="AG1")
            if scope["whole_required"]:
                if not scope["whole_obligations"]:
                    return self._reject("goal_whole_obligations_required", "not_ready", next_owner="AG1")
                whole_ops.update(requirement["key_operations"])
                whole_obligations.update(scope["whole_obligations"])
        if whole_ops:
            if not spec["whole_required"]:
                if spec.get("goal_coverage") != "local_only" or not set(activity["learner_operations"]) < whole_ops:
                    return self._reject("goal_whole_scope_cannot_be_lowered", "not_ready")
            elif not whole_obligations.issubset(spec["whole_obligations"]):
                return self._reject("goal_whole_obligations_not_covered", "not_ready")
        return None

    def _whole_basis(self, activity, spec, state, use="teaching_execution"):
        if not spec["whole_required"]:
            return self._guard(spec["whole_reference_refs"], state, use)
        records, problem = self._read(spec["whole_reference_refs"], state, use)
        if problem:
            return problem
        latest = self.store.read_context()
        if latest.get("state_revision") != state:
            return self._reject("context_changed", "blocked")
        current = {(o["id"], o["revision"]) for o in latest["objects"]}
        covered_ops, covered_obligations = set(), set()
        for record in records:
            content = record.get("verification", {}).get("content", {})
            coverage = content.get("whole_coverage", {})
            if ((record["id"], record["revision"]) not in current
                    or record.get("type") not in {"MaterialUse", "SourceFragment"}
                    or content.get("status") != "supported"
                    or content.get("checked_revision") != record["revision"]
                    or not isinstance(coverage, dict) or coverage.get("status") != "supported"
                    or not strings(coverage.get("target_operations"), True)
                    or not strings(coverage.get("obligations"), True)
                    or coverage.get("goal_refs") != activity.get("goal_refs")
                    or not isinstance(coverage.get("criterion_refs"), list)
                    or any(c not in coverage["criterion_refs"] for c in activity.get("criterion_refs", []))
                    or not isinstance(coverage.get("anchor_refs"), list) or not coverage["anchor_refs"]):
                continue
            problem = self._guard(coverage["anchor_refs"], state, use)
            if problem:
                return problem
            covered_ops.update(coverage["target_operations"])
            covered_obligations.update(coverage["obligations"])
        if not set(activity["learner_operations"]).issubset(covered_ops) or not set(spec["whole_obligations"]).issubset(covered_obligations):
            return self._reject("whole_reference_coverage_required", "not_ready", next_owner="AG2")
        return None

    def _commit(self, request, changes, artifacts=None, **extra):
        # Enrich an initial C0 event before its one atomic commit. No follow-up
        # metadata transaction, extra answer, or extra independent sample.
        changes = copy.deepcopy(changes)
        for obj in changes:
            if obj.get("type") == "PerformanceEvent" and obj.get("revision") == 1 and "c0" in obj:
                state = self.store.read_refs([obj["activity_ref"]], "teaching_execution")
                if state.get("status") != "ok":
                    return self._reject("specialized_basis_unavailable", "blocked")
                spec, problem = self._spec(state["objects"][0])
                if problem:
                    return problem
                obj.setdefault("metadata", {})["b4"] = {
                    "version": VERSION, "module": spec["module"], "stack": [],
                    "transition_history": [], "overall_support": "not_assessed",
                }
        return super()._commit(request, changes, artifacts, **extra)

    def _graph(self, refs, state, use):
        """Exact historical evidence remains historical; controls are current."""
        pending, seen, records = list(refs), set(), []
        while pending:
            batch = []
            for r in pending:
                if not exact_ref(r):
                    return None, self._reject("exact_basis_references_required")
                key = r["id"], r["revision"]
                if key not in seen:
                    seen.add(key)
                    batch.append(r)
            if not batch:
                break
            objects, problem = self._read(batch, state, use)
            if problem:
                return None, problem
            pending = []
            for obj in objects:
                records.append(obj)
                pending.extend(object_refs(obj))
                artifacts = [item for item in walk(obj) if isinstance(item, dict) and {"path", "locator", "origin"}.issubset(item)]
                problem = self._guard([ref(obj)] + artifacts, state, use)
                if problem:
                    return None, problem
        return records, None

    def _design(self, request, commit=False):
        if self.store.entry_actor != "AG1":
            return self._reject("ag1_design_actor_required")
        state = self.store.read_context()
        if state.get("status") != "ok" or not state.get("synthetic_only"):
            return self._reject("synthetic_workspace_unavailable", "blocked")
        activity = request.get("activity")
        if not isinstance(activity, dict) or activity.get("type") != "ActivitySpec" or activity.get("owner") != "AG1":
            return self._reject("ag1_activity_candidate_required")
        required = load_definition()["base_required"] + load_definition()["objects"]["ActivitySpec"]["required"]
        if any(k not in activity for k in required) or not exact_ref(ref(activity)) or not activity["id"].startswith("FIX-"):
            return self._reject("complete_activity_candidate_required")
        spec, problem = self._spec(activity)
        if problem:
            return problem
        checks = task_checks(activity)
        if not strings(activity.get("learner_operations"), True) or not strings(checks["target_operations"], True) or not set(activity["learner_operations"]).issubset(checks["target_operations"]) or checks["conflicts"] or any(not known_bool(checks[k]) for k in QUALIFICATIONS):
            return self._reject("task_qualification_required", "not_ready")
        current = {(o["id"], o["revision"]): o for o in state["objects"]}
        refs = list(object_refs(activity))
        records, problem = self._graph(refs, state["state_revision"], "teaching_design")
        if problem:
            return problem
        index = {(o["id"], o["revision"]): o for o in records}
        for field, kind in (("goal_refs", "GoalSpec"), ("material_refs", "MaterialUse")):
            if not isinstance(activity.get(field), list) or not activity[field]:
                return self._reject("current_design_basis_required")
            for r in activity[field]:
                basis = current.get((r.get("id"), r.get("revision")))
                if not basis or basis.get("type") != kind or ("adoption" in basis and basis["adoption"].get("status") not in {"adopted", "partially_adopted"}):
                    return self._reject("current_adopted_design_basis_required", "not_ready")
        criteria = activity.get("criterion_refs")
        if not isinstance(criteria, list) or not criteria:
            return self._reject("design_criteria_required")
        for c in criteria:
            goal = index.get((c.get("id"), c.get("revision")))
            if {"id": c.get("id"), "revision": c.get("revision")} not in activity["goal_refs"] or not goal or not str(c.get("locator", "")).startswith("requirements/") or not any(r.get("requirement_id") == c["locator"].split("/", 1)[1] for r in goal.get("requirements", [])):
                return self._reject("criterion_binding_mismatch")
        budget = current.get((activity["budget_ref"].get("id"), activity["budget_ref"].get("revision")))
        if not budget or budget.get("type") != "BudgetEnvelope" or activity["id"] not in budget.get("allocation_scope", []):
            return self._reject("shared_design_budget_required", "not_ready")
        if not isinstance(request.get("context"), dict) or request["context"].get("activity_ref") != ref(activity) or request["context"].get("goal_refs") != activity["goal_refs"]:
            return self._reject("design_material_context_required")
        problem = self._goal_scope(activity, spec, state["state_revision"], "teaching_design")
        if problem:
            return problem
        problem = self._whole_basis(activity, spec, state["state_revision"], "teaching_design")
        if problem:
            return problem
        if not activity.get("reference_refs") or not strings(activity.get("stop_conditions"), True) or not activity.get("return_conditions"):
            return self._reject("reliable_reference_and_exit_required")
        if not commit:
            candidate = copy.deepcopy(activity)
            candidate["adoption"] = {"status": "candidate"}
            return self._result("candidate", state_revision=state["state_revision"], activity_candidate=candidate,
                                execution_readiness="requires_adoption_and_current_c0_checks", professional_correctness="declared_not_proven")
        adoption = activity.get("adoption", {})
        if activity.get("decision_type") != "teaching_design" or adoption.get("status") != "adopted" or adoption.get("by") != "AG1" or not adoption.get("basis_refs"):
            return self._reject("explicit_ag1_adoption_required")
        return self._commit(request, [activity], activity_ref=ref(activity), execution_readiness="requires_current_c0_checks")

    def _observation(self, observation, event, state, after=None):
        if not isinstance(observation, dict) or not text_present(observation.get("quote")):
            return None, self._reject("locatable_observation_required")
        anchor = observation.get("artifact_ref")
        entries = [e for e in event["timeline"] if e.get("kind") in {"initial_response", "revision"} and e.get("artifact_ref") == anchor and (after is None or e["sequence"] > after)]
        if not entries:
            return None, self._reject("event_response_observation_required")
        text, problem = self._artifact(anchor, {}, state)
        if problem:
            return None, problem
        if observation["quote"] not in text or observation["quote"] not in entries[-1]["content"]:
            return None, self._reject("observation_quote_not_locatable")
        return entries[-1], None

    def _select(self, request, prepared):
        event, problem = self._event(request, prepared)
        if problem:
            return problem
        index = request.get("branch_index")
        if type(index) is not int or not 0 <= index < len(prepared["activity"]["branches"]):
            return self._reject("prepared_branch_index_required")
        entry, problem = self._observation(request.get("observation"), event, prepared["state_revision"])
        if problem:
            return problem
        return self._result("candidate", route=prepared["specialization"]["branch_routes"][index],
                            branch=copy.deepcopy(prepared["activity"]["branches"][index]),
                            event_ref=ref(event), response_point={"event_ref": ref(event), "kind": entry["kind"], "sequence": entry["sequence"]},
                            factual_conditions=self._help_conditions(event), diagnostic_status="not_created", next_action_adopted=False)

    def _transition(self, request, prepared, returning=False):
        event, problem = self._event(request, prepared)
        if problem:
            return problem
        extension = event.get("metadata", {}).get("b4")
        if not isinstance(extension, dict) or extension.get("version") != VERSION:
            return self._reject("specialized_event_required")
        sequence = event["timeline"][-1]["sequence"] + 1
        if returning:
            if not extension["stack"]:
                return self._reject("local_return_frame_required")
            frame = extension["stack"][-1]
            if request.get("return_connection") != frame["return_connection"]:
                return self._reject("same_local_return_required")
            if request.get("local_outcome") not in {"sufficient", "no_progress", "contradicted"} or request.get("parent_outcome") not in {"not_observed", "still_blocked"}:
                return self._reject("separate_local_and_parent_outcomes_required")
            entry, problem = self._observation(request.get("local_observation"), event, prepared["state_revision"], frame["entry_sequence"])
            if problem:
                return problem
            extension["stack"].pop()
            extension["module"] = frame["from_module"]
            change = {"kind": "return_local", "sequence": sequence, "module": extension["module"],
                      "parent_frame": frame, "local_outcome": request["local_outcome"],
                      "local_response_sequence": entry["sequence"], "parent_outcome": request["parent_outcome"],
                      "overall_support": "not_assessed", "goal_conditions": "not_reassessed"}
            connection = frame["return_connection"]
            next_action = "review_interfaces_or_close" if request["parent_outcome"] == "still_blocked" or request["local_outcome"] != "sufficient" else "resume_same_parent_work"
        else:
            local = request.get("local")
            if not isinstance(local, dict) or local.get("module") not in MODULES or local["module"] == extension["module"]:
                return self._reject("different_local_module_required")
            allowed_operations = extension["stack"][-1]["operations"] if extension["stack"] else prepared["activity"]["learner_operations"]
            if not strings(local.get("operations"), True) or not set(local["operations"]).issubset(set(allowed_operations)) or not all(text_present(local.get(k)) for k in ("reason", "blocker", "local_sufficiency", "return_connection")) or not strings(local.get("alternative_explanations"), True):
                return self._reject("bounded_local_scope_required")
            support_refs = local.get("preserved_support_refs")
            if not isinstance(support_refs, list) or any(not exact_ref(r) for r in support_refs):
                return self._reject("preserved_support_references_required")
            _, problem = self._graph(support_refs, prepared["state_revision"], "teaching_execution")
            if problem:
                return problem
            entry, problem = self._observation(local.get("observation"), event, prepared["state_revision"])
            if problem:
                return problem
            # A new explanation of the same old response is not new evidence.
            # Returning removes the active frame, but not this scope's history.
            observation_floor = extension["stack"][-1]["entry_sequence"] if extension["stack"] else 0
            for previous in extension["transition_history"]:
                frame = previous.get("frame", previous.get("parent_frame", {}))
                if set(frame.get("operations", [])) == set(local["operations"]):
                    observation_floor = max(observation_floor, previous["sequence"])
            if entry["sequence"] <= observation_floor:
                return self._reject("new_local_observation_required", "not_ready", next_action="change_route_or_close")
            supplied = local.get("premises_supplied")
            if not known_bool(supplied) and not known_bool(supplied, False):
                return self._reject("explicit_premise_condition_required")
            if extension["module"] == "post" and local["module"] == "encoding":
                prior_help = [e for e in event["timeline"] if e.get("kind") in {"help", "feedback", "exposure"} and e.get("visibility") == "displayed" and e["sequence"] < entry["sequence"]]
                if not known_bool(supplied) or not prior_help or entry["kind"] != "revision":
                    return self._reject("post_rebuild_requires_observation_after_supplied_premises")
            frame = {"from_module": extension["module"], "module": local["module"],
                     "parent_activity_ref": ref(prepared["activity"]), "parent_artifact": copy.deepcopy(entry["artifact_ref"]),
                     "parent_task": copy.deepcopy(prepared["activity"]["parent_task"]),
                     "budget_ref": ref(prepared["budget"]), "entry_sequence": sequence,
                     **{k: copy.deepcopy(local[k]) for k in ("operations", "reason", "blocker", "local_sufficiency", "return_connection", "alternative_explanations", "preserved_support_refs", "premises_supplied", "observation")}}
            extension["stack"].append(frame)
            extension["module"] = local["module"]
            change = {"kind": "enter_local", "sequence": sequence, "frame": copy.deepcopy(frame)}
            connection, next_action = local["return_connection"], "perform_declared_local_work"
        extension["transition_history"].append(change)
        event["timeline"].append({"kind": change["kind"], "sequence": sequence, "visibility": "backend_reference",
                                  "content": connection, "target_operations": [], "substituted_operations": [],
                                  "time": fact("unknown", "Module control is not a declared learner response time.")})
        event["revision"] += 1
        event["c0"]["declared_active_minutes"] = declared_minutes(request, event)
        return self._commit(request, [event], event_ref=ref(event), specialization=extension,
                            factual_conditions=self._help_conditions(event), next_action=next_action,
                            parent_artifact=frame["parent_artifact"], overall_support="not_assessed")

    def _whole(self, request, prepared):
        event_ref = request.get("event_ref")
        if not exact_ref(event_ref):
            return self._reject("event_reference_required")
        events, problem = self._read([event_ref], prepared["state_revision"])
        if problem:
            return problem
        event = events[0]
        if event.get("type") != "PerformanceEvent" or event.get("activity_ref") != ref(prepared["activity"]):
            return self._reject("event_activity_mismatch")
        requirements = request.get("requirement_ids")
        if not strings(requirements, True) or not set(requirements).issubset(prepared["requirements"]) or not text_present(request.get("intended_use")):
            return self._reject("whole_requirement_scope_required")
        product = request.get("product_ref")
        entry = next((e for e in reversed(event["timeline"]) if e.get("kind") in {"initial_response", "revision"} and e.get("artifact_ref") == product), None)
        if entry is None:
            return self._reject("continuous_product_required")
        text, problem = self._artifact(product, {}, prepared["state_revision"])
        if problem:
            return problem
        handoff = self._assessment_handoff(event, entry, prepared["context"])
        handoff.update(decision_type="complex_product", requirement_ids=copy.deepcopy(requirements), intended_use=request["intended_use"])
        return self._result("ready_for_review", event_ref=ref(event), product_ref=copy.deepcopy(product),
                            continuous_product=text, whole_obligations=prepared["specialization"]["whole_obligations"],
                            whole_reference_refs=prepared["specialization"]["whole_reference_refs"],
                            factual_conditions=self._help_conditions(event), parent_help_conditions=prepared["parent_help_conditions"],
                            assessment_handoff=handoff, overall_support="not_assessed", next_owner="AG3")

    def _reuse(self, request):
        state = self.store.read_context()
        if state.get("status") != "ok" or not state.get("synthetic_only"):
            return self._reject("synthetic_workspace_unavailable", "blocked")
        goal_ref, requirements, judgments = request.get("goal_ref"), request.get("requirement_ids"), request.get("judgment_refs")
        intended = request.get("intended_use")
        if not exact_ref(goal_ref) or not strings(requirements, True) or not isinstance(judgments, list) or not judgments or any(not exact_ref(r) for r in judgments) or not text_present(intended):
            return self._reject("goal_requirement_and_judgment_scope_required")
        records, problem = self._graph([goal_ref] + judgments, state["state_revision"], intended)
        if problem:
            return problem
        current = {(o["id"], o["revision"]): o for o in state["objects"]}
        goal = current.get((goal_ref["id"], goal_ref["revision"]))
        if not goal or goal.get("type") != "GoalSpec":
            return self._reject("current_goal_required")
        if "adoption" in goal and goal["adoption"].get("status") != "adopted":
            return self._reject("current_adopted_goal_required", "not_ready")
        criteria = {r["requirement_id"]: r.get("criterion_revision") for r in goal["requirements"]}
        if not set(requirements).issubset(criteria):
            return self._reject("criterion_binding_mismatch")
        covered, used = set(), []
        for r in judgments:
            j = current.get((r["id"], r["revision"]))
            if not j or j.get("type") != "Judgment":
                return self._reject("current_judgment_required")
            requirement = j.get("requirement_id")
            if (j.get("goal_ref") == goal_ref and requirement in requirements
                    and j.get("criterion_revision") == criteria[requirement]
                    and j.get("support") == "supported" and j.get("eligibility") == "usable"
                    and j.get("adoption", {}).get("status") == "adopted"
                    and intended in j.get("intended_uses", []) and not j.get("counterevidence")):
                from runtime.learning_assessment import AssessmentService
                inspection = AssessmentService(self.store).inspect_judgment(j, {"intended_use": intended, "review_triggers": []})
                if inspection.get("status") == "blocked":
                    return self._result("blocked", reasons=inspection.get("reasons", []))
                if inspection.get("status") == "compatible":
                    covered.add(requirement)
                    used.append({"judgment_ref": ref(j), "conditions": copy.deepcopy(j["conditions"]), "unsupported_scope": copy.deepcopy(j["unsupported_scope"])})
        missing = sorted(set(requirements) - covered)
        return self._result("needs_work" if missing else "sufficient_for_declared_use", state_revision=state["state_revision"],
                            reused_judgments=used, unmet_requirement_ids=missing, intended_use=intended,
                            next_action="refer_existing_scope_to_planning" if not missing else "resolve_only_goal_required_gap",
                            permanent_mastery="not_claimed")

    def _resume(self, request, prepared):
        result = super()._resume(request, prepared)
        if result.get("status") == "ready":
            event_ref = result["recovery"]["last_trusted_event_ref"]
            events, problem = self._read([event_ref], prepared["state_revision"])
            if problem:
                return problem
            result["recovery"]["specialization"] = copy.deepcopy(events[0].get("metadata", {}).get("b4"))
        return result

    def run(self, request):
        if not isinstance(request, dict) or request.get("synthetic_only") is not True:
            return self._reject("synthetic_request_required")
        action = request.get("action")
        if action in READ_ACTIONS | WRITE_ACTIONS:
            return super().run(request)
        if action not in {"design", "commit_design", "select_branch", "review_whole", "reuse_evidence"} | LOCAL_ACTIONS:
            return self._reject("unknown_specialized_action")
        writing = action == "commit_design" or action in LOCAL_ACTIONS
        if writing and (type(request.get("expected_state_revision")) is not int or request["expected_state_revision"] < 0 or not text_present(request.get("operation_id"))):
            return self._reject("explicit_cas_operation_required")
        try:
            if action in {"design", "commit_design"}:
                return self._design(request, action == "commit_design")
            if self.store.entry_actor != "AG0":
                return self._reject("ag0_fixture_actor_required")
            if action == "reuse_evidence":
                return self._reuse(request)
            context_request = dict(request, action="resume") if action == "review_whole" else request
            prepared, problem = self._prepare(context_request)
            if problem:
                return problem
            if writing and not any(r in request.get("authorization_refs", []) for r in prepared["execution_authorization_refs"]):
                return self._reject("explicit_execution_authorization_required")
            if action == "select_branch":
                return self._select(request, prepared)
            if action == "review_whole":
                return self._whole(request, prepared)
            return self._transition(request, prepared, action == "return_local")
        except (KeyError, TypeError, ValueError, AttributeError, IndexError):
            return self._reject("invalid_specialized_request")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--actor", choices=["AG0", "AG1"], default="AG0")
    args = parser.parse_args(argv)
    try:
        request = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
        result = SpecializedTeachingService(LearningStore(args.workspace, entry_actor=args.actor)).run(request)
    except (OSError, ValueError):
        result = SpecializedTeachingService._result("rejected", reasons=[issue("request_file_unavailable")])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"ready", "candidate", "committed", "ready_for_review", "sufficient_for_declared_use"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
