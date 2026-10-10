"""Run the finite B3a behavior slice and record observed test outcomes."""
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
    parser.add_argument("--report", default="validation/b3a-runtime-report.json")
    parser.add_argument("--output", default="validation/b3a-runtime-output.txt")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_b3a_assessment.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CaseResult).run(suite)
    report_path, raw_path = output_path(args.report), output_path(args.output)
    for path in (report_path, raw_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(stream.getvalue(), encoding="utf-8")
    from runtime.learning_assessment import VERSION
    from runtime.learning_store import SCHEMA_VERSION, STORE_VERSION
    report = {
        "batch": "B3a", "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "versions": {"shared": SCHEMA_VERSION, "store": STORE_VERSION, "assessment": VERSION},
        "executor": "scripts/check_b3a.py; Python unittest", "checker": "Independent B3a test author; root added audit regressions and reviewed observed outcomes",
        "status": "passed" if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else "failed",
        "synthetic_only": True, "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "cases": result.cases, "raw_output_path": str(raw_path),
        "host_versions": {"python": platform.python_version(), "platform": platform.platform(), "sqlite": sqlite3.sqlite_version},
        "limitations": [
            "Artificial fixtures in isolated temporary directories; no actual learner, course, diagnosis, or teaching exposure.",
            "Operation support findings are professional input declarations; this code does not grade arbitrary answers or establish their truth.",
            "Timeline completeness, task qualification, material validity, and active authorization are fixture declarations rather than host attestations.",
            "AG0 and AG3 entry actors are fixture configuration; no real identity binding, child delegation, clock expiration, or output interception is tested.",
            "Delay checks use supplied event/contact facts; no scheduler, automatic observation, new test, need, or plan is created.",
            "Deletion controls the store; request files, stdout, reports, caller memory, external histories, and backups remain outside that deletion scope.",
            "This finite B3a slice does not establish complete B10 cases, V1—V4 outcomes, or learning efficacy.",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B3a: {report['status']}; {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped.")
    print(f"Report: {report_path}")
    print(f"Test output: {raw_path}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
