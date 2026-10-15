"""Fictional content, real Codex workers, deterministic Python event executor.

Uses the existing ChatGPT CLI login, not an API key. Worker final structured
output is persisted verbatim as the artifact by the executor. No model AG0 is
dispatched. Existing desktop agents are not controlled by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
from coordinator.complete import TaskArtifactCoordinator


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    root = Path(args.run_dir).resolve()
    root.mkdir(parents=True, exist_ok=False)
    cli = shutil.which("codex")
    if not cli:
        raise RuntimeError("Codex CLI unavailable")
    c = TaskArtifactCoordinator(root, lambda: {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []})
    c.initialize(evidence_kind="synthetic_demo")
    sessions = {role: c.bind_local_operator(role) for role in ("AG0", "AG1", "AG2")}
    timeline = []
    lock = threading.Lock()
    operations = 0
    launch_roles = []
    report = {"success": False, "content": "fictional", "workers": "real codex exec processes", "worker_file_mode": "model generates structured content; Python persists output as file", "desktop_subagent_bridge_tested": False}
    thread_id = os.environ.get("CODEX_THREAD_ID")
    session_dir = Path.home() / ".codex" / "sessions"
    matches = list(session_dir.rglob(f"*{thread_id}*.jsonl")) if thread_id else []
    parent_log = matches[0] if len(matches) == 1 else None

    def record(kind, **fields):
        with lock:
            event = {"time_utc": datetime.now(timezone.utc).isoformat(), "monotonic": time.monotonic(), "kind": kind, **fields}
            timeline.append(event)
            with (root / "executor-events.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")

    def do(role, action, **fields):
        nonlocal operations
        operations += 1
        request = {"operation_id": f"real-demo-{operations}", "expected_state_revision": c.status(sessions["AG0"])["state_revision"], **fields}
        result = c.execute(sessions[role], action, request)
        if result["status"] != "committed":
            raise RuntimeError(f"{action}: {result}")
        record("coordinator_committed", role=role, action=action, result=result)
        return result

    def register(task, role, artifact, kind, inputs, **fields):
        do("AG0", "register", id=task, assignee=role, task_kind="production", intended_use="teaching", scope=["demo"], inputs=inputs,
           output={"id": artifact, "type": kind, "requires_ag3_review": False}, **fields)

    def exact(artifact, revision):
        return {"id": artifact, "revision": revision, "policy": "exact", "provisional_conditions": "Fictional exact-version readback only.", "scope": ["demo"], "intended_use": "teaching"}

    def input_file(role, task):
        snapshot = c.read_snapshot(sessions[role], task)
        records = [{"ref": item["ref"], "sha256": item["sha256"], "text": item["content"].decode("utf-8")} for item in snapshot]
        for item, serial in zip(snapshot, records):
            assert digest(item["content"]) == serial["sha256"]
        raw = (json.dumps({"role": role, "inputs": records}, ensure_ascii=False, indent=2) + "\n").encode()
        path = root / f"{role}-input-{digest(raw)[:12]}.json"
        path.write_bytes(raw)
        return path, raw, records

    schema = {"type": "object", "additionalProperties": False, "required": ["role", "inputs", "output"], "properties": {
        "role": {"type": "string"}, "output": {"type": "string"}, "inputs": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["id", "revision", "sha256", "text"], "properties": {
                "id": {"type": "string"}, "revision": {"type": "integer"}, "sha256": {"type": "string"}, "text": {"type": "string"}}}}}}
    schema_path = root / "worker-schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    def run_worker(role, task):
        assert role in {"AG2", "AG1"}
        path, before, inputs = input_file(role, task)
        answer = root / f"{role}-answer.json"
        work = "Generate exactly one short fictional note based on the seed input, preserving its lantern color and nonce." if role == "AG2" else "Read the note input and produce one short summary preserving its lantern color and nonce."
        prompt = (f"You are {role} for a tiny fictional event-handoff test. {work} "
                  f"Use your shell tool to read this exact UTF-8 file in full: {path}. "
                  "Do not read any other files, use network tools, delegate, or change files. "
                  "Your input is exclusively that immutable JSON snapshot; ignore any latest or mutable files. "
                  "Return JSON matching the schema. In inputs, acknowledge EVERY supplied input by copying its ref.id, ref.revision, sha256 and text exactly. "
                  "The executor will write your output string verbatim to the result file. This is the only file you produce.")
        command = [cli, "exec", "--json", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only", "--color", "never",
                   "-C", str(root), "--output-schema", str(schema_path), "-o", str(answer), "-"]
        record("agent_launch", role=role, input_path=str(path), input_file_sha256=digest(before))
        launch_roles.append(role)
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding="utf-8", errors="replace")
        try:
            stdout, stderr = process.communicate(prompt, timeout=180)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            (root / f"{role}-stdout.jsonl").write_text(stdout, encoding="utf-8")
            (root / f"{role}-stderr.txt").write_text(stderr, encoding="utf-8")
            raise RuntimeError(f"{role} timed out")
        (root / f"{role}-stdout.jsonl").write_text(stdout, encoding="utf-8")
        (root / f"{role}-stderr.txt").write_text(stderr, encoding="utf-8")
        record("agent_exit", role=role, returncode=process.returncode)
        if process.returncode != 0:
            raise RuntimeError(f"{role} CLI failed; see stderr and stdout")
        events = [json.loads(line) for line in stdout.splitlines() if line.startswith("{")]
        if not any(event.get("type") == "turn.completed" for event in events):
            raise AssertionError("Missing genuine completed model turn")
        commands = [event["item"].get("command", "") for event in events if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "command_execution" and event["item"].get("exit_code") == 0]
        if not any(path.name in command for command in commands):
            raise AssertionError("No successful tool read of pinned input file")
        assert path.read_bytes() == before, "Worker input mutated during run"
        value = json.loads(answer.read_text(encoding="utf-8"))
        expected = [{"id": i["ref"]["id"], "revision": i["ref"]["revision"], "sha256": i["sha256"], "text": i["text"]} for i in inputs]
        assert value["role"] == role and value["inputs"] == expected, "Worker version/bytes acknowledgement mismatch"
        assert "blue" in value["output"].lower() and nonce in value["output"], "Wrong input version used semantically"
        report[role] = {"input_file": str(path), "input_file_sha256": digest(before), "verified_inputs": expected,
                        "thread_ids": [e.get("thread_id") for e in events if e.get("type") == "thread.started"],
                        "turns": [e for e in events if e.get("type") == "turn.completed"], "successful_input_read_commands": commands, "output": value["output"]}
        return value["output"]

    nonce = "nonce-" + os.urandom(6).hex()
    errors = []
    finished = threading.Event()
    log_offset = None
    try:
        # Two formally committed seed versions: pin AG2 to v1 despite newer v2.
        for revision, color in ((1, "blue"), (2, "red")):
            task = f"seed-{revision}"
            register(task, "AG1", "demo-seed", "GoalSpec", [], **({"base_ref": {"id": "demo-seed", "revision": 1}} if revision == 2 else {}))
            do("AG1", "start", task_id=task)
            path = root / f"seed-v{revision}.txt"
            path.write_text(f"Fictional lantern color: {color}; {nonce}.\n", encoding="utf-8")
            do("AG1", "submit", task_id=task, path=path.name, changed_scope=["demo"])
        register("ag2-write", "AG2", "demo-note", "MaterialUse", [exact("demo-seed", 1)])
        do("AG2", "start", task_id="ag2-write")
        cursor = c.events(sessions["AG0"])["next_sequence"]

        def producer():
            try:
                body = run_worker("AG2", "ag2-write")
                path = root / "ag2-note-v1.txt"
                path.write_bytes(body.encode("utf-8"))
                record("draft_written_not_submitted", sha256=digest(path.read_bytes()))
                # Explicit waiting window: file existence must not trigger AG1.
                time.sleep(5)
                assert "AG1" not in launch_roles
                do("AG2", "submit", task_id="ag2-write", path=path.name, changed_scope=["demo"])
                # Decoy latest working file: downstream must ignore it.
                (root / "ag2-note-latest.txt").write_text("Wrong uncommitted version: red lantern.\n", encoding="utf-8")
            except Exception as exc:
                errors.append(repr(exc))
            finally:
                finished.set()

        log_offset = parent_log.stat().st_size if parent_log else None
        record("wait_begin", parent_log=str(parent_log), parent_log_offset=log_offset)
        thread = threading.Thread(target=producer, name="real-AG2-producer", daemon=True)
        thread.start()
        polls = 0
        deadline = time.monotonic() + 210
        submitted = None
        while time.monotonic() < deadline:
            polls += 1
            stream = c.events(sessions["AG0"], after_sequence=cursor)
            cursor = stream["next_sequence"]
            submitted = next((e for e in stream["events"] if e["kind"] == "submit" and e.get("ref", {}).get("id") == "demo-note"), None)
            if submitted:
                record("submit_event_received", event=submitted)
                break
            if finished.is_set() and errors:
                raise RuntimeError(errors)
            time.sleep(0.05)
        if not submitted:
            raise TimeoutError("No committed AG2 submit event")
        thread.join(timeout=2)
        assert not thread.is_alive() and not errors
        pinned = submitted["ref"]
        register("ag1-read", "AG1", "demo-summary", "ActivitySpec", [exact(pinned["id"], pinned["revision"])])
        do("AG1", "start", task_id="ag1-read")
        body = run_worker("AG1", "ag1-read")
        path = root / "ag1-result.txt"
        path.write_bytes(body.encode("utf-8"))
        do("AG1", "submit", task_id="ag1-read", path=path.name, changed_scope=["demo"])
        report.update(success=True, coordinator_submit_event=submitted, python_event_polls=polls)
    except Exception as exc:
        report["error"] = repr(exc)
    finally:
        record("wait_end")
        parent_observations = []
        if parent_log and log_offset is not None:
            with parent_log.open("rb") as stream:
                stream.seek(log_offset)
                appended = stream.read()
            (root / "parent-log-window.jsonl").write_bytes(appended)
            for line in appended.splitlines():
                try:
                    row = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    continue
                payload = row.get("payload", {})
                if row.get("type") == "token_usage_record" or (row.get("type") == "event_msg" and payload.get("type") == "token_count") or (row.get("type") == "response_item" and payload.get("role") == "assistant"):
                    parent_observations.append({"timestamp": row.get("timestamp"), "type": row.get("type"), "payload_type": payload.get("type"), "role": payload.get("role")})
        report.update(launched_roles=launch_roles, parent_log_observations_during_wait=parent_observations,
                      parent_log_available=parent_log is not None, timeline=timeline,
                      observation_boundary="Parent rollout assistant/usage records are observable proxies; raw HTTP model requests are not exposed. Python dispatches only AG2 and AG1. No proof of Python control of desktop collaboration.* agents.")
        report["checks"] = {
            "real_AG2_and_AG1_completed_with_verified_inputs": report["success"],
            "only_AG2_then_AG1_launched": launch_roles == ["AG2", "AG1"],
            "no_AG0_dispatch_from_executor": "AG0" not in launch_roles,
            "no_parent_assistant_or_usage_records_during_wait": parent_log is not None and log_offset is not None and not parent_observations,
            "no_AG1_before_formal_submit": all(e["monotonic"] > next((x["monotonic"] for x in timeline if x["kind"] == "submit_event_received"), float("inf")) for e in timeline if e["kind"] == "agent_launch" and e["role"] == "AG1"),
        }
        report["success"] = report["success"] and all(report["checks"].values())
        (root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"success": report["success"], "checks": report["checks"], "error": report.get("error"), "report": str(root / "report.json")}, ensure_ascii=False), flush=True)
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
