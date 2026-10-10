"""Create a clearly synthetic B2b demonstration once; existing spaces are read-only."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from runtime.learning_materials import MaterialsService, ref
from runtime.learning_store import LearningStore
from test_b2b_materials import fixture


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--report", default="validation/b2b-demo-report.json")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    existed = (workspace / "records.sqlite3").exists()
    store = LearningStore(workspace, entry_actor="AG2")
    service = MaterialsService(store)
    snapshot, artifacts, material, context = fixture()
    seed = {"status": "not_executed", "reason": "Existing workspace is never reseeded."}
    saved = {"status": "not_executed", "reason": "Existing workspace is read-only in this demonstration."}
    if not existed:
        initialized = store.init_workspace()
        if initialized["status"] != "committed":
            print(json.dumps(initialized, ensure_ascii=False, indent=2))
            return 1
        seed = store.import_fixture(snapshot, artifacts)
        if seed["status"] != "committed":
            print(json.dumps(seed, ensure_ascii=False, indent=2))
            return 1
        candidate = copy.deepcopy(material)
        candidate["id"] = "FIX-b2b-prepared-material"
        work_ref = {"id": "FIX-b2b-material-work", "revision": 1}
        candidate["basis_refs"].append(work_ref)
        candidate["adoption"] = {
            "status": "adopted", "by": "AG2", "basis_refs": [work_ref],
            "scope": "Only synthetic material metadata and reference compatibility.",
            "limitations": ["Not a real professional conclusion or display event."],
        }
        saved = service.submit_material({
            "expected_state_revision": seed["state_revision"], "operation_id": "FIX-b2b-demo-prepare",
            "changes": [candidate], "authorization_refs": [{"id": "FIX-b2b-material-grant", "revision": 1}],
            "adoption_refs": [work_ref], "context": context,
        })
        if saved["status"] != "committed":
            print(json.dumps(saved, ensure_ascii=False, indent=2))
            return 1
    # Reopen before checking; this observes durable state, not the prior object.
    reopened = LearningStore(workspace, entry_actor="AG2")
    state = reopened.read_context()
    current = next((o for o in state.get("objects", []) if o["id"] == "FIX-b2b-prepared-material"), None)
    inspected = MaterialsService(reopened).inspect_material(current, context) if current else {"status": "unavailable", "reason": "The previous material is absent or controlled; it is not regenerated."}
    integrity = reopened.check_integrity()
    report = {
        "batch": "B2b", "client_date": "2026-10-03", "synthetic_only": True,
        "workspace": str(workspace), "existing_workspace": existed,
        "seed_receipt": seed, "save_receipt": saved,
        "state_revision": state.get("state_revision"), "object_count": len(state.get("objects", [])),
        "prepared_material_ref": ref(current) if current else None,
        "inspection": inspected, "integrity": integrity,
        "teaching": False, "assessment": False, "new_performance_created": False,
        "limitations": ["Fixture declarations are not professional truth verification.", "Existing spaces are read-only; absent or deleted records are never reimported.", "The report is an external demonstration copy, outside the store deletion scope."],
    }
    path = Path(args.report)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B2b synthetic demonstration: {workspace}")
    print(f"Reopened state revision: {report['state_revision']}; objects: {report['object_count']}; inspection: {inspected['status']}; integrity: {integrity['status']}.")
    return 0 if integrity["status"] == "ok" and inspected["status"] == "compatible" else 1


if __name__ == "__main__":
    raise SystemExit(main())
