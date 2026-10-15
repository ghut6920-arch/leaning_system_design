"""Test-only hard-exit worker for the complete coordinator and file publisher."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator.complete import TaskArtifactCoordinator
from coordinator.publication import publish_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--action", default="submit")
    parser.add_argument("--failpoint")
    parser.add_argument("--source-path")
    parser.add_argument("--version-path")
    args = parser.parse_args()
    c = TaskArtifactCoordinator(args.workspace)
    if args.failpoint:
        c.failpoint = lambda name: os._exit(92) if name == args.failpoint else None
    request = json.loads(args.request.read_text(encoding="utf-8"))
    session = c.bind_local_operator(args.role)
    if args.source_path:
        result = publish_file(c, session, source_path=args.source_path, version_path=args.version_path, request=request)
    else:
        result = c.execute(session, args.action, request)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
