"""Host fault tests use fake stdio transports/processes; no real model or chat."""
from copy import deepcopy
import json
import os
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
import unittest

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
from coordinator.hosts import CLIResumeHost, DesktopMCPHost, StdioMCPClient
from coordinator.hosts.desktop_mcp import MCPError, MCPRejected, discover_app_tools_server


def snapshot(thread_id="target", state="idle", turn_id="old", turns=None, flags=None):
    return {"thread": {"id": thread_id, "status": {"type": state, "activeFlags": flags or []}},
            "turns": turns if turns is not None else [{"id": turn_id, "status": "completed", "items": []}]}


def final(dispatch_id="d1", output="A professional result."):
    return {"dispatch_id": dispatch_id, "output": output, "intents": []}


class FakeTools:
    def __init__(self, target=None, send_error=None, current=None):
        self.current = current or snapshot("caller")
        self.target = target or snapshot()
        self.send_error = send_error
        self.calls = []
        self.closed = False

    def notify(self, method):
        self.calls.append((method, {}))

    def call(self, method, params):
        self.calls.append((method, deepcopy(params)))
        if method == "initialize":
            return {"protocolVersion": "2024-11-05"}
        if method == "tools/list":
            return {"tools": [{"name": name, "inputSchema": {"properties": {
                "threadId": {}, "hostId": {}, "prompt": {}, "turnLimit": {},
                "includeOutputs": {}, "maxOutputCharsPerItem": {}}}}
                for name in ("read_thread", "send_message_to_thread")]}
        name = params["name"]
        if name == "send_message_to_thread":
            if self.send_error:
                raise self.send_error
            value = {"threadId": params["arguments"]["threadId"]}
        else:
            value = self.current if params["arguments"]["threadId"] == "caller" else self.target
        return {"content": [{"type": "text", "text": json.dumps(value)}]}

    def close(self):
        self.closed = True

    def sends(self):
        return [p for m, p in self.calls if m == "tools/call" and p["name"] == "send_message_to_thread"]


class DesktopHostTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=SUITE / "tests", prefix="host-desktop-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.binding = {"thread_id": "target", "host_id": "local"}

    def host(self, transport):
        host = DesktopMCPHost(self.root, transport=transport, env={"CODEX_THREAD_ID": "caller"})
        self.addCleanup(host.close)
        return host

    def test_access_uses_inherited_caller_metadata_for_every_tool(self):
        transport = FakeTools()
        host = self.host(transport)
        self.assertEqual(host.inspect(self.binding)["state"], "idle")
        reply = host.dispatch(self.binding, "Decide from the fixed evidence.", "d1")
        self.assertEqual(reply["status"], "accepted")
        self.assertEqual(reply["before_turn_id"], "old")
        calls = [p for method, p in transport.calls if method == "tools/call"]
        self.assertEqual(calls[0]["arguments"]["threadId"], "caller")
        self.assertTrue(all(p["_meta"] == {"codexThreadId": "caller"} for p in calls))
        self.assertNotIn("model", transport.sends()[0]["arguments"])
        self.assertIn("Coordinator dispatch_id: d1", transport.sends()[0]["arguments"]["prompt"])

    def test_missing_or_wrong_current_thread_never_sends(self):
        for env, transport in (({}, FakeTools()), ({"CODEX_THREAD_ID": "caller"}, FakeTools(current=snapshot("wrong")))):
            with self.subTest(env=env):
                host = DesktopMCPHost(transport=transport, env=env)
                self.addCleanup(host.close)
                self.assertEqual(host.inspect(self.binding)["state"], "unavailable")
                self.assertEqual(host.dispatch(self.binding, "Task", "d1")["status"], "host_unavailable")
                self.assertFalse(transport.sends())

    def test_idle_active_needs_user_and_unknown_are_distinct(self):
        transport = FakeTools()
        host = self.host(transport)
        for state, flags, expected in (("idle", [], "idle"), ("active", [], "active"),
                                       ("active", ["waitingForApproval"], "needs_user"),
                                       ("active", ["waitingOnApproval"], "needs_user"),
                                       ("active", ["waitingOnUserInput"], "needs_user"),
                                       ("idle", ["waitingForUserInput"], "needs_user"),
                                       ("unexpected", [], "unavailable")):
            with self.subTest(state=state, flags=flags):
                transport.target = snapshot(state=state, flags=flags)
                self.assertEqual(host.inspect(self.binding)["state"], expected)
                if expected != "idle":
                    host.dispatch(self.binding, "Task", "d1")
        self.assertFalse(transport.sends())

    def test_persisted_desktop_result_protocol_is_respected(self):
        transport = FakeTools()
        host = self.host(transport)
        host.dispatch(self.binding, "Persist result using coordinate_runtime.py result; then a normal final.", "d1")
        prompt = transport.sends()[0]["arguments"]["prompt"]
        self.assertIn("after successful persistence a normal user-facing final response is allowed", prompt)

    def test_wrong_target_thread_blocks_dispatch(self):
        transport = FakeTools(target=snapshot("another"))
        host = self.host(transport)
        self.assertEqual(host.inspect(self.binding)["state"], "unavailable")
        self.assertEqual(host.dispatch(self.binding, "Task", "d1")["status"], "host_unavailable")
        self.assertFalse(transport.sends())

    def test_timeout_does_not_retry_in_process_or_after_restart(self):
        transport = FakeTools(send_error=TimeoutError("no reply"))
        host = self.host(transport)
        first = host.dispatch(self.binding, "Task", "d1")
        self.assertEqual(first["status"], "dispatch_unknown")
        self.assertEqual(host.dispatch(self.binding, "Changed task", "d1"), first)
        replacement = FakeTools()
        restarted = self.host(replacement)
        self.assertEqual(restarted.dispatch(self.binding, "Task", "d1")["status"], "dispatch_unknown")
        self.assertEqual(len(transport.sends()), 1)
        self.assertFalse(replacement.sends())

    def test_explicit_send_rejection_is_failure_not_unknown(self):
        transport = FakeTools(send_error=MCPRejected("host rejected"))
        host = self.host(transport)
        self.assertEqual(host.dispatch(self.binding, "Task", "d1")["status"], "failed")
        host.dispatch(self.binding, "Task", "d1")
        self.assertEqual(len(transport.sends()), 1)

    def test_unrelated_new_turn_never_proves_completion(self):
        transport = FakeTools()
        host = self.host(transport)
        attempt = host.dispatch(self.binding, "Task", "d1")
        transport.target = snapshot(turns=[{"id": "new", "status": "completed", "items": [
            {"type": "userMessage", "text": "Coordinator dispatch_id: d1"},
            {"type": "agentMessage", "phase": "final_answer", "text": json.dumps(final("other"))}]}])
        self.assertEqual(host.observe(self.binding, attempt)["status"], "execution_unknown")

    def test_correlated_final_is_saved_and_same_old_turn_is_not(self):
        transport = FakeTools()
        host = self.host(transport)
        attempt = host.dispatch(self.binding, "Task", "d1")
        self.assertEqual(host.observe(self.binding, attempt)["status"], "accepted")
        message = {"type": "agentMessage", "phase": "final_answer", "text": json.dumps(final())}
        transport.target = snapshot(turns=[{"id": "old", "status": "completed", "items": [message]}])
        self.assertEqual(host.observe(self.binding, attempt)["status"], "accepted")
        transport.target = snapshot(turns=[{"id": "new", "status": "completed", "items": [message]}])
        observed = host.observe(self.binding, attempt)
        self.assertEqual(observed["status"], "result_saved")
        self.assertEqual(observed["result"], final())
        self.assertTrue(observed["turn_ended"])
        self.assertEqual(observed["turn_id"], "new")

    def test_discovery_uses_installed_manifest_versions(self):
        for version in ("0.1.6", "0.12.0"):
            plugin = self.root / "plugins/cache/vendor/codex-app-tools" / version
            (plugin / ".codex-plugin").mkdir(parents=True)
            (plugin / ".codex-plugin/plugin.json").write_text(json.dumps({"name": "codex-app-tools", "version": version}))
            (plugin / "server.mjs").write_text("// fake server")
        self.assertEqual(discover_app_tools_server({"CODEX_HOME": str(self.root)}).parent.name, "0.12.0")


