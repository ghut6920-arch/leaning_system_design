"""B1 synthetic-only transactional record store.

The database is the sole canonical source.  ``entry_actor`` is a fixture test
configuration, never authentication.  This module does not intercept host
output, erase conversation history, authenticate a user, or judge learning.
"""

from __future__ import annotations

import fnmatch
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator

from .contract_rules import artifact_paths, object_refs, validate_records
from .b3_semantics import active_grant


SCHEMA_VERSION = "pl-contracts/0.1.0"
STORE_VERSION = "pl-store/0.1.0"
_ACTORS = {"AG0", "AG1", "AG2", "AG3", "USER", "DEVELOPER"}
_PROFESSIONAL = {
    "GoalSpec", "SourceFragment", "MaterialUse", "ActivitySpec", "Judgment", "DiagnosticNote",
    "PlanCommitment", "MethodConfig", "WorkResult", "BudgetEnvelope",
}
_DECISION_TYPES = {
    "GoalSpec": {"goal_design"},
    "SourceFragment": {"material_read", "material_verification", "material_review"},
    "MaterialUse": {"material_review", "material_verification", "material_use"},
    "ActivitySpec": {"teaching_design", "teaching_adaptation"},
    "PlanCommitment": {"planning", "plan_adjustment"},
    "MethodConfig": {"teaching_design", "strategy_configuration"},
    "BudgetEnvelope": {"planning", "budget_allocation"},
    "WorkResult": {
        "material_read", "material_review", "material_verification", "material_use",
        "professional_review", "routine_scoring", "limited_diagnosis",
    },
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _issue(code: str, detail: str) -> dict[str, str]:
    return {"code": code, "detail": detail}


def _walk(value: Any) -> Iterator[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _artifact_refs(value: Any) -> Iterator[dict[str, Any]]:
    for item in _walk(value):
        if isinstance(item, dict) and "path" in item and "origin" in item:
            yield item


def _safe_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or "\0" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(part not in {"", ".", ".."} for part in value.split("/"))


def _mentions(value: str, token: str) -> bool:
    """Match whole identifiers/paths in text, including path#locators.

    A different path such as unrelated-originals.md is not originals.md.
    """
    return value == token or re.search(r"(?<![\w./-])" + re.escape(token) + r"(?![\w./-])", value) is not None


class LearningStore:
    """Small, serial SQLite adapter with fixture-only role checks.

    A caller may set ``failpoint`` to a callable accepting ``after_write`` or
    ``before_publish`` for transaction tests. Raising rolls back that mutation.
    Artifact paths are logical names inside SQLite, not filesystem paths.
    B1 artifact paths are immutable and have revision 1; a revised original
    needs a new logical path. Older object revisions remain exactly readable.
    """

    def __init__(self, root: str | Path, entry_actor: str = "AG0") -> None:
        self.root = Path(root).resolve()
        self.db_path = self.root / "records.sqlite3"
        self.entry_actor = entry_actor
        self.failpoint: Callable[[str], None] | None = None

    def _response(self, status: str, revision: int | None = None, **extra: Any) -> dict[str, Any]:
        return {"status": status, "state_revision": revision, "reasons": [], **extra}

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if not self.db_path.is_file():
            raise RuntimeError("workspace_not_initialized")
        connection = sqlite3.connect(str(self.db_path), timeout=3, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA secure_delete=ON")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA synchronous=FULL")
            marker = connection.execute("SELECT value FROM meta WHERE key='synthetic_only'").fetchone()
            if marker is None or marker[0] != "true":
                raise RuntimeError("synthetic_marker_missing")
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _revision(connection: sqlite3.Connection) -> int:
        row = connection.execute("SELECT value FROM meta WHERE key='state_revision'").fetchone()
        if row is None:
            raise RuntimeError("state_revision_missing")
        return int(row[0])

    @staticmethod
    def _bump(connection: sqlite3.Connection) -> int:
        revision = LearningStore._revision(connection) + 1
        connection.execute("UPDATE meta SET value=? WHERE key='state_revision'", (str(revision),))
        return revision

    @staticmethod
    def _all_records(connection: sqlite3.Connection) -> list[dict[str, Any]]:
        return [json.loads(row[0]) for row in connection.execute("SELECT body FROM records ORDER BY id,revision")]

    @staticmethod
    def _current_records(connection: sqlite3.Connection) -> list[dict[str, Any]]:
        query = "SELECT r.body FROM records r JOIN latest l ON r.id=l.id AND r.revision=l.revision ORDER BY r.id"
        return [json.loads(row[0]) for row in connection.execute(query)]

    @staticmethod
    def _controls(connection: sqlite3.Connection) -> dict[str, Any]:
        restrictions, paused, deleted = [], [], []
        for row in connection.execute("SELECT * FROM controls ORDER BY scope_id,kind"):
            if row["kind"] == "restriction":
                restrictions.append({
                    "scope_id": row["scope_id"], "intended_uses": json.loads(row["intended_uses"]),
                    "reason": row["reason"], "issued_by": row["issued_by"],
                })
            elif row["kind"] == "pause":
                paused.append(row["scope_id"])
            elif row["kind"] == "deleted":
                deleted.append(row["scope_id"])
        return {"restrictions": restrictions, "paused_ids": paused, "deleted_ids": deleted}

    @staticmethod
    def _closure(connection: sqlite3.Connection, identifiers: set[str]) -> set[str]:
        """Find actual upstream dependency IDs without guessing missing edges."""
        result = set(identifiers)
        frontier = set(identifiers)
        while frontier:
            found: set[str] = set()
            for identifier in frontier:
                found.update(row[0] for row in connection.execute(
                    "SELECT DISTINCT target_id FROM dependencies WHERE owner_id=?", (identifier,),
                ))
            frontier = found - result
            result.update(frontier)
        return result

    def _blocked(
        self, connection: sqlite3.Connection, identifiers: set[str], uses: set[str], *, writing: bool,
        revisions: set[tuple[str, int]] | None = None,
    ) -> list[dict[str, str]]:
        # Named object controls cover every revision. Dependency traversal for an
        # exact read follows only that revision, never later configurations.
        scope = self._closure(connection, identifiers) if revisions is None else set(identifiers)
        frontier = set(revisions or ())
        visited = set()
        while frontier:
            identifier, revision = frontier.pop()
            if (identifier, revision) in visited:
                continue
            visited.add((identifier, revision))
            scope.add(identifier)
            frontier.update((row[0], row[1]) for row in connection.execute(
                "SELECT target_id,target_revision FROM dependencies WHERE owner_id=? AND owner_revision=?",
                (identifier, revision),
            ))
        controls = self._controls(connection)
        problems: list[dict[str, str]] = []
        for identifier in sorted(scope.intersection(controls["deleted_ids"])):
            problems.append(_issue("deleted_scope", f"Scope {identifier} is unavailable."))
        if writing or uses != {"read"}:
            for identifier in sorted(scope.intersection(controls["paused_ids"])):
                problems.append(_issue("paused_scope", f"Scope {identifier} is paused."))
        for restriction in controls["restrictions"]:
            if restriction["scope_id"] not in scope:
                continue
            restricted = set(restriction["intended_uses"])
            if "*" in restricted or restricted.intersection(uses):
                problems.append(_issue("restricted_use", f"Scope {restriction['scope_id']} restricts the requested use."))
        return problems

    def _tick(self, stage: str) -> None:
        if self.failpoint is not None:
            try:
                self.failpoint(stage)
            except Exception:
                raise RuntimeError("injected_transaction_failure") from None

    def init_workspace(self) -> dict[str, Any]:
        """Create an explicitly marked empty fixture workspace, never a real one."""
        try:
            if self.entry_actor not in _ACTORS:
                return self._response("rejected", reasons=[_issue("unknown_fixture_actor", "Unknown fixture actor.")])
            if self.db_path.exists():
                with self._connect() as connection:
                    return self._response("ok", self._revision(connection), synthetic_only=True, initialized=False)
            if self.root.exists() and (not self.root.is_dir() or any(self.root.iterdir())):
                return self._response("rejected", reasons=[_issue("nonempty_root", "A new fixture root must be empty.")])
            self.root.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(str(self.db_path), timeout=3, isolation_level=None)
            try:
                connection.execute("PRAGMA journal_mode=DELETE")
                connection.execute("PRAGMA secure_delete=ON")
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA synchronous=FULL")
                connection.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    CREATE TABLE records(
                        id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
                        kind TEXT NOT NULL, owner TEXT NOT NULL, body TEXT NOT NULL,
                        PRIMARY KEY(id,revision));
                    CREATE TABLE latest(
                        id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                        FOREIGN KEY(id,revision) REFERENCES records(id,revision) ON DELETE CASCADE);
                    CREATE TABLE artifacts(path TEXT PRIMARY KEY, revision INTEGER NOT NULL CHECK(revision=1), content TEXT NOT NULL);
                    CREATE TABLE dependencies(
                        owner_id TEXT NOT NULL, owner_revision INTEGER NOT NULL,
                        target_id TEXT NOT NULL, target_revision INTEGER NOT NULL, locator TEXT NOT NULL,
                        PRIMARY KEY(owner_id,owner_revision,target_id,target_revision,locator),
                        FOREIGN KEY(owner_id,owner_revision) REFERENCES records(id,revision) ON DELETE CASCADE);
                    CREATE TABLE artifact_links(
                        owner_id TEXT NOT NULL, owner_revision INTEGER NOT NULL, path TEXT NOT NULL,
                        PRIMARY KEY(owner_id,owner_revision,path),
                        FOREIGN KEY(owner_id,owner_revision) REFERENCES records(id,revision) ON DELETE CASCADE);
                    CREATE TABLE controls(
                        scope_id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('restriction','pause','deleted')),
                        intended_uses TEXT NOT NULL, reason TEXT NOT NULL, issued_by TEXT NOT NULL,
                        PRIMARY KEY(scope_id,kind));
                    CREATE TABLE operations(operation_id TEXT PRIMARY KEY, kind TEXT NOT NULL, request_index TEXT NOT NULL, receipt TEXT NOT NULL);
                    CREATE TABLE delete_jobs(operation_id TEXT PRIMARY KEY, request_index TEXT NOT NULL, affected_ids TEXT NOT NULL, affected_paths TEXT NOT NULL);
                    INSERT INTO meta VALUES('synthetic_only','true');
                    INSERT INTO meta VALUES('schema_version','pl-contracts/0.1.0');
                    INSERT INTO meta VALUES('store_version','pl-store/0.1.0');
                    INSERT INTO meta VALUES('state_revision','0');
                    INSERT INTO meta VALUES('generation','0');
                    COMMIT;
                """)
            finally:
                connection.close()
            return self._response("committed", 0, synthetic_only=True, initialized=True)
        except (OSError, sqlite3.Error, RuntimeError, ValueError):
            return self._response("not_saved", reasons=[_issue("initialization_failed", "Fixture initialization could not be confirmed.")])

    def read_context(self) -> dict[str, Any]:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN")
                revision = self._revision(connection)
                records = self._current_records(connection)
                available = [record for record in records if not self._blocked(connection, {record["id"]}, {"read"}, writing=False, revisions={(record["id"], record["revision"])})]
                result = self._response(
                    "ok", revision, synthetic_only=True, objects=available, controls=self._controls(connection),
                    omitted_count=len(records) - len(available),
                    capabilities={"host_identity_bound": False, "output_interception_bound": False, "entry_actor_is_test_config": True},
                )
                connection.commit()
                return result
        except (OSError, sqlite3.Error, RuntimeError, ValueError, KeyError):
            return self._response("not_saved", reasons=[_issue("read_failed", "Current fixture context is unavailable.")])

    def _refs_problems(
        self, connection: sqlite3.Connection, refs: list[dict[str, Any]], intended_use: str,
        incoming: dict[tuple[str, int], dict[str, Any]] | None = None,
    ) -> list[dict[str, str]]:
        problems: list[dict[str, str]] = []
        incoming = incoming or {}
        for ref in refs:
            if not isinstance(ref, dict):
                problems.append(_issue("invalid_reference", "References must be objects."))
                continue
            if "path" in ref:
                path = ref.get("path")
                if not _safe_path(path) or ref.get("revision") != 1:
                    problems.append(_issue("invalid_artifact_ref", "B1 artifacts use a safe logical path and revision 1."))
                    continue
                row = connection.execute("SELECT revision FROM artifacts WHERE path=?", (path,)).fetchone()
                if row is None:
                    problems.append(_issue("missing_artifact", f"Managed artifact {path} is absent."))
                    continue
                owners = {(item[0], item[1]) for item in connection.execute("SELECT owner_id,owner_revision FROM artifact_links WHERE path=?", (path,))}
                problems.extend(self._blocked(connection, {path}, {intended_use}, writing=False, revisions=owners))
                continue
            identifier, revision = ref.get("id"), ref.get("revision")
            if not isinstance(identifier, str) or not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
                problems.append(_issue("invalid_reference", "Object references require an ID and positive revision."))
                continue
            problems.extend(self._blocked(connection, {identifier}, {intended_use}, writing=False, revisions={(identifier, revision)}))
            if (identifier, revision) not in incoming:
                found = connection.execute("SELECT 1 FROM records WHERE id=? AND revision=?", (identifier, revision)).fetchone()
                if found is None:
                    problems.append(_issue("missing_reference", f"Object {identifier} revision {revision} is absent."))
        return problems

    def validate_refs(self, refs: list[dict[str, Any]], intended_use: str = "read") -> dict[str, Any]:
        if not isinstance(refs, list) or not isinstance(intended_use, str) or not intended_use:
            return self._response("rejected", reasons=[_issue("invalid_request", "References and an intended use are required.")])
        try:
            with self._connect() as connection:
                connection.execute("BEGIN")
                problems = self._refs_problems(connection, refs, intended_use)
                result = self._response("rejected" if problems else "ok", self._revision(connection), reasons=problems, checked_count=len(refs))
                connection.commit()
                return result
        except (OSError, sqlite3.Error, RuntimeError, ValueError):
            return self._response("not_saved", reasons=[_issue("reference_check_failed", "References could not be checked.")])

    @staticmethod
    def _execution_records(connection: sqlite3.Connection, activity_ref: dict[str, Any]) -> list[dict[str, Any]]:
        return [record for record in LearningStore._current_records(connection)
                if record.get("type") == "ControlState"
                and record.get("execution", {}).get("activity_ref", {}).get("id") == activity_ref.get("id")]

    @staticmethod
    def _execution_basis_problems(connection: sqlite3.Connection, refs: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Execution also depends on current versions of its actual upstream basis.

        An omitted source cannot bypass the gate when a material or activity
        explicitly depends on it. This conservative gate requires professional
        rebind/review after a recorded dependency changes; it does not rewrite
        historical evidence to the latest version.
        """
        frontier = {(ref.get("id"), ref.get("revision")) for ref in refs if "id" in ref}
        visited = set()
        while frontier:
            identifier, revision = frontier.pop()
            if (identifier, revision) in visited:
                continue
            visited.add((identifier, revision))
            latest = connection.execute("SELECT revision FROM latest WHERE id=?", (identifier,)).fetchone()
            if latest is None or latest[0] != revision:
                return [_issue("stale_execution_basis", "An upstream execution dependency needs current professional review.")]
            frontier.update((row[0], row[1]) for row in connection.execute(
                "SELECT target_id,target_revision FROM dependencies WHERE owner_id=? AND owner_revision=?", (identifier, revision)))
        return []

    def set_execution(
        self, expected_state_revision: int, operation_id: str, activity_ref: dict[str, Any],
        executor_id: str, basis_refs: list[dict[str, Any]], expected_epoch: int | None = None,
    ) -> dict[str, Any]:
        """B6 fixture host's dedicated atomic execution claim.

        The serial host authenticates its capability and ends the old channel.
        This adapter checks records and CAS; a string here is not OS identity.
        Ordinary commit still cannot write a ControlState.
        """
        problems = self._request_problems(expected_state_revision, operation_id)
        if self.entry_actor != "AG0":
            problems.append(_issue("execution_owner", "Execution control belongs to the entry."))
        if (not isinstance(activity_ref, dict) or not isinstance(activity_ref.get("id"), str)
                or type(activity_ref.get("revision")) is not int or activity_ref["revision"] < 1
                or not isinstance(executor_id, str) or not executor_id or len(executor_id) > 200
                or not isinstance(basis_refs, list) or not all(isinstance(ref, dict) for ref in basis_refs)
                or (expected_epoch is not None and (type(expected_epoch) is not int or expected_epoch < 0))):
            problems.append(_issue("execution_request", "An exact activity, executor, basis and epoch are required."))
        if problems:
            return self._response("rejected", reasons=problems)
        refs = [activity_ref] + basis_refs
        index = {"activity_ref": activity_ref, "executor_id": executor_id, "basis_refs": basis_refs, "expected_epoch": expected_epoch}
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                revision = self._revision(connection)
                problems = self._refs_problems(connection, refs, "teaching")
                row = connection.execute("SELECT kind FROM records WHERE id=? AND revision=?", (activity_ref["id"], activity_ref["revision"])).fetchone()
                if row is None or row[0] != "ActivitySpec":
                    problems.append(_issue("execution_activity", "Execution requires a saved activity."))
                problems.extend(self._execution_basis_problems(connection, refs))
                previous = self._execution_records(connection, activity_ref)
                epoch = max((r.get("execution", {}).get("execution_epoch", 0) for r in previous), default=0)
                identifier = "FIX-network-execution-" + activity_ref["id"]
                problems.extend(self._blocked(connection, {identifier}, {"teaching"}, writing=True))
                if problems:
                    connection.rollback()
                    return self._response("rejected", revision, reasons=problems)
                retry = self._receipt(connection, operation_id, "execution", index)
                if retry is not None:
                    execution = next((r.get("execution") for r in previous if r["id"] == identifier), None)
                    if retry.get("execution") != execution:
                        retry = self._response("rejected", revision, reasons=[_issue("superseded_execution", "A prior execution receipt cannot restore an old channel.")])
                    connection.rollback()
                    return retry
                conflict = self._conflict(connection, expected_state_revision)
                if conflict:
                    connection.rollback()
                    return conflict
                if expected_epoch is not None and expected_epoch != epoch:
                    connection.rollback()
                    return self._response("rejected", revision, reasons=[_issue("execution_epoch_conflict", "Reload the current execution before taking over.")])
                if any(r.get("execution", {}).get("status") == "active" for r in previous) and expected_epoch is None:
                    connection.rollback()
                    return self._response("rejected", revision, reasons=[_issue("execution_epoch_required", "A takeover must identify the old execution epoch.")])
                latest = connection.execute("SELECT revision FROM latest WHERE id=?", (identifier,)).fetchone()
                object_revision = latest[0] + 1 if latest else 1
                execution = {"activity_ref": activity_ref, "current_executor": executor_id, "execution_epoch": epoch + 1, "status": "active"}
                record = {"type": "ControlState", "id": identifier, "revision": object_revision, "owner": "AG0",
                          "schema_version": SCHEMA_VERSION, "basis_refs": refs, "state_revision": revision + 1,
                          "restrictions": [], "execution": execution, "record_policy": "synthetic serial local host",
                          "pending_controls": []}
                artifacts = {r[0]: r[1] for r in connection.execute("SELECT path,content FROM artifacts")}
                problems = validate_records(self._all_records(connection) + [record], artifacts, synthetic_only=True)
                if problems:
                    connection.rollback()
                    return self._response("rejected", revision, reasons=problems)
                connection.execute("INSERT INTO records VALUES(?,?,?,?,?)", (identifier, object_revision, "ControlState", "AG0", _json(record)))
                connection.execute("INSERT INTO latest VALUES(?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision", (identifier, object_revision))
                for ref in object_refs(record):
                    connection.execute("INSERT OR IGNORE INTO dependencies VALUES(?,?,?,?,?)", (identifier, object_revision, ref["id"], ref["revision"], str(ref.get("locator", ""))))
                self._tick("after_write")
                revision = self._bump(connection)
                receipt = self._response("committed", revision, execution=execution,
                                         control_ref={"id": identifier, "revision": object_revision}, synthetic_only=True)
                self._save_receipt(connection, operation_id, "execution", index, receipt)
                self._tick("before_publish")
                connection.commit()
                return receipt
        except Exception:
            return self._response("not_saved", reasons=[_issue("execution_failed", "Execution control was not saved.")])

    def check_execution(
        self, activity_ref: dict[str, Any], executor_id: str, execution_epoch: int,
        basis_refs: list[dict[str, Any]], intended_use: str = "teaching",
    ) -> dict[str, Any]:
        """Read the current gate; a previous successful receipt is not a lease."""
        if (not isinstance(activity_ref, dict) or not isinstance(executor_id, str)
                or type(execution_epoch) is not int or execution_epoch < 1
                or not isinstance(basis_refs, list) or not all(isinstance(ref, dict) for ref in basis_refs)
                or not isinstance(intended_use, str) or not intended_use):
            return self._response("rejected", reasons=[_issue("execution_request", "Invalid execution check.")])
        try:
            with self._connect() as connection:
                connection.execute("BEGIN")
                revision = self._revision(connection)
                problems = self._refs_problems(connection, [activity_ref] + basis_refs, intended_use)
                records = [r for r in self._execution_records(connection, activity_ref) if r["id"].startswith("FIX-network-execution-")]
                current = max(records, key=lambda r: r["execution"]["execution_epoch"], default=None)
                if current is None or current["execution"] != {"activity_ref": activity_ref, "current_executor": executor_id,
                                                               "execution_epoch": execution_epoch, "status": "active"}:
                    problems.append(_issue("execution_revoked", "Only the current executor may continue this activity."))
                if current is not None:
                    problems.extend(self._refs_problems(connection, [{"id": current["id"], "revision": current["revision"]}], intended_use))
                    problems.extend(self._execution_basis_problems(connection, [activity_ref] + current["basis_refs"] + basis_refs))
                connection.commit()
                return self._response("rejected" if problems else "ok", revision, reasons=problems,
                                      **({"execution": current["execution"]} if not problems else {}))
        except Exception:
            return self._response("not_saved", reasons=[_issue("execution_check_failed", "Current execution could not be confirmed.")])

    def read_refs(self, refs: list[dict[str, Any]], intended_use: str = "read") -> dict[str, Any]:
        """Read exact legal historical revisions in one controlled snapshot."""
        if not isinstance(refs, list) or not isinstance(intended_use, str) or not intended_use:
            return self._response("rejected", reasons=[_issue("invalid_request", "References and an intended use are required.")])
        try:
            with self._connect() as connection:
                connection.execute("BEGIN")
                revision = self._revision(connection)
                problems = self._refs_problems(connection, refs, intended_use)
                if problems:
                    connection.rollback()
                    return self._response("rejected", revision, reasons=problems)
                records = []
                artifact_locations = []
                for ref in refs:
                    if "path" in ref:
                        artifact_locations.append(dict(ref))
                    else:
                        row = connection.execute("SELECT body FROM records WHERE id=? AND revision=?", (ref["id"], ref["revision"])).fetchone()
                        records.append(json.loads(row[0]))
                receipt = self._response("ok", revision, synthetic_only=True, objects=records, artifact_refs=artifact_locations)
                connection.commit()
                return receipt
        except (OSError, sqlite3.Error, RuntimeError, ValueError, KeyError, TypeError):
            return self._response("not_saved", reasons=[_issue("historical_read_failed", "Exact fixture revisions could not be read.")])

    def read_artifact_segment(
        self, artifact_ref: dict[str, Any], start_line: int, end_line: int,
        intended_use: str = "material_read",
    ) -> dict[str, Any]:
        """Read a bounded text segment in one controlled snapshot.

        Line numbers are one-based and inclusive. This retrieves text only; it
        does not establish that formulas or figures were read or verified.
        """
        if not isinstance(artifact_ref, dict) or not isinstance(intended_use, str) or not intended_use:
            return self._response("rejected", reasons=[_issue("invalid_request", "An artifact reference and intended use are required.")])
        if (
            type(start_line) is not int or type(end_line) is not int
            or start_line < 1 or end_line < start_line
        ):
            return self._response("rejected", reasons=[_issue("invalid_line_range", "Line numbers must be positive integers in inclusive order.")])
        if (
            not _safe_path(artifact_ref.get("path"))
            or type(artifact_ref.get("revision")) is not int or artifact_ref["revision"] != 1
            or artifact_ref.get("origin") != "synthetic_fixture"
            or not isinstance(artifact_ref.get("locator"), str) or not artifact_ref["locator"]
        ):
            return self._response("rejected", reasons=[_issue("invalid_artifact_ref", "A safe synthetic fixture artifact reference with revision 1 and a locator is required.")])
        try:
            with self._connect() as connection:
                connection.execute("BEGIN")
                revision = self._revision(connection)
                problems = self._refs_problems(connection, [artifact_ref], intended_use)
                if problems:
                    connection.rollback()
                    # Failed reads do not reflect a caller-supplied payload in
                    # an artifact path or reproduce any stored original text.
                    problems = [
                        _issue(problem["code"], "The managed artifact is unavailable.")
                        if problem["code"] == "missing_artifact" else problem
                        for problem in problems
                    ]
                    return self._response("rejected", revision, reasons=problems)
                row = connection.execute("SELECT content FROM artifacts WHERE path=? AND revision=?", (artifact_ref["path"], artifact_ref["revision"])).fetchone()
                if row is None:
                    connection.rollback()
                    return self._response("rejected", revision, reasons=[_issue("missing_artifact", "The managed artifact is unavailable.")])
                lines = row[0].splitlines(keepends=True)
                if end_line > len(lines):
                    connection.rollback()
                    return self._response("rejected", revision, reasons=[_issue("invalid_line_range", "The entire requested range must exist in the artifact.")])
                text = "".join(lines[start_line - 1:end_line])
                if artifact_ref["locator"] not in text:
                    connection.rollback()
                    return self._response("rejected", revision, reasons=[_issue("artifact_locator_outside_segment", "The requested locator must occur in the selected text segment.")])
                receipt = self._response(
                    "ok", revision, synthetic_only=True,
                    artifact_ref={field: artifact_ref[field] for field in ("path", "locator", "revision", "origin")},
                    start_line=start_line, end_line=end_line, text=text,
                )
                connection.commit()
                return receipt
        except (OSError, sqlite3.Error, RuntimeError, ValueError, KeyError, TypeError, AttributeError):
            return self._response("not_saved", reasons=[_issue("artifact_read_failed", "The fixture text segment could not be read.")])

    @staticmethod
    def _scope_matches(scope: Any, identifiers: set[str]) -> bool:
        if not isinstance(scope, list) or not scope:
            return False
        patterns = [item if isinstance(item, str) else item.get("id", "") for item in scope if isinstance(item, (str, dict))]
        return all(any(pattern and fnmatch.fnmatchcase(identifier, pattern) for pattern in patterns) for identifier in identifiers)

    def _authority_problems(
        self, connection: sqlite3.Connection, changes: list[dict[str, Any]],
        authorization_refs: list[dict[str, Any]], adoption_refs: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        problems: list[dict[str, str]] = []
        if self.entry_actor not in _ACTORS:
            return [_issue("unknown_fixture_actor", "Unknown fixture actor.")]
        incoming = {(record["id"], record["revision"]): record for record in changes}

        def resolve(ref: dict[str, Any]) -> dict[str, Any] | None:
            if (ref.get("id"), ref.get("revision")) in incoming:
                return incoming[(ref["id"], ref["revision"])]
            row = connection.execute("SELECT body FROM records WHERE id=? AND revision=?", (ref.get("id"), ref.get("revision"))).fetchone()
            return json.loads(row[0]) if row else None

        grants: list[dict[str, Any]] = []
        for ref in authorization_refs:
            row = connection.execute("SELECT body FROM records WHERE id=? AND revision=?", (ref.get("id"), ref.get("revision"))).fetchone()
            if row is not None:
                grant = json.loads(row[0])
                if grant.get("type") == "AuthorizationGrant" and grant.get("binding_status") == "verified_for_fixture" and grant.get("grantee") == self.entry_actor:
                    grants.append(grant)
        for record in changes:
            if record.get("owner") != self.entry_actor:
                problems.append(_issue("fixture_actor_scope", f"The fixture entry cannot write owner {record.get('owner')} objects."))
                continue
            kind = record.get("type")
            if kind == "AuthorizationGrant":
                problems.append(_issue("grant_creation_unavailable", "New grants require a separately bound issuer; B1 only imports fixture grants."))
            if kind == "ControlState":
                problems.append(_issue("control_write_unavailable", "Use the controlled pause, restrict, resume, or delete APIs."))
            if kind == "UseRestriction" and record.get("status") != "active":
                problems.append(_issue("professional_restoration_unavailable", "B1 cannot restore a professional use restriction."))
            if kind not in _PROFESSIONAL:
                continue
            if not authorization_refs or not adoption_refs:
                problems.append(_issue("professional_receipt_required", "Professional results require explicit authorization and adoption references."))
                continue
            decision_types = {record.get("decision_type")} if record.get("decision_type") else _DECISION_TYPES.get(kind, set())
            decision_types.discard(None)
            scope = {record["id"]} | {ref["id"] for ref in object_refs(record) if isinstance(ref.get("id"), str)}
            criteria = record.get("criterion_refs", [])
            if kind == "Judgment":
                criteria = [dict(record.get("goal_ref", {}), locator=f"requirements/{record.get('requirement_id', '')}")]
                # Object scope is the assessed event/activity. Goal and criterion
                # authority is checked on the separate criterion axis; grant IDs
                # and the new result's ID are not assessed object scope.
                scope = {ref["id"] for ref in record.get("event_refs", [])}
                for ref in record.get("event_refs", []):
                    event = resolve(ref)
                    if event and isinstance(event.get("activity_ref"), dict):
                        scope.add(event["activity_ref"]["id"])
            elif kind == "DiagnosticNote":
                scope = {ref["id"] for ref in record.get("observations", []) if isinstance(ref, dict) and "id" in ref}
                criteria = record.get("goal_refs", [])
            elif kind == "WorkResult" and record.get("metadata", {}).get("network", {}).get("version") == "pl-network/0.1.0":
                # A network envelope cannot broaden the underlying professional
                # grant merely by adding its own ID, budget or receipt references.
                order = resolve(record.get("work_order_ref", {}))
                if not order or order.get("type") != "WorkOrder" or order.get("assignee") != self.entry_actor:
                    problems.append(_issue("work_result_owner", "The accepted professional recipient owns the return."))
                    continue
                decision_types = {order.get("decision_type")}
                scope = {ref["id"] for ref in order.get("event_refs", []) + order.get("material_refs", [])}
                if not scope:
                    scope = {ref["id"] for ref in order.get("context_refs", [])
                             if ref["id"] != order.get("shared_budget_ref", {}).get("id")}
                criteria = order.get("goal_and_criteria_refs", [])
            compatible = False
            for grant in grants:
                if not decision_types.intersection(grant.get("decision_types", [])) or not self._scope_matches(grant.get("object_scope"), scope):
                    continue
                if not grant.get("permitted_conclusions") or not active_grant(grant.get("validity"), allow_legacy=True):
                    continue
                grant_criteria = grant.get("criterion_refs", [])
                if criteria and any(not any(
                    criterion.get("id") == allowed.get("id") and criterion.get("revision") == allowed.get("revision")
                    and (not criterion.get("locator") or criterion.get("locator") == allowed.get("locator")) for allowed in grant_criteria
                ) for criterion in criteria):
                    continue
                compatible = True
                break
            if not compatible:
                problems.append(_issue("authorization_scope", "No fixture grant covers this professional decision, object, and criterion scope."))
            if kind in {"Judgment", "DiagnosticNote"} and record.get("authorization_ref") not in authorization_refs:
                problems.append(_issue("authorization_reference_mismatch", "The result's authorization must be supplied explicitly."))
            if kind == "Judgment" and record.get("decision_type") != "routine_scoring" and self.entry_actor == "AG0":
                problems.append(_issue("professional_escalation", "Important review is outside the AG0 fixture entry's scope."))
            if kind == "DiagnosticNote" and record.get("decision_type") != "limited_diagnosis" and self.entry_actor == "AG0":
                problems.append(_issue("professional_escalation", "Only explicitly limited diagnosis can be delegated to AG0."))
            adoption = record.get("adoption")
            if isinstance(adoption, dict) and adoption.get("status") in {"adopted", "partially_adopted"}:
                if adoption.get("by") != self.entry_actor or not adoption.get("basis_refs"):
                    problems.append(_issue("adoption_scope", "Adoption needs the responsible fixture actor and explicit basis."))
                elif any(ref not in adoption_refs for ref in adoption["basis_refs"]):
                    problems.append(_issue("adoption_reference_mismatch", "Adoption basis must be included in adoption_refs."))
        return problems

    @staticmethod
    def _index(
        changes: list[dict[str, Any]], artifacts: dict[str, str],
        authorization_refs: list[dict[str, Any]], adoption_refs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "objects": sorted([[record["id"], record["revision"]] for record in changes]),
            "artifact_paths": sorted(artifacts),
            "authorization_refs": sorted(authorization_refs, key=_json),
            "adoption_refs": sorted(adoption_refs, key=_json),
        }

    @staticmethod
    def _receipt(connection: sqlite3.Connection, operation_id: str, kind: str, index: Any) -> dict[str, Any] | None:
        row = connection.execute("SELECT kind,request_index,receipt FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
        if row is None:
            if kind != "delete" and connection.execute("SELECT 1 FROM delete_jobs WHERE operation_id=?", (operation_id,)).fetchone():
                return {"status": "rejected", "state_revision": LearningStore._revision(connection), "reasons": [_issue("operation_id_reused", "This operation ID belongs to a pending deletion.")]}
            return None
        if row["kind"] != kind or row["request_index"] != _json(index):
            return {"status": "rejected", "state_revision": LearningStore._revision(connection), "reasons": [_issue("operation_id_reused", "An operation ID cannot describe a different request.")]}
        return json.loads(row["receipt"])

    @staticmethod
    def _save_receipt(connection: sqlite3.Connection, operation_id: str, kind: str, index: Any, receipt: dict[str, Any]) -> None:
        connection.execute("INSERT INTO operations VALUES(?,?,?,?)", (operation_id, kind, _json(index), _json(receipt)))

    @staticmethod
    def _request_problems(expected_state_revision: Any, operation_id: Any) -> list[dict[str, str]]:
        problems = []
        if not isinstance(expected_state_revision, int) or isinstance(expected_state_revision, bool) or expected_state_revision < 0:
            problems.append(_issue("invalid_state_revision", "A nonnegative expected state revision is required."))
        if not isinstance(operation_id, str) or not operation_id or len(operation_id) > 200 or "\0" in operation_id:
            problems.append(_issue("invalid_operation_id", "A bounded nonempty logical operation ID is required."))
        return problems

    @staticmethod
    def _conflict(connection: sqlite3.Connection, expected: int) -> dict[str, Any] | None:
        revision = LearningStore._revision(connection)
        if revision != expected:
            return {"status": "conflict", "state_revision": revision, "reasons": [_issue("state_revision_conflict", "Reload current state and refer the old decision for review.")]}
        return None

    def import_fixture(self, snapshot: dict[str, Any], artifacts: dict[str, str] | None = None) -> dict[str, Any]:
        """One-time explicit synthetic bootstrap; it is not an authorization API."""
        if not isinstance(snapshot, dict) or snapshot.get("synthetic_only") is not True or not isinstance(snapshot.get("objects"), list):
            return self._response("rejected", reasons=[_issue("synthetic_fixture_required", "Bootstrap requires synthetic_only=true and complete fixture objects.")])
        return self._commit(0, "FIX-bootstrap", snapshot["objects"], artifacts or {}, [], [], bootstrap=True)

    def commit(
        self, expected_state_revision: int, operation_id: str, changes: list[dict[str, Any]],
        artifacts: dict[str, str] | None = None, authorization_refs: list[dict[str, Any]] | None = None,
        adoption_refs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self._commit(expected_state_revision, operation_id, changes, artifacts or {}, authorization_refs or [], adoption_refs or [])

    def _commit(
        self, expected_state_revision: int, operation_id: str, changes: list[dict[str, Any]],
        artifacts: dict[str, str], authorization_refs: list[dict[str, Any]], adoption_refs: list[dict[str, Any]], *, bootstrap: bool = False,
    ) -> dict[str, Any]:
        problems = self._request_problems(expected_state_revision, operation_id)
        if not isinstance(changes, list) or not changes or not all(isinstance(record, dict) for record in changes):
            problems.append(_issue("invalid_changes", "Changes must be a nonempty list of complete contract objects."))
        if not isinstance(artifacts, dict) or any(not _safe_path(path) or not isinstance(content, str) for path, content in artifacts.items()):
            problems.append(_issue("invalid_artifacts", "Artifacts need safe relative logical paths and UTF-8 text."))
        if not isinstance(authorization_refs, list) or not isinstance(adoption_refs, list) or any(not isinstance(ref, dict) for ref in authorization_refs + adoption_refs):
            problems.append(_issue("invalid_authorization_refs", "Authorization and adoption references must be reference arrays."))
        if problems:
            return self._response("rejected", reasons=problems)
        try:
            # Serialize only in memory. Neither rejected data nor fingerprints are persisted.
            _json(changes)
            for content in artifacts.values():
                content.encode("utf-8")
            for record in changes:
                if not isinstance(record.get("id"), str) or not record["id"].startswith("FIX-"):
                    problems.append(_issue("synthetic_id_required", "B1 accepts only explicit FIX-* fixture records."))
                if not isinstance(record.get("revision"), int) or isinstance(record.get("revision"), bool) or record["revision"] < 1:
                    problems.append(_issue("invalid_object_revision", "An object needs a positive revision."))
                for item in _walk(record):
                    if isinstance(item, dict) and item.get("binding_status") == "host_verified":
                        problems.append(_issue("host_binding_unavailable", "B1 cannot verify host-bound authorization or real personal records."))
                for ref in _artifact_refs(record):
                    if ref.get("origin") != "synthetic_fixture" or ref.get("revision") != 1:
                        problems.append(_issue("synthetic_artifact_required", "B1 accepts only fixture artifacts at immutable revision 1."))
            if problems:
                return self._response("rejected", reasons=problems)
            index = self._index(changes, artifacts, authorization_refs, adoption_refs)
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                current_revision = self._revision(connection)
                if bootstrap and (current_revision != 0 or connection.execute("SELECT 1 FROM records LIMIT 1").fetchone()):
                    connection.rollback()
                    return self._response("rejected", current_revision, reasons=[_issue("bootstrap_not_empty", "Fixture bootstrap is only available once on a new empty workspace.")])
                touched = {record["id"] for record in changes} | set(artifacts)
                uses = {"commit"}
                for record in changes:
                    touched.update(ref["id"] for ref in object_refs(record) if isinstance(ref.get("id"), str))
                    touched.update(artifact_paths(record))
                    for field in ("intended_use", "intended_uses"):
                        value = record.get(field)
                        if isinstance(value, str):
                            uses.add(value)
                        elif isinstance(value, list):
                            uses.update(item for item in value if isinstance(item, str))
                touched.update(ref.get("id") for ref in authorization_refs + adoption_refs if isinstance(ref.get("id"), str))
                exact_dependencies = {(record["id"], record["revision"]) for record in changes}
                exact_dependencies.update((r["id"], r["revision"]) for record in changes for r in object_refs(record))
                exact_dependencies.update((r["id"], r["revision"]) for r in authorization_refs + adoption_refs)
                problems = self._blocked(connection, touched, uses, writing=True, revisions=exact_dependencies)
                # Control gates run before idempotency and adoption, including retries.
                if problems:
                    connection.rollback()
                    return self._response("rejected", current_revision, reasons=problems)
                retry = self._receipt(connection, operation_id, "bootstrap" if bootstrap else "commit", index)
                if retry is not None:
                    if retry["status"] == "committed":
                        equal = all(connection.execute("SELECT body FROM records WHERE id=? AND revision=?", (record["id"], record["revision"])).fetchone()[0] == _json(record) for record in changes)
                        equal = equal and all(connection.execute("SELECT content FROM artifacts WHERE path=?", (path,)).fetchone()[0] == content for path, content in artifacts.items())
                        if not equal:
                            retry = self._response("rejected", current_revision, reasons=[_issue("operation_id_reused", "An operation ID cannot describe different record or artifact bytes.")])
                    connection.rollback()
                    return retry
                conflict = self._conflict(connection, expected_state_revision)
                if conflict:
                    connection.rollback()
                    return conflict
                incoming = {(record["id"], record["revision"]): record for record in changes}
                if len(incoming) != len(changes) or len({record["id"] for record in changes}) != len(changes):
                    problems.append(_issue("duplicate_object_change", "A logical commit contains one new revision per object."))
                for record in changes:
                    latest = connection.execute("SELECT revision FROM latest WHERE id=?", (record["id"],)).fetchone()
                    needed_revision = latest[0] + 1 if latest else 1
                    if record["revision"] != needed_revision:
                        problems.append(_issue("object_revision_conflict", "Object revisions are immutable and must advance by one."))
                    if latest:
                        old_type = connection.execute("SELECT kind FROM records WHERE id=? AND revision=?", (record["id"], latest[0])).fetchone()[0]
                        if old_type != record.get("type"):
                            problems.append(_issue("stable_id_type", "A stable object ID cannot be reused for another type."))
                    elif not bootstrap and int(connection.execute("SELECT value FROM meta WHERE key='generation'").fetchone()[0]) > 0 and not record.get("basis_refs"):
                        problems.append(_issue("current_basis_required", "After index removal, new records must cite current surviving basis."))
                    for ref in object_refs(record):
                        if (ref.get("id"), ref.get("revision")) in incoming:
                            continue
                        current = connection.execute("SELECT revision FROM latest WHERE id=?", (ref.get("id"),)).fetchone()
                        if current is None or current[0] != ref.get("revision"):
                            problems.append(_issue("stale_basis_reference", "A new result must cite current surviving object revisions."))
                all_artifacts = {row[0]: row[1] for row in connection.execute("SELECT path,content FROM artifacts")}
                for path, content in artifacts.items():
                    if path in all_artifacts and all_artifacts[path] != content:
                        problems.append(_issue("immutable_artifact", "An original artifact path cannot be overwritten; use a new path."))
                    all_artifacts[path] = content
                for path in artifacts:
                    if not any(path in artifact_paths(record) for record in changes):
                        problems.append(_issue("unreferenced_artifact", "Artifacts must be associated with the submitted canonical objects."))
                all_records = self._all_records(connection) + changes
                try:
                    problems.extend(validate_records(all_records, all_artifacts, synthetic_only=True))
                except (ValueError, TypeError, KeyError, AttributeError):
                    problems.append(_issue("invalid_contract_shape", "Malformed nested contract fields cannot be accepted."))
                if not bootstrap:
                    problems.extend(self._refs_problems(connection, authorization_refs + adoption_refs, "commit"))
                    problems.extend(self._authority_problems(connection, changes, authorization_refs, adoption_refs))
                if problems:
                    connection.rollback()
                    return self._response("rejected", current_revision, reasons=problems)
                for path, content in artifacts.items():
                    connection.execute("INSERT OR IGNORE INTO artifacts VALUES(?,1,?)", (path, content))
                for record in changes:
                    connection.execute("INSERT INTO records VALUES(?,?,?,?,?)", (record["id"], record["revision"], record["type"], record["owner"], _json(record)))
                    connection.execute("INSERT INTO latest VALUES(?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision", (record["id"], record["revision"]))
                    for ref in object_refs(record):
                        connection.execute("INSERT OR IGNORE INTO dependencies VALUES(?,?,?,?,?)", (record["id"], record["revision"], ref["id"], ref["revision"], str(ref.get("locator", ""))))
                    for path in artifact_paths(record):
                        connection.execute("INSERT OR IGNORE INTO artifact_links VALUES(?,?,?)", (record["id"], record["revision"], path))
                    if record["type"] == "UseRestriction" and record.get("status") == "active":
                        for ref in record["scope_refs"]:
                            self._insert_restriction(connection, ref["id"], record["intended_uses"], str(record["reason"]), str(record["issued_by"]))
                self._tick("after_write")
                revision = self._bump(connection)
                receipt = self._response("committed", revision, affected_ids=sorted(record["id"] for record in changes), object_count=len(changes), artifact_count=len(artifacts), synthetic_only=True)
                self._save_receipt(connection, operation_id, "bootstrap" if bootstrap else "commit", index, receipt)
                self._tick("before_publish")
                connection.commit()
                return receipt
        except (TypeError, ValueError, KeyError, AttributeError, UnicodeError):
            return self._response("rejected", reasons=[_issue("invalid_contract_shape", "Malformed contract data cannot be accepted.")])
        except Exception:
            # No raw exception text or rejected content enters the receipt or DB.
            return self._response("not_saved", reasons=[_issue("transaction_failed", "The record transaction was rolled back or its result is unavailable.")])

    @staticmethod
    def _insert_restriction(connection: sqlite3.Connection, identifier: str, uses: list[str], reason: str, actor: str) -> None:
        old = connection.execute("SELECT intended_uses FROM controls WHERE scope_id=? AND kind='restriction'", (identifier,)).fetchone()
        combined = set(uses) | (set(json.loads(old[0])) if old else set())
        connection.execute("INSERT INTO controls VALUES(?,'restriction',?,?,?) ON CONFLICT(scope_id,kind) DO UPDATE SET intended_uses=excluded.intended_uses,reason=excluded.reason,issued_by=excluded.issued_by", (identifier, _json(sorted(combined)), reason, actor))

    def _control(
        self, kind: str, expected_state_revision: int, operation_id: str,
        scope_ids: list[str], reason: str = "", intended_uses: list[str] | None = None,
    ) -> dict[str, Any]:
        problems = self._request_problems(expected_state_revision, operation_id)
        if not isinstance(scope_ids, list) or not scope_ids or any(not isinstance(identifier, str) or not identifier.startswith("FIX-") for identifier in scope_ids):
            problems.append(_issue("invalid_scope", "Control scopes must be a nonempty list of fixture IDs."))
        if kind != "resume" and (not isinstance(reason, str) or not reason):
            problems.append(_issue("control_reason_required", "A control reason is required."))
        uses = intended_uses if intended_uses is not None else ["*"]
        if not isinstance(uses, list) or not uses or any(not isinstance(use, str) or not use for use in uses):
            problems.append(_issue("invalid_intended_uses", "Restrictions need explicit nonempty intended uses."))
        if problems:
            return self._response("rejected", reasons=problems)
        index = {"scope_ids": sorted(set(scope_ids)), "intended_uses": sorted(set(uses)) if kind == "restrict" else [], "actor": self.entry_actor}
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                revision = self._revision(connection)
                if self.entry_actor not in _ACTORS:
                    connection.rollback()
                    return self._response("rejected", revision, reasons=[_issue("unknown_fixture_actor", "Unknown fixture actor.")])
                deleted = set(self._controls(connection)["deleted_ids"])
                if deleted.intersection(scope_ids):
                    connection.rollback()
                    return self._response("rejected", revision, reasons=[_issue("deleted_scope", "A deleted scope cannot be resumed or reused.")])
                for identifier in scope_ids:
                    if connection.execute("SELECT 1 FROM latest WHERE id=?", (identifier,)).fetchone() is None:
                        problems.append(_issue("missing_control_scope", f"Scope {identifier} is absent."))
                if problems:
                    connection.rollback()
                    return self._response("rejected", revision, reasons=problems)
                retry = self._receipt(connection, operation_id, kind, index)
                if retry is not None:
                    if retry["status"] == "committed" and kind != "resume":
                        control_kind = "restriction" if kind == "restrict" else "pause"
                        equal = all((row := connection.execute("SELECT reason FROM controls WHERE scope_id=? AND kind=?", (identifier, control_kind)).fetchone()) is not None and row[0] == reason for identifier in scope_ids)
                        if not equal:
                            retry = self._response("rejected", revision, reasons=[_issue("operation_id_reused", "An operation ID cannot describe a different control reason.")])
                    connection.rollback()
                    return retry
                conflict = self._conflict(connection, expected_state_revision)
                if conflict:
                    connection.rollback()
                    return conflict
                for identifier in sorted(set(scope_ids)):
                    if kind == "restrict":
                        self._insert_restriction(connection, identifier, uses, reason, self.entry_actor)
                    elif kind == "pause":
                        connection.execute("INSERT INTO controls VALUES(?,'pause','[]',?,?) ON CONFLICT(scope_id,kind) DO UPDATE SET reason=excluded.reason,issued_by=excluded.issued_by", (identifier, reason, self.entry_actor))
                    elif kind == "resume":
                        # Resume is user-pause recovery only. Restrictions are untouched.
                        connection.execute("DELETE FROM controls WHERE scope_id=? AND kind='pause'", (identifier,))
                self._tick("after_write")
                revision = self._bump(connection)
                receipt = self._response("committed", revision, affected_ids=sorted(set(scope_ids)), remaining_restriction_count=len(self._controls(connection)["restrictions"]))
                self._save_receipt(connection, operation_id, kind, index, receipt)
                self._tick("before_publish")
                connection.commit()
                return receipt
        except Exception:
            return self._response("not_saved", reasons=[_issue("transaction_failed", "The control transaction was not saved.")])

    def restrict(
        self, expected_state_revision: int, operation_id: str, scope_ids: list[str],
        reason: str, intended_uses: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._control("restrict", expected_state_revision, operation_id, scope_ids, reason, intended_uses)

    def pause(self, expected_state_revision: int, operation_id: str, scope_ids: list[str], reason: str) -> dict[str, Any]:
        return self._control("pause", expected_state_revision, operation_id, scope_ids, reason)

    def resume(self, expected_state_revision: int, operation_id: str, scope_ids: list[str]) -> dict[str, Any]:
        return self._control("resume", expected_state_revision, operation_id, scope_ids)

    def delete_scope(
        self, expected_state_revision: int, operation_id: str, scope_ids: list[str], include_indexes: bool = False,
    ) -> dict[str, Any]:
        problems = self._request_problems(expected_state_revision, operation_id)
        if not isinstance(scope_ids, list) or not scope_ids or any(not isinstance(identifier, str) or not identifier for identifier in scope_ids):
            problems.append(_issue("invalid_scope", "Deletion needs explicit nonempty fixture IDs or managed artifact paths."))
        if not isinstance(include_indexes, bool):
            problems.append(_issue("invalid_index_policy", "include_indexes must be boolean."))
        if problems:
            return self._response("rejected", reasons=problems)
        index = {"scope_ids": sorted(set(scope_ids)), "include_indexes": include_indexes}
        gate_revision: int | None = None
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                revision = self._revision(connection)
                if self.entry_actor not in _ACTORS:
                    connection.rollback()
                    return self._response("rejected", revision, reasons=[_issue("unknown_fixture_actor", "Unknown fixture actor.")])
                retry = self._receipt(connection, operation_id, "delete", index)
                if retry is not None:
                    connection.rollback()
                    return retry
                pending = connection.execute("SELECT * FROM delete_jobs WHERE operation_id=?", (operation_id,)).fetchone()
                if pending is not None:
                    if pending["request_index"] != _json(index):
                        connection.rollback()
                        return self._response("rejected", revision, reasons=[_issue("operation_id_reused", "A pending deletion ID cannot describe a different scope.")])
                    affected_ids = set(json.loads(pending["affected_ids"]))
                    affected_paths = set(json.loads(pending["affected_paths"]))
                    gate_revision = revision
                    connection.rollback()
                else:
                    if connection.execute("SELECT 1 FROM operations WHERE operation_id=?", (operation_id,)).fetchone():
                        connection.rollback()
                        return self._response("rejected", revision, reasons=[_issue("operation_id_reused", "An operation ID cannot change operation kind.")])
                    conflict = self._conflict(connection, expected_state_revision)
                    if conflict:
                        connection.rollback()
                        return conflict
                    records = self._all_records(connection)
                    existing_ids = {record["id"] for record in records}
                    existing_paths = {row[0] for row in connection.execute("SELECT path FROM artifacts")}
                    deleted_markers = set(self._controls(connection)["deleted_ids"])
                    if any(identifier not in existing_ids | existing_paths | deleted_markers for identifier in scope_ids):
                        connection.rollback()
                        return self._response("rejected", revision, reasons=[_issue("missing_delete_scope", "At least one requested scope is not managed by this workspace.")])
                    affected_ids = set(scope_ids).intersection(existing_ids | deleted_markers)
                    affected_paths = set(scope_ids).intersection(existing_paths)
                    # Whole-object closure covers actual refs, free-text scope tokens,
                    # summaries, candidates, validation and all historical revisions.
                    changed = True
                    while changed:
                        changed = False
                        needles = affected_ids | affected_paths
                        for record in records:
                            if record["id"] in affected_ids:
                                paths = artifact_paths(record) - affected_paths
                                if paths:
                                    affected_paths.update(paths)
                                    changed = True
                                continue
                            strings = [item for item in _walk(record) if isinstance(item, str)]
                            if any(_mentions(value, needle) for needle in needles for value in strings):
                                affected_ids.add(record["id"])
                                affected_paths.update(artifact_paths(record))
                                changed = True
                    # Durable stop-use precedes cleanup. A cleanup rollback or process
                    # exit can never reopen these records through any public read API.
                    for identifier in sorted(affected_ids | affected_paths):
                        connection.execute("INSERT INTO controls VALUES(?,'deleted','[]','','') ON CONFLICT(scope_id,kind) DO NOTHING", (identifier,))
                    connection.execute("INSERT INTO delete_jobs VALUES(?,?,?,?)", (operation_id, _json(index), _json(sorted(affected_ids)), _json(sorted(affected_paths))))
                    gate_revision = self._bump(connection)
                    connection.commit()
                self._tick("after_delete_gate")
                connection.execute("BEGIN IMMEDIATE")
                # No ordinary writer can add a dependent record after the durable
                # gate. The remaining cleanup transaction may safely retry by op ID.
                for identifier in sorted(affected_ids):
                    connection.execute("DELETE FROM records WHERE id=?", (identifier,))
                    connection.execute("DELETE FROM controls WHERE scope_id=? AND kind!='deleted'", (identifier,))
                for path in sorted(affected_paths):
                    connection.execute("DELETE FROM artifacts WHERE path=?", (path,))
                    connection.execute("DELETE FROM artifact_links WHERE path=?", (path,))
                # Metadata associated with erased data cannot be used as a hidden copy.
                needles = affected_ids | affected_paths
                for row in connection.execute("SELECT operation_id,request_index,receipt FROM operations").fetchall():
                    strings = [row["operation_id"]] + [item for item in _walk(json.loads(row["request_index"])) if isinstance(item, str)] + [item for item in _walk(json.loads(row["receipt"])) if isinstance(item, str)]
                    if any(_mentions(value, needle) for needle in needles for value in strings):
                        connection.execute("DELETE FROM operations WHERE operation_id=?", (row["operation_id"],))
                connection.execute("DELETE FROM delete_jobs WHERE operation_id=?", (operation_id,))
                # Overlapping pending jobs cannot retain IDs after index-inclusive
                # deletion. They are subsumed only if every affected scope is erased.
                for row in connection.execute("SELECT * FROM delete_jobs").fetchall():
                    pending_ids = set(json.loads(row["affected_ids"]))
                    pending_paths = set(json.loads(row["affected_paths"]))
                    if pending_ids.issubset(affected_ids) and pending_paths.issubset(affected_paths):
                        connection.execute("DELETE FROM delete_jobs WHERE operation_id=?", (row["operation_id"],))
                if include_indexes:
                    for identifier in sorted(affected_ids | affected_paths):
                        connection.execute("DELETE FROM controls WHERE scope_id=?", (identifier,))
                    generation = int(connection.execute("SELECT value FROM meta WHERE key='generation'").fetchone()[0]) + 1
                    connection.execute("UPDATE meta SET value=? WHERE key='generation'", (str(generation),))
                self._tick("after_write")
                revision = self._bump(connection)
                receipt = self._response(
                    "committed", revision, deleted_count=len(affected_ids), cleaned_artifact_count=len(affected_paths),
                    include_indexes=include_indexes, professional_review_required=True,
                    uncontrollable=["external_session_history", "external_backups", "user_copies", "already_loaded_agent_context"],
                )
                if not include_indexes:
                    receipt["deleted_ids"] = sorted(affected_ids)
                    self._save_receipt(connection, operation_id, "delete", index, receipt)
                # Index-inclusive erasure intentionally retains no deletion receipt tied
                # to erased IDs; a stale retry conflicts and must reload current state.
                self._tick("before_publish")
                connection.commit()
                return receipt
        except Exception:
            try:
                with self._connect() as connection:
                    gate_revision = self._revision(connection)
                    pending = connection.execute("SELECT 1 FROM delete_jobs WHERE operation_id=?", (operation_id,)).fetchone() is not None
            except Exception:
                pending = gate_revision is not None
            return self._response("not_saved", gate_revision, pending_cleanup=pending, reasons=[_issue("delete_not_saved", "Deletion cleanup is unconfirmed; a persisted stop-use gate cannot be lifted by resume.")])

    def export_scope(self, scope_ids: list[str], include_artifacts: bool = True) -> dict[str, Any]:
        """Return a JSON-compatible in-memory export without writing a managed copy."""
        if not isinstance(scope_ids, list) or not scope_ids or any(not isinstance(identifier, str) for identifier in scope_ids):
            return self._response("rejected", reasons=[_issue("invalid_scope", "Export needs explicit object IDs.")])
        if not isinstance(include_artifacts, bool):
            return self._response("rejected", reasons=[_issue("invalid_artifact_policy", "include_artifacts must be boolean.")])
        try:
            with self._connect() as connection:
                connection.execute("BEGIN")
                revision = self._revision(connection)
                problems = self._blocked(connection, set(scope_ids), {"read", "export"}, writing=False)
                current = {record["id"]: record for record in self._current_records(connection)}
                if any(identifier not in current for identifier in scope_ids):
                    problems.append(_issue("missing_export_scope", "Export scope must still exist."))
                if problems:
                    connection.rollback()
                    return self._response("rejected", revision, reasons=problems)
                selected_ids = self._closure(connection, set(scope_ids))
                records = [record for record in self._all_records(connection) if record["id"] in selected_ids and not self._blocked(connection, {record["id"]}, {"read", "export"}, writing=False)]
                paths = set().union(*(artifact_paths(record) for record in records)) if records else set()
                artifacts = {row[0]: row[1] for row in connection.execute("SELECT path,content FROM artifacts") if row[0] in paths} if include_artifacts else {}
                missing = [path for path in paths if include_artifacts and path not in artifacts]
                receipt = self._response(
                    "ok", revision, synthetic_only=True, objects=records, artifacts=artifacts, controls=self._controls(connection),
                    limitations=["In-memory export only; saved external copies are outside store control."] + (["Original artifacts are omitted; this export cannot independently reproduce evidence."] if not include_artifacts or missing else []),
                )
                connection.commit()
                return receipt
        except Exception:
            return self._response("not_saved", reasons=[_issue("export_failed", "The selected fixture scope could not be exported.")])

    def check_integrity(self) -> dict[str, Any]:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN")
                revision = self._revision(connection)
                issues: list[dict[str, str]] = []
                for row in connection.execute("PRAGMA integrity_check"):
                    if row[0] != "ok":
                        issues.append(_issue("sqlite_integrity", "SQLite reports a structural integrity problem."))
                if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                    issues.append(_issue("foreign_key_integrity", "Canonical pointers or derived indexes have broken references."))
                records = self._all_records(connection)
                artifacts = {row[0]: row[1] for row in connection.execute("SELECT path,content FROM artifacts")}
                issues.extend(validate_records(records, artifacts, synthetic_only=True))
                deleted = set(self._controls(connection)["deleted_ids"])
                pending_ids: set[str] = set()
                for row in connection.execute("SELECT affected_ids FROM delete_jobs"):
                    pending_ids.update(json.loads(row[0]))
                if pending_ids:
                    issues.append(_issue("pending_deletion_cleanup", "A durable deletion gate remains active pending controlled cleanup."))
                for record in records:
                    final_deleted = deleted - pending_ids
                    if record["id"] in final_deleted or any(ref.get("id") in final_deleted for ref in object_refs(record)):
                        issues.append(_issue("deleted_reference_residue", "A controlled record still references deleted scope."))
                    actual_edges = {(ref["id"], ref["revision"], str(ref.get("locator", ""))) for ref in object_refs(record)}
                    indexed_edges = {tuple(row) for row in connection.execute("SELECT target_id,target_revision,locator FROM dependencies WHERE owner_id=? AND owner_revision=?", (record["id"], record["revision"]))}
                    if actual_edges != indexed_edges:
                        issues.append(_issue("dependency_index_mismatch", "Derived dependency indexes differ from canonical references."))
                    indexed_paths = {row[0] for row in connection.execute("SELECT path FROM artifact_links WHERE owner_id=? AND owner_revision=?", (record["id"], record["revision"]))}
                    if artifact_paths(record) != indexed_paths:
                        issues.append(_issue("artifact_index_mismatch", "Derived artifact indexes differ from canonical artifact references."))
                for row in connection.execute("SELECT id,MAX(revision) FROM records GROUP BY id"):
                    latest = connection.execute("SELECT revision FROM latest WHERE id=?", (row[0],)).fetchone()
                    if latest is None or latest[0] != row[1]:
                        issues.append(_issue("latest_pointer_mismatch", "Current pointers do not identify the latest committed revision."))
                linked_paths = {row[0] for row in connection.execute("SELECT DISTINCT path FROM artifact_links")}
                if set(artifacts) - linked_paths:
                    issues.append(_issue("unreferenced_artifact", "Managed artifact bytes have no canonical object reference."))
                for record in self._current_records(connection):
                    if record.get("type") == "UseRestriction" and record.get("status") == "active":
                        for ref in record.get("scope_refs", []):
                            row = connection.execute("SELECT intended_uses FROM controls WHERE scope_id=? AND kind='restriction'", (ref["id"],)).fetchone()
                            if row is None or not set(record["intended_uses"]).issubset(set(json.loads(row[0]))):
                                issues.append(_issue("omitted_restriction", "An active canonical use restriction is absent from current control gates."))
                result = self._response("rejected" if issues else "ok", revision, issues=issues, synthetic_only=True, object_revision_count=len(records), artifact_count=len(artifacts))
                connection.commit()
                return result
        except Exception:
            return self._response("not_saved", reasons=[_issue("integrity_check_failed", "Workspace integrity could not be verified.")], issues=[])
