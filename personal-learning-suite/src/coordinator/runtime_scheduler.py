"""A program waits for events; models run only for durable, ready work."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
import threading
import time
import uuid

from .agent_api import AgentCoordinator
from .runtime_outputs import materialize_output
from .runtime_store import RuntimeStore, TERMINAL, UNCERTAIN
from .workspace import GateError, encode, sha


class RuntimeScheduler:
    def __init__(self, coordinator, hosts, *, instance_id=None, shadow=False):
        self.c = coordinator
        self.store = RuntimeStore(coordinator)
        self.api = AgentCoordinator(coordinator)
        self.session = coordinator.bind_local_operator("AG0")
        self.hosts = hosts
        self.instance_id = instance_id or "scheduler-" + uuid.uuid4().hex
        self.shadow = shadow
        self.wakeup = threading.Event()
        self.started = False
        self.dispatch_count = 0

    def start(self):
        self.store.recover(self.instance_id)
        self.started = True
        return {"status": "ready", "instance_id": self.instance_id, "pid": os.getpid(), "shadow": self.shadow, "meaning": "listener_ready_plan_must_also_be_saved"}

    def context(self, attempt, binding):
        return {"dispatch_id": attempt["dispatch_id"], "claim_epoch": attempt["claim_epoch"], "thread_id": binding.get("thread_id")}

    def update(self, dispatch_id, state, **fields):
        return self.store.update_attempt(dispatch_id, state, instance_id=self.instance_id, **fields)

    def packet(self, work, attempt, binding):
        # Input bytes come only from registered immutable refs and are rechecked.
        inputs = []
        for item in work["inputs"]:
            with self.c.connect() as db:
                control = self.c.controls(db)
                self.c.gate(control, work["scope_ids"], work["intended_uses"])
                artifact = self.c.artifact(db, item["ref"])
                self.c.verify_file(artifact)
            raw = (self.c.root / item["path"]).read_bytes()
            if sha(raw) != item["sha256"]:
                raise GateError("runtime_input_changed")
            inputs.append({**item, "text": raw.decode("utf-8")})
        snapshots = []
        for setup in work["node"].get("setup_intents", []):
            with self.c.connect() as db:
                existing = db.execute("SELECT body FROM tasks WHERE id=?", (setup["task"],)).fetchone()
                if existing:
                    existing_task = json.loads(existing[0])
                    source = self.c.get(db, "tasks", setup["from_task"])
                    if setup["action"] == "assign_readback":
                        matches = (existing_task["task_kind"] == "production"
                                   and existing_task["assignee"] == "AG1"
                                   and set(existing_task["scope"]) == set(setup["scope"])
                                   and existing_task["intended_use"] == setup["use"]
                                   and existing_task["output"]["id"] == setup["output"]["id"]
                                   and existing_task["output"]["type"] == "ActivitySpec"
                                   and any({"id": item.get("id"), "revision": item.get("revision")} == source["result_ref"]
                                           and item.get("policy") == "exact"
                                           and set(item.get("scope", [])) == set(setup["scope"])
                                           and item.get("intended_use") == setup["use"]
                                           and item.get("provisional_conditions") == setup["provisional_conditions"]
                                           for item in existing_task["inputs"]))
                    else:
                        matches = existing_task.get("target_ref") == source["result_ref"]
                    if not matches:
                        raise GateError("runtime_setup_target_changed")
                    continue
            setup_session = self.c.bind_local_operator("AG0", dispatch=self.context(attempt, binding), runtime_setup=True)
            receipt = self.api.do(setup_session, setup, request_key=attempt["dispatch_id"] + ":setup:" + setup["task"])
            if receipt["status"] != "committed":
                raise GateError(receipt.get("problem", "runtime_setup_failed"))
        if work["node"].get("task"):
            task = work["node"]["task"]
            session = self.c.bind_local_operator(binding["role"], dispatch=self.context(attempt, binding))
            with self.c.connect() as db:
                current = self.c.get(db, "tasks", task)
            if current["phase"] != "running":
                begin = self.api.do(session, {"action": "begin", "task": task}, request_key=attempt["dispatch_id"] + ":begin:" + str(attempt["claim_epoch"]))
                if begin["status"] != "committed":
                    raise GateError(begin.get("problem", "task_begin_failed"))
            for item in self.c.read_snapshot(session, task):
                snapshots.append({"ref": item["ref"], "sha256": item["sha256"], "text": item["content"].decode("utf-8")})
        with self.c.connect() as db:
            control = self.c.controls(db)
            facts = self.store._facts(db, work["node"], control)
            prior_results = []
            dependencies = {condition["node"] for condition in work["node"].get("conditions", []) if condition["kind"] == "work_done"}
            for node_id in work["node"].get("include_prior_results", []):
                if node_id not in dependencies:
                    raise GateError("runtime_prior_result_not_dependency")
                candidates = [json.loads(row[0]) for row in db.execute("SELECT body FROM runtime_works")]
                source = next((row for row in candidates if row["workflow_id"] == work["workflow_id"]
                               and row["node"]["id"] == node_id and row["state"] == "done"), None)
                if source is None:
                    raise GateError("runtime_prior_result_not_done")
                self.c.gate(control, source["scope_ids"], source["intended_uses"])
                prior_attempt = self.store.get(db, "runtime_attempts", source["dispatch_id"])
                result_path = Path(prior_attempt["result_path"]).resolve()
                if (not result_path.is_relative_to(self.c.meta_root.resolve())
                        or sha(result_path.read_bytes()) != prior_attempt["result_sha256"]):
                    raise GateError("runtime_result_changed")
                result = json.loads(result_path.read_text(encoding="utf-8"))
                if result.get("dispatch_id") != source["dispatch_id"]:
                    raise GateError("invalid_correlated_result")
                prior_path = "artifacts/runtime/" + source["dispatch_id"] + ".txt"
                raw_prior = (self.c.root / prior_path).read_bytes()
                if "output_spec" not in source["node"]:
                    if raw_prior != result["output"].encode("utf-8"):
                        raise GateError("runtime_output_changed")
                else:
                    source_task = self.c.get(db, "tasks", source["node"]["task"])
                    source_artifact = self.c.artifact(db, source_task["result_ref"])
                    self.c.verify_file(source_artifact)
                    if source_artifact["path"] != prior_path or source_artifact["sha256"] != sha(raw_prior):
                        raise GateError("runtime_output_changed")
                prior_results.append({"node_id": node_id, "dispatch_id": source["dispatch_id"],
                                      "result_path": str(result_path), "result_sha256": prior_attempt["result_sha256"],
                                      "path": prior_path, "sha256": sha(raw_prior), "text": raw_prior.decode("utf-8")})
        packet = {"dispatch_id": attempt["dispatch_id"], "context": self.context(attempt, binding), "role": binding["role"], "workflow_id": work["workflow_id"], "node_id": work["node"]["id"], "task": work["node"].get("task"), "instructions": work["node"]["prompt"], "inputs": inputs, "task_snapshot": snapshots, "prior_results": prior_results, "decision_basis": facts["facts"], "current_controls": control, "allowed_tasks": work["node"]["allowed_tasks"], "allowed_actions": work["node"]["allowed_actions"], "workspace": str(self.c.root), "output_path_token": "$output", "result_via_file": work["node"].get("result_via_file", False)}
        if "output_spec" in work["node"]:
            packet["output_spec"] = work["node"]["output_spec"]
        directory = self.c.meta_root / "runtime-packets"
        directory.mkdir(exist_ok=True)
        path = directory / (attempt["dispatch_id"] + ".json")
        raw = encode(packet).encode("utf-8")
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        return packet, path, sha(raw)

    def prompt(self, packet, binding):
        protocol = ("Complete only this bounded task. Do not poll, wait, start other agents, change settings or arrange another wakeup. "
                    "Return one JSON object {dispatch_id, output, intents}. Copy the exact dispatch_id. "
                    "intents contains only your explicit professional decisions in the existing AgentCoordinator API shape. "
                    "For deliver, use path '$output'; the executor saves output verbatim. Do not invent supported opinions. "
                    "Use the exact input refs and hashes; a newer file is not a replacement. Finish the turn after the result.\n")
        if "output_spec" in packet:
            protocol += ("For output_spec.kind preparation_sources, output must be a JSON-encoded string containing "
                         "exactly {files:[{id,content},...]}, with one nonempty UTF-8 text content for every declared "
                         "member id and no extra ids or fields. Author all real teaching content in those members. "
                         "Do not write files or construct the inventory. The executor writes only the declared immutable "
                         "paths, hashes the bytes and makes the exact preparation_sources manifest. Your deliver path "
                         "remains '$output' and refers to that manifest. Judge the authored content in your opinion.\n")
        if binding["host_kind"] == "desktop":
            script = Path(__file__).resolve().parents[2] / "scripts" / "coordinate_runtime.py"
            protocol += ("First call the runtime begin-dispatch command with this context, before professional work. "
                         "If rejected, stop and report the rejection; do not perform the task. "
                         f"Entry: {script}; workspace: {self.c.root}. Command: begin-dispatch --dispatch-id "
                         f"{packet['dispatch_id']} --claim-epoch {packet['context']['claim_epoch']} --role {packet['role']}; "
                         "thread identity must come from your actual CODEX_THREAD_ID. "
                         "The executor publishes the intents after saving your result; do not publish through a different unbound entry.\n")
            if packet.get("result_via_file"):
                protocol += ("Persist your structured result as a UTF-8 JSON file under this workspace, then call "
                             f"{script} --workspace <workspace> result --dispatch-id {packet['dispatch_id']} "
                             f"--claim-epoch {packet['context']['claim_epoch']} --role {packet['role']} --result-file <file>. "
                             "After successful persistence, your final reply to the user can be ordinary readable prose. "
                             "Do not wait for other agents inside this turn.\n")
        return protocol + encode(packet)

    def tick(self):
        if not self.started:
            self.start()
        self.store.renew(self.instance_id)
        registered = self.store.reconcile(self.session)
        snapshot = self.store.status()
        if self.shadow:
            return {"registered": registered, "dispatches": 0, "shadow": True}
        # Observe previously sent work before considering new work.
        for short in snapshot["works"]:
            work = self.store.lookup("runtime_works", short["id"])
            if work["state"] in {"accepted", "running", "dispatch_unknown", "execution_unknown", "result_saved", "committed", "host_unavailable"}:
                self.progress(work)
        for short in self.store.status()["works"]:
            if short["state"] != "ready":
                continue
            work = self.store.lookup("runtime_works", short["id"])
            binding = self.store.lookup("runtime_bindings", work["node"]["binding"])
            host = self.hosts.get(binding["host_kind"])
            if host is None:
                continue
            try:
                state = host.inspect(binding)
                if state.get("state") != "idle":
                    continue
                attempt = self.store.claim(work["id"], self.instance_id)
            except GateError:
                continue
            try:
                packet, path, digest = self.packet(work, attempt, binding)
                self.store.assert_dispatch(self.context(attempt, binding), binding["role"])
                # The idle read isn't atomic with a user turn; the receiver and
                # publication gates enforce the remaining boundary.
                if host.inspect(binding).get("state") != "idle":
                    self.update(attempt["dispatch_id"], "ready", reason="host_became_busy")
                    continue
                self.update(attempt["dispatch_id"], "dispatching", before_turn_id=state.get("last_turn_id"), packet_path=str(path), packet_sha256=digest, sent_at_ms=self.c.clock_ms())
                self.c.checkpoint("runtime_before_send")
                self.dispatch_count += 1
                reply = host.dispatch(binding, self.prompt(packet, binding), attempt["dispatch_id"])
                self.c.checkpoint("runtime_after_send")
                latest = self.store.lookup("runtime_works", work["id"])
                # Fast receiver may have already saved its begin receipt.
                status = reply.get("status", "dispatch_unknown")
                if status not in {"accepted", "running", "dispatch_unknown", "host_unavailable", "failed"}:
                    status = "dispatch_unknown"
                if latest["state"] == "running" and status == "accepted":
                    status = "running"
                fields = {k: v for k, v in reply.items() if k not in {"status", "dispatch_id", "state", "work_id", "claim_epoch", "instance_id", "binding_generation"}}
                if reply.get("problem"):
                    fields["reason"] = reply["problem"]
                if reply.get("thread_id"):
                    self.store.adopt_thread(attempt["dispatch_id"], reply["thread_id"])
                self.update(attempt["dispatch_id"], status, **fields)
            except Exception as error:
                current = self.store.lookup("runtime_works", work["id"])
                if current["state"] == "claimed":
                    self.update(attempt["dispatch_id"], "failed", reason=getattr(error, "code", type(error).__name__))
                elif current["state"] in {"dispatching", "accepted"}:
                    self.update(attempt["dispatch_id"], "dispatch_unknown", reason=type(error).__name__)
                elif current["state"] == "running":
                    self.update(attempt["dispatch_id"], "execution_unknown", reason=type(error).__name__)
        return {"registered": registered, "dispatches": self.dispatch_count, "shadow": False}

    def progress(self, work):
        attempt = self.store.lookup("runtime_attempts", work["dispatch_id"])
        binding = self.store.lookup("runtime_bindings", work["node"]["binding"])
        if work["state"] in {"result_saved", "committed"}:
            try:
                self.publish(work, attempt, binding)
            except GateError as error:
                self.update(attempt["dispatch_id"], "needs_user", reason=error.code)
            return
        host = self.hosts.get(binding["host_kind"])
        if host is None:
            return
        try:
            observation = host.observe(binding, attempt)
        except Exception:
            return  # Keep unresolved ledger; never resend here.
        status = observation.get("status")
        if observation.get("thread_id"):
            try:
                binding = self.store.adopt_thread(attempt["dispatch_id"], observation["thread_id"])
            except GateError as error:
                self.update(attempt["dispatch_id"], "needs_user", reason=error.code)
                return
        if status == "result_saved":
            try:
                self.store.assert_dispatch(self.context(attempt, binding), binding["role"])
                if binding["host_kind"] != "desktop" and not attempt.get("agent_received"):
                    # CLI is read-only: executor owns all effectful operations.
                    self.store.begin_dispatch(self.context(attempt, binding), binding["role"], execution_observed=True)
                elif binding["host_kind"] == "desktop" and not attempt.get("agent_received"):
                    raise GateError("desktop_begin_receipt_required")
                self.store.save_result(attempt["dispatch_id"], observation["result"], instance_id=self.instance_id, context=self.context(attempt, binding), role=binding["role"])
                self.update(attempt["dispatch_id"], "result_saved", turn_id=observation.get("turn_id"), turn_ended=observation.get("turn_ended", False), usage=observation.get("usage"))
            except GateError as error:
                self.update(attempt["dispatch_id"], "needs_user", reason=error.code)
        elif status == "running":
            if binding["host_kind"] != "desktop" and not attempt.get("agent_received"):
                self.store.begin_dispatch(self.context(attempt, binding), binding["role"], execution_observed=True)
            elif work["state"] != "running":
                self.update(attempt["dispatch_id"], "running", turn_id=observation.get("turn_id"))
        elif status in {"failed", "needs_user"} and work["state"] not in UNCERTAIN:
            self.update(attempt["dispatch_id"], status, reason=observation.get("reason", "host_execution_failed"))
        timeout = work["node"].get("run_timeout_ms")
        if timeout and self.c.clock_ms() >= attempt.get("sent_at_ms", attempt["created_at_ms"]) + timeout:
            latest = self.store.lookup("runtime_works", work["id"])
            if latest["state"] in {"accepted", "running"}:
                self.update(attempt["dispatch_id"], "execution_unknown", reason="runtime_execution_timeout")

    def reconcile_result(self, dispatch_id):
        """Inspect one original execution, then consume its saved result only."""
        attempt = self.store.lookup("runtime_attempts", dispatch_id)
        work = self.store.lookup("runtime_works", attempt["work_id"])
        binding = self.store.lookup("runtime_bindings", work["node"]["binding"])
        host = self.hosts.get(binding["host_kind"])
        if binding["host_kind"] not in {"cli", "fake"} or host is None:
            raise GateError("cli_execution_evidence_required")
        observation = host.observe(binding, attempt)
        if (observation.get("status") != "result_saved" or observation.get("turn_ended") is not True
                or observation.get("thread_id") != binding.get("thread_id")
                or observation.get("result", {}).get("dispatch_id") != dispatch_id):
            raise GateError("completed_original_cli_result_required")
        if work["state"] == "needs_user":
            self.store.reopen_cli_result(self.context(attempt, binding), binding["role"], self.instance_id,
                evidence_sha256=sha(encode(observation["result"]).encode("utf-8")))
        elif work["state"] not in {"accepted", "running", "execution_unknown", "dispatch_unknown", "result_saved", "committed", "done"}:
            raise GateError("runtime_result_repair_not_applicable")
        if work["state"] != "done":
            self.progress(self.store.lookup("runtime_works", work["id"]))
            latest = self.store.lookup("runtime_works", work["id"])
            if latest["state"] in {"result_saved", "committed"}:
                self.progress(latest)
        final = self.store.lookup("runtime_works", work["id"])
        return {"status": "committed" if final["state"] == "done" else "rejected", "dispatch_id": dispatch_id,
                "work_state": final["state"], "reason": final.get("reason"), "model_resends": 0,
                "meaning": "original_result_only_professional_opinions_preserved"}

    def publish(self, work, attempt, binding):
        with self.c.connect() as db:
            self.c.gate(self.c.controls(db), work["scope_ids"], work["intended_uses"])
            plan = self.store.get(db, "runtime_plans", work["workflow_id"])
            if not plan["enabled"] or not binding["authorized"]:
                raise GateError("runtime_authorization_inactive")
        path = Path(attempt["result_path"])
        if not path.resolve().is_relative_to(self.c.meta_root.resolve()) or sha(path.read_bytes()) != attempt["result_sha256"]:
            raise GateError("runtime_result_changed")
        result = json.loads(path.read_text(encoding="utf-8"))
        if work["node"].get("handling_attention") and result["intents"]:
            raise GateError("runtime_attention_must_be_read_only")
        if not set(work["node"].get("required_intents", [])) <= {i.get("action") for i in result["intents"] if isinstance(i, dict)}:
            raise GateError("runtime_required_intent_missing")
        context = self.context(attempt, binding)
        session = self.c.bind_local_operator(binding["role"], dispatch=context)
        output_path = "artifacts/runtime/" + attempt["dispatch_id"] + ".txt"
        intents = []
        for original in result["intents"]:
            intent = dict(original)
            if intent.get("action") == "deliver":
                if intent.get("path") != "$output":
                    raise GateError("runtime_output_path_token_required")
                intent["path"] = output_path
            intents.append(intent)
        if intents and not result["output"] and any(i.get("action") == "deliver" for i in intents):
            raise GateError("empty_artifact")
        materialize_output(self.c, session, work["node"], result["output"], output_path,
                           assert_current=lambda: self.store.assert_dispatch(context, binding["role"]))
        receipts = []
        for index, intent in enumerate(intents):
            # A stable prior ticket is always consulted before any new request.
            attempt = self.store.lookup("runtime_attempts", attempt["dispatch_id"])
            keys = dict(attempt.get("publish_keys", {}))
            key = keys.get(str(index))
            prior = self.api.saved_intent(session, intent, request_key=key) if key else {"status": "not_committed"}
            if prior["status"] == "committed":
                receipts.append(prior)
                continue
            self.store.assert_dispatch(context, binding["role"])
            epoch_key = attempt["dispatch_id"] + ":intent:" + str(index) + ":epoch:" + str(attempt["claim_epoch"])
            if key != epoch_key:
                key = epoch_key
                keys[str(index)] = key
                self.update(attempt["dispatch_id"], "result_saved", publish_keys=keys)
            receipt = self.api.do(session, intent, request_key=key)
            if receipt["status"] != "committed":
                raise GateError(receipt.get("problem", "runtime_publication_rejected"))
            receipts.append(receipt)
            self.c.checkpoint("runtime_after_publish")
        completion = work["node"].get("completion", "business" if intents else "result")
        if completion == "business" and not receipts:
            raise GateError("runtime_business_receipt_required")
        if completion not in {"business", "result"}:
            raise GateError("invalid_runtime_completion")
        if not intents:
            self.store.assert_dispatch(context, binding["role"])
        self.update(attempt["dispatch_id"], "done", business_receipts=receipts, completed_at_ms=self.c.clock_ms())

    def run(self, *, max_seconds=None, stop_when_done=False, ready_path=None):
        started = time.monotonic()
        delay = 1
        try:
            ready = self.start()
            if ready_path:
                path = Path(ready_path)
                path.write_text(encode({**ready, "started_at_ms": self.c.clock_ms()}), encoding="utf-8")
            while max_seconds is None or time.monotonic() - started < max_seconds:
                try:
                    outcome = self.tick()
                    state = self.store.status()
                except sqlite3.OperationalError as error:
                    if not any(word in str(error).lower() for word in ("locked", "busy")):
                        raise
                    # A transient SQLite lock must not kill the project
                    # companion. Resume from durable state; never resend here.
                    self.wakeup.wait(min(5, delay))
                    self.wakeup.clear()
                    delay = min(30, delay * 2)
                    continue
                problems = any(not w["node"].get("handling_attention") and w["state"] in
                               {"failed", "needs_user", "host_unavailable", "dispatch_unknown", "execution_unknown"}
                               for w in state["works"])
                effective = [w for w in state["works"] if not (w["node"].get("handling_attention") and w["state"] == "blocked" and not problems)]
                if stop_when_done and effective and all(w["state"] in TERMINAL for w in effective):
                    break
                # Uncertain/failed professional work is never resent. Keep the
                # program alive to deliver its one planned AG0 attention task;
                # one workflow must not silently stop the project companion.
                pending = [w for w in state["works"] if w["state"] in {"ready", "accepted", "running"}]
                delay = 1 if pending or outcome["registered"]["created"] else min(30, delay * 2)
                deadlines = [w["node"]["deadline_ms"] for w in state["works"] if "node" in w and w["state"] not in TERMINAL and w["node"].get("deadline_ms")]
                wait = min(delay, max(.05, (min(deadlines) - self.c.clock_ms()) / 1000)) if deadlines else delay
                self.wakeup.wait(wait)
                self.wakeup.clear()
        finally:
            if self.started:
                self.store.release_supervisor(self.instance_id)
            for host in self.hosts.values():
                host.close()
        return self.store.status()
