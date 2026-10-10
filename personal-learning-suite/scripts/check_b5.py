"""Check B5 or the complete synthetic suite without rewriting older reports."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import platform
import sqlite3
import sys
import unittest

from check_b1 import CaseResult, output_path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=["entry", "all"], default="entry")
    parser.add_argument("--report")
    parser.add_argument("--output")
    args = parser.parse_args()
    pattern = "test_*.py" if args.scope == "all" else "test_b5_entry.py"
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=pattern)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CaseResult).run(tests)
    raw = output_path(args.output or f"validation/b5-{args.scope}-runtime-output.txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(stream.getvalue(), encoding="utf-8")
    from runtime.learning_store import SCHEMA_VERSION, STORE_VERSION
    report = {"batch": "B5", "scope": args.scope, "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "synthetic_only": True, "versions": {"shared": SCHEMA_VERSION, "store": STORE_VERSION, "entry": "pl-entry/0.1.0"},
        "executor": "scripts/check_b5.py; Python unittest", "checker": "Independent B5 integration test author; root reviews actual results",
        "host_versions": {"python": platform.python_version(), "platform": platform.platform(), "sqlite": sqlite3.sqlite_version},
        "status": "passed" if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else "failed",
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "cases": result.cases, "raw_output_path": str(raw),
        "limitations": ["All goals, findings, original responses, costs, exposure and grants are explicit fictional declarations.",
            "Serial single-entry orchestration preserves managed controls; it does not verify semantic correctness or learning efficacy.",
            "B6 authenticated host role binding and asynchronous delegation are outside this B5 slice.",
            "External requests, stdout and reports remain outside managed store deletion scope."]}
    path = output_path(args.report or f"validation/b5-{args.scope}-runtime-report.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B5 {args.scope}: {report['status']}; {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped.")
    print(f"Report: {path}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
