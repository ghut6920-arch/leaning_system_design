"""Save a synthetic shared plan and a permitted shrink; reopen read-only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from runtime.learning_store import LearningStore
from runtime.learning_planning import PlanningService, ref
from test_b4_planning import fixture, request, decision, PLAN, DUPLICATE, ADJUST


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--report", default="validation/b4-planning-demo-report.json")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    store = LearningStore(workspace, entry_actor="AG1")
    existed = (workspace / "records.sqlite3").exists()
    receipts = []
    if not existed:
        snapshot, artifacts = fixture()
        receipts.extend([store.init_workspace(), store.import_fixture(snapshot, artifacts)])
        combined = request(decisions=[decision(), decision(DUPLICATE, status="merged")],
            alternatives=[{"scope": "两个来源分别安排", "consequence": "重复同一连接，不增加独立样本"}])
        receipts.append(PlanningService(store).run(combined))
        if receipts[-1]["status"] != "committed":
            print(json.dumps(receipts[-1], ensure_ascii=False, indent=2))
            return 1
        state = store.read_context()
        shrink = request(state["state_revision"], "FIX-b4-demo-shrink", action="shrink", available_minutes=3,
            commitment_ref={"id": PLAN, "revision": 1}, authorization_refs=[{"id": ADJUST, "revision": 1}],
            decisions=[decision(revision=2, status="partially_scheduled", minutes=3)],
            alternatives=[{"scope": "原五分钟范围", "consequence": "三分钟保留反馈收束，未覆盖要求仍未知"}])
        receipts.append(PlanningService(LearningStore(workspace, entry_actor="AG0")).run(shrink))
        if receipts[-1]["status"] != "committed":
            print(json.dumps(receipts[-1], ensure_ascii=False, indent=2))
            return 1
    reopened = LearningStore(workspace, entry_actor="AG1")
    before = reopened.read_context()
    objects = {o["id"]: o for o in before.get("objects", [])}
    plan = objects.get(PLAN)
    resume = PlanningService(reopened).resume(ref(plan)) if plan else {"status": "unavailable"}
    integrity = reopened.check_integrity()
    unchanged = reopened.read_context().get("state_revision") == before.get("state_revision")
    report = {"batch": "B4-planning", "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "synthetic_only": True, "workspace": str(workspace), "existing_workspace": existed,
        "receipts": receipts, "state_revision": before.get("state_revision"), "commitment_ref": ref(plan) if plan else None,
        "needs": {key: {"ref": ref(objects[key]), "disposition": objects[key]["disposition"], "uncovered_impact": objects[key]["uncovered_impact"]}
                  for key in ("FIX-need", DUPLICATE) if key in objects},
        "resume": resume, "integrity": integrity, "reopen_read_only": unchanged,
        "limitations": ["Artificial decisions, grants, costs and evidence only; not an actual learner schedule.",
            "No reminder, automatic priority choice, semantic grading or host binding.",
            "Existing stores are not reimported; external report copies are beyond store deletion scope."]}
    path = Path(args.report)
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B4 planning: revision {report['state_revision']}; resume {resume['status']}; integrity {integrity['status']}; reopen read-only {unchanged}.")
    return 0 if resume["status"] == "ready" and integrity["status"] == "ok" and unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
