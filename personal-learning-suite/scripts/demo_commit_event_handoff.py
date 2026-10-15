"""Fictional event-driven handoff; workers are ordinary Python functions, not LLMs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
from coordinator.complete import TaskArtifactCoordinator


def main():
    with tempfile.TemporaryDirectory(prefix="fictional-agent-handoff-") as temporary:
        root = Path(temporary)
        c = TaskArtifactCoordinator(root, lambda: {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []})
        c.initialize(evidence_kind="synthetic_demo")
        sessions = {role: c.bind_local_operator(role) for role in ("AG0", "AG1", "AG2")}
        model_calls = {"AG0": 0, "AG1": 0, "AG2": 0}
        ops = 0

        def do(role, action, **fields):
            nonlocal ops
            ops += 1
            state = c.status(sessions["AG0"])
            request = {"operation_id": f"fictional-{ops}", "expected_state_revision": state["state_revision"], **fields}
            result = c.execute(sessions[role], action, request)
            if result["status"] != "committed":
                raise RuntimeError(f"{action} failed: {result}")
            return result

        # AG0 registers a fictional AG2 file-production task.
        do("AG0", "register", id="ag2-write", assignee="AG2", task_kind="production",
           intended_use="teaching", scope=["demo"], inputs=[],
           output={"id": "demo-note", "type": "MaterialUse", "requires_ag3_review": False})
        do("AG2", "start", task_id="ag2-write")

        event_seen = threading.Event()
        completed = {}
        errors = []
        wait_polls = 0
        event_start = c.events(sessions["AG0"])["next_sequence"]

        def python_executor():
            nonlocal wait_polls
            try:
                # This process waits on the local event stream; it makes no model calls.
                while not event_seen.is_set():
                    wait_polls += 1
                    stream = c.events(sessions["AG0"], after_sequence=event_start)
                    submitted = next((e for e in stream["events"] if e["kind"] == "submit" and e.get("ref", {}).get("id") == "demo-note"), None)
                    if submitted:
                        event = submitted
                        event_seen.set()
                        ref = event["ref"]
                        target = next(a for a in c.status(sessions["AG0"])["artifacts"] if a["id"] == ref["id"] and a["revision"] == ref["revision"])
                        # Event is the trigger; the exact committed revision is the input contract.
                        do("AG0", "register", id="ag1-read", assignee="AG1", task_kind="production",
                           intended_use="teaching", scope=["demo"],
                           inputs=[{"id": ref["id"], "revision": ref["revision"], "policy": "exact",
                                    "provisional_conditions": "Fictional readback of this exact committed candidate.",
                                    "scope": ["demo"], "intended_use": "teaching"}],
                           output={"id": "demo-summary", "type": "ActivitySpec", "requires_ag3_review": False})
                        do("AG1", "start", task_id="ag1-read")
                        snapshot = c.read_snapshot(sessions["AG1"], "ag1-read")
                        source = snapshot[0]
                        raw = source["content"]
                        if source["ref"]["id"] != ref["id"] or source["ref"]["revision"] != ref["revision"] or source["sha256"] != target["sha256"] or hashlib.sha256(raw).hexdigest() != target["sha256"]:
                            raise AssertionError("AG1 did not receive the exact event version")
                        text = raw.decode("utf-8")
                        output = f"AG1 read {ref['id']} v{ref['revision']}: {text.strip()}\n"
                        (root / "artifacts" / "ag1-result.txt").parent.mkdir(parents=True, exist_ok=True)
                        (root / "artifacts" / "ag1-result.txt").write_text(output, encoding="utf-8")
                        do("AG1", "submit", task_id="ag1-read", path="artifacts/ag1-result.txt", changed_scope=["demo"])
                        completed.update(event_ref=ref, event_sequence=event["sequence"], input_ref={**source["ref"], "sha256": source["sha256"]},
                                        input_sha256=hashlib.sha256(raw).hexdigest(), committed_sha256=target["sha256"], result=output)
                        return
                    time.sleep(0.01)
                raise AssertionError("unexpected duplicate trigger")
            except Exception as exc:  # surfaced in the main thread
                errors.append(repr(exc))
                event_seen.set()

        listener = threading.Thread(target=python_executor, name="fictional-event-executor", daemon=True)
        listener.start()
        # Fictional AG2 writes and formally submits one simple file.
        body = b"Fictional AG2 payload: blue lantern.\r\n"
        (root / "artifacts").mkdir(exist_ok=True)
        (root / "artifacts" / "ag2-note.txt").write_bytes(body)
        do("AG2", "submit", task_id="ag2-write", path="artifacts/ag2-note.txt", changed_scope=["demo"])
        listener.join(timeout=3)
        if listener.is_alive() or errors:
            raise RuntimeError(f"executor failed/timed out: {errors}")
        report = {
            "evidence": "synthetic_demo",
            "real_agents_launched": False,
            "event": "AG2 submit event read from coordinator event stream",
            "executor": "ordinary Python thread; zero LLM/model calls",
            "model_call_counts": model_calls,
            "python_wait_polls": wait_polls,
            "ag2_committed_ref": completed["event_ref"],
            "ag1_fixed_input_ref": {k: completed["input_ref"][k] for k in ("id", "revision")},
            "ag2_committed_sha256": completed["committed_sha256"],
            "ag1_input_sha256": completed["input_sha256"],
            "ag1_result": completed["result"],
            "assertions": {
                "event_after_commit": completed["event_sequence"] > event_start,
                "ag1_read_exact_revision": all(completed["event_ref"][k] == completed["input_ref"][k] for k in ("id", "revision")),
                "ag1_read_exact_bytes": completed["input_sha256"] == hashlib.sha256(body).hexdigest(),
                "no_repeated_ag0_model_requests": model_calls["AG0"] == 0,
                "both_agents_are_llm_agents": False,
            },
            "boundary": "Proves local event-driven Python handoff and exact-version snapshot. Does not prove ordinary Python can launch an AG1 Codex model; this host exposes no such model-launch API to the script.",
        }
        out = SUITE / "validation" / "commit-event-handoff-report.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
