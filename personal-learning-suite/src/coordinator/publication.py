"""Install complete version bytes exclusively, then submit coordination metadata."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from .workspace import GateError, sha


def publish_file(coordinator, session, *, source_path, version_path, request):
    """Never overwrite a version, never register a partially copied file.

    File installation and the SQLite commit are separate. A lost/failed commit
    leaves a complete unregistered version for explicit recovery, not adoption.
    """
    task_id = request["task_id"]
    with coordinator.connect() as db:
        db.execute("BEGIN")
        control = coordinator.controls(db)
        task = coordinator.get(db, "tasks", task_id)
        if coordinator.role(session) != task["assignee"] or task["phase"] not in {"running", "submitted"}:
            raise GateError("running_assignee_required")
        coordinator.preflight(db, {"task_id": task_id}, control)
        paths = [(coordinator.root / p).resolve() for p in (source_path, version_path)]
        if any(not p.is_relative_to(coordinator.root) or p.is_relative_to(coordinator.meta_root) or p == coordinator.root for p in paths):
            raise GateError("unsafe_publication_path")
        source, target = paths
        coordinator.assert_version_path(target.relative_to(coordinator.root).as_posix())
        if db.execute("SELECT 1 FROM artifacts WHERE path=?", (source.relative_to(coordinator.root).as_posix(),)).fetchone():
            raise GateError("published_version_cannot_be_mutable_draft")
        data = source.read_bytes()
        if not data:
            raise GateError("empty_artifact")
        digest = sha(data)
        draft = coordinator.draft_record(db, task_id)
        coordinator.validate_content({"path": source.relative_to(coordinator.root).as_posix(), "sha256": digest}, task["output"], {"id": draft["id"], "revision": draft["revision"]}, task["assignee"])
        if sha(source.read_bytes()) != digest:
            raise GateError("draft_changed_during_publication")
        if coordinator.controls(db) != control:
            raise GateError("control_changed_during_publication")
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = None
    try:
        if target.exists():
            if not target.is_file() or sha(target.read_bytes()) != digest:
                raise GateError("published_path_content_conflict")
        else:
            descriptor, name = tempfile.mkstemp(prefix=".tac-pending-", dir=target.parent)
            pending = Path(name)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                # Windows rename refuses an existing destination and works in
                # restricted hosts where creating hard links is forbidden.
                # POSIX rename can overwrite, so use exclusive link there.
                if os.name == "nt":
                    os.rename(pending, target)
                else:
                    os.link(pending, target)
            except FileExistsError:
                if sha(target.read_bytes()) != digest:
                    raise GateError("published_path_content_conflict")
            except OSError:
                # Some restricted Windows hosts forbid rename and hard links.
                # Exclusive creation is safe for the coordination protocol:
                # until all bytes are flushed/validated, this path is unknown
                # to the index and therefore unavailable as a formal input.
                # A crash can leave an unregistered partial file for inspection.
                try:
                    with target.open("xb") as stream:
                        stream.write(data)
                        stream.flush()
                        os.fsync(stream.fileno())
                except FileExistsError:
                    if sha(target.read_bytes()) != digest:
                        raise GateError("published_path_content_conflict")
        if sha(target.read_bytes()) != digest:
            raise GateError("installed_version_fingerprint_mismatch")
        coordinator.checkpoint("after_file_install")
        return coordinator.execute(session, "submit", {**request, "path": target.relative_to(coordinator.root).as_posix()})
    finally:
        if pending and pending.exists():
            pending.unlink()
