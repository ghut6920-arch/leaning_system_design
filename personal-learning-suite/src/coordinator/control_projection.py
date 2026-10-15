"""Diagnose and explicitly replace a source-bound control projection; no prose inference."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile

from .workspace import Coordinator, GateError, sha


def load_projection(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise GateError("duplicate_projection_field")
            result[key] = value
        return result
    data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique)
    Coordinator.validate_control(data)
    refs = data.get("source_refs")
    if not isinstance(refs, list) or not refs:
        raise GateError("control_source_refs_required")
    if any(not isinstance(r, dict) or not isinstance(r.get("path"), str)
           or not re.fullmatch(r"[0-9a-f]{64}", str(r.get("sha256", ""))) for r in refs):
        raise GateError("invalid_control_source_ref")
    return data


def source_rows(gate, data):
    rows, seen = [], set()
    for item in data["source_refs"]:
        path = (gate.root / item["path"]).resolve()
        if not path.is_relative_to(gate.root) or path == gate.path or path in seen:
            raise GateError("invalid_control_source_ref")
        seen.add(path)
        actual = sha(path.read_bytes()) if path.is_file() else None
        rows.append({"path": path.relative_to(gate.root).as_posix(), "expected_sha256": item["sha256"],
                     "actual_sha256": actual, "changed": actual != item["sha256"]})
    return rows


def diagnose(gate):
    raw = gate.path.read_bytes()
    data = load_projection(raw)
    rows = source_rows(gate, data)
    return {"status": "ok", "projection_sha256": sha(raw), "state_revision": data["state_revision"],
            "source_refs": rows, "current": not any(r["changed"] for r in rows),
            "next_action": "来源未变化。" if not any(r["changed"] for r in rows) else
            "按这些原件及新指纹取得实际控制，显式重解释paused_ids/deleted_ids/restrictions；使用control-update提交完整投影，不只刷新指纹。"}


def replace_projection(gate, candidate_path, *, expected_projection_sha256):
    destination = gate.path.resolve()
    if not destination.is_relative_to(gate.root / "coordination") or destination.suffix != ".json":
        raise GateError("projection_destination_outside_coordination")
    lock = destination.with_name("." + destination.name + ".update-lock")
    try:
        with lock.open("x", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except FileExistsError:
        raise GateError("control_projection_busy") from None
    try:
        return _replace_locked(gate, candidate_path, expected_projection_sha256=expected_projection_sha256)
    finally:
        lock.unlink(missing_ok=True)


def _replace_locked(gate, candidate_path, *, expected_projection_sha256):
    destination = gate.path.resolve()
    old_raw = destination.read_bytes()
    if sha(old_raw) != expected_projection_sha256:
        raise GateError("control_projection_changed")
    old = load_projection(old_raw)
    new = load_projection(Path(candidate_path).read_bytes())
    if new["state_revision"] <= old["state_revision"]:
        raise GateError("control_revision_must_advance")
    rationale = new.get("interpretation_rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise GateError("explicit_control_interpretation_required")
    old_rows, rows = source_rows(gate, old), source_rows(gate, new)
    if {r["path"] for r in old_rows} != {r["path"] for r in rows}:
        raise GateError("control_sources_changed")
    if any(r["changed"] for r in rows):
        raise GateError("control_projection_stale")
    # Validate before replacement, then recheck both bindings at the write boundary.
    encoded = (json.dumps(new, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".control-", suffix=".tmp", delete=False) as f:
            name = f.name
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        if sha(destination.read_bytes()) != expected_projection_sha256:
            raise GateError("control_projection_changed")
        if any(r["changed"] for r in source_rows(gate, new)):
            raise GateError("control_projection_stale")
        os.replace(name, destination)
        name = None
    finally:
        if name is not None:
            Path(name).unlink(missing_ok=True)
    return {"status": "ok", "state_revision": new["state_revision"], "projection_sha256": sha(encoded),
            "source_count": len(rows), "meaning": "仅替换显式解释且当前指纹相符的投影；没有解释正文、放行任务或更新采用指针。"}
