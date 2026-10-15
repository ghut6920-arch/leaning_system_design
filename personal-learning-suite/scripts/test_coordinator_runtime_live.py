"""One tiny synthetic integration: CLI professionals and the original desktop AG0.

Run only with explicit user authorization. The original AG0 must finish its turn;
this program waits without a model and delivers its decision/report work later.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
from coordinator.agent_api import AgentCoordinator
from coordinator.complete import TaskArtifactCoordinator
from coordinator.hosts import CLIResumeHost, DesktopMCPHost
from coordinator.runtime_scheduler import RuntimeScheduler
from coordinator.runtime_store import RuntimeStore
from coordinator.workspace import GateError, encode, sha


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def prepare(root, authorization_ref):
    if root.exists():
        raise GateError("use_new_live_test_directory")
    if not root.is_relative_to((SUITE.parent / "maintenance").resolve()):
        raise GateError("live_test_isolation_directory_required")
    thread_id = os.environ.get("CODEX_THREAD_ID")
    if not thread_id or not authorization_ref.strip():
        raise GateError("actual_thread_and_authorization_required")
    c = TaskArtifactCoordinator(root)
    c.initialize(evidence_kind="synthetic_demo")
    session = c.bind_local_operator("AG0")
    api = AgentCoordinator(c)
    store = RuntimeStore(c)
    store.migrate(session)
    nonce = "runtime-" + uuid.uuid4().hex[:12]
    for task, output, kind, role, review, inputs in [
        ("material", "tiny-note", "MaterialUse", "AG2", True, []),
        ("summary", "tiny-summary", "ActivitySpec", "AG1", False, [{"artifact": "tiny-note", "after_task": "material", "scope": ["demo"], "use": "teaching"}])]:
        intent = {"action": "assign", "task": task, "output": {"id": output, "type": kind}, "to": role, "scope": ["demo"], "use": "teaching", "review_required": review, "inputs": inputs, "wait_ms": 600000}
        receipt = api.do(session, intent, request_key="live-setup:" + task)
        if receipt["status"] != "committed":
            raise GateError(receipt.get("problem", "live_task_setup_failed"))
    for role in ("AG0", "AG1", "AG2", "AG3"):
        store.bind(session, {"id": role, "role": role, "host_kind": "desktop" if role == "AG0" else "cli", "thread_id": thread_id if role == "AG0" else None, "host_id": "local", "cwd": str(root), "authorization_ref": authorization_ref, "authorized": True})
    deadline = c.clock_ms() + 900000
    common = {"use": "teaching", "deadline_ms": deadline, "run_timeout_ms": 240000}
    plan = {"id": "live-integration", "revision": 1, "authorization_ref": authorization_ref, "nodes": [
        {**common, "id": "research", "binding": "AG2", "task": "material", "allowed_tasks": ["material"], "manage_tasks": ["material"], "allowed_actions": ["start", "submit", "confirm"], "conditions": [], "completion": "business", "required_intents": ["deliver", "opinion"], "expected_output_contains": ["blue", nonce],
         "prompt": f"Tiny fictional test, no real learning records. Produce exactly one sentence containing blue and {nonce}. Return explicit intents deliver(task='material',path='$output') then opinion(task='material',outcome='supported',rationale='I checked this tiny fictional note; it contains the supplied color and nonce.'). No tools are needed; keep output short."},
        {**common, "id": "review", "binding": "AG3", "task": "review", "allowed_tasks": ["review", "material"], "manage_tasks": ["review"], "allowed_actions": ["register", "start", "review"], "setup_intents": [{"action": "assign_review", "task": "review", "from_task": "material"}], "conditions": [{"kind": "submitted", "task": "material"}], "completion": "business", "required_intents": ["opinion"],
         "prompt": f"Independently inspect the supplied exact tiny-note v1. Check blue and {nonce} are in its text. Return a short output and one explicit opinion intent for task review: supported if both are present, rejected otherwise, with your actual rationale. Do not invent an author opinion. No tools are needed."},
        {**common, "id": "adopt", "binding": "AG0", "allowed_tasks": ["material"], "allowed_actions": ["adopt"], "conditions": [{"kind": "adoption_ready", "task": "material"}], "completion": "business", "required_intents": ["adopt"], "result_via_file": True,
         "prompt": "Continue the user's authorized coordinator implementation and its tiny isolated integration test. Your first action must receive this dispatch. Inspect the exact note and the real author/reviewer opinions in decision_basis. Make the adoption decision; if supported, save result with intents=[{action:'adopt',tasks:['material']}]. Use the result command to persist JSON, then give a brief normal final stating this same-chat adoption step completed and Python will continue AG1 and later wake this same chat for the final implementation report. End this turn without waiting. No learning records outside this isolation directory are involved."},
        {**common, "id": "design", "binding": "AG1", "task": "summary", "allowed_tasks": ["summary"], "manage_tasks": ["summary"], "allowed_actions": ["start", "submit"], "conditions": [{"kind": "adopted", "task": "material"}], "completion": "business", "required_intents": ["deliver"], "expected_output_contains": ["blue", nonce],
         "prompt": "Read the exact adopted note in task_snapshot. Produce a single short summary preserving its blue color and nonce verbatim. Return one deliver intent task summary path '$output'. No tools are needed."},
        {**common, "id": "report", "binding": "AG0", "allowed_tasks": ["material", "summary"], "allowed_actions": ["adopt"], "conditions": [{"kind": "work_done", "node": "design"}, {"kind": "adopted", "task": "material"}, {"kind": "submitted", "task": "summary"}], "completion": "result", "result_via_file": True,
         "prompt": f"The original user's implementation request is still active. Receive this dispatch first, inspect {root / 'live-report.json'} and maintenance/coordinator-runtime-20261015/实施记录.md under repository {SUITE.parent}. All actual test results are in this isolation directory. Save a result with intents=[] via the result command; no further business operation is required. Then give the user a concise final implementation report in Chinese, naming completed implementation, test counts, original AG0 same-thread integration success, and the remaining app-restart boundary. Link the implementation record and live report. End the turn; do not arrange any further wakeups."}
    ]}
    save(root / "plan.json", plan)
    store.register_plan(session, plan)
    store.reconcile(session)
    contract = {"thread_id": thread_id, "nonce": nonce, "authorization_ref": authorization_ref, "workflow_id": plan["id"], "prepared_at_ms": c.clock_ms(), "synthetic_only": True}
    save(root / "verification-contract.json", contract)
    return c, contract


def run(root, *, max_seconds=840):
    contract = json.loads((root / "verification-contract.json").read_text(encoding="utf-8"))
    if os.environ.get("CODEX_THREAD_ID") != contract["thread_id"]:
        raise GateError("live_caller_thread_mismatch")
    c = TaskArtifactCoordinator(root)
    store = RuntimeStore(c)
    hosts = {"cli": CLIResumeHost(c.meta_root / "host-runs"), "desktop": DesktopMCPHost(c.meta_root / "host-runs")}
    ag0 = store.lookup("runtime_bindings", "AG0")
    before = hosts["desktop"].inspect(ag0)
    if before["state"] not in {"active", "idle"}:
        raise GateError("desktop_access_unavailable")
    report = {"success": False, "status": "waiting_for_original_turn_end", "original_thread_id": contract["thread_id"], "before_turn_id": before.get("last_turn_id"), "synthetic_only": True, "started_at_ms": c.clock_ms()}
    save(root / "live-report.json", report)
    save(root / "ready.json", {"status": "ready", "pid": os.getpid(), "original_thread_id": contract["thread_id"], "waiting_in_python": True})
    started = time.monotonic()
    while time.monotonic() - started < 180:
        if hosts["desktop"].inspect(ag0)["state"] == "idle":
            report["original_idle_at_ms"] = c.clock_ms()
            break
        time.sleep(1)
    else:
        raise GateError("original_turn_did_not_end_no_message_sent")
    scheduler = RuntimeScheduler(c, hosts)
    scheduler.start()
    try:
        while time.monotonic() - started < max_seconds:
            scheduler.tick()
            status = store.status()
            report.update(status="running", work_states={w.get("node", {}).get("id", w["id"]): w["state"] for w in status["works"]}, works=status["works"], dispatches=scheduler.dispatch_count, updated_at_ms=c.clock_ms())
            with c.connect() as db:
                report["attempts"] = [json.loads(r[0]) for r in db.execute("SELECT body FROM runtime_attempts")]
                adopted = db.execute("SELECT revision FROM adopted WHERE id='tiny-note' AND intended_use='teaching' AND scope='demo'").fetchone()
                report["adopted_note_revision"] = adopted[0] if adopted else None
                summary = c.get(db, "tasks", "summary")
                report["summary_ref"] = summary.get("result_ref")
                if summary.get("result_ref"):
                    artifact = c.artifact(db, summary["result_ref"])
                    report["summary_sha256"] = artifact["sha256"]
                    report["summary_text"] = (root / artifact["path"]).read_text(encoding="utf-8")
            report["core_chain_success"] = report["adopted_note_revision"] == 1 and bool(report.get("summary_ref")) and contract["nonce"] in report.get("summary_text", "") and "blue" in report.get("summary_text", "")
            save(root / "live-report.json", report)
            if all(w["state"] == "done" for w in status["works"]):
                report.update(success=report["core_chain_success"], status="completed", completed_at_ms=c.clock_ms())
                break
            if any(w["state"] in {"failed", "needs_user"} for w in status["works"]):
                report.update(status="needs_attention")
                break
            time.sleep(1)
        else:
            report.update(status="timeout_without_blind_retry")
    except Exception as error:
        report.update(status="failed", problem=getattr(error, "code", type(error).__name__))
        raise
    finally:
        save(root / "live-report.json", report)
        store.release_supervisor(scheduler.instance_id)
        for host in hosts.values():
            host.close()
    return report


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--authorization-ref")
    args = parser.parse_args()
    root = args.run_dir.resolve()
    try:
        if args.prepare_only:
            if not args.authorization_ref:
                raise GateError("explicit_live_test_authorization_required")
            _, result = prepare(root, args.authorization_ref)
        else:
            result = run(root)
    except (GateError, OSError, ValueError) as error:
        result = {"success": False, "problem": getattr(error, "code", type(error).__name__)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if args.prepare_only and "workflow_id" in result or result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
