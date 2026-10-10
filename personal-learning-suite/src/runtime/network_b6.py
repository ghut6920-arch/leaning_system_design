"""B6 local serial host, explicitly limited to synthetic fixture workspaces.

Capabilities authenticate calls inside this Python host; they are neither JSON
actors nor real learner identities. The OS lock excludes another cooperating
host. It does not sandbox Python, intercept a chat, or deploy Codex agents.
All personal work and result state belongs to the existing SQLite objects.
"""
from __future__ import annotations

import copy
from functools import wraps
import json
import os
from pathlib import Path
import sqlite3
import threading
import uuid

from .b3_semantics import active_grant
from .contract_rules import PROTOCOL, object_refs, walk
from .entry_b5 import SingleEntryService, OPERATIONS, owner_for, is_write, successful
from .learning_store import LearningStore

VERSION = "pl-network/0.1.0"
NETWORK_VERSION = VERSION
ROLES = {
    "AG0": ("AG0-coach.md", ("personal-learning", "learning-teaching", "learning-assessment", "learning-planning")),
    "AG1": ("AG1-design-planning.md", ("learning-goals", "learning-teaching", "learning-planning", "learning-strategies")),
    "AG2": ("AG2-materials.md", ("learning-materials",)),
    "AG3": ("AG3-assessment.md", ("learning-assessment",)),
}


class _Capability:
    __slots__ = ()

    def __repr__(self):
        return "<local-role-capability>"


def _ref(obj):
    return {"id": obj["id"], "revision": obj["revision"]}


def _key(ref):
    return (ref.get("id", ref.get("path")), ref.get("revision"), ref.get("locator", ""))


def _unique(refs):
    return list({_key(ref): copy.deepcopy(ref) for ref in refs}.values())


def _refs(value):
    return _unique(list(object_refs(value)))


def _artifacts(value):
    return [item for item in walk(value) if isinstance(item, dict)
            and {"path", "locator", "revision", "origin"} <= item.keys()]


def _strings(value):
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def _primary_targets(operation, packet):
    """Derive object identity from the fixed professional operation, not labels."""
    if operation.endswith(".submit") or operation.endswith(".routine_submit") or operation == "goal.sources_submit":
        if operation.startswith("assessment."):
            targets = [ref.get("id") for obj in packet.get("changes", []) if isinstance(obj, dict)
                       for ref in obj.get("event_refs", obj.get("observations", [])) if isinstance(ref, dict)]
        else:
            targets = [obj.get("id") for obj in packet.get("changes", []) if isinstance(obj, dict)]
    elif operation == "goal.review":
        targets = [obj.get("id") for obj in walk(packet.get("package")) if isinstance(obj, dict) and obj.get("type") == "GoalSpec"]
    elif operation == "materials.read":
        targets = [packet.get("fragment_id")]
    elif operation == "materials.inspect":
        targets = [packet.get("material", {}).get("id")]
    elif operation == "strategies.inspect":
        targets = [packet.get("config", {}).get("id")]
    elif operation == "strategies.reuse":
        targets = [packet.get("config_ref", {}).get("id")]
    elif operation == "assessment.diagnose":
        targets = [ref.get("id") for ref in packet.get("note", {}).get("observations", []) if isinstance(ref, dict)]
    elif operation in {"assessment.inspect", "assessment.routine_inspect"}:
        targets = [ref.get("id") for ref in packet.get("judgment", {}).get("event_refs", []) if isinstance(ref, dict)]
    elif operation == "planning.resume":
        targets = [packet.get("commitment_ref", {}).get("id")]
    elif operation.startswith("planning."):
        targets = [decision.get("need_ref", {}).get("id") for decision in packet.get("decisions", []) if isinstance(decision, dict)]
        if packet.get("action") == "shrink":
            targets.append(packet.get("commitment_ref", {}).get("id"))
    elif operation == "teaching.run":
        targets = [packet.get("activity_ref", packet.get("context", {}).get("activity_ref", {})).get("id")]
        if packet.get("action") in {"design", "commit_design"}:
            targets = [obj.get("id") for obj in walk(packet) if isinstance(obj, dict) and obj.get("type") == "ActivitySpec"]
    else:
        targets = []
    return set(targets) if targets and all(isinstance(item, str) and item.startswith("FIX-") for item in targets) else set()


def _decisions_for(operation, packet):
    if operation in {"goal.review", "goal.submit"}:
        return {"goal_design"}
    if operation in {"materials.read", "goal.sources_submit"}:
        return {"material_read"}
    if operation == "materials.inspect":
        return {"material_review", "material_verification", "material_use"}
    if operation == "materials.submit":
        return {"material_review", "material_verification", "material_use"}
    if operation.startswith("strategies."):
        return {"strategy_configuration"}
    if operation == "need.submit" or operation == "planning.resume":
        return {"planning"}
    if operation.startswith("planning."):
        return {"plan_adjustment"} if packet.get("action") == "shrink" else {"planning"}
    if operation.startswith("assessment.routine_"):
        return {"routine_scoring"}
    if operation == "assessment.diagnose":
        return {"limited_diagnosis"}
    if operation == "assessment.submit":
        return {"professional_review", "limited_diagnosis"}
    if operation.startswith("assessment."):
        return {"professional_review"}
    if operation == "teaching.run":
        return {"teaching_design"} if packet.get("action") in {"design", "commit_design"} else {"teaching_execution", "teaching_adaptation"}
    return set()


