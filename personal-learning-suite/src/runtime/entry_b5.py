"""B5 single-entry sequential integration of synthetic professional requests.

The caller supplies decisions, adoption, observations and grants. This adapter
connects exact returned references; it neither grades text nor authenticates roles.
There is no second journal: every saved fact remains in LearningStore.
"""
from __future__ import annotations

import copy
import sqlite3

from .contract_rules import object_refs, walk
from .learning_store import LearningStore

VERSION = "pl-entry/0.1.0"
OPERATIONS = {
    "goal.review", "goal.sources_submit", "goal.submit", "need.submit",
    "materials.read", "materials.inspect", "materials.submit",
    "strategies.inspect", "strategies.reuse", "strategies.submit",
    "teaching.run", "assessment.inspect", "assessment.diagnose",
    "assessment.submit", "assessment.routine_inspect", "assessment.routine_submit",
    "planning.inspect", "planning.run", "planning.resume",
}
WRITES = {"goal.sources_submit", "goal.submit", "need.submit", "materials.submit", "strategies.submit",
          "assessment.submit", "assessment.routine_submit", "planning.run"}
TEACHING_WRITES = {"record_initial", "record_help", "record_revision", "record_feedback",
                   "checkpoint", "close", "return_parent", "commit_design", "enter_local", "return_local"}
TEACHING_ACTIONS = TEACHING_WRITES | {"open", "resume", "design", "select_branch", "review_whole", "reuse_evidence"}
SUCCESS = {"committed", "compatible", "reusable", "ready", "ready_for_review", "sufficient_for_declared_use"}
RESERVED = {"expected_state_revision", "operation_id", "actor", "entry_actor"}
DECISIONS = {
    "GoalSpec": {"goal_design"},
    "SourceFragment": {"material_read", "material_review", "material_verification"},
    "MaterialUse": {"material_use", "material_review", "material_verification"},
    "MethodConfig": {"teaching_design", "strategy_configuration"},
    "Judgment": {"routine_scoring", "professional_review"},
    "DiagnosticNote": {"limited_diagnosis", "professional_review"},
}


def problem(code):
    return {"status": "rejected", "mutated": False, "reasons": [{"code": code}]}


def pointer_parts(path):
    if not isinstance(path, str) or not path.startswith("/") or "~" in path.replace("~0", "").replace("~1", ""):
        raise ValueError("invalid_pointer")
    return [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]


def pointer_get(value, path):
    for part in pointer_parts(path):
        if isinstance(value, list):
            if not part.isdecimal():
                raise ValueError("invalid_pointer_index")
            value = value[int(part)]
        elif isinstance(value, dict):
            value = value[part]
        else:
            raise ValueError("invalid_pointer_target")
    return value


def pointer_set(value, path, replacement):
    parts = pointer_parts(path)
    parent = value
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    key = int(parts[-1]) if isinstance(parent, list) else parts[-1]
    # A binding replaces an explicit placeholder; it never manufactures fields.
    parent[key]
    parent[key] = copy.deepcopy(replacement)


def owner_for(operation, request):
    if operation == "goal.sources_submit":
        return "AG2"
    if operation.startswith("goal.") or operation.startswith("strategies.") or operation == "need.submit":
        return "AG1"
    if operation.startswith("materials."):
        return "AG2"
    if operation.startswith("assessment."):
        return "AG0" if ".routine_" in operation else "AG3"
    if operation.startswith("planning."):
        return "AG0" if request.get("action") == "shrink" else "AG1"
    return "AG1" if request.get("action") in {"design", "commit_design"} else "AG0"


def is_write(step):
    return step["operation"] in WRITES or (step["operation"] == "teaching.run" and step["request"].get("action") in TEACHING_WRITES)


def successful(operation, result):
    if result.get("status") in SUCCESS:
        return True
    if result.get("status") == "limited":
        return operation.startswith("assessment.") and result.get("submission_ready") is True
    if result.get("status") == "candidate":
        return (operation == "goal.review" and result.get("review_state") == "complete") or operation in {"planning.inspect", "teaching.run", "materials.read"}
    return False


