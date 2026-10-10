"""Reproduce checkpoint budget loss with public teaching APIs and fake fixtures.

All SQLite records live in TemporaryDirectory; only the small observation JSON
beside this script is saved. This is a software behavior probe, not learner data.
Run from any directory with Python 3.10+: python -B -X utf8 <this script>.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile

SUITE = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(SUITE / "src"), str(SUITE / "tests")]

from runtime.learning_store import LearningStore
from runtime.learning_teaching import fact, ref
from runtime.learning_teaching_b4 import SpecializedTeachingService
from test_b4_teaching import EVENT_ID, GRANT_ID, fixture, initial_request


def probe():
    snapshot, artifacts, context = fixture()
    with tempfile.TemporaryDirectory(prefix="pl-audit-fake-checkpoint-") as temp:
        store = LearningStore(Path(temp) / "workspace", entry_actor="AG0")
        assert store.init_workspace()["status"] == "committed"
        assert store.import_fixture(snapshot, artifacts)["status"] == "committed"
        service = SpecializedTeachingService(store)

        def state():
            result = store.read_context()
            assert result["status"] == "ok"
            return result

        def objects():
            return {obj["id"]: obj for obj in state()["objects"]}

        def packet(action, **extra):
            request = {
                "synthetic_only": True,
                "action": action,
                "activity_ref": {"id": "FIX-activity", "revision": 1},
                "context": copy.deepcopy(context),
                "authorization_refs": [{"id": GRANT_ID, "revision": 1}],
            }
            if action not in {"open", "resume"}:
                request.update(
                    expected_state_revision=state()["state_revision"],
                    operation_id="FIX-audit-" + action,
                )
            request.update(extra)
            return request

        initial = initial_request(state()["state_revision"], "FIX-audit-initial")
        initial["active_minutes"] = 1
        initial_result = service.run(initial)
        assert initial_result["status"] == "committed", initial_result
        budget_minutes = objects()["FIX-budget"]["user_active_time"]["value"]["minutes"]
        checkpoint_request = packet(
            "checkpoint",
            event_ref=ref(objects()[EVENT_ID]),
            checkpoint_id="FIX-audit-budget-checkpoint",
            active_minutes=budget_minutes,
            stop_reason="Synthetic declared budget exhausted",
            next_connection="Use only saved parent work after reconsideration",
            pending_owners=["AG1"],
            unrecorded_actions=fact("unknown", "No additional synthetic actions declared."),
        )
        checkpoint = service.run(checkpoint_request)
        assert checkpoint["status"] == "committed", checkpoint
        after_checkpoint = objects()
        checkpoint_object = after_checkpoint[checkpoint["checkpoint_ref"]["id"]]
        event_after_checkpoint = after_checkpoint[EVENT_ID]
        resume = service.run(packet("resume", checkpoint_ref=checkpoint["checkpoint_ref"]))
        opened = service.run(packet("open"))
        help_request = packet(
            "record_help",
            event_ref=ref(objects()[EVENT_ID]),
            help={
                "content": "Synthetic support: P and P implies Q are provided.",
                "visibility": "displayed",
                "target_operations": ["connect-P-to-Q"],
                "substituted_operations": [],
                "time": fact("unknown", "Synthetic ordering; no real learner or display."),
            },
        )
        help_result = service.run(help_request)
        return {
            "probe": "checkpoint-budget-loss",
            "synthetic_only": True,
            "claim": "software_behavior",
            "budget_minutes": budget_minutes,
            "initial_status": initial_result["status"],
            "checkpoint_status": checkpoint["status"],
            "checkpoint_affected_ids": checkpoint.get("affected_ids"),
            "checkpoint_event_ref": checkpoint.get("event_ref"),
            "checkpoint_minutes": checkpoint_object["declared_active_minutes"],
            "event_minutes_after_checkpoint": event_after_checkpoint["c0"]["declared_active_minutes"],
            "resume_status": resume["status"],
            "resume_minutes": resume.get("recovery", {}).get("declared_active_minutes"),
            "open_after_budget_status": opened["status"],
            "help_after_budget_status": help_result["status"],
            "help_after_budget_reasons": help_result.get("reasons", []),
            "help_event_ref": help_result.get("event_ref"),
            "bug_reproduced": (
                checkpoint_object["declared_active_minutes"]["value"]["minutes"] == budget_minutes
                and event_after_checkpoint["c0"]["declared_active_minutes"]["value"]["minutes"] < budget_minutes
                and help_result["status"] == "committed"
            ),
            "requests": {
                "initial": initial,
                "checkpoint": checkpoint_request,
                "help_after_checkpoint": help_request,
            },
        }


if __name__ == "__main__":
    result = probe()
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    Path(__file__).with_name("checkpoint-budget-result.json").write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
