"""Verify instruction links, public fingerprints and protected originals only."""
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
BASELINE = OUT / "protected-baseline.json"
MUTABLE_COURSE = {"AGENTS.md", "FRAMEWORK.md", "MODEL_ENTRY.md", "framework-manifest.json"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_paths():
    paths = set()
    for dirname in ("research", "designs", "architecture", "analysis", "audits"):
        paths.update(p for p in (ROOT / "docs" / dirname).rglob("*") if p.is_file())
    for dirname in ("runtime",):
        paths.update(p for p in (SUITE / "src" / dirname).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts)
    for dirname in ("contracts", "resources", "scripts", "tests", "fixtures", "templates", "specs"):
        paths.update(p for p in (SUITE / dirname).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts)
    paths.update(p for p in COURSE.rglob("*") if p.is_file()
                 and not set(p.relative_to(COURSE).parts) & {".git", "__pycache__"}
                 and p.relative_to(COURSE).as_posix() not in MUTABLE_COURSE)
    return sorted(paths)


def main():
    manifest_path = COURSE / "framework-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if "--capture" in sys.argv:
        if BASELINE.exists():
            raise ValueError("Refuse to replace an existing baseline")
        baseline = {"files": {p.relative_to(ROOT).as_posix(): sha(p) for p in protected_paths()},
                    "manifest_before": manifest}
        BASELINE.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"captured_files": len(baseline["files"]), "manifest_entries": len(manifest["entries"])}))
        return 0
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    changed = [name for name, value in baseline["files"].items()
               if not (ROOT / name).is_file() or sha(ROOT / name) != value]
    old = baseline["manifest_before"]
    declaration_errors = [key for key, value in old.items()
                          if key not in {"generated_at", "entries"} and manifest.get(key) != value]
    if "--refresh" in sys.argv:
        if changed or declaration_errors:
            raise ValueError("Refuse refresh: protected originals or capability declarations changed")
        for row in manifest["entries"]:
            path = (COURSE / row["path"]).resolve()
            if not path.is_file():
                raise ValueError(f"Missing manifest file: {row['path']}")
            row["sha256"] = sha(path)
        manifest["generated_at"] = "2026-10-11"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    actual = [row["path"] for row in manifest["entries"]]
    expected = {row["path"] for row in old["entries"]}
    manifest_errors = declaration_errors.copy()
    if set(actual) != expected or len(actual) != len(set(actual)):
        manifest_errors.append("entry_set_or_duplicates")
    for row in manifest["entries"]:
        path = (COURSE / row["path"]).resolve()
        if not path.is_file() or sha(path) != row["sha256"]:
            manifest_errors.append(row["path"])
    docs = (set((SUITE / "src/skills").rglob("*.md"))
            | set((SUITE / "src/agents").glob("*.md"))
            | {COURSE / name for name in MUTABLE_COURSE if name.endswith(".md")}
            | set(OUT.rglob("*.md"))
            | {ROOT / "docs/README.md", SUITE / "src/README.md",
               ROOT / "docs/implementation/AI个人学习系统_自由度分析与动态Encoding落实_2026-10-11.md"})
    missing, broken, checked_links = [], [], 0
    for path in sorted(docs):
        if not path.is_file():
            missing.append(path.relative_to(ROOT).as_posix())
            continue
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8-sig")):
            target = target.strip().strip("<>").split("#")[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            target = re.sub(r":\d+$", "", unquote(target))
            checked_links += 1
            if not (path.parent / target).resolve().is_file():
                broken.append({"file": path.relative_to(ROOT).as_posix(), "target": target})
    result = {"date": "2026-10-11", "status": "pass" if not (changed or manifest_errors or missing or broken) else "fail",
              "protected_files_checked": len(baseline["files"]), "protected_files_changed": changed,
              "markdown_files_checked": len(docs), "links_checked": checked_links,
              "broken_links": broken, "missing_documents": missing,
              "manifest_entries": len(actual), "manifest_errors": manifest_errors,
              "limits": ["Integrity and discoverability only; no semantic or learning-outcome score",
                         "No runtime APIs or real learning sessions executed"]}
    (OUT / "integrity-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
