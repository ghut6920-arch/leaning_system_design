"""Audit this maintenance scope, file links and public framework dependencies."""
from pathlib import Path
from urllib.parse import unquote
import argparse
import difflib
import hashlib
import json
import os
import re
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SUITE = ROOT / "personal-learning-suite"
COURSE = ROOT / "learning/embodied-intelligence"
REPORT = ROOT / "docs/implementation/AI个人学习系统_全策略编译与认知主线修复_2026-10-06.md"
GUIDES = [COURSE / p for p in ["AGENTS.md", "MODEL_ENTRY.md", "FRAMEWORK.md", "START_PROMPT.md", "INTERACTION.md"]]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-manifest", action="store_true")
    args = parser.parse_args()
    baseline = json.loads((OUT / "baseline.json").read_text(encoding="utf-8"))
    changed = [name for name, value in baseline["public_files"].items()
               if not (ROOT / name).is_file() or sha(ROOT / name) != value]
    active = sorted([*(SUITE / "src/agents").glob("*.md"), *(SUITE / "src/skills").rglob("*.md")])
    generated = sorted(p for p in (SUITE / "resources/strategies").rglob("*") if p.is_file())
    other = [ROOT / p for p in ["docs/README.md", "personal-learning-suite/README.md", "personal-learning-suite/src/README.md",
             "personal-learning-suite/contracts/strategies-b3c.md", "personal-learning-suite/resources/README.md",
             "personal-learning-suite/resources/runtime-dependencies.json", "personal-learning-suite/specs/skills/SK06-learning-strategies.md",
             "personal-learning-suite/scripts/build_b3c_resources.py", "personal-learning-suite/scripts/check_b3c.py",
             "personal-learning-suite/tests/test_b3c_strategies.py", "learning/embodied-intelligence/framework-manifest.json",
             "personal-learning-suite/validation/full-fidelity-audit-2026-10-05/reviewers/design-assessment-fresh/outputs/R3-affine-correction-and-materials.md"]]
    allowed = {p.relative_to(ROOT).as_posix() for p in active + generated + GUIDES + other}
    unexpected = sorted(set(changed) - allowed)
    source_errors = [n for n in baseline["source_files"] if not (ROOT / n).is_file() or sha(ROOT / n) != baseline["public_files"][n]]
    artifacts = [p for p in generated if p.suffix in {".json", ".md"}]
    assets = sorted((SUITE / "src/skills/learning-materials/assets").glob("*.png"))
    pointers = active + assets + [SUITE / "contracts/shared-contracts.md"] + artifacts + GUIDES
    manifest_file = COURSE / "framework-manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8-sig"))
    if manifest["mode"] != "manual_files" or any(manifest[k] is not False for k in ["native_skill_installation", "real_runtime_binding", "independent_agents_started"]):
        raise ValueError("Changed framework capability claims")
    if args.refresh_manifest:
        if unexpected or source_errors:
            raise ValueError("Refuse refresh with source/scope drift")
        manifest["entries"] = [{"path": Path(os.path.relpath(p, COURSE)).as_posix(), "sha256": sha(p)} for p in sorted(set(pointers))]
        manifest["generated_at"] = "2026-10-06"
        manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    errors = []
    paths = [(COURSE / entry["path"]).resolve() for entry in manifest["entries"]]
    if set(paths) != {p.resolve() for p in pointers} or len(paths) != len(set(paths)):
        errors.append("manifest_scope")
    for entry, path in zip(manifest["entries"], paths):
        if not path.is_file() or sha(path) != entry["sha256"]:
            errors.append(entry["path"])
    docs = set(active + GUIDES + [p for p in other if p.suffix == ".md"]) | set(OUT.rglob("*.md")) | {REPORT}
    links, broken = 0, []
    for p in sorted(docs):
        if not p.is_file():
            continue
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", p.read_text(encoding="utf-8-sig")):
            target = target.strip("<>").split("#")[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            target = re.sub(r":\d+$", "", unquote(target))
            links += 1
            if not (p.parent / target).resolve().is_file():
                broken.append({"file": p.relative_to(ROOT).as_posix(), "target": target})
    diff = []
    with zipfile.ZipFile(OUT / "before-public.zip") as z:
        for name in sorted(changed):
            if name.endswith((".md", ".py")) and name in z.namelist():
                before = z.read(name).decode("utf-8-sig").replace("\r\n", "\n").splitlines(True)
                after = (ROOT / name).read_text(encoding="utf-8-sig").splitlines(True)
                diff.extend(difflib.unified_diff(before, after, fromfile="before/" + name, tofile="after/" + name))
    (OUT / "public-changes.diff").write_text("".join(diff), encoding="utf-8")
    result = {"status": "pass" if not (unexpected or source_errors or errors or broken) else "fail",
              "changed_existing_files": sorted(changed), "unexpected_changes": unexpected,
              "registered_sources_checked": len(baseline["source_files"]), "source_errors": source_errors,
              "links_checked": links, "broken_links": broken, "manifest_entries": len(manifest["entries"]), "manifest_errors": errors,
              "limitations": ["File checks do not validate cognitive quality or model compliance", "No personal answers copied or learner hashes stored"]}
    (OUT / "integrity-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["status", "unexpected_changes", "registered_sources_checked", "source_errors", "links_checked", "broken_links", "manifest_entries", "manifest_errors"]}, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
