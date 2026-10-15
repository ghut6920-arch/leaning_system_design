"""Durable runtime contracts against fabricated workspaces and real SQLite.

No model or external host is called. The injected clock and crash seam exercise
the ledger at the same transaction boundaries used by the scheduler.
"""
from __future__ import annotations

from copy import deepcopy
from contextlib import closing
import json
import sqlite3
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
sys.path.insert(0, str(SUITE / "scripts"))
from coordinator.agent_api import AgentCoordinator
from coordinator.runtime_store import RUNTIME_VERSION, RuntimeStore
from coordinator.runtime_scheduler import RuntimeScheduler
from coordinator.workspace import GateError, sha
from test_coordinator_complete import CompleteWorkflow


class FakeRuntimeHost:
    """Deterministic host boundary: all sends and observations are recorded."""
    def __init__(self, *, state="idle", observation="result_saved", send_error=None, result=None):
        self.state = state
        self.observation = observation
        self.send_error = send_error
        self.result = result
        self.inspections = []
        self.dispatches = []
        self.observations = []

    def inspect(self, binding):
        self.inspections.append(deepcopy(binding))
        return {"state": self.state, "last_turn_id": "previous-completed-turn"}

    def dispatch(self, binding, prompt, dispatch_id):
        self.dispatches.append({"binding": deepcopy(binding), "prompt": prompt, "dispatch_id": dispatch_id})
        if self.send_error:
            raise self.send_error
        return {"status": "accepted", "thread_id": binding["thread_id"]}

    def observe(self, binding, attempt):
        self.observations.append(deepcopy(attempt))
        if self.observation != "result_saved":
            return {"status": self.observation, "thread_id": binding["thread_id"]}
        result = self.result or {"dispatch_id": attempt["dispatch_id"], "output": "Fabricated one-turn professional output.",
                                 "intents": [{"action": "deliver", "task": "producer", "path": "$output"},
                                             {"action": "opinion", "task": "producer", "outcome": "supported",
                                              "rationale": "An explicit fabricated owner judgment."}]}
        return {"status": "result_saved", "thread_id": binding["thread_id"], "turn_id": "correlated-completed-turn",
                "turn_ended": True, "result": deepcopy(result)}

    def close(self):
        pass


class FourRoleRuntimeHost(FakeRuntimeHost):
    """Tiny complete pipeline preserving exact packets and original identities."""
    def __init__(self):
        super().__init__()
        self.packets = {}

    def dispatch(self, binding, prompt, dispatch_id):
        self.packets[dispatch_id] = json.loads(prompt.rsplit("\n", 1)[-1])
        return super().dispatch(binding, prompt, dispatch_id)

    def observe(self, binding, attempt):
        self.observations.append(deepcopy(attempt))
        packet = self.packets[attempt["dispatch_id"]]
        node = packet["node_id"]
        if node == "research":
            output = "blue fabricated-four-role-nonce"
            intents = [{"action": "deliver", "task": "producer", "path": "$output"},
                       {"action": "opinion", "task": "producer", "outcome": "supported", "rationale": "Explicit fabricated author confirmation."}]
        elif node == "review":
            output = "Exact fictional note checked independently."
            intents = [{"action": "opinion", "task": "review-task", "outcome": "supported", "rationale": "Explicit fabricated AG3 confirmation of the exact note."}]
        elif node == "decide":
            output = "The two exact professional receipts support adopting this fictional version."
            intents = [{"action": "adopt", "tasks": ["producer"]}]
        elif node == "design":
            output = "Summary: " + packet["task_snapshot"][0]["text"]
            intents = [{"action": "deliver", "task": "summary", "path": "$output"}]
        else:
            output, intents = "The tiny fictional pipeline is complete.", []
        return {"status": "result_saved", "thread_id": binding["thread_id"], "turn_id": "turn-" + node,
                "turn_ended": True, "result": {"dispatch_id": attempt["dispatch_id"], "output": output, "intents": intents}}


class CoordinatorRuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tac-runtime-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.control = {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []}
        self.w = CompleteWorkflow(self.root, lambda: deepcopy(self.control))
        self.c = self.w.coordinator
        self.now = 100000
        self.c.clock_ms = lambda: self.now
        self.api = AgentCoordinator(self.c)
        self.store = RuntimeStore(self.c)
        self.ag0 = self.w.sessions["AG0"]

    def state(self):
        return self.c.status(self.ag0)

    def persisted(self):
        with self.c.connect() as db:
            tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            return {name: sorted(tuple(row) for row in db.execute('SELECT * FROM "' + name + '"')) for name in tables}

    def install(self):
        with self.c.connect() as db:
            present = db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_works'").fetchone()
        if not present:
            return self.store.migrate(self.ag0)

    def binding(self, role="AG2", *, name="worker", thread="original-worker-thread"):
        return self.store.bind(self.ag0, {"id": name, "role": role, "host_kind": "fake", "thread_id": thread,
                                          "authorization_ref": "user-authorized-fabricated-workflow", "authorized": True})

    @staticmethod
    def node(task="producer", *, name="produce", binding="worker", conditions=None, actions=None, managed=False):
        value = {"id": name, "binding": binding, "prompt": "Complete one fabricated finite unit of work.",
                 "allowed_tasks": [task], "allowed_actions": actions or ["start", "submit", "confirm"],
                 "conditions": conditions or [], "use": "teaching"}
        if managed:
            value["manage_tasks"] = [task]
        return value

    def plan(self, nodes, *, name="workflow"):
        return self.store.register_plan(self.ag0, {"id": name, "revision": 1,
                                                   "authorization_ref": "user-authorized-fabricated-workflow", "nodes": nodes})

    def work(self, name="produce"):
        return next(item for item in self.store.status()["works"] if item["node"]["id"] == name)

    @staticmethod
    def context(attempt, thread="original-worker-thread"):
        return {"dispatch_id": attempt["dispatch_id"], "claim_epoch": attempt["claim_epoch"], "thread_id": thread}

    def ready_production(self, *, managed=True):
        self.w.register("producer", "material")
        self.install()
        self.binding()
        self.plan([self.node(managed=managed)])
        self.store.reconcile(self.ag0)
        return self.work()

    def claim(self, work=None, *, lease_ms=60000):
        self.store.acquire_supervisor("instance-one", lease_ms=lease_ms)
        return self.store.claim((work or self.work())["id"], "instance-one", lease_ms=lease_ms)

    def receive(self, attempt, *, role="AG2", thread="original-worker-thread"):
        self.store.update_attempt(attempt["dispatch_id"], "dispatching", instance_id="instance-one")
        self.store.update_attempt(attempt["dispatch_id"], "accepted", instance_id="instance-one")
        context = self.context(attempt, thread)
        self.store.begin_dispatch(context, role)
        return self.c.bind_local_operator(role, dispatch=context)

    def decision_ready(self, *, review=True):
        self.w.register("producer", "material", review=review)
        self.w.op("AG2", "start", task_id="producer")
        target = self.w.submit("producer")["ref"]
        self.w.confirm(target)
        if review:
            self.w.review(target)
        self.install()
        self.binding("AG0", name="decision", thread="original-ag0-thread")
        self.plan([self.node(name="decide", binding="decision", actions=["adopt"],
                             conditions=[{"kind": "adoption_ready", "task": "producer", "ref": target}])])
        self.store.reconcile(self.ag0)
        return target, self.work("decide")

    def scheduler_production(self, host, *, timeout=None, shadow=False, required_intents=None):
        self.w.register("producer", "material")
        self.install()
        self.binding()
        node = {**self.node(managed=True), "task": "producer", "completion": "business"}
        if timeout is not None:
            node["run_timeout_ms"] = timeout
        if required_intents is not None:
            node["required_intents"] = required_intents
        self.plan([node])
        return RuntimeScheduler(self.c, {"fake": host}, instance_id="instance-one", shadow=shadow)

    def test_runtime_install_is_explicit_and_role_checked(self):
        before = self.persisted()
        with self.assertRaisesRegex(GateError, "runtime_upgrade_required"):
            self.store.status()
        with self.assertRaisesRegex(GateError, "ag0_runtime_upgrade_required"):
            self.store.migrate(self.w.sessions["AG2"])
        self.assertEqual(before, self.persisted())
        self.assertFalse((self.c.meta_root / "backups").exists())

    def test_workflow_attention_is_dormant_then_once_for_real_failure(self):
        self.w.register("producer", "material")
        self.install()
        self.binding()
        self.binding("AG0", name="attention", thread="original-ag0-thread")
        self.plan([self.node(managed=True), {**self.node(name="attention", binding="attention", actions=["start"],
                   conditions=[{"kind": "workflow_attention"}]), "handling_attention": True, "completion": "result"}])
        self.store.reconcile(self.ag0)
        self.assertEqual(self.work("attention")["state"], "blocked")
        attempt = self.claim()
        self.store.update_attempt(attempt["dispatch_id"], "failed", instance_id="instance-one", reason="actual_fixture_failure")
        self.store.reconcile(self.ag0)
        attention = self.work("attention")
        self.assertEqual(attention["state"], "ready")
        with self.c.connect() as db:
            facts = self.store._facts(db, attention["node"], self.c.controls(db))["facts"]
        self.assertEqual(facts[0]["problems"][0]["reason"], "actual_fixture_failure")
        self.store.reconcile(self.ag0)
        self.assertEqual(self.work("attention")["id"], attention["id"])

    def test_attention_cannot_read_other_workflows_failures(self):
        self.ready_production()
        attempt = self.claim()
        self.store.update_attempt(attempt["dispatch_id"], "failed", instance_id="instance-one")
        self.plan([{**self.node(name="other-attention", actions=["start"], conditions=[{"kind": "workflow_attention"}]),
                    "handling_attention": True, "completion": "result"}], name="other-workflow")
        self.store.reconcile(self.ag0)
        self.assertEqual(self.work("other-attention")["state"], "blocked")

    def test_companion_delivers_one_original_AG0_attention_after_failure(self):
        self.w.register("producer", "material")
        self.install()
        self.binding()
        self.binding("AG0", name="attention", thread="original-ag0-thread")
        self.plan([{**self.node(managed=True), "task": "producer"},
                   {**self.node(name="attention", binding="attention", actions=["start"],
                                conditions=[{"kind": "workflow_attention"}]), "handling_attention": True, "completion": "result"}])
        class Host(FakeRuntimeHost):
            def observe(self, binding, attempt):
                if binding["role"] != "AG0":
                    return {"status": "failed", "reason": "real_fixture_host_failure"}
                return {"status": "result_saved", "thread_id": binding["thread_id"], "turn_ended": True,
                        "result": {"dispatch_id": attempt["dispatch_id"], "output": "Actual failure reported; no retry.", "intents": []}}
        host = Host()
        scheduler = RuntimeScheduler(self.c, {"fake": host}, instance_id="instance-one")
        scheduler.wakeup.wait = lambda seconds: None
        scheduler.run(max_seconds=5, stop_when_done=True)
        self.assertEqual(self.work()["state"], "failed")
        self.assertEqual(self.work("attention")["state"], "done")
        self.assertEqual(len(host.dispatches), 2)
        self.assertEqual(host.dispatches[-1]["binding"]["thread_id"], "original-ag0-thread")

    def test_attention_can_report_unresolved_original_AG0_without_effectful_capability(self):
        self.install()
        self.binding("AG0", name="decision", thread="original-ag0-thread")
        decision = {**self.node(name="decision", binding="decision", actions=["start"]), "completion": "result"}
        attention = {**self.node(name="attention", binding="decision", actions=["start"], conditions=[{"kind": "workflow_attention"}]),
                     "completion": "result", "handling_attention": True}
        self.plan([decision, attention])
        self.store.reconcile(self.ag0)
        first = self.claim(self.work("decision"))
        self.receive(first, role="AG0", thread="original-ag0-thread")
        self.store.update_attempt(first["dispatch_id"], "needs_user", instance_id="instance-one")
        self.store.reconcile(self.ag0)
        second = self.store.claim(self.work("attention")["id"], "instance-one")
        self.assertNotEqual(first["dispatch_id"], second["dispatch_id"])
        self.receive(second, role="AG0", thread="original-ag0-thread")
        with self.store.transaction() as db:
            old = self.store.get(db, "runtime_works", self.work("decision")["id"])
            old["reason"] = "additional_detail_arrived_while_reporting"
            self.store.put(db, "runtime_works", old["id"], old)
        self.store.assert_dispatch(self.context(second, "original-ag0-thread"), "AG0")

    def test_attention_marker_cannot_relax_business_gates(self):
        self.install()
        self.binding("AG0", name="attention", thread="original-ag0-thread")
        with self.assertRaisesRegex(GateError, "runtime_attention_must_be_read_only"):
            self.plan([{**self.node(name="attention", binding="attention", actions=["adopt"], conditions=[{"kind": "workflow_attention"}]),
                        "handling_attention": True, "completion": "result"}])

    def test_migration_backs_up_pre_runtime_database_without_business_revision_change(self):
        self.w.register("producer", "material")
        ticket = self.api.prepare(self.w.sessions["AG2"], {"action": "begin", "task": "producer"})["ticket"]
        before = self.persisted()
        revision = self.state()["state_revision"]
        migrated = self.install()
        backup = Path(migrated["backup"])
        self.assertTrue(backup.is_file())
        self.assertEqual(migrated["runtime_version"], RUNTIME_VERSION)
        with closing(sqlite3.connect(backup)) as db:
            names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            copied = {name: sorted(tuple(row) for row in db.execute('SELECT * FROM "' + name + '"')) for name in names}
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_works'").fetchone())
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(before, copied)
        self.assertEqual(self.state()["state_revision"], revision)
        self.assertEqual(self.api.apply(self.w.sessions["AG2"], ticket)["status"], "committed")

    def test_ack_and_same_cursor_repeat_preserve_prepared_business_ticket(self):
        self.w.register("producer", "material")
        ticket = self.api.prepare(self.w.sessions["AG2"], {"action": "begin", "task": "producer"})["ticket"]
        revision = self.state()["state_revision"]
        inbox = self.c.inbox(self.ag0, "agent-context")
        through = inbox["next_sequence"]
        event_count = len(self.persisted()["events"])
        for operation in ("ack-once", "ack-repeat-same-cursor"):
            result = self.c.execute(self.ag0, "ack_events", {"operation_id": operation,
                                   "expected_state_revision": revision, "consumer_id": "agent-context", "through_sequence": through})
            self.assertEqual(result["status"], "committed", result)
            self.assertEqual(result["state_revision"], revision)
        self.assertEqual(self.state()["state_revision"], revision)
        self.assertEqual(len(self.persisted()["events"]), event_count)
        self.assertEqual(self.c.inbox(self.ag0, "agent-context")["acknowledged_sequence"], through)
        self.assertEqual(self.api.apply(self.w.sessions["AG2"], ticket)["status"], "committed")

    def test_ack_cursor_cannot_rewind_and_invalid_ack_does_not_mutate(self):
        self.w.register("producer", "material")
        through = self.c.inbox(self.ag0, "agent-context")["next_sequence"]
        self.w.op("AG0", "ack_events", consumer_id="agent-context", through_sequence=through)
        before = self.persisted()
        for cursor, reason in ((through - 1, "ack_cursor_cannot_rewind"), (through + 1, "invalid_ack_sequence")):
            result = self.c.execute(self.ag0, "ack_events", {"operation_id": "bad-ack-" + str(cursor),
                                   "expected_state_revision": self.state()["state_revision"], "consumer_id": "agent-context", "through_sequence": cursor})
            self.assertEqual(result["reasons"], [reason])
            self.assertEqual(self.persisted(), before)

    def test_runtime_bookkeeping_and_begin_receipt_preserve_unrelated_prepared_ticket(self):
        self.w.register("unrelated", "unrelated-material")
        ticket = self.api.prepare(self.w.sessions["AG2"], {"action": "begin", "task": "unrelated"})["ticket"]
        self.install()
        self.binding()
        # A runtime capability may be registered before its business task exists.
        self.plan([self.node(task="producer")])
        revision = self.state()["state_revision"]
        self.store.reconcile(self.ag0)
        attempt = self.claim()
        self.receive(attempt)
        self.store.renew("instance-one")
        self.assertEqual(self.state()["state_revision"], revision)
        self.assertGreater(self.store.status()["runtime_revision"], 0)
        self.assertEqual(self.api.apply(self.w.sessions["AG2"], ticket)["status"], "committed")

    def test_binding_and_plan_require_explicit_authorization(self):
        self.install()
        before = self.persisted()
        binding = {"id": "worker", "role": "AG2", "host_kind": "fake", "thread_id": "thread",
                   "authorization_ref": "user-authorized-fabricated-workflow", "authorized": False}
        with self.assertRaisesRegex(GateError, "explicit_runtime_authorization_required"):
            self.store.bind(self.ag0, binding)
        self.assertEqual(before, self.persisted())
        self.binding()
        before = self.persisted()
        with self.assertRaisesRegex(GateError, "runtime_authorization_mismatch"):
            self.store.register_plan(self.ag0, {"id": "workflow", "revision": 1, "authorization_ref": "another-authorization",
                                                "nodes": [self.node()]})
        self.assertEqual(before, self.persisted())

    def test_adoption_ready_waits_for_owner_and_all_review_scopes(self):
        self.w.register("producer", "material", scope=["M1", "M2"], review=True)
        self.w.op("AG2", "start", task_id="producer")
        target = self.w.submit("producer")["ref"]
        self.install()
        self.binding("AG0", name="decision", thread="original-ag0-thread")
        self.plan([self.node(name="decide", binding="decision", actions=["adopt"],
                             conditions=[{"kind": "adoption_ready", "task": "producer", "ref": target}])])
        self.store.reconcile(self.ag0)
        work_id = self.work("decide")["id"]
        self.assertEqual(self.work("decide")["state"], "blocked")
        self.w.confirm(target, scope=["M1", "M2"])
        self.store.reconcile(self.ag0)
        self.assertIn("waiting_for_AG3", self.work("decide")["reason"])
        self.w.review(target, scope=["M1"])
        self.store.reconcile(self.ag0)
        self.assertEqual(self.work("decide")["state"], "blocked")
        self.w.review(target, scope=["M2"])
        self.store.reconcile(self.ag0)
        self.assertEqual(self.work("decide")["state"], "ready")
        self.assertEqual(self.work("decide")["id"], work_id)
        self.assertEqual(len(self.store.status()["works"]), 1)
        self.assertFalse(self.state()["adopted_pointers"], "supported receipts are not automatic adoption")

    def test_review_arriving_before_owner_does_not_trigger_decision(self):
        self.w.register("producer", "material", review=True)
        self.w.op("AG2", "start", task_id="producer")
        target = self.w.submit("producer")["ref"]
        self.install()
        self.binding("AG0", name="decision", thread="original-ag0-thread")
        self.plan([self.node(name="decide", binding="decision", actions=["adopt"],
                             conditions=[{"kind": "adoption_ready", "task": "producer"}])])
        self.w.review(target)
        self.store.reconcile(self.ag0)
        self.assertEqual(self.work("decide")["state"], "blocked")
        self.assertIn("waiting_for_AG2", self.work("decide")["reason"])
        self.w.confirm(target)
        self.store.reconcile(self.ag0)
        self.assertEqual(self.work("decide")["state"], "ready")

    def test_reconcile_deduplicates_business_events_ack_and_repeated_queries(self):
        _, work = self.decision_ready()
        original = {key: work[key] for key in ("id", "work_key", "facts_fingerprint", "inputs")}
        self.w.register("unrelated", "unrelated-material")
        inbox = self.c.inbox(self.ag0, "agent-context")
        self.w.op("AG0", "ack_events", consumer_id="agent-context", through_sequence=inbox["next_sequence"])
        for _ in range(3):
            self.store.reconcile(self.ag0)
        current = self.work("decide")
        self.assertEqual({key: current[key] for key in original}, original)
        self.assertEqual(len(self.store.status()["works"]), 1)
        with self.c.connect() as db:
            consumers = {row[0]: row[1] for row in db.execute("SELECT id,sequence FROM consumers WHERE role='AG0'")}
        self.assertIn("runtime-scheduler", consumers)
        self.assertIn("agent-context", consumers)

    def test_enqueue_and_cursor_rollback_together_at_crash_boundary(self):
        self.w.register("producer", "material")
        self.install()
        self.binding()
        self.plan([self.node()])
        before = self.persisted()
        def fail(name):
            if name == "runtime_after_enqueue":
                raise RuntimeError("injected crash after enqueue before cursor")
        self.c.failpoint = fail
        with self.assertRaisesRegex(RuntimeError, "injected crash"):
            self.store.reconcile(self.ag0)
        self.c.failpoint = None
        self.assertEqual(self.persisted(), before)
        result = self.store.reconcile(self.ag0)
        self.assertEqual(len(result["created"]), 1)
        self.assertGreater(result["through_sequence"], 0)
        with self.c.connect() as db:
            self.assertEqual(db.execute("SELECT sequence FROM consumers WHERE id='runtime-scheduler' AND role='AG0'").fetchone()[0], result["through_sequence"])

    def test_supervisor_and_same_host_thread_exclude_second_claim(self):
        self.w.register("producer", "material")
        self.w.register("other", "other-material")
        self.install()
        self.binding(name="worker-one", thread="shared-thread")
        self.binding(name="worker-two", thread="shared-thread")
        self.plan([self.node(binding="worker-one"), self.node(task="other", name="other-node", binding="worker-two")])
        self.store.reconcile(self.ag0)
        self.store.acquire_supervisor("instance-one")
        with self.assertRaisesRegex(GateError, "scheduler_already_running"):
            self.store.acquire_supervisor("instance-two")
        first = self.store.claim(self.work()["id"], "instance-one")
        with self.assertRaisesRegex(GateError, "work_not_ready"):
            self.store.claim(self.work()["id"], "instance-one")
        with self.assertRaisesRegex(GateError, "thread_has_unfinished_dispatch"):
            self.store.claim(self.work("other-node")["id"], "instance-one")
        self.store.update_attempt(first["dispatch_id"], "ready", instance_id="instance-one")
        self.assertEqual(self.store.claim(self.work("other-node")["id"], "instance-one")["state"], "claimed")

    def test_managed_business_task_rejects_missing_runtime_context(self):
        self.ready_production()
        before = self.state()["state_revision"]
        with self.assertRaisesRegex(GateError, "runtime_dispatch_required"):
            self.api.prepare(self.w.sessions["AG2"], {"action": "begin", "task": "producer"})
        result = self.c.execute(self.w.sessions["AG2"], "start", self.w.request(task_id="producer"))
        self.assertEqual(result["reasons"], ["runtime_dispatch_required"])
        self.assertEqual(self.state()["state_revision"], before)

    def test_business_guard_requires_execution_receipt_and_context_is_frozen_in_ticket(self):
        self.ready_production()
        attempt = self.claim()
        context = self.context(attempt)
        session = self.c.bind_local_operator("AG2", dispatch=context)
        # The executor may freeze business inputs before sending the model.
        begin = self.api.prepare(session, {"action": "begin", "task": "producer"})
        self.assertEqual(self.api.apply(session, begin["ticket"])["status"], "committed")
        output = self.root / "fabricated-output.txt"
        output.write_text("Fabricated output; no learner evidence.", encoding="utf-8")
        with self.assertRaisesRegex(GateError, "dispatch_not_received"):
            self.api.prepare(session, {"action": "deliver", "task": "producer", "path": output.name})
        session = self.receive(attempt)
        prepared = self.api.prepare(session, {"action": "deliver", "task": "producer", "path": output.name})
        envelope = self.api.load_ticket(session, prepared["ticket"])
        self.assertEqual(envelope["request"]["runtime_dispatch"], context)
        result = self.api.apply(session, prepared["ticket"])
        self.assertEqual(result["status"], "committed", result)
        with self.c.connect() as db:
            commits = db.execute("SELECT dispatch_id,body FROM runtime_commits").fetchall()
        self.assertEqual(len(commits), 2)
        self.assertEqual({row[0] for row in commits}, {attempt["dispatch_id"]})
        bodies = [json.loads(row[1]) for row in commits]
        self.assertTrue(any(body.get("phase") == "running" for body in bodies))
        self.assertTrue(any(body.get("ref") == result["ref"] for body in bodies))

    def test_begin_dispatch_rejects_wrong_thread_and_duplicate_receipt(self):
        self.ready_production()
        attempt = self.claim()
        self.store.update_attempt(attempt["dispatch_id"], "dispatching")
        before = self.state()["state_revision"]
        with self.assertRaisesRegex(GateError, "dispatch_thread_mismatch"):
            self.store.begin_dispatch(self.context(attempt, "unrelated-thread"), "AG2")
        self.store.begin_dispatch(self.context(attempt), "AG2")
        with self.assertRaisesRegex(GateError, "dispatch_already_received"):
            self.store.begin_dispatch(self.context(attempt), "AG2")
        self.assertEqual(self.state()["state_revision"], before)

    def test_prepared_ticket_cannot_publish_from_changed_thread_or_claim_epoch(self):
        self.ready_production()
        attempt = self.claim()
        session = self.receive(attempt)
        ticket = self.api.prepare(session, {"action": "begin", "task": "producer"})["ticket"]
        before = self.state()["state_revision"]
        # Prepare an independently malformed session, so a ticket cannot supply
        # the missing host identity to the caller.
        wrong = self.c.bind_local_operator("AG2", dispatch=self.context(attempt, "wrong-thread"))
        self.assertEqual(self.api.apply(wrong, ticket)["problem"], "runtime_dispatch_mismatch")
        with self.store.transaction() as db:
            work = self.store.get(db, "runtime_works", self.work()["id"])
            work["claim_epoch"] += 1
            self.store.put(db, "runtime_works", work["id"], work)
        stale = self.api.apply(session, ticket)
        self.assertEqual(stale["problem"], "stale_dispatch")
        self.assertEqual(self.state()["state_revision"], before)

    def test_user_pause_after_prepare_blocks_publication_in_same_business_entry(self):
        self.ready_production()
        session = self.receive(self.claim())
        ticket = self.api.prepare(session, {"action": "begin", "task": "producer"})["ticket"]
        before = self.state()["state_revision"]
        self.control.update(state_revision=1, paused_ids=["producer"])
        result = self.api.apply(session, ticket)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["problem"], "paused_scope")
        with self.c.connect() as db:
            self.assertEqual(self.c.state_revision(db), before)
            self.assertEqual(self.c.get(db, "tasks", "producer")["phase"], "registered")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM runtime_commits").fetchone()[0], 0)

    def test_changed_control_revision_invalidates_frozen_ticket_even_without_pause(self):
        self.ready_production()
        session = self.receive(self.claim())
        ticket = self.api.prepare(session, {"action": "begin", "task": "producer"})["ticket"]
        revision = self.state()["state_revision"]
        self.control["state_revision"] += 1
        result = self.api.apply(session, ticket)
        self.assertEqual(result["problem"], "prepared_controls_changed")
        with self.c.connect() as db:
            self.assertEqual(self.c.state_revision(db), revision)
            self.assertEqual(self.c.get(db, "tasks", "producer")["phase"], "registered")

    def test_context_does_not_grant_actions_on_tasks_outside_registered_plan(self):
        self.w.register("unrelated", "unrelated-material")
        self.ready_production()
        session = self.receive(self.claim())
        before = self.persisted()
        with self.assertRaisesRegex(GateError, "runtime_action_outside_plan"):
            self.api.prepare(session, {"action": "begin", "task": "unrelated"})
        self.assertEqual(self.persisted(), before)

    def test_host_unavailable_keeps_thread_occupied_across_supervisor_recovery(self):
        self.w.register("producer", "material")
        self.w.register("other", "other-material")
        self.install()
        self.binding()
        self.plan([self.node(), self.node(task="other", name="other-node")])
        self.store.reconcile(self.ag0)
        attempt = self.claim(lease_ms=10)
        self.store.update_attempt(attempt["dispatch_id"], "dispatching", instance_id="instance-one")
        self.store.update_attempt(attempt["dispatch_id"], "host_unavailable", instance_id="instance-one")
        with self.assertRaisesRegex(GateError, "thread_has_unfinished_dispatch"):
            self.store.claim(self.work("other-node")["id"], "instance-one")
        self.now += 11
        self.store.recover("instance-two")
        self.store.reconcile(self.ag0)
        self.assertEqual(self.work()["state"], "host_unavailable")
        with self.assertRaisesRegex(GateError, "thread_has_unfinished_dispatch"):
            self.store.claim(self.work("other-node")["id"], "instance-two")

    def test_late_opposing_opinion_invalidates_inflight_adoption_ticket(self):
        target, work = self.decision_ready()
        attempt = self.claim(work)
        session = self.receive(attempt, role="AG0", thread="original-ag0-thread")
        ticket = self.api.prepare(session, {"action": "adopt", "tasks": ["producer"]})["ticket"]
        self.w.op("AG2", "confirm", ref=target, receipt_id="late-opposing-owner", scope=["whole"],
                  intended_use="teaching", outcome="rejected", rationale="Fabricated new evidence opposes adoption.")
        revision = self.state()["state_revision"]
        result = self.api.apply(session, ticket)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["problem"], "runtime_basis_changed")
        self.assertEqual(self.state()["state_revision"], revision)
        self.assertFalse(self.state()["adopted_pointers"])

    def test_saved_result_has_immutable_path_hash_and_correlated_identity(self):
        self.ready_production()
        attempt = self.claim()
        self.receive(attempt)
        dispatch = attempt["dispatch_id"]
        value = {"dispatch_id": dispatch, "output": "Fabricated professional output.", "intents": []}
        saved = self.store.save_result(dispatch, value)
        path = Path(saved["result_path"])
        self.assertTrue(path.is_relative_to(self.c.meta_root / "runtime-results"))
        self.assertEqual(sha(path.read_bytes()), saved["result_sha256"])
        original = path.read_bytes()
        again = self.store.save_result(dispatch, deepcopy(value))
        self.assertEqual(again["result_path"], str(path))
        self.assertEqual(path.read_bytes(), original)
        with self.assertRaisesRegex(GateError, "runtime_result_changed"):
            self.store.save_result(dispatch, {**value, "output": "A different late output."})
        self.assertEqual(path.read_bytes(), original)
        with self.assertRaisesRegex(GateError, "invalid_correlated_result"):
            self.store.save_result(dispatch, {**value, "dispatch_id": "another-dispatch"})
        path.write_bytes(b"tampered")
        with self.assertRaisesRegex(GateError, "runtime_result_changed"):
            self.store.save_result(dispatch, value)

    def test_recovery_before_send_creates_new_epoch_and_fences_old_executor(self):
        self.ready_production()
        attempt = self.claim(lease_ms=10)
        self.now += 11
        self.store.recover("instance-two")
        self.assertEqual(self.work()["state"], "ready")
        recovered_epoch = self.work()["claim_epoch"]
        retry = self.store.claim(self.work()["id"], "instance-two")
        self.assertNotEqual(retry["dispatch_id"], attempt["dispatch_id"])
        self.assertEqual(retry["claim_epoch"], recovered_epoch + 1)
        with self.assertRaisesRegex(GateError, "stale_dispatch"):
            self.store.begin_dispatch(self.context(attempt), "AG2")
        with self.assertRaisesRegex(GateError, "stale_dispatch"):
            self.store.update_attempt(attempt["dispatch_id"], "dispatching", instance_id="instance-one")

    def test_recovery_after_send_keeps_ambiguous_attempt_and_never_requeues(self):
        self.ready_production()
        attempt = self.claim(lease_ms=10)
        self.store.update_attempt(attempt["dispatch_id"], "dispatching", instance_id="instance-one")
        self.now += 11
        self.store.recover("instance-two")
        recovered = self.work()
        self.assertEqual(recovered["state"], "dispatch_unknown")
        self.assertEqual(recovered["dispatch_id"], attempt["dispatch_id"])
        self.store.reconcile(self.ag0)
        self.assertEqual(self.work()["state"], "dispatch_unknown")
        with self.assertRaisesRegex(GateError, "work_not_ready"):
            self.store.claim(recovered["id"], "instance-two")
        with self.assertRaisesRegex(GateError, "invalid_runtime_transition"):
            self.store.update_attempt(attempt["dispatch_id"], "ready", instance_id="instance-two")
        with self.assertRaisesRegex(GateError, "scheduler_lease_lost"):
            self.store.update_attempt(attempt["dispatch_id"], "running", instance_id="instance-one")
        with self.c.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM runtime_attempts").fetchone()[0], 1)

    def test_lease_expiry_does_not_make_running_work_available_for_second_execution(self):
        self.ready_production()
        attempt = self.claim(lease_ms=10)
        self.receive(attempt)
        self.now += 11
        with self.assertRaisesRegex(GateError, "scheduler_lease_lost"):
            self.store.claim(self.work()["id"], "instance-one")
        self.store.recover("instance-two")
        self.assertEqual(self.work()["state"], "execution_unknown")
        with self.assertRaisesRegex(GateError, "work_not_ready"):
            self.store.claim(self.work()["id"], "instance-two")
        self.assertEqual(self.work()["dispatch_id"], attempt["dispatch_id"])

    def test_recovery_keeps_saved_result_for_business_retry_without_new_attempt(self):
        self.ready_production()
        attempt = self.claim(lease_ms=10)
        self.receive(attempt)
        saved = self.store.save_result(attempt["dispatch_id"], {"dispatch_id": attempt["dispatch_id"], "output": "Saved output.", "intents": []})
        self.now += 11
        self.store.recover("instance-two")
        self.assertEqual(self.work()["state"], "result_saved")
        with self.c.connect() as db:
            restored = self.store.get(db, "runtime_attempts", attempt["dispatch_id"])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM runtime_attempts").fetchone()[0], 1)
        self.assertEqual(restored["result_path"], saved["result_path"])
        self.assertEqual(sha(Path(restored["result_path"]).read_bytes()), saved["result_sha256"])
        self.assertEqual(restored["instance_id"], "instance-two")

    def test_completed_CLI_result_after_restart_is_received_without_model_resend(self):
        host = FakeRuntimeHost()
        scheduler = self.scheduler_production(host)
        scheduler.tick()
        attempt_id = self.work()["dispatch_id"]
        self.store.update_attempt(attempt_id, "running", instance_id="instance-one")
        self.now += 60001
        resumed = RuntimeScheduler(self.c, {"fake": host}, instance_id="instance-two")
        resumed.tick()
        self.assertEqual(self.work()["state"], "result_saved")
        resumed.tick()
        self.assertEqual(self.work()["state"], "done")
        self.assertEqual(self.work()["dispatch_id"], attempt_id)
        self.assertEqual(len(host.dispatches), 1)

    def test_running_CLI_receipt_is_persisted_before_a_late_result(self):
        host = FakeRuntimeHost(observation="running")
        scheduler = self.scheduler_production(host)
        scheduler.tick()
        scheduler.tick()
        with self.c.connect() as db:
            attempt = self.store.get(db, "runtime_attempts", self.work()["dispatch_id"])
        self.assertTrue(attempt.get("agent_received"))

    def test_known_receipt_failure_recovers_partial_result_without_rewriting_opinion(self):
        host = FakeRuntimeHost()
        scheduler = self.scheduler_production(host)
        scheduler.tick()
        dispatch = self.work()["dispatch_id"]
        host.result = {"dispatch_id": dispatch, "output": "Actually completed, with a partial professional conclusion.",
                       "intents": [{"action": "deliver", "task": "producer", "path": "$output"},
                                   {"action": "opinion", "task": "producer", "outcome": "partial", "rationale": "An unresolved actual evidence limit."}]}
        self.store.update_attempt(dispatch, "needs_user", instance_id="instance-one", reason="dispatch_not_sent")
        receipt = scheduler.reconcile_result(dispatch)
        self.assertEqual(receipt["work_state"], "done")
        self.assertEqual(receipt["model_resends"], 0)
        self.assertEqual(len(host.dispatches), 1)
        opinions = self.c.status(self.ag0)["receipts"]
        self.assertEqual(opinions[0]["outcome"], "partial")

    def test_result_repair_requires_original_thread_and_completed_evidence(self):
        host = FakeRuntimeHost(observation="running")
        scheduler = self.scheduler_production(host)
        scheduler.tick()
        dispatch = self.work()["dispatch_id"]
        self.store.update_attempt(dispatch, "needs_user", instance_id="instance-one", reason="dispatch_not_sent")
        with self.assertRaisesRegex(GateError, "completed_original_cli_result_required"):
            scheduler.reconcile_result(dispatch)
        self.assertEqual(self.work()["state"], "needs_user")
        self.assertEqual(len(host.dispatches), 1)

    def test_unrelated_needs_user_failure_cannot_be_reopened_as_receipt_bug(self):
        host = FakeRuntimeHost()
        scheduler = self.scheduler_production(host)
        scheduler.tick()
        dispatch = self.work()["dispatch_id"]
        self.store.update_attempt(dispatch, "needs_user", instance_id="instance-one", reason="actual_professional_gate_failure")
        with self.assertRaisesRegex(GateError, "runtime_result_repair_not_applicable"):
            scheduler.reconcile_result(dispatch)
        self.assertEqual(self.work()["state"], "needs_user")

    def test_temporary_SQLite_contention_does_not_kill_or_redispatch_companion(self):
        host = FakeRuntimeHost()
        scheduler = self.scheduler_production(host)
        original = scheduler.tick
        calls = []
        def busy_then_tick():
            calls.append(True)
            if len(calls) == 1:
                raise sqlite3.OperationalError("database is locked")
            return original()
        scheduler.tick = busy_then_tick
        scheduler.wakeup.wait = lambda seconds: None
        scheduler.run(max_seconds=5, stop_when_done=True)
        self.assertEqual(self.work()["state"], "done")
        self.assertEqual(len(host.dispatches), 1)

    def test_scheduler_waits_with_zero_host_dispatches_until_all_conditions_arrive(self):
        self.w.register("producer", "material", review=True)
        self.install()
        self.binding("AG0", name="decision", thread="original-ag0-thread")
        self.plan([self.node(name="decide", binding="decision", actions=["adopt"],
                             conditions=[{"kind": "adoption_ready", "task": "producer"}])])
        host = FakeRuntimeHost()
        scheduler = RuntimeScheduler(self.c, {"fake": host}, instance_id="instance-one")
        for _ in range(3):
            scheduler.tick()
        self.assertEqual(self.work("decide")["state"], "blocked")
        self.assertFalse(host.dispatches)
        self.assertFalse(host.inspections, "a blocked dependency needs no host polling")
        self.w.op("AG2", "start", task_id="producer")
        target = self.w.submit("producer")["ref"]
        self.w.confirm(target)
        scheduler.tick()
        self.assertFalse(host.dispatches)
        self.w.review(target)
        scheduler.tick()
        self.assertEqual(len(host.dispatches), 1)
        self.assertEqual(host.dispatches[0]["binding"]["thread_id"], "original-ag0-thread")

    def test_scheduler_correlated_result_sends_once_and_requires_business_receipts(self):
        host = FakeRuntimeHost()
        scheduler = self.scheduler_production(host)
        scheduler.tick()
        self.assertEqual(self.work()["state"], "accepted")
        self.assertEqual(len(host.dispatches), 1)
        scheduler.tick()
        self.assertEqual(self.work()["state"], "result_saved")
        with self.c.connect() as db:
            self.assertIsNone(self.c.get(db, "tasks", "producer").get("result_ref"))
        scheduler.tick()
        self.assertEqual(self.work()["state"], "done")
        for _ in range(3):
            scheduler.tick()
        self.assertEqual(len(host.dispatches), 1)
        self.assertEqual(len(host.observations), 1)
        task = next(item for item in self.state()["tasks"] if item["id"] == "producer")
        self.assertEqual(task["phase"], "submitted")
        self.assertEqual(len(self.state()["artifacts"]), 1)
        self.assertEqual(len(self.state()["receipts"]), 1)
        self.assertFalse(self.state()["adopted_pointers"])
        with self.c.connect() as db:
            attempt = self.store.get(db, "runtime_attempts", self.work()["dispatch_id"])
        self.assertEqual(len(attempt["business_receipts"]), 2)
        self.assertTrue(attempt["agent_received"])

    def test_scheduler_send_timeout_keeps_unknown_attempt_without_resending(self):
        host = FakeRuntimeHost(send_error=TimeoutError("host send response lost"), observation="unresolved")
        scheduler = self.scheduler_production(host)
        scheduler.tick()
        dispatch_id = self.work()["dispatch_id"]
        self.assertEqual(self.work()["state"], "dispatch_unknown")
        for _ in range(4):
            scheduler.tick()
        self.assertEqual(self.work()["state"], "dispatch_unknown")
        self.assertEqual(self.work()["dispatch_id"], dispatch_id)
        self.assertEqual(len(host.dispatches), 1)
        with self.c.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM runtime_attempts").fetchone()[0], 1)

    def test_scheduler_execution_timeout_preserves_original_attempt(self):
        host = FakeRuntimeHost(observation="unresolved")
        scheduler = self.scheduler_production(host, timeout=25)
        scheduler.tick()
        dispatch_id = self.work()["dispatch_id"]
        self.now += 26
        scheduler.tick()
        self.assertEqual(self.work()["state"], "execution_unknown")
        for _ in range(3):
            scheduler.tick()
        self.assertEqual(self.work()["dispatch_id"], dispatch_id)
        self.assertEqual(len(host.dispatches), 1)

    def test_scheduler_rejects_uncorrelated_result_and_publishes_no_artifact(self):
        host = FakeRuntimeHost(result={"dispatch_id": "unrelated-dispatch", "output": "Old unrelated output", "intents": []})
        scheduler = self.scheduler_production(host)
        scheduler.tick()
        scheduler.tick()
        self.assertEqual(self.work()["state"], "needs_user")
        self.assertEqual(self.work()["reason"], "invalid_correlated_result")
        self.assertFalse(self.state()["artifacts"])
        scheduler.tick()
        self.assertEqual(len(host.dispatches), 1)

    def test_scheduler_restart_publishes_saved_result_without_model_or_host_calls(self):
        host = FakeRuntimeHost()
        scheduler = self.scheduler_production(host)
        scheduler.tick()
        scheduler.tick()
        self.assertEqual(self.work()["state"], "result_saved")
        dispatch_id = self.work()["dispatch_id"]
        self.now += 60001
        replacement_host = FakeRuntimeHost(send_error=AssertionError("saved results must not invoke a model"))
        restarted = RuntimeScheduler(self.c, {"fake": replacement_host}, instance_id="instance-two")
        restarted.tick()
        self.assertEqual(self.work()["state"], "done")
        self.assertEqual(self.work()["dispatch_id"], dispatch_id)
        self.assertFalse(replacement_host.dispatches)
        self.assertFalse(replacement_host.inspections)
        self.assertFalse(replacement_host.observations)
        self.assertEqual(len(self.state()["artifacts"]), 1)
        self.assertEqual(len(self.state()["receipts"]), 1)

    def test_scheduler_restart_reuses_committed_ticket_after_partial_publish_crash(self):
        host = FakeRuntimeHost()
        scheduler = self.scheduler_production(host)
        scheduler.tick()
        scheduler.tick()
        def fail(name):
            if name == "runtime_after_publish":
                raise RuntimeError("injected crash after first business receipt")
        self.c.failpoint = fail
        with self.assertRaisesRegex(RuntimeError, "injected crash"):
            scheduler.tick()
        self.c.failpoint = None
        self.assertEqual(self.work()["state"], "result_saved")
        self.assertEqual(len(self.state()["artifacts"]), 1)
        self.assertFalse(self.state()["receipts"])
        self.now += 60001
        replacement_host = FakeRuntimeHost(send_error=AssertionError("publication retry must not invoke a model"))
        restarted = RuntimeScheduler(self.c, {"fake": replacement_host}, instance_id="instance-two")
        restarted.tick()
        self.assertEqual(self.work()["state"], "done")
        self.assertFalse(replacement_host.dispatches)
        self.assertEqual(len(self.state()["artifacts"]), 1)
        self.assertEqual(len(self.state()["receipts"]), 1)
        with self.c.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM runtime_attempts").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM runtime_commits").fetchone()[0], 3)

    def test_scheduler_shadow_mode_durably_evaluates_without_dispatch(self):
        host = FakeRuntimeHost()
        scheduler = self.scheduler_production(host, shadow=True)
        outcome = scheduler.tick()
        self.assertEqual(outcome["dispatches"], 0)
        self.assertTrue(outcome["shadow"])
        self.assertEqual(self.work()["state"], "ready")
        self.assertFalse(host.dispatches)
        self.assertFalse(host.inspections)

    def test_four_role_pipeline_uses_exact_review_adoption_and_ag1_snapshot(self):
        self.w.register("producer", "material", review=True)
        self.w.op("AG0", "register", id="summary", assignee="AG1", task_kind="production", scope=["whole"],
                  intended_use="teaching", wait_timeout_ms=300000,
                  inputs=[{"id": "material", "policy": "after_task", "producer_task_id": "producer", "scope": ["whole"], "intended_use": "teaching"}],
                  output={"id": "summary-artifact", "type": "ActivitySpec", "requires_ag3_review": False, "validation_profile": "utf8"})
        self.install()
        for role in ("AG0", "AG1", "AG2", "AG3"):
            self.binding(role, name=role, thread="original-" + role + "-thread")
        common = {"prompt": "One tiny fictional finite unit of work.", "use": "teaching", "completion": "business"}
        nodes = [
            {**common, "id": "research", "binding": "AG2", "task": "producer", "allowed_tasks": ["producer"], "manage_tasks": ["producer"],
             "allowed_actions": ["start", "submit", "confirm"], "conditions": [], "required_intents": ["deliver", "opinion"]},
            {**common, "id": "review", "binding": "AG3", "task": "review-task", "allowed_tasks": ["review-task", "producer"], "manage_tasks": ["review-task"],
             "allowed_actions": ["register", "start", "review"], "conditions": [{"kind": "submitted", "task": "producer"}], "required_intents": ["opinion"],
             "setup_intents": [{"action": "assign_review", "task": "review-task", "from_task": "producer"}]},
            {**common, "id": "decide", "binding": "AG0", "allowed_tasks": ["producer"], "allowed_actions": ["adopt"],
             "conditions": [{"kind": "adoption_ready", "task": "producer"}], "required_intents": ["adopt"], "result_via_file": True},
            {**common, "id": "design", "binding": "AG1", "task": "summary", "allowed_tasks": ["summary"], "manage_tasks": ["summary"],
             "allowed_actions": ["start", "submit"], "conditions": [{"kind": "adopted", "task": "producer"}], "required_intents": ["deliver"]},
            {**common, "id": "report", "binding": "AG0", "allowed_tasks": ["producer", "summary"], "allowed_actions": ["adopt"],
             "conditions": [{"kind": "work_done", "node": "design"}, {"kind": "adopted", "task": "producer"}, {"kind": "submitted", "task": "summary"}],
             "completion": "result", "required_intents": [], "result_via_file": True},
        ]
        self.plan(nodes)
        host = FourRoleRuntimeHost()
        scheduler = RuntimeScheduler(self.c, {"fake": host}, instance_id="instance-one")
        for _ in range(24):
            scheduler.tick()
            states = {work["node"]["id"]: work["state"] for work in self.store.status()["works"]}
            if all(state == "done" for state in states.values()):
                break
        self.assertEqual(states, {node["id"]: "done" for node in nodes}, self.store.status())
        self.assertEqual([send["binding"]["role"] for send in host.dispatches], ["AG2", "AG3", "AG0", "AG1", "AG0"])
        packets = {packet["node_id"]: packet for packet in host.packets.values()}
        tasks = {task["id"]: task for task in self.state()["tasks"]}
        exact = tasks["producer"]["result_ref"]
        self.assertEqual(tasks["review-task"]["target_ref"], exact)
        self.assertEqual(packets["review"]["inputs"][0]["ref"], exact)
        self.assertEqual(packets["review"]["task_snapshot"][0]["ref"], exact)
        self.assertEqual(packets["design"]["task_snapshot"][0]["ref"], exact)
        self.assertEqual(packets["design"]["task_snapshot"][0]["text"], "blue fabricated-four-role-nonce")
        self.assertEqual({opinion["by"] for opinion in packets["decide"]["decision_basis"][0]["opinions"]}, {"AG2", "AG3"})
        self.assertEqual({send["binding"]["thread_id"] for send in host.dispatches if send["binding"]["role"] == "AG0"}, {"original-AG0-thread"})
        self.assertTrue(packets["decide"]["result_via_file"])
        self.assertTrue(packets["report"]["result_via_file"])
        self.assertEqual(self.state()["adopted_pointers"][0]["revision"], exact["revision"])
        self.assertEqual(len(self.state()["artifacts"]), 2)
        for _ in range(2):
            scheduler.tick()
        self.assertEqual(len(host.dispatches), 5)

    def test_review_setup_rejects_explicit_target_override_before_dispatch(self):
        first = self.w.candidate("material")["ref"]
        other = self.w.candidate("other-material")["ref"]
        with self.c.connect() as db:
            source = self.c.artifact(db, first)["task_id"]
            other_task = self.c.artifact(db, other)["task_id"]
        self.install()
        self.binding("AG3")
        node = {**self.node(task=source, actions=["register", "start", "review"]), "task": "review-task",
                "allowed_tasks": [source, other_task, "review-task"],
                "conditions": [{"kind": "submitted", "task": source, "ref": first}],
                "setup_intents": [{"action": "assign_review", "task": "review-task", "from_task": source, "target": other}]}
        before = self.persisted()
        with self.assertRaisesRegex(GateError, "unsupported_runtime_setup"):
            self.plan([node])
        self.assertEqual(self.persisted(), before)

    def test_existing_review_task_with_wrong_exact_source_is_never_dispatched(self):
        first = self.w.candidate("material")["ref"]
        other = self.w.candidate("other-material")["ref"]
        with self.c.connect() as db:
            source = self.c.artifact(db, first)["task_id"]
        self.w.op("AG0", "register", id="review-task", assignee="AG3", task_kind="review", scope=["whole"], intended_use="teaching", target_ref=other)
        self.install()
        self.binding("AG3")
        node = {**self.node(task=source, actions=["register", "start", "review"]), "task": "review-task", "allowed_tasks": [source, "review-task"],
                "conditions": [{"kind": "submitted", "task": source, "ref": first}],
                "setup_intents": [{"action": "assign_review", "task": "review-task", "from_task": source}]}
        self.plan([node])
        host = FakeRuntimeHost()
        scheduler = RuntimeScheduler(self.c, {"fake": host}, instance_id="instance-one")
        scheduler.tick()
        self.assertEqual(self.work()["state"], "failed")
        self.assertEqual(self.work()["reason"], "runtime_setup_target_changed")
        self.assertFalse(host.dispatches)

    def test_saved_result_rechecks_original_context_after_takeover(self):
        self.ready_production()
        attempt = self.claim(lease_ms=10)
        self.receive(attempt)
        context = self.context(attempt)
        self.store.assert_dispatch(context, "AG2")
        self.now += 11
        self.store.recover("instance-two")
        with self.assertRaisesRegex(GateError, "stale_dispatch"):
            self.store.save_result(attempt["dispatch_id"], {"dispatch_id": attempt["dispatch_id"], "output": "Late old executor output.", "intents": []},
                                   context=context, role="AG2")
        self.assertEqual(self.work()["state"], "execution_unknown")
        restored = self.store.lookup("runtime_attempts", attempt["dispatch_id"])
        self.assertNotIn("result_sha256", restored)

    def test_required_intents_reject_missing_opinion_before_any_publication(self):
        host = FakeRuntimeHost()
        scheduler = self.scheduler_production(host, required_intents=["deliver", "opinion"])
        scheduler.tick()
        dispatch = self.work()["dispatch_id"]
        host.result = {"dispatch_id": dispatch, "output": "Incomplete professional result.",
                       "intents": [{"action": "deliver", "task": "producer", "path": "$output"}]}
        scheduler.tick()
        scheduler.tick()
        self.assertEqual(self.work()["state"], "needs_user")
        self.assertEqual(self.work()["reason"], "runtime_required_intent_missing")
        self.assertFalse(self.state()["artifacts"])
        self.assertFalse(self.state()["receipts"])

    def test_explicit_business_completion_rejects_empty_intents(self):
        host = FakeRuntimeHost()
        scheduler = self.scheduler_production(host)
        scheduler.tick()
        host.result = {"dispatch_id": self.work()["dispatch_id"], "output": "Just a chat completion claim.", "intents": []}
        scheduler.tick()
        scheduler.tick()
        self.assertEqual(self.work()["state"], "needs_user")
        self.assertEqual(self.work()["reason"], "runtime_business_receipt_required")
        self.assertFalse(self.state()["artifacts"])

    def test_result_file_rejects_malformed_intent_entries_before_persistence(self):
        self.ready_production()
        attempt = self.claim()
        self.receive(attempt)
        before = self.persisted()
        for intents in ([None], [{}], ["deliver"], [{"action": 1}], [{"action": ""}]):
            with self.subTest(intents=intents):
                with self.assertRaisesRegex(GateError, "invalid_correlated_result"):
                    self.store.save_result(attempt["dispatch_id"], {"dispatch_id": attempt["dispatch_id"], "output": "Malformed fictional result.", "intents": intents},
                                           context=self.context(attempt), role="AG2")
                self.assertEqual(self.persisted(), before)

    def test_result_sender_identity_must_match_actual_bound_thread_and_role(self):
        self.ready_production()
        attempt = self.claim()
        self.receive(attempt)
        value = {"dispatch_id": attempt["dispatch_id"], "output": "An unrelated sender's output.", "intents": []}
        for context, role in ((self.context(attempt, "different-thread"), "AG2"), (self.context(attempt), "AG1")):
            with self.subTest(context=context, role=role):
                with self.assertRaisesRegex(GateError, "dispatch_thread_mismatch"):
                    self.store.save_result(attempt["dispatch_id"], value, context=context, role=role)
        self.assertEqual(self.work()["state"], "running")
        self.assertNotIn("result_sha256", self.store.lookup("runtime_attempts", attempt["dispatch_id"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
