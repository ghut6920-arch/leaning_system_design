"""Isolated test worker. Never called automatically by the production CLI."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator.reliability import ReliableCoordinator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--failpoint")
    parser.add_argument("--pause-at")
    parser.add_argument("--pause-marker", type=Path)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--ready", type=Path)
    parser.add_argument("--go", type=Path)
    parser.add_argument("--retry-factual-register", action="store_true")
    parser.add_argument("--register-count", type=int, default=1)
    args = parser.parse_args()
    c = ReliableCoordinator(args.workspace)
    session = c.bind_local_operator(args.role)
    request = json.loads(args.request.read_text(encoding="utf-8"))
    if args.failpoint or args.pause_at:
        def checkpoint(point):
            if point == args.failpoint:
                os._exit(91)
            if point == args.pause_at and not args.pause_marker.exists():
                args.pause_marker.write_text(point, encoding="ascii")
                deadline = time.monotonic() + 15
                while not args.resume.exists():
                    if time.monotonic() >= deadline:
                        raise RuntimeError("test_pause_timeout")
                    time.sleep(.01)
        c.failpoint = checkpoint
    if args.ready:
        args.ready.write_text("ready", encoding="ascii")
    if args.go:
        deadline = time.monotonic() + 15
        while not args.go.exists():
            if time.monotonic() >= deadline:
                raise RuntimeError("test_barrier_timeout")
            time.sleep(.01)
    if args.register_count != 1 and (not args.retry_factual_register or args.action != "register" or not 1 <= args.register_count <= 50):
        raise RuntimeError("invalid_factual_register_stress")
    results = []
    original = request
    for index in range(args.register_count):
        request = json.loads(json.dumps(original))
        if args.register_count > 1:
            request["id"] += f"-{index}"
            request["output"]["id"] += f"-{index}"
            request["operation_id"] += f"-{index}"
            request["expected_state_revision"] = c.status(session)["state_revision"]
        attempts = 0
        while True:
            attempts += 1
            result = c.execute(session, args.action, request)
            if not args.retry_factual_register or result["status"] not in {"busy", "conflict"} or attempts >= 100:
                break
            if args.action != "register":
                raise RuntimeError("automatic_decision_retry_forbidden")
            request["expected_state_revision"] = c.status(session)["state_revision"]
        results.append({"result": result, "attempts": attempts})
    print(json.dumps({**results[-1], "results": results}, ensure_ascii=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
