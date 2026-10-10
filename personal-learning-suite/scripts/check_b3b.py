"""Run B3b C0 behavior on artificial records and retain a compact report."""
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
    parser.add_argument("--report", default="validation/b3b-runtime-report.json")
    parser.add_argument("--output", default="validation/b3b-runtime-output.txt")
    args = parser.parse_args()
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_b3b_teaching.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CaseResult).run(tests)
    report_path, raw_path = output_path(args.report), output_path(args.output)
    for path in (report_path, raw_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(stream.getvalue(), encoding="utf-8")
    from runtime.learning_teaching import VERSION
    from runtime.learning_store import SCHEMA_VERSION, STORE_VERSION
    report = {
        "batch": "B3b", "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "versions": {"shared": SCHEMA_VERSION, "store": STORE_VERSION, "teaching": VERSION},
        "executor": "scripts/check_b3b.py; Python unittest",
        "checker": "Independent C0 test author; root reviewed observed outcomes",
        "status": "passed" if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else "failed",
        "synthetic_only": True, "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "cases": result.cases, "raw_output_path": str(raw_path),
        "host_versions": {"python": platform.python_version(), "platform": platform.platform(), "sqlite": sqlite3.sqlite_version},
        "limitations": [
            "All goals, materials, answers, budgets and grants are developer-made fixtures.",
            "C0 records explicit actions and declared observations; it does not infer semantic correctness or authenticate display.",
            "This C0 slice does not integrate B3a scoring/diagnosis or create a new mastery scale, automatic tests or scheduled plans.",
            "Parent repair uses the shared task and artifact contract; Encoding/Post modules remain B4 work.",
            "Fixture AG0 and serial SQLite calls do not establish real host identity or prevent an old agent from displaying output.",
            "Requests, stdout and saved reports are external copies beyond controlled store deletion.",
            "This establishes a finite software slice, not complete B10 scenarios, V1—V4 or learning efficacy.",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B3b: {report['status']}; {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped.")
    print(f"Report: {report_path}")
    print(f"Test output: {raw_path}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
