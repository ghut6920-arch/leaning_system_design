"""Deterministic lifecycle, impact views and manual-file host boundaries.

The database owns registered versions and coordination facts only. Professional
conclusions come from explicit role receipts, never from content interpretation.
"""
from __future__ import annotations

from contextlib import contextmanager
import difflib
import json

from .reliability import ReliableCoordinator
from .workspace import GateError, encode, identifier, overlaps, ref, scopes, sha
from .preparation_sources import VERSION as SOURCES_VERSION, load_map

COMPLETE_VERSION = "tac-complete/0.1.0"
# These objects already have a dedicated authority; do not create parallel truth.
EXTERNAL_TYPES = {"ControlState", "AuthorizationGrant", "UseRestriction"}
EXTERNAL_PATHS = {"state/control.md", "state/current.md", "plan/current.md", "AGENTS.md", "MODEL_ENTRY.md", "FRAMEWORK.md", "framework-manifest.json", "coordination/control.json", "coordination/entry.json"}


class TaskArtifactCoordinator(ReliableCoordinator):
    def actions(self):
        return super().actions() | {"draft", "bootstrap", "ack_events"}

    @contextmanager
    def connect(self, *, allow_legacy=False):
        with super().connect(allow_legacy=allow_legacy) as db:
            marker = db.execute("SELECT value FROM meta WHERE key='complete_version'").fetchone()
            if marker is None and not allow_legacy:
                raise GateError("complete_upgrade_required")
            if marker is not None and marker[0] != COMPLETE_VERSION:
                raise GateError("unsupported_complete_version")
            yield db

    @staticmethod
    def install(db):
        ReliableCoordinator.install(db)
        db.execute("CREATE TABLE IF NOT EXISTS drafts(task_id TEXT PRIMARY KEY, id TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL, UNIQUE(id,revision))")
        db.execute("CREATE TABLE IF NOT EXISTS lifecycle(id TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(id,revision))")
        db.execute("CREATE TABLE IF NOT EXISTS consumers(id TEXT NOT NULL, role TEXT NOT NULL, sequence INTEGER NOT NULL, PRIMARY KEY(id,role))")
        db.execute("INSERT INTO meta VALUES('complete_version',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (COMPLETE_VERSION,))
        # Explicit upgrades preserve former adoptions and validate existing bytes
        # only on subsequent use. No new professional receipt is fabricated.
        for row in db.execute("SELECT id,revision FROM artifacts").fetchall():
            history = [dict(p) for p in db.execute("SELECT * FROM adopted WHERE id=? AND revision=?", tuple(row))]
            for bundle_row in db.execute("SELECT body FROM bundles"):
                for member in json.loads(bundle_row[0])["members"]:
                    if ref(member["ref"]) == {"id": row[0], "revision": row[1]}:
                        history += [{"intended_use": member["intended_use"], "scope": s} for s in member["scope"]]
            db.execute("INSERT OR IGNORE INTO lifecycle VALUES(?,?,?)", (row[0], row[1], encode({"adoption_history": history, "validation": {"status": "legacy_requires_check"}})))
        for row in db.execute("SELECT body FROM tasks").fetchall():
            task = json.loads(row[0])
            if task["task_kind"] != "production" or task["phase"] not in {"registered", "running", "waiting"} or db.execute("SELECT 1 FROM drafts WHERE task_id=?", (task["id"],)).fetchone():
                continue
            output = task["output"]
            allocated = [r[0] for r in db.execute("SELECT revision FROM artifacts WHERE id=? UNION ALL SELECT revision FROM drafts WHERE id=?", (output["id"], output["id"]))]
            revision = max(allocated, default=0) + 1
            draft = {"task_id": task["id"], "id": output["id"], "revision": revision, "base_ref": None,
                     "scope": task["scope"], "intended_use": task["intended_use"], "owner": task["assignee"], "state": "Draft",
                     "planned_changed_scope": None, "path": None, "validation_profile": "file_integrity", "origin": "explicit_legacy_task_upgrade"}
            db.execute("INSERT INTO drafts VALUES(?,?,?,?)", (task["id"], output["id"], revision, encode(draft)))
            task["draft_ref"] = ref(draft)
            db.execute("UPDATE tasks SET body=? WHERE id=?", (encode(task), task["id"]))

    def initialize(self, *, evidence_kind):
        return {**super().initialize(evidence_kind=evidence_kind), "complete_version": COMPLETE_VERSION}

    def status(self, session):
        with self.connect(allow_legacy=True) as db:
            marker = db.execute("SELECT value FROM meta WHERE key='complete_version'").fetchone()
        if marker is None:
            legacy = ReliableCoordinator(self.root, self.control_gate)
            return {**legacy.status(legacy.bind_local_operator(self.role(session))), "complete_upgrade_required": True}
        return super().status(session)

    @staticmethod
    def draft_record(db, task_id):
        row = db.execute("SELECT body FROM drafts WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise GateError("draft_registration_required")
        return json.loads(row[0])

    def _primary_owner(self, kind):
        specification = self.definition["objects"].get(kind)
        if not specification or kind in EXTERNAL_TYPES or specification["owners"][0] not in {"AG0", "AG1", "AG2", "AG3"}:
            raise GateError("unsupported_managed_type")
        return specification["owners"][0]

    def _register(self, db, role, request, control):
        result = super()._register(db, role, request, control)
        task = self.get(db, "tasks", request["id"])
        if task["task_kind"] == "production":
            output = task["output"]
            candidates = [row[0] for row in db.execute("SELECT revision FROM artifacts WHERE id=? UNION ALL SELECT revision FROM drafts WHERE id=?", (output["id"], output["id"]))]
            revision = max(candidates, default=0) + 1
            base = request.get("base_ref")
            if base:
                existing = self.artifact(db, base)
                if existing["id"] != output["id"] or existing["owner"] != task["assignee"] or existing["type"] != output["type"]:
                    raise GateError("draft_base_mismatch")
                self.gate(control, {existing["id"]}, {existing["intended_use"]})
                self.verify_file(existing)
            elif db.execute("SELECT 1 FROM artifacts WHERE id=?", (output["id"],)).fetchone():
                raise GateError("explicit_revision_base_required")
            planned = request.get("planned_changed_scope")
            if planned is not None and not set(scopes(planned)) <= set(task["scope"]):
                raise GateError("changed_scope_expansion")
            profile = output.get("validation_profile", "file_integrity")
            if profile not in {"file_integrity", "utf8", "contract_fields", "preparation_sources"}:
                raise GateError("unsupported_validation_profile")
            if profile == "preparation_sources" and (output["type"] != "MaterialUse" or task["assignee"] != "AG2"):
                raise GateError("ag2_material_sources_required")
            draft = {"task_id": task["id"], "id": output["id"], "revision": revision,
                     "base_ref": ref(base) if base else None, "scope": task["scope"],
                     "intended_use": task["intended_use"], "owner": task["assignee"],
                     "state": "Draft", "planned_changed_scope": planned, "path": None,
                     "validation_profile": profile}
            if base:
                draft["base_sha256"] = existing["sha256"]
            db.execute("INSERT INTO drafts VALUES(?,?,?,?)", (task["id"], output["id"], revision, encode(draft)))
            task.update(draft_ref=ref(draft), base_ref=draft["base_ref"])
            db.execute("UPDATE tasks SET body=? WHERE id=?", (encode(task), task["id"]))
            result.update(draft_ref=ref(draft), base_ref=draft["base_ref"])
        return result

    def _draft(self, db, role, request, control):
        task = self.get(db, "tasks", request["task_id"])
        if role != task["assignee"] or task["task_kind"] != "production" or task["phase"] not in {"registered", "running", "waiting"}:
            raise GateError("editable_draft_required")
        draft = self.draft_record(db, task["id"])
        # Merely locate the mutable draft; it is never returned by snapshot().
        path = (self.root / request["draft_path"]).resolve()
        if not path.is_relative_to(self.root) or path.is_relative_to(self.meta_root) or path == self.root:
            raise GateError("unsafe_draft_path")
        if db.execute("SELECT 1 FROM artifacts WHERE path=?", (path.relative_to(self.root).as_posix(),)).fetchone():
            raise GateError("draft_cannot_overwrite_version")
        planned = request.get("planned_changed_scope", draft["planned_changed_scope"])
        if planned is not None and not set(scopes(planned)) <= set(task["scope"]):
            raise GateError("changed_scope_expansion")
        draft.update(path=path.relative_to(self.root).as_posix(), planned_changed_scope=planned)
        db.execute("UPDATE drafts SET body=? WHERE task_id=?", (encode(draft), task["id"]))
        return {"task_id": task["id"], "draft_ref": ref(draft), "state": "Draft"}

    def change_scope(self, db, old, new):
        if old["id"] != new["id"] or old["revision"] >= new["revision"]:
            return None
        # Parallel drafts can have a common base rather than form a chain.
        # Numeric revisions alone do not establish a semantic predecessor.
        left, steps, current = {}, [], self.artifact(db, old)
        while True:
            left[current["revision"]] = list(steps)
            if not current.get("base_ref"):
                break
            steps.append(current["changed_scope"])
            current = self.artifact(db, current["base_ref"])
        right, current = [], self.artifact(db, new)
        while current["revision"] not in left:
            if not current.get("base_ref"):
                return None
            right.append(current["changed_scope"])
            current = self.artifact(db, current["base_ref"])
        changes = right + left[current["revision"]]
        return None if any(s is None for s in changes) else sorted({part for change in changes for part in change})

    def validate_content(self, info, output, exact, role):
        checks = ["nonempty", "sha256"]
        profile = output.get("validation_profile", "file_integrity")
        data = (self.root / info["path"]).read_bytes()
        if sha(data) != info["sha256"]:
            raise GateError("artifact_changed_during_validation")
        if profile in {"utf8", "contract_fields"}:
            try:
                text = data.decode("utf-8-sig")
            except UnicodeError as error:
                raise GateError("invalid_utf8") from error
            checks.append("utf8")
        if profile == "contract_fields":
            try:
                value = json.loads(text)
            except ValueError as error:
                raise GateError("invalid_contract_json") from error
            required = self.definition["base_required"] + self.definition["objects"][output["type"]]["required"]
            if not isinstance(value, dict) or any(k not in value for k in required):
                raise GateError("contract_fields_missing")
            if any(value.get(k) != v for k, v in {**exact, "type": output["type"], "owner": role, "schema_version": self.definition["protocol_version"]}.items()) or not isinstance(value["basis_refs"], list):
                raise GateError("contract_identity_mismatch")
            checks.append("shared_required_fields_and_identity")
        if profile == "preparation_sources":
            load_map(self, info, exact=exact)
            checks.append("canonical_source_map_and_member_bytes")
        return {"status": "passed", "profile": profile, "checks": checks,
                "sha256": info["sha256"], "meaning": "structural_checks_not_professional_correctness"}

    def assert_version_path(self, path):
        external = set(EXTERNAL_PATHS)
        if self.control_gate is not None:
            external.update(item["path"] for item in self.control_gate().get("source_refs", []))
            projection = getattr(self.control_gate, "path", None)
            if projection and projection.is_relative_to(self.root):
                external.add(projection.relative_to(self.root).as_posix())
        if path in external:
            raise GateError("external_authority_cannot_be_managed_artifact")

    def verify_file(self, artifact):
        super().verify_file(artifact)
        if artifact.get("preparation_sources_version") == SOURCES_VERSION:
            load_map(self, artifact, exact=artifact, scope=artifact["scope"], intended_use=artifact["intended_use"])

    def _submit(self, db, role, request, control):
        task = self.get(db, "tasks", request["task_id"])
        if task["task_kind"] != "production" or task["phase"] != "running" or role != task["assignee"]:
            raise GateError("running_production_task_required")
        draft = self.draft_record(db, task["id"])
        output, exact = task["output"], ref(draft)
        previous = db.execute("SELECT body FROM artifacts WHERE id=? ORDER BY revision DESC LIMIT 1", (exact["id"],)).fetchone()
        if previous and any(json.loads(previous[0])[k] != v for k, v in {"owner": role, "type": output["type"]}.items()):
            raise GateError("stable_id_type_or_owner_changed")
        # A late older draft may be published for traceability; cannot be mistaken
        # for a replacement of a newer adopted result.
        changed = request.get("changed_scope", draft["planned_changed_scope"])
        if changed is not None and not set(scopes(changed)) <= set(task["scope"]):
            raise GateError("changed_scope_expansion")
        info = self.file_info(request["path"])
        self.assert_version_path(info["path"])
        validation = self.validate_content(info, output, exact, role)
        if output.get("validation_profile") == "preparation_sources":
            load_map(self, info, exact=exact, scope=task["scope"], intended_use=task["intended_use"])
        artifact = {**exact, "owner": role, "type": output["type"], "scope": task["scope"],
                    "intended_use": task["intended_use"], "changed_scope": changed,
                    "requires_ag3_review": output["requires_ag3_review"], "basis_refs": task["snapshot"],
                    "task_id": task["id"], "base_ref": draft["base_ref"], "adoption": {"status": "candidate"}, **info}
        if output.get("validation_profile") == "preparation_sources":
            artifact["preparation_sources_version"] = SOURCES_VERSION
        stamp, issues = self.basis_status(db, artifact)
        db.execute("INSERT INTO artifacts VALUES(?,?,?,?)", (exact["id"], exact["revision"], info["path"], encode(artifact)))
        db.execute("INSERT INTO lifecycle VALUES(?,?,?)", (exact["id"], exact["revision"], encode({"validation": validation, "adoption_history": []})))
        self.checkpoint("after_candidate_insert")
        draft["state"] = "Candidate"
        db.execute("UPDATE drafts SET body=? WHERE task_id=?", (encode(draft), task["id"]))
        task.pop("progress", None)
        task.update(phase="submitted", result_ref=exact, submission_operation_id=request["operation_id"])
        db.execute("UPDATE tasks SET body=? WHERE id=?", (encode(task), task["id"]))
        return {"ref": exact, "adoption": "candidate", "state": "Candidate", "validation": validation,
                "input_issues": issues, "basis_signature": stamp}

    def _input(self, db, item):
        chosen = super()._input(db, item)
        artifact = self.artifact(db, chosen)
        if item["intended_use"] != artifact["intended_use"] or not set(item["scope"]) <= set(artifact["scope"]):
            raise GateError("input_scope_or_use_mismatch")
        if item["policy"] == "exact":
            rows = [db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?", (item["id"], item["intended_use"], s)).fetchone() for s in item["scope"]]
            if any(p is None or p[0] != chosen["revision"] for p in rows):
                if not isinstance(item.get("provisional_conditions"), str) or not item["provisional_conditions"].strip():
                    raise GateError("explicit_provisional_conditions_required")
        return chosen

    def _start(self, db, role, request, control):
        result = super()._start(db, role, request, control)
        task = self.get(db, "tasks", request["task_id"])
        if task["phase"] == "running" and task["task_kind"] == "production":
            snapshot = []
            for item in task["inputs"]:
                chosen = self._input(db, item)
                artifact = self.artifact(db, chosen)
                _, issues = self.basis_status(db, artifact)
                relevant = [i for i in issues if overlaps([i.get("scope", "*")], item["scope"])]
                if relevant and item["policy"] != "exact":
                    raise GateError("adopted_input_requires_recheck")
                snapshot.append({**chosen, "sha256": artifact["sha256"], "scope": item["scope"], "intended_use": item["intended_use"], "adoption_required": True})
                snapshot += self.effective_basis(db, artifact)
            task["snapshot"] = list({encode(i): i for i in snapshot}.values())
            task["provisional_inputs"] = [{"ref": self._input(db, i), "conditions": i["provisional_conditions"]} for i in task["inputs"] if "provisional_conditions" in i]
            db.execute("UPDATE tasks SET body=? WHERE id=?", (encode(task), task["id"]))
            self.preflight(db, {"task_id": task["id"], "intended_use": task["intended_use"]}, control)
            result["snapshot"] = task["snapshot"]
            result["provisional_inputs"] = task["provisional_inputs"]
        return result

    def effective_basis(self, db, artifact):
        """A new task pins explicitly reconciled inputs; old records stay intact."""
        result, pending, seen = [], list(artifact["basis_refs"]), set()
        resolutions = [json.loads(r[0]) for r in db.execute("SELECT body FROM rechecks")]
        while pending:
            item = pending.pop(0)
            if encode(item) in seen:
                continue
            seen.add(encode(item))
            for part in item["scope"]:
                pointer = db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?", (item["id"], item["intended_use"], part)).fetchone()
                resolution = next((r for r in resolutions if r["target_ref"] == ref(artifact) and r["old_ref"] == ref(item) and part in r["scope"] and r["intended_use"] == item["intended_use"] and pointer and r["new_ref"]["revision"] == pointer[0]), None)
                if resolution:
                    new = self.artifact(db, resolution["new_ref"])
                    result.append({**item, **ref(new), "sha256": new["sha256"], "scope": [part], "original_ref": ref(item), "inherited_recheck_id": resolution["id"]})
                    pending += resolution["new_basis_refs"]
                else:
                    result.append({**item, "scope": [part]})
        return list({encode(i): i for i in result}.values())

    def ensure_validation(self, db, artifact):
        life = self.life(db, artifact)
        if life["validation"]["status"] != "passed":
            life["validation"] = self.validate_content(self.file_info(artifact["path"]), {"type": artifact["type"]}, ref(artifact), artifact["owner"])
            db.execute("INSERT INTO lifecycle VALUES(?,?,?) ON CONFLICT(id,revision) DO UPDATE SET body=excluded.body", (artifact["id"], artifact["revision"], encode(life)))

    def _confirm(self, db, role, request, control):
        self.ensure_validation(db, self.artifact(db, request["ref"]))
        return super()._confirm(db, role, request, control)

    def _review(self, db, role, request, control):
        task = self.get(db, "tasks", request["task_id"])
        self.ensure_validation(db, self.artifact(db, task["target_ref"]))
        return super()._review(db, role, request, control)

    def _adopt(self, db, role, request, control):
        if "expected_pointers" not in request:
            raise GateError("explicit_pointer_preconditions_required")
        for member in request["members"]:
            a = self.artifact(db, member["ref"])
            self.ensure_validation(db, a)
            for s in member["scope"]:
                current = db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?", (a["id"], member["intended_use"], s)).fetchone()
                if current and current[0] > a["revision"] and not request.get("rollback_rationale", "").strip():
                    raise GateError("explicit_rollback_rationale_required")
        result = super()._adopt(db, role, request, control)
        for member in request["members"]:
            exact = ref(member["ref"])
            life = self.life(db, exact)
            life["adoption_history"] += [{"intended_use": member["intended_use"], "scope": s, "bundle_id": request["bundle_id"]} for s in member["scope"]]
            db.execute("UPDATE lifecycle SET body=? WHERE id=? AND revision=?", (encode(life), exact["id"], exact["revision"]))
        return result

    def life(self, db, exact):
        row = db.execute("SELECT body FROM lifecycle WHERE id=? AND revision=?", (exact["id"], exact["revision"])).fetchone()
        return json.loads(row[0]) if row else {"adoption_history": [], "validation": {"status": "legacy_requires_check"}}

    def preflight(self, db, request, control):
        if "base_ref" in request and request["base_ref"]:
            self.gate(control, {request["base_ref"]["id"]}, {request.get("intended_use", "coordination")})
        extra = []
        if request.get("task_id"):
            row = db.execute("SELECT body FROM drafts WHERE task_id=?", (request["task_id"],)).fetchone()
            draft = json.loads(row[0]) if row else None
            if draft and draft["base_ref"]:
                base = self.artifact(db, draft["base_ref"])
                self.gate(control, {base["id"]}, {base["intended_use"]})
                self.verify_file(base)
        for entry in request.get("entries", []):
            self.gate(control, {identifier(entry["id"])} | {r["id"] for r in entry.get("basis_refs", [])}, {entry["intended_use"]})
        # All source/entry metadata is gated before any import body is read.
        for entry in request.get("entries", []):
            extra.append(self.file_info(entry["path"]))
            for proof in entry.get("adoption_evidence", []):
                extra.append(self.file_info(proof["path"]))
            for compatibility in entry.get("basis_compatibility", []):
                for proof in compatibility.get("evidence", []):
                    extra.append(self.file_info(proof["path"]))
        infos = super().preflight(db, request, control) + extra
        original_count = len(infos)
        # Bind member bytes to the original prepared ticket as well. The base
        # preflight gates all scopes/uses before this body inspection.
        for info in list(infos):
            row = db.execute("SELECT body FROM artifacts WHERE path=?", (info["path"],)).fetchone()
            if row:
                artifact = json.loads(row[0])
                if artifact.get("preparation_sources_version") == SOURCES_VERSION:
                    _, members = load_map(self, artifact, exact=artifact, scope=artifact["scope"], intended_use=artifact["intended_use"])
                    infos.extend(members)
        if request.get("task_id") and request.get("path"):
            task = self.get(db, "tasks", request["task_id"])
            if task.get("output", {}).get("validation_profile") == "preparation_sources":
                _, members = load_map(self, self.file_info(request["path"]), exact=task["draft_ref"],
                                      scope=task["scope"], intended_use=task["intended_use"])
                infos.extend(members)
        # Preserve the original order/duplicates for existing frozen tickets;
        # deduplicate only the newly appended source-map member inventory.
        seen = {info["path"] for info in infos[:original_count]}
        members = []
        for info in infos[original_count:]:
            if info["path"] not in seen:
                members.append(info)
                seen.add(info["path"])
        return infos[:original_count] + members

    def check_evidence(self, evidence):
        if not isinstance(evidence, list) or not evidence:
            raise GateError("bootstrap_adoption_evidence_required")
        for proof in evidence:
            source = self.file_info(proof["path"])
            if source["sha256"] != proof.get("sha256") or not isinstance(proof.get("anchor"), str) or not proof["anchor"].strip():
                raise GateError("bootstrap_adoption_evidence_required")
            if (self.root / source["path"]).read_text(encoding="utf-8-sig").count(proof["anchor"]) != 1:
                raise GateError("bootstrap_evidence_anchor_not_unique")

    def _bootstrap(self, db, role, request, control):
        if role != "AG0" or db.execute("SELECT 1 FROM artifacts").fetchone():
            raise GateError("empty_ag0_bootstrap_required")
        entries = request.get("entries")
        if not isinstance(entries, list) or not entries:
            raise GateError("explicit_bootstrap_entries_required")
        for entry in entries:
            exact = ref(entry)
            owner = self._primary_owner(entry["type"])
            scope, use = scopes(entry["scope"]), identifier(entry["intended_use"])
            info = self.file_info(entry["path"])
            self.assert_version_path(info["path"])
            if info["sha256"] != entry.get("sha256"):
                raise GateError("bootstrap_fingerprint_mismatch")
            evidence = entry.get("adoption_evidence", [])
            if evidence:
                self.check_evidence(evidence)
            if entry.get("adopted") is True and (not evidence or not entry.get("adoption_rationale", "").strip()):
                raise GateError("bootstrap_adoption_evidence_required")
            basis = entry.get("basis_refs", [])
            if not isinstance(basis, list):
                raise GateError("explicit_inputs_required")
            pinned = []
            for item in basis:
                upstream = self.artifact(db, item)  # explicit topological import
                if item["intended_use"] != upstream["intended_use"] or not set(scopes(item["scope"])) <= set(upstream["scope"]):
                    raise GateError("input_scope_or_use_mismatch")
                pinned += [{**ref(item), "sha256": upstream["sha256"], "scope": item["scope"], "intended_use": item["intended_use"], "adoption_required": True}] + upstream["basis_refs"]
            artifact = {**exact, **info, "type": entry["type"], "owner": owner, "scope": scope,
                        "intended_use": use, "basis_refs": list({encode(i): i for i in pinned}.values()), "changed_scope": None,
                        "requires_ag3_review": entry["requires_ag3_review"], "task_id": None,
                        "adoption": {"status": "candidate"}, "origin": "explicit_historical_file_registration"}
            if type(entry["requires_ag3_review"]) is not bool:
                raise GateError("explicit_review_policy_required")
            db.execute("INSERT INTO artifacts VALUES(?,?,?,?)", (exact["id"], exact["revision"], info["path"], encode(artifact)))
            history = [{"intended_use": use, "scope": s, "origin": "historical_adoption_attestation"} for s in scope] if entry.get("adopted") is True else []
            life = {"validation": self.validate_content(info, {"type": entry["type"]}, exact, owner),
                    "adoption_history": history, "historical_adoption_evidence": evidence,
                    "adoption_rationale": entry.get("adoption_rationale"), "meaning": "historical_pointer_not_new_professional_review"}
            db.execute("INSERT INTO lifecycle VALUES(?,?,?)", (exact["id"], exact["revision"], encode(life)))
            if history:
                db.executemany("INSERT INTO adopted VALUES(?,?,?,?)", [(exact["id"], use, s, exact["revision"]) for s in scope])
        # Compatibility is migrated only with a pinned original declaration.
        # It is labelled as history, never as a newly executed owner decision.
        for entry in entries:
            for compatibility in entry.get("basis_compatibility", []):
                self.check_evidence(compatibility.get("evidence"))
                target = self.artifact(db, entry)
                request_part = {**compatibility, "ref": ref(entry)}
                result = super()._recheck(db, target["owner"], request_part, control)
                recorded = self.get(db, "rechecks", result["recheck_id"])
                recorded.update(origin="historical_compatibility_registration", evidence=compatibility["evidence"],
                                meaning="registration_of_explicit_original_compatibility_not_new_review")
                db.execute("UPDATE rechecks SET body=? WHERE id=?", (encode(recorded), result["recheck_id"]))
        # A migrated pointer must have a coherent migrated dependency collection.
        for entry in entries:
            if entry.get("adopted") is True and self.basis_status(db, self.artifact(db, entry))[1]:
                raise GateError("bootstrap_basis_not_adopted")
        return {"imported_refs": [ref(e) for e in entries], "meaning": "explicit_historical_registration_no_new_review"}

    def context(self, db, request):
        result = super().context(db, request)
        for entry in request.get("entries", []):
            result["scope_ids"] += [entry["id"]] + [b["id"] for b in entry.get("basis_refs", [])]
            result["intended_uses"].append(entry["intended_use"])
        result["scope_ids"] = sorted(set(result["scope_ids"]))
        result["intended_uses"] = sorted(set(result["intended_uses"]))
        return result

    def visible(self, control, ids, uses):
        try:
            self.gate(control, ids, uses)
            return True
        except GateError:
            return False

    def impacts(self, db, control):
        artifacts = [json.loads(r[0]) for r in db.execute("SELECT body FROM artifacts")]
        tasks = [json.loads(r[0]) for r in db.execute("SELECT body FROM tasks")]
        rows = []
        for target_kind, targets in (("artifact", artifacts), ("task", tasks)):
            for target in targets:
                if target_kind == "task" and target["phase"] not in {"registered", "running", "waiting"}:
                    continue
                if target_kind == "artifact" and all((db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?", (target["id"], target["intended_use"], s)).fetchone() or (0,))[0] > target["revision"] for s in target["scope"]):
                    # Retired historical bodies are not current work to repair.
                    # Active tasks/outputs pinned to them have their own notices.
                    continue
                dependencies = target.get("basis_refs", target.get("snapshot", []))
                if target_kind == "task" and not dependencies and target["task_kind"] == "production":
                    dependencies = []
                    for item in target["inputs"]:
                        try:
                            chosen = ref(item) if item["policy"] == "exact" else self._input(db, item)
                            dependencies.append({**chosen, "scope": item["scope"], "intended_use": item["intended_use"]})
                        except (GateError, KeyError, TypeError):
                            # No available version yet: bounded wait/reporting is
                            # responsible, not a guessed historical snapshot.
                            continue
                for basis in dependencies:
                    for updated in artifacts:
                        if updated["id"] != basis["id"] or updated["revision"] <= basis["revision"] or updated["intended_use"] != basis["intended_use"]:
                            continue
                        affected = [s for s in basis["scope"] if overlaps(self.change_scope(db, basis, updated), [s])]
                        if not affected:
                            continue
                        adopted = [s for s in affected if (db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?", (updated["id"], updated["intended_use"], s)).fetchone() or (None,))[0] == updated["revision"]]
                        # Ignore formerly adopted versions already replaced again.
                        pointers = [db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?", (updated["id"], updated["intended_use"], s)).fetchone() for s in affected]
                        if all(p and p[0] > updated["revision"] for p in pointers):
                            continue
                        ids = {target["id"], basis["id"]} | {b["id"] for b in dependencies}
                        uses = {target["intended_use"], basis["intended_use"]}
                        if not self.visible(control, ids, uses):
                            continue
                        for severity, parts in (("recheck_required", adopted), ("candidate_warning", sorted(set(affected) - set(adopted)))):
                            if not parts:
                                continue
                            if target_kind == "artifact" and severity == "recheck_required":
                                resolved = [json.loads(r[0]) for r in db.execute("SELECT body FROM rechecks")]
                                parts = [s for s in parts if not any(r["target_ref"] == ref(target) and r["old_ref"] == ref(basis) and r["new_ref"] == ref(updated) and r["intended_use"] == basis["intended_use"] and s in r["scope"] for r in resolved)]
                            if parts:
                                rows.append({"target_kind": target_kind, "target_id": target["id"],
                                             "target_ref": ref(target) if target_kind == "artifact" else None,
                                             "old_ref": ref(basis), "new_ref": ref(updated), "scope": parts,
                                             "intended_use": basis["intended_use"], "severity": severity,
                                             "next_owner": target.get("owner", target.get("assignee")),
                                             "next_action": "compare_declared_change_before_adoption" if severity == "candidate_warning" else "local_recheck_or_new_revision"})
                if target_kind == "task" and target["task_kind"] == "review":
                    for updated in artifacts:
                        if updated["id"] == target["target_ref"]["id"] and updated["revision"] > target["target_ref"]["revision"] and self.visible(control, {updated["id"], target["id"]}, {target["intended_use"]}):
                            rows.append({"target_kind": "task", "target_id": target["id"], "old_ref": target["target_ref"], "new_ref": ref(updated),
                                         "scope": target["scope"], "severity": "review_target_warning", "next_owner": "AG0",
                                         "next_action": "keep_review_binding_or_assign_supplement"})
        return list({encode(r): r for r in rows}.values())

    def decorate_status(self, db, result):
        result = super().decorate_status(db, result)
        control = self.controls(db)
        # Unlike historical base views, all detailed metadata observes current
        # pause/use gates as well as deletion before file validation.
        result["artifacts"] = [a for a in result["artifacts"] if self.visible(control, {a["id"]} | {b["id"] for b in a["basis_refs"] + self.recheck_inputs(db, a)}, {a["intended_use"]} | {b["intended_use"] for b in a["basis_refs"] + self.recheck_inputs(db, a)})]
        result["tasks"] = [t for t in result["tasks"] if self.visible(control, {t["id"]} | {b["id"] for b in t["snapshot"] + t["inputs"]} | {b["producer_task_id"] for b in t["inputs"] if b.get("producer_task_id")} | ({t["output"]["id"]} if t["output"] else {t["target_ref"]["id"]}), {t["intended_use"]} | {b["intended_use"] for b in t["snapshot"] + t["inputs"]})]
        visible = {(a["id"], a["revision"]) for a in result["artifacts"]}
        result["adopted_pointers"] = [p for p in result["adopted_pointers"] if (p["id"], p["revision"]) in visible]
        for a in result["artifacts"]:
            life = self.life(db, a)
            issues = []
            try:
                self.preflight(db, {"ref": ref(a), "intended_use": a["intended_use"]}, control)
                stamp, issues = self.basis_status(db, a)
                opinions, retired = self.active_opinions(db, a, a["intended_use"], stamp)
            except (GateError, OSError) as error:
                issues = [{"code": getattr(error, "code", "artifact_unavailable")}]
                opinions, retired = [], set()
            verified, reasons = [], []
            for part in a["scope"]:
                relevant = [r for r in opinions if r["id"] not in retired and part in r["scope"]]
                part_issues = [i for i in issues if "scope" not in i or overlaps([i["scope"]], [part])]
                if not part_issues and life["validation"]["status"] == "passed" and not any(r["outcome"] != "supported" for r in relevant) and any(r["kind"] == "professional_confirmation" and r["by"] == a["owner"] for r in relevant) and (not a["requires_ag3_review"] or any(r["kind"] == "ag3_review" for r in relevant)):
                    verified.append(part)
                else:
                    reasons.append({"scope": part, "next_owner": a["owner"] if not any(r["kind"] == "professional_confirmation" and r["outcome"] == "supported" for r in relevant) else "AG3" if a["requires_ag3_review"] else a["owner"]})
            adopted = a["adoption"]["scope"]
            ever = {h["scope"] for h in life["adoption_history"] if h["intended_use"] == a["intended_use"]}
            replaced = sorted((ever - set(adopted)) | {s for s in a["scope"] if (db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?", (a["id"], a["intended_use"], s)).fetchone() or (0,))[0] > a["revision"]})
            state = "Adopted" if adopted else "Superseded" if replaced else "Verified" if set(verified) == set(a["scope"]) else "Candidate"
            scope_states = {s: "Adopted" if s in adopted else "Superseded" if s in replaced else "Verified" if s in verified else "Candidate" for s in a["scope"]}
            a.update(state=state, verified_scope=verified, superseded_scope=replaced, validation=life["validation"], input_issues=issues,
                     scope_states=scope_states,
                     eligibility="pending_recheck" if issues else "usable" if adopted or set(verified) == set(a["scope"]) else "pending_review",
                     verification_pending=reasons, historical_adoption=bool(life.get("historical_adoption_evidence")))
            if state == "Superseded":
                a["adoption"]["status"] = "superseded"
        by_ref = {(a["id"], a["revision"]): a for a in result["artifacts"]}
        receipts = {json.loads(r[0])["id"]: json.loads(r[0]) for r in db.execute("SELECT body FROM receipts")}
        operations = [json.loads(r[0]) for r in db.execute("SELECT body FROM operations")]
        for task in result["tasks"]:
            # Historical percentage fields are ignored in current views; retain
            # original stored records instead of rewriting past receipts.
            task.pop("progress", None)
            phase = task.get("effective_phase", task["phase"])
            task["work_status"] = "running" if phase == "running" else "submitted" if phase == "submitted" else "blocked" if phase in {"waiting", "blocked", "failed", "cancelled"} else None
            task["output_receipt"] = None
            if task["work_status"] == "blocked":
                task["blocked_reason"] = task.get("stop_reason") or ("waiting_for_dependency" if phase == "waiting" else phase)
            if task.get("result_ref"):
                target = by_ref.get((task["result_ref"]["id"], task["result_ref"]["revision"]))
                if target:
                    operation = next((o["operation_id"] for o in operations if o.get("ref") == task["result_ref"]), None)
                    task["output_receipt"] = {"kind": "artifact_submission", "operation_id": task.get("submission_operation_id") or operation,
                                              "ref": ref(target), "path": target["path"], "sha256": target["sha256"],
                                              "validation": target["validation"], "adoption_state": target["state"],
                                              "meaning": "registered_file_submission_not_adoption"}
            elif task.get("receipt_id"):
                receipt = receipts.get(task["receipt_id"])
                if receipt and (receipt["target_ref"]["id"], receipt["target_ref"]["revision"]) in visible:
                    operation = next((o["operation_id"] for o in operations if o.get("receipt_id") == task["receipt_id"]), None)
                    task["output_receipt"] = {"kind": "review_submission", "operation_id": operation, "receipt_id": receipt["id"],
                                              "target_ref": receipt["target_ref"], "target_sha256": receipt["target_sha256"],
                                              "basis_signature": receipt["basis_signature"], "scope": receipt["scope"],
                                              "outcome": receipt["outcome"], "meaning": "version_bound_review_not_adoption"}
        task_ids = {t["id"] for t in result["tasks"]}
        result["drafts"] = [json.loads(r[0]) for r in db.execute("SELECT body FROM drafts ORDER BY id,revision") if json.loads(r[0])["task_id"] in task_ids and json.loads(r[0])["state"] == "Draft"]
        for draft in result["drafts"]:
            task = next(t for t in result["tasks"] if t["id"] == draft["task_id"])
            draft["task_phase"] = task["phase"]
            draft["usable"] = False
        result.update(complete_version=COMPLETE_VERSION, impacts=self.impacts(db, control),
                      authority={"coordination": "sqlite_registered_versions_tasks_receipts_pointers", "external": ["state/control.md", "state/current.md", "plan/current.md"], "professional_decisions": "explicit_role_receipts"})
        result["receipts"] = [json.loads(row[0]) for row in db.execute("SELECT body FROM receipts") if (json.loads(row[0])["target_ref"]["id"], json.loads(row[0])["target_ref"]["revision"]) in visible]
        result["dependency_edges"] = [{"consumer": {"kind": "artifact", "ref": ref(a)}, "input": {**ref(b), "sha256": b["sha256"]},
                                      "scope": b["scope"], "intended_use": b["intended_use"], "relation": "depends_on", "provenance": "registered_version_basis"}
                                     for a in result["artifacts"] for b in a["basis_refs"]]
        result["dependency_edges"] += [{"consumer": {"kind": "task", "id": t["id"]}, "input": b,
                                       "scope": b["scope"], "intended_use": b["intended_use"], "relation": "depends_on", "provenance": "declared_task_input"}
                                      for t in result["tasks"] for b in t["inputs"]]
        result["summary"] = self.summarize(result)
        if encode(self.controls(db)) != encode(control):
            raise GateError("control_changed_during_read")
        return result

    @staticmethod
    def summarize(state):
        rows = []
        for a in state["artifacts"]:
            if a["state"] == "Superseded":
                continue
            if a["input_issues"]:
                action, owner = "核对上游变化，局部复核或提交修订", a["owner"]
            elif a["state"] == "Adopted":
                action, owner = "可按已采用范围使用", None
            elif a["state"] == "Verified":
                action, owner = "等待AG0决定是否采用", "AG0"
            else:
                pending = a["verification_pending"]
                owner = pending[0]["next_owner"] if pending else a["owner"]
                action = "等待专业确认" if owner == a["owner"] else "等待AG3审查"
            rows.append({"kind": "artifact", "ref": ref(a), "state": a["state"], "scope": a["adoption"]["scope"] if a["state"] == "Adopted" else a["scope"], "intended_use": a["intended_use"], "next_owner": owner, "next_action": action,
                         "scope_states": a["scope_states"]})
        for t in state["tasks"]:
            if t["work_status"] is None:
                continue
            phase = t["work_status"]
            rows.append({"kind": "task", "task_id": t["id"], "state": phase,
                         "ref": t.get("target_ref") or t.get("draft_ref"), "scope": t["scope"],
                         "next_owner": None if phase == "submitted" else t.get("next_owner", t["requester"] if phase == "blocked" else t["assignee"]),
                         "next_action": "查看实际提交回执；采用另行核对" if phase == "submitted" else "等待指定上游结果" if t["phase"] == "waiting" and not t.get("stop_reason") else "处理阻塞原因或重新安排" if phase == "blocked" else "继续当前任务",
                         "blocked_reason": t.get("blocked_reason"), "output_receipt": t["output_receipt"]})
        return rows

    def brief(self, session):
        state = self.status(session)
        lines = [f"协作状态 · revision {state['state_revision']}", "", "| 任务或产物 | 状态 | 下一责任人 | 后续动作 |", "|---|---|---|---|"]
        def cell(value):
            return str(value).replace("|", "\\|").replace("\n", " ")
        for row in state["summary"]:
            name = row.get("task_id") or f"{row['ref']['id']} v{row['ref']['revision']}"
            action = row["next_action"]
            receipt = row.get("output_receipt")
            if receipt:
                action += "：" + (receipt.get("receipt_id") or f"{receipt['ref']['id']} v{receipt['ref']['revision']}")
            if row.get("blocked_reason"):
                action += "：" + row["blocked_reason"]
            lines.append("| " + " | ".join(cell(v) for v in [name, row["state"], row["next_owner"] or "—", action]) + " |")
        if state["impacts"]:
            lines += ["", f"依赖影响：{len(state['impacts'])} 项；候选预警不自动替换当前采用输入。"]
        return "\n".join(lines) + "\n"

    def boundary(self, session, task_id):
        state = self.status(session)
        task = next((t for t in state["tasks"] if t["id"] == task_id), None)
        if task is None:
            raise GateError("task_unavailable_under_current_controls")
        if self.role(session) not in {"AG0", task["assignee"], task["requester"]}:
            raise GateError("task_assignee_required")
        return {"status": "ok", "state_revision": state["state_revision"], "task": task,
                "impacts": [i for i in state["impacts"] if i["target_id"] == task_id or i.get("target_ref") == task.get("result_ref")],
                "meaning": "read_only_checkpoint_not_permission_to_adopt"}

    def inbox(self, session, consumer_id, *, limit=100):
        role, consumer = self.role(session), identifier(consumer_id)
        with self.connect() as db:
            row = db.execute("SELECT sequence FROM consumers WHERE id=? AND role=?", (consumer, role)).fetchone()
            cursor = row[0] if row else 0
        stream = self.events(session, after_sequence=cursor, limit=limit)
        return {**stream, "consumer_id": consumer, "acknowledged_sequence": cursor,
                "meaning": "local_host_pull_ack_only_after_context_received"}

    def _ack_events(self, db, role, request, control):
        consumer, sequence = identifier(request["consumer_id"]), request["through_sequence"]
        latest = db.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0]
        if type(sequence) is not int or sequence < 0 or sequence > latest:
            raise GateError("invalid_ack_sequence")
        previous = db.execute("SELECT sequence FROM consumers WHERE id=? AND role=?", (consumer, role)).fetchone()
        if previous and sequence < previous[0]:
            raise GateError("ack_cursor_cannot_rewind")
        db.execute("INSERT INTO consumers VALUES(?,?,?) ON CONFLICT(id,role) DO UPDATE SET sequence=excluded.sequence", (consumer, role, sequence))
        return {"consumer_id": consumer, "acknowledged_sequence": sequence}

    def after_action(self, db, role, action, request, result, control):
        if action == "ack_events":
            # An acknowledgement is durable but must not notify about itself.
            return
        super().after_action(db, role, action, request, result, control)
        if action in {"submit", "adopt", "recheck"}:
            affected = self.impacts(db, control)
            result["affected_downstream"] = affected
            previous = {encode({k: v for k, v in json.loads(row[0]).items() if k not in {"kind", "scope_ids", "intended_uses"}}) for row in db.execute("SELECT body FROM events") if json.loads(row[0]).get("kind") == "dependency_impact"}
            for item in affected:
                if encode(item) in previous:
                    continue
                self.emit(db, request["operation_id"], {"kind": "dependency_impact", **item,
                          "scope_ids": sorted({item["target_id"], item["old_ref"]["id"], item["new_ref"]["id"]}),
                          "intended_uses": [item.get("intended_use", "coordination")]})

    def read_snapshot(self, session, task_id):
        result = super().read_snapshot(session, task_id)
        with self.connect() as db:
            db.execute("BEGIN")
            control = self.controls(db)
            row = db.execute("SELECT body FROM drafts WHERE task_id=?", (task_id,)).fetchone()
            draft = json.loads(row[0]) if row else None
            if draft and draft["base_ref"] and not any(i["ref"] == draft["base_ref"] for i in result):
                base = self.artifact(db, draft["base_ref"])
                self.gate(control, {task_id, base["id"]}, {base["intended_use"]})
                self.verify_file(base)
                content = (self.root / base["path"]).read_bytes()
                if sha(content) != draft["base_sha256"]:
                    raise GateError("edit_base_fingerprint_changed")
                result.append({"ref": ref(base), "sha256": base["sha256"], "path": base["path"], "content": content, "kind": "edit_base"})
            # Gate all returned content again if the external source changed
            # between the first snapshot transaction and the edit-base read.
            self.gate(control, {task_id} | {i["ref"]["id"] for i in result}, {self.artifact(db, i["ref"])["intended_use"] for i in result})
            if encode(self.controls(db)) != encode(control):
                raise GateError("control_changed_during_read")
        return result

    def diff(self, session, old_ref, new_ref):
        self.role(session)
        with self.connect() as db:
            db.execute("BEGIN")
            control = self.controls(db)
            old, new = self.artifact(db, old_ref), self.artifact(db, new_ref)
            if old["id"] != new["id"]:
                raise GateError("diff_requires_same_artifact")
            self.preflight(db, {"old_ref": old_ref, "new_ref": new_ref, "intended_use": new["intended_use"]}, control)
            try:
                left, right = [(self.root / a["path"]).read_text(encoding="utf-8-sig").splitlines(keepends=True) for a in (old, new)]
                difference = "".join(difflib.unified_diff(left, right, fromfile=old["path"], tofile=new["path"]))
            except UnicodeError:
                difference = None
            self.verify_file(old)
            self.verify_file(new)
            if encode(self.controls(db)) != encode(control):
                raise GateError("control_changed_during_read")
            return {"status": "ok", "old_ref": ref(old), "new_ref": ref(new), "old_sha256": old["sha256"], "new_sha256": new["sha256"],
                    "changed_scope": self.change_scope(db, old, new), "text_diff": difference, "meaning": "byte_diff_plus_declared_scope_not_semantic_judgment"}

    def preparation_source(self, session, source_id, *, task_id=None, input_index=None,
                           artifact_id=None, intended_use=None, scope=None):
        # Establish the same read authority as normal inputs/current; no path
        # supplied by the caller can select an unrelated file.
        if task_id is not None:
            items = self.read_snapshot(session, task_id)
            if type(input_index) is not int or not 0 <= input_index < len(items):
                raise GateError("select_preparation_map_input")
            parent = items[input_index]
        else:
            parent = self.resolve(session, artifact_id, intended_use, scope)
        with self.connect() as db:
            db.execute("BEGIN")
            control = self.controls(db)
            request = {"ref": parent["ref"]}
            if task_id is not None:
                request["task_id"] = task_id
                task = self.get(db, "tasks", task_id)
                if self.role(session) not in {task["assignee"], task["requester"]} or task["phase"] not in {"running", "submitted"}:
                    raise GateError("task_snapshot_not_available")
            else:
                current = self._input(db, {"id": artifact_id, "intended_use": intended_use, "scope": scopes(scope), "policy": "adopted"})
                if ref(current) != parent["ref"]:
                    raise GateError("read_version_changed")
            self.preflight(db, request, control)
            artifact = self.artifact(db, parent["ref"])
            if artifact.get("preparation_sources_version") != SOURCES_VERSION:
                raise GateError("preparation_map_required")
            if task_id is None:
                _, issues = self.basis_status(db, artifact)
                if issues:
                    raise GateError("adopted_input_requires_recheck")
                self.check_opinions(db, artifact, intended_use, scope)
            elif task["task_kind"] == "production":
                item = next((i for i in task["snapshot"] if ref(i) == parent["ref"]), None)
                if item is None:
                    raise GateError("preparation_map_required")
                self.check_opinions(db, artifact, item["intended_use"], item["scope"])
            value, _ = load_map(self, artifact, exact=artifact, scope=artifact["scope"], intended_use=artifact["intended_use"])
            member = next((e for e in value["entries"] if e["id"] == source_id), None)
            if member is None:
                raise GateError("preparation_source_not_found")
            data = (self.root / member["path"]).read_bytes()
            if sha(data) != member["sha256"] or len(data) != member["bytes"]:
                raise GateError("preparation_source_fingerprint_changed")
            self.verify_file(artifact)
            if encode(self.controls(db)) != encode(control):
                raise GateError("control_changed_during_read")
            return {"ref": parent["ref"], "map_path": artifact["path"], "source_id": member["id"],
                    "source_kind": member["kind"], "path": member["path"], "sha256": member["sha256"],
                    "content": data, "meaning": "member_of_verified_fixed_map_not_professional_read_or_adoption"}

    def resolve(self, session, artifact_id, intended_use, scope):
        """Read the formal input through the scoped pointer, never max(revision)."""
        self.role(session)
        with self.connect() as db:
            db.execute("BEGIN")
            control = self.controls(db)
            self.gate(control, {identifier(artifact_id)}, {identifier(intended_use)})
            item = {"id": artifact_id, "intended_use": intended_use, "scope": scopes(scope), "policy": "adopted"}
            exact = self._input(db, item)
            self.preflight(db, {"ref": exact, "intended_use": intended_use}, control)
            artifact = self.artifact(db, exact)
            _, issues = self.basis_status(db, artifact)
            if issues:
                raise GateError("adopted_input_requires_recheck")
            self.check_opinions(db, artifact, intended_use, scope)
            data = (self.root / artifact["path"]).read_bytes()
            if sha(data) != artifact["sha256"]:
                raise GateError("artifact_fingerprint_changed")
            if encode(self.controls(db)) != encode(control):
                raise GateError("control_changed_during_read")
            return {"ref": exact, "path": artifact["path"], "sha256": artifact["sha256"], "content": data,
                    "scope": item["scope"], "intended_use": intended_use, "meaning": "scoped_adopted_input_not_latest_file"}

    def receipt(self, session, receipt_id):
        role = self.role(session)
        with self.connect() as db:
            db.execute("BEGIN")
            control = self.controls(db)
            record = self.get(db, "receipts", identifier(receipt_id))
            if role not in {"AG0", record["by"]}:
                raise GateError("receipt_role_scope")
            self.preflight(db, {"ref": record["target_ref"], "intended_use": record["intended_use"]}, control)
            target = self.artifact(db, record["target_ref"])
            stamp, issues = self.basis_status(db, target)
            _, retired = self.active_opinions(db, target, record["intended_use"], stamp)
            applicable = not issues and record["basis_signature"] == stamp and record["target_sha256"] == target["sha256"] and record["id"] not in retired
            if encode(self.controls(db)) != encode(control):
                raise GateError("control_changed_during_read")
            return {"status": "ok", "receipt": record, "currently_applicable_to_exact_target": applicable,
                    "input_issues": issues, "meaning": "exact_target_scope_receipt_not_newer_version_or_adoption"}
