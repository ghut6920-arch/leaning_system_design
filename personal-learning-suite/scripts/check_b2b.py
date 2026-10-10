"""Run the finite B2b behavioral slice and save a content-free test report."""
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
    parser.add_argument("--report", default="validation/b2b-runtime-report.json")
    parser.add_argument("--output", default="validation/b2b-runtime-output.txt")
    args = parser.parse_args()
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_b2b_materials.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CaseResult).run(tests)
    report_path, raw_path = output_path(args.report), output_path(args.output)
    for path in (report_path, raw_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(stream.getvalue(), encoding="utf-8")
    from runtime.learning_materials import VERSION
    from runtime.learning_store import SCHEMA_VERSION, STORE_VERSION
    report = {
        "batch": "B2b", "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "versions": {"shared": SCHEMA_VERSION, "store": STORE_VERSION, "materials": VERSION},
        "executor": "scripts/check_b2b.py; Python unittest",
        "checker": "Independent B2b test author; root reviewed observed outcomes",
        "status": "passed" if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else "failed",
        "synthetic_only": True, "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "cases": result.cases, "raw_output_path": str(raw_path),
        "host_versions": {"python": platform.python_version(), "platform": platform.platform(), "sqlite": sqlite3.sqlite_version},
        "limitations": [
            "Artificial fixtures in isolated temporary directories; no real learner course or responses.",
            "Only declared metadata, exact managed references, annotated leakage, and storage/control behavior are checked by code.",
            "No generic domain truth verifier, OCR/PDF/image parser, semantic leakage detector, or actual exposure recorder.",
            "AG2 is a fixture actor configuration, not authenticated host identity or a bound multi-agent runtime.",
            "Correction tracing covers recorded references; unknown dependencies and four recovery responsibilities stay separate.",
            "This does not establish complete B10 scenarios, V1—V4 outcomes, or learning efficacy.",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B2b: {report['status']}; {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped.")
    print(f"Report: {report_path}")
    print(f"Test output: {raw_path}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
