"""Replay an explicit historical case without changing source artifacts or state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator.replay import Replay, ReplayError, write_outputs


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        replay = Replay(args.case)
        report = replay.run()
        output = write_outputs(replay, report, args.output_dir)
    except (ReplayError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"Replay rejected: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], ensure_ascii=False))
    print(f"Report: {output / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
