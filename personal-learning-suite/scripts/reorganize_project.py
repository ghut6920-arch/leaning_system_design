"""Plan, repair references, and verify the 2026-10-04 folder organization.

Moves and cache removal are performed separately with guarded PowerShell native
commands. This helper never edits SQLite or historical JSON/TXT test outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote
import zipfile

SUITE = Path(__file__).resolve().parents[1]
ROOT = SUITE.parent
RECORD = ROOT / "maintenance/organization-2026-10-04"
MANIFEST = RECORD / "manifest.json"
LINK = re.compile(r"(\[[^\]\n]*\]\()([^\)\n]+)(\))")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(value):
    MANIFEST.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def category(name):
    if name.startswith(("01_", "02_", "04_", "Post-Encoding-Dynamics", "post-encoding", "Retrieval-Integration")):
        return "research"
    if "设计提示词" in name:
        return "prompts"
    if "综合审计" in name or "架构审计修复" in name:
        return "audits"
    if re.match(r"AI个人学习系统_B\d", name):
        return "implementation"
    if "顶层设计分析" in name:
        return "analysis"
    if "审阅评估" in name or "检查记录" in name:
        return "reviews"
    if "工作包" in name and ("设计方案" in name or "交接对齐" in name):
        return "designs"
    if name.startswith("AI个人学习系统_"):
        return "architecture"
    raise ValueError(f"Unclassified root document: {name}")


def prepare():
    if MANIFEST.exists():
        raise ValueError("An organization manifest already exists; do not replace the before snapshot.")
    moves = []
    for path in sorted(ROOT.iterdir()):
        if path.is_file() and path.suffix.lower() in {".md", ".json"} and path.name != "README.md":
            moves.append({"old": path.name, "new": f"docs/{category(path.name)}/{path.name}", "kind": "document"})
        elif path.is_dir() and re.match(r"^B\d.*虚构.*空间$", path.name):
            moves.append({"old": path.name, "new": f"examples/workspaces/{path.name}", "kind": "synthetic_workspace"})
    for item in moves:
        source, target = ROOT / item["old"], ROOT / item["new"]
        if not source.resolve().is_relative_to(ROOT) or not target.resolve().is_relative_to(ROOT) or target.exists():
            raise ValueError(f"Unsafe or occupied move: {item}")
    paths = sorted(path for path in ROOT.rglob("*") if path.is_file()
                   and "__pycache__" not in path.parts and not path.is_relative_to(ROOT / "maintenance"))
    RECORD.mkdir(parents=True, exist_ok=True)
    before = [{"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path), "bytes": path.stat().st_size} for path in paths]
    with zipfile.ZipFile(RECORD / "before-organization.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, path.relative_to(ROOT).as_posix())
    registry = json.loads((SUITE / "resources/source-registry.json").read_text(encoding="utf-8-sig"))
    save({"date": "2026-10-04", "status": "planned", "moves": moves, "before_files": before,
          "before_source_registry": registry, "backup": "before-organization.zip",
          "changed_files": [], "source_path_changes": [], "preservation": "SQLite and historical raw JSON/TXT evidence are not rewritten."})
    print(json.dumps({"documents": sum(m["kind"] == "document" for m in moves),
                      "workspaces": sum(m["kind"] == "synthetic_workspace" for m in moves),
                      "snapshotted_files": len(before), "manifest": str(MANIFEST)}, ensure_ascii=False))


def relocated(path, moves):
    resolved = path.resolve()
    for item in moves:
        source = ROOT / item["old"]
        if resolved == source:
            return ROOT / item["new"]
        if item["kind"] == "synthetic_workspace" and resolved.is_relative_to(source):
            return ROOT / item["new"] / resolved.relative_to(source)
    return resolved


def split_target(target):
    angled = target.startswith("<") and target.endswith(">")
    raw = target[1:-1] if angled else target
    path, separator, fragment = raw.partition("#")
    line = re.search(r":\d+(?::\d+)?$", path)
    suffix = line.group() if line else ""
    path = path[:-len(suffix)] if suffix else path
    return path, suffix + (separator + fragment if separator else ""), angled


def repair_link(target, old_parent, new_parent, moves):
    raw, suffix, angled = split_target(target)
    raw = unquote(raw)
    if not raw or "://" in raw or re.match(r"^(mailto|data|app|plugin|codex):", raw):
        return target
    path = Path(raw)
    absolute = path.is_absolute()
    original = path.resolve() if absolute else (old_parent / path).resolve()
    if not original.is_relative_to(ROOT):
        return target
    current = relocated(original, moves)
    if not current.exists():
        return target
    replacement = current.as_posix() if absolute else Path(os.path.relpath(current, new_parent)).as_posix()
    if raw.endswith("/") and current.is_dir():
        replacement += "/"
    replacement += suffix
    return f"<{replacement}>" if angled else replacement


def record_write(path, content, state, reason):
    raw = content.encode("utf-8") if isinstance(content, str) else content
    previous = path.read_bytes()
    if previous == raw:
        return
    path.write_bytes(raw)
    state["changed_files"].append({"path": path.relative_to(ROOT).as_posix(), "before_sha256": hashlib.sha256(previous).hexdigest(),
                                   "after_sha256": digest(path), "reason": reason})


def migrate():
    state = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if state["status"] != "planned":
        raise ValueError("Reference migration is one-shot; inspect the existing manifest before another change.")
    moves = state["moves"]
    reverse = {(ROOT / m["new"]).resolve(): ROOT / m["old"] for m in moves if m["kind"] == "document"}
    for item in moves:
        if (ROOT / item["old"]).exists() or not (ROOT / item["new"]).exists():
            raise ValueError(f"Move not completed: {item}")
    for path in sorted(ROOT.rglob("*.md")):
        if path.is_relative_to(ROOT / "maintenance"):
            continue
        original = reverse.get(path.resolve(), path)
        raw = path.read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig")
        updated = LINK.sub(lambda m: m[1] + repair_link(m[2], original.parent, path.parent, moves) + m[3], text)
        # CLI examples are still executed from the project root.
        for item in moves:
            if item["kind"] == "synthetic_workspace":
                updated = re.sub(r'(--workspace\s+["\']?)' + re.escape(item["old"]) + r'(?=["\'\s`]|$)',
                                 lambda m: m[1] + item["new"], updated)
        record_write(path, (b"\xef\xbb\xbf" if bom else b"") + updated.encode("utf-8"), state,
                     "Relocate Markdown link targets and project-root demo command paths only.")
    registry_path = SUITE / "resources/source-registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8-sig"))
    for source in registry["sources"]:
        old_relative, old_hash = source["project_relative_path"], source["sha256"]
        current = relocated(SUITE / old_relative, moves)
        source["project_relative_path"] = Path(os.path.relpath(current, SUITE)).as_posix()
        source["sha256"] = digest(current)
        state["source_path_changes"].append({"source_id": source["source_id"], "old_path": old_relative,
                                              "new_path": source["project_relative_path"], "before_sha256": old_hash,
                                              "after_sha256": source["sha256"], "reason": "Directory relocation and link-only source edits; no teaching or research claims changed."})
    registry["source_path_base_note"] = "suite_root 指 personal-learning-suite。../docs/ 指向分类保存的设计与研究原文；目录整理映射与原始备份见 ../maintenance/organization-2026-10-04/manifest.json。"
    registry["path_relocation_record"] = "../maintenance/organization-2026-10-04/manifest.json"
    record_write(registry_path, json.dumps(registry, ensure_ascii=False, indent=2) + "\n", state,
                 "Update 19 source locations and fingerprints after link-only source edits; retain prior registration in the manifest.")
    summary_path = SUITE / "validation/architecture-fixes-2026-10-04/repair-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    original_record = (summary_path.parent / summary["implementation_record"]).resolve()
    summary["implementation_record"] = Path(os.path.relpath(relocated(original_record, moves), summary_path.parent)).as_posix()
    record_write(summary_path, json.dumps(summary, ensure_ascii=False, indent=2) + "\n", state, "Repair the implementation-document navigation pointer only.")
    state["status"] = "references_migrated"
    save(state)
    print(json.dumps({"status": state["status"], "changed_files": len(state["changed_files"]),
                      "sources_relocated": len(state["source_path_changes"])}, ensure_ascii=False))


def verify():
    state = json.loads(MANIFEST.read_text(encoding="utf-8"))
    moves = state["moves"]
    changed = {item["path"] for item in state["changed_files"]}
    generated = {path.relative_to(ROOT).as_posix() for path in (SUITE / "resources/strategies").rglob("*") if path.is_file()}
    lost, unexpected, dbs, history = [], [], [], []
    for item in state["before_files"]:
        path = relocated(ROOT / item["path"], moves)
        if not path.is_file():
            lost.append(item["path"])
            continue
        relative = path.relative_to(ROOT).as_posix()
        same = digest(path) == item["sha256"]
        if not same and relative not in changed | generated:
            unexpected.append(relative)
        if path.suffix == ".sqlite3":
            dbs.append({"path": relative, "bytes_unchanged": same})
        if path.is_relative_to(SUITE / "validation") and path.suffix in {".txt", ".json"} and relative not in changed:
            history.append({"path": relative, "bytes_unchanged": same})
    broken = []
    for path in ROOT.rglob("*.md"):
        if path.is_relative_to(ROOT / "maintenance"):
            continue
        for match in LINK.finditer(path.read_text(encoding="utf-8-sig")):
            raw, _, _ = split_target(match[2])
            if not raw or "://" in raw or re.match(r"^(mailto|data|app|plugin|codex):", raw):
                continue
            target = Path(unquote(raw))
            target = target if target.is_absolute() else path.parent / target
            if not target.exists():
                broken.append({"file": path.relative_to(ROOT).as_posix(), "target": match[2]})
    result = {"status": "passed" if not lost and not unexpected and not broken and all(x["bytes_unchanged"] for x in dbs + history) else "failed",
              "moved_documents": sum(m["kind"] == "document" for m in moves), "moved_workspaces": len(dbs),
              "missing_original_files": lost, "unexpected_changed_files": unexpected, "broken_local_links": broken,
              "sqlite_preservation": dbs, "historical_raw_evidence": history}
    (RECORD / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state["status"] = "verified" if result["status"] == "passed" else "verification_failed"
    save(state)
    print(json.dumps({"status": result["status"], "documents": result["moved_documents"], "sqlite_files": len(dbs),
                      "historical_raw_files": len(history), "missing": len(lost), "unexpected_changes": len(unexpected),
                      "broken_links": len(broken)}, ensure_ascii=False))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "migrate", "verify"])
    arguments = parser.parse_args()
    if arguments.phase == "prepare":
        prepare()
    elif arguments.phase == "migrate":
        migrate()
    else:
        raise SystemExit(verify())
