"""Read-only architecture probe over existing public APIs and fictional fixtures.

Only writes the requested report. Learning records live in an isolated temporary
directory, which is removed after the probe. No runtime or fixture files change.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
SUITE = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(SUITE / "src"), str(SUITE / "tests")]

from runtime.learning_store import LearningStore
from runtime.personal_learning import PersonalLearningEntry
from test_b5_entry import envelope, new_goal_fixture, step


def main() -> None:
    snapshot, _package, source_request, goal_request = new_goal_fixture()
    with tempfile.TemporaryDirectory(prefix="pl-architecture-source-probe-") as temporary:
        store = LearningStore(temporary, entry_actor="AG0")
        initialized = store.init_workspace()
        seeded = store.import_fixture(snapshot, {})
        assert initialized["status"] == seeded["status"] == "committed"
        entry = PersonalLearningEntry(store)
        prepared = entry.execute(envelope(1, [
            step("sources", "goal.sources_submit", source_request),
            step("goal", "goal.submit", goal_request),
        ]))
        assert prepared["status"] == "completed", prepared
        saved_sources = [
            {"id": obj["id"], "revision": obj["revision"],
             "read_scope_keys": list(obj["read_scope"]),
             "verification_keys": list(obj["verification"])}
            for obj in store.read_context()["objects"]
            if obj["type"] == "SourceFragment"
        ]
        request = copy.deepcopy(source_request)
        request.pop("package", None)
        request["operation_id"] = "FIX-audit-prepare-sources"
        request["changes"] = [{**obj, "revision": 2} for obj in request["changes"]]
        before = store.read_context()["state_revision"]
        material_stage = entry.execute(envelope(before, [
            step("prepare", "materials.submit", request),
        ]))
        after = store.read_context()["state_revision"]
        result = {
            "probe": "B5 goal.sources_submit -> goal.submit -> materials.submit",
            "data_kind": "synthetic",
            "source": "Existing test_b5_entry.new_goal_fixture()",
            "observed": {
                "source_and_goal_status": prepared["status"],
                "source_and_goal_steps": [
                    {"operation": item["operation"], "status": item["result"]["status"]}
                    for item in prepared["steps"]
                ],
                "saved_source_shapes": saved_sources,
                "material_stage_status": material_stage["status"],
                "material_stage_result": material_stage["steps"][0]["result"],
                "state_before_material_stage": before,
                "state_after_material_stage": after,
                "material_stage_mutated": material_stage["mutated"],
            },
            "limitations": [
                "A metadata-only source revision intentionally preserves the accepted B2a representation.",
                "This verifies that B5 does not automatically bridge the B2a/B2b source formats.",
                "It does not claim that an explicitly redesigned source packet cannot be submitted.",
                "No semantic verification, real user learning, or effectiveness claim is made.",
            ],
        }
        destination = Path(__file__).with_name("source-contract-result.json")
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
