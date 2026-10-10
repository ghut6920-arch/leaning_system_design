"""Save and reopen one explicitly artificial B3c configuration; existing spaces are read-only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from runtime.learning_store import LearningStore, STORE_VERSION
from runtime.learning_strategies import StrategyCatalog, StrategiesService, VERSION, CONFIG_VERSION
from test_b3c_strategies import configured, fixture, ref


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default="B3c_虚构策略学习空间")
    parser.add_argument("--report", default="validation/b3c-demo-report.json")
    args = parser.parse_args()
    workspace = Path(args.workspace)
    workspace = workspace.resolve() if workspace.is_absolute() else (ROOT.parent / workspace).resolve()
    report_path = Path(args.report)
    report_path = report_path.resolve() if report_path.is_absolute() else (ROOT / report_path).resolve()
    if not report_path.is_relative_to(ROOT):
        parser.error("Report must stay within the suite.")
    catalog = StrategyCatalog()
    config, context = configured(catalog)
    store = LearningStore(workspace, entry_actor="AG1")
    existing = (workspace / "records.sqlite3").exists()
    creation = None
    if not existing:
        initialized = store.init_workspace()
        if initialized["status"] != "committed" or initialized.get("initialized") is not True:
            print(json.dumps(initialized, ensure_ascii=False, indent=2))
            return 1
        snapshot, artifacts = fixture()
        imported = store.import_fixture(snapshot, artifacts)
        if imported["status"] != "committed":
            print(json.dumps(imported, ensure_ascii=False, indent=2))
            return 1
        creation = StrategiesService(store, catalog).submit_config({
            "expected_state_revision": imported["state_revision"], "operation_id": "FIX-b3c-demo-save",
            "changes": [config], "context": context,
            "authorization_refs": [{"id": "FIX-b3c-grant", "revision": 1}],
            "adoption_refs": [{"id": "FIX-b3c-work", "revision": 1}],
        })
    # Existing, restricted or deleted workspaces are never repopulated.
    reopened = LearningStore(workspace, entry_actor="AG1")
    state = reopened.read_context()
    reuse = StrategiesService(reopened, catalog).reuse_config(ref(config), context)
    integrity = reopened.check_integrity()
    report = {
        "batch": "B3c", "client_date": "2026-10-03", "synthetic_only": True,
        "workspace": str(workspace), "existing_workspace_read_only": existing,
        "creation_receipt": creation, "state_revision": state.get("state_revision"),
        "object_count": len(state.get("objects", [])), "reuse_status": reuse["status"],
        "reuse_reasons": reuse.get("reasons", []),
        "integrity_status": integrity["status"], "new_performance_events": 0, "new_plans": 0,
        "versions": {"store": STORE_VERSION, "strategies": VERSION, "strategy_input": CONFIG_VERSION, "python": platform.python_version()},
        "limitations": ["Developer-made declarations and grants; not real professional verification or learning.",
                        "Existing workspace is read only, including after deletion or restriction.",
                        "Seven Skill installation, host identity, timing, content truth and method efficacy remain unverified."],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if reuse["status"] == "reusable" and integrity["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
