"""Run B4 specialist behavior on isolated artificial records and retain evidence."""
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
    parser.add_argument("--report", default="validation/b4-teaching-runtime-report.json")
    parser.add_argument("--output", default="validation/b4-teaching-runtime-output.txt")
    args = parser.parse_args()
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_b4_teaching.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CaseResult).run(tests)
    report_path, raw_path = output_path(args.report), output_path(args.output)
    for path in (report_path, raw_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(stream.getvalue(), encoding="utf-8")
    from runtime.learning_teaching_b4 import VERSION
    from runtime.learning_store import SCHEMA_VERSION, STORE_VERSION
    report = {
        "batch": "B4-teaching", "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "versions": {"shared": SCHEMA_VERSION, "store": STORE_VERSION, "teaching_specialist": VERSION},
        "executor": "scripts/check_b4_teaching.py; Python unittest",
        "checker": "Independent B4 specialist test author; root reviewed observed outcomes",
        "status": "passed" if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else "failed",
        "synthetic_only": True, "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "cases": result.cases, "raw_output_path": str(raw_path),
        "host_versions": {"python": platform.python_version(), "platform": platform.platform(), "sqlite": sqlite3.sqlite_version},
        "limitations": [
            "All goals, observations, whole references, answers, budgets and grants are developer-made fixtures.",
            "Tests establish preservation, finite branching and controlled specialist entry, not content truth or learning efficacy.",
            "Local sufficiency is a caller declaration; whole review hands off an intact product without assigning overall support.",
            "Existing judgments are reused only within their declared adopted conditions; no new score or automatic test is created.",
            "Sequential SQLite calls do not bind a real host identity, authenticate display or stop an old executor.",
            "Requests, stdout and saved reports are external copies beyond controlled store deletion.",
            "This report covers specialist teaching; B4 planning has its own report and B5/B6 remain later work.",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B4 teaching: {report['status']}; {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped.")
    print(f"Report: {report_path}")
    print(f"Test output: {raw_path}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
