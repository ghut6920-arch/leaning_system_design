"""Check this change's public links, source immutability and manifest pointers."""
from pathlib import Path
from urllib.parse import unquote
import argparse
import hashlib
import json
import re
import difflib
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SUITE = ROOT / "personal-learning-suite"
COURSE = ROOT / "learning/embodied-intelligence"

ALLOWED = {
    "personal-learning-suite/src/skills/learning-teaching/references/design-whole.md",
    "personal-learning-suite/src/skills/personal-learning/references/session-entry.md",
    "personal-learning-suite/src/skills/personal-learning/SKILL.md",
    "personal-learning-suite/src/skills/learning-teaching/SKILL.md",
    "personal-learning-suite/src/skills/learning-planning/SKILL.md",
    "personal-learning-suite/src/skills/learning-planning/references/multi-scale-plan.md",
    "personal-learning-suite/src/skills/learning-goals/SKILL.md",
    "personal-learning-suite/src/skills/learning-goals/references/goal-design.md",
    "personal-learning-suite/src/skills/learning-materials/SKILL.md",
    "personal-learning-suite/src/skills/learning-materials/references/materials-workflow.md",
    "personal-learning-suite/src/skills/learning-teaching/references/encoding.md",
    "personal-learning-suite/src/skills/learning-teaching/references/post-encoding.md",
    "personal-learning-suite/src/skills/learning-teaching/references/c0.md",
    "personal-learning-suite/src/skills/learning-teaching/references/teaching-examples.md",
    "personal-learning-suite/src/agents/AG0-coach.md",
    "personal-learning-suite/src/agents/AG1-design-planning.md",
    "personal-learning-suite/src/agents/AG2-materials.md",
    "personal-learning-suite/src/agents/AG3-assessment.md",
    "personal-learning-suite/src/README.md",
    "docs/README.md",
    "personal-learning-suite/validation/full-fidelity-audit-2026-10-05/README.md",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-manifest", action="store_true")
    args = parser.parse_args()
    baseline = json.loads((OUT / "baseline.json").read_text(encoding="utf-8"))
    changed = [name for name, value in baseline["public_files"].items()
               if not (ROOT / name).is_file() or digest(ROOT / name) != value]
    unexpected = sorted(set(changed) - ALLOWED)
    frozen_errors = [name for name in baseline["source_files"]
                     if not (ROOT / name).is_file() or digest(ROOT / name) != baseline["public_files"][name]]

    active = sorted([*(SUITE / "src/agents").glob("*.md"), *(SUITE / "src/skills").rglob("*.md")])
    assets = sorted((SUITE / "src/skills/learning-materials/assets").glob("*.png"))
    expected = {p.resolve() for p in active + assets + [SUITE / "contracts/shared-contracts.md"]}
    manifest_file = COURSE / "framework-manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8-sig"))
    errors = []
    paths = [(COURSE / x["path"]).resolve() for x in manifest["entries"]]
    if set(paths) != expected or len(paths) != len(set(paths)):
        errors.append("manifest_scope")
    if manifest["mode"] != "manual_files" or any(manifest[k] is not False for k in
            ["native_skill_installation", "real_runtime_binding", "independent_agents_started"]):
        errors.append("manifest_capabilities")
    if args.refresh_manifest:
        if errors or unexpected or frozen_errors:
            raise SystemExit("Refuse manifest refresh with public scope/source errors")
        for entry, path in zip(manifest["entries"], paths):
            entry["sha256"] = digest(path)
        manifest["generated_at"] = "2026-10-05"
        manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for entry, path in zip(manifest["entries"], paths):
        if not path.is_file() or digest(path) != entry["sha256"]:
            errors.append(entry["path"])

    docs = set(active) | set(OUT.rglob("*.md"))
    docs |= {ROOT / name for name in ALLOWED if name.endswith(".md")}
    report_file = ROOT / "docs/implementation/AI个人学习系统_本次学习完整备课修复_2026-10-05.md"
    if report_file.exists():
        docs.add(report_file)
    broken, links = [], 0
    for path in sorted(docs):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8-sig")
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", content):
            target = target.strip("<>").split("#")[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            target = re.sub(r":\d+$", "", unquote(target))
            if not (path.parent / target).resolve().is_file():
                broken.append({"file": path.relative_to(ROOT).as_posix(), "target": target})
            links += 1

    changes = []
    with zipfile.ZipFile(OUT / "before-instructions.zip") as archive:
        for name in sorted(changed):
            if name.endswith(".md") and name in archive.namelist():
                # Normalize line endings only for the readable diff; scope hashes stay byte-exact.
                before = archive.read(name).decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").splitlines(True)
                after = (ROOT / name).read_text(encoding="utf-8-sig").splitlines(True)
                changes.extend(difflib.unified_diff(before, after, fromfile="before/" + name, tofile="after/" + name))
    (OUT / "public-changes.diff").write_text("".join(changes), encoding="utf-8")
    result = {"status": "pass" if not (unexpected or frozen_errors or errors or broken) else "fail",
              "changed_existing_public_files": sorted(changed), "unexpected_public_changes": unexpected,
              "frozen_sources_checked": len(baseline["source_files"]), "frozen_source_errors": frozen_errors,
              "public_instruction_files": len(active), "links_checked": links, "broken_links": broken,
              "manifest_entries": len(manifest["entries"]), "manifest_errors": errors,
              "limitations": ["Links and fingerprints do not validate teaching quality",
                              "No learner fingerprints or records are persisted in this report"]}
    (OUT / "integrity-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["status", "unexpected_public_changes", "frozen_sources_checked",
          "frozen_source_errors", "public_instruction_files", "links_checked", "broken_links",
          "manifest_entries", "manifest_errors"]}, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
