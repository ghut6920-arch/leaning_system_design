"""Materialize finite authored text at explicit, immutable runtime paths.

The model returns text only. A preparation output specification names every
member in advance; the executor inventories those bytes using the existing
preparation-sources contract. It never executes authored code or chooses paths.
"""
from __future__ import annotations

import json
import os
from pathlib import Path, PureWindowsPath

from .preparation_sources import VERSION, build_map, validate_map, verify_map
from .workspace import GateError, encode, ref, sha


def validate_output_spec(spec):
    """Validate the complete path capability without reading or writing files."""
    if (not isinstance(spec, dict) or set(spec) != {"kind", "members"}
            or spec["kind"] != "preparation_sources" or not isinstance(spec["members"], list)):
        raise GateError("invalid_runtime_output_spec")
    members = spec["members"]
    entries = []
    for index, member in enumerate(members):
        if not isinstance(member, dict) or set(member) != {"id", "kind", "path"}:
            raise GateError("invalid_runtime_output_spec")
        entries.append({**member, "sha256": sha(str(index).encode("ascii")), "bytes": 1})
    validate_map({"version": VERSION, "artifact_ref": {"id": "runtime-output", "revision": 1},
                  "scope": ["runtime"], "intended_use": "teaching", "entries": entries})
    # Windows aliases must not turn two declared names into one writable file.
    normalized = set()
    for member in members:
        path = member["path"]
        if (any(part.endswith((".", " ")) for part in path.split("/"))
                or any(char in path for char in '<>"|?*')
                or any(ord(char) < 32 for char in path)
                or any(PureWindowsPath(part).is_reserved() for part in path.split("/"))):
            raise GateError("unsafe_runtime_output_path")
        key = path.casefold()
        if key in normalized:
            raise GateError("duplicate_runtime_output_path")
        normalized.add(key)
    return members


def _safe_path(coordinator, relative):
    coordinator.assert_version_path(relative)
    path = (coordinator.root / relative).resolve()
    if not path.is_relative_to(coordinator.root):
        raise GateError("unsafe_runtime_output_path")
    coordinator.assert_version_path(path.relative_to(coordinator.root).as_posix())
    return path


def _bundle(coordinator, session, node, output, output_path):
    members = validate_output_spec(node["output_spec"])
    try:
        value = json.loads(output)
    except (ValueError, TypeError) as error:
        raise GateError("invalid_runtime_output_bundle") from error
    if not isinstance(value, dict) or set(value) != {"files"} or not isinstance(value["files"], list):
        raise GateError("invalid_runtime_output_bundle")
    contents = {}
    for item in value["files"]:
        if (not isinstance(item, dict) or set(item) != {"id", "content"}
                or not isinstance(item["id"], str) or item["id"] in contents
                or not isinstance(item["content"], str) or not item["content"]):
            raise GateError("invalid_runtime_output_bundle")
        contents[item["id"]] = item["content"]
    if set(contents) != {member["id"] for member in members}:
        raise GateError("runtime_output_members_mismatch")
    with coordinator.connect() as db:
        task = coordinator.get(db, "tasks", node.get("task"))
        if (coordinator.role(session) != "AG2" or task["assignee"] != "AG2"
                or task["task_kind"] != "production" or task["phase"] not in {"running", "submitted"}
                or task["output"]["type"] != "MaterialUse"
                or task["output"].get("validation_profile") != "preparation_sources"):
            raise GateError("running_ag2_preparation_sources_task_required")
        if task["phase"] == "submitted":
            # Recovery may re-materialize the exact already delivered bytes,
            # never repurpose some other dispatch's submitted task.
            receipt = db.execute("SELECT 1 FROM runtime_commits WHERE dispatch_id=? AND ref=?",
                                 (session.dispatch["dispatch_id"], encode(ref(task["result_ref"])))).fetchone()
            if not receipt:
                raise GateError("runtime_output_task_already_submitted")
        files, entries, paths = [], [], set()
        for member in members:
            path = _safe_path(coordinator, member["path"])
            key = str(path).casefold()
            if key in paths or path == _safe_path(coordinator, output_path):
                raise GateError("duplicate_runtime_output_path")
            paths.add(key)
            if db.execute("SELECT 1 FROM artifacts WHERE path IN (?,?) LIMIT 1",
                          (member["path"], path.relative_to(coordinator.root).as_posix())).fetchone():
                raise GateError("registered_source_requires_fixed_input")
            try:
                raw = contents[member["id"]].encode("utf-8")
            except UnicodeError as error:
                raise GateError("invalid_utf8") from error
            entries.append({**member, "sha256": sha(raw), "bytes": len(raw)})
            files.append((path, raw))
    manifest = {"version": VERSION, "artifact_ref": task["draft_ref"], "scope": task["scope"],
                "intended_use": task["intended_use"], "entries": entries}
    validate_map(manifest)
    return task, members, files, manifest, "\n".join(contents[member["id"]] for member in members)


def materialize_output(coordinator, session, node, output, output_path, *, assert_current):
    """Validate all output first, then write only new immutable, declared files.

    ``assert_current`` verifies the actual dispatch immediately before writes.
    Identical existing bytes are replayable after a business receipt committed.
    """
    manifest = None
    if "output_spec" in node:
        task, members, files, manifest, authored = _bundle(coordinator, session, node, output, output_path)
        raw_output = encode(manifest).encode("utf-8")
    else:
        files, authored = [], output
        try:
            raw_output = output.encode("utf-8")
        except UnicodeError as error:
            raise GateError("invalid_utf8") from error
    if any(literal not in authored for literal in node.get("expected_output_contains", [])):
        raise GateError("runtime_output_acceptance_failed")
    primary = _safe_path(coordinator, output_path)
    planned = files + ([(primary, raw_output)] if raw_output else [])
    planned_paths = {str(path).casefold() for path, _ in planned}
    if any(str(parent).casefold() in planned_paths for path, _ in planned for parent in path.parents):
        raise GateError("duplicate_runtime_output_path")
    # Check every conflict before creating even the first directory or file.
    for path, raw in planned:
        if path.exists() and (not path.is_file() or path.read_bytes() != raw):
            raise GateError("runtime_output_changed")
        for parent in path.parents:
            if parent == coordinator.root:
                break
            if parent.exists() and not parent.is_dir():
                raise GateError("unsafe_runtime_output_path")
    for path, raw in planned:
        if path.exists():
            continue
        assert_current()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    if manifest is not None:
        if task["phase"] == "running":
            actual = build_map(coordinator, session, task["id"], members)
            if encode(actual) != encode(manifest):
                raise GateError("runtime_output_changed")
        else:
            verify_map(coordinator, manifest, exact=task["result_ref"], scope=task["scope"],
                       intended_use=task["intended_use"], path=output_path)
    return {"path": output_path, "sha256": sha(raw_output), "authored_text": authored}
