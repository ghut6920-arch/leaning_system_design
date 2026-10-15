"""Task & Artifact Coordinator entry for the actual manual-file learning host."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator.complete import TaskArtifactCoordinator
from coordinator.publication import publish_file
from coordinator.reading import add_read_arguments, read_options, verified_view
from coordinator.workspace import FileControlGate, GateError


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--role", required=True, choices=["AG0", "AG1", "AG2", "AG3"])
    parser.add_argument("--control-projection", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--evidence-kind", required=True, choices=["real_file_metadata", "synthetic_demo"])
    commands.add_parser("state")
    commands.add_parser("brief")
    event = commands.add_parser("events")
    event.add_argument("--after-sequence", type=int, default=0)
    event.add_argument("--limit", type=int, default=100)
    inbox = commands.add_parser("inbox")
    inbox.add_argument("--consumer-id", required=True)
    inbox.add_argument("--limit", type=int, default=100)
    for command in ("boundary", "snapshot"):
        target = commands.add_parser(command)
        target.add_argument("--task-id", required=True)
    compare = commands.add_parser("diff")
    compare.add_argument("--artifact-id", required=True)
    compare.add_argument("--old-revision", type=int, required=True)
    compare.add_argument("--new-revision", type=int, required=True)
    current = commands.add_parser("current")
    current.add_argument("--artifact-id", required=True)
    current.add_argument("--intended-use", required=True)
    current.add_argument("--scope", action="append", required=True)
    add_read_arguments(current, default_view="metadata", allow_base64=True)
    operation = commands.add_parser("operation")
    operation.add_argument("--operation-id", required=True)
    receipt = commands.add_parser("receipt")
    receipt.add_argument("--receipt-id", required=True)
    recovery = commands.add_parser("recover")
    recovery.add_argument("--scan-root", action="append", default=[])
    execute = commands.add_parser("execute")
    execute.add_argument("--action", required=True, choices=["register", "start", "draft", "submit", "confirm", "review", "recheck", "adopt", "finish", "refresh", "upgrade", "bootstrap", "ack_events"])
    execute.add_argument("--request-file", type=Path, required=True)
    publication = commands.add_parser("publish")
    publication.add_argument("--source-path", required=True)
    publication.add_argument("--version-path", required=True)
    publication.add_argument("--request-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        projection = args.control_projection or args.workspace / "coordination/control.json"
        gate = FileControlGate(args.workspace, projection) if projection.is_file() else None
        c = TaskArtifactCoordinator(args.workspace, gate)
        session = c.bind_local_operator(args.role)
        if args.command == "init":
            if args.role != "AG0":
                raise GateError("ag0_initialization_required")
            result = c.initialize(evidence_kind=args.evidence_kind)
        elif args.command == "brief":
            print(c.brief(session), end="")
            return 0
        elif args.command == "state":
            result = c.status(session)
        elif args.command == "events":
            result = c.events(session, after_sequence=args.after_sequence, limit=args.limit)
        elif args.command == "inbox":
            result = c.inbox(session, args.consumer_id, limit=args.limit)
        elif args.command == "boundary":
            result = c.boundary(session, args.task_id)
        elif args.command == "snapshot":
            result = {"status": "ok", "snapshot": [{**{k: v for k, v in i.items() if k != "content"}, "content_base64": base64.b64encode(i["content"]).decode("ascii")} for i in c.read_snapshot(session, args.task_id)]}
        elif args.command == "diff":
            result = c.diff(session, {"id": args.artifact_id, "revision": args.old_revision}, {"id": args.artifact_id, "revision": args.new_revision})
        elif args.command == "current":
            item = c.resolve(session, args.artifact_id, args.intended_use, args.scope)
            result = {"status": "ok", **verified_view(item, root=c.root, **read_options(args))}
        elif args.command == "operation":
            result = c.operation(session, args.operation_id)
        elif args.command == "receipt":
            result = c.receipt(session, args.receipt_id)
        elif args.command == "recover":
            result = c.recover(session, scan_roots=args.scan_root)
        elif args.command == "publish":
            result = publish_file(c, session, source_path=args.source_path, version_path=args.version_path,
                                  request=json.loads(args.request_file.read_text(encoding="utf-8-sig")))
        else:
            result = c.execute(session, args.action, json.loads(args.request_file.read_text(encoding="utf-8-sig")))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in {"ok", "committed"} else 1
    except (GateError, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "rejected", "reasons": [getattr(error, "code", type(error).__name__)]}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