class QueueLines:
    def __init__(self):
        self.queue = queue.Queue()
    def __iter__(self):
        while True:
            value = self.queue.get()
            if value is None:
                return
            yield value
    def close(self):
        self.queue.put(None)


class FakeInput:
    def __init__(self, process):
        self.process = process
    def write(self, value):
        request = json.loads(value)
        self.process.requests.append(request)
        if self.process.respond:
            self.process.respond(request, self.process)
    def flush(self):
        pass
    def close(self):
        pass


class FakeStdioProcess:
    def __init__(self, respond=None):
        self.respond = respond
        self.requests = []
        self.stdout = QueueLines()
        self.stdin = FakeInput(self)
        self.returncode = None
    def poll(self):
        return self.returncode
    def terminate(self):
        self.returncode = -15
        self.stdout.close()
    def kill(self):
        self.terminate()
    def wait(self, timeout=None):
        return self.returncode
    def reply(self, request, result):
        self.stdout.queue.put(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}) + "\n")


class StdioClientTests(unittest.TestCase):
    def test_timeout_closes_transport_and_cannot_send_again(self):
        process = FakeStdioProcess()
        client = StdioMCPClient(process=process, timeout=0.02)
        with self.assertRaises(TimeoutError):
            client.call("tools/call", {})
        with self.assertRaises(MCPError):
            client.call("tools/call", {})
        self.assertEqual(len(process.requests), 1)
        self.assertIsNotNone(process.returncode)

    def test_eof_has_bounded_failure(self):
        process = FakeStdioProcess(lambda request, p: p.stdout.close())
        client = StdioMCPClient(process=process, timeout=0.05)
        with self.assertRaisesRegex(MCPError, "mcp_eof"):
            client.call("tools/list", {})

    def test_foreign_response_and_notification_are_not_accepted(self):
        def respond(request, process):
            process.stdout.queue.put(json.dumps({"id": 9999, "result": {"wrong": True}}) + "\n")
            process.stdout.queue.put(json.dumps({"method": "notifications/message", "params": {}}) + "\n")
            process.reply(request, {"correct": request["id"]})
        process = FakeStdioProcess(respond)
        client = StdioMCPClient(process=process)
        self.addCleanup(client.close)
        self.assertEqual(client.call("tools/list", {}), {"correct": 1})

    def test_concurrent_calls_allow_only_one_pending_request(self):
        pending, maximum = 0, 0
        guard = threading.Lock()
        def respond(request, process):
            nonlocal pending, maximum
            with guard:
                pending += 1
                maximum = max(maximum, pending)
            def complete():
                nonlocal pending
                with guard:
                    pending -= 1
                process.reply(request, {"id": request["id"]})
            threading.Timer(0.01, complete).start()
        client = StdioMCPClient(process=FakeStdioProcess(respond), timeout=0.2)
        self.addCleanup(client.close)
        results = []
        threads = [threading.Thread(target=lambda: results.append(client.call("tools/list", {}))) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=1)
        self.assertEqual(maximum, 1)
        self.assertEqual(sorted(r["id"] for r in results), [1, 2])

    def test_remote_error_body_is_not_exposed(self):
        def respond(request, process):
            process.stdout.queue.put(json.dumps({"id": request["id"], "error": {"message": "secret-token"}}) + "\n")
        client = StdioMCPClient(process=FakeStdioProcess(respond))
        self.addCleanup(client.close)
        with self.assertRaises(MCPRejected) as failure:
            client.call("tools/call", {})
        self.assertNotIn("secret-token", str(failure.exception))


