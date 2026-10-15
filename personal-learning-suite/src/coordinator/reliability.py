"""Batch-three bounded waits, transactional events and explicit recovery inspection.

No background scheduler, automatic adoption, semantic re-review or process liveness
inference is performed. Event consumers own their cursor and poll key boundaries.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time

from .workspace import Coordinator, GateError, encode, identifier, ref, scopes

RELIABILITY_VERSION = "tac-reliability/0.1.0"


class ReliableCoordinator(Coordinator):
    def __init__(self, root, control_gate=None, *, clock_ms=None, lock_timeout=3):
        super().__init__(root, control_gate)
        self.clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        if not isinstance(lock_timeout, (int, float)) or not 0 < lock_timeout <= 60:
            raise GateError("invalid_lock_timeout")
        self.lock_timeout = lock_timeout
        self.failpoint = None

    def checkpoint(self, name):
        if self.failpoint is not None:
            self.failpoint(name)

    def actions(self):
        return super().actions() | {"refresh", "upgrade"}

    @contextmanager
    def connect(self, *, allow_legacy=False):
        with super().connect() as db:
            marker = db.execute("SELECT value FROM meta WHERE key='reliability_version'").fetchone()
            if marker is None and not allow_legacy:
                raise GateError("reliability_upgrade_required")
            if marker is not None and marker[0] != RELIABILITY_VERSION:
                raise GateError("unsupported_reliability_version")
            yield db

    def initialize(self, *, evidence_kind):
        result = super().initialize(evidence_kind=evidence_kind)
        with self.connect(allow_legacy=True) as db:
            db.execute("BEGIN IMMEDIATE")
            self.install(db)
            self.checkpoint("before_extension_commit")
            db.commit()
        return {**result, "reliability_version": RELIABILITY_VERSION}

    @staticmethod
    def install(db):
        db.execute("CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT, operation_id TEXT NOT NULL, body TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS operation_contexts(id TEXT PRIMARY KEY, body TEXT NOT NULL)")
        db.execute("INSERT INTO meta VALUES('reliability_version',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (RELIABILITY_VERSION,))

    def execute(self, session, action, request):
        if action != "upgrade":
            return super().execute(session, action, request)
        # Upgrade is the only explicitly permitted mutation on a legacy workspace.
        return self.upgrade(session, request)

    def upgrade(self, session, request):
        try:
            if self.role(session) != "AG0":
                raise GateError("ag0_upgrade_required")
            operation = identifier(request["operation_id"])
            expected = request["expected_state_revision"]
            if type(expected) is not int or expected < 0 or set(request) != {"operation_id", "expected_state_revision"}:
                raise GateError("invalid_upgrade_request")
            with self.connect(allow_legacy=True) as db:
                db.execute("BEGIN IMMEDIATE")
                control = self.controls(db)
                if any(control[key] for key in ("paused_ids", "deleted_ids", "restrictions")):
                    raise GateError("upgrade_controls_unavailable")
                revision = self.state_revision(db)
                from .workspace import sha
                request_hash = sha(encode({"action": "upgrade", "role": "AG0", "operation_id": operation}).encode("utf-8"))
                prior = db.execute("SELECT request_hash,body FROM operations WHERE id=?", (operation,)).fetchone()
                if prior:
                    if prior[0] != request_hash:
                        raise GateError("operation_id_reused")
                    return json.loads(prior[1])
                if expected != revision:
                    return {"status": "conflict", "state_revision": revision, "reasons": ["state_revision_conflict"]}
                self.install(db)
                self.checkpoint("before_extension_commit")
                if encode(self.controls(db)) != encode(control):
                    raise GateError("control_changed_during_commit")
                response = {"status": "committed", "operation_id": operation, "state_revision": revision + 1,
                            "reliability_version": RELIABILITY_VERSION}
                db.execute("UPDATE meta SET value=? WHERE key='state_revision'", (str(revision + 1),))
                self.save_operation(db, operation, request_hash, response, "AG0", "upgrade", request, control)
                self.emit(db, operation, {"kind": "workspace_upgraded", "scope_ids": [], "intended_uses": ["coordination"]})
                self.checkpoint("before_commit")
                db.commit()
                self.checkpoint("after_commit")
                return response
        except GateError as error:
            return {"status": "rejected", "reasons": [error.code]}
        except (OSError, sqlite3.Error, RuntimeError) as error:
            return {"status": "commit_status_unknown", "operation_id": request.get("operation_id"), "reasons": [type(error).__name__]}

    def context(self, db, request):
        """Metadata-only scope closure; safe before a commit-receipt body is shown."""
        ids, uses = set(), {request.get("intended_use", "coordination")}
        pending = []
        for name in ("id", "task_id"):
            if request.get(name):
                ids.add(request[name])
        for name in ("ref", "target_ref", "old_ref", "new_ref"):
            if request.get(name):
                pending.append(ref(request[name]))
        for member in request.get("members", []):
            pending.append(ref(member["ref"]))
            uses.add(member["intended_use"])
        for item in request.get("inputs", []):
            ids.add(item["id"])
            if item.get("producer_task_id"):
                ids.add(item["producer_task_id"])
        if request.get("output"):
            ids.add(request["output"]["id"])
        if request.get("task_id"):
            task = self.get(db, "tasks", request["task_id"])
            uses.add(task["intended_use"])
            pending += task["snapshot"]
            if task.get("target_ref"):
                pending.append(task["target_ref"])
            if task.get("result_ref"):
                pending.append(task["result_ref"])
            if task["output"]:
                ids.add(task["output"]["id"])
            for item in task["inputs"]:
                ids.add(item["id"])
                if item.get("producer_task_id"):
                    ids.add(item["producer_task_id"])
        seen = set()
        while pending:
            item = ref(pending.pop())
            key = (item["id"], item["revision"])
            if key in seen:
                continue
            seen.add(key)
            artifact = self.artifact(db, item)
            ids.add(item["id"])
            uses.add(artifact["intended_use"])
            pending += artifact["basis_refs"] + self.recheck_inputs(db, artifact)
        return {"scope_ids": sorted(ids), "intended_uses": sorted(uses)}

    def save_operation(self, db, operation, request_hash, response, role, action, request, control):
        super().save_operation(db, operation, request_hash, response, role, action, request, control)
        context = {**self.context(db, request), "role": role, "action": action}
        db.execute("INSERT INTO operation_contexts VALUES(?,?)", (operation, encode(context)))

    def emit(self, db, operation, body):
        db.execute("INSERT INTO events(operation_id,body) VALUES(?,?)", (operation, encode(body)))

    def after_action(self, db, role, action, request, result, control):
        if action != "refresh" or result.get("changed", True):
            context = self.context(db, request)
            self.emit(db, request["operation_id"], {**context, "kind": action, "by": role,
                      "task_id": result.get("task_id"), "phase": result.get("phase"), "ref": result.get("ref"),
                      "bundle_id": result.get("bundle_id"), "next_owner": result.get("next_owner")})
        self.settle_waiters(db, request["operation_id"], control)
        if result.get("task_id"):
            final = self.get(db, "tasks", result["task_id"])
            result["phase"] = final["phase"]
            if final["phase"] == "blocked":
                result.update(reason=final["stop_reason"], next_owner=final["next_owner"])

    def _register(self, db, role, request, control):
        after = [i for i in request.get("inputs", []) if i.get("policy") == "after_task"]
        normalized = json.loads(encode(request))
        if after:
            timeout = request.get("wait_timeout_ms")
            if type(timeout) is not int or not 0 < timeout <= 86_400_000:
                raise GateError("bounded_wait_timeout_required")
            for item in after:
                producer = self.get(db, "tasks", identifier(item["producer_task_id"]))
                if producer["id"] == request["id"] or not producer["output"] or producer["output"]["id"] != item["id"]:
                    raise GateError("wait_producer_output_mismatch")
                if item["intended_use"] != producer["intended_use"] or not set(scopes(item["scope"])) <= set(producer["scope"]):
                    raise GateError("wait_scope_expansion")
            # Validate common fields with the base gate, then preserve the real policy.
            for item in normalized["inputs"]:
                if item["policy"] == "after_task":
                    item["policy"] = "adopted"
        result = super()._register(db, role, normalized, control)
        if after:
            task = self.get(db, "tasks", request["id"])
            task.update(inputs=request["inputs"], wait_timeout_ms=request["wait_timeout_ms"])
            db.execute("UPDATE tasks SET body=? WHERE id=?", (encode(task), task["id"]))
        return result

    def wait_report(self, db, task):
        if task.get("wait_deadline_ms") is not None and task.get("wait_resolved_at_ms") is None and self.clock_ms() >= task["wait_deadline_ms"]:
            return {"phase": "blocked", "reason": "wait_timeout", "waiting_for": task.get("waiting_for", [])}
        waiting = []
        for item in task["inputs"]:
            if item["policy"] != "after_task":
                continue
            producer = self.get(db, "tasks", item["producer_task_id"])
            if producer["phase"] in {"failed", "cancelled", "blocked"}:
                return {"phase": "blocked", "reason": "upstream_" + producer["phase"], "producer_task_id": producer["id"]}
            exact = producer.get("result_ref")
            if exact is None:
                waiting.append({"producer_task_id": producer["id"], "reason": "producer_not_submitted"})
                continue
            available = True
            for part in item["scope"]:
                pointer = db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?",
                                     (item["id"], item["intended_use"], part)).fetchone()
                if pointer is not None and pointer[0] > exact["revision"]:
                    return {"phase": "blocked", "reason": "required_result_superseded", "producer_task_id": producer["id"]}
                available &= pointer is not None and pointer[0] == exact["revision"]
            if not available:
                waiting.append({"producer_task_id": producer["id"], "reason": "required_result_not_adopted", "ref": exact})
        if waiting and task.get("wait_deadline_ms") is not None and self.clock_ms() >= task["wait_deadline_ms"]:
            return {"phase": "blocked", "reason": "wait_timeout", "waiting_for": waiting}
        return {"phase": "waiting", "waiting_for": waiting} if waiting else {"phase": "ready"}

    def apply_wait(self, db, task, report):
        if report["phase"] == "blocked":
            task.update(phase="blocked", stop_reason=report["reason"], next_owner=task["requester"],
                        next_trigger="explicit_replan_or_new_task", waiting_for=report.get("waiting_for", []))
        elif report["phase"] == "waiting":
            task.update(phase="waiting", waiting_for=report["waiting_for"], next_owner=task["assignee"], next_trigger="required_result_or_deadline")
        else:
            task.setdefault("wait_resolved_at_ms", self.clock_ms())
            task.update(phase="registered", waiting_for=[],
                        next_owner=task["assignee"], next_trigger="start_with_fixed_inputs")
        db.execute("UPDATE tasks SET body=? WHERE id=?", (encode(task), task["id"]))

    def _input(self, db, item):
        if item["policy"] != "after_task":
            return super()._input(db, item)
        producer = self.get(db, "tasks", item["producer_task_id"])
        return ref(producer["result_ref"])

    def _start(self, db, role, request, control):
        task = self.get(db, "tasks", request["task_id"])
        if role != task["assignee"]:
            raise GateError("task_assignee_required")
        if task["phase"] not in {"registered", "waiting"}:
            raise GateError("task_not_registered")
        if any(i["policy"] == "after_task" for i in task["inputs"]):
            task["acceptance"] = {"status": "accepted", "by": role}
            if "wait_deadline_ms" not in task:
                task["wait_deadline_ms"] = self.clock_ms() + task["wait_timeout_ms"]
            report = self.wait_report(db, task)
            self.apply_wait(db, task, report)
            if report["phase"] != "ready":
                return {"task_id": task["id"], **report, "wait_deadline_ms": task["wait_deadline_ms"], "next_owner": task["next_owner"]}
        return super()._start(db, role, request, control)

    def _refresh(self, db, role, request, control):
        task = self.get(db, "tasks", request["task_id"])
        if role not in {task["requester"], task["assignee"]} or task["phase"] != "waiting":
            raise GateError("waiting_task_required")
        report = self.wait_report(db, task)
        changed = report["phase"] != "waiting" or report.get("waiting_for") != task.get("waiting_for")
        self.apply_wait(db, task, report)
        return {"task_id": task["id"], **report, "changed": changed, "next_owner": task["next_owner"]}

    def settle_waiters(self, db, operation, control):
        count = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        # Registration references already existing producer tasks, so wait edges
        # are acyclic. Each pass retires or readies a task; propagation is bounded.
        for _ in range(count + 1):
            changed = False
            tasks = [json.loads(row[0]) for row in db.execute("SELECT body FROM tasks ORDER BY id")]
            for task in tasks:
                if task["phase"] not in {"registered", "waiting"} or not any(i["policy"] == "after_task" for i in task["inputs"]):
                    continue
                context = self.context(db, {"task_id": task["id"]})
                try:
                    self.gate(control, context["scope_ids"], context["intended_uses"])
                except GateError:
                    continue
                report = self.wait_report(db, task)
                if report["phase"] == "blocked" or task["phase"] == "waiting" and report["phase"] == "ready":
                    self.apply_wait(db, task, report)
                    self.emit(db, operation, {**context, "kind": "wait_" + report["phase"], "task_id": task["id"],
                              "reason": report.get("reason"), "next_owner": task["next_owner"]})
                    changed = True
            if not changed:
                break

    def _finish(self, db, role, request, control):
        task = self.get(db, "tasks", request["task_id"])
        if task["phase"] in {"waiting", "blocked"}:
            if role not in {task["requester"], task["assignee"]} or request["phase"] not in {"failed", "cancelled"} or not request.get("reason", "").strip():
                raise GateError("task_finish_not_allowed")
            task.update(phase=request["phase"], stop_reason=request["reason"])
            db.execute("UPDATE tasks SET body=? WHERE id=?", (encode(task), task["id"]))
            return {"task_id": task["id"], "phase": task["phase"]}
        return super()._finish(db, role, request, control)

    def _adopt(self, db, role, request, control):
        if "expected_pointers" in request:
            expected = request["expected_pointers"]
            if not isinstance(expected, list):
                raise GateError("explicit_pointer_preconditions_required")
            keys = {(ref(m["ref"])["id"], m["intended_use"], part) for m in request["members"] for part in scopes(m["scope"])}
            seen = set()
            for item in expected:
                key = (identifier(item["id"]), identifier(item["intended_use"]), item["scope"])
                if key in seen or key not in keys or item["revision"] is not None and (type(item["revision"]) is not int or item["revision"] < 1):
                    raise GateError("invalid_pointer_preconditions")
                seen.add(key)
                row = db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?", key).fetchone()
                actual = row[0] if row else None
                if actual != item["revision"]:
                    raise GateError("pointer_conflict")
            if seen != keys:
                raise GateError("incomplete_pointer_preconditions")
        return super()._adopt(db, role, request, control)

    def events(self, session, *, after_sequence=0, limit=100):
        self.role(session)
        if type(after_sequence) is not int or after_sequence < 0 or type(limit) is not int or not 1 <= limit <= 1000:
            raise GateError("invalid_event_cursor")
        with self.connect() as db:
            db.execute("BEGIN")
            control = self.controls(db)
            rows = db.execute("SELECT sequence,operation_id,body FROM events WHERE sequence>? ORDER BY sequence LIMIT ?", (after_sequence, limit)).fetchall()
            visible = []
            for row in rows:
                body = json.loads(row["body"])
                try:
                    self.gate(control, body["scope_ids"], body["intended_uses"])
                except GateError:
                    continue
                visible.append({"sequence": row["sequence"], "operation_id": row["operation_id"], **body})
            return {"status": "ok", "events": visible, "next_sequence": rows[-1]["sequence"] if rows else after_sequence,
                    "meaning": "local_pull_events_no_external_messages"}

    def operation(self, session, operation_id):
        role = self.role(session)
        with self.connect() as db:
            db.execute("BEGIN")
            control = self.controls(db)
            row = db.execute("SELECT body FROM operations WHERE id=?", (identifier(operation_id),)).fetchone()
            if row is None:
                return {"status": "not_committed", "operation_id": operation_id, "state_revision": self.state_revision(db),
                        "meaning": "not_observed_at_snapshot_not_proof_of_stopped_worker"}
            context = db.execute("SELECT body FROM operation_contexts WHERE id=?", (operation_id,)).fetchone()
            if context is None:
                raise GateError("legacy_operation_requires_original_request")
            context = json.loads(context[0])
            if role not in {"AG0", context["role"]}:
                raise GateError("operation_receipt_role_scope")
            self.gate(control, context["scope_ids"], context["intended_uses"])
            return {"status": "committed", "receipt": json.loads(row[0]),
                    "meaning": "historical_commit_receipt_not_current_usability"}

    def status(self, session):
        # Base schema remains readable; extension installation is never implicit.
        with self.connect(allow_legacy=True) as db:
            marker = db.execute("SELECT value FROM meta WHERE key='reliability_version'").fetchone()
        if marker is None:
            base = Coordinator(self.root, self.control_gate)
            result = base.status(base.bind_local_operator(self.role(session)))
            return {**result, "reliability_upgrade_required": True}
        result = super().status(session)
        return result

    def decorate_status(self, db, result):
        for task in result["tasks"]:
            if task["phase"] == "waiting":
                current = self.wait_report(db, task)
                task.update(effective_phase=current["phase"], wait_status=current,
                            refresh_needed=current["phase"] != "waiting")
                if current["phase"] == "blocked":
                    task["next_owner"] = task["requester"]
        return {**result, "reliability_version": RELIABILITY_VERSION}

    def recover(self, session, *, scan_roots=()):
        if self.role(session) != "AG0":
            raise GateError("ag0_recovery_inspection_required")
        with self.connect() as db:
            db.execute("BEGIN")
            control = self.controls(db)
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                return {"status": "blocked", "reason": "database_integrity_failure", "automatic_repair": False}
            registered = [json.loads(r[0]) for r in db.execute("SELECT body FROM artifacts")]
            issues, known = [], {a["path"] for a in registered}
            for artifact in registered:
                try:
                    self.preflight(db, {"ref": ref(artifact), "intended_use": artifact["intended_use"]}, control)
                except GateError as error:
                    if error.code not in {"deleted_scope", "paused_scope", "restricted_use"}:
                        issues.append({"ref": ref(artifact), "reason": error.code})
            unregistered = []
            scan_allowed = not any(control[key] for key in ("deleted_ids", "restrictions"))
            if scan_allowed:
                for relative in scan_roots:
                    if not isinstance(relative, str) or not relative or ":" in relative or "\\" in relative or any(p in {"", ".", ".."} for p in relative.split("/")):
                        raise GateError("unsafe_recovery_scan_root")
                    root = (self.root / relative).resolve()
                    if not root.is_relative_to(self.root) or root.is_relative_to(self.meta_root):
                        raise GateError("unsafe_recovery_scan_root")
                    for path in root.rglob("*") if root.is_dir() else []:
                        if path.is_file() and path.resolve().is_relative_to(self.root) and not path.resolve().is_relative_to(self.meta_root):
                            value = path.relative_to(self.root).as_posix()
                            if value not in known:
                                unregistered.append(value)
            task_ids = []
            for row in db.execute("SELECT body FROM tasks"):
                task = json.loads(row[0])
                if task["phase"] != "running":
                    continue
                context = self.context(db, {"task_id": task["id"]})
                try:
                    self.gate(control, context["scope_ids"], context["intended_uses"])
                except GateError:
                    continue
                task_ids.append(task["id"])
            return {"status": "ok", "integrity": integrity, "state_revision": self.state_revision(db),
                    "artifact_issues": issues, "unregistered_files": sorted(set(unregistered)),
                    "scan_performed": scan_allowed and bool(scan_roots), "running_task_ids": task_ids,
                    "next_action": "query_operation_then_resume_or_explicit_finish", "automatic_adoption": False,
                    "automatic_file_deletion": False, "meaning": "inspection_not_process_liveness_or_repair"}
