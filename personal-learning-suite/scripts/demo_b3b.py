"""Save a synthetic C0 trace once; existing workspaces are inspected read-only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from runtime.learning_materials import fact, ref
from runtime.learning_store import LearningStore
from runtime.learning_teaching import TeachingService
from test_b3b_teaching import (
    EVENT_ID, GRANT_ID, INITIAL_PATH, REVISION_PATH, REVISION_TEXT,
    anchor, fixture, initial_request,
)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--report", default="validation/b3b-demo-report.json")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    existed = (workspace / "records.sqlite3").exists()
    store = LearningStore(workspace, entry_actor="AG0")
    snapshot, artifacts, context = fixture()
    service = TeachingService(store)
    receipts = []
    if not existed:
        receipts.append(store.init_workspace())
        if receipts[-1]["status"] == "committed":
            receipts.append(store.import_fixture(snapshot, artifacts))
        if receipts[-1]["status"] != "committed":
            print(json.dumps(receipts[-1], ensure_ascii=False, indent=2))
            return 1
        receipts.append(service.run(initial_request(store.read_context()["state_revision"], "FIX-b3b-demo-initial")))
        if receipts[-1]["status"] != "committed":
            print(json.dumps(receipts[-1], ensure_ascii=False, indent=2))
            return 1

        def request(action, **fields):
            state = store.read_context()
            event = next(obj for obj in state["objects"] if obj["id"] == EVENT_ID)
            return dict(
                synthetic_only=True, action=action, context=context,
                activity_ref={"id": "FIX-activity", "revision": 1}, event_ref=ref(event),
                authorization_refs=[{"id": GRANT_ID, "revision": 1}],
                expected_state_revision=state["state_revision"], operation_id="FIX-b3b-demo-" + action,
                **fields,
            )

        actions = [
            ("record_feedback", {
                "branch_index": 0,
                "observation": {"artifact_ref": anchor(INITIAL_PATH, "B3b-initial"), "quote": "Q。"},
                "feedback": {
                    "content": "原答写出了 Q，请将给定前提连接写成理由。", "visibility": "displayed",
                    "target_operations": ["connect-P-to-Q"], "substituted_operations": [],
                    "time": fact("unknown", "人工演示顺序，无真实展示时间"),
                },
            }),
            ("record_help", {"help": {
                "content": "前提 P 使 P→Q 可推出 Q。", "visibility": "displayed",
                "target_operations": ["connect-P-to-Q"], "substituted_operations": ["connect-P-to-Q"],
                "time": fact("unknown", "人工演示顺序，无真实展示时间"),
            }}),
            ("record_revision", {
                "revision_response": anchor(REVISION_PATH, "B3b-revision"),
                "artifacts": {REVISION_PATH: REVISION_TEXT},
                "revision": {
                    "content": "P 成立且 P→Q，所以 Q。", "visibility": "displayed",
                    "target_operations": ["connect-P-to-Q"], "substituted_operations": [],
                    "time": fact("unknown", "人工演示顺序，无真实作答时间"),
                },
            }),
            ("close", {
                "checkpoint_id": "FIX-b3b-demo-checkpoint", "stop_reason": "当前局部支持够用，保留父任务整体未完成",
                "next_connection": "返回同一父产物的第二步连接", "pending_owners": ["AG3", "AG1"],
                "unrecorded_actions": fact("unknown", "演示之外的动作不推断"),
                "unfinished_requirement_ids": ["infer-Q"],
                "closure": {"status": "local_sufficient", "reason": "活动收束，不判断目标达成"},
                "existing_need_ref": {"id": "FIX-need", "revision": 1},
            }),
        ]
        for action, fields in actions:
            receipts.append(service.run(request(action, **fields)))
            if receipts[-1]["status"] != "committed":
                print(json.dumps(receipts[-1], ensure_ascii=False, indent=2))
                return 1

    reopened = LearningStore(workspace, entry_actor="AG0")
    state = reopened.read_context()
    event = next((obj for obj in state.get("objects", []) if obj["id"] == EVENT_ID), None)
    resume = TeachingService(reopened).run({
        "synthetic_only": True, "action": "resume", "context": context,
        "activity_ref": {"id": "FIX-activity", "revision": 1},
        "authorization_refs": [{"id": GRANT_ID, "revision": 1}],
        "event_ref": ref(event) if event else None,
    }) if event else {"status": "unavailable", "reason": "Absent or deleted records are never reimported."}
    integrity = reopened.check_integrity()
    report = {
        "batch": "B3b", "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "synthetic_only": True, "workspace": str(workspace), "existing_workspace": existed,
        "write_receipts": receipts, "state_revision": state.get("state_revision"),
        "object_count": len(state.get("objects", [])), "event_ref": ref(event) if event else None,
        "sample_id": event.get("independent_sample_id") if event else None,
        "timeline_kinds": [entry["kind"] for entry in event.get("timeline", [])] if event else [],
        "resume": resume, "integrity": integrity, "scoring": "not_executed", "plan_changed": False,
        "limitations": [
            "All original answers and displayed actions are explicit synthetic declarations.",
            "Local sufficiency does not establish independent performance or the complete parent goal.",
            "Existing spaces are read-only; missing/deleted records are not recreated.",
            "This saved report is outside managed SQLite deletion scope.",
        ],
    }
    path = Path(args.report)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B3b synthetic demonstration: {workspace}")
    print(f"Reopened state: {report['state_revision']}; event revision: {event['revision'] if event else 'absent'}; resume: {resume['status']}; integrity: {integrity['status']}.")
    return 0 if integrity["status"] == "ok" and resume["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
