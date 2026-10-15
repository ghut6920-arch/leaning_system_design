"""Acceptance for the short agent interface; all professional data are fabricated."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
sys.path.insert(0, str(SUITE / "scripts"))
from coordinator.agent_api import AgentCoordinator
from coordinator.workspace import GateError
from test_coordinator_complete import CompleteWorkflow


class CoordinatorAgentApiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tac-agent-api-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.control = {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []}
        self.w = CompleteWorkflow(self.root, lambda: deepcopy(self.control))
        self.c = self.w.coordinator
        self.api = AgentCoordinator(self.c)

    def state(self):
        return self.c.status(self.w.sessions["AG0"])

    def persisted(self):
        """Compare all durable business, operation, cursor, and event records."""
        with self.c.connect() as db:
            names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            return {name: sorted(tuple(r) for r in db.execute('SELECT * FROM "' + name + '"')) for name in names}

    def prepare(self, role, intent):
        result = self.api.prepare(self.w.sessions[role], intent)
        self.assertEqual(result["status"], "prepared", result)
        return result

    def run_intent(self, role, intent):
        ticket = self.prepare(role, intent)["ticket"]
        result = self.api.apply(self.w.sessions[role], ticket)
        self.assertEqual(result["status"], "committed", result)
        return result

    def cli(self, role, *arguments, intent=None, expect=0):
        arguments = list(arguments)
        if intent is not None:
            path = self.root / "cli-intent.json"
            path.write_text(json.dumps(intent), encoding="utf-8")
            arguments += ["--intent-file", str(path)]
        process = subprocess.run([sys.executable, str(SUITE / "scripts/coordinate_agents.py"),
                                  "--workspace", str(self.root), "--role", role, *arguments],
                                 capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(process.returncode, expect, process.stdout + process.stderr)
        self.assertFalse(process.stderr, process.stderr)
        return json.loads(process.stdout)

    @staticmethod
    def assignment(task="material-task", output="material", *, kind="MaterialUse", scope=None, inputs=None, review=False):
        return {"action": "assign", "task": task, "output": {"id": output, "type": kind, "validation": "utf8"},
                "scope": scope or ["whole"], "use": "teaching", "inputs": inputs or [], "review_required": review}

    def artifact_file(self, task):
        relative = "artifacts/" + task + ".md"
        (self.root / "artifacts").mkdir(exist_ok=True)
        (self.root / relative).write_text("Fabricated version for " + task + "; no learner evidence.\n", encoding="utf-8")
        return relative

    def produced(self, task="material-task", output="material", *, kind="MaterialUse", scope=None, inputs=None, review=False):
        self.run_intent("AG0", self.assignment(task, output, kind=kind, scope=scope, inputs=inputs, review=review))
        owner = "AG1" if kind == "ActivitySpec" else "AG2"
        self.run_intent(owner, {"action": "begin", "task": task})
        result = self.run_intent(owner, {"action": "deliver", "task": task, "path": self.artifact_file(task), "changed_scope": scope})
        return result["ref"]

    def owner_opinion(self, task, *, role="AG2", outcome="supported", **extra):
        return self.run_intent(role, {"action": "opinion", "task": task, "outcome": outcome,
                                     "rationale": "Fabricated explicit professional judgment.", **extra})

    def seed(self, *, scope=None, review=False):
        target = self.w.candidate("material", scope=scope, review=review)["ref"]
        receipts = [self.w.confirm(target, scope=scope)]
        if review:
            receipts.append(self.w.review(target, scope=scope))
        self.w.adopt(target, receipts, scope=scope)
        with self.c.connect() as db:
            task = self.c.artifact(db, target)["task_id"]
        return target, receipts, task

    def refuses_prepare(self, role, intent, codes):
        before = self.persisted()
        try:
            response = self.api.prepare(self.w.sessions[role], intent)
        except GateError as error:
            actual = error.code
        else:
            self.assertNotEqual(response["status"], "prepared", response)
            actual = response.get("problem")
        self.assertIn(actual, codes)
        self.assertEqual(self.persisted(), before)

    def refuses_apply(self, role, ticket, codes):
        before = self.persisted()
        try:
            response = self.api.apply(self.w.sessions[role], ticket)
        except GateError as error:
            actual = error.code
        else:
            self.assertNotEqual(response["status"], "committed", response)
            actual = response.get("problem")
        self.assertIn(actual, codes)
        self.assertEqual(self.persisted(), before)

    def test_daily_closed_loop_keeps_professional_opinion_and_adoption_explicit(self):
        target = self.produced(review=True)
        state = self.state()
        self.assertFalse(state["receipts"])
        self.assertFalse(state["adopted_pointers"])
        self.owner_opinion("material-task")
        self.refuses_prepare("AG0", {"action": "adopt", "tasks": ["material-task"]}, {"ag3_review_required"})
        self.run_intent("AG0", {"action": "assign_review", "task": "exact-review", "from_task": "material-task"})
        self.run_intent("AG3", {"action": "begin", "task": "exact-review"})
        review = self.run_intent("AG3", {"action": "opinion", "task": "exact-review", "outcome": "supported",
                                           "rationale": "Fabricated version-specific review; no real professional assessment."})
        self.assertEqual(review["target_ref"], target)
        self.assertFalse(self.state()["adopted_pointers"])
        self.run_intent("AG0", {"action": "adopt", "tasks": ["material-task"]})
        self.assertEqual(self.c.resolve(self.w.sessions["AG1"], "material", "teaching", ["whole"])["ref"], target)

    def test_prepare_preview_leaves_all_durable_business_and_events_unchanged(self):
        before = self.persisted()
        preview = self.prepare("AG0", self.assignment())
        self.assertEqual(self.persisted(), before)
        self.assertEqual(preview["preview"]["assigned_to"], "AG2")
        self.assertFalse(self.state()["tasks"])
        self.assertTrue((self.api.ticket_root / (preview["ticket"] + ".json")).is_file())

    def test_same_ticket_retry_returns_saved_commit_without_new_draft_or_event(self):
        ticket = self.prepare("AG0", self.assignment())["ticket"]
        first = self.api.apply(self.w.sessions["AG0"], ticket)
        self.assertEqual(first["status"], "committed")
        committed = self.persisted()
        second = self.api.apply(self.w.sessions["AG0"], ticket)
        self.assertEqual(second["status"], "committed", second)
        self.assertEqual(self.persisted(), committed)
        self.assertEqual(self.api.saved(self.w.sessions["AG0"], ticket)["status"], "committed")

    def test_commit_reply_and_receipts_do_not_depend_on_post_commit_boundary_read(self):
        self.run_intent("AG0", self.assignment(review=True))
        self.run_intent("AG2", {"action": "begin", "task": "material-task"})
        delivered_ticket = self.prepare("AG2", {"action": "deliver", "task": "material-task", "path": self.artifact_file("material-task")})["ticket"]
        with patch.object(self.c, "boundary", side_effect=GateError("control_changed_during_read")):
            delivered = self.api.apply(self.w.sessions["AG2"], delivered_ticket)
            self.assertEqual(delivered["status"], "committed")
            self.assertEqual(delivered["receipt"]["kind"], "artifact_submission")
            self.assertEqual(self.api.saved(self.w.sessions["AG2"], delivered_ticket)["result"]["ref"], delivered["ref"])
        self.run_intent("AG0", {"action": "assign_review", "task": "review", "from_task": "material-task"})
        self.run_intent("AG3", {"action": "begin", "task": "review"})
        review_ticket = self.prepare("AG3", {"action": "opinion", "task": "review", "outcome": "supported", "rationale": "Fabricated direct review."})["ticket"]
        with patch.object(self.c, "boundary", side_effect=GateError("control_changed_during_read")):
            reviewed = self.api.apply(self.w.sessions["AG3"], review_ticket)
            self.assertEqual(reviewed["status"], "committed")
            self.assertEqual(reviewed["receipt"]["kind"], "review_submission")
            self.assertEqual(reviewed["receipt"]["target_ref"], delivered["ref"])
            self.assertEqual(self.api.saved(self.w.sessions["AG3"], review_ticket)["result"]["receipt_id"], reviewed["receipt_id"])

    def test_lost_commit_confirmation_can_be_queried_and_retried_without_duplicate_output(self):
        self.run_intent("AG0", self.assignment())
        self.run_intent("AG2", {"action": "begin", "task": "material-task"})
        ticket = self.prepare("AG2", {"action": "deliver", "task": "material-task", "path": self.artifact_file("material-task")})["ticket"]

        def lose_confirmation(name):
            if name == "after_commit":
                raise RuntimeError("Fabricated lost commit confirmation")

        with patch.object(self.c, "checkpoint", side_effect=lose_confirmation):
            unknown = self.api.apply(self.w.sessions["AG2"], ticket)
        self.assertEqual(unknown["status"], "commit_status_unknown")
        self.assertEqual(unknown["ticket"], ticket)
        committed = self.persisted()
        saved = self.api.saved(self.w.sessions["AG2"], ticket)
        self.assertEqual(saved["status"], "committed")
        self.assertEqual(saved["result"]["ref"], {"id": "material", "revision": 1})
        recovered = self.api.apply(self.w.sessions["AG2"], ticket)
        self.assertEqual(recovered["status"], "committed")
        self.assertEqual(recovered["receipt"]["kind"], "artifact_submission")
        self.assertEqual(self.persisted(), committed)

    def test_durable_do_identity_recovers_lost_confirmation_without_duplicate_draft_or_event(self):
        intent = self.assignment()
        key = str((self.root / "assign-intent.json").resolve())

        def lose_confirmation(name):
            if name == "after_commit":
                raise RuntimeError("Fabricated lost entire do confirmation")

        with patch.object(self.c, "checkpoint", side_effect=lose_confirmation):
            uncertain = self.api.do(self.w.sessions["AG0"], intent, request_key=key)
        self.assertEqual(uncertain["status"], "commit_status_unknown")
        committed = self.persisted()
        recovered = self.api.do(self.w.sessions["AG0"], deepcopy(intent), request_key=key)
        self.assertEqual(recovered["status"], "committed")
        self.assertEqual(recovered["ticket"], uncertain["ticket"])
        self.assertEqual(self.persisted(), committed)
        self.assertEqual(len(committed["drafts"]), 1)
        self.assertEqual(self.api.saved_intent(self.w.sessions["AG0"], intent, request_key=key)["status"], "committed")

    def test_repeating_do_after_discarding_response_reuses_canonical_intent_and_actual_output(self):
        self.run_intent("AG0", self.assignment())
        self.run_intent("AG2", {"action": "begin", "task": "material-task"})
        intent = {"action": "deliver", "task": "material-task", "path": self.artifact_file("material-task")}
        key = str((self.root / "deliver-intent.json").resolve())
        # Simulate a host that lost the complete response, including its ticket.
        self.api.do(self.w.sessions["AG2"], intent, request_key=key)
        committed = self.persisted()
        reordered = dict(reversed(list(intent.items())))
        recovered = self.api.do(self.w.sessions["AG2"], reordered, request_key=key)
        self.assertEqual(recovered["status"], "committed")
        self.assertEqual(recovered["receipt"]["kind"], "artifact_submission")
        self.assertEqual(recovered["ref"], {"id": "material", "revision": 1})
        self.assertEqual(self.persisted(), committed)
        self.assertEqual(len(committed["artifacts"]), 1)
        saved = self.api.saved_intent(self.w.sessions["AG2"], reordered, request_key=key)
        self.assertEqual(saved["status"], "committed")
        self.assertEqual(saved["result"]["ref"], recovered["ref"])

    def test_repeated_do_never_recompiles_after_controls_change_but_saved_intent_recovers_commit(self):
        intent = self.assignment()
        key = str((self.root / "assign-intent.json").resolve())
        original = self.api.do(self.w.sessions["AG0"], intent, request_key=key)
        self.assertEqual(original["status"], "committed")
        committed = self.persisted()
        self.control.update(state_revision=1, paused_ids=["unrelated-output"])
        rejected = self.api.do(self.w.sessions["AG0"], intent, request_key=key)
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(rejected["problem"], "prepared_controls_changed")
        self.assertEqual(rejected["ticket"], original["ticket"])
        self.assertEqual(self.persisted(), committed)
        saved = self.api.saved_intent(self.w.sessions["AG0"], intent, request_key=key)
        self.assertEqual(saved["status"], "committed")
        self.assertEqual(saved["ticket"], original["ticket"])

    def test_stale_ticket_conflicts_instead_of_refreshing_or_retrying_decision(self):
        first = self.prepare("AG0", self.assignment("first", "one"))["ticket"]
        stale = self.prepare("AG0", self.assignment("second", "two"))["ticket"]
        self.assertEqual(self.api.apply(self.w.sessions["AG0"], first)["status"], "committed")
        self.refuses_apply("AG0", stale, {"state_revision_conflict"})
        self.assertEqual([t["id"] for t in self.state()["tasks"]], ["first"])

    def test_old_version_review_cannot_be_selected_for_a_new_version(self):
        old, old_receipts, _ = self.seed(review=True)
        new = self.produced("new-version", review=True)
        self.assertNotEqual(old, new)
        owner = self.owner_opinion("new-version")["receipt_id"]
        self.refuses_prepare("AG0", {"action": "adopt", "tasks": [{"task": "new-version", "receipts": [owner, old_receipts[1]]}]},
                             {"receipt_version_mismatch"})
        self.assertEqual(self.c.resolve(self.w.sessions["AG2"], "material", "teaching", ["whole"])["ref"], old)

    def test_later_support_does_not_silently_resolve_an_opposing_opinion(self):
        self.produced()
        self.owner_opinion("material-task", outcome="rejected")
        self.owner_opinion("material-task", outcome="supported")
        self.refuses_prepare("AG0", {"action": "adopt", "tasks": ["material-task"]}, {"conflicting_professional_receipts"})
        self.assertEqual(len(self.state()["receipts"]), 2)
        self.assertFalse(self.state()["adopted_pointers"])

    def test_edit_base_defaults_to_adopted_version_despite_newer_candidate(self):
        adopted, _, _ = self.seed()
        newer = self.w.candidate("material")["ref"]
        prepared = self.prepare("AG0", self.assignment("later-draft", "material"))
        self.assertGreater(newer["revision"], adopted["revision"])
        self.assertEqual(prepared["preview"]["base"], adopted)
        self.assertEqual(self.c.resolve(self.w.sessions["AG2"], "material", "teaching", ["whole"])["ref"], adopted)

    def test_split_adopted_scope_demands_an_explicit_edit_base(self):
        first = self.w.candidate("material", scope=["M1", "M3"])["ref"]
        first_receipt = self.w.confirm(first, scope=["M1", "M3"])
        self.w.adopt(first, [first_receipt], scope=["M1"])
        second = self.w.candidate("material", scope=["M1", "M3"], changed_scope=["M3"])["ref"]
        second_receipt = self.w.confirm(second, scope=["M1", "M3"])
        self.w.adopt(second, [second_receipt], scope=["M3"])
        intent = self.assignment("split-edit", "material", scope=["M1", "M3"])
        self.refuses_prepare("AG0", intent, {"ambiguous_edit_base"})
        intent["base"] = first
        self.assertEqual(self.prepare("AG0", intent)["preview"]["base"], first)

    def test_candidate_only_existing_output_requires_explicit_revision_choice(self):
        candidate = self.w.candidate("material")["ref"]
        intent = self.assignment("later", "material")
        self.refuses_prepare("AG0", intent, {"explicit_edit_base_required"})
        intent["base"] = candidate
        self.assertEqual(self.prepare("AG0", intent)["preview"]["base"], candidate)

    def test_desk_is_bounded_role_specific_and_omits_internal_history_and_percent(self):
        self.produced("done", "material")
        for number in range(4):
            self.run_intent("AG0", self.assignment("ag1-" + str(number), "activity-" + str(number), kind="ActivitySpec"))
        self.run_intent("AG1", {"action": "begin", "task": "ag1-0"})
        desk = self.api.desk(self.w.sessions["AG1"], limit=2)
        self.assertEqual(len(desk["tasks"]), 2)
        self.assertEqual(desk["remaining"]["tasks"], 2)
        self.assertTrue(all(row["assigned_to"] == "AG1" for row in desk["tasks"]))
        self.assertNotIn("done", [row["task"] for row in desk["tasks"]])
        self.assertTrue(all(row.get("status") in {None, "running", "submitted", "blocked"} for row in desk["tasks"]))
        rendered = json.dumps(desk, ensure_ascii=False)
        for internals in ("sha256", "basis_signature", "state_revision", "expected_pointers", "progress", "percent", "snapshot", "adoption_history"):
            self.assertNotIn('"' + internals + '"', rendered)

    def test_started_task_keeps_exact_old_input_when_upstream_is_submitted_and_adopted(self):
        original, _, _ = self.seed()
        inputs = [{"artifact": "material", "scope": ["whole"], "use": "teaching"}]
        self.run_intent("AG0", self.assignment("dependent", "activity", kind="ActivitySpec", inputs=inputs))
        self.run_intent("AG1", {"action": "begin", "task": "dependent"})
        pinned = self.c.read_snapshot(self.w.sessions["AG1"], "dependent")
        self.assertEqual(pinned[0]["ref"], original)
        newer = self.w.candidate("material")["ref"]
        self.assertEqual(self.c.resolve(self.w.sessions["AG1"], "material", "teaching", ["whole"])["ref"], original)
        self.w.adopt(newer, [self.w.confirm(newer)])
        still_pinned = self.c.read_snapshot(self.w.sessions["AG1"], "dependent")
        self.assertEqual(still_pinned[0]["ref"], original)
        self.assertEqual(still_pinned[0]["content"], pinned[0]["content"])
        desk = self.api.desk(self.w.sessions["AG1"], task_id="dependent")
        self.assertTrue(desk["attention"])
        self.assertTrue(all(item["target"] == "dependent" for item in desk["attention"]))

    def test_alerts_are_relevant_and_pull_never_acknowledges_delivery(self):
        self.run_intent("AG0", self.assignment("ag2-only", "ag2-output"))
        self.run_intent("AG0", self.assignment("ag1-only", "ag1-output", kind="ActivitySpec"))
        before = self.persisted()
        first = self.api.alerts(self.w.sessions["AG1"], "agent-one")
        again = self.api.alerts(self.w.sessions["AG1"], "agent-one")
        self.assertEqual(first, again)
        self.assertEqual(self.persisted(), before)
        self.assertTrue(first["notifications"])
        self.assertNotIn("ag2-only", json.dumps(first))
        self.assertNotIn("ag2-output", json.dumps(first))
        self.run_intent("AG1", {"action": "ack", "consumer": "agent-one", "through": first["through"]})
        self.assertFalse(self.api.alerts(self.w.sessions["AG1"], "agent-one")["notifications"])
        self.assertTrue(self.api.alerts(self.w.sessions["AG0"], "agent-one")["notifications"])

    def test_assignment_never_guesses_review_policy_or_input_dependency_list(self):
        for missing in ("review_required", "inputs"):
            with self.subTest(missing=missing):
                intent = self.assignment()
                intent.pop(missing)
                self.refuses_prepare("AG0", intent, {"explicit_agent_intent_fields_required", "explicit_review_policy_and_inputs_required", "invalid_agent_intent", "explicit_review_policy_required", "explicit_inputs_required"})
        self.refuses_prepare("AG0", self.assignment() | {"review_required": "false"}, {"explicit_review_policy_and_inputs_required", "explicit_review_policy_required"})

    def test_dependency_wait_always_requires_an_explicit_finite_timeout(self):
        self.run_intent("AG0", self.assignment("producer", "material"))
        intent = self.assignment("dependent", "activity", kind="ActivitySpec",
                                 inputs=[{"artifact": "material", "after_task": "producer", "scope": ["whole"], "use": "teaching"}])
        self.refuses_prepare("AG0", intent, {"explicit_agent_intent_fields_required", "wait_timeout_ms_required"})
        intent["wait_ms"] = 1000
        self.run_intent("AG0", intent)
        begun = self.run_intent("AG1", {"action": "begin", "task": "dependent"})
        self.assertEqual(begun["work_status"], "blocked")
        row = self.api.desk(self.w.sessions["AG1"], task_id="dependent")["tasks"][0]
        self.assertEqual(row["status"], "blocked")
        self.assertEqual(row["reason"], "waiting_for_dependency")

    def test_professional_opinion_never_guesses_outcome_or_rationale(self):
        self.produced()
        for missing in ("outcome", "rationale"):
            with self.subTest(missing=missing):
                intent = {"action": "opinion", "task": "material-task", "outcome": "supported", "rationale": "Fabricated explicit rationale."}
                intent.pop(missing)
                self.refuses_prepare("AG2", intent, {"explicit_agent_intent_fields_required", "explicit_professional_opinion_required", "invalid_agent_intent", "invalid_receipt_outcome", "rationale_required"})
        self.assertFalse(self.state()["receipts"])

    def test_ticket_is_role_bound_and_only_assignee_can_begin_work(self):
        ticket = self.prepare("AG0", self.assignment())["ticket"]
        self.refuses_apply("AG2", ticket, {"request_ticket_mismatch"})
        self.assertEqual(self.api.apply(self.w.sessions["AG0"], ticket)["status"], "committed")
        self.refuses_prepare("AG0", {"action": "begin", "task": "material-task"}, {"task_assignee_required"})
        self.refuses_prepare("AG1", {"action": "begin", "task": "material-task"}, {"task_assignee_required"})

    def test_pause_after_prepare_prevents_application_and_does_not_register_task(self):
        ticket = self.prepare("AG0", self.assignment())["ticket"]
        self.control.update(state_revision=1, paused_ids=["material"])
        self.refuses_apply("AG0", ticket, {"paused_scope", "prepared_controls_changed"})
        self.assertFalse(self.persisted()["tasks"])

    def test_any_control_change_requires_reconsidering_prepared_decision(self):
        ticket = self.prepare("AG0", self.assignment())["ticket"]
        self.control.update(state_revision=1, paused_ids=["unrelated-output"])
        self.refuses_apply("AG0", ticket, {"prepared_controls_changed"})

    def test_delivery_ticket_cannot_register_different_file_bytes(self):
        self.run_intent("AG0", self.assignment())
        self.run_intent("AG2", {"action": "begin", "task": "material-task"})
        relative = self.artifact_file("material-task")
        ticket = self.prepare("AG2", {"action": "deliver", "task": "material-task", "path": relative})["ticket"]
        (self.root / relative).write_text("Different fabricated contents after the delivery decision.\n", encoding="utf-8")
        self.refuses_apply("AG2", ticket, {"prepared_files_changed", "artifact_fingerprint_changed"})
        self.assertFalse(self.state()["artifacts"])
        self.assertEqual(self.api.desk(self.w.sessions["AG2"])["tasks"][0]["status"], "running")

    def test_file_change_at_execute_boundary_is_rejected_in_mutation_transaction(self):
        self.run_intent("AG0", self.assignment())
        self.run_intent("AG2", {"action": "begin", "task": "material-task"})
        relative = self.artifact_file("material-task")
        ticket = self.prepare("AG2", {"action": "deliver", "task": "material-task", "path": relative})["ticket"]
        original_execute = self.c.execute

        def change_before_execute(session, action, request):
            # Simulates an upstream write after any agent-layer precheck but
            # before the actual write transaction obtains its frozen request.
            (self.root / relative).write_text("Fabricated race at execution boundary.\n", encoding="utf-8")
            return original_execute(session, action, request)

        with patch.object(self.c, "execute", side_effect=change_before_execute):
            self.refuses_apply("AG2", ticket, {"prepared_files_changed"})
        self.assertFalse(self.state()["artifacts"])

    def test_control_change_at_execute_boundary_is_rejected_even_if_scope_allowed(self):
        ticket = self.prepare("AG0", self.assignment())["ticket"]
        original_execute = self.c.execute

        def change_before_execute(session, action, request):
            self.control.update(state_revision=1, paused_ids=["unrelated-output"])
            return original_execute(session, action, request)

        with patch.object(self.c, "execute", side_effect=change_before_execute):
            self.refuses_apply("AG0", ticket, {"prepared_controls_changed"})
        self.assertFalse(self.persisted()["tasks"])

    def test_actual_artifact_and_review_receipts_are_reported_without_fake_completion(self):
        self.produced(review=True)
        production = self.api.desk(self.w.sessions["AG2"])["tasks"][0]
        self.assertEqual(production["status"], "submitted")
        self.assertEqual(production["receipt"]["kind"], "artifact_submission")
        self.assertEqual(production["receipt"]["ref"], {"id": "material", "revision": 1})
        self.assertTrue((self.root / production["receipt"]["path"]).is_file())
        self.run_intent("AG0", {"action": "assign_review", "task": "review", "from_task": "material-task"})
        self.run_intent("AG3", {"action": "begin", "task": "review"})
        running = self.api.desk(self.w.sessions["AG3"])["tasks"][0]
        self.assertEqual(running["status"], "running")
        self.assertIsNone(running["receipt"])
        self.run_intent("AG3", {"action": "opinion", "task": "review", "outcome": "supported", "rationale": "Fabricated professional review."})
        submitted = self.api.desk(self.w.sessions["AG3"])["tasks"][0]
        self.assertEqual(submitted["status"], "submitted")
        self.assertEqual(submitted["receipt"]["kind"], "review_submission")
        self.assertEqual(submitted["receipt"]["target_ref"], production["receipt"]["ref"])

    def test_candidate_input_requires_explicit_provisional_conditions_at_start(self):
        candidate = self.w.candidate("material")["ref"]
        inputs = [{"artifact": "material", "revision": candidate["revision"], "scope": ["whole"], "use": "teaching"}]
        self.run_intent("AG0", self.assignment("dependent", "activity", kind="ActivitySpec", inputs=inputs))
        self.refuses_prepare("AG1", {"action": "begin", "task": "dependent"}, {"explicit_provisional_conditions_required"})
        inputs[0]["provisional_conditions"] = "Fabricated temporary comparison only; not final learning use."
        self.run_intent("AG0", self.assignment("provisional", "provisional-activity", kind="ActivitySpec", inputs=inputs))
        self.run_intent("AG1", {"action": "begin", "task": "provisional"})
        self.assertEqual(self.c.read_snapshot(self.w.sessions["AG1"], "provisional")[0]["ref"], candidate)
        row = self.api.desk(self.w.sessions["AG1"], task_id="provisional")["tasks"][0]
        self.assertEqual(row["provisional_inputs"][0]["conditions"], inputs[0]["provisional_conditions"])

    def test_failed_work_is_blocked_with_reason_and_no_artifact_receipt(self):
        self.run_intent("AG0", self.assignment())
        self.run_intent("AG2", {"action": "begin", "task": "material-task"})
        self.run_intent("AG2", {"action": "stop", "task": "material-task", "outcome": "failed", "reason": "Fabricated unavailable source."})
        row = self.api.desk(self.w.sessions["AG0"])["tasks"][0]
        self.assertEqual(row["status"], "blocked")
        self.assertIn("Fabricated unavailable source", row["reason"])
        self.assertIsNone(row["receipt"])

    def test_cli_do_submits_concrete_intents_and_saved_returns_the_original_receipt(self):
        assigned = self.cli("AG0", "do", intent=self.assignment())
        self.assertEqual(assigned["status"], "committed")
        registered = self.persisted()
        assigned_again = self.cli("AG0", "do", intent=self.assignment())
        self.assertEqual(assigned_again["ticket"], assigned["ticket"])
        self.assertEqual(assigned_again["status"], "committed")
        self.assertEqual(self.persisted(), registered)
        self.cli("AG2", "do", intent={"action": "begin", "task": "material-task"})
        delivery_intent = {"action": "deliver", "task": "material-task", "path": self.artifact_file("material-task")}
        delivered = self.cli("AG2", "do", intent=delivery_intent)
        self.assertEqual(delivered["work_status"], "submitted")
        self.assertEqual(delivered["receipt"]["kind"], "artifact_submission")
        submitted = self.persisted()
        delivered_again = self.cli("AG2", "do", intent=delivery_intent)
        self.assertEqual(delivered_again["ticket"], delivered["ticket"])
        self.assertEqual(delivered_again["ref"], delivered["ref"])
        self.assertEqual(self.persisted(), submitted)
        saved = self.cli("AG2", "saved", "--ticket", delivered["ticket"])
        self.assertEqual(saved["status"], "committed")
        self.assertEqual(saved["result"]["ref"], delivered["ref"])
        saved_by_intent = self.cli("AG2", "saved", intent=delivery_intent)
        self.assertEqual(saved_by_intent["ticket"], delivered["ticket"])
        self.assertEqual(saved_by_intent["result"]["ref"], delivered["ref"])
        self.cli("AG2", "do", intent={"action": "opinion", "task": "material-task", "outcome": "supported", "rationale": "Fabricated explicit CLI judgment."})
        adopted = self.cli("AG0", "do", intent={"action": "adopt", "tasks": ["material-task"]})
        self.assertEqual(adopted["adopted"][0]["ref"], delivered["ref"])
        desk = self.cli("AG2")
        self.assertEqual(desk["tasks"][0]["status"], "submitted")
        self.assertEqual(desk["tasks"][0]["receipt"]["ref"], delivered["ref"])
        self.assertFalse("state_revision" in desk)

    def test_cli_inputs_reads_the_frozen_body_after_new_upstream_adoption(self):
        old, _, _ = self.seed()
        self.cli("AG0", "do", intent=self.assignment("dependent", "activity", kind="ActivitySpec",
                 inputs=[{"artifact": "material", "scope": ["whole"], "use": "teaching"}]))
        self.cli("AG1", "do", intent={"action": "begin", "task": "dependent"})
        before = self.cli("AG1", "inputs", "--task", "dependent")
        self.assertEqual(before["inputs"][0]["ref"], old)
        newer = self.w.candidate("material")["ref"]
        self.w.adopt(newer, [self.w.confirm(newer)])
        after = self.cli("AG1", "inputs", "--task", "dependent")
        self.assertEqual(before, after)
        self.assertIn("Fabricated demonstration artifact", after["inputs"][0]["text"])
        self.assertEqual(after["inputs"][0]["sha256"], before["inputs"][0]["sha256"])
        self.assertTrue(after["inputs"][0]["coverage"]["complete"])


if __name__ == "__main__":
    unittest.main()
