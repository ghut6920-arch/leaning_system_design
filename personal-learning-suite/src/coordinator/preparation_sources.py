"""One versioned byte inventory of prepared materials; no learning state.

References never substitute for professional reading. This map provides an
integrity check over the actual task, lesson, full teacher reference and checks.
"""
import json
import re

from .workspace import GateError, identifier, ref, scopes, sha

VERSION = "preparation-sources/0.1.0"
KINDS = {"formal_task", "mainline", "teacher_reference", "backup_help", "visual", "code", "verification", "material_report"}
REQUIRED = {"formal_task", "mainline", "teacher_reference", "material_report"}
PREFIXES = ("questions/", "materials/", "artifacts/", "code/")


def validate_map(value):
    if (not isinstance(value, dict) or set(value) != {"version", "artifact_ref", "scope", "intended_use", "entries"}
            or value["version"] != VERSION):
        raise GateError("invalid_preparation_sources")
    ref(value["artifact_ref"])
    scopes(value["scope"])
    identifier(value["intended_use"])
    entries = value["entries"]
    if not isinstance(entries, list) or not 4 <= len(entries) <= 64:
        raise GateError("invalid_preparation_sources")
    ids, paths, digests, kinds = set(), set(), set(), []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"id", "kind", "path", "sha256", "bytes"}:
            raise GateError("invalid_preparation_sources")
        key = identifier(entry["id"])
        path, digest, kind = entry["path"], entry["sha256"], entry["kind"]
        if (not isinstance(path, str) or not path.startswith(PREFIXES) or "\\" in path or ":" in path
                or any(part in {"", ".", ".."} or part.startswith(".") for part in path.split("/"))):
            raise GateError("unsafe_preparation_source_path")
        if not isinstance(digest, str) or not re.fullmatch("[a-f0-9]{64}", digest) or type(entry["bytes"]) is not int or entry["bytes"] <= 0:
            raise GateError("invalid_preparation_sources")
        if kind not in KINDS:
            raise GateError("invalid_preparation_source_kind")
        if key in ids or path in paths or digest in digests:
            raise GateError("duplicate_preparation_source")
        ids.add(key)
        paths.add(path)
        digests.add(digest)
        kinds.append(kind)
    if not REQUIRED <= set(kinds) or kinds.count("formal_task") != 1 or kinds.count("material_report") != 1:
        raise GateError("canonical_task_and_complete_reference_required")


def verify_map(coordinator, value, *, exact=None, scope=None, intended_use=None, path=None):
    validate_map(value)
    if ((exact is not None and value["artifact_ref"] != ref(exact))
            or (scope is not None and set(value["scope"]) != set(scope))
            or (intended_use is not None and value["intended_use"] != intended_use)):
        raise GateError("preparation_sources_identity_mismatch")
    verified = []
    for entry in value["entries"]:
        if path == entry["path"]:
            raise GateError("preparation_sources_cannot_include_itself")
        coordinator.assert_version_path(entry["path"])
        resolved = (coordinator.root / entry["path"]).resolve()
        if not resolved.is_relative_to(coordinator.root):
            raise GateError("unsafe_preparation_source_path")
        coordinator.assert_version_path(resolved.relative_to(coordinator.root).as_posix())
        # Independently registered objects have their own identity/scope gates.
        # They belong in fixed task inputs, not as unscoped raw map members.
        with coordinator.validation_connection() as source_db:
            registered = source_db.execute("SELECT 1 FROM artifacts WHERE path IN (?,?) LIMIT 1",
                (entry["path"], resolved.relative_to(coordinator.root).as_posix())).fetchone()
        if registered:
            raise GateError("registered_source_requires_fixed_input")
        info = coordinator.file_info(entry["path"])
        if info["sha256"] != entry["sha256"] or info["bytes"] != entry["bytes"]:
            raise GateError("preparation_source_fingerprint_changed")
        verified.append(info)
    return verified


def load_map(coordinator, info, **expected):
    try:
        value = json.loads((coordinator.root / info["path"]).read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError) as error:
        raise GateError("invalid_preparation_sources") from error
    return value, verify_map(coordinator, value, path=info["path"], **expected)


def build_map(coordinator, session, task_id, members):
    """AG2 locates its own unsubmitted product; no submit/adopt/opinion."""
    with coordinator.connect() as db:
        control = coordinator.controls(db)
        task = coordinator.get(db, "tasks", task_id)
        if (coordinator.role(session) != "AG2" or task["assignee"] != "AG2"
                or task["task_kind"] != "production" or task["phase"] != "running"
                or task["output"]["type"] != "MaterialUse"
                or task["output"].get("validation_profile") != "preparation_sources"):
            raise GateError("running_ag2_preparation_sources_task_required")
        coordinator.preflight(db, {"task_id": task_id}, control)
        coordinator.gate(control, {task_id, task["output"]["id"]} | set(task["scope"]), {task["intended_use"]})
        if not isinstance(members, list) or not 4 <= len(members) <= 64:
            raise GateError("invalid_preparation_sources")
        provisional = []
        for index, member in enumerate(members):
            if not isinstance(member, dict) or set(member) != {"id", "kind", "path"}:
                raise GateError("invalid_preparation_sources")
            provisional.append({**member, "sha256": sha(str(index).encode("ascii")), "bytes": 1})
        validate_map({"version": VERSION, "artifact_ref": task["draft_ref"], "scope": task["scope"],
                      "intended_use": task["intended_use"], "entries": provisional})
        entries = []
        for member in members:
            if not isinstance(member, dict) or set(member) != {"id", "kind", "path"}:
                raise GateError("invalid_preparation_sources")
            entries.append({**member, **coordinator.file_info(member["path"])})
        value = {"version": VERSION, "artifact_ref": task["draft_ref"], "scope": task["scope"],
                 "intended_use": task["intended_use"], "entries": entries}
        verify_map(coordinator, value)
        if coordinator.controls(db) != control:
            raise GateError("control_changed_during_read")
        return value
