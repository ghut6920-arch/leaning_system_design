"""Check this instruction update without writing learning facts or running runtime APIs."""
from pathlib import Path
from urllib.parse import unquote
import hashlib
import json
import re
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SUITE = ROOT / "personal-learning-suite"
COURSE = ROOT / "learning/embodied-intelligence"
NEW_REFERENCE = "../../personal-learning-suite/src/skills/learning-teaching/references/disciplinary-to-teaching.md"
REPORT = ROOT / "docs/implementation/AI个人学习系统_学科研究与教学转换协作修订_2026-10-11.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    baseline = json.loads((OUT / "protected-baseline.json").read_text(encoding="utf-8"))
    changed = [name for name, value in baseline["files"].items()
               if not (ROOT / name).is_file() or sha(ROOT / name) != value]
    manifest_path = COURSE / "framework-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    old = baseline["manifest_before"]
    fixed_errors = [key for key, value in old.items()
                    if key not in {"generated_at", "entries"} and manifest.get(key) != value]
    if "--refresh" in sys.argv:
        if changed or fixed_errors:
            raise ValueError("Refuse refresh: protected originals or capability declarations changed")
        if not any(row["path"] == NEW_REFERENCE for row in manifest["entries"]):
            manifest["entries"].append({"path": NEW_REFERENCE, "sha256": ""})
        for row in manifest["entries"]:
            path = (COURSE / row["path"]).resolve()
            if not path.is_file():
                raise ValueError(f"Missing manifest file: {row['path']}")
            row["sha256"] = sha(path)
        manifest["generated_at"] = "2026-10-11"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    expected = {row["path"] for row in old["entries"]} | {NEW_REFERENCE}
    actual = [row["path"] for row in manifest["entries"]]
    manifest_errors = fixed_errors.copy()
    if set(actual) != expected or len(actual) != len(set(actual)):
        manifest_errors.append("entry_set_or_duplicates")
    if manifest["generated_at"] != "2026-10-11":
        manifest_errors.append("revision_date")
    for row in manifest["entries"]:
        path = (COURSE / row["path"]).resolve()
        if not path.is_file() or sha(path) != row["sha256"]:
            manifest_errors.append(row["path"])
    docs = (set((SUITE / "src/skills").rglob("*.md"))
            | set((SUITE / "src/agents").glob("*.md"))
            | set(COURSE.glob("*.md")) | set(OUT.rglob("*.md"))
            | {REPORT, ROOT / "docs/README.md", SUITE / "README.md",
               SUITE / "specs/skills/SK03-learning-teaching.md"})
    missing, broken, checked_links = [], [], 0
    for path in sorted(docs):
        if not path.is_file():
            missing.append(str(path))
            continue
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8-sig")):
            target = target.strip().strip("<>").split("#")[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            target = re.sub(r":\d+$", "", unquote(target))
            checked_links += 1
            if not (path.parent / target).resolve().is_file():
                broken.append({"file": path.relative_to(ROOT).as_posix(), "target": target})
    result = {
        "date": "2026-10-11",
        "status": "pass" if not (changed or manifest_errors or missing or broken) else "fail",
        "protected_files_checked": len(baseline["files"]), "protected_files_changed": changed,
        "markdown_files_checked": len(docs), "links_checked": checked_links,
        "broken_links": broken, "missing_documents": missing,
        "manifest_entries": len(actual), "manifest_errors": manifest_errors,
        "limits": ["Checks integrity and discoverability, not discipline correctness or learning outcomes",
                   "Originals include already-present user edits and untracked WM preparation files",
                   "Runtime APIs and real learning sessions were not executed"]}
    (OUT / "integrity-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
