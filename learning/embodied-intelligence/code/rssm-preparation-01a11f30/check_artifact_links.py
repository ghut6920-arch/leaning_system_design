"""AI-authored structural check of this preparation package only, revision1."""
import json
from pathlib import Path
import re

base = Path(__file__).resolve().parents[2]
package = base / "artifacts/preparation-tests/2026-10-09-rssm-01a11f30"
report = {}
for path in sorted(package.glob("*.md")):
    content = path.read_text(encoding="utf-8-sig")
    controls = [{"codepoint": ord(c), "position": i} for i, c in enumerate(content) if ord(c) < 32 and c not in "\r\n\t"]
    missing = []
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", content):
        target = target.strip("<>").split("#", 1)[0]
        if not target or "://" in target:
            continue
        resolved = Path(target) if Path(target).is_absolute() else path.parent / target
        if not resolved.exists():
            missing.append(target)
    block_open = len(re.findall(r"^\s*\\\[\s*$", content, re.MULTILINE))
    block_close = len(re.findall(r"^\s*\\\]\s*$", content, re.MULTILINE))
    report[path.name] = {"unexpected_controls": controls, "missing_link_targets": missing,
                         "display_math_blocks": [block_open, block_close],
                         "inline_math_pairs": [content.count(r"\("), content.count(r"\)")]}
print(json.dumps(report, indent=2, ensure_ascii=False))
