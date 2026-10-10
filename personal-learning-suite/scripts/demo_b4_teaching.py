"""Save one artificial Post/Encoding/return trace; existing stores stay read-only."""
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
from runtime.learning_teaching_b4 import SpecializedTeachingService
from test_b4_teaching import (
    EVENT_ID, GRANT_ID, SAMPLE_ID, SUPPLIED_PATH, SUPPLIED_TEXT, LOCAL_PATH, LOCAL_TEXT,
    anchor, fixture, initial_request,
)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--report", default="validation/b4-teaching-demo-report.json")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    existed = (workspace / "records.sqlite3").exists()
    store = LearningStore(workspace, entry_actor="AG0")
    snapshot, artifacts, context = fixture()
    service = SpecializedTeachingService(store)
    receipts = []
    middle_recovery = None

    def state():
        return store.read_context()

    def event():
        return next((obj for obj in state().get("objects", []) if obj["id"] == EVENT_ID), None)

    def request(action, **fields):
        return dict(
            synthetic_only=True, action=action, context=context,
            activity_ref={"id": "FIX-activity", "revision": 1}, event_ref=ref(event()),
            authorization_refs=[{"id": GRANT_ID, "revision": 1}],
            expected_state_revision=state()["state_revision"], operation_id="FIX-b4-demo-" + action,
            **fields,
        )

    def save(result):
        receipts.append(result)
        if result.get("status") != "committed":
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return False
        return True

    def revision(path, text, locator):
        return {
            "revision_response": anchor(path, locator), "artifacts": {path: text},
            "revision": {"content": text.splitlines()[-1], "visibility": "displayed",
                "target_operations": ["connect-P-to-Q"], "substituted_operations": [],
                "time": fact("unknown", "人工演示顺序，无真实响应时间")},
        }

    connection = "返回同一父产物的当前连接，保留整体未完成"
    if not existed:
        if not save(store.init_workspace()) or not save(store.import_fixture(snapshot, artifacts)):
            return 1
        if not save(service.run(initial_request(state()["state_revision"], "FIX-b4-demo-initial"))):
            return 1
        if not save(service.run(request("record_help", help={
            "content": "人工支持：P 与 P→Q 已明确给定。", "visibility": "displayed",
            "target_operations": ["connect-P-to-Q"], "substituted_operations": [],
            "time": fact("unknown", "人工演示顺序，无真实展示时间"),
        }))):
            return 1
        if not save(service.run(request("record_revision", **revision(SUPPLIED_PATH, SUPPLIED_TEXT, "B4-supplied-revision")))):
            return 1
        local = {
            "module": "encoding", "operations": ["connect-P-to-Q"],
            "reason": "供给前提后本人工修订仍未连接，进入有限关系工作",
            "blocker": "人工修订未写连接", "local_sufficiency": "实际使用前提写出连接理由",
            "return_connection": connection, "alternative_explanations": ["可能只省略表达", "可能尚未连接"],
            "preserved_support_refs": [{"id": "FIX-judgment", "revision": 1}],
            "observation": {"artifact_ref": anchor(SUPPLIED_PATH, "B4-supplied-revision"), "quote": "已看到前提，仍只写 Q。"},
            "premises_supplied": fact("known", value=True),
        }
        if not save(service.run(request("enter_local", local=local))):
            return 1
        checkpoint = service.run(request("checkpoint", checkpoint_id="FIX-b4-demo-middle-checkpoint",
            stop_reason="人工局部会话中断", next_connection=connection, pending_owners=["AG0", "AG1"],
            unrecorded_actions=fact("unknown", "未保存期间的动作不推断")))
        if not save(checkpoint):
            return 1
        reopened = LearningStore(workspace, entry_actor="AG0")
        middle_recovery = SpecializedTeachingService(reopened).run({
            "synthetic_only": True, "action": "resume", "context": context,
            "activity_ref": {"id": "FIX-activity", "revision": 1},
            "authorization_refs": [{"id": GRANT_ID, "revision": 1}], "checkpoint_ref": checkpoint["checkpoint_ref"],
        })
        if middle_recovery.get("status") != "ready":
            print(json.dumps(middle_recovery, ensure_ascii=False, indent=2))
            return 1
        # A distinct operation id identifies the second original artifact write.
        local_revision = request("record_revision", **revision(LOCAL_PATH, LOCAL_TEXT, "B4-local-revision"))
        local_revision["operation_id"] = "FIX-b4-demo-local-revision"
        if not save(service.run(local_revision)):
            return 1
        if not save(service.run(request("return_local", return_connection=connection,
            local_observation={"artifact_ref": anchor(LOCAL_PATH, "B4-local-revision"), "quote": "P 成立且 P→Q，所以 Q。"},
            local_outcome="sufficient", parent_outcome="still_blocked"))):
            return 1
        if not save(service.run(request("close", checkpoint_id="FIX-b4-demo-final-checkpoint",
            stop_reason="人工局部修复结束，父任务整体保留", next_connection=connection, pending_owners=["AG1", "AG3"],
            unrecorded_actions=fact("unknown", "未保存动作未知"), unfinished_requirement_ids=["infer-Q"],
            closure={"status": "local_sufficient", "reason": "帮助后局部可用，独立条件及父整体不自动通过"},
            existing_need_ref={"id": "FIX-need", "revision": 1}))):
            return 1

    reopened = LearningStore(workspace, entry_actor="AG0")
    current = reopened.read_context()
    current_event = next((obj for obj in current.get("objects", []) if obj["id"] == EVENT_ID), None)
    resume = SpecializedTeachingService(reopened).run({
        "synthetic_only": True, "action": "resume", "context": context,
        "activity_ref": {"id": "FIX-activity", "revision": 1},
        "authorization_refs": [{"id": GRANT_ID, "revision": 1}], "event_ref": ref(current_event),
    }) if current_event else {"status": "unavailable", "reason": "Missing or deleted records are never reimported."}
    integrity = reopened.check_integrity()
    specialist = current_event.get("metadata", {}).get("b4") if current_event else None
    report = {
        "batch": "B4-teaching", "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "synthetic_only": True, "workspace": str(workspace), "existing_workspace": existed,
        "write_receipts": receipts, "state_revision": current.get("state_revision"),
        "object_count": len(current.get("objects", [])), "event_ref": ref(current_event) if current_event else None,
        "sample_id": current_event.get("independent_sample_id") if current_event else None,
        "expected_synthetic_sample_id": SAMPLE_ID,
        "timeline_kinds": [entry["kind"] for entry in current_event.get("timeline", [])] if current_event else [],
        "specialization": specialist, "middle_recovery": middle_recovery,
        "resume": resume, "integrity": integrity, "scoring": "not_executed", "plan_changed": False,
        "limitations": [
            "Answers, supplied premises, observations and visibility are explicit artificial declarations.",
            "One event and one sample survive Post/Encoding/return; local success does not establish the parent goal.",
            "Existing spaces are inspected read-only; absent or deleted records are never recreated.",
            "C0 close returns any need update as a candidate; this demonstration makes no real planning or host claim.",
            "The saved report is outside managed SQLite deletion scope.",
        ],
    }
    path = Path(args.report)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B4 synthetic teaching demonstration: {workspace}")
    print(f"Reopened state: {report['state_revision']}; module: {specialist.get('module') if specialist else 'absent'}; resume: {resume['status']}; integrity: {integrity['status']}.")
    return 0 if integrity["status"] == "ok" and resume["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
