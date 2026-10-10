"""Check B6 or the complete fictional suite without rewriting older reports."""
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
    parser.add_argument("--scope", choices=["network", "all"], default="network")
    parser.add_argument("--report")
    parser.add_argument("--output")
    args = parser.parse_args()
    pattern = "test_*.py" if args.scope == "all" else "test_b6_network.py"
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=pattern)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CaseResult).run(tests)
    raw = output_path(args.output or f"validation/b6-{args.scope}-runtime-output.txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(stream.getvalue(), encoding="utf-8")
    from runtime.learning_store import SCHEMA_VERSION, STORE_VERSION
    from runtime.network_b6 import VERSION as NETWORK_VERSION
    from runtime.entry_b5 import VERSION as ENTRY_VERSION
    from runtime.learning_goals import INPUT_VERSION as GOAL_VERSION
    from runtime.learning_materials import VERSION as MATERIALS_VERSION
    from runtime.learning_assessment import VERSION as ASSESSMENT_VERSION
    from runtime.learning_teaching import VERSION as TEACHING_VERSION
    from runtime.learning_teaching_b4 import VERSION as SPECIALIZED_TEACHING_VERSION
    from runtime.learning_planning import VERSION as PLANNING_VERSION
    from runtime.learning_strategies import VERSION as STRATEGIES_VERSION
    resource_manifest = json.loads((ROOT / "resources/strategies/manifest.json").read_text(encoding="utf-8-sig"))
    report = {"batch": "B6", "scope": args.scope,
        "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "synthetic_only": True,
        "versions": {"shared": SCHEMA_VERSION, "store": STORE_VERSION, "network": NETWORK_VERSION,
            "professional_services": {"entry": ENTRY_VERSION, "goals_input": GOAL_VERSION,
                "materials": MATERIALS_VERSION, "assessment": ASSESSMENT_VERSION,
                "teaching_core": TEACHING_VERSION, "teaching_specialized": SPECIALIZED_TEACHING_VERSION,
                "planning": PLANNING_VERSION, "strategies": STRATEGIES_VERSION},
            "strategy_resources": resource_manifest["resource_revision"]},
        "executor": "scripts/check_b6.py; Python unittest",
        "checker": "Independent B6 network test author; root reviews actual results",
        "host_versions": {"python": platform.python_version(), "platform": platform.platform(),
            "sqlite": sqlite3.sqlite_version},
        "status": "passed" if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else "failed",
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "cases": result.cases, "raw_output_path": str(raw),
        "limitations": [
            "All inputs, findings, original responses, costs, exposure and grants are explicitly fictional.",
            "Host authority is verified only for this managed in-process serial adapter; arbitrary callers with filesystem or Python process access remain outside its boundary.",
            "Background agents, parallel learner displays, distributed hosts and crash-recovery leases are not enabled or validated.",
            "OS workspace lock checks establish cooperative local exclusion, not protection from direct SQLite or filesystem access.",
            "No learning efficacy or benefit from four roles is established by these software behavior checks.",
            "External requests, stdout and reports remain outside managed store deletion scope."]}
    path = output_path(args.report or f"validation/b6-{args.scope}-runtime-report.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B6 {args.scope}: {report['status']}; {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped.")
    print(f"Report: {path}")
    print(f"Test output: {raw}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
