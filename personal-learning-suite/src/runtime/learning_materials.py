"""B2b material packet checks. Declarations and anchors are not proof of truth.

Only synthetic records are supported. LearningStore owns reads and mutations;
this module never grades, teaches, schedules, or executes supplied code.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.contract_rules import PROTOCOL, load_definition, object_refs
from runtime.learning_store import LearningStore

VERSION = "pl-materials/0.1.0"
MODALITIES = ("text", "formula", "figure")
CONTENT_STATES = {"supported", "partial", "pending", "error"}
METHODS = {"source_comparison", "derivation", "test", "expert_review"}
DOMAIN_CHECKS = {
    "math": ("domain", "inference", "boundaries", "completeness"),
    "ai": ("specification", "environment", "normal_cases", "edge_cases", "interpretation"),
    "finance": ("assumptions", "units", "data_time", "scenario"),
    "politics": ("sources", "fact_interpretation_values", "competing_explanations", "causal_limits"),
    "general": ("source_fidelity", "conditions", "scope"),
}


def fact(status, reason=None, value=None):
    return {"status": status, "value": value} if status == "known" else {"status": status, "reason": reason}


def ref(record):
    return {"id": record["id"], "revision": record["revision"]}


def issue(code):
    # Error output contains no input excerpts, content hashes, or source claims.
    return {"code": code}


def valid_fact(value):
    if not isinstance(value, dict):
        return False
    if value.get("status") == "known":
        return "value" in value
    return value.get("status") in {"unknown", "not_required", "not_applicable", "not_executed"} and bool(value.get("reason")) and "value" not in value


def nonempty_strings(value):
    return isinstance(value, list) and bool(value) and all(isinstance(v, str) and bool(v.strip()) for v in value)


def reference_paths(value, path=()):
    """Keep nested dual-source paths when deriving a non-authoritative view."""
    if isinstance(value, dict):
        if "id" in value and "type" not in value:
            yield path, value
        for key, item in value.items():
            yield from reference_paths(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from reference_paths(item, path + (str(index),))


class MaterialsService:
    """Development AG2 helper; entry_actor remains a fixture configuration."""

    def __init__(self, store):
        self.store = store

    def read_fragment(self, request):
        """Extract an explicit text segment, leaving all semantic checks pending."""
        context = self.store.read_context()
        if context.get("status") != "ok" or not context.get("synthetic_only"):
            return {"status": "blocked", "reasons": [issue("workspace_unavailable")]}
        identifier = request.get("fragment_id", "")
        source = request.get("source_ref", {})
        if not isinstance(identifier, str) or not identifier.startswith("FIX-") or not isinstance(source, dict) or source.get("identity_kind") != "synthetic" or not all(source.get(k) for k in ("source_id", "declared_revision", "locator")):
            return {"status": "rejected", "reasons": [issue("synthetic_source_required")]}
        segment = self.store.read_artifact_segment(request.get("artifact_ref"), request.get("start_line"), request.get("end_line"), "material_read")
        if segment.get("status") != "ok":
            return segment
        fragment = {
            "type": "SourceFragment", "id": identifier, "revision": 1,
            "owner": "AG2", "schema_version": PROTOCOL, "basis_refs": [],
            "source_ref": copy.deepcopy(source),
            "artifact_ref": segment["artifact_ref"],
            "read_scope": {
                "text": fact("known", value={"start_line": segment["start_line"], "end_line": segment["end_line"], "kind": "text_extraction_only"}),
                "formula": fact("unknown", "Text extraction does not verify formulas."),
                "figure": fact("unknown", "Figures have not been inspected."),
            },
            "claims": fact("unknown", "Extracted text has not been interpreted or verified."),
            "verification": {"content": {"status": "pending", "checked_revision": 1, "scope": "extracted segment", "conditions": [], "anchor_refs": [], "unchecked_scope": ["meaning", "formula", "figure"]}},
            "unread_parts": fact("known", value=["Outside the explicitly selected line range.", "Formula and figure meaning remain unverified."]),
        }
        return {"status": "candidate", "state_revision": segment["state_revision"], "fragment": fragment, "text": segment["text"], "mutated": False, "semantic_verification": "not_executed"}

    def _objects(self, refs, incoming=None, intended_use="material_review"):
        incoming = incoming or []
        proposed = {(o.get("id"), o.get("revision")): o for o in incoming if isinstance(o, dict)}
        existing = [r for r in refs if (r.get("id"), r.get("revision")) not in proposed]
        result = self.store.read_refs(existing, intended_use)
        if result.get("status") != "ok":
            return {}, result.get("reasons", [issue("references_unavailable")])
        index = {(o["id"], o["revision"]): o for o in result["objects"]}
        index.update(proposed)
        return index, []

    @staticmethod
    def _source_problems(source, required_modalities=()):
        problems = []
        scopes = source.get("read_scope", {})
        if not isinstance(scopes, dict) or any(not valid_fact(scopes.get(m)) for m in MODALITIES):
            return [issue("modality_facts_required")]
        for modality in required_modalities:
            if scopes[modality]["status"] != "known":
                problems.append(issue("required_modality_unread"))
        if not valid_fact(source.get("unread_parts")):
            problems.append(issue("unread_scope_required"))
        verification = source.get("verification")
        if not isinstance(verification, dict) or not isinstance(verification.get("content"), dict) or verification["content"].get("status") not in CONTENT_STATES:
            problems.append(issue("source_verification_required"))
        return problems

    def inspect_material(self, material, context, incoming=None):
        """Check completeness, exact compatibility, and annotated operation leaks.

        'compatible' describes a declared, reviewable packet; the helper cannot
        establish mathematical truth or detect unannotated semantic leakage.
        """
        errors = []
        if not isinstance(material, dict) or not isinstance(context, dict):
            return {"status": "rejected", "reasons": [issue("material_context_required")]}
        definition = load_definition()
        required = definition["base_required"] + definition["objects"]["MaterialUse"]["required"]
        if material.get("type") != "MaterialUse" or material.get("owner") != "AG2" or material.get("schema_version") != PROTOCOL or any(k not in material for k in required):
            return {"status": "rejected", "reasons": [issue("material_contract")]}
        if not isinstance(material.get("id"), str) or not material["id"].startswith("FIX-") or type(material.get("revision")) is not int or material["revision"] < 1:
            return {"status": "rejected", "reasons": [issue("synthetic_material_required")]}
        modality_list = context.get("required_modalities")
        if not nonempty_strings(modality_list) or not set(modality_list).issubset(MODALITIES):
            return {"status": "rejected", "reasons": errors + [issue("required_modalities_required")]}
        if context.get("purpose") not in {"teaching", "independent", "comparison"} or not nonempty_strings(context.get("conditions")) or not context.get("intended_use"):
            errors.append(issue("use_context_required"))
        goals = material.get("goal_refs", [])
        fragments = material.get("fragment_refs", [])
        activity_ref = context.get("activity_ref")
        if not isinstance(goals, list) or not goals or not isinstance(fragments, list) or not fragments or not isinstance(activity_ref, dict):
            return {"status": "rejected", "reasons": errors + [issue("typed_references_required")]}
        refs = goals + fragments + [activity_ref]
        if not all(isinstance(r, dict) and "id" in r and type(r.get("revision")) is int for r in refs):
            return {"status": "rejected", "reasons": errors + [issue("typed_references_required")]}
        index, problems = self._objects(refs, incoming, context.get("intended_use", "material_review"))
        if problems:
            return {"status": "blocked", "reasons": problems, "mutated": False}
        source_objects = [index.get((r["id"], r["revision"])) for r in fragments]
        goal_objects = [index.get((r["id"], r["revision"])) for r in goals]
        activity = index.get((activity_ref["id"], activity_ref["revision"]))
        if any(not o or o.get("type") != "SourceFragment" for o in source_objects) or any(not o or o.get("type") != "GoalSpec" for o in goal_objects) or not activity or activity.get("type") != "ActivitySpec":
            return {"status": "rejected", "reasons": errors + [issue("reference_type_mismatch")]}
        if goals != context.get("goal_refs") or material.get("intended_use") != context.get("intended_use") or any(g not in activity.get("goal_refs", []) for g in goals):
            errors.append(issue("use_binding_mismatch"))
        for source in source_objects:
            errors.extend(self._source_problems(source, modality_list))
            source_verification = source.get("verification", {})
            source_content = source_verification.get("content", {}) if isinstance(source_verification, dict) else {}
            if isinstance(source_content, dict) and source_content.get("status") == "error":
                errors.append(issue("source_content_error"))
        own_guard = self.store.validate_refs([ref(material)], context.get("intended_use", "material_review"))
        own_problems = [p for p in own_guard.get("reasons", []) if p.get("code") != "missing_reference"]
        if own_guard.get("status") == "not_saved" or own_problems:
            return {"status": "blocked", "reasons": own_problems or [issue("material_control_unavailable")], "mutated": False}
        current = self.store.read_context()
        if current.get("status") != "ok":
            return {"status": "blocked", "reasons": [issue("current_state_unavailable")], "mutated": False}
        latest = {o["id"]: o["revision"] for o in current["objects"]}
        proposed = {(o.get("id"), o.get("revision")) for o in incoming or []}
        if any((r["id"], r["revision"]) not in proposed and latest.get(r["id"]) != r["revision"] for r in refs):
            errors.append(issue("stale_basis_reference"))
        operations = set(activity.get("learner_operations", []))
        if not operations:
            errors.append(issue("learner_operations_required"))
        verification = material.get("verification", {})
        content = verification.get("content", {}) if isinstance(verification, dict) else {}
        use = verification.get("use", {}) if isinstance(verification, dict) else {}
        if not isinstance(content, dict) or not isinstance(use, dict):
            return {"status": "rejected", "reasons": errors + [issue("verification_scope_required")]}
        for part in (content, use):
            if not isinstance(part, dict) or part.get("status") not in CONTENT_STATES or part.get("checked_revision") != material.get("revision") or not part.get("scope") or not isinstance(part.get("unchecked_scope"), list) or not nonempty_strings(part.get("conditions")):
                errors.append(issue("verification_scope_required"))
        if content.get("status") != "supported" or use.get("status") != "supported":
            errors.append(issue("limited_or_pending_verification"))
        if content.get("method") not in METHODS or content.get("reviewer") != "AG2" or not content.get("anchor_refs"):
            errors.append(issue("verification_anchor_required"))
        anchors = content.get("anchor_refs", [])
        if not isinstance(anchors, list) or not all(isinstance(a, dict) for a in anchors):
            errors.append(issue("verification_anchor_required"))
        else:
            # Only managed exact references; existence is not semantic correctness.
            for anchor in anchors:
                if "path" in anchor:
                    checked = self.store.read_artifact_segment(anchor, anchor.get("start_line"), anchor.get("end_line"), context.get("intended_use", "material_review"))
                else:
                    checked = self.store.validate_refs([anchor], context.get("intended_use", "material_review"))
                if checked.get("status") != "ok":
                    errors.append(issue("verification_anchor_unavailable"))
        binding = use.get("binding", {})
        if not isinstance(binding, dict) or any(binding.get(k) != context.get(k) for k in ("goal_refs", "activity_ref", "intended_use", "required_modalities", "conditions", "purpose")) or use.get("reviewer") != "AG2":
            errors.append(issue("use_binding_mismatch"))
        domain = content.get("domain")
        checks = content.get("domain_checks", {})
        if domain not in DOMAIN_CHECKS or not isinstance(checks, dict) or any(not valid_fact(checks.get(k)) or checks[k]["status"] not in {"known", "not_applicable", "not_required"} for k in DOMAIN_CHECKS.get(domain, ())):
            errors.append(issue("domain_checks_incomplete"))
        substituted = set()
        potential = set()
        for field in ("visible_input", "backup_help", "teacher_reference"):
            entries = material.get(field)
            if not isinstance(entries, list):
                errors.append(issue("partition_entries_required"))
                continue
            for entry in entries:
                if not isinstance(entry, dict) or not entry.get("content") or not isinstance(entry.get("provided_operations"), list) or not entry.get("channel"):
                    errors.append(issue("presentation_annotation_required"))
                    continue
                provided = entry["provided_operations"]
                if not all(isinstance(op, str) for op in provided):
                    errors.append(issue("presentation_annotation_required"))
                    continue
                potential.update(set(provided).intersection(operations))
                if field == "visible_input":
                    substituted.update(set(provided).intersection(operations))
        if substituted and context.get("purpose") == "independent":
            errors.append(issue("target_operation_provided"))
        if not valid_fact(material.get("actual_exposure")) or material["actual_exposure"]["status"] != "unknown":
            errors.append(issue("preparation_cannot_record_exposure"))
        return {
            "status": "compatible" if not errors else "limited",
            "reasons": errors, "content_status": content.get("status", "pending"),
            "substituted_operations": sorted(substituted), "potential_help_operations": sorted(potential),
            "mutated": False, "semantic_verification": "agent_declaration_with_managed_anchors",
            "limitations": ["The helper checks declared metadata and references, not truth, hidden visual clues, or actual display."] ,
        }

    def submit_material(self, request):
        """Submit a reviewed P-Material through the original CAS/authority gate."""
        if self.store.entry_actor != "AG2":
            return {"status": "rejected", "reasons": [issue("ag2_fixture_actor_required")]}
        changes = request.get("changes", [])
        if not isinstance(changes, list) or not changes or any(not isinstance(o, dict) or o.get("type") not in {"SourceFragment", "MaterialUse", "WorkResult"} or o.get("owner") != "AG2" for o in changes):
            return {"status": "rejected", "reasons": [issue("material_objects_only")]}
        # Stop controls before interpreting a caller's candidate payload.
        refs = list(object_refs(changes)) + request.get("authorization_refs", []) + request.get("adoption_refs", [])
        incoming_keys = {(o.get("id"), o.get("revision")) for o in changes}
        external = [r for r in refs if (r.get("id"), r.get("revision")) not in incoming_keys]
        guard = self.store.validate_refs(external, "material_review")
        if guard.get("status") != "ok":
            return guard
        for source in (o for o in changes if o["type"] == "SourceFragment"):
            errors = self._source_problems(source)
            if errors:
                return {"status": "rejected", "reasons": errors}
        for material in (o for o in changes if o["type"] == "MaterialUse"):
            inspection = self.inspect_material(material, request.get("context", {}), changes)
            if inspection["status"] != "compatible":
                return {"status": "rejected", "reasons": inspection["reasons"]}
        for result in (o for o in changes if o["type"] == "WorkResult"):
            order = self.store.read_refs([result.get("work_order_ref", {})], "material_review")
            if order.get("status") != "ok":
                return order
            work = order["objects"][0]
            if work.get("type") != "WorkOrder" or work.get("assignee") != "AG2" or work.get("acceptance", {}).get("status") not in {"accepted", "partially_accepted"} or result.get("decision_type") != work.get("decision_type"):
                return {"status": "rejected", "reasons": [issue("accepted_material_work_required")]}
        return self.store.commit(
            expected_state_revision=request.get("expected_state_revision"),
            operation_id=request.get("operation_id"), changes=changes,
            artifacts=request.get("artifacts", {}), authorization_refs=request.get("authorization_refs", []),
            adoption_refs=request.get("adoption_refs", []),
        )

    def trace_change(self, request):
        """Trace known direct references and return separate recovery responsibilities.

        This read-only view is not a complete semantic dependency inventory.
        'change --restrict' additionally issues a store control gate first.
        """
        changed = request.get("changed_refs", [])
        checked = self.store.validate_refs(changed, "read")
        if checked.get("status") != "ok" or not changed:
            return {"status": "blocked", "reasons": checked.get("reasons", [issue("changed_refs_required")])}
        state = self.store.read_context()
        if state.get("status") != "ok":
            return state
        affected = {r["id"] for r in changed}
        objects = state["objects"]
        while True:
            new = {o["id"] for o in objects if any(r.get("id") in affected for r in object_refs(o))}
            if new.issubset(affected):
                break
            affected.update(new)
        edges = []
        for obj in objects:
            if obj["id"] not in affected:
                continue
            for field, value in obj.items():
                for nested_path, target in reference_paths(value, (field,)):
                    if target["id"] in affected:
                        chain = "requirement" if obj["type"] == "GoalSpec" and "requirement_source_refs" in nested_path else "content"
                        edges.append({"from_ref": target, "to_ref": ref(obj), "relation": field, "locator": "/".join(nested_path), "chain": chain})
        recovery = {name: {"owner": owner, "status": "pending", "action": action} for name, owner, action in (
            ("material_recovery", "AG2", "Verify corrected sources and each affected material use."),
            ("judgment_recovery", "AG3", "Reassess sufficient original responses without automatically adding a test."),
            ("teaching_recovery", "AG0", "Check and repair actual misleading exposure; preserve original events."),
            ("planning_recovery", "AG1", "Review criteria and commitments only where the correction changes them."),
        )}
        return {"status": "candidate", "state_revision": state["state_revision"], "changed_refs": changed,
                "affected_refs": [ref(o) for o in objects if o["id"] in affected], "direct_dependencies": edges,
                "unknown_dependencies": fact("unknown", "Only recorded ObjectRefs are traced; unrecorded semantic dependencies remain unknown."),
                "recovery": recovery, "mutated": False, "professional_restrictions_lifted": False}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--request", required=True, help="UTF-8 synthetic JSON request; caller-owned file, outside deletion scope.")
    parser.add_argument("command", choices=("read", "inspect", "submit", "change"))
    parser.add_argument("--restrict", action="store_true", help="With change, restrict affected source uses before returning the trace.")
    args = parser.parse_args()
    try:
        request = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
        if not isinstance(request, dict):
            raise ValueError()
        service = MaterialsService(LearningStore(args.workspace, entry_actor="AG2"))
        if args.command == "read":
            result = service.read_fragment(request)
        elif args.command == "inspect":
            result = service.inspect_material(request.get("material"), request.get("context"))
        elif args.command == "submit":
            result = service.submit_material(request)
        else:
            if args.restrict:
                gate = service.store.restrict(expected_state_revision=request["expected_state_revision"], operation_id=request["operation_id"], scope_ids=[r["id"] for r in request["changed_refs"]], reason=request["reason"], intended_uses=request.get("intended_uses", ["material_review", "independent_check", "teaching", "assessment", "use"]))
                if gate.get("status") != "committed":
                    result = gate
                else:
                    result = service.trace_change(request)
                    result.update(control_receipt=gate, mutated=True)
            else:
                result = service.trace_change(request)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        result = {"status": "rejected", "reasons": [issue("invalid_or_unavailable_request")]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"candidate", "compatible", "committed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
