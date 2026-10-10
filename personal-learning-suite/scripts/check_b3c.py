"""Run the finite synthetic B3c behavior slice and preserve its observed report."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import platform
import sqlite3
import sys
import unittest

from check_b1 import CaseResult

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def output_path(value):
    candidate = Path(value)
    destination = candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
    if not destination.is_relative_to(ROOT):
        raise ValueError("B3c verification output must stay inside the development suite.")
    return destination


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="validation/b3c-runtime-report.json")
    parser.add_argument("--output", default="validation/b3c-runtime-output.txt")
    args = parser.parse_args()
    try:
        report_path, raw_path = output_path(args.report), output_path(args.output)
    except ValueError as error:
        parser.error(str(error))
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_b3c_strategies.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CaseResult).run(tests)
    for path in (report_path, raw_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(stream.getvalue(), encoding="utf-8")
    from runtime.learning_strategies import VERSION
    from runtime.learning_store import SCHEMA_VERSION, STORE_VERSION
    report = {
        "batch": "B3c", "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "versions": {"shared": SCHEMA_VERSION, "store": STORE_VERSION, "strategies": VERSION},
        "executor": "scripts/check_b3c.py; Python unittest",
        "checker": "Automated unittest; caller reviews actual results, no independent agent is implied",
        "status": "passed" if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else "failed",
        "synthetic_only": True, "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "cases": result.cases, "raw_output_path": str(raw_path),
        "host_versions": {"python": platform.python_version(), "platform": platform.platform(), "sqlite": sqlite3.sqlite_version},
        "limitations": [
            "Artificial fixtures and temporary SQLite workspaces; no real course, learner response, or actual teaching.",
            "Resources and declared compatibility are checked; this does not establish domain truth, hidden semantic leakage, or method efficacy.",
            "All sixty Encoding packets are loaded with their full carriers; availability does not approve any lesson's adaptation or cognitive work.",
            "Catalog integrity and source versions do not independently reverify research papers or create a causal strategy ranking.",
            "AG1/AG0 actors are fixture configuration, not authenticated host identity or deployed multi-agent authority.",
            "Only managed records are subject to SQLite deletion; external requests, stdout copies, host history, and already loaded context remain outside its control.",
            "Passing this finite slice does not establish complete B10 scenarios, real V1—V4 outcomes, or learning benefits.",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B3c: {report['status']}; {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped.")
    print(f"Report: {report_path}")
    print(f"Test output: {raw_path}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