def _decision_matches(operation, packet, decision):
    return decision in _decisions_for(operation, packet) and all(
        not isinstance(obj, dict) or "decision_type" not in obj or obj["decision_type"] == decision
        for obj in packet.get("changes", []))


def _serial(method):
    @wraps(method)
    def guarded(self, capability, *args, **kwargs):
        with self._mutex:
            if self._closed or type(capability) is not _Capability or capability not in self._capabilities:
                return self._reject("invalid_capability")
            try:
                return method(self, capability, *args, **kwargs)
            except (KeyError, TypeError, ValueError, AttributeError, IndexError):
                return self._reject("invalid_network_request")
            except (OSError, sqlite3.Error, RuntimeError):
                return self._reject("network_service_unavailable", "not_saved")
    return guarded


class NetworkHost:
    """One trusted local serial dispatcher per already initialized workspace.

    The caller holding this host may bind roles; untrusted requests only receive
    an already bound capability. No capability, original, or result is serialized
    into a host cache. Closing releases the OS lease and invalidates every cap.
    """

    def __init__(self, store_or_root):
        root = store_or_root.root if isinstance(store_or_root, LearningStore) else store_or_root
        self.store = LearningStore(root, entry_actor="AG0")
        self._mutex = threading.RLock()
        self._closed = True
        self._capabilities = {}
        self._guidance = {}
        self._lock_file = None
        state = self.store.read_context()
        if state.get("status") != "ok" or state.get("synthetic_only") is not True:
            raise RuntimeError("initialized_synthetic_workspace_required")
        src = Path(__file__).resolve().parents[1]
        for role, (agent, skills) in ROLES.items():
            paths = [src / "agents" / agent] + [src / "skills" / skill / "SKILL.md" for skill in skills]
            self._guidance[role] = [{"path": str(path), "text": path.read_text(encoding="utf-8-sig")} for path in paths]
        lock = open(self.store.root / ".network-b6.lock", "a+b")
        try:
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError):
            lock.close()
            raise RuntimeError("workspace_host_already_active") from None
        self._lock_file = lock
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()

    def close(self):
        with self._mutex:
            if self._closed:
                return
            self._closed = True
            self._capabilities.clear()
            lock, self._lock_file = self._lock_file, None
            try:
                lock.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            finally:
                lock.close()

    def bind(self, role):
        with self._mutex:
            if self._closed:
                raise RuntimeError("host_closed")
            if role not in ROLES:
                raise ValueError("unknown_role")
            cap = _Capability()
            self._capabilities[cap] = (role, "FIX-executor-" + uuid.uuid4().hex)
            return cap

    def _role(self, capability):
        return self._capabilities[capability][0]

    def _reply(self, status, **fields):
        return {"network_version": VERSION, "synthetic_only": True, "mode": "local_serial",
                "status": status, "background_delegation": False, "codex_deployed": False, **fields}

    def _reject(self, code, status="rejected", **fields):
        return self._reply(status, mutated=False, reasons=[{"code": code}], **fields)

    def _shape(self, request, mutation=True):
        if not isinstance(request, dict) or request.get("network_version") != VERSION or request.get("synthetic_only") is not True:
            return self._reject("synthetic_network_request_required")
        if any(isinstance(item, dict) and ({"actor", "entry_actor", "executor_id", "capability"} & item.keys()) for item in walk(request)):
            return self._reject("actor_override_not_supported")
        if request.get("async") or request.get("parallel") or request.get("background"):
            return self._reject("serial_host_only")
        if mutation and (type(request.get("expected_state_revision")) is not int or request["expected_state_revision"] < 0
                         or not isinstance(request.get("operation_id"), str) or not request["operation_id"]):
            return self._reject("explicit_network_cas_required")
        return None

    def _current(self, refs, use):
        checked = self.store.validate_refs(refs, use)
        if checked.get("status") != "ok":
            return self._reject("controlled_basis_unavailable", state_revision=checked.get("state_revision"))
        state = self.store.read_context()
        if state.get("status") != "ok":
            return self._reject("current_state_unavailable", "not_saved")
        latest = {obj["id"]: obj["revision"] for obj in state["objects"]}
        if any("id" in ref and latest.get(ref["id"]) != ref["revision"] for ref in refs):
            return self._reject("stale_basis_requires_recheck", state_revision=state["state_revision"])
        return None

    def _definition_controls(self, operation, packet, use):
        """Check inline object identities even though object_refs omits them.

        Only the professional API's explicit definition positions may carry a
        complete object. New authored candidates may be absent, but historical
        deleted/paused definitions and arbitrary memo copies cannot be imported.
        Existing definition identities also become canonical dependencies.
        """
        fields = {"changes"} if operation.endswith(".submit") or operation.endswith(".routine_submit") or operation == "goal.sources_submit" else set()
        if operation.startswith("goal."):
            fields.add("package")
        elif operation == "materials.inspect":
            fields.add("material")
        elif operation == "strategies.inspect":
            fields.add("config")
        elif operation in {"assessment.inspect", "assessment.routine_inspect"}:
            fields.add("judgment")
        elif operation == "assessment.diagnose":
            fields.add("note")
        elif operation == "teaching.run" and packet.get("action") in {"design", "commit_design"}:
            fields.add("activity")
        definitions = []
        for field, value in packet.items():
            found = [obj for obj in walk(value) if isinstance(obj, dict) and "type" in obj and "id" in obj]
            if found and field not in fields:
                return [], self._reject("inline_definition_outside_professional_input")
            definitions.extend(found)
        own_refs = _unique([_ref(obj) for obj in definitions])
        state = self.store.read_context()
        if state.get("status") != "ok":
            return [], self._reject("current_state_unavailable", "not_saved")
        current = {obj["id"]: obj["revision"] for obj in state["objects"]}
        existing = []
        for reference in own_refs:
            checked = self.store.validate_refs([reference], use)
            if checked.get("status") not in {"ok", "rejected"} or any(reason.get("code") != "missing_reference" for reason in checked.get("reasons", [])):
                return [], self._reject("controlled_inline_definition_unavailable")
            if checked.get("status") == "ok":
                if current.get(reference["id"]) != reference["revision"]:
                    return [], self._reject("stale_inline_definition_requires_recheck")
                existing.append(reference)
        return existing, None

    def _load(self, reference, kind, use="network"):
        checked = self.store.read_refs([reference], use)
        if checked.get("status") != "ok":
            return None, self._reject("controlled_basis_unavailable", state_revision=checked.get("state_revision"))
        if len(checked.get("objects", [])) != 1 or checked["objects"][0].get("type") != kind:
            return None, self._reject("network_object_type")
        obj = checked["objects"][0]
        state = self.store.read_context()
        if not any(other["id"] == obj["id"] and other["revision"] == obj["revision"] for other in state.get("objects", [])):
            return None, self._reject("stale_network_reference")
        return obj, None

    def _order(self, capability, reference):
        order, error = self._load(reference, "WorkOrder")
        if error:
            return None, error
        if self._role(capability) not in {order["requester"], order["assignee"], order["return_owner"]}:
            return None, self._reject("work_order_role_scope")
        if order.get("metadata", {}).get("network", {}).get("version") != VERSION:
            return None, self._reject("network_work_order_required")
        return order, None

    def _authority(self, order):
        refs = order.get("authorization_refs", [])
        if not refs:
            return self._reject("receiver_authorization_required")
        error = self._current(refs + [order["shared_budget_ref"]], order["decision_type"])
        if error:
            return error
        result = self.store.read_refs(refs, order["decision_type"])
        for grant in result.get("objects", []):
            if (grant.get("type") != "AuthorizationGrant" or grant.get("binding_status") != "verified_for_fixture"
                    or grant.get("grantee") != order["assignee"] or order["decision_type"] not in grant.get("decision_types", [])
                    or grant.get("budget_ref") != order["shared_budget_ref"] or not grant.get("permitted_conclusions")
                    or not active_grant(grant.get("validity"), allow_legacy=True)):
                continue
            objects = {ref["id"] for ref in order["event_refs"] + order["material_refs"]}
            if not objects:
                objects = {ref["id"] for ref in order["context_refs"] if "id" in ref and ref["id"] != order["shared_budget_ref"]["id"]}
            if not self.store._scope_matches(grant.get("object_scope"), objects):
                continue
            allowed = grant.get("criterion_refs", [])
            if any(not any(ref["id"] == item.get("id") and ref["revision"] == item.get("revision")
                           and (not ref.get("locator") or ref["locator"] == item.get("locator")) for item in allowed)
                   for ref in order["goal_and_criteria_refs"]):
                continue
            return None
        return self._reject("receiver_authorization_scope")

    def _save(self, role, request, obj, authorization_refs=None, adoption_refs=None):
        store = LearningStore(self.store.root, entry_actor=role)
        receipt = store.commit(request["expected_state_revision"], request["operation_id"], [obj],
                               authorization_refs=authorization_refs or [], adoption_refs=adoption_refs or [])
        if receipt.get("status") != "committed":
            return self._reply(receipt.get("status", "not_saved"), mutated=False,
                               state_revision=receipt.get("state_revision"), reasons=receipt.get("reasons", []))
        return self._reply("committed", mutated=True, state_revision=receipt["state_revision"],
                           **{"order_ref" if obj["type"] == "WorkOrder" else "result_ref": _ref(obj)})

    @_serial
    def role_info(self, capability):
        role = self._role(capability)
        return self._reply("ok", role=role, instructions=copy.deepcopy(self._guidance[role]),
                           identity_boundary="trusted_local_capability", grant_binding="verified_for_fixture",
                           capabilities={"asynchronous": False, "asynchronous_delegation": False, "parallel_presentation": False, "host_identity_bound": True,
                                         "local_output_gate": True, "external_chat_interception": False})

    @_serial
    def dispatch(self, capability, request):
        error = self._shape(request)
        if error:
            return error
        role, receiver = self._role(capability), request.get("assignee")
        operation, packet = request.get("operation"), request.get("professional_request")
        if receiver not in ROLES or operation not in OPERATIONS or not isinstance(packet, dict) or owner_for(operation, packet) != receiver:
            return self._reject("professional_owner_mismatch")
        if "expected_state_revision" in packet or packet.get("synthetic_only") is not True:
            return self._reject("explicit_professional_request_required")
        if not _decision_matches(operation, packet, request.get("decision_type")):
            return self._reject("professional_decision_type_mismatch")
        definition_refs, error = self._definition_controls(operation, packet, request["decision_type"])
        if error:
            return error
        scope = request.get("scope")
        if not _strings(scope) or not scope or not isinstance(request.get("order_id"), str) or not request["order_id"].startswith("FIX-"):
            return self._reject("explicit_order_scope_required")
        refs = request.get("context_refs", [])
        grants, budget = request.get("authorization_refs", []), request.get("shared_budget_ref")
        if not isinstance(refs, list) or not isinstance(grants, list) or not isinstance(budget, dict):
            return self._reject("minimal_references_and_budget_required")
        if any(reference not in grants for reference in packet.get("authorization_refs", [])):
            return self._reject("professional_authorization_scope_expansion")
        segments = request.get("context_segments", [])
        if not isinstance(segments, list) or any(not isinstance(segment, dict)
                or set(segment) != {"artifact_ref", "start_line", "end_line"}
                or type(segment["start_line"]) is not int or type(segment["end_line"]) is not int
                or not 1 <= segment["start_line"] <= segment["end_line"] for segment in segments):
            return self._reject("bounded_context_segments_required")
        required = _unique(refs + definition_refs + grants + [budget] + request.get("goal_and_criteria_refs", [])
                           + request.get("event_refs", []) + request.get("material_refs", [])
                           + [segment["artifact_ref"] for segment in segments])
        definitions = {(obj.get("id"), obj.get("revision")) for obj in walk(packet) if isinstance(obj, dict) and "type" in obj}
        incoming_refs = [ref for ref in _refs(packet) if (ref.get("id"), ref.get("revision")) not in definitions]
        used_fields = {"materials.inspect": {"material", "context"}, "strategies.inspect": {"config", "context"},
                       "strategies.reuse": {"config_ref", "context"}, "assessment.inspect": {"judgment", "context"},
                       "assessment.routine_inspect": {"judgment", "context"}, "assessment.diagnose": {"note", "context"},
                       "planning.resume": {"commitment_ref"}}
        used_packet = {field: value for field, value in packet.items() if field in used_fields[operation]} if operation in used_fields else packet
        legal_context = {_key(ref) for ref in _refs(used_packet) + definition_refs + grants + [budget]
                         + request.get("goal_and_criteria_refs", []) + request.get("event_refs", []) + request.get("material_refs", [])}
        if any(_key(reference) not in legal_context for reference in refs):
            return self._reject("unrelated_context_reference")
        contextual = self.store.read_refs([reference for reference in refs if "id" in reference], request["decision_type"])
        if contextual.get("status") != "ok":
            return self._reject("controlled_basis_unavailable")
        allowed_artifacts = {}
        for item in _artifacts(contextual.get("objects", [])):
            identity = (item["path"], item["locator"], item["revision"], item["origin"])
            allowed_artifacts.setdefault(identity, []).append(item)
        for segment in segments:
            identity = tuple(segment["artifact_ref"].get(field) for field in ("path", "locator", "revision", "origin"))
            matches = allowed_artifacts.get(identity, [])
            if not matches:
                return self._reject("context_segment_outside_original_scope")
            bounded = [item for item in matches if type(item.get("start_line")) is int and type(item.get("end_line")) is int]
            if bounded and not any(item["start_line"] <= segment["start_line"] <= segment["end_line"] <= item["end_line"] for item in bounded):
                return self._reject("context_segment_outside_declared_bounds")
            if not bounded and segment["start_line"] != segment["end_line"]:
                return self._reject("unbounded_original_requires_locator_line")
        approved = {_key(ref) for ref in required}
        if any(_key(ref) not in approved for ref in incoming_refs):
            return self._reject("undeclared_professional_reference")
        error = self._current(required, request["decision_type"])
        if error:
            return error
        budget_read = self.store.read_refs([budget], request["decision_type"])
        if budget_read.get("status") != "ok" or len(budget_read.get("objects", [])) != 1 or budget_read["objects"][0].get("type") != "BudgetEnvelope":
            return self._reject("shared_budget_envelope_required")
        for segment in segments:
            if self.store.read_artifact_segment(segment["artifact_ref"], segment["start_line"], segment["end_line"], request["decision_type"]).get("status") != "ok":
                return self._reject("controlled_original_unavailable")
        primary = _primary_targets(operation, packet)
        operation_scope = request.get("operation_scope", sorted(primary))
        if not _strings(operation_scope) or not operation_scope or not set(operation_scope) <= set(scope):
            return self._reject("operation_scope_outside_order")
        if not primary or not primary <= set(operation_scope):
            return self._reject("professional_targets_outside_operation_scope")
        state = self.store.read_context()
        order = {"type": "WorkOrder", "id": request["order_id"], "revision": 1, "owner": role,
                 "schema_version": PROTOCOL, "basis_refs": required, "operation_id": request["operation_id"],
                 "requester": role, "assignee": receiver, "decision_needed": request["decision_needed"],
                 "decision_type": request["decision_type"], "scope": scope,
                 "output_contract": "WorkResult candidate; separate explicit professional adoption",
                 "goal_and_criteria_refs": request.get("goal_and_criteria_refs", []),
                 "material_refs": request.get("material_refs", []), "event_refs": request.get("event_refs", []),
                 "context_refs": refs, "current_restrictions": {"restrictions": [item for item in state["controls"]["restrictions"] if item["scope_id"] in {ref.get("id") for ref in required}],
                    "paused_ids": [], "deleted_ids": []}, "basis_revisions": required,
                 "execution_epoch": request.get("execution_epoch", 0), "authority_scope": scope,
                 "authorization_refs": grants, "shared_budget_ref": budget,
                 "stop_condition": request["stop_condition"], "return_owner": request.get("return_owner", role),
                 "next_trigger": request["next_trigger"],
                 "acceptance": {"status": "proposed", "handled_scope": [], "unhandled_scope": scope},
                 "metadata": {"network": {"version": VERSION, "phase": "proposed" if grants else "proposed_unready",
                                           "operation": operation, "professional_request": copy.deepcopy(packet),
                                           "operation_scope": operation_scope, "context_segments": segments, "responsible_owner": role}}}
        if order["return_owner"] not in ROLES:
            return self._reject("unknown_return_owner")
        if grants:
            error = self._authority(order)
            if error:
                return error
        result = self._save(role, request, order)
        if result["status"] == "committed":
            result.update(ready=False, acceptance="proposed", responsible_owner=role,
                          authorization_ready=bool(grants))
        return result

    @_serial
    def accept(self, capability, request):
        error = self._shape(request, mutation=request.get("status") != "received" if isinstance(request, dict) else True)
        if error:
            return error
        order, error = self._order(capability, request.get("order_ref"))
        if error:
            return error
        role, status = self._role(capability), request.get("status")
        if status == "declined":
            status = "rejected"
        if role != order["assignee"]:
            return self._reject("receiver_capability_required")
        if status == "received":
            return self._reply("received", mutated=False, order_ref=_ref(order),
                               responsible_owner=order["metadata"]["network"]["responsible_owner"])
        if status not in {"accepted", "partially_accepted", "rejected"}:
            return self._reject("explicit_acceptance_required")
        if order["metadata"]["network"]["phase"] == "proposed_unready":
            return self._reject("receiver_authorization_required")
        error = self._current(order["basis_refs"], order["decision_type"]) or self._authority(order)
        if error:
            return error
        handled, unhandled = request.get("handled_scope", []), request.get("unhandled_scope", [])
        if not _strings(handled) or not _strings(unhandled) or set(handled) & set(unhandled) or set(handled + unhandled) != set(order["scope"]):
            return self._reject("explicit_acceptance_partition_required")
        if (status == "accepted" and unhandled) or (status == "partially_accepted" and (not handled or not unhandled)) or (status == "rejected" and handled):
            return self._reject("acceptance_scope_mismatch")
        if order["acceptance"]["status"] != "proposed":
            return self._reject("order_already_decided")
        updated = copy.deepcopy(order)
        updated.update(revision=order["revision"] + 1, owner=role)
        updated["acceptance"] = {"status": "declined" if status == "rejected" else status, "by": role, "handled_scope": handled, "unhandled_scope": unhandled,
                                 "limitations": request.get("limitations", []), "next_trigger": request.get("next_trigger", order["next_trigger"])}
        updated["metadata"]["network"].update(phase=status, responsible_owner=role if handled else order["requester"])
        return self._save(role, request, updated)

    @_serial
    def context(self, capability, order_ref):
        order, error = self._order(capability, order_ref)
        if error:
            return error
        if order["metadata"]["network"]["phase"] == "proposed_unready":
            return self._reject("receiver_authorization_required")
        error = self._current(order["basis_refs"], order["decision_type"]) or self._authority(order)
        if error:
            return error
        read = self.store.read_refs(order["context_refs"], order["decision_type"])
        if read.get("status") != "ok":
            return self._reject("controlled_basis_unavailable")
        objects = read.get("objects", [])
        objects.sort(key=lambda obj: 0 if obj["type"] == "PerformanceEvent" else 1)
        artifacts = list(read.get("artifact_refs", []))
        for obj in objects:
            if obj["type"] == "PerformanceEvent":
                artifacts.append(copy.deepcopy(obj["original_response"]))
        # Only explicitly bounded artifact segments can return original text.
        segments = []
        for segment in order["metadata"]["network"].get("context_segments", []):
            read_segment = self.store.read_artifact_segment(segment["artifact_ref"], segment["start_line"], segment["end_line"], order["decision_type"])
            if read_segment.get("status") != "ok":
                return self._reject("controlled_original_unavailable")
            segments.append(read_segment)
        return self._reply("ok", order_ref=_ref(order), objects=objects, artifact_refs=artifacts,
                           segments=segments, original_event_priority=self._role(capability) == "AG3")

    def _execution(self, capability, packet, epoch=None, basis=None):
        if self._role(capability) != "AG0":
            return self._reject("only_ag0_may_present")
        activity = packet.get("activity_ref") or packet.get("context", {}).get("activity_ref")
        if not isinstance(activity, dict):
            return self._reject("execution_activity_required")
        state = self.store.read_context()
        controls = [obj for obj in state.get("objects", []) if obj["type"] == "ControlState"
                    and obj.get("execution", {}).get("activity_ref") == activity and obj["id"].startswith("FIX-network-execution-")]
        current = max(controls, key=lambda obj: obj["execution"]["execution_epoch"], default=None)
        if current is None:
            return self._reject("execution_takeover_required")
        result = self.store.check_execution(activity, self._capabilities[capability][1],
                                           current["execution"]["execution_epoch"] if epoch is None else epoch,
                                           current["basis_refs"] if basis is None else basis)
        return None if result.get("status") == "ok" else self._reject("execution_revoked", state_revision=result.get("state_revision"))

    @staticmethod
    def _public_professional(result):
        allowed = {"output_refs", "event_ref", "checkpoint_ref", "activity_ref", "budget_ref"}
        public = {key: copy.deepcopy(value) for key, value in result.items() if key in allowed}
        recovery = result.get("recovery")
        if isinstance(recovery, dict):
            public["recovery"] = {key: copy.deepcopy(recovery[key]) for key in
                                  ("source", "checkpoint_ref", "activity_ref", "last_trusted_event_ref", "unrecorded_actions") if key in recovery}
        return public

    @_serial
    def run(self, capability, request):
        error = self._shape(request)
        if error:
            return error
        order, error = self._order(capability, request.get("order_ref"))
        if error:
            return error
        role, network = self._role(capability), order["metadata"]["network"]
        if role != order["assignee"] or order["acceptance"]["status"] not in {"accepted", "partially_accepted"}:
            return self._reject("accepted_receiver_required")
        if not set(network["operation_scope"]) <= set(order["acceptance"]["handled_scope"]):
            return self._reject("operation_outside_accepted_scope")
        error = self._current(order["basis_refs"], order["decision_type"]) or self._authority(order)
        if error:
            return error
        packet = copy.deepcopy(network["professional_request"])
        if "professional_request" in request and request["professional_request"] != packet:
            return self._reject("professional_request_scope_expansion")
        if "operation" in request and request["operation"] != network["operation"]:
            return self._reject("professional_operation_scope_expansion")
        operation = network["operation"]
        if owner_for(operation, packet) != role:
            return self._reject("professional_owner_mismatch")
        if not _decision_matches(operation, packet, order["decision_type"]):
            return self._reject("professional_decision_type_mismatch")
        if any(reference not in order["authorization_refs"] for reference in packet.get("authorization_refs", [])):
            return self._reject("professional_authorization_scope_expansion")
        _, error = self._definition_controls(operation, packet, order["decision_type"])
        if error:
            return error
        primary = _primary_targets(operation, packet)
        if not primary or not primary <= set(network["operation_scope"]) or not primary <= set(order["acceptance"]["handled_scope"]):
            return self._reject("professional_targets_outside_accepted_scope")
        if operation == "teaching.run" and role == "AG0":
            error = self._execution(capability, packet)
            if error:
                return error
        identifier = request.get("result_id")
        if not isinstance(identifier, str) or not identifier.startswith("FIX-"):
            return self._reject("explicit_result_id_required")
        state = self.store.read_context()
        previous = next((obj for obj in state["objects"] if obj["id"] == identifier), None)
        if previous is not None:
            if previous["type"] == "WorkResult" and previous.get("metadata", {}).get("network", {}).get("run_operation_id") == request["operation_id"] and previous["work_order_ref"] == _ref(order):
                return self._reply("committed", mutated=False, state_revision=state["state_revision"], result_ref=_ref(previous), professional_status=previous["metadata"]["network"]["professional_status"])
            return self._reject("result_id_reused")
        if request["expected_state_revision"] != state["state_revision"]:
            return self._reject("state_revision_conflict", "conflict", state_revision=state["state_revision"])
        step = {"operation": operation, "request": packet}
        if is_write(step):
            packet["expected_state_revision"] = state["state_revision"]
        raw = SingleEntryService(self.store)._dispatch(operation, packet, LearningStore(self.store.root, entry_actor=role))
        if not isinstance(raw, dict):
            return self._reject("invalid_professional_result")
        after = self.store.read_context()
        error = self._current([_ref(order)], order["decision_type"])
        if error:
            return error
        latest = {obj["id"]: obj for obj in after.get("objects", [])}
        result_refs = _unique([ref for ref in raw.get("output_refs", []) if ref.get("id") in latest]
                              + [_ref(latest[obj["id"]]) for obj in packet.get("changes", []) if isinstance(obj, dict) and obj.get("id") in latest]
                              + [raw[key] for key in ("event_ref", "checkpoint_ref") if isinstance(raw.get(key), dict)])
        expected = state["state_revision"]
        allowed_revision = after.get("state_revision") in ({expected, expected + 1} if raw.get("status") == "committed" else {expected})
        if not allowed_revision or (after.get("state_revision") == expected + 1 and raw.get("state_revision") != expected + 1):
            legal = self.store.validate_refs(result_refs, order["decision_type"]).get("status") == "ok"
            return self._reject("state_changed_during_professional_operation", "partial" if raw.get("status") == "committed" else "conflict",
                                state_revision=after.get("state_revision"), professional_saved=raw.get("status") == "committed",
                                output_refs=result_refs if legal else [])
        basis = _unique([_ref(order)] + [dict(ref, revision=latest[ref["id"]]["revision"]) if "id" in ref else ref
                                       for ref in order["basis_refs"] if "id" not in ref or ref["id"] in latest] + result_refs)
        professional_ok = successful(operation, raw)
        handled = [target for target in network["operation_scope"] if target in order["acceptance"]["handled_scope"]] if professional_ok else []
        unhandled = [target for target in order["scope"] if target not in handled]
        # Do not store a raw service payload: a reference-only candidate is enough
        # for adoption. Detailed professional facts remain their original objects.
        result = {"type": "WorkResult", "id": identifier, "revision": 1, "owner": role,
                  "schema_version": PROTOCOL, "basis_refs": basis, "work_order_ref": _ref(order),
                  "decision_type": order["decision_type"], "handled_scope": handled,
                  "unhandled_scope": unhandled, "result_refs": result_refs,
                  "limitations": ["Local explicit operation; no independent model review or learning benefit proven."],
                  "adoption_needed": True, "next_owner": role, "next_trigger": "Explicit responsible professional adoption with current legal basis",
                  "compatibility": {"status": "pending_review", "basis_refs": basis},
                  "adoption": {"status": "candidate"}, "metadata": {"network": {"version": VERSION,
                    "phase": "candidate", "run_operation_id": request["operation_id"], "operation": operation,
                    "professional_status": raw.get("status", "unknown"), "professional_successful": professional_ok,
                    "responsible_owner": role}}}
        saved_request = dict(request, expected_state_revision=after["state_revision"])
        saved = self._save(role, saved_request, result, order["authorization_refs"], basis)
        saved["professional_status"] = raw.get("status", "unknown")
        if saved["status"] != "committed" and raw.get("status") == "committed":
            saved["professional_saved"] = True
            saved["output_refs"] = result_refs
        return saved

    @_serial
    def adopt(self, capability, request):
        error = self._shape(request)
        if error:
            return error
        result, error = self._load(request.get("result_ref"), "WorkResult")
        if error:
            return error
        role, status = self._role(capability), request.get("status")
        if role != result["owner"]:
            return self._reject("responsible_professional_required")
        if status not in {"adopted", "partially_adopted", "recheck", "rejected"}:
            return self._reject("explicit_result_adoption_required")
        order, error = self._order(capability, result["work_order_ref"])
        if error:
            return error
        basis = request.get("basis_refs", [])
        if not isinstance(basis, list) or not basis or not _strings(request.get("limitations", [])):
            return self._reject("explicit_current_basis_and_limits_required")
        allowed_basis = {reference.get("id", reference.get("path")) for reference in result["basis_refs"] + order["basis_refs"] + result["result_refs"]}
        if any(reference.get("id", reference.get("path")) not in allowed_basis for reference in basis):
            return self._reject("adoption_basis_scope_expansion")
        error = self._current(basis, order["decision_type"]) or self._authority(order)
        if error:
            return error
        stale = self._current(result["basis_refs"], order["decision_type"])
        handled, unhandled = request.get("handled_scope", result["handled_scope"]), request.get("unhandled_scope", result["unhandled_scope"])
        if not _strings(handled) or not _strings(unhandled) or set(handled) & set(unhandled) or set(handled + unhandled) != set(order["scope"]):
            return self._reject("explicit_adoption_partition_required")
        if not set(handled) <= set(result["handled_scope"]):
            return self._reject("adoption_scope_expansion")
        if stale and status in {"adopted", "partially_adopted"}:
            return self._reject("stale_result_requires_recheck")
        if status == "adopted" and unhandled:
            return self._reject("unhandled_scope_requires_partial_adoption")
        if status in {"adopted", "partially_adopted"} and result["metadata"]["network"].get("professional_successful") is not True:
            return self._reject("unsuccessful_professional_result")
        updated = copy.deepcopy(result)
        updated.update(revision=result["revision"] + 1, basis_refs=_unique([_ref(order)] + basis),
                       handled_scope=handled, unhandled_scope=unhandled, limitations=request["limitations"],
                       adoption_needed=status == "recheck", next_trigger=request.get("next_trigger", result["next_trigger"]))
        if stale:
            # Recheck/rejection retires old direct result references. Historical
            # revisions remain history, never usable authority for the new scope.
            updated["result_refs"] = []
        updated["compatibility"] = {"status": "current" if not stale else "recheck_required", "basis_refs": basis}
        updated["adoption"] = {"status": status, "by": role, "basis_refs": basis}
        updated["metadata"]["network"]["phase"] = status
        if status == "recheck":
            updated["metadata"]["network"]["professional_successful"] = False
            updated["next_trigger"] = request.get("next_trigger", "Dispatch a new legal scoped professional recheck; this receipt remains unresolved")
        saved = self._save(role, request, updated, order["authorization_refs"], basis)
        if saved["status"] == "committed":
            saved["adoption"] = copy.deepcopy(updated["adoption"])
        return saved

    @_serial
    def pending(self, capability):
        state = self.store.read_context()
        if state.get("status") != "ok":
            return self._reject("current_state_unavailable", "not_saved")
        role, pending = self._role(capability), []
        results = {}
        for obj in state["objects"]:
            if obj["type"] == "WorkResult":
                results.setdefault(obj["work_order_ref"]["id"], []).append(obj)
        for order in state["objects"]:
            if order["type"] != "WorkOrder" or order.get("metadata", {}).get("network", {}).get("version") != VERSION:
                continue
            if role != "AG0" and role not in {order["requester"], order["assignee"], order["return_owner"]}:
                continue
            error = self._current([_ref(order)] + order["basis_refs"], order["decision_type"])
            # Each explicit run has its own result and adoption responsibility.
            # Adopting one result never disposes of another run's candidate.
            for result in results.get(order["id"]) or [None]:
                result_error = error
                if result and not result_error:
                    result_error = self._current([_ref(result)] + result["basis_refs"] + result["result_refs"], order["decision_type"])
                adoption = result.get("adoption", {}).get("status") if result else None
                if adoption == "adopted" and not result_error:
                    continue
                pending.append({"order_ref": _ref(order), "responsible_owner": order["metadata"]["network"]["responsible_owner"],
                                "unhandled_owner": order["requester"],
                                "acceptance": order["acceptance"]["status"], "result_ref": _ref(result) if result and not result_error else None,
                                "adoption": adoption if not result_error else "recheck", "blocked": bool(result_error),
                                "unhandled_scope": result["unhandled_scope"] if result and not result_error else order["acceptance"]["unhandled_scope"],
                                "next_trigger": result["next_trigger"] if result and not result_error else order["next_trigger"]})
        return self._reply("ok", state_revision=state["state_revision"], pending=pending)

    @_serial
    def takeover(self, capability, request):
        error = self._shape(request)
        if error:
            return error
        if self._role(capability) != "AG0":
            return self._reject("only_ag0_may_takeover")
        activity, error = self._load(request.get("activity_ref"), "ActivitySpec", "teaching")
        if error:
            return error
        basis = _unique(request["basis_refs"] + activity.get("goal_refs", []) + activity.get("criterion_refs", [])
                        + activity.get("material_refs", []) + activity.get("reference_refs", [])
                        + activity.get("authority_refs", []) + [activity["budget_ref"]])
        error = self._current(basis, "teaching")
        if error:
            return error
        before = self.store.read_context()
        prior = [obj for obj in before.get("objects", []) if obj["type"] == "ControlState"
                 and obj["id"].startswith("FIX-network-execution-")
                 and obj.get("execution", {}).get("activity_ref") == request["activity_ref"]]
        old_control = max(prior, key=lambda obj: obj["execution"]["execution_epoch"], default=None)
        old_executor = old_control["execution"].get("current_executor") if old_control else None
        receipt = self.store.set_execution(request["expected_state_revision"], request["operation_id"], request["activity_ref"],
                                           self._capabilities[capability][1], basis, request.get("expected_epoch"))
        if receipt.get("status") == "committed":
            for old_cap, (role, executor) in list(self._capabilities.items()):
                if old_cap is not capability and executor == old_executor:
                    del self._capabilities[old_cap]
        # No previous local capability can pass a new gate after this atomic
        # update; methods and presentation share the same reentrant mutex.
        return self._reply(receipt.get("status", "not_saved"), **{key: copy.deepcopy(value) for key, value in receipt.items() if key != "status"})

    @_serial
    def present(self, capability, request):
        error = self._shape(request, mutation=False)
        if error:
            return error
        if self._role(capability) != "AG0":
            return self._reject("only_ag0_may_present")
        packet = copy.deepcopy(request.get("professional_request", {}))
        if type(request.get("execution_epoch")) is not int or not isinstance(request.get("basis_refs"), list):
            return self._reject("explicit_presentation_epoch_and_basis_required")
        if packet.get("action") != "open" or packet.get("synthetic_only") is not True:
            return self._reject("explicit_open_packet_required")
        if packet.get("activity_ref") != request.get("activity_ref"):
            return self._reject("presentation_activity_mismatch")
        error = self._execution(capability, packet, request.get("execution_epoch"), request.get("basis_refs"))
        if error:
            return error
        raw = SingleEntryService(self.store)._dispatch("teaching.run", packet, self.store)
        if raw.get("status") != "ready" or not isinstance(raw.get("learner_packet"), dict):
            return self._reject("learner_packet_not_ready", state_revision=raw.get("state_revision"))
        error = self._execution(capability, packet, request.get("execution_epoch"), request.get("basis_refs"))
        if error:
            return error
        return self._reply("ready", state_revision=raw.get("state_revision"), activity_ref=request["activity_ref"],
                           learner_packet={key: copy.deepcopy(raw["learner_packet"][key]) for key in ("prompt", "visible_input") if key in raw["learner_packet"]})

    @_serial
    def execute(self, capability, request):
        """AG0's ordinary authorized short path, without network work orders."""
        error = self._shape(request)
        if error:
            return error
        operation, packet = request.get("operation"), copy.deepcopy(request.get("professional_request"))
        if self._role(capability) != "AG0" or operation not in OPERATIONS or not isinstance(packet, dict) or owner_for(operation, packet) != "AG0":
            return self._reject("ag0_short_path_scope")
        if "expected_state_revision" in packet or packet.get("synthetic_only") is not True:
            return self._reject("explicit_professional_request_required")
        _, error = self._definition_controls(operation, packet, "teaching" if operation == "teaching.run" else "professional_review")
        if error:
            return error
        if operation == "teaching.run":
            error = self._execution(capability, packet)
            if error:
                return error
        state = self.store.read_context()
        if state.get("state_revision") != request["expected_state_revision"]:
            return self._reject("state_revision_conflict", "conflict", state_revision=state.get("state_revision"))
        if is_write({"operation": operation, "request": packet}):
            packet["expected_state_revision"] = state["state_revision"]
        raw = SingleEntryService(self.store)._dispatch(operation, packet, self.store)
        # Ordinary local work never returns a teacher reference through this
        # learner-facing adapter. Explicit presentation is a separate live gate.
        return self._reply(raw.get("status", "not_saved"), state_revision=raw.get("state_revision", state["state_revision"]),
                           professional_status=raw.get("status", "unknown"), learner_view=self._public_professional(raw),
                           reasons=[{"code": reason["code"]} for reason in raw.get("reasons", []) if isinstance(reason, dict) and "code" in reason])

    @_serial
    def control(self, capability, request):
        error = self._shape(request)
        if error:
            return error
        if self._role(capability) != "AG0":
            return self._reject("only_ag0_may_control")
        action = request.get("action")
        args = (request["expected_state_revision"], request["operation_id"], request["scope_ids"])
        if action == "restrict":
            receipt = self.store.restrict(*args, request["reason"], request.get("intended_uses"))
        elif action == "pause":
            receipt = self.store.pause(*args, request["reason"])
        elif action == "resume":
            receipt = self.store.resume(*args)
        elif action == "delete":
            receipt = self.store.delete_scope(*args, include_indexes=request.get("include_indexes", False))
            if receipt.get("status") in {"committed", "partial", "pending_cleanup"} or receipt.get("pending_cleanup") is True:
                # A conservative context termination also covers index-only
                # deletion of execution control. Rebind before further work.
                self._capabilities.clear()
                receipt["capabilities_invalidated"] = True
                receipt["next_trigger"] = "Bind fresh local role capabilities and reload surviving legal context"
        else:
            return self._reject("unknown_control_action")
        # Dependencies make affected work unusable immediately, even if paused
        # metadata cannot itself be changed. There is no queued task/cache here.
        return self._reply(receipt.get("status", "not_saved"), **{key: copy.deepcopy(value) for key, value in receipt.items() if key != "status"})
