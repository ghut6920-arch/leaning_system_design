"""Verify the shared B3 handoff and its B1/B2/B3 regression boundaries."""
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
    path = candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Verification output must stay inside the development suite.")
    return path


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="validation/b3-interop-report.json")
    parser.add_argument("--output", default="validation/b3-interop-output.txt")
    args = parser.parse_args()
    report_path, raw_path = output_path(args.report), output_path(args.output)
    stream = io.StringIO()
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_b*.py")
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CaseResult).run(tests)
    from runtime.learning_store import SCHEMA_VERSION, STORE_VERSION
    from runtime.learning_assessment import VERSION as ASSESSMENT_VERSION
    from runtime.learning_teaching import VERSION as TEACHING_VERSION
    from runtime.learning_strategies import VERSION as STRATEGIES_VERSION, CONFIG_VERSION
    report = {
        "batch": "B3-interop", "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "synthetic_only": True, "status": "passed" if result.wasSuccessful() and result.testsRun and not result.skipped else "failed",
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "cases": result.cases, "raw_output_path": str(raw_path), "executor": "scripts/check_b3_interop.py; Python unittest",
        "versions": {"shared": SCHEMA_VERSION, "store": STORE_VERSION, "assessment": ASSESSMENT_VERSION,
                     "teaching": TEACHING_VERSION, "strategy_resources": STRATEGIES_VERSION, "strategy_input": CONFIG_VERSION},
        "host_versions": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version, "platform": platform.platform()},
        "scope": ["Exact adopted configuration -> authorized C0 fact -> explicit response point -> conditional judgment",
                  "One canonical store, immutable originals, one sample identity, current controls and exact historical dependencies",
                  "Regression checks for the implemented B1, B2a, B2b, B3a, B3b and B3c slices"],
        "limitations": ["Artificial declarations, grants, observations and timestamps; no real learner or course.",
                        "Professional findings and completeness remain supplied claims; software does not verify subject truth or actual exposure.",
                        "Explicit handoff only; B5 automatic routing, host authentication, installation and learning efficacy remain unverified.",
                        "Historical configurations missing the explicit material binding require professional recheck for new execution; they are not rewritten."],
    }
    for path in (report_path, raw_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(stream.getvalue(), encoding="utf-8")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B3 interoperability: {report['status']}; {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped.")
    print(f"Report: {report_path}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
