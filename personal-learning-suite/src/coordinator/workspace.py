"""Batch-two file coordination gates, independent of fixture-only LearningStore.

File contents remain at immutable, caller-owned version paths. SQLite owns only
coordination metadata, receipts and per-use/scope adopted pointers. Role sessions
are issued by a trusted local operator: they are NOT host identity authentication.
Existing learning workspaces require an explicit, current external-control gate.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import threading
from typing import Callable

from runtime.contract_rules import load_definition

VERSION = "tac-workspace/0.1.0"
ROLES = {"AG0", "AG1", "AG2", "AG3"}
TYPES = {"GoalSpec", "SourceFragment", "MaterialUse", "ActivitySpec", "MethodConfig", "PlanCommitment"}


class GateError(ValueError):
    def __init__(self, code, detail=""):
        super().__init__(detail or code)
        self.code = code


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", value):
        raise GateError("invalid_id")
    return value


def scopes(value):
    if not isinstance(value, list) or not value or any(not isinstance(s, str) or not s.strip() for s in value):
        raise GateError("explicit_scope_required")
    if len(set(value)) != len(value):
        raise GateError("duplicate_scope")
    return sorted(value)


def ref(value):
    if not isinstance(value, dict) or type(value.get("revision")) is not int or value["revision"] < 1:
        raise GateError("exact_ref_required")
    return {"id": identifier(value.get("id")), "revision": value["revision"]}


def overlaps(left, right):
    return left is None or right is None or "*" in left or "*" in right or bool(set(left) & set(right))


@dataclass(frozen=True)
class Session:
    role: str
    issuer: object
    dispatch: dict | None = None
    runtime_setup: bool = False


class FileControlGate:
    """Read a manually/host-derived projection, pinned to its actual source files.

    The projection declares controls explicitly. It cannot interpret Markdown or
    authenticate its author. A changed source invalidates it rather than silently
    reusing a stale all-clear projection.
    """
    def __init__(self, root, projection):
        self.root = Path(root).resolve()
        self.path = Path(projection).resolve()

    def __call__(self):
        data = json.loads(self.path.read_text(encoding="utf-8-sig"))
        source_refs = data.get("source_refs")
        if not isinstance(source_refs, list) or not source_refs:
            raise GateError("control_source_refs_required")
        for item in source_refs:
            path = (self.root / item["path"]).resolve()
            if not path.is_relative_to(self.root) or not path.is_file():
                raise GateError("control_source_unavailable")
            if sha(path.read_bytes()) != item["sha256"]:
                raise GateError("control_projection_stale")
        return data


class Coordinator:
    def __init__(self, root, control_gate: Callable | None = None):
        self.root = Path(root).resolve()
        self.meta_root = self.root / ".coordinator"
        self.db_path = self.meta_root / "records.sqlite3"
        self.control_gate = control_gate
        self._issuer = object()
        self.lock_timeout = 3
        # Read views share one connection only while nested on the same thread.
        # This avoids opening a second reader behind a writer waiting for the
        # outer reader's SHARED lock. Effectful callers keep separate handles.
        self.read_only = False
        self._read_connections = threading.local()
        self._connection_contexts = threading.local()
        self.definition = load_definition()

    def bind_local_operator(self, role, *, dispatch=None, runtime_setup=False):
        if role not in ROLES:
            raise GateError("unknown_role")
        return Session(role, self._issuer, dispatch, runtime_setup)

    def role(self, session):
        if not isinstance(session, Session) or session.issuer is not self._issuer or session.role not in ROLES:
            raise GateError("unbound_session")
        return session.role

    @contextmanager
    def connect(self):
        if not self.db_path.is_file():
            raise GateError("workspace_not_initialized")
        if self.read_only:
            active = getattr(self._read_connections, "connection", None)
            if active is not None:
                yield active
                return
            # mode=ro still observes the current database and normal locks;
            # immutable=1 would silently skip live coordination changes.
            db = sqlite3.connect(self.db_path.as_uri() + "?mode=ro", uri=True,
                                 timeout=self.lock_timeout, isolation_level=None)
        else:
            db = sqlite3.connect(self.db_path, timeout=self.lock_timeout, isolation_level=None)
        db.row_factory = sqlite3.Row
        stack = getattr(self._connection_contexts, "stack", None)
        if stack is None:
            stack = self._connection_contexts.stack = []
        try:
            db.execute("PRAGMA foreign_keys=ON")
            if self.read_only:
                db.execute("PRAGMA query_only=ON")
                self._read_connections.connection = db
            else:
                db.execute("PRAGMA synchronous=FULL")
            stack.append(db)
            yield db
        finally:
            if stack and stack[-1] is db:
                stack.pop()
            if getattr(self._read_connections, "connection", None) is db:
                del self._read_connections.connection
            db.close()

    @contextmanager
    def validation_connection(self):
        """Use the caller's current snapshot for nested SELECT-only checks.

        Validation cannot open a fresh reader behind a writer waiting on the
        caller's existing read transaction. Ordinary effectful ``connect``
        contexts remain independent; only explicit validation uses this handle.
        """
        stack = getattr(self._connection_contexts, "stack", ())
        if stack:
            yield stack[-1]
        else:
            with self.connect() as db:
                yield db

    def initialize(self, *, evidence_kind):
        if evidence_kind not in {"synthetic_demo", "real_file_metadata"}:
            raise GateError("explicit_evidence_kind_required")
        if self.meta_root.exists():
            raise GateError("coordinator_already_exists")
        if evidence_kind == "real_file_metadata" and self.control_gate is None:
            raise GateError("external_control_gate_required")
        # Validate the external source before creating any metadata.
        if self.control_gate is not None:
            self.validate_control(self.control_gate())
        self.root.mkdir(parents=True, exist_ok=True)
        self.meta_root.mkdir()
        db = sqlite3.connect(self.db_path)
        try:
            db.executescript("""
                CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE tasks(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE artifacts(id TEXT NOT NULL, revision INTEGER NOT NULL, path TEXT UNIQUE NOT NULL,
                    body TEXT NOT NULL, PRIMARY KEY(id, revision));
                CREATE TABLE receipts(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE rechecks(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE adopted(id TEXT NOT NULL, intended_use TEXT NOT NULL, scope TEXT NOT NULL,
                    revision INTEGER NOT NULL, PRIMARY KEY(id, intended_use, scope));
                CREATE TABLE bundles(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE operations(id TEXT PRIMARY KEY, request_hash TEXT NOT NULL, body TEXT NOT NULL);
            """)
            db.executemany("INSERT INTO meta VALUES(?,?)", [("version", VERSION), ("state_revision", "0"),
                ("evidence_kind", evidence_kind), ("authority_mode", "local_operator_attested"),
                ("shared_protocol", self.definition["protocol_version"])])
            db.commit()
        finally:
            db.close()
        return {"status": "committed", "state_revision": 0, "evidence_kind": evidence_kind,
                "authority_mode": "local_operator_attested"}

    @staticmethod
    def validate_control(control):
        if not isinstance(control, dict) or type(control.get("state_revision")) is not int or control["state_revision"] < 0:
            raise GateError("invalid_control_revision")
        for field in ("paused_ids", "deleted_ids", "restrictions"):
            if not isinstance(control.get(field), list):
                raise GateError("explicit_controls_required")
        for field in ("paused_ids", "deleted_ids"):
            if any(not isinstance(item, str) or not item for item in control[field]):
                raise GateError("invalid_controls")
        for item in control["restrictions"]:
            scopes(item.get("scope_ids"))
            scopes(item.get("intended_uses"))
        return control

    def controls(self, db):
        mode = db.execute("SELECT value FROM meta WHERE key='evidence_kind'").fetchone()[0]
        if self.control_gate is None:
            if mode != "synthetic_demo":
                raise GateError("external_control_gate_required")
            return {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []}
        return self.validate_control(self.control_gate())

    def gate(self, control, ids, uses):
        if "*" in control["deleted_ids"] or set(ids) & set(control["deleted_ids"]):
            raise GateError("deleted_scope")
        if "*" in control["paused_ids"] or set(ids) & set(control["paused_ids"]):
            raise GateError("paused_scope")
        for item in control["restrictions"]:
            if overlaps(item["scope_ids"], list(ids)) and overlaps(item["intended_uses"], list(uses)):
                raise GateError("restricted_use")

    @staticmethod
    def state_revision(db):
        return int(db.execute("SELECT value FROM meta WHERE key='state_revision'").fetchone()[0])

    @staticmethod
    def get(db, table, key):
        row = db.execute(f"SELECT body FROM {table} WHERE id=?", (identifier(key),)).fetchone()
        if row is None:
            raise GateError("record_not_found", f"{table}: {key}")
        return json.loads(row[0])

    def artifact(self, db, value):
        value = ref(value)
        row = db.execute("SELECT body FROM artifacts WHERE id=? AND revision=?", (value["id"], value["revision"])).fetchone()
        if row is None:
            raise GateError("version_not_found")
        return json.loads(row[0])

    def file_info(self, path):
        if not isinstance(path, str) or not path or "\\" in path or ":" in path or "\0" in path:
            raise GateError("unsafe_artifact_path")
        if any(part in {"", ".", ".."} for part in path.split("/")):
            raise GateError("unsafe_artifact_path")
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root) or target.is_relative_to(self.meta_root):
            raise GateError("unsafe_artifact_path")
        if not target.is_file():
            raise GateError("artifact_file_unavailable")
        data = target.read_bytes()
        if not data:
            raise GateError("empty_artifact")
        return {"path": path, "sha256": sha(data), "bytes": len(data)}

    def verify_file(self, artifact):
        actual = self.file_info(artifact["path"])
        if actual["sha256"] != artifact["sha256"] or actual["bytes"] != artifact["bytes"]:
            raise GateError("artifact_fingerprint_changed")

    def closure(self, db, value):
        artifact = self.artifact(db, value)
        refs = [ref(artifact)] + [ref(item) for item in artifact["basis_refs"]]
        return refs

    def preflight(self, db, request, control):
        ids, uses = set(), {request.get("intended_use", "coordination")}
        file_infos = []
        pinned = []
        for field in ("ref", "target_ref", "old_ref", "new_ref"):
            if field in request:
                pinned += self.closure(db, request[field])
        for item in request.get("members", []):
            pinned += self.closure(db, item["ref"])
            uses.add(item["intended_use"])
        if "task_id" in request:
            task = self.get(db, "tasks", request["task_id"])
            ids.add(task["id"])
            uses.add(task["intended_use"])
            for item in task.get("snapshot", []):
                pinned += self.closure(db, item)
                for part in item["scope"]:
                    current = db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?",
                                         (item["id"], item["intended_use"], part)).fetchone()
                    if current is not None:
                        current_ref = {"id": item["id"], "revision": current[0]}
                        if current_ref != ref(item) and overlaps(self.change_scope(db, item, current_ref), [part]):
                            pinned += self.closure(db, current_ref)
            if task.get("target_ref"):
                pinned += self.closure(db, task["target_ref"])
            if task.get("output"):
                ids.add(task["output"]["id"])
        if request.get("output"):
            ids.add(request["output"]["id"])
        for item in request.get("inputs", []):
            ids.add(item["id"])
        # Include current dependency closures before reading any artifact body.
        pending, seen = list(pinned), set()
        while pending:
            item = pending.pop(0)
            exact_key = (item["id"], item["revision"])
            if exact_key in seen:
                continue
            seen.add(exact_key)
            artifact = self.artifact(db, item)
            uses.add(artifact["intended_use"])
            for basis in artifact["basis_refs"]:
                uses.add(basis["intended_use"])
                for scope in basis["scope"]:
                    current = db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?",
                                         (basis["id"], basis["intended_use"], scope)).fetchone()
                    if current:
                        additional = self.closure(db, {"id": basis["id"], "revision": current[0]})
                        pinned += additional
                        pending += additional
        ids.update(r["id"] for r in pinned)
        self.gate(control, ids, uses)
        for item in pinned:
            self.verify_file(self.artifact(db, item))
        if "path" in request:
            file_infos.append(self.file_info(request["path"]))
        return file_infos

    def execute(self, session, action, request):
        """Successful operations are idempotent; rejected requests do not mutate.

        Caller role is bound to the session, never accepted from request fields.
        Global state CAS is intentionally conservative in batch two.
        """
        revision = None
        committed = False
        try:
            role = self.role(session)
            if action not in self.actions():
                raise GateError("unknown_action")
            if not isinstance(request, dict) or any(key in request for key in ("actor", "role", "owner", "binding_status")):
                raise GateError("caller_identity_not_request_data")
            expected = request.get("expected_state_revision")
            if type(expected) is not int or expected < 0:
                raise GateError("expected_state_revision_required")
            operation = identifier(request.get("operation_id"))
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                revision = self.state_revision(db)
                control = self.controls(db)
                self.execution_guard(db, session, action, request, control)
                file_infos = self.preflight(db, request, control)
                # Agent decisions may be prepared before execution. Compare
                # frozen controls and bytes in this same write transaction.
                prepared = request.get("prepared_preconditions")
                if prepared is not None:
                    if not isinstance(prepared, dict) or set(prepared) != {"control", "files"}:
                        raise GateError("invalid_prepared_preconditions")
                    if encode(control) != encode(prepared["control"]):
                        raise GateError("prepared_controls_changed")
                    if file_infos != prepared["files"]:
                        raise GateError("prepared_files_changed")
                body = {key: value for key, value in request.items() if key != "expected_state_revision"}
                request_hash = sha(encode({"action": action, "role": role, "body": body, "files": file_infos}).encode("utf-8"))
                prior = db.execute("SELECT request_hash,body FROM operations WHERE id=?", (operation,)).fetchone()
                if prior:
                    if prior[0] != request_hash:
                        raise GateError("operation_id_reused")
                    db.rollback()
                    return json.loads(prior[1])
                if action != "ack_events" and expected != revision:
                    db.rollback()
                    return {"status": "conflict", "state_revision": revision, "reasons": ["state_revision_conflict"]}
                result = getattr(self, "_" + action)(db, role, request, control)
                self.after_action(db, role, action, request, result, control)
                self.checkpoint("after_action")
                if self.preflight(db, request, control) != file_infos:
                    raise GateError("artifact_changed_during_commit")
                # Re-read external controls before publishing a pointer or receipt.
                if encode(self.controls(db)) != encode(control):
                    raise GateError("control_changed_during_commit")
                if action != "ack_events":
                    revision += 1
                    db.execute("UPDATE meta SET value=? WHERE key='state_revision'", (str(revision),))
                response = {"status": "committed", "state_revision": revision, "operation_id": operation, **result}
                self.save_operation(db, operation, request_hash, response, role, action, request, control)
                self.execution_receipt(db, session, action, request, response)
                self.checkpoint("before_commit")
                db.commit()
                committed = True
                self.checkpoint("after_commit")
                return response
        except GateError as error:
            return {"status": "conflict" if error.code == "pointer_conflict" else "rejected", "state_revision": revision, "reasons": [error.code]}
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, RuntimeError) as error:
            if committed:
                return {"status": "commit_status_unknown", "operation_id": request.get("operation_id"), "reasons": [type(error).__name__]}
            if isinstance(error, sqlite3.Error) and getattr(error, "sqlite_errorcode", 0) & 255 in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
                return {"status": "busy", "state_revision": None, "retryable": True, "reasons": ["database_busy"]}
            return {"status": "not_saved", "state_revision": None, "reasons": [type(error).__name__]}

    def actions(self):
        return {"register", "start", "submit", "confirm", "review", "recheck", "adopt", "finish"}

    def execution_guard(self, db, session, action, request, control):
        # The fence is checked under the very same write lock as publication.
        from .runtime_store import guard_business
        guard_business(self, db, session, action, request, control)

    def execution_receipt(self, db, session, action, request, response):
        from .runtime_store import record_business_receipt
        record_business_receipt(db, session, request, response)

    def checkpoint(self, name):
        """Fault-injection seam; inactive in the ordinary coordinator."""

    def after_action(self, db, role, action, request, result, control):
        """Extension seam within the same transaction as the action."""

    def save_operation(self, db, operation, request_hash, response, role, action, request, control):
        db.execute("INSERT INTO operations VALUES(?,?,?)", (operation, request_hash, encode(response)))

    def _primary_owner(self, kind):
        if kind not in TYPES:
            raise GateError("unsupported_artifact_type")
        # Conservative first-owner route: optional AG0 delegations are not inferred.
        return self.definition["objects"][kind]["owners"][0]

    def _register(self, db, role, request, control):
        task_id = identifier(request["id"])
        if db.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone():
            raise GateError("task_already_registered")
        assignee = request["assignee"]
        kind = request["task_kind"]
        use, scope = identifier(request["intended_use"]), scopes(request["scope"])
        if role != "AG0" and role != assignee:
            raise GateError("task_requester_scope")
        if kind == "production":
            output = request["output"]
            identifier(output["id"])
            if assignee != self._primary_owner(output["type"]):
                raise GateError("professional_owner_required")
            if type(output.get("requires_ag3_review")) is not bool:
                raise GateError("explicit_review_policy_required")
            # Only AG0 can set or relax the review requirement for this first slice.
            if role != "AG0":
                raise GateError("ag0_output_policy_required")
            inputs = request["inputs"]
            if not isinstance(inputs, list):
                raise GateError("explicit_inputs_required")
            for item in inputs:
                identifier(item["id"])
                scopes(item["scope"])
                if item["policy"] not in {"adopted", "exact"}:
                    raise GateError("unsupported_input_policy")
                if item["policy"] == "exact":
                    ref(item)
                identifier(item["intended_use"])
            target = None
        elif kind == "review":
            if assignee != "AG3":
                raise GateError("reviewer_required")
            target = ref(request["target_ref"])
            artifact = self.artifact(db, target)
            if use != artifact["intended_use"] or not set(scope) <= set(artifact["scope"]):
                raise GateError("review_scope_expansion")
            inputs, output = [], None
        else:
            raise GateError("unsupported_task_kind")
        self.gate(control, {task_id} | ({output["id"]} if output else {target["id"]}), {use})
        task = {"id": task_id, "requester": role, "assignee": assignee, "task_kind": kind,
                "scope": scope, "intended_use": use, "inputs": inputs, "output": output,
                "target_ref": target, "phase": "registered", "acceptance": {"status": "proposed"},
                "snapshot": [], "authority_mode": "local_operator_attested"}
        db.execute("INSERT INTO tasks VALUES(?,?)", (task_id, encode(task)))
        return {"task_id": task_id, "phase": "registered"}

    def _input(self, db, item):
        if item["policy"] == "exact":
            return ref(item)
        versions = []
        for scope in item["scope"]:
            row = db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?",
                             (item["id"], item["intended_use"], scope)).fetchone()
            if row is None:
                raise GateError("adopted_input_unavailable")
            versions.append(row[0])
        if len(set(versions)) != 1:
            raise GateError("split_input_versions_requires_explicit_tasks")
        return {"id": item["id"], "revision": versions[0]}

    def active_opinions(self, db, artifact, intended_use, stamp):
        opinions = [json.loads(row[0]) for row in db.execute("SELECT body FROM receipts")]
        opinions = [r for r in opinions if r["target_ref"] == ref(artifact) and r["basis_signature"] == stamp
                    and r["intended_use"] == intended_use]
        retired = {receipt_id for opinion in opinions for receipt_id in opinion["supersedes_receipt_ids"]}
        return opinions, retired

    def check_opinions(self, db, artifact, intended_use, scope):
        stamp, _ = self.basis_status(db, artifact)
        opinions, retired = self.active_opinions(db, artifact, intended_use, stamp)
        if any(r["outcome"] != "supported" and r["id"] not in retired and overlaps(r["scope"], scope) for r in opinions):
            raise GateError("conflicting_professional_receipts")

    def _start(self, db, role, request, control):
        task = self.get(db, "tasks", request["task_id"])
        if role != task["assignee"]:
            raise GateError("task_assignee_required")
        if task["phase"] != "registered":
            raise GateError("task_not_registered")
        snapshot = []
        if task["task_kind"] == "review":
            target = self.artifact(db, task["target_ref"])
            snapshot = target["basis_refs"] + self.recheck_inputs(db, target)
        else:
            for item in task["inputs"]:
                chosen = self._input(db, item)
                artifact = self.artifact(db, chosen)
                snapshot.append({**chosen, "sha256": artifact["sha256"], "scope": item["scope"],
                                 "intended_use": item["intended_use"], "adoption_required": True})
                snapshot += artifact["basis_refs"]
        # Deduplicate exact records without losing per-use or per-scope constraints.
        snapshot = list({encode(item): item for item in snapshot}.values())
        roots = snapshot + ([task["target_ref"]] if task["target_ref"] else [])
        self.preflight(db, {"members": [{"ref": ref(item), "intended_use": task["intended_use"]} for item in roots],
                            "intended_use": task["intended_use"]}, control)
        self.gate(control, {item["id"] for item in snapshot} | ({task["target_ref"]["id"]} if task["target_ref"] else set()),
                  {task["intended_use"]} | {item["intended_use"] for item in snapshot})
        for item in snapshot:
            self.verify_file(self.artifact(db, item))
            if task["task_kind"] == "production":
                self.check_opinions(db, self.artifact(db, item), item["intended_use"], item["scope"])
        if task["task_kind"] == "review":
            self.verify_file(target)
            stamp, issues = self.basis_status(db, target)
            task.update(review_target_fingerprint=target["sha256"], review_basis_signature=stamp,
                        review_input_issues=issues)
        task.update(phase="running", snapshot=snapshot, control_revision_at_start=control["state_revision"],
                    acceptance={"status": "accepted", "by": role})
        db.execute("UPDATE tasks SET body=? WHERE id=?", (encode(task), task["id"]))
        return {"task_id": task["id"], "snapshot": snapshot, "phase": "running"}

    def _submit(self, db, role, request, control):
        task = self.get(db, "tasks", request["task_id"])
        if task["task_kind"] != "production" or task["phase"] != "running":
            raise GateError("running_production_task_required")
        if role != task["assignee"]:
            raise GateError("task_assignee_required")
        output = task["output"]
        existing = db.execute("SELECT body FROM artifacts WHERE id=? ORDER BY revision DESC LIMIT 1", (output["id"],)).fetchone()
        previous = json.loads(existing[0]) if existing else None
        if previous and (previous["type"] != output["type"] or previous["owner"] != role):
            raise GateError("stable_id_type_or_owner_changed")
        revision = previous["revision"] + 1 if previous else 1
        changed = request.get("changed_scope")
        if changed is not None:
            changed = scopes(changed)
            if not set(changed) <= set(task["scope"]):
                raise GateError("changed_scope_expansion")
        artifact = {"id": output["id"], "revision": revision, "owner": role, "type": output["type"],
                    "scope": task["scope"], "intended_use": task["intended_use"], "changed_scope": changed,
                    "requires_ag3_review": output["requires_ag3_review"], "basis_refs": task["snapshot"],
                    "task_id": task["id"], "adoption": {"status": "candidate"}, **self.file_info(request["path"])}
        stamp, issues = self.basis_status(db, artifact)
        db.execute("INSERT INTO artifacts VALUES(?,?,?,?)", (artifact["id"], revision, artifact["path"], encode(artifact)))
        self.checkpoint("after_candidate_insert")
        task.update(phase="submitted", result_ref=ref(artifact))
        db.execute("UPDATE tasks SET body=? WHERE id=?", (encode(task), task["id"]))
        return {"ref": ref(artifact), "adoption": "candidate", "input_issues": issues, "basis_signature": stamp}

    def change_scope(self, db, old, new):
        if old["id"] != new["id"] or old["revision"] >= new["revision"]:
            return None
        changes = set()
        for revision in range(old["revision"] + 1, new["revision"] + 1):
            scope = self.artifact(db, {"id": old["id"], "revision": revision})["changed_scope"]
            if scope is None:
                return None
            changes.update(scope)
        return sorted(changes)

    def basis_status(self, db, artifact, proposed=None):
        evidence, issues = [], []
        pending = list(artifact["basis_refs"])
        seen = set()
        while pending:
            item = pending.pop(0)
            key_item = encode(item)
            if key_item in seen:
                continue
            seen.add(key_item)
            old = self.artifact(db, item)
            self.verify_file(old)
            base = {**item, "sha256": old["sha256"]}
            for scope in item["scope"]:
                key = (item["id"], item["intended_use"], scope)
                current = (proposed[key],) if proposed is not None and key in proposed else db.execute(
                    "SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?", key).fetchone()
                if current is None:
                    issues.append({"code": "input_not_adopted", "ref": ref(item), "scope": scope})
                    continue
                new_ref = {"id": item["id"], "revision": current[0]}
                new = self.artifact(db, new_ref)
                self.verify_file(new)
                if new_ref == ref(item):
                    continue
                if not overlaps(self.change_scope(db, item, new_ref), [scope]):
                    continue
                resolutions = [json.loads(row[0]) for row in db.execute("SELECT body FROM rechecks")]
                found = next((r for r in resolutions if r["target_ref"] == ref(artifact) and r["old_ref"] == ref(item)
                              and r["new_ref"] == new_ref and r["intended_use"] == item["intended_use"]
                              and scope in r["scope"]), None)
                if found:
                    base.setdefault("resolutions", []).append({"recheck_id": found["id"], "ref": new_ref,
                                                              "sha256": new["sha256"], "scope": scope})
                    pending.extend(found["new_basis_refs"])
                else:
                    issues.append({"code": "upstream_changed", "old_ref": ref(item), "new_ref": new_ref,
                                   "scope": scope, "intended_use": item["intended_use"]})
            evidence.append(base)
        return sha(encode(evidence).encode("utf-8")), issues

    def recheck_inputs(self, db, artifact):
        """Expose explicit updated sources to a reviewer without rewriting old basis."""
        inputs = []
        for row in db.execute("SELECT body FROM rechecks"):
            record = json.loads(row[0])
            if record["target_ref"] != ref(artifact):
                continue
            active_scope = []
            for part in record["scope"]:
                pointer = db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?",
                                     (record["new_ref"]["id"], record["intended_use"], part)).fetchone()
                if pointer is not None and pointer[0] == record["new_ref"]["revision"]:
                    active_scope.append(part)
            if active_scope:
                new = self.artifact(db, record["new_ref"])
                inputs.append({**record["new_ref"], "sha256": new["sha256"], "scope": active_scope,
                               "intended_use": record["intended_use"], "adoption_required": True,
                               "recheck_id": record["id"]})
                inputs += record["new_basis_refs"]
        return inputs

    def _receipt(self, db, role, request, artifact, stamp, kind, directly_checked, inherited=None):
        receipt_id = identifier(request["receipt_id"])
        outcome = request["outcome"]
        if outcome not in {"supported", "partial", "rejected"} or not isinstance(request.get("rationale"), str) or not request["rationale"].strip():
            raise GateError("explicit_professional_conclusion_required")
        coverage = scopes(request["scope"])
        if request["intended_use"] != artifact["intended_use"] or not set(coverage) <= set(artifact["scope"]):
            raise GateError("receipt_scope_expansion")
        supersedes = request.get("supersedes_receipt_ids", [])
        if not isinstance(supersedes, list) or len(set(supersedes)) != len(supersedes):
            raise GateError("invalid_receipt_supersession")
        for prior_id in supersedes:
            prior = self.get(db, "receipts", prior_id)
            if prior["by"] != role or prior["target_ref"] != ref(artifact) or prior["basis_signature"] != stamp or prior["intended_use"] != request["intended_use"] or not set(prior["scope"]) <= set(coverage):
                raise GateError("receipt_supersession_scope")
        receipt = {"id": receipt_id, "kind": kind, "by": role, "target_ref": ref(artifact),
                   "target_sha256": artifact["sha256"], "basis_signature": stamp,
                   "scope": coverage, "intended_use": request["intended_use"], "outcome": outcome,
                   "directly_checked_scope": directly_checked, "inherited_scope": inherited or [],
                   "base_receipt_id": request.get("base_receipt_id"), "rationale": request["rationale"],
                   "supersedes_receipt_ids": supersedes,
                   "authority_mode": "local_operator_attested"}
        db.execute("INSERT INTO receipts VALUES(?,?)", (receipt_id, encode(receipt)))
        return {"receipt_id": receipt_id, "target_ref": ref(artifact), "covered_scope": coverage}

    def _confirm(self, db, role, request, control):
        artifact = self.artifact(db, request["ref"])
        if role != artifact["owner"]:
            raise GateError("professional_owner_required")
        stamp, issues = self.basis_status(db, artifact)
        if issues and not (request.get("allow_provisional") is True and all(i["code"] == "input_not_adopted" for i in issues)):
            raise GateError("input_recheck_required")
        result = self._receipt(db, role, request, artifact, stamp, "professional_confirmation", scopes(request["scope"]))
        return {**result, "input_issues": issues, "provisional": bool(issues)}

    def _review(self, db, role, request, control):
        task = self.get(db, "tasks", request["task_id"])
        if role != "AG3" or task["assignee"] != role or task["task_kind"] != "review" or task["phase"] != "running":
            raise GateError("running_ag3_review_task_required")
        artifact = self.artifact(db, task["target_ref"])
        if "ref" in request and ref(request["ref"]) != task["target_ref"]:
            raise GateError("review_target_changed")
        coverage = scopes(request["scope"])
        if not set(coverage) <= set(task["scope"]):
            raise GateError("review_scope_expansion")
        checked = scopes(request.get("directly_checked_scope", coverage))
        inherited = request.get("inherited_scope", [])
        if inherited:
            inherited = scopes(inherited)
            base = self.get(db, "receipts", request["base_receipt_id"])
            if base["by"] != "AG3" or base["outcome"] != "supported" or base["intended_use"] != task["intended_use"]:
                raise GateError("invalid_base_review")
            if base["target_ref"]["id"] != artifact["id"] or base["target_ref"]["revision"] >= artifact["revision"]:
                raise GateError("supplement_version_mismatch")
            if not set(inherited) <= set(base["scope"]) or not request.get("compatibility_rationale", "").strip():
                raise GateError("explicit_inherited_compatibility_required")
        if set(checked) & set(inherited) or set(checked + inherited) != set(coverage):
            raise GateError("review_coverage_partition_required")
        # The conclusion binds the start snapshot even if pointers moved meanwhile.
        result = self._receipt(db, role, request, artifact, task["review_basis_signature"], "ag3_review", checked, inherited)
        if inherited:
            receipt = self.get(db, "receipts", request["receipt_id"])
            receipt["compatibility_rationale"] = request["compatibility_rationale"]
            db.execute("UPDATE receipts SET body=? WHERE id=?", (encode(receipt), receipt["id"]))
        task.update(phase="submitted", receipt_id=request["receipt_id"])
        db.execute("UPDATE tasks SET body=? WHERE id=?", (encode(task), task["id"]))
        return result

    def _recheck(self, db, role, request, control):
        artifact = self.artifact(db, request["ref"])
        if role != artifact["owner"]:
            raise GateError("professional_owner_required")
        scope = scopes(request["scope"])
        old, new = ref(request["old_ref"]), ref(request["new_ref"])
        use = request["intended_use"]
        _, issues = self.basis_status(db, artifact)
        matching = {i["scope"] for i in issues if i["code"] == "upstream_changed" and i["old_ref"] == old and i["new_ref"] == new and i["intended_use"] == use}
        if not set(scope) <= matching:
            raise GateError("recheck_not_in_changed_basis")
        if old["id"] != new["id"] or old == new or not request.get("rationale", "").strip():
            raise GateError("explicit_version_compatibility_required")
        for part in scope:
            row = db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?", (new["id"], use, part)).fetchone()
            if row is None or row[0] != new["revision"]:
                raise GateError("recheck_new_version_not_adopted")
        record = {"id": identifier(request["recheck_id"]), "target_ref": ref(artifact), "old_ref": old,
                  "new_ref": new, "scope": scope, "intended_use": use, "by": role,
                  "new_basis_refs": self.artifact(db, new)["basis_refs"],
                  "conclusion": "compatible", "rationale": request["rationale"]}
        db.execute("INSERT INTO rechecks VALUES(?,?)", (record["id"], encode(record)))
        return {"recheck_id": record["id"], "target_ref": ref(artifact)}

    def _adopt(self, db, role, request, control):
        if role != "AG0":
            raise GateError("ag0_bundle_adoption_required")
        bundle_id = identifier(request["bundle_id"])
        members = request["members"]
        if not isinstance(members, list) or not members:
            raise GateError("explicit_bundle_members_required")
        claimed_keys, validated = set(), []
        proposed = {}
        for member in members:
            exact = ref(member["ref"])
            for part in scopes(member["scope"]):
                key = (exact["id"], member["intended_use"], part)
                if key in proposed:
                    raise GateError("duplicate_bundle_pointer")
                proposed[key] = exact["revision"]
        for member in members:
            artifact = self.artifact(db, member["ref"])
            use, coverage = member["intended_use"], scopes(member["scope"])
            if use != artifact["intended_use"] or not set(coverage) <= set(artifact["scope"]):
                raise GateError("adoption_scope_expansion")
            stamp, issues = self.basis_status(db, artifact, proposed)
            if issues:
                raise GateError("input_recheck_required")
            owner_scope, reviewed_scope = set(), set()
            applicable, superseded = self.active_opinions(db, artifact, use, stamp)
            if any(r["outcome"] != "supported" and r["id"] not in superseded and overlaps(r["scope"], coverage) for r in applicable):
                raise GateError("conflicting_professional_receipts")
            for receipt_id in member["receipt_ids"]:
                receipt = self.get(db, "receipts", receipt_id)
                if receipt["target_ref"] != ref(artifact) or receipt["target_sha256"] != artifact["sha256"]:
                    raise GateError("receipt_version_mismatch")
                if receipt["basis_signature"] != stamp or receipt["intended_use"] != use:
                    raise GateError("receipt_basis_or_use_mismatch")
                if receipt["outcome"] != "supported":
                    raise GateError("receipt_not_supported")
                if receipt_id in superseded:
                    raise GateError("receipt_superseded")
                if receipt["kind"] == "professional_confirmation" and receipt["by"] == artifact["owner"]:
                    owner_scope.update(receipt["scope"])
                if receipt["kind"] == "ag3_review" and receipt["by"] == "AG3":
                    reviewed_scope.update(receipt["scope"])
            if not set(coverage) <= owner_scope:
                raise GateError("professional_confirmation_required")
            if artifact["requires_ag3_review"] and not set(coverage) <= reviewed_scope:
                raise GateError("ag3_review_required")
            for part in coverage:
                key = (artifact["id"], use, part)
                if key in claimed_keys:
                    raise GateError("duplicate_bundle_pointer")
                claimed_keys.add(key)
            validated.append(member)
        # All gates precede all pointer writes; no half-adopted collection.
        for member in validated:
            for part in member["scope"]:
                db.execute("INSERT INTO adopted VALUES(?,?,?,?) ON CONFLICT(id,intended_use,scope) DO UPDATE SET revision=excluded.revision",
                           (member["ref"]["id"], member["intended_use"], part, member["ref"]["revision"]))
                self.checkpoint("after_pointer_write")
        bundle = {"id": bundle_id, "by": role, "members": validated, "adoption": {"status": "adopted"},
                  "control_revision": control["state_revision"], "authority_mode": "local_operator_attested"}
        db.execute("INSERT INTO bundles VALUES(?,?)", (bundle_id, encode(bundle)))
        return {"bundle_id": bundle_id, "adoption": "adopted", "members": validated}

    def _finish(self, db, role, request, control):
        task = self.get(db, "tasks", request["task_id"])
        if role not in {task["requester"], task["assignee"]} or task["phase"] not in {"registered", "running"}:
            raise GateError("task_finish_not_allowed")
        if request["phase"] not in {"failed", "cancelled"} or not request.get("reason", "").strip():
            raise GateError("explicit_task_stop_required")
        task.update(phase=request["phase"], stop_reason=request["reason"])
        db.execute("UPDATE tasks SET body=? WHERE id=?", (encode(task), task["id"]))
        return {"task_id": task["id"], "phase": task["phase"]}

    def status(self, session):
        self.role(session)
        with self.connect() as db:
            db.execute("BEGIN")
            control = self.controls(db)
            tasks = [json.loads(row[0]) for row in db.execute("SELECT body FROM tasks ORDER BY id")]
            artifacts = [json.loads(row[0]) for row in db.execute("SELECT body FROM artifacts ORDER BY id,revision")]
            # State query has no body reads; paused/deleted IDs are filtered.
            hidden = set(control["deleted_ids"])
            if "*" in hidden:
                tasks, artifacts = [], []
            else:
                tasks = [t for t in tasks if t["id"] not in hidden and (not t["output"] or t["output"]["id"] not in hidden)
                         and (not t["target_ref"] or t["target_ref"]["id"] not in hidden)
                         and not any(i["id"] in hidden for i in t["snapshot"])]
                artifacts = [a for a in artifacts if a["id"] not in hidden and
                             not any(i["id"] in hidden for i in a["basis_refs"] + self.recheck_inputs(db, a))]
            visible = {(a["id"], a["revision"]) for a in artifacts}
            pointers = [dict(row) for row in db.execute("SELECT * FROM adopted ORDER BY id,intended_use,scope")
                        if (row["id"], row["revision"]) in visible]
            for artifact in artifacts:
                adopted = sorted({p["scope"] for p in pointers if p["id"] == artifact["id"] and p["revision"] == artifact["revision"]
                                  and p["intended_use"] == artifact["intended_use"]})
                artifact["adoption"] = {"status": "adopted" if set(adopted) == set(artifact["scope"]) else "partially_adopted" if adopted else "candidate",
                                        "scope": adopted, "meaning": "derived_from_use_scope_pointers"}
            result = {"status": "ok", "state_revision": self.state_revision(db), "control_revision": control["state_revision"],
                    "version": VERSION, "authority_mode": "local_operator_attested",
                    "tasks": tasks, "artifacts": artifacts, "adopted_pointers": pointers}
            return self.decorate_status(db, result)

    def decorate_status(self, db, result):
        return result

    def read_snapshot(self, session, task_id):
        role = self.role(session)
        with self.connect() as db:
            db.execute("BEGIN")
            task = self.get(db, "tasks", task_id)
            if role not in {task["assignee"], task["requester"]} or task["phase"] not in {"running", "submitted"}:
                raise GateError("task_snapshot_not_available")
            refs = task["snapshot"] + ([task["target_ref"]] if task["target_ref"] else [])
            control = self.controls(db)
            self.gate(control, {r["id"] for r in refs} | {task_id}, {task["intended_use"]} | {r["intended_use"] for r in task["snapshot"]})
            self.preflight(db, {"task_id": task_id, "intended_use": task["intended_use"]}, control)
            result = []
            for item in refs:
                artifact = self.artifact(db, item)
                if task["task_kind"] == "production":
                    self.check_opinions(db, artifact, item["intended_use"], item["scope"])
                self.verify_file(artifact)
                # Return exact bytes through one read; not a second mutable path read.
                data = (self.root / artifact["path"]).read_bytes()
                if sha(data) != artifact["sha256"]:
                    raise GateError("artifact_fingerprint_changed")
                result.append({"ref": ref(artifact), "path": artifact["path"], "sha256": artifact["sha256"], "content": data})
            if encode(self.controls(db)) != encode(control):
                raise GateError("control_changed_during_read")
            return result