class FakeCLIProcess:
    def __init__(self, command, options, pid):
        self.command = command
        self.options = options
        self.pid = pid
        self.prompt = options["stdin"].read().decode("utf-8")
        self.output = os.fdopen(os.dup(options["stdout"].fileno()), "wb")
        self.returncode = None
        self.finished = threading.Event()
    def emit(self, *rows):
        for row in rows:
            self.output.write((json.dumps(row) + "\n").encode())
        self.output.flush()
    def finish(self, code=0):
        if self.returncode is None:
            self.output.close()
            self.returncode = code
            self.finished.set()
    def poll(self):
        return self.returncode
    def wait(self):
        self.finished.wait()
        return self.returncode


class CLIHostTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=SUITE / "tests", prefix="host-cli-test-")
        self.root = Path(temporary.name)
        self.addCleanup(temporary.cleanup)
        self.processes = []
        def factory(command, **options):
            process = FakeCLIProcess(command, options, 7000 + len(self.processes))
            self.processes.append(process)
            return process
        self.factory = factory
        self.host = CLIResumeHost(self.root, cli_path=sys.executable, process_factory=factory,
                                  env={"CODEX_THREAD_ID": "caller", "PROFILE_DEFAULT": "inherited"})
        self.addCleanup(self.host.close)
        self.addCleanup(self.finish_processes)
        self.binding = {"id": "research", "generation": 1, "thread_id": None, "cwd": str(self.root)}

    def finish_processes(self):
        for process in self.processes:
            process.finish()
        for attempt in self.host._attempts.values():
            deadline = time.monotonic() + 1
            while not Path(attempt["exit_path"]).exists() and time.monotonic() < deadline:
                time.sleep(0.001)

    def completed(self, attempt, dispatch_id=None, thread_id="thread-1"):
        process = self.processes[-1]
        process.emit({"type": "thread.started", "thread_id": thread_id},
                     {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(final(dispatch_id or attempt["dispatch_id"]))}},
                     {"type": "turn.completed", "turn_id": "turn-" + attempt["dispatch_id"], "usage": {"output_tokens": 12}})
        process.finish()
        return self.host.observe({**self.binding, "thread_id": thread_id}, attempt)

    def test_dispatch_is_async_hidden_read_only_and_inherits_defaults(self):
        attempt = self.host.dispatch(self.binding, "Complete the professional task.", "d1")
        self.assertEqual(attempt["status"], "accepted")
        self.assertIsNone(self.processes[0].poll())
        self.assertEqual(attempt["pid"], 7000)
        self.assertTrue(attempt["start_handle"])
        command = self.processes[0].command
        self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
        self.assertIn("--output-schema", command)
        self.assertNotIn("--model", command)
        self.assertNotIn("--ignore-user-config", command)
        self.assertNotIn("--ephemeral", command)
        self.assertEqual(self.processes[0].options["env"]["PROFILE_DEFAULT"], "inherited")
        self.assertIn("Coordinator dispatch_id: d1", self.processes[0].prompt)
        if os.name == "nt":
            import subprocess
            self.assertEqual(self.processes[0].options["creationflags"], subprocess.CREATE_NO_WINDOW)
        self.assertEqual(self.host.observe(self.binding, attempt)["status"], "accepted")

    def test_thread_started_and_correlated_completion_preserve_identity(self):
        attempt = self.host.dispatch(self.binding, "Task", "d1")
        self.processes[-1].emit({"type": "thread.started", "thread_id": "thread-1"})
        observed = self.host.observe(self.binding, attempt)
        self.assertEqual(observed["status"], "running")
        self.assertEqual(observed["thread_id"], "thread-1")
        observed = self.completed(attempt)
        self.assertEqual(observed["status"], "result_saved")
        self.assertEqual(observed["thread_id"], "thread-1")
        self.assertEqual(observed["result"], final())
        self.assertTrue(observed["turn_ended"])

    def test_started_thread_blocks_stale_none_binding_but_not_other_roles(self):
        attempt = self.host.dispatch(self.binding, "Task", "d1")
        self.processes[-1].emit({"type": "thread.started", "thread_id": "thread-1"})
        state = self.host.inspect(self.binding)
        self.assertEqual(state["state"], "active")
        self.assertEqual(state["thread_id"], "thread-1")
        self.assertEqual(self.host.dispatch(self.binding, "Another task", "d2")["status"], "host_unavailable")
        other = {**self.binding, "id": "review"}
        self.assertEqual(self.host.inspect(other)["state"], "idle")
        self.assertEqual(self.host.dispatch(other, "Independent review", "d3")["status"], "accepted")
        self.assertEqual(len(self.processes), 2)
        self.assertEqual(self.host.observe(self.binding, attempt)["status"], "running")

    def test_completed_persistent_thread_is_resumed_with_new_turn(self):
        first = self.host.dispatch(self.binding, "First task", "d1")
        self.completed(first)
        binding = {**self.binding, "thread_id": "thread-1"}
        self.assertEqual(self.host.inspect(binding)["state"], "idle")
        second = self.host.dispatch(binding, "Second task", "d2")
        self.assertEqual(second["status"], "accepted")
        command = self.processes[-1].command
        self.assertIn("resume", command)
        self.assertEqual(command[-2:], ["thread-1", "-"])
        self.assertLess(command.index("--sandbox"), command.index("resume"))
        self.assertEqual(self.completed(second)["status"], "result_saved")

    def test_other_roles_do_not_block_resuming_completed_bound_thread(self):
        first = self.host.dispatch(self.binding, "Research", "research-1")
        self.completed(first, thread_id="research-thread")
        review_binding = {**self.binding, "id": "review", "thread_id": None}
        review = self.host.dispatch(review_binding, "Review", "review-1")
        self.completed(review, thread_id="review-thread")
        research_binding = {**self.binding, "thread_id": "research-thread"}
        self.assertEqual(self.host.inspect(research_binding)["state"], "idle")
        self.assertEqual(self.host.dispatch(research_binding, "Materials", "research-2")["status"], "accepted")

    def test_same_dispatch_is_not_spawned_twice_or_after_restart(self):
        attempt = self.host.dispatch(self.binding, "Task", "d1")
        self.assertEqual(self.host.dispatch(self.binding, "Changed task", "d1"), attempt)
        restarted = CLIResumeHost(self.root, cli_path=sys.executable, process_factory=self.factory)
        self.addCleanup(restarted.close)
        self.assertEqual(restarted.dispatch(self.binding, "Task", "d1"), attempt)
        self.assertEqual(len(self.processes), 1)
        self.assertEqual(restarted.observe(self.binding, attempt)["status"], "execution_unknown")

    def test_completed_turn_recovers_without_old_python_exit_watcher(self):
        attempt = self.host.dispatch(self.binding, "Task", "d1")
        process = self.processes[-1]
        process.emit({"type": "thread.started", "thread_id": "thread-1"},
                     {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(final())}},
                     {"type": "turn.completed", "turn_id": "turn-d1"})
        binding = {**self.binding, "thread_id": "thread-1"}
        self.assertFalse(Path(attempt["exit_path"]).exists())
        self.assertEqual(self.host.inspect(binding)["state"], "active")
        restarted = CLIResumeHost(self.root, cli_path=sys.executable, process_factory=self.factory)
        self.addCleanup(restarted.close)
        observed = restarted.observe(binding, attempt)
        self.assertEqual(observed["status"], "result_saved")
        self.assertTrue(observed["turn_ended"])
        self.assertFalse(observed["process_exited"])
        self.assertEqual(restarted.inspect(binding)["state"], "idle")

    def test_wrong_thread_and_wrong_dispatch_result_are_unknown(self):
        attempt = self.host.dispatch(self.binding, "Task", "d1")
        observed = self.completed(attempt, dispatch_id="other")
        self.assertEqual(observed["status"], "execution_unknown")
        wrong = self.host.observe({**self.binding, "thread_id": "not-thread-1"}, {**attempt, "thread_id": "thread-1"})
        self.assertEqual(wrong["problem"], "attempt_thread_mismatch")

    def test_failed_turn_is_failed_and_zero_exit_without_completion_is_unknown(self):
        attempt = self.host.dispatch(self.binding, "Task", "d1")
        self.processes[-1].emit({"type": "thread.started", "thread_id": "thread-1"},
                               {"type": "turn.failed", "error": {"message": "private-diagnostic"}})
        self.processes[-1].finish(1)
        observed = self.host.observe(self.binding, attempt)
        self.assertEqual(observed["status"], "failed")
        self.assertNotIn("private-diagnostic", json.dumps(observed))
        other = {**self.binding, "id": "other", "thread_id": None}
        attempt2 = self.host.dispatch(other, "Task", "d2")
        self.assertEqual(attempt2["status"], "accepted")
        self.processes[-1].finish(0)
        self.assertEqual(self.host.observe(other, attempt2)["status"], "execution_unknown")

    def test_pid_without_matching_start_handle_is_not_exit_evidence(self):
        path = self.root / "exit.json"
        attempt = {"dispatch_id": "d1", "thread_id": "thread-1", "pid": 7000,
                   "start_handle": "original", "process_started_at": "2026-10-15T00:00:00Z", "exit_path": str(path)}
        path.write_text(json.dumps({"returncode": 1, "pid": 7000, "start_handle": "replacement",
                                   "process_started_at": attempt["process_started_at"]}), encoding="utf-8")
        self.assertEqual(self.host.observe({"thread_id": "thread-1"}, attempt)["status"], "execution_unknown")
        path.write_text(json.dumps({"returncode": 1, "pid": 7000, "start_handle": "original",
                                   "process_started_at": attempt["process_started_at"]}), encoding="utf-8")
        self.assertEqual(self.host.observe({"thread_id": "thread-1"}, attempt)["status"], "failed")

    def test_cli_evidence_is_only_read_inside_its_owned_root(self):
        foreign = tempfile.TemporaryDirectory(dir=SUITE / "tests", prefix="host-foreign-test-")
        self.addCleanup(foreign.cleanup)
        path = Path(foreign.name) / "not-host-evidence.jsonl"
        path.write_text(json.dumps({"type": "thread.started", "thread_id": "thread-1"}) + "\n", encoding="utf-8")
        observed = self.host.observe(self.binding, {"dispatch_id": "d1", "stdout_path": str(path)})
        self.assertEqual(observed["status"], "execution_unknown")
        self.assertIsNone(observed["thread_id"])

    def test_unrecognized_existing_thread_is_not_assumed_idle(self):
        binding = {**self.binding, "thread_id": "unowned-thread"}
        self.assertEqual(self.host.inspect(binding)["state"], "unavailable")
        self.assertEqual(self.host.dispatch(binding, "Task", "d1")["status"], "host_unavailable")
        self.assertFalse(self.processes)

    def test_close_detaches_without_killing_pending_process(self):
        attempt = self.host.dispatch(self.binding, "Task", "d1")
        self.host.close()
        self.assertIsNone(self.processes[-1].poll())
        self.assertEqual(self.host.observe(self.binding, attempt)["status"], "accepted")

    def test_invalid_dispatch_path_does_not_spawn(self):
        with self.assertRaises(ValueError):
            self.host.dispatch(self.binding, "Task", "../escape")
        self.assertFalse(self.processes)


if __name__ == "__main__":
    unittest.main()
