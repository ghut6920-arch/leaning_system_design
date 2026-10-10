"""Check maintenance scope, immutable originals, file links and course fingerprints."""
from pathlib import Path
from urllib.parse import unquote
import difflib
import hashlib
import json
import re
import sys
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SUITE = ROOT / "personal-learning-suite"
COURSE = ROOT / "learning/embodied-intelligence"
REPORT = ROOT / "docs/implementation/AI个人学习系统_认知备课质量升级_2026-10-10.md"
PROTECTED_ROOTS = [ROOT / p for p in ["docs/research", "docs/designs",
    "personal-learning-suite/src", "personal-learning-suite/resources",
    "personal-learning-suite/contracts", "learning/embodied-intelligence"]]
NEW_REFERENCE = "../../personal-learning-suite/src/skills/learning-teaching/references/preparation-quality-examples.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    result = set()
    for folder in PROTECTED_ROOTS:
        for path in folder.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(ROOT).as_posix()
            if relative.startswith("learning/embodied-intelligence/reviews/"):
                continue
            result.add(relative)
    return result


def main():
    baseline = json.loads((OUT / "baseline.json").read_text(encoding="utf-8"))
    allowed = set(baseline["allowed_changes"])
    changed = {name for name, value in baseline["files"].items()
               if not (ROOT / name).is_file() or sha(ROOT / name) != value}
    added = inventory() - set(baseline["files"])
    unexpected = sorted((changed | added) - allowed)
    originals = {name for name in baseline["files"]
                 if name.startswith(("docs/research/", "docs/designs/"))}
    source_errors = sorted(originals & changed)
    manifest_file = COURSE / "framework-manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8-sig"))
    with zipfile.ZipFile(OUT / "before-public-files.zip") as archive:
        old_manifest = json.loads(archive.read("learning/embodied-intelligence/framework-manifest.json").decode("utf-8-sig"))
    fixed = [key for key in old_manifest if key not in {"generated_at", "entries"}]
    manifest_errors = [key for key in fixed if manifest.get(key) != old_manifest[key]]
    if "--refresh" in sys.argv:
        if unexpected or source_errors or manifest_errors:
            raise ValueError("Refuse refresh while scope, source or capability changes exist")
        if not any(row["path"] == NEW_REFERENCE for row in manifest["entries"]):
            manifest["entries"].append({"path": NEW_REFERENCE, "sha256": ""})
        for row in manifest["entries"]:
            path = (COURSE / row["path"]).resolve()
            if not path.is_file():
                raise ValueError(f"Manifest target is not a file: {row['path']}")
            row["sha256"] = sha(path)
        manifest["generated_at"] = "2026-10-10"
        manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    expected_paths = {row["path"] for row in old_manifest["entries"]} | {NEW_REFERENCE}
    actual_paths = [row["path"] for row in manifest["entries"]]
    if set(actual_paths) != expected_paths or len(actual_paths) != len(set(actual_paths)):
        manifest_errors.append("entry_set_or_duplicates")
    if manifest["generated_at"] != "2026-10-10":
        manifest_errors.append("revision_date")
    for row in manifest["entries"]:
        path = (COURSE / row["path"]).resolve()
        if not path.is_file() or sha(path) != row["sha256"]:
            manifest_errors.append(row["path"])
    # Create the report's output targets before checking links to those outputs.
    changed = {name for name, value in baseline["files"].items()
               if not (ROOT / name).is_file() or sha(ROOT / name) != value}
    diff = []
    with zipfile.ZipFile(OUT / "before-public-files.zip") as archive:
        for name in sorted(changed | added):
            if name.endswith(".md") and (ROOT / name).is_file():
                before = archive.read(name).decode("utf-8-sig").replace("\r\n", "\n").splitlines(True) if name in archive.namelist() else []
                after = (ROOT / name).read_text(encoding="utf-8-sig").splitlines(True)
                diff.extend(difflib.unified_diff(before, after, fromfile="before/" + name, tofile="after/" + name))
    (OUT / "public-changes.diff").write_text("".join(diff), encoding="utf-8")
    (OUT / "integrity-result.json").write_text('{"status":"pending"}\n', encoding="utf-8")
    active = set((SUITE / "src/skills").rglob("*.md")) | set((SUITE / "src/agents").glob("*.md"))
    docs = active | set(COURSE.glob("*.md")) | set(OUT.rglob("*.md")) | {REPORT}
    missing_docs = [str(path) for path in docs if not path.is_file()]
    checked_links, broken = 0, []
    for path in sorted(docs):
        if not path.is_file():
            continue
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8-sig")):
            target = target.strip().strip("<>").split("#")[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            target = re.sub(r":\d+$", "", unquote(target))
            checked_links += 1
            if not (path.parent / target).resolve().is_file():
                broken.append({"file": path.relative_to(ROOT).as_posix(), "target": target})
    course_changed = sorted(name for name in changed | added if name.startswith("learning/embodied-intelligence/"))
    result = {
        "date": "2026-10-10", "status": "pass" if not (unexpected or source_errors or manifest_errors or broken or missing_docs) else "fail",
        "baseline_files_checked": len(baseline["files"]), "changed_public_files": sorted(changed | added),
        "unexpected_changes": unexpected, "research_and_design_originals_checked": len(originals), "source_errors": source_errors,
        "course_changes": course_changed, "markdown_files_checked": len(docs), "links_checked": checked_links,
        "broken_links": broken, "missing_documents": missing_docs, "manifest_entries": len(manifest["entries"]),
        "manifest_errors": manifest_errors, "limits": ["Hash/link checks do not evaluate teaching or learning outcomes",
        "Existing course review files excluded; no review files edited by this upgrade",
        "Protected snapshot covers sources, runtime definitions, resources, contracts and course records, not all workspace files"]}
    (OUT / "integrity-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ["status", "baseline_files_checked", "research_and_design_originals_checked",
        "links_checked", "manifest_entries", "unexpected_changes", "broken_links", "manifest_errors"]}, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
