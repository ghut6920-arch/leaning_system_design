"""Save a fictional B5 handoff chain; an existing workspace stays read-only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from runtime.learning_store import LearningStore
from runtime.personal_learning import PersonalLearningEntry
from runtime.learning_materials import ref
from test_b5_entry import CHECKPOINT, EVENT_ID, VERSION, envelope, fixture, flow_request, step, teach


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--report", default="validation/b5-demo-report.json")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    existed = (workspace / "records.sqlite3").exists()
    store = LearningStore(workspace, entry_actor="AG0")
    snapshot, artifacts, context, _, _ = fixture()
    initialization = []
    execution = None
    if not existed:
        initialization.append(store.init_workspace())
        if initialization[-1].get("status") != "committed":
            print(json.dumps(initialization[-1], ensure_ascii=False, indent=2))
            return 1
        initialization.append(store.import_fixture(snapshot, artifacts))
        if initialization[-1].get("status") != "committed":
            print(json.dumps(initialization[-1], ensure_ascii=False, indent=2))
            return 1
        execution = PersonalLearningEntry(store).execute(flow_request(store.read_context()["state_revision"]))
    reopened = LearningStore(workspace, entry_actor="AG0")
    before = reopened.read_context()
    objects = {o["id"]: o for o in before.get("objects", [])}
    checkpoint = objects.get(CHECKPOINT)
    entry = PersonalLearningEntry(reopened)
    if checkpoint:
        recovery = entry.execute(envelope(before["state_revision"], [step("resume", "teaching.run",
            teach("resume", context, checkpoint_ref=ref(checkpoint)))]))
    else:
        recovery = entry.status()
    integrity = reopened.check_integrity()
    unchanged = reopened.read_context().get("state_revision") == before.get("state_revision")
    report = {"batch": "B5", "client_date": "2026-10-03", "client_timezone": "Asia/Shanghai",
        "entry_version": VERSION, "synthetic_only": True, "workspace": str(workspace),
        "existing_workspace": existed, "initialization": initialization, "execution": execution,
        "recovery": recovery, "integrity": integrity, "reopen_read_only": unchanged,
        "state_revision": before.get("state_revision"), "event_ref": ref(objects[EVENT_ID]) if EVENT_ID in objects else None,
        "checkpoint_ref": ref(checkpoint) if checkpoint else None,
        "limitations": ["Explicit fictional professional findings and grants only; no real learner or host identity is established.",
            "Existing workspaces are never reseeded, replayed or professionally adopted by this demo.",
            "External reports and request copies are beyond managed store deletion scope."]}
    path = Path(args.report)
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    completed = execution is None or execution.get("status") == "completed"
    print(f"B5: revision {report['state_revision']}; execution {execution.get('status') if execution else 'existing workspace read-only'}; recovery {recovery['status']}; integrity {integrity['status']}; reopen read-only {unchanged}.")
    return 0 if completed and integrity.get("status") == "ok" and unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
