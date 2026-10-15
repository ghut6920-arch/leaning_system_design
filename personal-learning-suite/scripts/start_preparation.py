"""Normal preparation startup; no manual per-chat database setup."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator.complete import TaskArtifactCoordinator
from coordinator.delivery import bounded_output
from coordinator.preparation_start import start_preparation
from coordinator.workspace import FileControlGate, GateError


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--request-file", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.workspace.resolve()
        projection = root / "coordination/control.json"
        coordinator = TaskArtifactCoordinator(root, FileControlGate(root, projection) if projection.is_file() else None)
        request = json.loads(args.request_file.read_text(encoding="utf-8-sig"))
        result = start_preparation(coordinator, request)
    except GateError as error:
        result = {"status": "rejected", "problem": error.code, "runtime_takeover": False,
                  "next_action": "查看已保存的计划和监听回执，修复接管；不得改为模型轮询或重复派发。"}
        if getattr(error, "receipt", None):
            result["listener"] = error.receipt
    except (ValueError, KeyError, TypeError, UnicodeError):
        result = {"status": "rejected", "problem": "invalid_preparation_request", "runtime_takeover": False}
    except (OSError, sqlite3.Error):
        result = {"status": "rejected", "problem": "preparation_storage_unavailable", "runtime_takeover": False}
    print(bounded_output(result), end="")
    return 0 if result["status"] == "committed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
