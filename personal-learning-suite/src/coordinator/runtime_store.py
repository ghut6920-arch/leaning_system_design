"""Durable, local execution ledger. Business tables remain authoritative.

All transactions are short; host calls are deliberately outside this module.
Session roles are trusted-local attestations, just like the existing coordinator.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from .workspace import GateError, encode, identifier, ref, sha

RUNTIME_VERSION = "tac-runtime/0.1.0"
TERMINAL = {"done", "failed", "cancelled", "superseded"}
UNCERTAIN = {"dispatch_unknown", "execution_unknown", "needs_user"}
BUSY = {"claimed", "dispatching", "accepted", "running", "result_saved", "committed", "host_unavailable"} | UNCERTAIN


def read_only_attention(node):
    return (node.get("handling_attention") is True and node.get("completion") == "result"
            and set(node.get("allowed_actions", [])) <= {"start"}
            and not node.get("task") and not node.get("setup_intents"))


def installed(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_works'").fetchone() is not None


def guard_business(c, db, session, action, request, control):
    if not installed(db):
        if session.dispatch or request.get("runtime_dispatch"):
            raise GateError("runtime_upgrade_required")
        return
    ids = {request[k] for k in ("task_id", "id") if request.get(k)}
    for field in ("ref", "target_ref"):
        if request.get(field):
            ids.add(c.artifact(db, request[field])["task_id"])
    for member in request.get("members", []):
        ids.add(c.artifact(db, member["ref"])["task_id"])
    managed = [row[0] for row in db.execute("SELECT task_id FROM runtime_tasks WHERE active=1") if row[0] in ids]
    context = session.dispatch
    if context is None:
        if managed and action not in {"ack_events"}:
            raise GateError("runtime_dispatch_required")
        if request.get("runtime_dispatch"):
            raise GateError("runtime_session_binding_required")
        return
    if request.get("runtime_dispatch") != context:
        raise GateError("runtime_dispatch_mismatch")
    if session.runtime_setup:
        if session.role != "AG0" or request.get("runtime_setup") is not True:
            raise GateError("runtime_setup_role_required")
        a = RuntimeStore.get(db, "runtime_attempts", context["dispatch_id"])
        w = RuntimeStore.get(db, "runtime_works", a["work_id"])
        b = RuntimeStore.get(db, "runtime_bindings", w["node"]["binding"])
        attempt, work, binding = verify_dispatch(c, db, context, b["role"], control)
        from .agent_api import AgentCoordinator
        matching = False
        actual = {k: v for k, v in request.items() if k not in {"runtime_dispatch", "runtime_setup", "prepared_preconditions", "expected_state_revision"}}
        for intent in work["node"].get("setup_intents", []):
            expected_action, expected = AgentCoordinator(c).compile(db, "AG0", intent, request["operation_id"])
            expected.pop("expected_state_revision", None)
            if expected_action == action and encode(expected) == encode(actual):
                matching = True
        if not matching or action != "register":
            raise GateError("runtime_setup_outside_plan")
    else:
        if request.get("runtime_setup"):
            raise GateError("runtime_setup_session_required")
        attempt, work, binding = verify_dispatch(c, db, context, session.role, control)
    if action != "start" and not session.runtime_setup and not attempt.get("agent_received"):
        raise GateError("dispatch_not_received")
    node = work["node"]
    if action not in node["allowed_actions"] or not ids <= set(node["allowed_tasks"]):
        raise GateError("runtime_action_outside_plan")
    if action in {"adopt", "confirm", "review", "recheck"}:
        frozen = {encode(i["ref"]) for i in work["inputs"]}
        targets = [m["ref"] for m in request.get("members", [])]
        targets += [request[k] for k in ("ref", "target_ref") if request.get(k)]
        for target in targets:
            # Owner opinions may cover the result just submitted by this work.
            artifact = c.artifact(db, target)
            produced_here = db.execute("SELECT 1 FROM runtime_commits WHERE dispatch_id=? AND ref=?", (attempt["dispatch_id"], encode(ref(artifact)))).fetchone()
            if encode(ref(target)) not in frozen and not produced_here:
                raise GateError("runtime_target_not_frozen")
    for item in work["inputs"]:
        c.verify_file(c.artifact(db, item["ref"]))


def verify_dispatch(c, db, context, role, control, *, allow_expired=False):
    if not isinstance(context, dict) or set(context) != {"dispatch_id", "claim_epoch", "thread_id"}:
        raise GateError("invalid_runtime_dispatch")
    row = db.execute("SELECT body FROM runtime_attempts WHERE id=?", (identifier(context["dispatch_id"]),)).fetchone()
    if row is None:
        raise GateError("dispatch_not_found")
    attempt = json.loads(row[0])
    work = json.loads(db.execute("SELECT body FROM runtime_works WHERE id=?", (attempt["work_id"],)).fetchone()[0])
    binding = json.loads(db.execute("SELECT body FROM runtime_bindings WHERE id=?", (work["node"]["binding"],)).fetchone()[0])
    if work["state"] not in BUSY or work.get("dispatch_id") != context["dispatch_id"] or work["claim_epoch"] != context["claim_epoch"]:
        raise GateError("stale_dispatch")
    if binding["role"] != role or binding["generation"] != attempt["binding_generation"] or binding.get("thread_id") != context["thread_id"]:
        raise GateError("dispatch_thread_mismatch")
    if not allow_expired and attempt["lease_until_ms"] <= c.clock_ms():
        raise GateError("dispatch_lease_expired")
    plan = json.loads(db.execute("SELECT body FROM runtime_plans WHERE id=?", (work["workflow_id"],)).fetchone()[0])
    if not plan["enabled"] or not binding["authorized"] or binding["authorization_ref"] != plan["authorization_ref"]:
        raise GateError("runtime_authorization_inactive")
    if work["node"].get("deadline_ms") is not None and c.clock_ms() >= work["node"]["deadline_ms"]:
        raise GateError("runtime_deadline_passed")
    c.gate(control, work["scope_ids"], work["intended_uses"])
    # In-flight decisions cannot silently adopt newer opinions or pointers.
    facts = RuntimeStore(c)._facts(db, work["node"], control)
    if (facts["fingerprint"] != work["facts_fingerprint"] or not facts["ready"]) and not read_only_attention(work["node"]):
        # A successful decision may change its own adopted pointers. Recovery
        # reads those receipts; it does not authorize another business write.
        raise GateError("runtime_basis_changed")
    return attempt, work, binding


def record_business_receipt(db, session, request, response):
    if not installed(db) or session.dispatch is None:
        return
    dispatch = session.dispatch["dispatch_id"]
    db.execute("INSERT OR IGNORE INTO runtime_commits VALUES(?,?,?,?)", (response["operation_id"], dispatch, encode(response.get("ref")) if response.get("ref") else None, encode(response)))


class RuntimeStore:
    def __init__(self, coordinator):
        self.c = coordinator

    def migrate(self, session):
        if self.c.role(session) != "AG0":
            raise GateError("ag0_runtime_upgrade_required")
        # Explicit entry only; an ordinary read never silently upgrades a DB.
        with self.c.connect() as db:
            self.c.controls(db)
            backup = self.c.meta_root / "backups" / ("before-runtime-" + uuid.uuid4().hex + ".sqlite3")
            backup.parent.mkdir(exist_ok=True)
            destination = sqlite3.connect(backup)
            try:
                db.backup(destination)
            finally:
                destination.close()
            db.execute("BEGIN IMMEDIATE")
            marker = db.execute("SELECT value FROM meta WHERE key='runtime_version'").fetchone()
            if marker and marker[0] != RUNTIME_VERSION:
                raise GateError("unsupported_runtime_version")
            statements = [
                "CREATE TABLE IF NOT EXISTS runtime_bindings(id TEXT PRIMARY KEY,body TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS runtime_plans(id TEXT PRIMARY KEY,body TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS runtime_works(id TEXT PRIMARY KEY,work_key TEXT UNIQUE NOT NULL,state TEXT NOT NULL,body TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS runtime_attempts(id TEXT PRIMARY KEY,body TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS runtime_tasks(task_id TEXT PRIMARY KEY,workflow_id TEXT NOT NULL,active INTEGER NOT NULL)",
                "CREATE TABLE IF NOT EXISTS runtime_commits(operation_id TEXT PRIMARY KEY,dispatch_id TEXT NOT NULL,ref TEXT,body TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS runtime_supervisor(id TEXT PRIMARY KEY,body TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS runtime_audit(sequence INTEGER PRIMARY KEY AUTOINCREMENT,at_ms INTEGER NOT NULL,kind TEXT NOT NULL,body TEXT NOT NULL)"]
            for statement in statements:
                db.execute(statement)
            db.execute("INSERT OR IGNORE INTO meta VALUES('runtime_revision','0')")
            db.execute("INSERT OR IGNORE INTO meta VALUES('runtime_version',?)", (RUNTIME_VERSION,))
            db.commit()
        return {"status": "committed", "runtime_version": RUNTIME_VERSION, "backup": str(backup)}

    @contextmanager
    def transaction(self):
        with self.c.connect() as db:
            if not installed(db):
                raise GateError("runtime_upgrade_required")
            db.execute("BEGIN IMMEDIATE")
            yield db
            self.c.checkpoint("runtime_before_commit")
            db.commit()

    def audit(self, db, kind, body):
        db.execute("INSERT INTO runtime_audit(at_ms,kind,body) VALUES(?,?,?)", (self.c.clock_ms(), kind, encode(body)))
        db.execute("UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='runtime_revision'")

    @staticmethod
    def put(db, table, key, body):
        if table == "runtime_works":
            db.execute("INSERT INTO runtime_works VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET work_key=excluded.work_key,state=excluded.state,body=excluded.body", (key, body["work_key"], body["state"], encode(body)))
        else:
            db.execute(f"INSERT INTO {table} VALUES(?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body", (key, encode(body)))

    @staticmethod
    def get(db, table, key):
        row = db.execute(f"SELECT body FROM {table} WHERE id=?", (identifier(key),)).fetchone()
        if row is None:
            raise GateError("runtime_record_not_found")
        return json.loads(row[0])

    def bind(self, session, binding):
        if self.c.role(session) != "AG0":
            raise GateError("ag0_runtime_binding_required")
        identifier(binding["id"])
        if binding["role"] not in {"AG0", "AG1", "AG2", "AG3"} or binding["host_kind"] not in {"desktop", "cli", "fake"}:
            raise GateError("invalid_host_binding")
        if binding["host_kind"] == "desktop" and not binding.get("thread_id"):
            raise GateError("original_thread_binding_required")
        if not isinstance(binding.get("authorization_ref"), str) or not binding["authorization_ref"].strip() or binding.get("authorized") is not True:
            raise GateError("explicit_runtime_authorization_required")
        with self.transaction() as db:
            self.c.controls(db)
            previous = db.execute("SELECT body FROM runtime_bindings WHERE id=?", (binding["id"],)).fetchone()
            if previous:
                old = json.loads(previous[0])
                if any(self.get(db, "runtime_works", r[0])["node"]["binding"] == binding["id"] for r in db.execute("SELECT id FROM runtime_works WHERE state NOT IN ('done','failed','cancelled','superseded')")):
                    raise GateError("binding_has_unfinished_work")
            else:
                old = {}
            value = {**binding, "generation": old.get("generation", 0) + 1, "authorized": True}
            self.put(db, "runtime_bindings", binding["id"], value)
            self.audit(db, "binding_saved", {"id": binding["id"], "generation": value["generation"]})
        return value

    def register_plan(self, session, plan):
        if self.c.role(session) != "AG0":
            raise GateError("ag0_runtime_plan_required")
        identifier(plan["id"])
        if type(plan.get("revision")) is not int or plan["revision"] < 1 or not plan.get("nodes") or not plan.get("authorization_ref"):
            raise GateError("explicit_runtime_plan_required")
        # Nodes are explicit capabilities and conditions, not an inferred plan.
        seen = set()
        with self.transaction() as db:
            control = self.c.controls(db)
            if db.execute("SELECT 1 FROM runtime_plans WHERE id=?", (plan["id"],)).fetchone():
                raise GateError("runtime_plan_already_registered")
            for node in plan["nodes"]:
                identifier(node["id"])
                if node["id"] in seen:
                    raise GateError("duplicate_runtime_node")
                seen.add(node["id"])
                binding = self.get(db, "runtime_bindings", node["binding"])
                if not binding["authorized"] or binding["authorization_ref"] != plan["authorization_ref"]:
                    raise GateError("runtime_authorization_mismatch")
                if not isinstance(node.get("allowed_tasks"), list) or not node["allowed_tasks"] or not node.get("allowed_actions") or not node.get("prompt"):
                    raise GateError("explicit_runtime_capability_required")
                if not set(node["allowed_actions"]) <= self.c.actions() - {"upgrade", "bootstrap", "ack_events"}:
                    raise GateError("invalid_runtime_actions")
                if not isinstance(node.get("required_intents", []), list) or not set(node.get("required_intents", [])) <= {"deliver", "opinion", "adopt", "stop", "check_change"}:
                    raise GateError("invalid_runtime_required_intents")
                if node.get("completion", "business") not in {"business", "result"} or type(node.get("result_via_file", False)) is not bool:
                    raise GateError("invalid_runtime_completion")
                for task in node["allowed_tasks"]:
                    identifier(task)
                self._validate_conditions(node.get("conditions", []))
                if "output_spec" in node:
                    from .runtime_outputs import validate_output_spec
                    validate_output_spec(node["output_spec"])
                prior_results = node.get("include_prior_results", [])
                completed_dependencies = {condition["node"] for condition in node.get("conditions", [])
                                          if condition["kind"] == "work_done"}
                if (not isinstance(prior_results, list)
                        or len(set(prior_results)) != len(prior_results)
                        or not set(prior_results) <= completed_dependencies):
                    raise GateError("runtime_prior_result_outside_dependencies")
                for prior in prior_results:
                    identifier(prior)
                for setup in node.get("setup_intents", []):
                    if (setup.get("action") not in {"assign_review", "assign_readback"}
                            or setup.get("task") not in node["allowed_tasks"]
                            or setup.get("from_task") not in node["allowed_tasks"]
                            or "target" in setup or "inputs" in setup):
                        raise GateError("unsupported_runtime_setup")
                    from .agent_api import intent_shape
                    intent_shape(setup)
                if node.get("task") and node["task"] not in node["allowed_tasks"]:
                    raise GateError("runtime_task_outside_plan")
                if type(node.get("decision_epoch", 0)) is not int or node.get("decision_epoch", 0) < 0:
                    raise GateError("invalid_decision_epoch")
                if node.get("handling_attention") and (not read_only_attention(node)
                        or node.get("required_intents") or node.get("output_spec")):
                    raise GateError("runtime_attention_must_be_read_only")
                for key in ("deadline_ms", "run_timeout_ms"):
                    if key in node and (type(node[key]) is not int or node[key] <= 0):
                        raise GateError("invalid_runtime_deadline")
                self.c.gate(control, node["allowed_tasks"], [node.get("use", "coordination")])
                for task in node.get("manage_tasks", []):
                    if task not in node["allowed_tasks"]:
                        raise GateError("managed_task_outside_plan")
                    prior = db.execute("SELECT workflow_id FROM runtime_tasks WHERE task_id=?", (task,)).fetchone()
                    if prior and prior[0] != plan["id"]:
                        raise GateError("task_already_managed")
                    db.execute("INSERT OR REPLACE INTO runtime_tasks VALUES(?,?,1)", (task, plan["id"]))
            value = {**plan, "enabled": plan.get("enabled", True), "registered_at_ms": self.c.clock_ms()}
            if type(value["enabled"]) is not bool:
                raise GateError("invalid_runtime_enabled")
            self.put(db, "runtime_plans", plan["id"], value)
            self.audit(db, "plan_saved", {"id": plan["id"]})
        return {"status": "committed", "workflow_id": plan["id"], "meaning": "durable_plan_not_listener_health"}

    def set_enabled(self, session, workflow_id, enabled):
        if self.c.role(session) != "AG0" or type(enabled) is not bool:
            raise GateError("ag0_runtime_control_required")
        with self.transaction() as db:
            plan = self.get(db, "runtime_plans", workflow_id)
            plan["enabled"] = enabled
            self.put(db, "runtime_plans", workflow_id, plan)
            self.audit(db, "plan_enabled", {"workflow_id": workflow_id, "enabled": enabled})
        return {"status": "committed", "enabled": enabled}

    def release_supervisor(self, instance_id):
        with self.transaction() as db:
            record = self.get(db, "runtime_supervisor", "local")
            if record["instance_id"] != instance_id:
                raise GateError("scheduler_lease_lost")
            record["lease_until_ms"] = 0
            self.put(db, "runtime_supervisor", "local", record)

    def lookup(self, table, key):
        if table not in {"runtime_attempts", "runtime_works", "runtime_bindings", "runtime_plans"}:
            raise GateError("invalid_runtime_table")
        with self.c.connect() as db:
            return self.get(db, table, key)

    def assert_dispatch(self, context, role):
        with self.c.connect() as db:
            db.execute("BEGIN")
            return verify_dispatch(self.c, db, context, role, self.c.controls(db))

    @staticmethod
    def _validate_conditions(conditions):
        if not isinstance(conditions, list):
            raise GateError("invalid_runtime_conditions")
        for condition in conditions:
            if not isinstance(condition, dict) or condition.get("kind") not in {"submitted", "adoption_ready", "adopted", "work_done", "workflow_attention"}:
                raise GateError("unsupported_runtime_condition")
            if condition["kind"] == "workflow_attention":
                if set(condition) != {"kind"}:
                    raise GateError("invalid_runtime_conditions")
                continue
            identifier(condition["node"] if condition["kind"] == "work_done" else condition["task"])
            if condition.get("ref"):
                ref(condition["ref"])

    def _facts(self, db, node, control):
        ready, reasons, inputs, facts = True, [], [], []
        ids, uses = set(node["allowed_tasks"]) | set(node.get("scope", [])), {node.get("use", "coordination")}
        for condition in node.get("conditions", []):
            kind = condition["kind"]
            if kind == "workflow_attention":
                problems = []
                for row in db.execute("SELECT body FROM runtime_works"):
                    other = json.loads(row[0])
                    if (other["workflow_id"] == node["workflow_id"] and not other["node"].get("handling_attention")
                            and other["state"] in {"failed", "needs_user", "host_unavailable", "dispatch_unknown", "execution_unknown"}):
                        problems.append({"node": other["node"]["id"], "state": other["state"],
                                         "reason": other.get("reason"), "dispatch_id": other.get("dispatch_id")})
                facts.append({"kind": kind, "problems": sorted(problems, key=lambda p: p["node"])})
                if not problems:
                    ready = False
                    reasons.append("no_workflow_attention_needed")
                continue
            if kind == "work_done":
                # Refer only to a previously registered node in this workflow.
                rows = [json.loads(r[0]) for r in db.execute("SELECT body FROM runtime_works")]
                done = any(w["workflow_id"] == node["workflow_id"] and w["node"]["id"] == condition["node"] and w["state"] == "done" for w in rows)
                facts.append({"kind": kind, "node": condition["node"], "done": done})
                if not done:
                    ready = False
                    reasons.append("waiting_for_work")
                continue
            row = db.execute("SELECT body FROM tasks WHERE id=?", (condition["task"],)).fetchone()
            if row is None:
                ready = False
                reasons.append("waiting_for_task_registration")
                facts.append({"task": condition["task"], "ref": None})
                continue
            task = json.loads(row[0])
            ids.add(task["id"])
            uses.add(task["intended_use"])
            target = task.get("result_ref")
            if not target or task["phase"] in {"failed", "cancelled", "blocked"}:
                ready = False
                reasons.append("upstream_" + task["phase"])
                facts.append({"task": task["id"], "phase": task["phase"], "ref": target})
                continue
            artifact = self.c.artifact(db, target)
            self.c.verify_file(artifact)
            if condition.get("ref") and ref(target) != ref(condition["ref"]):
                ready = False
                reasons.append("required_result_superseded")
            pinned = {"ref": ref(artifact), "sha256": artifact["sha256"], "path": artifact["path"], "use": artifact["intended_use"], "scope": artifact["scope"]}
            inputs.append(pinned)
            ids.add(artifact["id"])
            for dependency in artifact["basis_refs"]:
                a = self.c.artifact(db, dependency)
                self.c.verify_file(a)
                ids.add(a["id"])
                uses.add(a["intended_use"])
                inputs.append({"ref": ref(a), "sha256": a["sha256"], "path": a["path"], "use": a["intended_use"], "scope": a["scope"]})
            fact = {"kind": kind, "task": task["id"], "ref": ref(artifact), "sha256": artifact["sha256"]}
            if kind in {"adoption_ready", "adopted"}:
                stamp, issues = self.c.basis_status(db, artifact)
                opinions, retired = self.c.active_opinions(db, artifact, artifact["intended_use"], stamp)
                active = [o for o in opinions if o["id"] not in retired]
                fact.update(basis=stamp, opinions=sorted(active, key=lambda o: o["id"]), issues=issues)
                if issues:
                    ready = False
                    reasons.append("input_recheck_required")
                if kind == "adoption_ready":
                    for role in [artifact["owner"]] + (["AG3"] if artifact["requires_ag3_review"] else []):
                        covered = {s for o in active if o["by"] == role and o["outcome"] == "supported" for s in o["scope"]}
                        if not set(artifact["scope"]) <= covered:
                            ready = False
                            reasons.append("waiting_for_" + role)
                    if any(o["outcome"] != "supported" for o in active):
                        ready = False
                        reasons.append("conflicting_professional_receipts")
                pointers = [dict(r) for r in db.execute("SELECT * FROM adopted WHERE id=? AND intended_use=? ORDER BY scope", (artifact["id"], artifact["intended_use"]))]
                fact["pointers"] = pointers
                if kind == "adopted" and not all(any(p["scope"] == s and p["revision"] == artifact["revision"] for p in pointers) for s in artifact["scope"]):
                    ready = False
                    reasons.append("waiting_for_adoption")
            facts.append(fact)
        self.c.gate(control, ids, uses)
        # Freeze relevant facts, not unrelated event sequence/revisions.
        return {"ready": ready, "reasons": reasons, "inputs": list({encode(i["ref"]): i for i in inputs}.values()), "scope_ids": sorted(ids), "intended_uses": sorted(uses), "facts": facts, "fingerprint": sha(encode(facts).encode())}

    def reconcile(self, session, *, consumer="runtime-scheduler", limit=100):
        if self.c.role(session) != "AG0":
            raise GateError("ag0_runtime_scheduler_required")
        identifier(consumer)
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise GateError("invalid_event_cursor")
        created, changed = [], []
        with self.transaction() as db:
            control = self.c.controls(db)
            row = db.execute("SELECT sequence FROM consumers WHERE id=? AND role='AG0'", (consumer,)).fetchone()
            cursor = row[0] if row else 0
            events = db.execute("SELECT sequence FROM events WHERE sequence>? ORDER BY sequence LIMIT ?", (cursor, limit)).fetchall()
            through = events[-1][0] if events else cursor
            for plan_row in db.execute("SELECT body FROM runtime_plans").fetchall():
                plan = json.loads(plan_row[0])
                if not plan["enabled"]:
                    continue
                for original in plan["nodes"]:
                    node = {**original, "workflow_id": plan["id"]}
                    # One decision epoch remains one work even if facts change.
                    existing = [json.loads(r[0]) for r in db.execute("SELECT body FROM runtime_works")]
                    old = next((w for w in existing if w["workflow_id"] == plan["id"] and w["node"]["id"] == node["id"] and w["node"].get("decision_epoch", 0) == node.get("decision_epoch", 0)), None)
                    if old and old["state"] in TERMINAL:
                        continue
                    try:
                        fact = self._facts(db, node, control)
                    except GateError as error:
                        if old and old["state"] not in BUSY:
                            old.update(state="blocked", reason=error.code)
                            self.put(db, "runtime_works", old["id"], old)
                        continue
                    if old:
                        if old["state"] in BUSY:
                            continue
                        if node.get("deadline_ms") is not None and self.c.clock_ms() >= node["deadline_ms"]:
                            old.update(state="failed", reason="runtime_deadline_passed")
                        elif fact["ready"]:
                            old.update(state="ready", reason=None, **{k: fact[k] for k in ("inputs", "scope_ids", "intended_uses")}, facts_fingerprint=fact["fingerprint"])
                            old["work_key"] = sha(encode({"workflow": plan["id"], "revision": plan["revision"], "node": node["id"], "inputs": fact["inputs"], "decision_epoch": node.get("decision_epoch", 0)}).encode())
                        else:
                            old.update(state="blocked", reason=",".join(fact["reasons"]))
                        self.put(db, "runtime_works", old["id"], old)
                        changed.append(old["id"])
                        continue
                    key = sha(encode({"workflow": plan["id"], "revision": plan["revision"], "node": node["id"], "inputs": fact["inputs"], "decision_epoch": node.get("decision_epoch", 0)}).encode())
                    work_id = "work-" + uuid.uuid4().hex
                    work = {"id": work_id, "work_key": key, "workflow_id": plan["id"], "node": node, "state": "ready" if fact["ready"] else "blocked", "reason": None if fact["ready"] else ",".join(fact["reasons"]), "inputs": fact["inputs"], "facts_fingerprint": fact["fingerprint"], "scope_ids": fact["scope_ids"], "intended_uses": fact["intended_uses"], "claim_epoch": 0, "created_at_ms": self.c.clock_ms(), "event_through": through}
                    self.put(db, "runtime_works", work_id, work)
                    created.append(work_id)
            self.c.checkpoint("runtime_after_enqueue")
            db.execute("INSERT INTO consumers VALUES(?,'AG0',?) ON CONFLICT(id,role) DO UPDATE SET sequence=excluded.sequence", (consumer, through))
            if events or created:
                self.audit(db, "events_registered", {"from": cursor, "through": through, "created": created})
        return {"created": created, "changed": changed, "through_sequence": through}

    def acquire_supervisor(self, instance_id, *, lease_ms=60000):
        identifier(instance_id)
        with self.transaction() as db:
            row = db.execute("SELECT body FROM runtime_supervisor WHERE id='local'").fetchone()
            old = json.loads(row[0]) if row else {}
            if old.get("instance_id") != instance_id and old.get("lease_until_ms", 0) > self.c.clock_ms():
                raise GateError("scheduler_already_running")
            record = {"instance_id": instance_id, "pid": os.getpid(), "started_at_ms": old.get("started_at_ms", self.c.clock_ms()) if old.get("instance_id") == instance_id else self.c.clock_ms(), "lease_until_ms": self.c.clock_ms() + lease_ms}
            self.put(db, "runtime_supervisor", "local", record)
        return record

    def claim(self, work_id, instance_id, *, lease_ms=60000):
        with self.transaction() as db:
            supervisor = self.get(db, "runtime_supervisor", "local")
            if supervisor["instance_id"] != instance_id or supervisor["lease_until_ms"] <= self.c.clock_ms():
                raise GateError("scheduler_lease_lost")
            work = self.get(db, "runtime_works", work_id)
            if work["state"] != "ready":
                raise GateError("work_not_ready")
            binding = self.get(db, "runtime_bindings", work["node"]["binding"])
            for row in db.execute("SELECT body FROM runtime_works WHERE id<>?", (work_id,)):
                other = json.loads(row[0])
                if other["state"] in BUSY:
                    b = self.get(db, "runtime_bindings", other["node"]["binding"])
                    if b["id"] == binding["id"] or (b.get("thread_id") and b.get("thread_id") == binding.get("thread_id") and b["host_kind"] == binding["host_kind"]):
                        # A bounded, result-only diagnostic may report an
                        # unresolved AG0 operation once the caller has checked
                        # that the real original chat is idle. It cannot adopt,
                        # publish an opinion or retry that operation.
                        if (read_only_attention(work["node"]) and binding["role"] == "AG0"
                                and other["state"] in UNCERTAIN | {"host_unavailable"}):
                            continue
                        raise GateError("thread_has_unfinished_dispatch")
            work["claim_epoch"] += 1
            dispatch_id = "dispatch-" + uuid.uuid4().hex
            attempt = {"dispatch_id": dispatch_id, "work_id": work_id, "claim_epoch": work["claim_epoch"], "binding_generation": binding["generation"], "instance_id": instance_id, "lease_until_ms": self.c.clock_ms() + lease_ms, "state": "claimed", "created_at_ms": self.c.clock_ms()}
            work.update(state="claimed", dispatch_id=dispatch_id)
            self.put(db, "runtime_works", work_id, work)
            self.put(db, "runtime_attempts", dispatch_id, attempt)
            context = {"dispatch_id": dispatch_id, "claim_epoch": attempt["claim_epoch"], "thread_id": binding.get("thread_id")}
            verify_dispatch(self.c, db, context, binding["role"], self.c.controls(db))
            self.audit(db, "work_claimed", {"dispatch_id": dispatch_id, "work_id": work_id})
        return attempt

    def update_attempt(self, dispatch_id, state, *, instance_id=None, context=None, role=None, **fields):
        allowed = {"claimed": {"ready", "dispatching", "failed", "cancelled"}, "dispatching": {"accepted", "running", "dispatch_unknown", "host_unavailable", "failed"}, "accepted": {"running", "result_saved", "dispatch_unknown", "execution_unknown", "needs_user", "failed", "cancelled"}, "running": {"result_saved", "execution_unknown", "needs_user", "failed", "cancelled"}, "result_saved": {"committed", "done", "needs_user", "cancelled"}, "committed": {"done", "needs_user"}, "dispatch_unknown": {"running", "result_saved", "needs_user"}, "execution_unknown": {"running", "result_saved", "needs_user"}, "host_unavailable": {"dispatch_unknown", "needs_user"}, "needs_user": {"cancelled"}}
        with self.transaction() as db:
            if context is not None:
                verify_dispatch(self.c, db, context, role, self.c.controls(db))
            attempt = self.get(db, "runtime_attempts", dispatch_id)
            work = self.get(db, "runtime_works", attempt["work_id"])
            if work.get("dispatch_id") != dispatch_id or work["claim_epoch"] != attempt["claim_epoch"]:
                raise GateError("stale_dispatch")
            if instance_id is not None and attempt["instance_id"] != instance_id:
                raise GateError("scheduler_lease_lost")
            if fields.get("result_sha256") and attempt.get("result_sha256") and fields["result_sha256"] != attempt["result_sha256"]:
                raise GateError("runtime_result_changed")
            if state != work["state"] and state not in allowed.get(work["state"], set()):
                raise GateError("invalid_runtime_transition")
            attempt.update(fields, state=state, updated_at_ms=self.c.clock_ms())
            work.update(state=state, reason=fields.get("reason"))
            self.put(db, "runtime_attempts", dispatch_id, attempt)
            self.put(db, "runtime_works", work["id"], work)
            self.audit(db, "dispatch_" + state, {"dispatch_id": dispatch_id, "reason": fields.get("reason")})
        return attempt

    def adopt_thread(self, dispatch_id, thread_id):
        """CLI first launch may assign its real ID; never replace an existing ID."""
        if not thread_id or not isinstance(thread_id, str):
            raise GateError("actual_thread_id_required")
        with self.transaction() as db:
            attempt = self.get(db, "runtime_attempts", dispatch_id)
            work = self.get(db, "runtime_works", attempt["work_id"])
            binding = self.get(db, "runtime_bindings", work["node"]["binding"])
            if binding.get("thread_id") and binding["thread_id"] != thread_id:
                raise GateError("dispatch_thread_mismatch")
            if binding["generation"] != attempt["binding_generation"] or work.get("dispatch_id") != dispatch_id:
                raise GateError("stale_dispatch")
            binding["thread_id"] = thread_id
            self.put(db, "runtime_bindings", binding["id"], binding)
        return binding

    def begin_dispatch(self, context, role, *, execution_observed=False):
        with self.transaction() as db:
            attempt, work, binding = verify_dispatch(self.c, db, context, role, self.c.controls(db))
            if attempt.get("agent_received"):
                raise GateError("dispatch_already_received")
            allowed = {"dispatching", "accepted", "dispatch_unknown"}
            if execution_observed:
                if binding["host_kind"] not in {"cli", "fake"}:
                    raise GateError("cli_execution_evidence_required")
                allowed |= {"running", "execution_unknown"}
            if work["state"] not in allowed:
                raise GateError("dispatch_not_sent")
            attempt.update(agent_received=True, state="running", agent_received_at_ms=self.c.clock_ms())
            work["state"] = "running"
            self.put(db, "runtime_attempts", context["dispatch_id"], attempt)
            self.put(db, "runtime_works", work["id"], work)
            self.audit(db, "agent_received", {"dispatch_id": context["dispatch_id"], "thread_id": binding["thread_id"]})
        return {"status": "committed", "dispatch_id": context["dispatch_id"], "meaning": "execution_receipt_not_business_commit"}

    def reopen_cli_result(self, context, role, instance_id, *, evidence_sha256):
        """Explicitly repair this known receipt defect, never resend a model."""
        with self.transaction() as db:
            attempt, work, binding = verify_dispatch(self.c, db, context, role, self.c.controls(db))
            supervisor = self.get(db, "runtime_supervisor", "local")
            if (supervisor["instance_id"] != instance_id or supervisor["lease_until_ms"] <= self.c.clock_ms()):
                raise GateError("scheduler_lease_lost")
            if (binding["host_kind"] not in {"cli", "fake"} or work["state"] != "needs_user"
                    or work.get("reason") != "dispatch_not_sent"):
                raise GateError("runtime_result_repair_not_applicable")
            work.update(state="execution_unknown", reason=None, claim_epoch=work["claim_epoch"] + 1)
            attempt.update(state="execution_unknown", reason=None, claim_epoch=work["claim_epoch"],
                           instance_id=instance_id, lease_until_ms=self.c.clock_ms() + 60000)
            self.put(db, "runtime_works", work["id"], work)
            self.put(db, "runtime_attempts", context["dispatch_id"], attempt)
            self.audit(db, "cli_result_receipt_repaired", {"dispatch_id": context["dispatch_id"],
                       "evidence_sha256": evidence_sha256, "claim_epoch": work["claim_epoch"], "model_resends": 0})
        return attempt

    def renew(self, instance_id, *, lease_ms=60000):
        self.acquire_supervisor(instance_id, lease_ms=lease_ms)
        with self.transaction() as db:
            for row in db.execute("SELECT body FROM runtime_attempts").fetchall():
                attempt = json.loads(row[0])
                work = self.get(db, "runtime_works", attempt["work_id"])
                if attempt["instance_id"] == instance_id and work.get("dispatch_id") == attempt["dispatch_id"] and work["state"] in BUSY:
                    attempt["lease_until_ms"] = self.c.clock_ms() + lease_ms
                    self.put(db, "runtime_attempts", attempt["dispatch_id"], attempt)

    def recover(self, instance_id):
        """Reattach ledger ownership, never infer a stopped model from a lease."""
        self.acquire_supervisor(instance_id)
        with self.transaction() as db:
            for row in db.execute("SELECT body FROM runtime_works").fetchall():
                work = json.loads(row[0])
                if work["state"] not in BUSY | {"host_unavailable"}:
                    continue
                attempt = self.get(db, "runtime_attempts", work["dispatch_id"])
                if attempt["instance_id"] != instance_id:
                    # Fence all old writers, including a process that wakes late.
                    work["claim_epoch"] += 1
                    attempt["claim_epoch"] = work["claim_epoch"]
                    attempt["instance_id"] = instance_id
                    attempt["lease_until_ms"] = self.c.clock_ms() + 60000
                    if work["state"] == "claimed":
                        work["state"] = "ready"  # send boundary not crossed
                    elif work["state"] == "dispatching":
                        work["state"] = "dispatch_unknown"
                    elif work["state"] in {"accepted", "running"}:
                        work["state"] = "execution_unknown"
                    attempt["state"] = work["state"]
                    self.put(db, "runtime_attempts", attempt["dispatch_id"], attempt)
                    self.put(db, "runtime_works", work["id"], work)
                    self.audit(db, "recovery_registered", {"dispatch_id": attempt["dispatch_id"], "state": work["state"]})

    def save_result(self, dispatch_id, value, *, instance_id=None, context=None, role=None):
        if not isinstance(value, dict) or value.get("dispatch_id") != dispatch_id or not isinstance(value.get("output"), str) or not isinstance(value.get("intents"), list):
            raise GateError("invalid_correlated_result")
        if any(not isinstance(intent, dict) or not isinstance(intent.get("action"), str) or not intent["action"].strip() for intent in value["intents"]):
            raise GateError("invalid_correlated_result")
        directory = self.c.meta_root / "runtime-results"
        directory.mkdir(exist_ok=True)
        raw = encode(value).encode("utf-8")
        previous = self.lookup("runtime_attempts", dispatch_id)
        if previous.get("result_sha256") and previous["result_sha256"] != sha(raw):
            raise GateError("runtime_result_changed")
        # Full SHA-256 remains in the ledger; keep filenames short on Windows.
        path = directory / (dispatch_id + "-" + sha(raw)[:16] + ".json")
        if not path.resolve().is_relative_to(self.c.meta_root.resolve()):
            raise GateError("unsafe_runtime_result_path")
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        else:
            if path.read_bytes() != raw:
                raise GateError("runtime_result_changed")
        return self.update_attempt(dispatch_id, "result_saved", instance_id=instance_id, context=context, role=role, result_path=str(path), result_sha256=sha(raw))

    def status(self):
        with self.c.connect() as db:
            control = self.c.controls(db)
            if not installed(db):
                raise GateError("runtime_upgrade_required")
            works = []
            for row in db.execute("SELECT body FROM runtime_works ORDER BY rowid"):
                work = json.loads(row[0])
                try:
                    self.c.gate(control, work["scope_ids"], work["intended_uses"])
                except GateError as error:
                    works.append({"id": work["id"], "state": work["state"], "reason": error.code})
                    continue
                works.append(work)
            return {"status": "ok", "runtime_version": RUNTIME_VERSION, "state_revision": self.c.state_revision(db), "runtime_revision": int(db.execute("SELECT value FROM meta WHERE key='runtime_revision'").fetchone()[0]), "works": works, "bindings": [json.loads(r[0]) for r in db.execute("SELECT body FROM runtime_bindings")], "plans": [json.loads(r[0]) for r in db.execute("SELECT body FROM runtime_plans")], "supervisor": [json.loads(r[0]) for r in db.execute("SELECT body FROM runtime_supervisor")]}
