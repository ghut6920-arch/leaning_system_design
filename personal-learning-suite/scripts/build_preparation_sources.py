"""Create an exclusive AG2 source map for an explicitly assigned material task."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator.complete import TaskArtifactCoordinator
from coordinator.preparation_sources import build_map
from coordinator.workspace import FileControlGate, GateError, sha


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--task", required=True)
    parser.add_argument("--members-file", required=True, type=Path)
    parser.add_argument("--output", required=True, help="新的工作区内规范清单路径")
    args = parser.parse_args(argv)
    try:
        projection = args.workspace / "coordination/control.json"
        c = TaskArtifactCoordinator(args.workspace, FileControlGate(args.workspace, projection) if projection.is_file() else None)
        session = c.bind_local_operator("AG2")
        value = build_map(c, session, args.task, json.loads(args.members_file.read_text(encoding="utf-8-sig")))
        # Apply the same safe-root and external-authority rules to the new map.
        if (not isinstance(args.output, str) or not args.output.startswith("artifacts/") or "\\" in args.output
                or ":" in args.output or any(p in {"", ".", ".."} or p.startswith(".") for p in args.output.split("/"))):
            raise GateError("unsafe_preparation_source_path")
        target = (c.root / args.output).resolve()
        if not target.is_relative_to(c.root) or target.is_relative_to(c.meta_root):
            raise GateError("unsafe_preparation_source_path")
        c.assert_version_path(args.output)
        if args.output in {e["path"] for e in value["entries"]}:
            raise GateError("preparation_sources_cannot_include_itself")
        data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Existing maps are never overwritten, even when unregistered.
        with target.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        result = {"status": "ok", "path": args.output, "sha256": sha(data), "bytes": len(data),
                  "entries": len(value["entries"]), "artifact_ref": value["artifact_ref"],
                  "meaning": "静态字节清单；尚未提交、专业确认或采用；不证明教学正确或已读。"}
    except (GateError, OSError, ValueError, KeyError, TypeError) as error:
        result = {"status": "rejected", "problem": getattr(error, "code", type(error).__name__)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
