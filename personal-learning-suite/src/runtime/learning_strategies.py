"""B3c strategy resources and synthetic configuration declarations.

This helper does not rank methods, verify subject truth, teach, score, or plan.
Generic resources are immutable inputs; personal configurations use LearningStore.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.contract_rules import PROTOCOL, SUITE_ROOT, load_definition, object_refs
from runtime.learning_store import LearningStore
from runtime.learning_materials import MaterialsService, fact, issue, nonempty_strings, ref, valid_fact

VERSION = "pl-strategies/0.1.0"
CONFIG_VERSION = "pl-strategies-input/0.2.0"
BINDING_FIELDS = ("synthetic_only", "intended_work", "goal_refs", "activity_ref", "material_refs",
                  "purpose", "conditions", "allowed_resources", "budget_ref", "requires_time_condition", "material_context")
COST_FIELDS = ("preparation", "execution", "feedback", "verification", "closure")


def known_bool(value, expected=True):
    return valid_fact(value) and value.get("status") == "known" and type(value.get("value")) is bool and value["value"] is expected


def exact_ref(value):
    return isinstance(value, dict) and isinstance(value.get("id"), str) and value["id"].startswith("FIX-") and type(value.get("revision")) is int and value["revision"] > 0


class StrategyCatalog:
    """Read only registered local generic resources; a title is never a bundle."""

    def __init__(self, resource_root=None, project_root=None):
        self.root = Path(resource_root or SUITE_ROOT / "resources/strategies").resolve()
        self.project_root = Path(project_root or SUITE_ROOT.parent).resolve()

    def _path(self, relative):
        if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
            raise ValueError("invalid resource path")
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or path == self.root:
            raise ValueError("resource path outside catalog")
        return path

    def _manifest(self):
        manifest = json.loads(self._path("manifest.json").read_text(encoding="utf-8-sig"))
        if manifest.get("resource_revision") != VERSION:
            raise ValueError("resource revision")
        for source in manifest["source_fingerprints"]:
            path = (self.project_root / source["workspace_relative_path"]).resolve()
            if not path.is_relative_to(self.project_root) or hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
                raise ValueError("source changed")
        return manifest

    def _verified_json(self, relative, manifest):
        entries = manifest["resources"]
        if isinstance(entries, dict):
            item = entries.get(relative)
        else:
            item = next((entry for entry in entries if entry.get("path", entry.get("relative_path")) == relative), None)
        if not isinstance(item, dict):
            raise ValueError("unregistered resource")
        data = self._path(relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != item.get("sha256"):
            raise ValueError("resource changed")
        return json.loads(data.decode("utf-8-sig"))

    def index(self, work=None):
        try:
            manifest = self._manifest()
            index = self._verified_json("strategy-index.json", manifest)
            if index.get("resource_revision") != VERSION:
                raise ValueError("index revision")
            entries = index["entries"]
            if work:
                if not isinstance(work, str):
                    raise ValueError("work must be text")
                entries = [entry for entry in entries if work.casefold() in json.dumps(entry, ensure_ascii=False).casefold()]
            return {"status": "ok", "resource_revision": VERSION, "entries": entries,
                    "mutated": False, "executable": False, "ranking": None,
                    "limitations": ["Index navigation does not establish adaptation, truth, or effectiveness."]}
        except (OSError, ValueError, TypeError, KeyError, StopIteration):
            return {"status": "blocked", "reasons": [issue("resource_integrity_unavailable")], "mutated": False}

    def load(self, resource_key):
        try:
            manifest = self._manifest()
            index = self._verified_json("strategy-index.json", manifest)
            entry = next((entry for entry in index["entries"] if entry.get("resource_key") == resource_key), None)
            if entry is None:
                return {"status": "blocked", "reasons": [issue("unknown_resource_key")], "mutated": False}
            if entry.get("compiled") is not True:
                return {"status": "needs_source_review", "resource_key": resource_key,
                        "source_refs": entry.get("source_refs", []), "executable": False, "mutated": False}
            resource = self._verified_json(entry["bundle_path"], manifest)
            if resource.get("resource_key") != resource_key or resource.get("resource_revision") != VERSION:
                raise ValueError("bundle identity")
            required = ("source_refs", "intended_work", "prerequisites", "exclusions", "required_learner_operations",
                        "help_and_feedback_constraints", "stop_or_return_conditions", "evidence_limits",
                        "original_claim_status", "local_adaptations", "review_status", "conditions")
            if any(key not in resource for key in required) or not resource["conditions"]:
                raise ValueError("incomplete bundle")
            if not isinstance(resource.get("content_markdown"), str) or not resource["content_markdown"].strip():
                raise ValueError("body required")
            if resource.get("resource_kind") == "encoding-card-bundle":
                carriers = resource.get("full_carriers", {})
                rules = resource.get("common_rules", {})
                if (not isinstance(carriers, dict) or any(not isinstance(carriers.get(key), dict)
                        or not carriers[key].get("content_markdown") for key in ("R02", "R03"))
                        or not isinstance(rules, dict) or any(not isinstance(rules.get(key), dict)
                        or not rules[key].get("content_markdown") for key in ("opening", "closing"))):
                    raise ValueError("full carriers and shared rules required")
            elif resource.get("resource_kind") == "post-method-note":
                excerpts = resource.get("source_excerpts")
                if not isinstance(excerpts, list) or not excerpts or any(not isinstance(part, dict) or not part.get("content_markdown") or not part.get("source_ref") for part in excerpts):
                    raise ValueError("post sources required")
            else:
                raise ValueError("unsupported resource kind")
            return {"status": "ok", "resource": resource, "executable": False, "mutated": False,
                    "limitations": ["Complete source constraints require current task adaptation and subject verification."]}
        except (OSError, ValueError, TypeError, KeyError):
            return {"status": "blocked", "reasons": [issue("resource_integrity_unavailable")], "mutated": False}


class StrategiesService:
    """AG1 fixture configuration helper; the actor parameter is not authentication."""

    def __init__(self, store, catalog=None):
        self.store = store
        self.catalog = catalog or StrategyCatalog()

    def _context(self, context):
        if not isinstance(context, dict) or context.get("synthetic_only") is not True:
            return None, [issue("synthetic_context_required")]
        goals, materials = context.get("goal_refs"), context.get("material_refs")
        if (not isinstance(goals, list) or not goals or not isinstance(materials, list) or not materials
                or any(not exact_ref(r) for r in goals + materials)
                or not exact_ref(context.get("activity_ref")) or not exact_ref(context.get("budget_ref"))):
            return None, [issue("typed_context_refs_required")]
        if (not isinstance(context.get("intended_work"), str) or not context["intended_work"].strip()
                or context.get("purpose") not in {"teaching", "independent"}
                or not nonempty_strings(context.get("conditions"))
                or not isinstance(context.get("allowed_resources"), list)
                or any(not isinstance(r, str) or not r.strip() for r in context["allowed_resources"])
                or type(context.get("requires_time_condition")) is not bool
                or type(context.get("selection_needed")) is not bool):
            return None, [issue("work_context_required")]
        refs = goals + materials + [context["activity_ref"], context["budget_ref"]]
        state = self.store.read_context()
        read = self.store.read_refs(refs, "strategy_configuration")
        if state.get("status") != "ok" or read.get("status") != "ok":
            return None, read.get("reasons", [issue("context_unavailable")])
        if state.get("state_revision") != read.get("state_revision"):
            return None, [issue("context_changed")]
        latest = {obj["id"]: obj["revision"] for obj in state["objects"]}
        if any(latest.get(r["id"]) != r["revision"] for r in refs):
            return None, [issue("stale_basis_reference")]
        index = {(obj["id"], obj["revision"]): obj for obj in read["objects"]}
        if (any(index[(r["id"], r["revision"])]["type"] != "GoalSpec" for r in goals)
                or any(index[(r["id"], r["revision"])]["type"] != "MaterialUse" for r in materials)
                or index[(context["budget_ref"]["id"], context["budget_ref"]["revision"])]["type"] != "BudgetEnvelope"):
            return None, [issue("context_type_mismatch")]
        activity = index[(context["activity_ref"]["id"], context["activity_ref"]["revision"])]
        if activity["type"] != "ActivitySpec" or any(r not in activity.get("goal_refs", []) for r in goals) or any(r not in activity.get("material_refs", []) for r in materials) or activity.get("budget_ref") != context["budget_ref"]:
            return None, [issue("activity_binding_mismatch")]
        needed_time = False
        for goal_ref in goals:
            goal = index[(goal_ref["id"], goal_ref["revision"])]
            allowed = goal.get("allowed_resources", [])
            if isinstance(allowed, dict):
                allowed = allowed.get("value") if allowed.get("status") == "known" else None
            if not isinstance(allowed, list) or any(resource not in allowed for resource in context["allowed_resources"]):
                return None, [issue("goal_resource_scope_mismatch")]
            if context["purpose"] == "independent":
                time = goal.get("time_requirements", {})
                if not isinstance(time, dict):
                    return None, [issue("goal_time_scope_unresolved")]
                if time.get("status") == "known":
                    value = time.get("value")
                    if not isinstance(value, dict) or not isinstance(value.get("requirement_ids"), list) or any(not isinstance(k, str) or not k for k in value["requirement_ids"]):
                        return None, [issue("goal_time_scope_unresolved")]
                    target_ids = {r.get("locator", "").split("/", 1)[1] for r in activity.get("criterion_refs", [])
                                  if r.get("id") == goal_ref["id"] and r.get("revision") == goal_ref["revision"]
                                  and isinstance(r.get("locator"), str) and r["locator"].startswith("requirements/")}
                    if not target_ids:
                        return None, [issue("goal_time_scope_unresolved")]
                    needed_time = needed_time or bool(target_ids.intersection(value["requirement_ids"]))
                elif time.get("status") not in {"not_required", "not_applicable"}:
                    return None, [issue("goal_time_scope_unresolved")]
        if context["purpose"] == "independent" and context["requires_time_condition"] != needed_time:
            return None, [issue("goal_time_scope_mismatch")]
        material_context = context.get("material_context")
        if (not isinstance(material_context, dict) or material_context.get("activity_ref") != context["activity_ref"]
                or material_context.get("goal_refs") != goals):
            return None, [issue("material_use_context_required")]
        for material_ref in materials:
            material = index[(material_ref["id"], material_ref["revision"])]
            verification = material.get("verification", {})
            if (not isinstance(verification, dict) or any(not isinstance(verification.get(axis), dict)
                    or verification[axis].get("status") != "supported"
                    or verification[axis].get("checked_revision") != material["revision"] for axis in ("content", "use"))):
                return None, [issue("current_material_verification_required")]
            inspection = MaterialsService(self.store).inspect_material(material, material_context)
            if inspection.get("status") != "compatible":
                return None, inspection.get("reasons") or [issue("material_use_not_compatible")]
            if context["purpose"] == "independent" and material_context.get("purpose") != "independent":
                return None, [issue("independent_material_use_required")]
        current = self.store.read_context()
        if current.get("status") != "ok" or current.get("state_revision") != state["state_revision"]:
            return None, [issue("context_changed")]
        return activity, []

    def inspect_config(self, config, context):
        try:
            return self._inspect_config(config, context)
        except (ValueError, KeyError, TypeError, AttributeError):
            return {"status": "rejected", "reasons": [issue("invalid_strategy_shape")], "mutated": False}

    @staticmethod
    def _adopted(config, context):
        adoption = config.get("adoption", {})
        if (not isinstance(adoption, dict) or adoption.get("status") != "adopted" or adoption.get("by") != "AG1"
                or not isinstance(adoption.get("basis_refs"), list) or not adoption["basis_refs"]
                or any(not exact_ref(r) for r in adoption["basis_refs"])
                or not isinstance(adoption.get("scope"), (str, list, dict)) or not adoption["scope"]
                or not isinstance(adoption.get("limitations"), list)
                or any(not isinstance(item, str) for item in adoption["limitations"])
                or not valid_fact(adoption.get("time"))):
            return False
        scope = adoption["scope"]
        return not isinstance(scope, dict) or all(scope[key] == context.get(key) for key in scope if key in BINDING_FIELDS)

    def _inspect_config(self, config, context):
        activity, errors = self._context(context)
        if errors:
            return {"status": "blocked", "reasons": errors, "mutated": False}
        if config is None and context["selection_needed"] is False and known_bool(context.get("existing_activity_reliable")):
            return {"status": "direct_reuse", "activity_ref": context["activity_ref"], "catalog_loaded": False,
                    "mutated": False, "teaching_started": False, "new_performance_events": 0}
        if not isinstance(config, dict):
            return {"status": "rejected", "reasons": [issue("config_required")], "mutated": False}
        required = load_definition()["base_required"] + load_definition()["objects"]["MethodConfig"]["required"]
        if (config.get("type") != "MethodConfig" or config.get("owner") != "AG1" or config.get("schema_version") != PROTOCOL
                or any(k not in config for k in required) or not exact_ref(ref(config))):
            return {"status": "rejected", "reasons": [issue("method_config_contract")], "mutated": False}
        own = self.store.validate_refs([ref(config)], "strategy_configuration")
        problems = [p for p in own.get("reasons", []) if p.get("code") != "missing_reference"]
        if own.get("status") == "not_saved" or problems:
            return {"status": "blocked", "reasons": problems or [issue("config_control_unavailable")], "mutated": False}
        refs = list(object_refs(config))
        read = self.store.read_refs(refs, "strategy_configuration")
        if read.get("status") != "ok":
            return {"status": "blocked", "reasons": read.get("reasons", []), "mutated": False}
        state = self.store.read_context()
        latest = {obj["id"]: obj["revision"] for obj in state.get("objects", [])}
        historical = config.get("previous_config")
        current_refs = list(object_refs({k: v for k, v in config.items() if k != "previous_config"}))
        if any(latest.get(r["id"]) != r["revision"] for r in current_refs):
            errors.append(issue("stale_basis_reference"))
        if historical is not None and not any(o.get("type") == "MethodConfig" and ref(o) == historical for o in read["objects"]):
            errors.append(issue("previous_config_type_required"))
        context_refs = context["goal_refs"] + context["material_refs"] + [context["activity_ref"], context["budget_ref"]]
        if any(r not in config.get("basis_refs", []) for r in context_refs):
            errors.append(issue("config_basis_binding_required"))
        if config.get("intended_work") != context["intended_work"] or config.get("resource_revision") != VERSION:
            errors.append(issue("work_or_version_mismatch"))
        selected = config.get("selected_parts")
        if not isinstance(selected, list) or not selected or not all(isinstance(p, dict) for p in selected):
            return {"status": "rejected", "reasons": [issue("selected_parts_required")], "mutated": False}
        keys = [part.get("resource_key") for part in selected]
        if any(not isinstance(k, str) for k in keys) or len(set(keys)) != len(keys):
            return {"status": "rejected", "reasons": [issue("unique_resource_keys_required")], "mutated": False}
        packages = {}
        for part in selected:
            loaded = self.catalog.load(part["resource_key"])
            if loaded["status"] != "ok":
                errors.append(issue("complete_resource_required"))
                continue
            package = loaded["resource"]
            packages[part["resource_key"]] = package
            if (part.get("resource_revision") != package["resource_revision"] or not nonempty_strings(part.get("borrowed_parts"))
                    or not isinstance(part.get("omitted_parts"), list) or any(not isinstance(v, str) for v in part["omitted_parts"])
                    or not isinstance(part.get("non_equivalence"), str) or not part["non_equivalence"].strip()):
                errors.append(issue("borrowed_scope_required"))
            if any(source not in config.get("source_refs", []) for source in package["source_refs"]):
                errors.append(issue("source_identity_or_revision_mismatch"))
            checks = config.get("resource_checks", {}).get(part["resource_key"], {})
            for condition in package["conditions"]:
                if context["purpose"] in condition["required_for"]:
                    if not known_bool(checks.get(condition["key"]), condition.get("scope") != "exclusion"):
                        errors.append(issue("resource_condition_unresolved"))
        for field in ("prerequisites", "exclusions"):
            values = config.get(field)
            if not isinstance(values, list) or not values or any(not isinstance(v, dict) or not v.get("condition") or not known_bool(v.get("check"), field != "exclusions") for v in values):
                errors.append(issue("config_conditions_unresolved"))
        registered_sources = [source for package in packages.values() for source in package["source_refs"]]
        if (not isinstance(config.get("source_refs"), list)
                or any(source not in registered_sources for source in config["source_refs"])):
            errors.append(issue("unregistered_strategy_source"))
        operations = config.get("required_learner_operations")
        if not nonempty_strings(operations) or any(op not in activity.get("learner_operations", []) for op in operations):
            errors.append(issue("learner_work_binding_required"))
        help_info = config.get("help_and_feedback_constraints", {})
        if not isinstance(help_info, dict):
            help_info = {}
        if not known_bool(help_info.get("feedback")):
            errors.append(issue("necessary_feedback_unavailable"))
        if help_info.get("allowed_resources") != context["allowed_resources"]:
            errors.append(issue("allowed_resources_mismatch"))
        provided = help_info.get("provided_operations")
        if not isinstance(provided, list) or any(not isinstance(op, str) for op in provided):
            errors.append(issue("provided_operations_required"))
        elif context["purpose"] == "independent" and set(provided).intersection(operations or []):
            errors.append(issue("target_operation_provided"))
        for field in ("exposure", "contact_history", "time_condition"):
            if not valid_fact(help_info.get(field)):
                errors.append(issue("help_time_fact_required"))
        if context["requires_time_condition"] and not known_bool(help_info.get("time_condition")):
            errors.append(issue("time_condition_unresolved"))
        if context["purpose"] == "independent" and any(help_info.get(field, {}).get("status") != "known" for field in ("exposure", "contact_history")):
            errors.append(issue("independent_conditions_unresolved"))
        costs = config.get("cost", {})
        if not isinstance(costs, dict) or any(not valid_fact(costs.get(field)) for field in COST_FIELDS) or not known_bool(costs.get("budget_fit")):
            errors.append(issue("whole_cost_or_budget_unresolved"))
        if not valid_fact(config.get("interruptibility")):
            errors.append(issue("interruptibility_required"))
        combination = config.get("combination_and_non_equivalence", {})
        if (not isinstance(combination, dict) or not combination.get("rationale") or not known_bool(combination.get("interference_check"))
                or combination.get("single_performance") is not True or not isinstance(combination.get("alternatives"), list)):
            errors.append(issue("combination_scope_required"))
        review = config.get("review_status", {})
        if (not isinstance(review, dict) or review.get("status") != "reviewed" or review.get("reviewer") != "AG1"
                or review.get("binding") != {key: context[key] for key in BINDING_FIELDS}):
            errors.append(issue("current_review_binding_required"))
        limits = config.get("evidence_limits", {})
        if (not isinstance(limits, dict) or not nonempty_strings(limits.get("config_limits"))
                or limits.get("resource_limits") != {k: p["evidence_limits"] for k, p in packages.items()}
                or config.get("original_claim_status") != {k: p["original_claim_status"] for k, p in packages.items()}):
            errors.append(issue("inherited_evidence_limits_required"))
        for field in ("adjustable_parts", "stop_or_return_conditions", "reuse_limits"):
            if not nonempty_strings(config.get(field)):
                errors.append(issue("adaptation_return_reuse_required"))
        if not isinstance(config.get("local_adaptations"), list):
            errors.append(issue("local_adaptations_required"))
        if config.get("previous_config") is not None and not exact_ref(config["previous_config"]):
            errors.append(issue("previous_config_ref_required"))
        return {"status": "compatible" if not errors else "limited", "reasons": errors, "mutated": False,
                "resource_keys": keys, "new_performance_events": 0, "plan_changed": False,
                "adopted": False, "semantic_verification": "declaration_checks_only",
                "limitations": ["No truth, hidden-clue, timing, professional review, or method-effect verification is performed."]}

    def submit_config(self, request):
        try:
            return self._submit_config(request)
        except (ValueError, KeyError, TypeError, AttributeError):
            return {"status": "rejected", "reasons": [issue("invalid_strategy_request")], "mutated": False}

    def _submit_config(self, request):
        if self.store.entry_actor != "AG1":
            return {"status": "rejected", "reasons": [issue("ag1_fixture_actor_required")]}
        if not isinstance(request, dict):
            return {"status": "rejected", "reasons": [issue("config_request_required")]}
        changes = request.get("changes")
        if not isinstance(changes, list) or len(changes) != 1 or not isinstance(changes[0], dict) or changes[0].get("type") != "MethodConfig" or request.get("artifacts"):
            return {"status": "rejected", "reasons": [issue("one_method_config_only")]}
        config = changes[0]
        context = request.get("context")
        inspection = self.inspect_config(config, context)
        if inspection["status"] != "compatible":
            return {"status": "rejected", "reasons": inspection.get("reasons", [issue("compatible_config_required")])}
        adoption = config.get("adoption", {})
        if (not self._adopted(config, context)
                or any(r not in request.get("adoption_refs", []) for r in adoption["basis_refs"])):
            return {"status": "rejected", "reasons": [issue("explicit_config_adoption_required")]}
        return self.store.commit(expected_state_revision=request.get("expected_state_revision"),
                                 operation_id=request.get("operation_id"), changes=changes,
                                 authorization_refs=request.get("authorization_refs", []), adoption_refs=request.get("adoption_refs", []))

    def reuse_config(self, config_ref, context):
        try:
            return self._reuse_config(config_ref, context)
        except (ValueError, KeyError, TypeError, AttributeError):
            return {"status": "rejected", "reasons": [issue("invalid_strategy_request")], "mutated": False}

    def _reuse_config(self, config_ref, context):
        if not exact_ref(config_ref):
            return {"status": "rejected", "reasons": [issue("config_ref_required")], "mutated": False}
        read = self.store.read_refs([config_ref], "strategy_configuration")
        if read.get("status") != "ok":
            return read
        config = read["objects"][0]
        adoption = config.get("adoption", {})
        if config.get("type") != "MethodConfig" or not self._adopted(config, context):
            return {"status": "blocked", "reasons": [issue("adopted_config_required")], "mutated": False}
        state = self.store.read_context()
        if not any(o["id"] == config_ref["id"] and o["revision"] == config_ref["revision"] for o in state.get("objects", [])):
            return {"status": "blocked", "reasons": [issue("stale_config_revision")], "mutated": False}
        result = self.inspect_config(config, context)
        if result["status"] == "compatible":
            result.update(status="reusable", adopted=True, config_ref=config_ref, teaching_started=False)
        return result

    def trace_change(self, request):
        try:
            return self._trace_change(request)
        except (ValueError, KeyError, TypeError, AttributeError):
            return {"status": "rejected", "reasons": [issue("invalid_strategy_request")], "mutated": False}

    def _trace_change(self, request):
        if not isinstance(request, dict):
            return {"status": "blocked", "reasons": [issue("change_request_required")]}
        changed = request.get("changed_refs", [])
        resource_keys = request.get("resource_keys", [])
        source_changes = request.get("resource_changes", [])
        if (not isinstance(changed, list) or any(not exact_ref(r) for r in changed)
                or not isinstance(resource_keys, list) or any(not isinstance(k, str) for k in resource_keys)
                or not isinstance(source_changes, list) or any(not isinstance(s, dict) or not isinstance(s.get("source_id"), str) for s in source_changes)
                or not (changed or resource_keys or source_changes)):
            return {"status": "blocked", "reasons": [issue("changed_refs_required")]}
        state = self.store.read_context()
        if state.get("status") != "ok":
            return state
        for obj in state["objects"]:
            if obj.get("type") != "MethodConfig":
                continue
            selected = obj.get("selected_parts", [])
            key_match = any(isinstance(part, dict) and part.get("resource_key") in resource_keys for part in selected)
            source_match = any(isinstance(source, dict) and source.get("source_id") == change["source_id"]
                               and (not change.get("previous_revision") or source.get("declared_revision") == change["previous_revision"])
                               for source in obj.get("source_refs", []) for change in source_changes)
            if (key_match or source_match) and ref(obj) not in changed:
                changed = changed + [ref(obj)]
        check = self.store.read_refs(changed, "read")
        if check.get("status") != "ok":
            return check
        if any(obj["type"] != "MethodConfig" for obj in check["objects"]):
            return {"status": "rejected", "reasons": [issue("method_change_only")]}
        affected = {r["id"] for r in changed}
        while True:
            new = {o["id"] for o in state["objects"] if any(r.get("id") in affected for r in object_refs(o))}
            if new.issubset(affected):
                break
            affected.update(new)
        edges = [{"from_ref": r, "to_ref": ref(o)} for o in state["objects"] for r in object_refs(o) if r.get("id") in affected and o["id"] in affected]
        return {"status": "candidate", "state_revision": state["state_revision"], "changed_refs": changed,
                "affected_refs": [ref(o) for o in state["objects"] if o["id"] in affected], "direct_dependencies": edges,
                "unknown_dependencies": fact("unknown", "Only managed recorded references are traced."),
                "recovery": {"configuration": {"owner": "AG1", "status": "pending"}, "material": {"owner": "AG2", "status": "pending"},
                             "judgment": {"owner": "AG3", "status": "pending"}, "teaching": {"owner": "AG0", "status": "pending"}, "planning": {"owner": "AG1", "status": "pending"}},
                "resource_keys": resource_keys, "resource_changes": source_changes,
                "mutated": False, "professional_restrictions_lifted": False, "historical_events_rewritten": False}

    def restrict_change(self, request):
        trace = self.trace_change(request)
        if trace.get("status") != "candidate":
            return trace
        uses = request.get("intended_uses")
        if not trace["changed_refs"] or not nonempty_strings(uses) or not request.get("reason"):
            return {"status": "rejected", "reasons": [issue("restriction_scope_required")]}
        receipt = self.store.restrict(request.get("expected_state_revision"), request.get("operation_id"),
                                      [r["id"] for r in trace["changed_refs"]], request["reason"], uses)
        if receipt.get("status") != "committed":
            return receipt
        # Trace can be rebuilt only after the blocking use has been committed.
        result = self.trace_change(request)
        result.update(control_receipt=receipt, mutated=True)
        return result


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("index", "load", "inspect", "reuse", "submit", "change"))
    parser.add_argument("--workspace")
    parser.add_argument("--request", type=Path)
    parser.add_argument("--resource-key")
    parser.add_argument("--work")
    parser.add_argument("--restrict", action="store_true")
    args = parser.parse_args()
    try:
        catalog = StrategyCatalog()
        if args.command == "index":
            result = catalog.index(args.work)
        elif args.command == "load":
            result = catalog.load(args.resource_key)
        else:
            if not args.workspace or not args.request:
                raise ValueError("workspace and request required")
            request = json.loads(args.request.read_text(encoding="utf-8-sig"))
            if not isinstance(request, dict):
                raise ValueError("request must be object")
            service = StrategiesService(LearningStore(args.workspace, entry_actor="AG1"), catalog)
            if args.command == "inspect":
                result = service.inspect_config(request.get("config"), request.get("context"))
            elif args.command == "reuse":
                result = service.reuse_config(request.get("config_ref"), request.get("context"))
            elif args.command == "submit":
                result = service.submit_config(request)
            else:
                result = service.restrict_change(request) if args.restrict else service.trace_change(request)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        result = {"status": "rejected", "reasons": [issue("invalid_strategy_request")], "mutated": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"ok", "compatible", "reusable", "direct_reuse", "candidate", "committed", "controlled"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
