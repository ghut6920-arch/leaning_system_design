"""B7 read-only pilot preparation and review of declared, canonical evidence.

This adapter never writes a store, binds a real host, runs teaching, measures
learning, or proves source authenticity.  Callers supply an in-memory snapshot;
only reference metadata, reason codes and bounded summaries leave this module.
"""
from __future__ import annotations

import argparse
from fnmatch import fnmatchcase
import json
import math
import ntpath
from pathlib import Path, PureWindowsPath
import sys
from typing import Any

if __package__:
    from .contract_rules import SUITE_ROOT, artifact_paths, object_refs, safe_artifact_path, validate_records, walk
    from .b3_semantics import timestamp
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime.contract_rules import SUITE_ROOT, artifact_paths, object_refs, safe_artifact_path, validate_records, walk
    from runtime.b3_semantics import timestamp

VERSION = "pl-pilot/0.1.0"
AXES = ("user_active_time", "blocked_wait", "system_effort", "fees")
LAYERS = ("V1", "V2", "V3", "V4")
STATUSES = {"passed", "failed", "not_executed", "unknown", "not_required"}
CLAIMS = {"configuration", "software_behavior", "current_support", "learning_gain", "retention", "design_effect", "collaboration_gain"}


def _ref(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or not isinstance(value.get("id"), str) or not value["id"] or type(value.get("revision")) is not int or value["revision"] < 1:
        return None
    return {"id": value["id"], "revision": value["revision"]}


def _reason(code: str, refs=()) -> dict[str, Any]:
    return {"code": code, **({"refs": [r for value in refs if (r := _ref(value))]} if refs else {})}


def _known(value: Any, direct=False) -> tuple[bool, Any]:
    if isinstance(value, dict):
        if value.get("status") == "known" and "value" in value:
            return True, value["value"]
        return (True, value) if direct and "status" not in value else (False, None)
    return (True, value) if direct and value is not None else (False, None)


def _present(value: Any, direct=False) -> bool:
    known, actual = _known(value, direct)
    return known and actual is not None and actual != "" and actual != [] and actual != {}


def _true(value: Any) -> bool:
    known, actual = _known(value)
    return actual is True if known else value is True


def _finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _original_identity(event):
    """Original identity is independent of event labels and sample labels."""
    original = event.get("original_response") if isinstance(event, dict) else None
    if not isinstance(original, dict):
        return None
    path, revision, locator = original.get("path"), original.get("revision"), original.get("locator")
    if not isinstance(path, str) or type(revision) is not int or not isinstance(locator, str):
        return None
    return path, revision, locator


def _axis(value: Any, allow_not_required=False) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("status") == "not_required" and isinstance(value.get("reason"), str) and value["reason"]:
        return {"status": "not_required"} if allow_not_required else {"status": "unknown"}
    known, actual = _known(value)
    if not known:
        return {"status": "unknown"}
    unit = "declared"
    measurement = "unknown"
    amount = actual
    if isinstance(actual, dict):
        keys = [key for key in ("amount", "minutes", "seconds", "units", "tokens", "value", "calls") if key in actual]
        if len(keys) != 1:
            return {"status": "unknown"}
        amount = actual[keys[0]]
        declared_measurement = actual.get("measurement", actual.get("kind"))
        if declared_measurement in {"observed", "measured", "recorded", "actual"}:
            measurement = "observed"
        elif declared_measurement in {"estimated", "estimate", "manual_estimate"}:
            measurement = "estimated"
        elif declared_measurement in {"user_limit", "synthetic_limit", "limit", "budget_limit"}:
            measurement = "limit"
        if keys[0] != "amount" and keys[0] != "value":
            unit = keys[0]
        elif actual.get("unit") in {"minutes", "seconds", "tokens", "calls", "units", "USD", "CNY"}:
            unit = actual["unit"]
    return {"status": "known", "amount": amount, "unit": unit, "measurement": measurement} if _finite(amount) else {"status": "unknown"}


class _Snapshot:
    def __init__(self, request):
        self.request = request
        self.kind = request["data_kind"]
        self.records = request["objects"]
        self.artifacts = request["artifacts"]
        self.by_ref = {(o["id"], o["revision"]): o for o in self.records}
        self.latest = {}
        for obj in self.records:
            self.latest[obj["id"]] = max(obj["revision"], self.latest.get(obj["id"], 0))
        errors = validate_records(self.records, self.artifacts, synthetic_only=self.kind != "real")
        self.invalid = set()
        self.global_invalid = False
        for error in errors:
            detail = error.get("detail", "")
            matched = [identifier for identifier in self.latest if detail == identifier or detail.startswith(identifier + "/") or detail.startswith(identifier + ":")]
            self.invalid.update(matched)
            if not matched:
                self.global_invalid = True
        self.contract_errors = bool(errors)

    def resolve(self, reference, kind=None, current=False):
        ref = _ref(reference)
        if ref is None:
            return None
        obj = self.by_ref.get((ref["id"], ref["revision"]))
        if not obj or (kind and obj["type"] != kind) or (current and self.latest[ref["id"]] != ref["revision"]):
            return None
        if "locator" in reference:
            locator = reference["locator"]
            if not isinstance(locator, str) or not locator:
                return None
            if locator.startswith("requirements/"):
                if obj["type"] != "GoalSpec" or not any(r.get("requirement_id") == locator.split("/", 1)[1] for r in obj.get("requirements", []) if isinstance(r, dict)):
                    return None
            elif locator not in obj:
                # Only an existing direct field can be located internally;
                # arbitrary nested path languages are outside this slice.
                return None
        return obj

    def closure(self, refs):
        found, scope, missing = [], set(), False
        frontier = list(refs)
        seen = set()
        while frontier:
            reference = frontier.pop()
            if isinstance(reference, dict) and {"path", "locator", "origin"}.issubset(reference):
                if self.artifact(reference):
                    scope.add(reference["path"])
                else:
                    missing = True
                continue
            ref = _ref(reference)
            if ref is None:
                missing = True
                continue
            key = ref["id"], ref["revision"]
            if key in seen:
                continue
            seen.add(key)
            scope.add(ref["id"])
            obj = self.resolve(reference)
            if obj is None:
                missing = True
                continue
            found.append(obj)
            scope.update(artifact_paths(obj))
            frontier.extend(object_refs(obj))
        return found, scope, missing

    def gated(self, refs, uses):
        controls = self.request.get("controls")
        reasons = []
        if not isinstance(controls, dict) or controls.get("known") is not True:
            return [_reason("controls_unknown")]
        objects, scope, missing = self.closure(refs)
        if missing:
            reasons.append(_reason("dependency_unavailable", refs))
        if self.global_invalid or any(o["id"] in self.invalid for o in objects):
            reasons.append(_reason("shared_contract_invalid", refs))
        if set(controls["deleted_ids"]) & scope:
            reasons.append(_reason("deleted_dependency"))
        if set(controls["paused_ids"]) & scope:
            reasons.append(_reason("paused_dependency"))
        restrictions = list(controls["restrictions"])
        for obj in self.records:
            if obj.get("type") == "UseRestriction" and obj.get("status") == "active":
                restrictions.extend({"scope_id": r["id"], "intended_uses": obj.get("intended_uses", [])} for r in obj.get("scope_refs", []) if _ref(r))
        for restriction in restrictions:
            if restriction["scope_id"] in scope and ("*" in restriction["intended_uses"] or set(uses) & set(restriction["intended_uses"])):
                reasons.append(_reason("restricted_dependency"))
                break
        return reasons

    def artifact(self, reference):
        return (isinstance(reference, dict) and isinstance(reference.get("path"), str)
                and isinstance(reference.get("locator"), str) and bool(reference["locator"])
                and reference.get("revision") == 1 and isinstance(reference.get("origin"), str)
                and reference["path"] in self.artifacts and reference["locator"] in self.artifacts[reference["path"]])

    def located(self, obj):
        if any(self.artifact(item) for item in walk(obj) if isinstance(item, dict) and "path" in item):
            return True
        source_ref = obj.get("source_ref", {}) if isinstance(obj, dict) else {}
        locator = source_ref.get("locator") if isinstance(source_ref, dict) else None
        if isinstance(locator, str) and "#" in locator:
            path, anchor = locator.split("#", 1)
            return bool(anchor and path in self.artifacts and anchor in self.artifacts[path])
        return False


class PilotService:
    """Read-only preparation and evidence review; no authentication or execution."""

    @staticmethod
    def _base(kind="unconfigured", status="needs_input", reasons=()):
        return {"pilot_version": VERSION, "data_kind": kind, "status": status, "reasons": list(reasons),
                "inputs_ready": False, "can_start_automated": False, "live_execution_status": "not_enabled",
                "mutated": False, "persisted": False,
                "limits": ["declaration_checks_only", "source_authenticity_not_proven", "host_identity_not_authenticated", "no_teaching_execution", "no_new_scoring"]}

    def _parse(self, request):
        if not isinstance(request, dict) or request.get("pilot_version") != VERSION or request.get("data_kind") not in {"unconfigured", "synthetic", "real"}:
            return None, self._base(status="rejected", reasons=[_reason("invalid_pilot_request")])
        kind = request["data_kind"]
        if not isinstance(request.get("objects"), list) or not isinstance(request.get("artifacts"), dict):
            return None, self._base(kind, "rejected", [_reason("invalid_snapshot")])
        if any(not safe_artifact_path(path) or not isinstance(text, str) for path, text in request["artifacts"].items()):
            return None, self._base(kind, "rejected", [_reason("invalid_artifacts")])
        # Check serializability without retaining or printing rejected content.
        json.dumps(request, allow_nan=False)
        for obj in request["objects"]:
            if not isinstance(obj, dict) or _ref(obj) is None or not isinstance(obj.get("type"), str):
                return None, self._base(kind, "rejected", [_reason("invalid_object_shape")])
        if len({(o["id"], o["revision"]) for o in request["objects"]}) != len(request["objects"]):
            return None, self._base(kind, "rejected", [_reason("duplicate_object")])
        controls = request.get("controls")
        if controls is not None:
            if not isinstance(controls, dict) or type(controls.get("known")) is not bool:
                return None, self._base(kind, "rejected", [_reason("invalid_controls")])
            if any(not isinstance(controls.get(key), list) or any(not isinstance(s, str) for s in controls[key]) for key in ("deleted_ids", "paused_ids")):
                return None, self._base(kind, "rejected", [_reason("invalid_controls")])
            if not isinstance(controls.get("restrictions"), list) or any(not isinstance(r, dict) or not isinstance(r.get("scope_id"), str) or not isinstance(r.get("intended_uses"), list) or not all(isinstance(u, str) for u in r["intended_uses"]) for r in controls["restrictions"]):
                return None, self._base(kind, "rejected", [_reason("invalid_controls")])
        host = request.get("host")
        if host is not None and (not isinstance(host, dict) or host.get("mode") != "manual_single_entry" or host.get("execution_available") is not False):
            return None, self._base(kind, "rejected", [_reason("host_execution_not_supported")])
        if kind == "real":
            if request.get("synthetic_only") is True or request.get("synthetic") is True:
                return None, self._base(kind, "rejected", [_reason("synthetic_data_in_real_request")])
            for value in walk(request):
                if isinstance(value, dict) and (any(isinstance(value.get(key), str) and value[key].startswith("FIX-") for key in ("id", "source_id", "independent_sample_id")) or value.get("origin") == "synthetic_fixture" or value.get("identity_kind") == "synthetic" or value.get("binding_status") == "verified_for_fixture"):
                    return None, self._base(kind, "rejected", [_reason("synthetic_data_in_real_request")])
        snapshot = _Snapshot(request)
        for field in ("instance_ref", "budget_ref", "current_goal_refs", "validation_refs"):
            values = request.get(field)
            values = values if isinstance(values, list) else [values]
            for reference in values:
                if not isinstance(reference, dict) or "locator" not in reference:
                    continue
                locator = reference["locator"]
                if not isinstance(locator, str) or not locator:
                    return None, self._base(kind, "rejected", [_reason("invalid_reference_locator")])
                if field != "current_goal_refs" or not locator.startswith("requirements/"):
                    return None, self._base(kind, "rejected", [_reason("unsupported_top_level_locator")])
                canonical = snapshot.by_ref.get((reference.get("id"), reference.get("revision")))
                if canonical is not None and snapshot.resolve(reference, "GoalSpec") is None:
                    return None, self._base(kind, "rejected", [_reason("invalid_reference_locator")])
        return snapshot, None

    @staticmethod
    def _anchor_ready(snapshot, reference):
        if snapshot.artifact(reference):
            return True
        obj = snapshot.resolve(reference, current=True)
        if obj is not None:
            return snapshot.located(obj)
        return False

    def _source_ready(self, source, snapshot):
        verification = source.get("verification")
        known, value = _known(verification)
        allowed = {"supported", "verified"} | ({"supported_for_fixture"} if snapshot.kind == "synthetic" else set())
        located = snapshot.located(source)
        if known and isinstance(value, dict) and value.get("recorded_status") in allowed and value.get("method") and value.get("scope"):
            anchors = value.get("anchor_refs", [])
            return located or bool(anchors and all(self._anchor_ready(snapshot, ref) for ref in anchors))
        if isinstance(verification, dict):
            content = verification.get("content", {})
            return (isinstance(content, dict) and content.get("status") == "supported" and content.get("checked_revision") == source["revision"]
                    and bool(content.get("scope")) and bool(content.get("conditions")) and content.get("reviewer") == "AG2"
                    and (located or bool(content.get("anchor_refs") and all(self._anchor_ready(snapshot, ref) for ref in content["anchor_refs"]))))
        return False

    def _goal_reasons(self, snapshot, goal):
        reasons = []
        reference = _ref(goal)
        known, resources = _known(goal.get("allowed_resources"), True)
        if not goal.get("requirements") or not known or not isinstance(resources, (list, str)):
            reasons.append(_reason("goal_requirements_or_resources_missing", [reference]))
        dual_sources = list(goal.get("requirement_source_refs", [])) + list(goal.get("content_basis_refs", []))
        for requirement in goal.get("requirements", []):
            for group in (requirement, requirement.get("criterion", {})):
                dual_sources.extend(group.get("requirement_source_refs", []))
                dual_sources.extend(group.get("content_basis_refs", []))
        for source_ref in dual_sources:
            source = snapshot.resolve(source_ref, "SourceFragment", current=True)
            if not source or not self._source_ready(source, snapshot):
                reasons.append(_reason("current_reliable_source_required", [source_ref]))
        return reasons

    def _whole_ready(self, snapshot, goal, requirement):
        declaration = requirement.get("teaching_scope")
        if not isinstance(declaration, dict) or type(declaration.get("whole_required")) is not bool:
            return False
        if declaration["whole_required"] is False:
            return True
        obligations = declaration.get("whole_obligations")
        operations = requirement.get("key_operations", [])
        if not isinstance(obligations, list) or not obligations:
            return False
        for obj in snapshot.records:
            if obj["type"] not in {"SourceFragment", "MaterialUse"} or snapshot.latest[obj["id"]] != obj["revision"]:
                continue
            verification = obj.get("verification", {})
            content = verification.get("content", {}) if isinstance(verification, dict) else {}
            coverage = content.get("whole_coverage", {}) if isinstance(content, dict) else {}
            if (not isinstance(coverage, dict) or coverage.get("status") != "supported" or content.get("status") != "supported"
                    or content.get("checked_revision") != obj["revision"]):
                continue
            if obj["type"] == "MaterialUse":
                use = verification.get("use", {})
                if not isinstance(use, dict) or use.get("status") != "supported" or use.get("checked_revision") != obj["revision"]:
                    continue
            if not self._source_ready(obj, snapshot):
                continue
            goal_refs = coverage.get("goal_refs", [])
            criteria = coverage.get("criterion_refs", [])
            if (any(_ref(r) == _ref(goal) for r in goal_refs)
                    and any(_ref(r) == _ref(goal) and r.get("locator") == "requirements/" + requirement["requirement_id"] for r in criteria)
                    and set(operations).issubset(coverage.get("target_operations", []))
                    and set(obligations).issubset(coverage.get("obligations", []))
                    and coverage.get("anchor_refs") and all(self._anchor_ready(snapshot, ref) for ref in coverage["anchor_refs"])
                    and not snapshot.gated([_ref(obj)], {"prepare", "teaching"})):
                return True
        return False

    def preflight(self, request):
        try:
            snapshot, error = self._parse(request)
            if error:
                return error
            response = self._base(snapshot.kind)
            reasons, checks = [], {}
            if snapshot.kind == "unconfigured":
                reasons.append(_reason("pilot_not_configured"))
            if snapshot.contract_errors:
                reasons.append(_reason("shared_contract_invalid"))
            instance = snapshot.resolve(request.get("instance_ref"), "LearningInstance", current=True)
            checks["instance"] = instance is not None
            if not instance:
                reasons.append(_reason("current_instance_required"))
            else:
                for field in ("course", "purpose", "scope", "user_constraints", "record_control_scope"):
                    if not _present(instance.get(field), field in {"scope", "record_control_scope"}):
                        reasons.append(_reason("instance_" + field + "_unknown", [_ref(instance)]))
                known, bindings = _known(instance.get("actor_bindings"))
                if not known or not isinstance(bindings, dict) or any(not _present(bindings.get(role), True) for role in ("AG0", "AG1", "AG2", "AG3")):
                    reasons.append(_reason("four_role_bindings_required", [_ref(instance)]))
                known, root = _known(instance.get("record_root"))
                external = False
                if known and isinstance(root, str) and (Path(root).is_absolute() or PureWindowsPath(root).is_absolute()):
                    if PureWindowsPath(root).is_absolute():
                        pilot_root = PureWindowsPath(ntpath.normcase(ntpath.normpath(root)))
                        suite_root = PureWindowsPath(ntpath.normcase(ntpath.normpath(str(SUITE_ROOT))))
                        external = not pilot_root.is_relative_to(suite_root)
                    else:
                        external = not Path(root).resolve().is_relative_to(SUITE_ROOT.resolve())
                if not external:
                    reasons.append(_reason("external_absolute_record_root_required", [_ref(instance)]))
            goal_refs = request.get("current_goal_refs")
            if not isinstance(goal_refs, list) or not goal_refs:
                reasons.append(_reason("current_goal_required"))
                goal_refs = []
            ready_goals = []
            for reference in goal_refs:
                goal = snapshot.resolve(reference, "GoalSpec", current=True)
                if not goal:
                    reasons.append(_reason("current_goal_required", [reference]))
                    continue
                goal_reasons = self._goal_reasons(snapshot, goal)
                goal_reasons.extend(snapshot.gated([_ref(goal)], {"prepare", "teaching", "use"}))
                if any(not self._whole_ready(snapshot, goal, requirement) for requirement in goal.get("requirements", [])):
                    goal_reasons.append(_reason("whole_goal_reference_or_scope_missing", [_ref(goal)]))
                reasons.extend(goal_reasons)
                if not goal_reasons:
                    ready_goals.append(_ref(goal))
            checks["current_goals"] = bool(ready_goals)
            budget = snapshot.resolve(request.get("budget_ref"), "BudgetEnvelope", current=True)
            axes = {axis: _axis(budget.get(axis), True) if budget else {"status": "unknown"} for axis in AXES}
            checks["budget_axes"] = all(axis["status"] in {"known", "not_required"} for axis in axes.values())
            if not budget or not checks["budget_axes"]:
                reasons.append(_reason("current_budget_bounds_required"))
            if budget:
                grant = snapshot.resolve(budget.get("authorization_ref"), "AuthorizationGrant", current=True)
                goal_ids = [r["id"] for r in goal_refs if _ref(r)]
                scope = budget.get("allocation_scope", [])
                permitted = grant.get("object_scope", []) if grant else []
                active = _known(grant.get("validity"))[1] if grant else None
                if (not grant or grant.get("binding_status") != ("host_verified" if snapshot.kind == "real" else "verified_for_fixture")
                        or not isinstance(active, dict) or active.get("active") is not True
                        or grant.get("grantee") != "AG1" or not grant.get("permitted_conclusions")
                        or _ref(grant.get("budget_ref")) != _ref(budget)
                        or not any(t in grant.get("decision_types", []) for t in ("planning", "budget_allocation"))
                        or not goal_ids or not all(any(fnmatchcase(identifier, s) for s in scope) and any(fnmatchcase(identifier, s) for s in permitted) for identifier in goal_ids)):
                    reasons.append(_reason("current_budget_scope_authorization_required", [_ref(budget)]))
            selected = [request.get("instance_ref"), request.get("budget_ref")] + goal_refs
            reasons.extend(snapshot.gated([r for r in selected if _ref(r)], {"prepare", "teaching", "use"}))
            followup = request.get("followup", {})
            if not isinstance(followup, dict) or followup.get("status") not in {"unknown", "not_required", "required"}:
                reasons.append(_reason("followup_status_required"))
            elif followup["status"] == "unknown":
                reasons.append(_reason("necessary_followup_unknown"))
            elif followup["status"] == "required":
                refs = followup.get("goal_refs")
                if (not isinstance(refs, list) or not refs or not _present(followup.get("purpose"), True)
                        or any(not snapshot.resolve(r, "GoalSpec", current=True) or _ref(r) not in ready_goals for r in refs)):
                    reasons.append(_reason("necessary_followup_not_covered"))
            if request.get("host") is None:
                reasons.append(_reason("manual_host_declaration_required"))
            response.update(status="prepared" if not reasons else "needs_input", inputs_ready=not reasons,
                            reasons=reasons, checks=checks, prepared_goal_refs=ready_goals,
                            budget={"axes": axes, "aggregation": "shared_envelope_not_multiplied"})
            return response
        except Exception:
            return self._base(status="rejected", reasons=[_reason("invalid_pilot_input")])

    def report(self, request):
        try:
            snapshot, error = self._parse(request)
            if error:
                return error
            response = self._base(snapshot.kind, "reported")
            response.update(reviews={layer: {"reported_status": "not_executed", "review_refs": [], "reasons": [], "claim_scope": "none", "assessments": []} for layer in LAYERS},
                            real_results={layer: "not_executed" for layer in LAYERS},
                            costs={"records": [], "aggregation": "not_added", "unknown_is_zero": False})
            refs = request.get("validation_refs")
            if not isinstance(refs, list):
                response.update(status="needs_input", reasons=[_reason("validation_refs_required")])
                return response
            for reference in refs:
                review = snapshot.resolve(reference, "ValidationDecision", current=True)
                if review is None:
                    response["reasons"].append(_reason("canonical_validation_required", [reference]))
                    continue
                layer = review.get("validation_layer")
                if layer not in LAYERS:
                    response["reasons"].append(_reason("validation_layer_invalid", [reference]))
                    continue
                try:
                    assessment = self._review(snapshot, review)
                except Exception:
                    assessment = {"review_ref": _ref(review), "reported_status": "unknown", "claim_scope": "none", "reasons": [_reason("invalid_review_metadata")]}
                response["reviews"][layer]["assessments"].append(assessment)
                response["reviews"][layer]["review_refs"].append(_ref(review))
                cost = review.get("cost", {}) if not snapshot.gated([_ref(review)], {"read", "review", "cost"}) else {}
                response["costs"]["records"].append({"review_ref": _ref(review), "axes": {axis: _axis(cost.get(axis), True) if isinstance(cost, dict) else {"status": "unknown"} for axis in AXES}})
            for layer, summary in response["reviews"].items():
                assessments = summary["assessments"]
                if not assessments:
                    summary["reasons"] = [_reason("no_selected_review")]
                    continue
                statuses = {a["reported_status"] for a in assessments}
                summary["reported_status"] = next((s for s in ("unknown", "failed", "not_executed", "passed", "not_required") if s in statuses))
                summary["reasons"] = [reason for a in assessments for reason in a["reasons"]]
                scopes = {a["claim_scope"] for a in assessments}
                summary["claim_scope"] = next(iter(scopes)) if len(scopes) == 1 else "per_review_only"
                if snapshot.kind == "real":
                    response["real_results"][layer] = summary["reported_status"]
            if response["reasons"] or any(s["reported_status"] == "unknown" for s in response["reviews"].values()):
                response["status"] = "needs_input"
            return response
        except Exception:
            return self._base(status="rejected", reasons=[_reason("invalid_pilot_input")])

    def _review(self, snapshot, review):
        result = {"review_ref": _ref(review), "reported_status": review.get("status") if review.get("status") in STATUSES else "unknown",
                  "reasons": [], "claim_scope": "none"}
        result["reasons"].extend(snapshot.gated([_ref(review)], {"read", "review", review["validation_layer"], review.get("metadata", {}).get("pilot", {}).get("claim", "review")}))
        if result["reported_status"] in {"passed", "failed"}:
            if any(not _present(review.get(field), True) for field in ("executor", "checker", "host", "versions")) or not snapshot.artifact(review.get("raw_output_ref")):
                result["reasons"].append(_reason("review_provenance_or_original_missing"))
        pilot = review.get("metadata", {}).get("pilot", {})
        if result["reported_status"] == "passed":
            result["reasons"].extend(self._layer_reasons(snapshot, review, pilot))
            claim = pilot.get("claim")
            if claim in CLAIMS:
                result["claim_scope"] = claim
            else:
                result["reasons"].append(_reason("bounded_claim_required"))
        if review["validation_layer"] == "V3" and isinstance(pilot, dict):
            result["judgments"] = []
            for reference in pilot.get("judgment_refs", []):
                judgment = snapshot.resolve(reference, "Judgment", current=True)
                if judgment is not None and not snapshot.gated([_ref(judgment)], {"read", "review", "V3", "current_support"}):
                    result["judgments"].append({"judgment_ref": _ref(judgment),
                        "goal_ref": _ref(judgment.get("goal_ref")),
                        "requirement_id": judgment.get("requirement_id"), "criterion_revision": judgment.get("criterion_revision"),
                        "event_refs": [_ref(r) for r in judgment.get("event_refs", []) if _ref(r)],
                        "support": judgment.get("support") if judgment.get("support") in {"unknown", "supported", "observed_not_met", "mixed_or_conflicting"} else "unknown",
                        "eligibility": judgment.get("eligibility") if judgment.get("eligibility") in {"usable", "pending_review", "withdrawn"} else "unknown",
                        "conditions_ref": dict(_ref(judgment), locator="conditions"),
                        "unsupported_scope_ref": dict(_ref(judgment), locator="unsupported_scope"),
                        "adoption_status": "adopted" if judgment.get("adoption", {}).get("status") == "adopted" else "unknown"})
        # Configuration and software evidence cannot establish attribution by
        # themselves.  Retain a lawful adopted judgment as current support.
        attribution = [r for r in result["reasons"] if r["code"] == "design_attribution_not_established"]
        blocking = [r for r in result["reasons"] if r not in attribution]
        if attribution and not blocking:
            result["claim_scope"] = "current_support"
        if review["validation_layer"] == "V4" and result["reasons"] and all(r["code"] == "comparison_not_executed" for r in result["reasons"]):
            result["reported_status"] = "not_executed"
            result["claim_scope"] = "none"
            blocking = []
        if blocking:
            result["reported_status"] = "unknown"
            result["claim_scope"] = "none"
        if snapshot.kind != "real":
            result["real_result_status"] = "not_executed"
        return result

    def _layer_reasons(self, snapshot, review, pilot):
        if not isinstance(pilot, dict):
            return [_reason("pilot_review_metadata_required")]
        layer = review["validation_layer"]
        goals = pilot.get("goal_refs", [])
        events = pilot.get("event_refs", [])
        judgments = pilot.get("judgment_refs", [])
        reasons = []
        if not isinstance(goals, list) or not goals or any(not snapshot.resolve(r, "GoalSpec", current=True) for r in goals):
            reasons.append(_reason("review_current_goal_required"))
        if layer == "V1":
            for reference in goals:
                goal = snapshot.resolve(reference, "GoalSpec", current=True)
                if goal:
                    reasons.extend(self._goal_reasons(snapshot, goal))
            if pilot.get("claim") != "configuration":
                reasons.append(_reason("v1_configuration_claim_only"))
        elif layer in {"V2", "V3"}:
            if not isinstance(events, list) or not events:
                reasons.append(_reason("original_event_required"))
            else:
                for reference in events:
                    event = snapshot.resolve(reference, "PerformanceEvent")
                    if not event or not snapshot.artifact(event.get("original_response")) or not event.get("timeline") or not any(item.get("kind") == "initial_response" for item in event.get("timeline", [])):
                        reasons.append(_reason("event_original_or_timeline_missing", [reference]))
                    elif not any(_ref(r) in [_ref(g) for g in goals] for r in event.get("goal_refs", [])):
                        reasons.append(_reason("event_goal_binding_missing", [reference]))
            if layer == "V2" and pilot.get("claim") != "software_behavior":
                reasons.append(_reason("v2_behavior_claim_only"))
            if layer == "V3":
                reasons.extend(self._v3_reasons(snapshot, pilot, goals, events, judgments))
        elif layer == "V4":
            reasons.extend(self._v4_reasons(snapshot, pilot))
        return reasons

    def _v3_reasons(self, snapshot, pilot, goals, events, judgments):
        reasons = []
        if not isinstance(judgments, list) or not judgments:
            return [_reason("adopted_judgment_required")]
        for reference in judgments:
            judgment = snapshot.resolve(reference, "Judgment", current=True)
            if (not judgment or judgment.get("adoption", {}).get("status") != "adopted"
                    or judgment.get("support") not in {"supported", "observed_not_met", "mixed_or_conflicting", "unknown"}
                    or judgment.get("eligibility") not in {"usable", "pending_review", "withdrawn"}
                    or not _present(judgment.get("conditions"), True)
                    or _ref(judgment.get("goal_ref")) not in [_ref(r) for r in goals]
                    or not judgment.get("event_refs") or any(_ref(r) not in [_ref(e) for e in events] for r in judgment.get("event_refs", []))):
                reasons.append(_reason("adopted_judgment_axes_or_conditions_missing", [reference]))
        claim = pilot.get("claim")
        if claim not in {"current_support", "learning_gain", "retention", "design_effect"}:
            reasons.append(_reason("v3_claim_invalid"))
        if claim in {"learning_gain", "retention"}:
            baselines = pilot.get("baseline_event_refs", [])
            if not _true(pilot.get("baseline_comparable")) or not isinstance(baselines, list) or not baselines:
                reasons.append(_reason("comparable_baseline_required"))
            else:
                current = [snapshot.resolve(r, "PerformanceEvent") for r in events]
                prior = [snapshot.resolve(r, "PerformanceEvent") for r in baselines]
                if any(not e for e in current + prior) or any(e["independent_sample_id"] == b["independent_sample_id"] or e["id"] == b["id"] for e in current if e for b in prior if b):
                    reasons.append(_reason("same_sample_cannot_establish_gain"))
                if any(_original_identity(e) is not None and _original_identity(e) == _original_identity(b) for e in current if e for b in prior if b):
                    reasons.append(_reason("original_response_reused_as_sample"))
                if snapshot.gated(baselines, {"review", "V3"}):
                    reasons.append(_reason("baseline_unavailable"))
                baseline_judgments = pilot.get("baseline_judgment_refs", [])
                if not isinstance(baseline_judgments, list) or not baseline_judgments:
                    reasons.append(_reason("known_adopted_baseline_judgment_required"))
                else:
                    known_prior = []
                    for reference in baseline_judgments:
                        previous = snapshot.resolve(reference, "Judgment", current=True)
                        if (not previous or previous.get("adoption", {}).get("status") != "adopted"
                                or previous.get("support") not in {"supported", "observed_not_met", "mixed_or_conflicting"}
                                or previous.get("eligibility") != "usable" or not _present(previous.get("conditions"), True)
                                or not previous.get("event_refs") or any(_ref(r) not in [_ref(b) for b in baselines] for r in previous.get("event_refs", []))
                                or snapshot.gated([reference], {"read", "review", "V3", claim})):
                            reasons.append(_reason("baseline_support_or_eligibility_unknown", [reference]))
                        else:
                            known_prior.append(previous)
                    current_judgments = [snapshot.resolve(r, "Judgment", current=True) for r in judgments]
                    if any(not any(_ref(prior_j.get("goal_ref")) == _ref(now.get("goal_ref"))
                            and prior_j.get("requirement_id") == now.get("requirement_id")
                            and prior_j.get("criterion_revision") == now.get("criterion_revision") for prior_j in known_prior)
                            for now in current_judgments if now):
                        reasons.append(_reason("baseline_criterion_not_comparable"))
                    if claim == "learning_gain" and not any(now and now.get("support") == "supported" and now.get("eligibility") == "usable"
                            and any(prior_j.get("support") == "observed_not_met" and prior_j.get("requirement_id") == now.get("requirement_id") for prior_j in known_prior)
                            for now in current_judgments):
                        reasons.append(_reason("learning_gain_difference_not_established"))
            if claim == "retention":
                reasons.extend(self._retention_reasons(snapshot, goals, events, pilot.get("baseline_event_refs", []), judgments))
        if claim == "design_effect":
            reasons.append(_reason("design_attribution_not_established"))
        return reasons

    @staticmethod
    def _retention_reasons(snapshot, goals, events, baselines, judgments):
        if __package__:
            from .learning_assessment import AssessmentService
        else:
            from runtime.learning_assessment import AssessmentService
        reasons = []
        for goal_ref in goals:
            goal = snapshot.resolve(goal_ref, "GoalSpec", current=True)
            known, time_requirements = _known(goal.get("time_requirements")) if goal else (False, None)
            if (not known or not isinstance(time_requirements, dict) or not _finite(time_requirements.get("minimum_delay_seconds"))
                    or not time_requirements.get("requirement_ids") or type(time_requirements.get("require_no_contact")) is not bool):
                reasons.append(_reason("goal_retention_conditions_missing", [goal_ref]))
                continue
            for reference in events:
                event = snapshot.resolve(reference, "PerformanceEvent")
                # Select the exact response point of the adopted Judgment;
                # an unknown revised time never falls back to the initial time.
                selected = []
                for judgment_ref in judgments:
                    judgment = snapshot.resolve(judgment_ref, "Judgment", current=True)
                    if not judgment or _ref(judgment.get("goal_ref")) != _ref(goal_ref) or judgment.get("adoption", {}).get("status") != "adopted":
                        continue
                    conditions = judgment.get("conditions", {})
                    if not isinstance(conditions, dict):
                        continue
                    for response_point in conditions.get("response_points", []):
                        if _ref(response_point.get("event_ref")) == _ref(reference):
                            selected.append((judgment, response_point.get("sequence")))
                if not event or not selected:
                    reasons.append(_reason("retention_response_point_required", [reference]))
                    continue
                for judgment, sequence in selected:
                    requirement_id = judgment.get("requirement_id")
                    if requirement_id not in time_requirements["requirement_ids"]:
                        reasons.append(_reason("retention_outside_goal_time_scope", [reference]))
                        continue
                    response = next((entry for entry in event["timeline"] if entry.get("sequence") == sequence), None)
                    if not response or timestamp(response.get("time")) is None:
                        reasons.append(_reason("retention_selected_time_unknown", [reference]))
                        continue
                    requirement = next((r for r in goal["requirements"] if r["requirement_id"] == requirement_id), {})
                    exposures, inheritance_errors, incomplete = AssessmentService._exposure_records(event, sequence, snapshot.by_ref, include_responses=True)
                    reasons.extend(_reason(code, [reference]) for code in inheritance_errors)
                    if incomplete:
                        reasons.append(_reason("retention_inherited_contact_not_reviewed", [reference]))
                    codes = AssessmentService._time_limits(goal, requirement_id, event, response, requirement.get("key_operations", []), exposures)
                    reasons.extend(_reason(code, [reference]) for code in codes)
        return reasons

    def _v4_reasons(self, snapshot, pilot):
        comparison = pilot.get("comparison", snapshot.request.get("comparison", {}))
        if isinstance(snapshot.request.get("comparison"), dict) and snapshot.request["comparison"].get("status") == "withdrawn":
            return [_reason("comparison_not_executed")]
        if not isinstance(comparison, dict) or comparison.get("status") != "requested":
            return [_reason("comparison_not_executed")]
        arms = comparison.get("arms", [])
        if (pilot.get("claim") != "collaboration_gain" or not _present(comparison.get("question"), True)
                or not _present(comparison.get("decision_needed"), True) or not _true(comparison.get("planned"))
                or not _true(comparison.get("comparable")) or not isinstance(arms, list) or len(arms) < 2):
            return [_reason("planned_comparable_units_required")]
        matching_refs = comparison.get("matching_basis_refs", [])
        if not isinstance(matching_refs, list):
            return [_reason("comparison_matching_basis_required")]
        if (not _present(comparison.get("matching_basis")) and not matching_refs):
            return [_reason("comparison_matching_basis_required")]
        if matching_refs and (any(not snapshot.resolve(r, current=True) or not self._anchor_ready(snapshot, r) for r in matching_refs)
                              or snapshot.gated(matching_refs, {"read", "review", "V4", "collaboration_gain"})):
            return [_reason("comparison_matching_basis_unavailable")]
        # A top-level comparison is outside ValidationDecision.basis_refs;
        # explicitly traverse every declared object and original reference.
        comparison_refs = list(object_refs(comparison))
        if comparison_refs and snapshot.gated(comparison_refs, {"read", "review", "V4", "collaboration_gain"}):
            return [_reason("comparison_dependency_unavailable")]
        originals_refs = [value for value in walk(comparison) if isinstance(value, dict) and {"path", "locator", "origin"}.issubset(value)]
        if originals_refs and snapshot.gated(originals_refs, {"read", "review", "V4", "collaboration_gain"}):
            return [_reason("comparison_original_unavailable")]
        units, samples, originals, content_signatures, reasons = set(), set(), set(), set(), []
        for arm in arms:
            if not isinstance(arm, dict) or _ref(arm.get("unit_ref")) is None:
                reasons.append(_reason("comparison_unit_missing"))
                continue
            unit = _ref(arm["unit_ref"])
            if unit["id"] in units:
                reasons.append(_reason("comparison_units_not_distinct"))
            units.add(unit["id"])
            event_refs = arm.get("event_refs", [])
            activity = snapshot.resolve(unit, "ActivitySpec")
            known, prior = _known(arm.get("prior_learning"))
            if not known or not isinstance(prior, str) or prior not in {"unlearned", "not_previously_learned"}:
                reasons.append(_reason("comparison_prior_learning_unknown"))
            if not activity or not _present(arm.get("quality")) or not _present(arm.get("conditions")) or not isinstance(event_refs, list) or not event_refs:
                reasons.append(_reason("comparison_actual_conditions_or_quality_missing"))
            if activity and not any(_ref(r) in [_ref(g) for g in pilot.get("goal_refs", [])] for r in activity.get("goal_refs", [])):
                reasons.append(_reason("comparison_goal_binding_missing"))
            if activity:
                # Renaming a task or advancing its revision does not produce a
                # different learning unit.  Compare content in memory only.
                material_content = [snapshot.resolve(r, "MaterialUse").get("visible_input") for r in activity.get("material_refs", []) if snapshot.resolve(r, "MaterialUse")]
                reference_content = [snapshot.resolve(r, "SourceFragment").get("claims") for r in activity.get("reference_refs", []) if snapshot.resolve(r, "SourceFragment")]
                signature = json.dumps([activity.get("prompt"), material_content, reference_content, activity.get("learner_operations")], sort_keys=True, ensure_ascii=False)
                if signature in content_signatures:
                    reasons.append(_reason("comparison_same_content_repeated"))
                content_signatures.add(signature)
            for reference in event_refs:
                event = snapshot.resolve(reference, "PerformanceEvent")
                if not event or not snapshot.artifact(event.get("original_response")) or _ref(event.get("activity_ref")) != unit:
                    reasons.append(_reason("comparison_event_missing"))
                elif event["independent_sample_id"] in samples:
                    reasons.append(_reason("comparison_samples_not_distinct"))
                else:
                    samples.add(event["independent_sample_id"])
                if event and _original_identity(event) is not None:
                    identity = _original_identity(event)
                    if identity in originals:
                        reasons.append(_reason("original_response_reused_as_sample"))
                    originals.add(identity)
            cost = arm.get("cost", {})
            if not isinstance(cost, dict) or any(_axis(cost.get(axis), True)["status"] not in {"known", "not_required"} for axis in AXES):
                reasons.append(_reason("comparison_complete_axis_cost_required"))
            reasons.extend(snapshot.gated([unit] + event_refs, {"review", "V4"}))
        return reasons


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="B7 read-only pilot preparation and declared evidence report")
    parser.add_argument("action", choices=("preflight", "report"))
    parser.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    service = PilotService()
    try:
        request = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
        result = getattr(service, args.action)(request)
    except Exception:
        result = service._base(status="rejected", reasons=[_reason("request_unreadable")])
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if result["status"] == "rejected" else 2 if result["status"] == "needs_input" else 0


if __name__ == "__main__":
    raise SystemExit(main())
