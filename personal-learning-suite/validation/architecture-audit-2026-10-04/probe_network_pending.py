"""Reproduce a B6 pending-visibility omission using temporary synthetic records.

This read-only audit of the implementation creates and removes an isolated
fictional workspace. It does not edit runtime code or the existing tests.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SUITE = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(SUITE / "src"), str(SUITE / "tests")]

from test_b6_network import B6NetworkTests


def probe():
    case = B6NetworkTests(
        "test_candidate_result_and_professional_adoption_are_distinct_and_cannot_be_forged"
    )
    case.setUp()
    try:
        order = case.accepted(case.dispatch())
        first = case.host.run(
            case.roles["AG2"],
            case.mutation(
                "audit-run-z", order_ref=order,
                result_id="FIX-z-old-adopted-result",
            ),
        )
        adopted = case.adoption(first["result_ref"])
        second = case.host.run(
            case.roles["AG2"],
            case.mutation(
                "audit-run-a", order_ref=order,
                result_id="FIX-a-new-candidate-result",
            ),
        )
        pending = case.host.pending(case.roles["AG0"])
        current = case.record(second["result_ref"]["id"])
        return {
            "audit": "B6 current candidate omitted from pending",
            "client_date": "2026-10-04",
            "client_timezone": "Asia/Shanghai",
            "synthetic_only": True,
            "workspace": "TemporaryDirectory; removed after probe",
            "order_ref": order,
            "first_run": first,
            "first_adoption": adopted,
            "second_run": second,
            "second_candidate_adoption": current["adoption"],
            "pending": pending,
            "omission_reproduced": (
                first["status"] == adopted["status"] == second["status"] == "committed"
                and current["adoption"]["status"] == "candidate"
                and not any(
                    item["order_ref"]["id"] == order["id"]
                    for item in pending.get("pending", [])
                )
            ),
            "explanation": (
                "pending collapses multiple WorkResults by order id; read_context "
                "orders records by id, so FIX-z-old-adopted-result wins over the "
                "later FIX-a-new-candidate-result and hides its pending adoption."
            ),
        }
    finally:
        case.doCleanups()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = probe()
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["omission_reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
