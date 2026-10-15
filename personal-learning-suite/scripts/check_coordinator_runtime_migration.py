"""Migrate and shadow a snapshot of a real DB; never change the source DB."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
from coordinator.complete import TaskArtifactCoordinator
from coordinator.runtime_scheduler import RuntimeScheduler
from coordinator.runtime_store import RuntimeStore
from coordinator.workspace import FileControlGate, GateError, sha


def tables(db):
    names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    return {name: sorted(tuple(row) for row in db.execute('SELECT * FROM "' + name + '"')) for name in names}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-workspace", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    original = args.source_workspace.resolve()
    output = args.output_dir.resolve()
    if output.exists() or not output.is_relative_to((SUITE.parent / "maintenance").resolve()):
        raise GateError("new_isolated_output_directory_required")
    source = original / ".coordinator/records.sqlite3"
    before_hash = sha(source.read_bytes())
    output.mkdir(parents=True)
    (output / ".coordinator").mkdir()
    db_path = output / ".coordinator/records.sqlite3"
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as db:
        previous = tables(db)
        with sqlite3.connect(db_path) as destination:
            db.backup(destination)
    gate_path = original / "coordination/control.json"
    gate = FileControlGate(original, gate_path) if gate_path.is_file() else None
    c = TaskArtifactCoordinator(output, gate)
    store = RuntimeStore(c)
    session = c.bind_local_operator("AG0")
    with sqlite3.connect(db_path) as db:
        revision_before = c.state_revision(db)
    migration = store.migrate(session)
    scheduler = RuntimeScheduler(c, {}, shadow=True)
    scheduler.start()
    try:
        shadow = scheduler.tick()
        snapshot = store.status()
    finally:
        store.release_supervisor(scheduler.instance_id)
    with c.connect() as db:
        after = tables(db)
    # Shadow adds only its independent consumer cursor to existing tables.
    unchanged = all((all(row in after[name] for row in rows) if name == "meta" else after[name] == rows)
                    for name, rows in previous.items() if name != "consumers")
    report = {"success": unchanged and snapshot["state_revision"] == revision_before and sha(source.read_bytes()) == before_hash and shadow["dispatches"] == 0,
              "source_db_unchanged": sha(source.read_bytes()) == before_hash, "business_tables_unchanged": unchanged,
              "state_revision_before": revision_before, "state_revision_after": snapshot["state_revision"],
              "model_dispatches": shadow["dispatches"], "existing_tasks_taken_over": len(snapshot["works"]), "migration": migration,
              "scope": "real DB snapshot only; no original task or artifact modified"}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
