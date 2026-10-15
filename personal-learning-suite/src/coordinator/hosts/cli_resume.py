"""Asynchronous, persistent ``codex exec`` turns with durable JSONL evidence.

Model and provider settings are inherited. The sandbox is always read-only.
Only completed turns are resumed; unknown old executions are never restarted.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import uuid

from . import DEFAULT_OUTPUT_SCHEMA, attempt_directory, dispatch_prompt, save_json, structured_result


def _stamp():
    return datetime.now(timezone.utc).isoformat()


def _binding_key(binding):
    return json.dumps([binding.get("id") or binding.get("binding_id") or binding.get("role"),
                       binding.get("generation", binding.get("binding_generation")),
                       binding.get("host_id"), binding.get("cwd")], sort_keys=True)


class CLIResumeHost:
    def __init__(self, run_root, output_schema=None, *, cli_path=None, env=None, process_factory=None):
        self.run_root = Path(run_root).resolve()
        self.output_schema = deepcopy(DEFAULT_OUTPUT_SCHEMA if output_schema is None else output_schema)
        self.env = dict(os.environ if env is None else env)
        self.cli_path = cli_path or self.env.get("CODEX_CLI_PATH") or shutil.which("codex", path=self.env.get("PATH"))
        self._process_factory = subprocess.Popen if process_factory is None else process_factory
        self._processes = {}
        self._attempts = {}
        self._lock = threading.Lock()
        self._closed = False

    def _record(self, dispatch_id):
        directory = attempt_directory(self.run_root, dispatch_id)
        try:
            value = json.loads((directory / "attempt.json").read_text(encoding="utf-8"))
            if isinstance(value, dict) and value.get("dispatch_id") == dispatch_id:
                return value
            raise ValueError("invalid_attempt")
        except (OSError, ValueError):
            return {"status": "dispatch_unknown", "dispatch_id": dispatch_id,
                    "stdout_path": str(directory / "stdout.jsonl"),
                    "result_path": str(directory / "result.json"),
                    "exit_path": str(directory / "exit.json"),
                    "problem": "existing_attempt_unresolved"}

    def _known_attempts(self):
        rows = dict(self._attempts)
        if self.run_root.is_dir():
            for path in self.run_root.glob("*/attempt.json"):
                try:
                    value = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if isinstance(value, dict) and value.get("dispatch_id"):
                    rows[value["dispatch_id"]] = value
        return sorted(rows.values(), key=lambda a: a.get("process_started_at", a.get("created_at", "")), reverse=True)

    def inspect(self, binding):
        base = {"thread_id": binding.get("thread_id"), "last_turn_id": binding.get("last_turn_id")}
        if self._closed or not self.cli_path:
            return {**base, "state": "unavailable", "problem": "cli_host_unavailable"}
        for attempt in self._known_attempts():
            same_binding = attempt.get("binding_key") == _binding_key(binding)
            if not same_binding:
                continue
            observed = self.observe(binding, attempt)
            if base["thread_id"] and observed.get("thread_id") != base["thread_id"]:
                continue
            observed_base = {**base, "thread_id": observed.get("thread_id")}
            if observed["status"] == "result_saved" and observed.get("turn_ended"):
                process = self._processes.get(attempt.get("start_handle"))
                return {**observed_base, "state": "active" if process and process.poll() is None else "idle",
                        "last_turn_id": observed.get("turn_id")}
            if observed["status"] in {"accepted", "running"}:
                return {**observed_base, "state": "active", "last_turn_id": observed.get("turn_id")}
            return {**observed_base, "state": "unavailable", "problem": observed.get("problem", "cli_execution_unresolved")}
        # A fresh binding is safe to create. An existing thread without evidence
        # is not presumed idle: the adapter does not inspect private session files.
        return {**base, "state": "idle" if not base["thread_id"] else "unavailable",
                **({"problem": "bound_cli_thread_state_unknown"} if base["thread_id"] else {})}

    def dispatch(self, binding, prompt, dispatch_id):
        with self._lock:
            directory = attempt_directory(self.run_root, dispatch_id)
            if directory.exists():
                return self._record(dispatch_id)
            if self._closed or not self.cli_path:
                return {"status": "host_unavailable", "dispatch_id": dispatch_id,
                        "thread_id": binding.get("thread_id"), "problem": "cli_host_unavailable"}
            state = self.inspect(binding)
            if state["state"] != "idle":
                return {"status": "host_unavailable", "dispatch_id": dispatch_id,
                        **state, "problem": "target_not_idle"}
            directory.mkdir(parents=True, exist_ok=False)
            stdout_path = directory / "stdout.jsonl"
            result_path = directory / "result.json"
            schema_path = directory / "schema.json"
            prompt_path = directory / "prompt.txt"
            save_json(schema_path, self.output_schema)
            prompt_path.write_text(dispatch_prompt(prompt, dispatch_id), encoding="utf-8")
            receipt = {"status": "dispatch_unknown", "dispatch_id": dispatch_id,
                       "thread_id": state.get("thread_id"), "before_turn_id": state["last_turn_id"],
                       "binding_key": _binding_key(binding),
                       "created_at": _stamp(), "stdout_path": str(stdout_path),
                       "result_path": str(result_path), "exit_path": str(directory / "exit.json"),
                       "attempt_path": str(directory / "attempt.json")}
            save_json(directory / "attempt.json", receipt)
            cwd = Path(binding.get("cwd") or Path.cwd()).resolve()
            command = [str(self.cli_path), "exec", "--sandbox", "read-only", "-C", str(cwd)]
            if receipt.get("thread_id"):
                command.append("resume")
            command += ["--json", "--skip-git-repo-check", "--output-schema", str(schema_path), "-o", str(result_path)]
            if receipt.get("thread_id"):
                command.append(receipt["thread_id"])
            command.append("-")
            options = {"stderr": subprocess.DEVNULL, "cwd": str(cwd), "env": self.env}
            if os.name == "nt":
                options["creationflags"] = subprocess.CREATE_NO_WINDOW
            try:
                # File-backed stdio avoids pipe deadlocks and survives scheduler
                # exit. No communicate()/run() waits for a whole model turn.
                with prompt_path.open("rb") as source, stdout_path.open("xb") as output:
                    process = self._process_factory(command, stdin=source, stdout=output, **options)
            except OSError:
                # Popen failed before returning a child handle; no model run is
                # known to have started. Never log exception/env/CLI stderr.
                receipt.update(status="host_unavailable", problem="cli_process_start_failed")
                save_json(directory / "attempt.json", receipt)
                return dict(receipt)
            receipt.update(status="accepted", pid=process.pid,
                           process_started_at=_stamp(), start_handle=uuid.uuid4().hex)
            self._processes[receipt["start_handle"]] = process
            self._attempts[dispatch_id] = receipt
            threading.Thread(target=self._watch, args=(process, dict(receipt)), daemon=True).start()
            try:
                save_json(directory / "attempt.json", receipt)
            except OSError:
                receipt.update(status="dispatch_unknown", problem="cli_launch_receipt_persist_failed")
            return dict(receipt)

    def _watch(self, process, attempt):
        try:
            returncode = process.wait()
            save_json(Path(attempt["exit_path"]), {"returncode": returncode, "pid": attempt["pid"],
                     "start_handle": attempt["start_handle"], "process_started_at": attempt["process_started_at"],
                     "finished_at": _stamp()})
        except OSError:
            pass  # Missing exit metadata stays unknown; do not emit private diagnostics.

    def _owned_path(self, path):
        return bool(path) and Path(path).resolve().is_relative_to(self.run_root)

    def _events(self, path):
        rows = []
        if not self._owned_path(path):
            return rows
        try:
            with Path(path).open(encoding="utf-8", errors="replace") as source:
                for line in source:
                    # A running writer may have only flushed half its last row.
                    if not line.endswith("\n"):
                        continue
                    try:
                        value = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(value, dict):
                        rows.append(value)
        except OSError:
            pass
        return rows

    def observe(self, binding, attempt):
        # The scheduler may persist the adapter receipt inside its own attempt.
        attempt = {**attempt, **attempt.get("host_receipt", {})}
        dispatch_id = attempt.get("dispatch_id")
        expected_thread = attempt.get("thread_id") or binding.get("thread_id")
        base = {"dispatch_id": dispatch_id, "thread_id": expected_thread}
        if (attempt.get("thread_id") and binding.get("thread_id")
                and attempt["thread_id"] != binding["thread_id"]):
            return {**base, "status": "execution_unknown", "problem": "attempt_thread_mismatch"}
        events = self._events(attempt.get("stdout_path"))
        started = [e.get("thread_id") for e in events if e.get("type") == "thread.started"]
        if any(not isinstance(t, str) or not t for t in started):
            return {**base, "status": "execution_unknown", "problem": "invalid_cli_thread_evidence"}
        if started:
            if len(set(started)) != 1 or expected_thread and started[0] != expected_thread:
                return {**base, "status": "execution_unknown", "problem": "cli_thread_mismatch"}
            base["thread_id"] = started[0]
        terminal = [e for e in events if e.get("type") in {"turn.completed", "turn.failed", "turn.cancelled"}]
        turn = terminal[-1] if terminal else {}
        turn_id = turn.get("turn_id") or turn.get("id")
        process = self._processes.get(attempt.get("start_handle"))
        returncode = process.poll() if process is not None else None
        exited = returncode is not None
        if self._owned_path(attempt.get("exit_path")):
            try:
                exit_record = json.loads(Path(attempt["exit_path"]).read_text(encoding="utf-8"))
                # PID alone never identifies an execution, including after reboot.
                if (exit_record.get("start_handle") == attempt.get("start_handle")
                        and exit_record.get("process_started_at") == attempt.get("process_started_at")
                        and exit_record.get("pid") == attempt.get("pid")
                        and attempt.get("start_handle")):
                    returncode, exited = exit_record["returncode"], True
            except (OSError, ValueError, KeyError):
                pass
        if started and turn.get("type") in {"turn.failed", "turn.cancelled"}:
            return {**base, "status": "failed", "turn_id": turn_id,
                    "problem": "cli_turn_failed", "turn_ended": exited}
        if started and turn.get("type") == "turn.completed":
            result = None
            if self._owned_path(attempt.get("result_path")):
                try:
                    result = structured_result(Path(attempt["result_path"]).read_text(encoding="utf-8-sig"), dispatch_id)
                except OSError:
                    pass
            if result is None:
                for event in reversed(events):
                    item = event.get("item", {})
                    if event.get("type") == "item.completed" and item.get("type") == "agent_message":
                        result = structured_result(item.get("text"), dispatch_id)
                        if result:
                            break
            if result:
                return {**base, "status": "result_saved", "turn_id": turn_id,
                        "turn_ended": True, "process_exited": exited, "result": result,
                        "result_path": attempt.get("result_path"), "usage": turn.get("usage")}
            return {**base, "status": "execution_unknown", "turn_id": turn_id,
                    "problem": "no_correlated_structured_result"}
        if exited:
            return {**base, "status": "failed" if returncode else "execution_unknown",
                    "problem": "cli_process_failed" if returncode else "cli_completion_evidence_missing",
                    "returncode": returncode, "turn_ended": True}
        if process is not None:
            return {**base, "status": "running" if started else "accepted", "turn_id": turn_id}
        return {**base, "status": "execution_unknown", "problem": "cli_process_state_unknown"}

    def close(self):
        # Detach only. Cancellation is a separate scheduler/user decision. Direct
        # child file descriptors and the child itself do not depend on this object.
        self._closed = True
