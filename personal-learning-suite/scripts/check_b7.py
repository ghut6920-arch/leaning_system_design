"""Check the B7 read-only pilot slice or all fictional behavior checks."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import platform
import re
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
    parser.add_argument("--scope", choices=["pilot", "all"], default="pilot")
    parser.add_argument("--report")
    parser.add_argument("--output")
    args = parser.parse_args()
    raw = output_path(args.output or f"validation/b7-{args.scope}-runtime-output.txt")
    path = output_path(args.report or f"validation/b7-{args.scope}-runtime-report.json")
    # Reject historical batch destinations before running any tests.
    for destination in (raw, path):
        if re.match(r"^b[0-6][abc]?[-_]", destination.name.casefold()):
            parser.error("B7 output must not replace a historical batch report")
    pattern = "test_*.py" if args.scope == "all" else "test_b7_pilot.py"
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=pattern)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CaseResult).run(tests)
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(stream.getvalue(), encoding="utf-8")
    from runtime.learning_store import SCHEMA_VERSION, STORE_VERSION
    from runtime.pilot_b7 import VERSION as PILOT_VERSION
    from runtime.network_b6 import VERSION as NETWORK_VERSION
    from runtime.entry_b5 import VERSION as ENTRY_VERSION
    from runtime.learning_goals import INPUT_VERSION as GOAL_VERSION
    from runtime.learning_materials import VERSION as MATERIALS_VERSION
    from runtime.learning_assessment import VERSION as ASSESSMENT_VERSION
    from runtime.learning_teaching import VERSION as TEACHING_VERSION
    from runtime.learning_teaching_b4 import VERSION as SPECIALIZED_TEACHING_VERSION
    from runtime.learning_planning import VERSION as PLANNING_VERSION
    from runtime.learning_strategies import VERSION as STRATEGIES_VERSION
    manifest = json.loads((ROOT / "resources/strategies/manifest.json").read_text(encoding="utf-8-sig"))
    report = {
        "batch": "B7", "scope": args.scope,
        "client_date": "2026-10-04", "client_timezone": "Asia/Shanghai", "synthetic_only": True,
        "versions": {"shared": SCHEMA_VERSION, "store": STORE_VERSION, "pilot": PILOT_VERSION,
            "network": NETWORK_VERSION,
            "professional_services": {"entry": ENTRY_VERSION, "goals_input": GOAL_VERSION,
                "materials": MATERIALS_VERSION, "assessment": ASSESSMENT_VERSION,
                "teaching_core": TEACHING_VERSION, "teaching_specialized": SPECIALIZED_TEACHING_VERSION,
                "planning": PLANNING_VERSION, "strategies": STRATEGIES_VERSION},
            "strategy_resources": manifest["resource_revision"]},
        "executor": "scripts/check_b7.py; Python unittest",
        "checker": "Independent B7 pilot test author; root reviews actual results",
        "host_versions": {"python": platform.python_version(),
            "python_implementation": platform.python_implementation(), "platform": platform.platform(),
            "sqlite": sqlite3.sqlite_version},
        "status": "passed" if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else "failed",
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "cases": result.cases, "raw_output_path": str(raw),
        "real_validation": {layer: "not_executed" for layer in ("V1", "V2", "V3", "V4")},
        "limitations": [
            "All test inputs, reviewer findings, responses, costs, identities and grants are explicitly fictional.",
            "In-memory real-mode boundary probes are artificial declarations, never a real learner dataset or proof of authentic provenance.",
            "Software contract checks establish conservative configuration and report behavior, not real V1–V4 or learning efficacy.",
            "The pilot service does not persist records, conduct learning, adopt findings, bind real identities or enable an execution channel.",
            "Reports and input files held by callers remain outside managed SQLite deletion scope.",
            "No benefit from additional roles, independent samples or same-content repetition is inferred from these checks."]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B7 {args.scope}: {report['status']}; {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped.")
    print(f"Report: {path}")
    print(f"Test output: {raw}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
