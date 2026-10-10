"""Run four fictional serial role handoffs once; reopen existing workspaces read-only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from runtime.learning_store import LearningStore
from runtime.network_b6 import NetworkHost, VERSION
from test_b5_entry import fixture, teach
from test_b6_network import ACTIVITY, BASIS, packet, role_review_orders


def metadata(result):
    """Reports hold stage/ref metadata; professional text remains in the store."""
    allowed = {"status", "state_revision", "order_ref", "result_ref", "professional_status",
        "ready", "acceptance", "responsible_owner", "authorization_ready", "control_ref"}
    selected = {key: result[key] for key in allowed if key in result}
    if "execution" in result:
        execution = result["execution"]
        selected["execution"] = {key: execution[key] for key in
            ("activity_ref", "execution_epoch", "status") if key in execution}
    if "adoption" in result:
        selected["adoption"] = {key: result["adoption"][key] for key in ("status", "by") if key in result["adoption"]}
    if result.get("reasons"):
        selected["reason_codes"] = [reason.get("code", "unknown") for reason in result["reasons"]]
    return selected


def execute_demo(store, context, judgment, assessment_context):
    steps, failures, pending_roles = [], [], []
    sequence = 0

    def request(name, **fields):
        nonlocal sequence
        sequence += 1
        return packet(store.read_context()["state_revision"], "FIX-b6-demo-" + name + "-" + str(sequence), **fields)

    with NetworkHost(store) as host:
        roles = {role: host.bind(role) for role in ("AG0", "AG1", "AG2", "AG3")}
        bindings = []
        for role, cap in roles.items():
            info = host.role_info(cap)
            bindings.append({"role": role, "status": info["status"], "loaded_rule_files": len(info["instructions"]),
                "capabilities": info["capabilities"]})
        claim = host.takeover(roles["AG0"], request("claim", activity_ref=ACTIVITY, basis_refs=BASIS))
        steps.append({"stage": "execution_claim", "result": metadata(claim)})
        if claim.get("status") != "committed":
            return {"status": "failed", "bindings": bindings, "steps": steps}
        objects = {o["id"]: o for o in store.read_context()["objects"]}
        for definition in role_review_orders(objects, context, judgment, assessment_context):
            role = definition["assignee"]
            stages = []
            dispatched = host.dispatch(roles["AG0"], request("dispatch-" + role, **definition))
            stages.append({"stage": "proposed", "result": metadata(dispatched)})
            if dispatched.get("status") == "committed":
                received = host.accept(roles[role], packet(order_ref=dispatched["order_ref"], status="received",
                    handled_scope=[], unhandled_scope=[], limitations=[]))
                stages.append({"stage": "received_only", "result": metadata(received)})
                accepted = host.accept(roles[role], request("accept-" + role, order_ref=dispatched["order_ref"],
                    status="accepted", handled_scope=definition["scope"], unhandled_scope=[], limitations=[]))
                stages.append({"stage": "responsibility_accepted", "result": metadata(accepted)})
                if accepted.get("status") == "committed":
                    result = host.run(roles[role], request("run-" + role, order_ref=accepted["order_ref"],
                        result_id="FIX-b6-demo-result-" + role))
                    stages.append({"stage": "candidate_returned", "result": metadata(result)})
                    if result.get("status") == "committed":
                        saved = next(o for o in store.read_context()["objects"] if o["id"] == result["result_ref"]["id"])
                        adoption_status = "adopted" if saved["metadata"]["network"]["professional_successful"] else "recheck"
                        if adoption_status == "recheck":
                            pending_roles.append(role)
                        adopted = host.adopt(roles[role], request("adopt-" + role, result_ref=result["result_ref"],
                            status=adoption_status, basis_refs=definition["context_refs"], handled_scope=saved["handled_scope"],
                            unhandled_scope=saved["unhandled_scope"], limitations=["Explicit fictional professional declaration only."],
                            next_trigger="Recheck when the relevant basis or intended use changes."))
                        stages.append({"stage": "professionally_adopted" if adoption_status == "adopted" else "professional_recheck_recorded", "result": metadata(adopted)})
            succeeded = stages[-1]["stage"] in {"professionally_adopted", "professional_recheck_recorded"} and stages[-1]["result"]["status"] == "committed"
            if not succeeded:
                failures.append(role)
            steps.append({"role": role, "stages": stages})
        replacement = host.bind("AG0")
        takeover = host.takeover(replacement, request("takeover", activity_ref=ACTIVITY, basis_refs=BASIS,
            expected_epoch=claim["execution"]["execution_epoch"]))
        presentation = packet(activity_ref=ACTIVITY, execution_epoch=claim["execution"]["execution_epoch"],
            basis_refs=BASIS, professional_request=teach("open", context))
        old_display = host.present(roles["AG0"], presentation)
        current_display = {"status": "not_executed"}
        if takeover.get("status") == "committed":
            presentation["execution_epoch"] = takeover["execution"]["execution_epoch"]
            current_display = host.present(replacement, presentation)
        steps.append({"stage": "takeover", "result": metadata(takeover),
            "old_executor_presentation": metadata(old_display), "current_executor_presentation": metadata(current_display)})
        success = not failures and takeover.get("status") == "committed" and old_display.get("status") == "rejected" and current_display.get("status") == "ready"
        return {"status": "completed" if success else "failed", "bindings": bindings, "steps": steps,
            "failed_roles": failures, "pending_professional_roles": pending_roles,
            "background_delegation": False, "parallel_presentation": False}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--report", default="validation/b6-demo-report.json")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    existed = (workspace / "records.sqlite3").exists()
    store = LearningStore(workspace, entry_actor="AG0")
    initialization, execution = [], None
    if not existed:
        snapshot, artifacts, context, judgment, assessment_context = fixture()
        initialization.append(metadata(store.init_workspace()))
        if initialization[-1]["status"] == "committed":
            initialization.append(metadata(store.import_fixture(snapshot, artifacts)))
        if len(initialization) == 2 and initialization[-1]["status"] == "committed":
            execution = execute_demo(store, context, judgment, assessment_context)
    before = store.read_context()
    integrity = store.check_integrity()
    # Reopening does not import, execute, claim an epoch, or adopt a prior result.
    reopened = LearningStore(workspace, entry_actor="AG0")
    recovery = reopened.read_context()
    unchanged = recovery == before
    refs = [{"id": o["id"], "revision": o["revision"], "type": o["type"]}
        for o in recovery.get("objects", []) if o["id"].startswith("FIX-b6-") or o["id"].startswith("FIX-network-execution-")]
    completed = execution is None if existed else execution is not None and execution["status"] == "completed"
    report = {"batch": "B6", "network_version": VERSION, "client_date": "2026-10-03",
        "client_timezone": "Asia/Shanghai", "synthetic_only": True, "workspace": str(workspace),
        "existing_workspace": existed, "initialization": initialization, "execution": execution,
        "recovery": {"status": recovery.get("status"), "state_revision": recovery.get("state_revision"), "object_refs": refs},
        "integrity": {"status": integrity.get("status")}, "reopen_read_only": unchanged,
        "state_revision": recovery.get("state_revision"),
        "limitations": ["Synthetic fixture declarations only; no real learner, correctness review or learning efficacy is established.",
            "Four roles use one cooperating local serial host with opaque in-process capabilities; distributed or background execution is disabled.",
            "Existing workspaces are never reseeded, replayed, professionally adopted or assigned a new execution epoch by this demo.",
            "External reports and request copies are beyond managed store deletion scope."]}
    path = Path(args.report)
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    execution_label = execution["status"] if execution else "existing workspace read-only" if existed else "not executed"
    print(f"B6: revision {report['state_revision']}; execution {execution_label}; integrity {integrity.get('status')}; reopen read-only {unchanged}.")
    return 0 if completed and integrity.get("status") == "ok" and unchanged and recovery.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
