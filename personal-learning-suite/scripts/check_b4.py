"""Check B4 or the complete synthetic suite, retaining actual per-case results."""
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


def main(default_scope="all"):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=["all", "teaching", "planning"], default=default_scope)
    parser.add_argument("--report")
    parser.add_argument("--output")
    args = parser.parse_args()
    pattern = "test_*.py" if args.scope == "all" else f"test_b4_{args.scope}.py"
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=pattern)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CaseResult).run(tests)
    raw = output_path(args.output or f"validation/b4-{args.scope}-runtime-output.txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(stream.getvalue(), encoding="utf-8")
    from runtime.learning_store import SCHEMA_VERSION, STORE_VERSION
    from runtime.learning_teaching_b4 import VERSION as TEACHING_VERSION
    from runtime.learning_planning import VERSION as PLANNING_VERSION
    report = {
        "batch": "B4", "scope": args.scope, "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "synthetic_only": True, "versions": {"shared": SCHEMA_VERSION, "store": STORE_VERSION,
            "teaching_specialist": TEACHING_VERSION, "planning": PLANNING_VERSION},
        "executor": "scripts/check_b4.py; Python unittest", "checker": "Independent initial test authors; primary agent reviewed and repaired failures",
        "host_versions": {"python": platform.python_version(), "platform": platform.platform(), "sqlite": sqlite3.sqlite_version},
        "status": "passed" if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else "failed",
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "cases": result.cases, "raw_output_path": str(raw),
        "limitations": ["Artificial goals, original answers, grants, observations, costs and references only.",
            "Software checks declarations and controls; it does not prove content correctness, learning efficacy or real host authority.",
            "B5 automatic single-entry orchestration and B6 host delegation remain unimplemented.",
            "Reports and request copies are outside managed store deletion scope."],
    }
    path = output_path(args.report or f"validation/b4-{args.scope}-runtime-report.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.scope == "all":
        for scope in ("teaching", "planning"):
            prefix = f"test_b4_{scope}."
            cases = [c for c in result.cases if c["case"].startswith(prefix)]
            selected = {**report, "scope": scope, "tests_run": len(cases), "cases": cases,
                        "failures": sum(c["status"] == "failed" for c in cases),
                        "errors": sum(c["status"] == "error" for c in cases), "skipped": sum(c["status"] == "skipped" for c in cases)}
            selected["status"] = "passed" if cases and all(c["status"] == "passed" for c in cases) else "failed"
            (ROOT / f"validation/b4-{scope}-runtime-report.json").write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B4 {args.scope}: {report['status']}; {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped.")
    print(f"Report: {path}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
