"""Local-operator CLI for explicit task, snapshot, review and adoption operations."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator.workspace import FileControlGate, GateError
from coordinator.reliability import ReliableCoordinator


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--role", required=True, choices=["AG0", "AG1", "AG2", "AG3"],
                        help="Trusted local operator's role assertion, not host authentication")
    parser.add_argument("--control-projection", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--evidence-kind", required=True, choices=["synthetic_demo", "real_file_metadata"])
    commands.add_parser("state")
    events = commands.add_parser("events")
    events.add_argument("--after-sequence", type=int, default=0)
    events.add_argument("--limit", type=int, default=100)
    operation = commands.add_parser("operation")
    operation.add_argument("--operation-id", required=True)
    recover = commands.add_parser("recover")
    recover.add_argument("--scan-root", action="append", default=[])
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--task-id", required=True)
    execute = commands.add_parser("execute")
    execute.add_argument("--action", required=True, choices=["register", "start", "submit", "confirm", "review", "recheck", "adopt", "finish", "refresh", "upgrade"])
    execute.add_argument("--request-file", required=True, type=Path)
    args = parser.parse_args()
    try:
        gate = FileControlGate(args.workspace, args.control_projection) if args.control_projection else None
        coordinator = ReliableCoordinator(args.workspace, gate)
        session = coordinator.bind_local_operator(args.role)
        if args.command == "init":
            if args.role != "AG0":
                raise GateError("ag0_initialization_required")
            result = coordinator.initialize(evidence_kind=args.evidence_kind)
        elif args.command == "state":
            result = coordinator.status(session)
        elif args.command == "events":
            result = coordinator.events(session, after_sequence=args.after_sequence, limit=args.limit)
        elif args.command == "operation":
            result = coordinator.operation(session, args.operation_id)
        elif args.command == "recover":
            result = coordinator.recover(session, scan_roots=args.scan_root)
        elif args.command == "snapshot":
            contents = coordinator.read_snapshot(session, args.task_id)
            result = {"status": "ok", "task_id": args.task_id, "snapshot": [
                {**{k: v for k, v in item.items() if k != "content"},
                 "content_base64": base64.b64encode(item["content"]).decode("ascii")} for item in contents]}
        else:
            request = json.loads(args.request_file.read_text(encoding="utf-8-sig"))
            result = coordinator.execute(session, args.action, request)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in {"ok", "committed"} else 1
    except (GateError, OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"status": "rejected", "reasons": [getattr(error, "code", type(error).__name__)]}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
