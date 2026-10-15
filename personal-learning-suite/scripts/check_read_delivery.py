"""Check an exact captured read response; do not feed a reconstructed or source-side copy."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator.delivery import body_nodes, verify_delivery
from coordinator.workspace import GateError


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = verify_delivery(args.file.read_bytes())
        result = {"status": "ok", "received_complete": True,
                  "pages": [{"ref": row.get("ref"), "sha256": row.get("sha256"), "coverage": row["coverage"]}
                            for row in body_nodes(payload)],
                  "meaning": "仅确认这份实际捕获文本的边界、内容和区间；不确认另一层宿主展示，不证明专业阅读或采用。"}
    except (GateError, OSError) as error:
        result = {"status": "rejected", "received_complete": False,
                  "problem": getattr(error, "code", type(error).__name__)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
