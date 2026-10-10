"""Save one artificial B3a judgment; never reseed an existing workspace."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from runtime.learning_assessment import AssessmentService, ref
from runtime.learning_store import LearningStore
from test_b3a_assessment import fixture


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--report", default="validation/b3a-demo-report.json")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    existed = (workspace / "records.sqlite3").exists()
    store = LearningStore(workspace, entry_actor="AG3")
    service = AssessmentService(store)
    snapshot, artifacts, judgment, context, _note, _diagnostic_context = fixture()
    seed = {"status": "not_executed", "reason": "An existing workspace is never reseeded."}
    saved = {"status": "not_executed", "reason": "An existing workspace is read-only in this demonstration."}
    if not existed:
        initialized = store.init_workspace()
        if initialized["status"] != "committed":
            print(json.dumps(initialized, ensure_ascii=False, indent=2))
            return 1
        seed = store.import_fixture(snapshot, artifacts)
        if seed["status"] != "committed":
            print(json.dumps(seed, ensure_ascii=False, indent=2))
            return 1
        candidate = copy.deepcopy(judgment)
        candidate["id"] = "FIX-b3a-demo-judgment"
        grant_ref = candidate["authorization_ref"]
        saved = service.submit_assessment({
            "expected_state_revision": seed["state_revision"], "operation_id": "FIX-b3a-demo-save",
            "changes": [candidate], "authorization_refs": [grant_ref], "adoption_refs": [grant_ref],
            "contexts": {candidate["id"]: context},
        })
        if saved["status"] != "committed":
            print(json.dumps(saved, ensure_ascii=False, indent=2))
            return 1
    reopened = LearningStore(workspace, entry_actor="AG3")
    state = reopened.read_context()
    current = next((obj for obj in state.get("objects", []) if obj["id"] == "FIX-b3a-demo-judgment"), None)
    inspected = AssessmentService(reopened).inspect_judgment(current, context) if current else {
        "status": "unavailable", "reason": "The earlier judgment is absent or controlled; it is not regenerated."}
    integrity = reopened.check_integrity()
    report = {
        "batch": "B3a", "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai", "synthetic_only": True,
        "workspace": str(workspace), "existing_workspace": existed, "seed_receipt": seed, "save_receipt": saved,
        "state_revision": state.get("state_revision"), "object_count": len(state.get("objects", [])),
        "judgment_ref": ref(current) if current else None, "inspection": inspected, "integrity": integrity,
        "teaching": False, "new_performance_created": False, "new_learning_need_created": False,
        "plan_changed": False, "professional_restrictions_lifted": False,
        "limitations": [
            "Artificial professional findings are inputs; compatible does not prove answer truth or learning efficacy.",
            "The saved judgment remains candidate; inspection does not automatically adopt or schedule it.",
            "Existing spaces are read-only; absent or deleted records are never reimported.",
            "This report is a caller copy outside the store deletion scope.",
        ],
    }
    path = Path(args.report)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B3a synthetic demonstration: {workspace}")
    print(f"Reopened state revision: {report['state_revision']}; objects: {report['object_count']}; inspection: {inspected['status']}; integrity: {integrity['status']}.")
    return 0 if integrity["status"] == "ok" and inspected["status"] == "compatible" else 1


if __name__ == "__main__":
    raise SystemExit(main())
