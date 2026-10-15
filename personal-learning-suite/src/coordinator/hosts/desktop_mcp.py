"""Installed Codex App Tools over stdio MCP, using inherited caller identity.

No credentials, session-log reads, private IPC, or fabricated host metadata.
No send is retried: an interrupted send remains unknown until reconciled.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading
import time

from . import attempt_directory, dispatch_prompt, save_json, structured_result


class MCPError(RuntimeError):
    """Only a safe error category is surfaced, never raw host diagnostics."""


class MCPRejected(MCPError):
    pass


def discover_app_tools_server(env: dict | None = None) -> Path:
    """Find installed manifests instead of fixing a plugin version in source."""
    env = os.environ if env is None else env
    codex_home = Path(env.get("CODEX_HOME") or Path(env.get("USERPROFILE") or Path.home()) / ".codex")
    candidates = []
    for manifest in (codex_home / "plugins" / "cache").glob("*/codex-app-tools/*/.codex-plugin/plugin.json"):
        try:
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        server = manifest.parent.parent / "server.mjs"
        if metadata.get("name") == "codex-app-tools" and server.is_file():
            version = str(metadata.get("version", server.parent.name))
            parts = tuple(int(n) for n in re.findall(r"\d+", version))
            candidates.append((parts, server.stat().st_mtime_ns, str(server), server))
    if not candidates:
        raise MCPError("app_tools_not_installed")
    return max(candidates)[-1]


def _node_runtime(env: dict) -> str:
    paths = [env.get("CODEX_MCP_NODE_PATH"), env.get("CODEX_BROWSER_USE_NODE_PATH")]
    if env.get("CODEX_ELECTRON_RESOURCES_PATH"):
        paths.append(str(Path(env["CODEX_ELECTRON_RESOURCES_PATH"]) / "cua_node/bin/node.exe"))
    if env.get("CODEX_CLI_PATH"):
        paths.append(str(Path(env["CODEX_CLI_PATH"]).parent / "cua_node/bin/node.exe"))
    if env.get("USERPROFILE"):
        paths.append(str(Path(env["USERPROFILE"]) / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"))
    for path in paths:
        if path and Path(path).is_file():
            return path
    runtime = shutil.which("node", path=env.get("PATH"))
    if not runtime:
        raise MCPError("node_runtime_unavailable")
    return runtime


class StdioMCPClient:
    """One pending request, bounded waits, permanently closed after timeout/EOF.

    ``process`` can be a fake stdio process in tests. This class never logs raw
    requests, inherited environment, stderr, or remote error bodies.
    """
    def __init__(self, command=None, *, env=None, timeout=20.0, process=None, process_factory=None):
        self.timeout = timeout
        self._lock = threading.Lock()
        self._queue = queue.Queue()
        self._seq = 0
        self._closed = False
        if process is None:
            process_factory = subprocess.Popen if process_factory is None else process_factory
            options = {"stdin": subprocess.PIPE, "stdout": subprocess.PIPE,
                       "stderr": subprocess.DEVNULL, "text": True, "encoding": "utf-8",
                       "errors": "replace", "env": env}
            if os.name == "nt":
                options["creationflags"] = subprocess.CREATE_NO_WINDOW
            process = process_factory(command, **options)
        self.process = process
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    self._queue.put(row)
        except (OSError, ValueError):
            pass  # Closing the transport can interrupt its reader.
        finally:
            self._queue.put(None)

    def _send(self, row):
        if self._closed:
            raise MCPError("mcp_closed")
        try:
            self.process.stdin.write(json.dumps(row, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
        except (OSError, ValueError) as exc:
            self.close()
            raise MCPError("mcp_write_failed") from exc

    def notify(self, method, params=None):
        with self._lock:
            self._send({"jsonrpc": "2.0", "method": method, **({"params": params} if params else {})})

    def call(self, method, params, *, timeout=None):
        timeout = self.timeout if timeout is None else timeout
        started = time.monotonic()
        if not self._lock.acquire(timeout=max(0.0, timeout)):
            raise TimeoutError("mcp_request_busy")
        try:
            self._seq += 1
            request_id = self._seq
            self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
            deadline = started + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self.close()
                    raise TimeoutError("mcp_request_timeout")
                try:
                    row = self._queue.get(timeout=remaining)
                except queue.Empty as exc:
                    self.close()
                    raise TimeoutError("mcp_request_timeout") from exc
                if row is None:
                    self.close()
                    raise MCPError("mcp_eof")
                if row.get("id") != request_id:
                    continue
                if "error" in row:
                    raise MCPRejected("mcp_request_rejected")
                if "result" not in row:
                    raise MCPError("mcp_invalid_response")
                return row["result"]
        finally:
            self._lock.release()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
        for stream in (self.process.stdin, self.process.stdout):
            try:
                stream.close()
            except (AttributeError, OSError, ValueError):
                pass


def _payload(result):
    if not isinstance(result, dict):
        raise MCPError("invalid_tool_result")
    if result.get("isError"):
        raise MCPRejected("host_tool_rejected")
    if isinstance(result.get("structuredContent"), dict):
        return result["structuredContent"]
    parts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
    try:
        parsed = json.loads("\n".join(parts))
    except ValueError as exc:
        raise MCPError("unstructured_tool_result") from exc
    if not isinstance(parsed, dict):
        raise MCPError("invalid_tool_result")
    return parsed


def _state(snapshot, thread_id):
    thread = snapshot.get("thread", {})
    if thread.get("id") != thread_id:
        raise MCPError("host_thread_mismatch")
    turns = snapshot.get("turns", [])
    status = thread.get("status", {})
    status = {"type": status} if isinstance(status, str) else status
    kind = str(status.get("type", "")).lower().replace("_", "")
    flags = {str(x).lower().replace("_", "") for x in status.get("activeFlags", [])}
    needs = {"needsuser", "needsapproval", "waitingforapproval", "waitingforuserinput",
             "waitingonapproval", "waitingonuserinput", "awaitingapproval", "awaitinguserinput"}
    if kind in needs or flags & needs:
        state = "needs_user"
    elif kind == "active" or any(t.get("status") in {"inProgress", "running"} for t in turns):
        state = "active"
    elif kind == "idle":
        state = "idle"
    else:
        state = "unavailable"
    return {"state": state, "thread_id": thread_id, "last_turn_id": turns[0].get("id") if turns else None}


class DesktopMCPHost:
    def __init__(self, run_root=None, *, transport=None, env=None, timeout=20.0):
        self.run_root = Path(run_root).resolve() if run_root is not None else None
        self.env = dict(os.environ if env is None else env)
        self.current_thread_id = self.env.get("CODEX_THREAD_ID")
        self.timeout = timeout
        self._transport = transport
        self._initialized = False
        self._closed = False
        self._catalog = {}
        self._dispatches = {}
        self._dispatch_lock = threading.Lock()
        self._connect_lock = threading.Lock()

    def _connect(self):
        with self._connect_lock:
            self._initialize()

    def _initialize(self):
        if self._closed:
            raise MCPError("host_closed")
        if self._initialized:
            return
        if not self.current_thread_id:
            raise MCPError("current_thread_context_missing")
        if self._transport is None:
            server = discover_app_tools_server(self.env)
            self._transport = StdioMCPClient([_node_runtime(self.env), str(server)], env=self.env, timeout=self.timeout)
        self._transport.call("initialize", {"protocolVersion": "2024-11-05",
                             "clientInfo": {"name": "coordinator-host", "version": "1.0"}, "capabilities": {}})
        self._transport.notify("notifications/initialized")
        catalog = self._transport.call("tools/list", {})
        self._catalog = {t["name"]: t for t in catalog.get("tools", [])}
        for suffix in ("read_thread", "send_message_to_thread"):
            self._tool_name(suffix)
        # Prove the actual inherited caller can access itself before any binding.
        current = self._tool("read_thread", {"threadId": self.current_thread_id, "turnLimit": 1,
                                            "includeOutputs": False, "maxOutputCharsPerItem": 0})
        _state(current, self.current_thread_id)
        self._initialized = True

    def _tool_name(self, suffix):
        names = [n for n in self._catalog if n == suffix or n.endswith("__" + suffix)]
        if len(names) != 1:
            raise MCPError("required_host_tool_unavailable")
        return names[0]

    def _tool(self, suffix, arguments):
        name = self._tool_name(suffix)
        schema = self._catalog[name].get("inputSchema", {})
        supported = schema.get("properties", {})
        if supported:
            arguments = {k: v for k, v in arguments.items() if k in supported}
        return _payload(self._transport.call("tools/call", {"name": name, "arguments": arguments,
                        "_meta": {"codexThreadId": self.current_thread_id}}))

    def _read(self, binding, *, outputs=False):
        self._connect()
        thread_id = binding.get("thread_id")
        if not isinstance(thread_id, str) or not thread_id:
            raise MCPError("bound_thread_missing")
        arguments = {"threadId": thread_id, "turnLimit": 10 if outputs else 1,
                     "includeOutputs": outputs, "maxOutputCharsPerItem": 20000 if outputs else 0}
        if binding.get("host_id"):
            arguments["hostId"] = binding["host_id"]
        snapshot = self._tool("read_thread", arguments)
        _state(snapshot, thread_id)
        return snapshot

    def inspect(self, binding):
        try:
            return _state(self._read(binding), binding.get("thread_id"))
        except (MCPError, TimeoutError, OSError):
            return {"state": "unavailable", "thread_id": binding.get("thread_id"),
                    "last_turn_id": None, "problem": "desktop_host_unavailable"}

    def dispatch(self, binding, prompt, dispatch_id):
        with self._dispatch_lock:
            if dispatch_id in self._dispatches:
                return dict(self._dispatches[dispatch_id])
            directory = attempt_directory(self.run_root, dispatch_id) if self.run_root else None
            if directory and directory.is_dir():
                try:
                    previous = json.loads((directory / "attempt.json").read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    previous = {"status": "dispatch_unknown", "dispatch_id": dispatch_id,
                                "thread_id": binding.get("thread_id"), "problem": "existing_attempt_unresolved"}
                self._dispatches[dispatch_id] = previous
                return dict(previous)
            state = self.inspect(binding)
            if state["state"] != "idle":
                return {"status": "needs_user" if state["state"] == "needs_user" else "host_unavailable",
                        "dispatch_id": dispatch_id, **state, "problem": "target_not_idle"}
            receipt = {"status": "dispatch_unknown", "dispatch_id": dispatch_id,
                       "thread_id": binding["thread_id"], "before_turn_id": state["last_turn_id"]}
            if directory:
                directory.mkdir(parents=True, exist_ok=False)
                receipt["attempt_path"] = str(directory / "attempt.json")
                save_json(directory / "attempt.json", receipt)
            # Once this boundary is crossed, every ambiguous failure prohibits resend.
            self._dispatches[dispatch_id] = receipt
            arguments = {"threadId": binding["thread_id"],
                         "prompt": dispatch_prompt(prompt, dispatch_id, allow_persisted_result=True)}
            if binding.get("host_id"):
                arguments["hostId"] = binding["host_id"]
            try:
                response = self._tool("send_message_to_thread", arguments)
                actual = response.get("threadId", response.get("thread_id"))
                if actual != binding["thread_id"]:
                    receipt["problem"] = "send_receipt_thread_mismatch"
                else:
                    receipt["status"] = "accepted"
            except MCPRejected:
                receipt.update(status="failed", problem="host_send_rejected")
            except (MCPError, TimeoutError, OSError):
                receipt["problem"] = "host_send_outcome_unknown"
            if directory:
                save_json(directory / "attempt.json", receipt)
            return dict(receipt)

    def observe(self, binding, attempt):
        attempt = {**attempt, **attempt.get("host_receipt", {})}
        base = {"dispatch_id": attempt.get("dispatch_id"), "thread_id": binding.get("thread_id")}
        if attempt.get("thread_id") and attempt["thread_id"] != base["thread_id"]:
            return {**base, "status": "execution_unknown", "problem": "attempt_thread_mismatch"}
        try:
            snapshot = self._read(binding, outputs=True)
            state = _state(snapshot, binding["thread_id"])
        except (MCPError, TimeoutError, OSError):
            return {**base, "status": "host_unavailable", "problem": "desktop_host_unavailable"}
        if state["state"] == "needs_user":
            return {**base, "status": "needs_user", "last_turn_id": state["last_turn_id"]}
        for turn in snapshot.get("turns", []):
            if turn.get("id") == attempt.get("before_turn_id"):
                continue
            for item in turn.get("items", []):
                if item.get("type") not in {"agentMessage", "agent_message"}:
                    continue
                result = structured_result(item.get("text"), base["dispatch_id"])
                if result and item.get("phase") in {None, "final", "final_answer"}:
                    # A structured final message can be saved while its turn settles.
                    return {**base, "status": "result_saved", "turn_id": turn.get("id"),
                            "turn_ended": turn.get("status") in {"completed", "failed", "interrupted"},
                            "result": result}
        if state["last_turn_id"] == attempt.get("before_turn_id") or not snapshot.get("turns"):
            return {**base, "status": "accepted", "last_turn_id": state["last_turn_id"]}
        return {**base, "status": "execution_unknown", "last_turn_id": state["last_turn_id"],
                "problem": "no_correlated_dispatch_result"}

    def close(self):
        self._closed = True
        if self._transport is not None:
            self._transport.close()
