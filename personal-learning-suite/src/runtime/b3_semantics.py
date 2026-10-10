"""Shared B3 declaration adapters; no inferred qualification or learning facts."""
from __future__ import annotations

import copy
from datetime import datetime


def known_bool(value, expected=True):
    return (isinstance(value, dict) and value.get("status") == "known"
            and type(value.get("value")) is bool and value["value"] is expected)


def _unknown(reason):
    return {"status": "unknown", "reason": reason}


def task_checks(activity):
    """Read one canonical shape and explicit legacy B3b claims, without saving.

    Legacy target_operation_call applies to the activity's declared operations;
    prerequisite_burden was the old affirmative suitability check. Contradictory
    parallel declarations remain conflicts instead of choosing the convenient one.
    """
    qualification = activity.get("task_qualification", {})
    value = qualification.get("value") if isinstance(qualification, dict) and qualification.get("status") == "known" else None
    value = value if isinstance(value, dict) else {}
    result = {key: copy.deepcopy(value.get(key, _unknown("No explicit task qualification was supplied.")))
              for key in ("prerequisite_fit", "not_substituted", "reference_scorable", "evidence_conditions")}
    result["target_operations"] = copy.deepcopy(value.get("target_operations", []))
    result["conflicts"] = []
    legacy_call = value.get("target_operation_call")
    if legacy_call is not None:
        legacy_targets = activity.get("learner_operations", []) if known_bool(legacy_call) else []
        if "target_operations" not in value:
            result["target_operations"] = copy.deepcopy(legacy_targets)
        elif known_bool(legacy_call) and (not isinstance(result["target_operations"], list)
                or set(result["target_operations"]) != set(legacy_targets)):
            result["conflicts"].append("target_operation_declarations_conflict")
        elif not known_bool(legacy_call) and result["target_operations"]:
            result["conflicts"].append("target_operation_declarations_conflict")
    legacy_fit = value.get("prerequisite_burden")
    if legacy_fit is not None:
        if "prerequisite_fit" not in value:
            result["prerequisite_fit"] = copy.deepcopy(legacy_fit)
        elif _claim(result["prerequisite_fit"]) != _claim(legacy_fit):
            result["conflicts"].append("prerequisite_declarations_conflict")
    return result


def _claim(value):
    if not isinstance(value, dict):
        return (None, value)
    return (value.get("status"), value.get("value") if value.get("status") == "known" else None)


def active_grant(validity, allow_legacy=False):
    """Modern grants require explicit active=true; prose is fixture compatibility."""
    if isinstance(validity, dict):
        return (validity.get("status") == "known" and isinstance(validity.get("value"), dict)
                and validity["value"].get("active") is True)
    return allow_legacy and isinstance(validity, str) and bool(validity.strip())


def timestamp(value):
    """Parse a timezone-bearing known timestamp; unknown never becomes a time."""
    if not isinstance(value, dict) or value.get("status") != "known":
        return None
    raw = value.get("value")
    if isinstance(raw, dict):
        raw = raw.get("timestamp")
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None
    except (ValueError, OverflowError):
        return None
