"""Run the installed Skill format validator and retain its actual outputs."""
from pathlib import Path
import json
import subprocess
import sys

OUT = Path(__file__).resolve().parent
SUITE = OUT.parents[1]
VALIDATOR = Path("C:/Users/15006/.codex/skills/.system/skill-creator/scripts/quick_validate.py")


def main():
    results = []
    for folder in sorted((SUITE / "src/skills").iterdir()):
        if not (folder / "SKILL.md").is_file():
            continue
        run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(VALIDATOR), str(folder)], capture_output=True, text=True, encoding="utf-8")
        results.append({"skill": folder.name, "exit_code": run.returncode, "output": run.stdout.strip(), "error": run.stderr.strip()})
    payload = {"status": "pass" if all(row["exit_code"] == 0 for row in results) else "fail", "validator": str(VALIDATOR), "results": results,
               "limits": ["Format validation does not evaluate cognition or model execution"]}
    (OUT / "skill-format-results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "skills": len(results)}, ensure_ascii=False))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