class SingleEntryService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _shape(request):
        if not isinstance(request, dict) or request.get("entry_version") != VERSION or request.get("synthetic_only") is not True:
            return "synthetic_entry_request_required"
        if type(request.get("expected_state_revision")) is not int or request["expected_state_revision"] < 0:
            return "explicit_entry_cas_required"
        if "actor" in request or "entry_actor" in request:
            return "actor_override_not_supported"
        steps = request.get("steps")
        if not isinstance(steps, list) or not 1 <= len(steps) <= 32:
            return "explicit_steps_required"
        seen, operations = set(), set()
        for step in steps:
            if not isinstance(step, dict) or set(step) - {"id", "operation", "request", "bindings"}:
                return "invalid_step"
            identifier, operation, packet = step.get("id"), step.get("operation"), step.get("request")
            if not isinstance(identifier, str) or not identifier.strip() or len(identifier) > 80 or identifier in seen:
                return "unique_step_id_required"
            if not isinstance(operation, str) or operation not in OPERATIONS or not isinstance(packet, dict):
                return "explicit_professional_request_required"
            if any(key in packet for key in {"actor", "entry_actor", "expected_state_revision"}):
                return "step_cas_or_actor_override"
            if operation == "teaching.run" and (not isinstance(packet.get("action"), str) or packet["action"] not in TEACHING_ACTIONS):
                return "unknown_teaching_action"
            if operation.startswith("planning.") and "action" in packet and not isinstance(packet["action"], str):
                return "invalid_planning_action"
            if is_write(step):
                op_id = packet.get("operation_id")
                if not isinstance(op_id, str) or not op_id.strip() or len(op_id) > 200 or "\0" in op_id or op_id in operations:
                    return "unique_explicit_operation_id_required"
                operations.add(op_id)
            bindings = step.get("bindings", {})
            if not isinstance(bindings, dict):
                return "invalid_bindings"
            try:
                for target, source in bindings.items():
                    parts = pointer_parts(target)
                    if any(part in RESERVED for part in parts) or parts[0] in {"action", "synthetic_only"}:
                        return "binding_cannot_change_control_fields"
                    pointer_get(packet, target)
                    if not isinstance(source, dict) or set(source) != {"step", "path"} or source["step"] not in seen:
                        return "binding_requires_previous_step"
                    pointer_parts(source["path"])
            except (KeyError, TypeError, ValueError, IndexError):
                return "invalid_binding_pointer"
            seen.add(identifier)
        return None

    def _goal(self, packet, operation, store):
        from .learning_goals import review_goal_package
        package = packet.get("package")
        # Check controls even for caller-supplied candidate definitions. Missing
        # new definitions may be reviewed, but deletion and pause are not bypassed.
        definitions = [o for o in walk(package) if isinstance(o, dict) and o.get("type") in {"GoalSpec", "SourceFragment"}]
        incoming = {(o.get("id"), o.get("revision")) for o in definitions}
        refs = list(object_refs(package))
        for obj in definitions:
            gate = store.validate_refs([{"id": obj.get("id"), "revision": obj.get("revision")}], "goal_design")
            reasons = [r for r in gate.get("reasons", []) if r.get("code") != "missing_reference"]
            if reasons or gate.get("status") == "not_saved":
                return {"status": "blocked", "reasons": reasons or [{"code": "goal_controls_unavailable"}]}
            if gate.get("status") == "ok":
                read = store.read_refs([{"id": obj["id"], "revision": obj["revision"]}], "goal_design")
                if read.get("status") != "ok":
                    return read
                actual = read["objects"][0]
                excluded = {"adoption", "authorization_ref", "decision_type"} if obj["type"] == "GoalSpec" else set()
                if {k: v for k, v in actual.items() if k not in excluded} != {k: v for k, v in obj.items() if k not in excluded}:
                    return problem("candidate_definition_differs_from_saved")
        gate = store.validate_refs([r for r in refs if (r.get("id"), r.get("revision")) not in incoming], "goal_design")
        if gate.get("status") != "ok":
            return gate
        review = review_goal_package(package)
        if operation == "goal.review":
            return review
        changes = packet.get("changes")
        if review.get("review_state") != "complete" or not isinstance(changes, list) or not changes:
            return problem("complete_explicit_goal_changes_required")
        if operation == "goal.sources_submit":
            if any(not isinstance(o, dict) or o.get("type") != "SourceFragment" or o not in package.get("sources", []) for o in changes):
                return problem("reviewed_goal_sources_only")
            return store.commit(packet["expected_state_revision"], packet["operation_id"], changes,
                                packet.get("artifacts", {}), packet.get("authorization_refs", []), packet.get("adoption_refs", []))
        goals = [o for o in changes if isinstance(o, dict) and o.get("type") == "GoalSpec"]
        if len(goals) != 1 or any(not isinstance(o, dict) or o.get("type") not in {"GoalSpec", "SourceFragment"} for o in changes):
            return problem("goal_objects_only")
        authored = {k: v for k, v in goals[0].items() if k not in {"adoption", "authorization_ref", "decision_type"}}
        reviewed = {k: v for k, v in review["goal_candidate"].items() if k not in {"adoption", "authorization_ref", "decision_type"}}
        if authored != reviewed:
            return problem("submitted_goal_differs_from_review")
        if any(o not in package.get("sources", []) for o in changes if o["type"] == "SourceFragment"):
            return problem("submitted_source_differs_from_review")
        return store.commit(packet["expected_state_revision"], packet["operation_id"], changes,
                            packet.get("artifacts", {}), packet.get("authorization_refs", []), packet.get("adoption_refs", []))

    def _dispatch(self, operation, packet, store):
        # A caller cannot relabel a result to spend a grant for a different
        # professional decision. The underlying store accepts several legacy
        # decision carriers, so the new entry constrains its own typed writes.
        for obj in packet.get("changes", []):
            if isinstance(obj, dict) and "decision_type" in obj and obj.get("type") in DECISIONS and obj["decision_type"] not in DECISIONS[obj["type"]]:
                return problem("professional_decision_type_mismatch")
        if operation.startswith("goal."):
            return self._goal(packet, operation, store)
        if operation == "need.submit":
            changes = packet.get("changes")
            if not isinstance(changes, list) or not changes or any(not isinstance(o, dict) or o.get("type") != "LearningNeed" or o.get("disposition", {}).get("status") != "pending" or o.get("acceptance", {}).get("status") != "proposed" for o in changes) or packet.get("artifacts"):
                return problem("proposed_pending_needs_only")
            state = store.read_context()
            current_ids = {o["id"] for o in state.get("objects", [])}
            if any(o.get("id") in current_ids for o in changes):
                return problem("existing_need_requires_planning_disposition")
            return store.commit(packet["expected_state_revision"], packet["operation_id"], changes,
                                authorization_refs=packet.get("authorization_refs", []), adoption_refs=packet.get("adoption_refs", []))
        if operation.startswith("materials."):
            from .learning_materials import MaterialsService
            service = MaterialsService(store)
            if operation == "materials.read":
                return service.read_fragment(packet)
            if operation == "materials.inspect":
                return service.inspect_material(packet.get("material"), packet.get("context", {}))
            return service.submit_material(packet)
        if operation.startswith("strategies."):
            from .learning_strategies import StrategiesService
            service = StrategiesService(store)
            if operation == "strategies.inspect":
                return service.inspect_config(packet.get("config"), packet.get("context"))
            if operation == "strategies.reuse":
                return service.reuse_config(packet.get("config_ref"), packet.get("context"))
            return service.submit_config(packet)
        if operation == "teaching.run":
            from .learning_teaching_b4 import SpecializedTeachingService
            return SpecializedTeachingService(store).run(packet)
        if operation.startswith("assessment."):
            from .learning_assessment import AssessmentService
            service = AssessmentService(store)
            if operation in {"assessment.inspect", "assessment.routine_inspect"}:
                return service.inspect_judgment(packet.get("judgment"), packet.get("context"))
            if operation == "assessment.diagnose":
                return service.inspect_diagnostic(packet.get("note"), packet.get("context"))
            return service.submit_assessment(packet)
        from .learning_planning import PlanningService
        service = PlanningService(store)
        if operation == "planning.resume":
            return service.resume(packet.get("commitment_ref"))
        return service.inspect(packet) if operation == "planning.inspect" else service.run(packet)

    def _view(self, steps, related_ids):
        context = self.store.read_context()
        view = {"current_work": [{"step": s["id"], "operation": s["operation"], "owner": s["owner"], "stage": s["stage"], "budget": s["result"].get("budget", {"status": "unknown", "reason": "本步骤未返回投入视图"})} for s in steps],
                "activity_facts": [], "conditional_support": [], "learning_needs": [],
                "controls": context.get("controls", {})}
        selected = set()
        for step in steps:
            if step["result"].get("status") == "committed":
                selected.update(r["id"] for r in step["result"].get("output_refs", []))
        for obj in context.get("objects", []):
            ref = {"id": obj["id"], "revision": obj["revision"]}
            if obj["type"] == "LearningNeed":
                if obj["id"] not in related_ids and obj.get("goal_ref", {}).get("id") not in related_ids:
                    continue
            elif obj["id"] not in selected:
                continue
            if self.store.validate_refs([ref], "read").get("status") != "ok":
                continue
            if obj["type"] == "PerformanceEvent":
                view["activity_facts"].append({"event_ref": ref, "activity_ref": obj["activity_ref"], "status": obj.get("c0", {}).get("status", "recorded"), "independent_sample_id": obj.get("independent_sample_id"), "judgment_implied": False})
            elif obj["type"] == "Judgment":
                view["conditional_support"].append({"judgment_ref": ref, "support": obj["support"], "eligibility": obj["eligibility"], "goal_ref": obj.get("goal_ref"), "requirement_id": obj.get("requirement_id"), "conditions": obj["conditions"], "adoption": obj.get("adoption", {"status": "unknown"})})
            elif obj["type"] == "LearningNeed":
                view["learning_needs"].append({"need_ref": ref, "goal_ref": obj["goal_ref"], "requirement_ids": obj["requirement_ids"], "acceptance": obj["acceptance"], "disposition": obj["disposition"], "uncovered_impact": obj["uncovered_impact"], "next_trigger": obj["next_trigger"], "assignee": obj["assignee"]})
        return view

    def execute(self, request):
        before = self.store.read_context()
        response = {"entry_version": VERSION, "synthetic_only": True, "mode": "single_entry_sequential",
                    "status": "rejected", "state_revision": before.get("state_revision"), "mutated": False,
                    "steps": [], "pending": [], "output_refs": [], "background_delegation": False,
                    "host_identity_verified": False, "learning_effect_verified": False}
        if before.get("status") != "ok" or before.get("synthetic_only") is not True or self.store.entry_actor != "AG0":
            return {**response, "status": "blocked", "reasons": [{"code": "synthetic_ag0_workspace_required"}]}
        # An intent alone remains a preview; executable scope needs a concrete request.
        if isinstance(request, dict) and "steps" not in request and isinstance(request.get("intent"), str):
            from .personal_learning import PersonalLearningEntry
            return {**response, "status": "needs_input", "route": PersonalLearningEntry(self.store).route(request["intent"]),
                    "needed_inputs": ["explicit_professional_steps", "entry_version", "synthetic_only", "expected_state_revision"]}
        error = self._shape(request)
        if error:
            return {**response, "reasons": [{"code": error}]}
        if request["expected_state_revision"] != before["state_revision"]:
            return {**response, "status": "conflict", "reasons": [{"code": "state_revision_conflict"}],
                    "pending": [{"owner": "AG0", "decision_needed": "重读当前状态并复核旧请求", "next_trigger": "提供当前修订与经复核的剩余步骤"}]}
        results, expected, related_ids = {}, before["state_revision"], set()
        completed = True
        for step in request["steps"]:
            operation, packet = step["operation"], copy.deepcopy(step["request"])
            owner = owner_for(operation, packet)
            try:
                for target, source in step.get("bindings", {}).items():
                    pointer_set(packet, target, pointer_get(results[source["step"]], source["path"]))
                related_ids.update(r["id"] for r in object_refs(packet) if isinstance(r.get("id"), str))
                related_ids.update(o["id"] for o in walk(packet) if isinstance(o, dict) and "type" in o and isinstance(o.get("id"), str))
                current = self.store.read_context()
                if current.get("status") != "ok" or current.get("state_revision") != expected:
                    result = {"status": "conflict", "reasons": [{"code": "state_revision_conflict"}]}
                else:
                    if is_write(step):
                        packet["expected_state_revision"] = expected
                    service_store = self.store if owner == "AG0" else LearningStore(self.store.root, entry_actor=owner)
                    result = self._dispatch(operation, packet, service_store)
                if not isinstance(result, dict):
                    result = problem("invalid_service_result")
            except (KeyError, ValueError, TypeError, AttributeError, IndexError):
                result = problem("invalid_professional_request_or_binding")
            except (OSError, sqlite3.Error):
                result = {"status": "not_saved", "reasons": [{"code": "service_unavailable"}]}
            after = self.store.read_context()
            # Never advance a stale decision to arbitrary newly observed state.
            saved = result.get("status") == "committed"
            if saved:
                saved_refs = list(result.get("output_refs", []))
                saved_refs.extend({"id": o["id"], "revision": o["revision"]} for o in packet.get("changes", []))
                saved_refs.extend(result[key] for key in ("event_ref", "checkpoint_ref") if isinstance(result.get(key), dict))
                result["output_refs"] = list({(r["id"], r["revision"]): r for r in saved_refs}.values())
            stage = "saved" if saved else "candidate" if result.get("status") == "candidate" else "limited" if result.get("status") == "limited" else "checked" if successful(operation, result) else "pending"
            response["steps"].append({"id": step["id"], "operation": operation, "owner": owner, "status": result.get("status"), "stage": stage, "result": result})
            results[step["id"]] = result
            if saved:
                response["output_refs"].extend(result.get("output_refs", []))
            response["pending"].extend(copy.deepcopy(result.get("unresolved_items", [])))
            if result.get("learning_need_candidate"):
                candidate = result["learning_need_candidate"]
                response["pending"].append({"owner": "AG1", "decision_needed": "同一教学后续需求尚需实质处置", "next_trigger": "以已保存事件和当前需求提交明确处置", "step": step["id"], "existing_need_ref": candidate.get("existing_need_ref"), "additional_event_ref": candidate.get("additional_event_ref", candidate.get("event_ref"))})
            if not successful(operation, result):
                completed = False
                codes = {r.get("code") for r in result.get("reasons", []) if isinstance(r, dict)}
                declared_owner = result.get("next_owner")
                next_owner = declared_owner if isinstance(declared_owner, str) and declared_owner in {"AG0", "AG1", "AG2", "AG3"} else "AG3" if operation.startswith("assessment.routine_") and codes.intersection({"important_review_required", "professional_escalation", "authorization_scope", "assessment_authorization_required"}) else owner
                response["pending"].append({"owner": next_owner, "decision_needed": "补齐或复核本步骤，后续步骤未执行", "next_trigger": "解决返回缺项后，以当前修订提交剩余步骤", "step": step["id"], "status": result.get("status")})
                break
            if saved:
                # Idempotent service receipts may name an older commit. Only our
                # single new commit (or a read-only replay) may advance this chain.
                if after.get("state_revision") not in {expected, expected + 1} or (after.get("state_revision") == expected + 1 and result.get("state_revision") != expected + 1):
                    completed = False
                    response["pending"].append({"owner": "AG0", "decision_needed": "串行入口外状态变化，须重读", "next_trigger": "以当前修订重新确认剩余范围"})
                    break
                expected = after["state_revision"]
            elif after.get("state_revision") != expected:
                completed = False
                response["pending"].append({"owner": "AG0", "decision_needed": "读取期间状态改变", "next_trigger": "重新读取当前条件"})
                break
        final = self.store.read_context()
        response["state_revision"] = final.get("state_revision")
        response["mutated"] = any(s["stage"] == "saved" for s in response["steps"]) and response["state_revision"] != before["state_revision"]
        response["status"] = "completed" if completed else "partial" if any(s["stage"] == "saved" for s in response["steps"]) else response["steps"][-1]["status"]
        response["user_view"] = self._view(response["steps"], related_ids)
        # Reconcile a teaching handoff only when this chain actually disposed
        # the same stable need. Receipt or acceptance alone remains pending.
        disposed = set()
        for item in response["steps"]:
            if item["operation"] == "planning.run" and item["stage"] == "saved":
                disposed.update(r["id"] for r in item["result"].get("output_refs", []))
        actual_needs = {n["need_ref"]["id"]: n for n in response["user_view"]["learning_needs"]}
        response["pending"] = [p for p in response["pending"] if not (
            isinstance(p.get("existing_need_ref"), dict)
            and p["existing_need_ref"].get("id") in disposed
            and actual_needs.get(p["existing_need_ref"]["id"], {}).get("disposition", {}).get("status", "pending") != "pending")]
        response["unexecuted_steps"] = [s["id"] for s in request["steps"][len(response["steps"]):]]
        return response
