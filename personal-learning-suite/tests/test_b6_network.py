"""Independent B6 behavior checks on temporary, explicitly fictional records.

The managed host capability is the caller identity. Supplied role labels, findings
and fixture grants do not authenticate arbitrary processes or real learners.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from runtime.learning_materials import ref
from runtime.contract_rules import object_refs, walk
from runtime.learning_store import LearningStore
from runtime.personal_learning import PersonalLearningEntry
from test_b4_planning import request as planning_request, decision
from test_b5_entry import fixture, flow_request, CHECKPOINT, EVENT_ID
from test_b5_entry import teach

VERSION = "pl-network/0.1.0"
ACTIVITY = {"id": "FIX-activity", "revision": 1}
BASIS = [{"id": "FIX-goal", "revision": 1}, {"id": "FIX-material", "revision": 1},
         {"id": "FIX-budget", "revision": 1}]


def packet(state_revision=None, operation_id=None, **fields):
    result = {"network_version": VERSION, "synthetic_only": True, **copy.deepcopy(fields)}
    if state_revision is not None:
        result["expected_state_revision"] = state_revision
    if operation_id is not None:
        result["operation_id"] = operation_id
    return result


def material_order(objects, context, identifier="FIX-b6-material-order"):
    """One explicit review with one budget reference, without other records."""
    professional = {"synthetic_only": True, "material": copy.deepcopy(objects["FIX-material"]), "context": copy.deepcopy(context)}
    references = [ref(objects["FIX-material"]), {"id": "FIX-goal", "revision": 1}, ACTIVITY] + list(object_refs(professional))
    references = list({(r["id"], r["revision"], r.get("locator", "")): r for r in references}.values())
    return {"order_id": identifier, "assignee": "AG2", "decision_needed": "核查虚构材料用途资格",
        "decision_type": "material_review", "scope": ["FIX-material"],
        "operation": "materials.inspect",
        "professional_request": professional, "context_refs": references,
        "authorization_refs": [{"id": "FIX-b2b-material-grant", "revision": 1}],
        "shared_budget_ref": {"id": "FIX-budget", "revision": 1},
        "material_refs": [{"id": "FIX-material", "revision": 1}],
        "goal_and_criteria_refs": [{"id": "FIX-goal", "revision": 1}],
        "stop_condition": "当前材料资格够用即返回", "next_trigger": "人工重新声明用途或来源变化", "return_owner": "AG0"}


def role_review_orders(objects, context, judgment, assessment_context):
    """Four declared professional reads, with distinct roles and one shared budget."""
    planning = planning_request(action="accept", decisions=[decision(status="pending")], checkpoint_ref=None)
    planning.pop("expected_state_revision")
    definitions = [
        ("AG1", "planning", "planning.inspect", planning, "FIX-user-grant", ["FIX-need"]),
        ("AG2", "material_review", "materials.inspect", {"synthetic_only": True,
            "material": copy.deepcopy(objects["FIX-material"]), "context": copy.deepcopy(context)},
            "FIX-b2b-material-grant", ["FIX-material"]),
        ("AG3", "professional_review", "assessment.inspect", {"synthetic_only": True,
            "judgment": copy.deepcopy(judgment), "context": copy.deepcopy(assessment_context)},
            "FIX-evidence-grant", ["FIX-event"]),
        ("AG0", "teaching_execution", "teaching.run", teach("open", context),
            "FIX-b3b-teaching-grant", ["FIX-activity"]),
    ]
    orders = []
    for role, decision_type, operation, professional, grant, scope in definitions:
        definitions_in_packet = {(o.get("id"), o.get("revision")) for o in walk(professional)
            if isinstance(o, dict) and "type" in o}
        refs = [r for r in object_refs(professional) if (r["id"], r["revision"]) not in definitions_in_packet]
        refs += [ref(objects[identifier]) for identifier in scope]
        refs = list({(r["id"], r["revision"], r.get("locator", "")): r for r in refs}.values())
        orders.append({"order_id": "FIX-b6-review-" + role, "assignee": role,
            "decision_needed": "按本角色既有专业服务核查虚构声明", "decision_type": decision_type,
            "scope": scope, "operation": operation, "professional_request": professional,
            "context_refs": refs, "authorization_refs": [{"id": grant, "revision": 1}],
            "shared_budget_ref": {"id": "FIX-budget", "revision": 1},
            "goal_and_criteria_refs": [{"id": "FIX-goal", "revision": 1}],
            "event_refs": [ref(objects["FIX-event"])] if role == "AG3" else [],
            "material_refs": [ref(objects["FIX-material"])] if role == "AG2" else [],
            "stop_condition": "当前合法依据够用即返回；不追加测验", "return_owner": "AG0",
            "next_trigger": "依据、授权、控制或用途发生实质变化"})
    return orders


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pl-b6-network-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "workspace"
        self.snapshot, self.artifacts, self.material_context, self.judgment, self.assessment_context = fixture()
        self.store = LearningStore(self.workspace, entry_actor="AG0")
        self.assertEqual(self.store.init_workspace()["status"], "committed")
        self.assertEqual(self.store.import_fixture(self.snapshot, self.artifacts)["status"], "committed")

    def state(self):
        return self.store.read_context()

    def objects(self):
        return {o["id"]: o for o in self.state()["objects"]}

    def revision(self):
        return self.state()["state_revision"]

    def record(self, identifier):
        return self.objects()[identifier]


class B6ExecutionStoreTests(FixtureCase):
    def claim(self, operation="FIX-b6-claim", executor="fixture-host-A", epoch=None, revision=None):
        return self.store.set_execution(self.revision() if revision is None else revision,
            operation, ACTIVITY, executor, copy.deepcopy(BASIS), expected_epoch=epoch)

    def test_execution_claim_cas_and_identical_retry_do_not_increase_epoch(self):
        revision = self.revision()
        result = self.claim(revision=revision)
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(result["execution"]["execution_epoch"], 2)
        before = self.state()
        repeated = self.claim(revision=revision)
        self.assertEqual(repeated["status"], "committed", repeated)
        self.assertEqual(self.state(), before)
        self.assertEqual(repeated["execution"], result["execution"])
        stale = self.claim(operation="FIX-b6-stale", epoch=2, revision=revision)
        self.assertEqual(stale["status"], "conflict", stale)
        self.assertEqual(self.state(), before)

    def test_takeover_revokes_old_executor_epoch_and_old_claim_receipt(self):
        original_revision = self.revision()
        first = self.claim(revision=original_revision)
        self.assertEqual(first["status"], "committed", first)
        current = self.claim("FIX-b6-takeover", "fixture-host-B", epoch=2)
        self.assertEqual(current["status"], "committed", current)
        self.assertEqual(current["execution"]["execution_epoch"], 3)
        self.assertEqual(self.store.check_execution(ACTIVITY, "fixture-host-A", 2, BASIS)["status"], "rejected")
        self.assertEqual(self.store.check_execution(ACTIVITY, "fixture-host-B", 3, BASIS)["status"], "ok")
        before = self.state()
        replay = self.claim(revision=original_revision)
        self.assertEqual(replay["status"], "rejected", replay)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.store.check_execution(ACTIVITY, "fixture-host-B", 3, BASIS)["status"], "ok")

    def test_controls_are_checked_before_successful_execution_receipt(self):
        revision = self.revision()
        self.assertEqual(self.claim(revision=revision)["status"], "committed")
        self.assertEqual(self.store.pause(self.revision(), "FIX-b6-pause-before-retry", ["FIX-activity"], "人工暂停")["status"], "committed")
        before = self.state()
        result = self.claim(revision=revision)
        self.assertEqual(result["status"], "rejected", result)
        self.assertEqual(self.store.check_execution(ACTIVITY, "fixture-host-A", 2, BASIS)["status"], "rejected")
        self.assertEqual(self.state(), before)

    def test_execution_failure_rolls_back_control_record_epoch_and_receipt(self):
        before = self.state()
        for failpoint in ("after_write", "before_publish"):
            with self.subTest(failpoint=failpoint):
                def fail(stage):
                    if stage == failpoint:
                        raise RuntimeError("synthetic failure")
                self.store.failpoint = fail
                result = self.claim("FIX-b6-failed-" + failpoint)
                self.assertEqual(result["status"], "not_saved", result)
                self.assertEqual(self.state(), before)
                self.store.failpoint = None
                retry = self.claim("FIX-b6-failed-" + failpoint)
                self.assertEqual(retry["status"], "committed", retry)
                self.assertEqual(retry["execution"]["execution_epoch"], 2)
                # Return to a fresh fixture for the second transaction failpoint.
                if failpoint == "after_write":
                    next_workspace = Path(self.temp.name) / "failure-before-publish"
                    self.store = LearningStore(next_workspace, entry_actor="AG0")
                    self.assertEqual(self.store.init_workspace()["status"], "committed")
                    self.assertEqual(self.store.import_fixture(self.snapshot, self.artifacts)["status"], "committed")
                    before = self.state()

    def test_non_entry_actor_and_stale_or_deleted_basis_cannot_claim(self):
        before = self.state()
        forbidden = LearningStore(self.workspace, entry_actor="AG3").set_execution(self.revision(),
            "FIX-b6-non-entry-claim", ACTIVITY, "AG0", BASIS)
        self.assertEqual(forbidden["status"], "rejected", forbidden)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.claim()["status"], "committed")
        self.assertEqual(self.store.delete_scope(self.revision(), "FIX-b6-delete-activity", ["FIX-activity"])["status"], "committed")
        before = self.state()
        self.assertEqual(self.claim("FIX-b6-deleted-claim", epoch=2)["status"], "rejected")
        self.assertEqual(self.state(), before)
        self.assertNotIn("FIX-activity", self.objects())
        self.assertEqual(self.store.check_execution(ACTIVITY, "fixture-host-A", 2, BASIS)["status"], "rejected")

    def test_upstream_source_revision_change_invalidates_execution_even_if_caller_omits_it(self):
        self.assertEqual(self.claim()["status"], "committed")
        source = copy.deepcopy(self.record("FIX-content-source"))
        source.update(revision=2, decision_type="material_review")
        grant = {"id": "FIX-b2b-material-grant", "revision": 1}
        receipt = LearningStore(self.workspace, entry_actor="AG2").commit(self.revision(),
            "FIX-b6-update-intrinsic-source", [source], authorization_refs=[grant], adoption_refs=[grant])
        self.assertEqual(receipt["status"], "committed", receipt)
        before = self.state()
        gate = self.store.check_execution(ACTIVITY, "fixture-host-A", 2, [])
        self.assertEqual(gate["status"], "rejected", gate)
        self.assertEqual(self.state(), before)


class B6NetworkTests(FixtureCase):
    def setUp(self):
        super().setUp()
        from runtime.network_b6 import NetworkHost
        self.host_type = NetworkHost
        self.host = NetworkHost(self.store)
        self.addCleanup(self.host.close)
        self.roles = {role: self.host.bind(role) for role in ("AG0", "AG1", "AG2", "AG3")}
        self.sequence = 0

    def mutation(self, prefix, **fields):
        self.sequence += 1
        return packet(self.revision(), "FIX-b6-" + prefix + "-" + str(self.sequence), **fields)

    def dispatch(self, identifier="FIX-b6-material-order", **overrides):
        fields = material_order(self.objects(), self.material_context, identifier)
        fields.update(copy.deepcopy(overrides))
        result = self.host.dispatch(self.roles["AG0"], self.mutation("dispatch", **fields))
        self.assertEqual(result["status"], "committed", result)
        return result["order_ref"]

    def accepted(self, order_ref, role="AG2", status="accepted", handled=None, unhandled=None):
        result = self.host.accept(self.roles[role], self.mutation("accept", order_ref=order_ref,
            status=status, handled_scope=handled if handled is not None else ["FIX-material"],
            unhandled_scope=unhandled or [], limitations=[]))
        self.assertEqual(result["status"], "committed", result)
        return result["order_ref"]

    def candidate(self, order_ref=None):
        order_ref = order_ref or self.accepted(self.dispatch())
        result = self.host.run(self.roles["AG2"], self.mutation("run", order_ref=order_ref,
            result_id="FIX-b6-material-result"))
        self.assertEqual(result["status"], "committed", result)
        return result

    def adoption(self, result_ref, role="AG2", **overrides):
        fields = {"result_ref": result_ref, "status": "adopted", "basis_refs": [
            {"id": "FIX-material", "revision": 1}, {"id": "FIX-goal", "revision": 1}],
            "handled_scope": ["FIX-material"], "unhandled_scope": [], "limitations": [],
            "next_trigger": "人工来源或用途声明变化后重新核查"}
        fields.update(overrides)
        return self.host.adopt(self.roles[role], self.mutation("adopt", **fields))

    def claim(self, capability=None):
        current = [o for o in self.objects().values() if o["type"] == "ControlState"
            and o["id"].startswith("FIX-network-execution-") and o["execution"]["activity_ref"] == ACTIVITY]
        fields = {"activity_ref": ACTIVITY, "basis_refs": BASIS}
        if current:
            fields["expected_epoch"] = max(o["execution"]["execution_epoch"] for o in current)
        result = self.host.takeover(capability or self.roles["AG0"], self.mutation("takeover", **fields))
        self.assertEqual(result["status"], "committed", result)
        return result

    def display_request(self, claim):
        return packet(activity_ref=ACTIVITY, execution_epoch=claim["execution"]["execution_epoch"],
            basis_refs=BASIS, professional_request=teach("open", self.material_context))

    def test_opaque_identity_ignores_claimed_roles_and_cross_host_or_closed_capabilities(self):
        before = self.state()
        for forged in ("AG2", {"role": "AG2"}, object(), copy.copy(self.roles["AG2"])):
            with self.subTest(forged_type=type(forged).__name__):
                self.assertEqual(self.host.role_info(forged)["status"], "rejected")
        fields = material_order(self.objects(), self.material_context)
        fields["actor"] = "AG2"
        spoof = self.host.dispatch(self.roles["AG0"], self.mutation("spoof", **fields))
        self.assertEqual(spoof["status"], "rejected", spoof)
        other_workspace = Path(self.temp.name) / "other-host"
        other_store = LearningStore(other_workspace)
        self.assertEqual(other_store.init_workspace()["status"], "committed")
        other = self.host_type(other_store)
        self.addCleanup(other.close)
        self.assertEqual(other.role_info(self.roles["AG2"])["status"], "rejected")
        self.host.close()
        self.assertEqual(self.host.role_info(self.roles["AG0"])["status"], "rejected")
        self.assertEqual(self.state(), before)

    def test_received_is_read_only_and_unaccepted_work_stays_sender_responsibility(self):
        order_ref = self.dispatch()
        before = self.state()
        receipt = self.host.accept(self.roles["AG2"], packet(order_ref=order_ref, status="received",
            handled_scope=[], unhandled_scope=[], limitations=[]))
        self.assertIn(receipt["status"], {"received", "ok"}, receipt)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.record(order_ref["id"])["acceptance"]["status"], "proposed")
        pending = self.host.pending(self.roles["AG0"])
        own = next(x for x in pending["pending"] if x["order_ref"]["id"] == order_ref["id"])
        self.assertEqual(own["responsible_owner"], "AG0")
        declined = self.accepted(order_ref, status="rejected", handled=[], unhandled=["FIX-material"])
        self.assertEqual(self.record(declined["id"])["acceptance"]["status"], "declined")
        own = next(x for x in self.host.pending(self.roles["AG0"])["pending"] if x["order_ref"]["id"] == order_ref["id"])
        self.assertEqual(own["responsible_owner"], "AG0")
        self.assertEqual(self.record("FIX-need")["disposition"]["status"], "pending")

    def test_partial_acceptance_keeps_unhandled_scope_and_does_not_schedule(self):
        order_ref = self.dispatch(scope=["FIX-material", "FIX-goal"])
        accepted = self.accepted(order_ref, status="partially_accepted", handled=["FIX-material"], unhandled=["FIX-goal"])
        record = self.record(accepted["id"])
        self.assertEqual(record["acceptance"]["status"], "partially_accepted")
        serialized = json.dumps(self.host.pending(self.roles["AG0"]), ensure_ascii=False)
        self.assertIn("FIX-goal", serialized)
        pending = next(o for o in self.host.pending(self.roles["AG0"])["pending"] if o["order_ref"]["id"] == order_ref["id"])
        self.assertEqual(pending["responsible_owner"], "AG2")
        self.assertEqual(pending["unhandled_owner"], "AG0")
        self.assertEqual(self.record("FIX-need")["disposition"]["status"], "pending")
        self.assertFalse(any(o["type"] == "PlanCommitment" and o.get("status") == "active" for o in self.objects().values()))

    def test_candidate_result_and_professional_adoption_are_distinct_and_cannot_be_forged(self):
        candidate = self.candidate()
        result_ref = candidate["result_ref"]
        saved = self.record(result_ref["id"])
        self.assertEqual(saved["type"], "WorkResult")
        self.assertEqual(saved["adoption"]["status"], "candidate")
        before = self.state()
        denied = self.adoption(result_ref, role="AG0")
        self.assertEqual(denied["status"], "rejected", denied)
        self.assertEqual(self.state(), before)
        adopted = self.adoption(result_ref)
        self.assertEqual(adopted["status"], "committed", adopted)
        self.assertEqual(self.record(result_ref["id"])["adoption"]["status"], "adopted")
        self.assertEqual(self.record("FIX-need")["disposition"]["status"], "pending")
        self.assertEqual(self.record("FIX-budget"), next(o for o in self.snapshot["objects"] if o["id"] == "FIX-budget"))

    def test_pending_keeps_new_candidate_after_another_result_is_adopted_in_either_id_order(self):
        for index, (adopted_id, candidate_id) in enumerate((
            ("FIX-z-adopted-result", "FIX-a-new-candidate-result"),
            ("FIX-a-adopted-result", "FIX-z-new-candidate-result"),
        )):
            with self.subTest(adopted_id=adopted_id, candidate_id=candidate_id):
                order = self.accepted(self.dispatch(identifier="FIX-multi-result-order-" + str(index)))
                first = self.host.run(self.roles["AG2"], self.mutation("old-result",
                    order_ref=order, result_id=adopted_id))
                self.assertEqual(first["status"], "committed", first)
                adopted = self.adoption(first["result_ref"])
                self.assertEqual(adopted["status"], "committed", adopted)
                second = self.host.run(self.roles["AG2"], self.mutation("new-result",
                    order_ref=order, result_id=candidate_id))
                self.assertEqual(second["status"], "committed", second)
                before = self.state()
                result = self.host.pending(self.roles["AG0"])
                self.assertEqual(result["status"], "ok", result)
                own = [item for item in result["pending"] if item["order_ref"] == order]
                self.assertEqual([item["result_ref"] for item in own], [second["result_ref"]])
                self.assertEqual(own[0]["adoption"], "candidate")
                self.assertEqual(own[0]["responsible_owner"], "AG2")
                self.assertFalse(own[0]["blocked"])
                self.assertEqual(self.state(), before)
                final_adoption = self.adoption(second["result_ref"])
                self.assertEqual(final_adoption["status"], "committed", final_adoption)
                self.assertFalse(any(item["order_ref"] == order for item in self.host.pending(self.roles["AG0"])["pending"]))

    def test_pending_preserves_both_candidates_and_idempotent_run_adds_no_duplicate(self):
        order = self.accepted(self.dispatch())
        first_request = self.mutation("first-candidate", order_ref=order, result_id="FIX-z-candidate")
        first = self.host.run(self.roles["AG2"], first_request)
        self.assertEqual(first["status"], "committed", first)
        second = self.host.run(self.roles["AG2"], self.mutation("second-candidate",
            order_ref=order, result_id="FIX-a-candidate"))
        self.assertEqual(second["status"], "committed", second)
        before = self.state()
        replay = self.host.run(self.roles["AG2"], first_request)
        self.assertEqual(replay["status"], "committed", replay)
        self.assertEqual(replay["result_ref"], first["result_ref"])
        self.assertFalse(replay["mutated"])
        for role in ("AG0", "AG2"):
            result = self.host.pending(self.roles[role])
            self.assertEqual(result["status"], "ok", result)
            own = [item for item in result["pending"] if item["order_ref"] == order]
            self.assertCountEqual([item["result_ref"] for item in own], [first["result_ref"], second["result_ref"]])
            self.assertTrue(all(item["adoption"] == "candidate" and not item["blocked"] for item in own))
        self.assertFalse(any(item["order_ref"] == order for item in self.host.pending(self.roles["AG1"])["pending"]))
        self.assertEqual(self.state(), before)

    def test_pending_preserves_partial_recheck_and_rejected_followup_beside_new_candidate(self):
        order = self.accepted(self.dispatch(scope=["FIX-material", "FIX-goal"]),
            status="partially_accepted", handled=["FIX-material"], unhandled=["FIX-goal"])
        expected = []
        for identifier, status in (("FIX-z-partial", "partially_adopted"),
                                   ("FIX-m-recheck", "recheck"), ("FIX-b-rejected", "rejected")):
            result = self.host.run(self.roles["AG2"], self.mutation(identifier,
                order_ref=order, result_id=identifier))
            self.assertEqual(result["status"], "committed", result)
            adopted = self.adoption(result["result_ref"], status=status,
                handled_scope=["FIX-material"], unhandled_scope=["FIX-goal"],
                next_trigger="核对本结果的未处理范围：" + status)
            self.assertEqual(adopted["status"], "committed", adopted)
            expected.append((adopted["result_ref"], status))
        candidate = self.host.run(self.roles["AG2"], self.mutation("new-partial-candidate",
            order_ref=order, result_id="FIX-a-partial-candidate"))
        self.assertEqual(candidate["status"], "committed", candidate)
        expected.append((candidate["result_ref"], "candidate"))
        before = self.state()
        pending = self.host.pending(self.roles["AG0"])
        own = [item for item in pending["pending"] if item["order_ref"] == order]
        self.assertEqual(len(own), len(expected))
        for result_ref, status in expected:
            item = next(item for item in own if item["result_ref"] == result_ref)
            self.assertEqual(item["adoption"], status)
            self.assertEqual(item["unhandled_scope"], ["FIX-goal"])
            self.assertEqual(item["unhandled_owner"], "AG0")
            self.assertFalse(item["blocked"])
        self.assertEqual(self.state(), before)

    def test_pending_checks_each_result_control_without_hiding_an_unrestricted_candidate(self):
        order = self.accepted(self.dispatch())
        first = self.host.run(self.roles["AG2"], self.mutation("restricted-result",
            order_ref=order, result_id="FIX-z-restricted-result"))
        self.assertEqual(first["status"], "committed", first)
        adopted = self.adoption(first["result_ref"])
        self.assertEqual(adopted["status"], "committed", adopted)
        second = self.host.run(self.roles["AG2"], self.mutation("unrestricted-result",
            order_ref=order, result_id="FIX-a-unrestricted-result"))
        self.assertEqual(second["status"], "committed", second)
        restricted = self.host.control(self.roles["AG0"], self.mutation("restrict-result",
            action="restrict", scope_ids=[first["result_ref"]["id"]],
            reason="人工核验本返回待查", intended_uses=["material_review"]))
        self.assertEqual(restricted["status"], "committed", restricted)
        before = self.state()
        result = self.host.pending(self.roles["AG0"])
        self.assertEqual(result["status"], "ok", result)
        own = [item for item in result["pending"] if item["order_ref"] == order]
        self.assertEqual(len(own), 2)
        available = next(item for item in own if item["result_ref"] == second["result_ref"])
        self.assertEqual(available["adoption"], "candidate")
        self.assertFalse(available["blocked"])
        unavailable = next(item for item in own if item["blocked"])
        self.assertIsNone(unavailable["result_ref"])
        self.assertEqual(unavailable["adoption"], "recheck")
        self.assertEqual(self.state(), before)

    def test_pending_rechecks_old_order_result_and_keeps_new_revision_candidate(self):
        order = self.accepted(self.dispatch())
        first = self.host.run(self.roles["AG2"], self.mutation("old-order-result",
            order_ref=order, result_id="FIX-z-old-order-result"))
        self.assertEqual(first["status"], "committed", first)
        self.assertEqual(self.adoption(first["result_ref"])["status"], "committed")
        updated_order = copy.deepcopy(self.record(order["id"]))
        updated_order["revision"] += 1
        updated_order["next_trigger"] = "人工调整本工作单触发，旧返回需重核"
        # The public shared store may change while a host is open; its returned
        # results must still use current order revisions on the next read.
        saved = LearningStore(self.workspace, entry_actor="AG2").commit(self.revision(),
            "FIX-b6-order-new-trigger", [updated_order])
        self.assertEqual(saved["status"], "committed", saved)
        current_order = ref(updated_order)
        second = self.host.run(self.roles["AG2"], self.mutation("new-order-result",
            order_ref=current_order, result_id="FIX-a-new-order-result"))
        self.assertEqual(second["status"], "committed", second)
        before = self.state()
        result = self.host.pending(self.roles["AG0"])
        own = [item for item in result["pending"] if item["order_ref"] == current_order]
        self.assertEqual(len(own), 2)
        candidate = next(item for item in own if item["result_ref"] == second["result_ref"])
        self.assertEqual(candidate["adoption"], "candidate")
        self.assertFalse(candidate["blocked"])
        stale = next(item for item in own if item["blocked"])
        self.assertIsNone(stale["result_ref"])
        self.assertEqual(stale["adoption"], "recheck")
        self.assertEqual(stale["next_trigger"], updated_order["next_trigger"])
        self.assertEqual(self.state(), before)

    def test_pending_rechecks_adopted_result_when_its_separate_professional_output_is_paused(self):
        material = copy.deepcopy(self.record("FIX-material"))
        material.update(id="FIX-new-output-material", revision=1, decision_type="material_review")
        grant = {"id": "FIX-b2b-material-grant", "revision": 1}
        professional = {"synthetic_only": True, "operation_id": "FIX-professional-new-output",
            "changes": [material], "context": copy.deepcopy(self.material_context),
            "authorization_refs": [grant], "adoption_refs": [grant]}
        order = self.accepted(self.dispatch(identifier="FIX-new-output-order", operation="materials.submit",
            professional_request=professional, scope=[material["id"]], operation_scope=[material["id"]]),
            handled=[material["id"]])
        returned = self.host.run(self.roles["AG2"], self.mutation("run-new-output",
            order_ref=order, result_id="FIX-new-output-result"))
        self.assertEqual(returned["status"], "committed", returned)
        self.assertEqual(returned["professional_status"], "committed")
        adopted = self.adoption(returned["result_ref"], handled_scope=[material["id"]])
        self.assertEqual(adopted["status"], "committed", adopted)
        unrelated = self.candidate()
        stopped = self.host.control(self.roles["AG0"], self.mutation("pause-new-output",
            action="pause", scope_ids=[material["id"]], reason="暂停该新专业产物"))
        self.assertEqual(stopped["status"], "committed", stopped)
        before = self.state()
        result = self.host.pending(self.roles["AG0"])
        own = [item for item in result["pending"] if item["order_ref"] == order]
        self.assertEqual(len(own), 1)
        self.assertTrue(own[0]["blocked"])
        self.assertIsNone(own[0]["result_ref"])
        self.assertEqual(own[0]["adoption"], "recheck")
        other = next(item for item in result["pending"] if item["result_ref"] == unrelated["result_ref"])
        self.assertEqual(other["adoption"], "candidate")
        self.assertFalse(other["blocked"])
        self.assertEqual(self.state(), before)

    def test_run_wrong_role_or_relabelled_professional_operation_has_no_authority(self):
        order_ref = self.accepted(self.dispatch())
        before = self.state()
        denied = self.host.run(self.roles["AG3"], self.mutation("wrong-role", order_ref=order_ref, result_id="FIX-b6-forged-result"))
        self.assertEqual(denied["status"], "rejected", denied)
        self.assertEqual(self.state(), before)
        fields = material_order(self.objects(), self.material_context, "FIX-b6-forged-order")
        fields.update(assignee="AG3", decision_type="professional_review")
        fields["authorization_refs"] = [{"id": "FIX-evidence-grant", "revision": 1}]
        denied = self.host.dispatch(self.roles["AG0"], self.mutation("relabel", **fields))
        self.assertEqual(denied["status"], "rejected", denied)
        self.assertEqual(self.state(), before)

    def test_minimal_context_and_candidate_return_do_not_expose_unrelated_records_or_teacher_reference(self):
        order_ref = self.accepted(self.dispatch())
        context = self.host.context(self.roles["AG2"], order_ref)
        self.assertEqual(context["status"], "ok", context)
        selected = {o["id"] for o in context["objects"]}
        self.assertNotIn("FIX-need", selected)
        self.assertNotIn("FIX-b3c-work", selected)
        self.assertNotIn("FIX-work-order", selected)
        candidate = self.candidate(order_ref)
        text = json.dumps(candidate, ensure_ascii=False)
        self.assertNotIn("按假言推理得到 Q", text)
        self.assertNotIn("OUTSIDE-BEFORE-MARKER", text)
        self.assertNotIn("B3B-TEACHER-SECRET", text)
        self.assertNotIn("B3B-BACKUP-SECRET", text)
        self.assertNotIn("professional_request", text)
        self.assertNotIn("learner_packet", candidate)

    def test_shared_budget_is_referenced_once_without_creation_of_new_envelopes(self):
        before = [o for o in self.objects().values() if o["type"] == "BudgetEnvelope"]
        first = self.dispatch()
        second = self.dispatch("FIX-b6-second-material-order")
        self.assertEqual(self.record(first["id"])["shared_budget_ref"], self.record(second["id"])["shared_budget_ref"])
        self.assertEqual([o for o in self.objects().values() if o["type"] == "BudgetEnvelope"], before)

    def test_same_operation_retry_cas_and_failed_candidate_are_transactional(self):
        fields = material_order(self.objects(), self.material_context)
        request = self.mutation("fixed-retry", **fields)
        first = self.host.dispatch(self.roles["AG0"], request)
        self.assertEqual(first["status"], "committed", first)
        before = self.state()
        replay = self.host.dispatch(self.roles["AG0"], request)
        self.assertEqual(replay["status"], "committed", replay)
        self.assertEqual(self.state(), before)
        stale_request = copy.deepcopy(request)
        stale_request.update(operation_id="FIX-b6-new-stale-op", order_id="FIX-b6-new-stale-order")
        stale = self.host.dispatch(self.roles["AG0"], stale_request)
        self.assertEqual(stale["status"], "conflict", stale)
        self.assertEqual(self.state(), before)
        accepted = self.accepted(first["order_ref"])
        request = self.mutation("run-fail", order_ref=accepted, result_id="FIX-b6-atomic-result")
        before = self.state()
        def fail(stage):
            if stage == "before_publish":
                raise RuntimeError("fictional failure")
        with patch.object(LearningStore, "_tick", side_effect=fail):
            result = self.host.run(self.roles["AG2"], request)
        self.assertEqual(result["status"], "not_saved", result)
        self.assertEqual(self.state(), before)
        self.assertNotIn("FIX-b6-atomic-result", self.objects())
        self.assertEqual(self.host.run(self.roles["AG2"], request)["status"], "committed")

    def test_delete_rejects_cached_dispatch_run_and_result_adoption_without_reviving_payload(self):
        fields = material_order(self.objects(), self.material_context)
        request = self.mutation("cache-order", **fields)
        dispatched = self.host.dispatch(self.roles["AG0"], request)
        self.assertEqual(dispatched["status"], "committed", dispatched)
        accepted = self.accepted(dispatched["order_ref"])
        candidate = self.candidate(accepted)
        delete = self.host.control(self.roles["AG0"], self.mutation("delete", action="delete", scope_ids=["FIX-material"], reason="删除虚构材料", intended_uses=[]))
        self.assertEqual(delete["status"], "committed", delete)
        before = self.state()
        for replay in (lambda: self.host.dispatch(self.roles["AG0"], request),
                       lambda: self.host.run(self.roles["AG2"], self.mutation("late-run", order_ref=accepted, result_id="FIX-b6-late-result")),
                       lambda: self.adoption(candidate["result_ref"])):
            result = replay()
            self.assertEqual(result["status"], "rejected", result)
            self.assertEqual(self.state(), before)
            self.assertNotIn("按假言推理得到 Q", json.dumps(result, ensure_ascii=False))
        self.assertNotIn("FIX-material", self.objects())
        self.assertNotIn("FIX-b6-late-result", self.objects())
        self.assertEqual(self.store.check_integrity()["status"], "ok")

    def test_takeover_allows_only_current_executor_epoch_to_present_learner_packet(self):
        original = self.claim()
        first_request = self.display_request(original)
        shown = self.host.present(self.roles["AG0"], first_request)
        self.assertEqual(shown["status"], "ready", shown)
        self.assertNotIn("按假言推理得到 Q", json.dumps(shown, ensure_ascii=False))
        self.assertNotIn("B3B-TEACHER-SECRET", json.dumps(shown, ensure_ascii=False))
        self.assertNotIn("B3B-BACKUP-SECRET", json.dumps(shown, ensure_ascii=False))
        replacement = self.host.bind("AG0")
        current = self.claim(replacement)
        self.assertGreater(current["execution"]["execution_epoch"], original["execution"]["execution_epoch"])
        self.assertEqual(self.host.present(self.roles["AG0"], first_request)["status"], "rejected")
        self.assertEqual(self.host.present(replacement, first_request)["status"], "rejected")
        self.assertEqual(self.host.present(replacement, self.display_request(current))["status"], "ready")
        self.assertEqual(self.host.present(self.roles["AG2"], self.display_request(current))["status"], "rejected")

    def test_pause_controls_are_checked_before_cached_context_and_presentation(self):
        order_ref = self.accepted(self.dispatch())
        self.assertEqual(self.host.context(self.roles["AG2"], order_ref)["status"], "ok")
        claim = self.claim()
        self.assertEqual(self.host.present(self.roles["AG0"], self.display_request(claim))["status"], "ready")
        pause = self.host.control(self.roles["AG0"], self.mutation("pause", action="pause", scope_ids=["FIX-material"], reason="暂停虚构材料", intended_uses=[]))
        self.assertEqual(pause["status"], "committed", pause)
        before = self.state()
        self.assertEqual(self.host.context(self.roles["AG2"], order_ref)["status"], "rejected")
        self.assertEqual(self.host.present(self.roles["AG0"], self.display_request(claim))["status"], "rejected")
        self.assertEqual(self.state(), before)

    def test_duplicate_host_is_rejected_in_process_and_subprocess_then_can_reopen(self):
        with self.assertRaisesRegex(RuntimeError, "workspace_host_already_active"):
            self.host_type(self.store)
        script = "import sys;from runtime.network_b6 import NetworkHost;NetworkHost(sys.argv[1])"
        import os
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        command = [sys.executable, "-X", "utf8", "-c", script, str(self.workspace)]
        second = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=environment)
        self.assertNotEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("workspace_host_already_active", second.stderr)
        self.host.close()
        reopened = self.host_type(self.store)
        self.addCleanup(reopened.close)
        self.assertNotEqual(reopened.role_info(reopened.bind("AG0"))["status"], "rejected")

    def test_four_roles_load_actual_agent_and_skill_rules_and_execute_declared_review_services(self):
        for role in self.roles:
            info = self.host.role_info(self.roles[role])
            self.assertEqual(info["status"], "ok", info)
            self.assertEqual(info["role"], role)
            self.assertGreaterEqual(len(info["instructions"]), 2)
            for instruction in info["instructions"]:
                self.assertEqual(instruction["text"], Path(instruction["path"]).read_text(encoding="utf-8-sig"))
        self.claim()
        before_count = len([o for o in self.objects().values() if o["type"] == "PerformanceEvent"])
        for definition in role_review_orders(self.objects(), self.material_context, self.judgment, self.assessment_context):
            with self.subTest(role=definition["assignee"]):
                role = definition["assignee"]
                dispatched = self.host.dispatch(self.roles["AG0"], self.mutation("four-dispatch", **definition))
                self.assertEqual(dispatched["status"], "committed", dispatched)
                accepted = self.accepted(dispatched["order_ref"], role=role, handled=definition["scope"])
                context = self.host.context(self.roles[role], accepted)
                self.assertEqual(context["status"], "ok", context)
                if role == "AG3":
                    self.assertEqual(context["objects"][0]["type"], "PerformanceEvent")
                    self.assertEqual(context["objects"][0]["timeline"], self.record("FIX-event")["timeline"])
                candidate = self.host.run(self.roles[role], self.mutation("four-run", order_ref=accepted,
                    result_id="FIX-b6-four-result-" + role))
                self.assertEqual(candidate["status"], "committed", candidate)
                self.assertNotIn(candidate["professional_status"], {"rejected", "blocked", "not_saved", "conflict", "not_ready"}, candidate)
                self.assertEqual(self.record(candidate["result_ref"]["id"])["adoption"]["status"], "candidate")
                saved = self.record(candidate["result_ref"]["id"])
                adoption_status = "adopted" if saved["metadata"]["network"]["professional_successful"] else "recheck"
                adopted = self.adoption(candidate["result_ref"], role=role, status=adoption_status,
                    basis_refs=definition["context_refs"], handled_scope=saved["handled_scope"], unhandled_scope=saved["unhandled_scope"])
                self.assertEqual(adopted["status"], "committed", adopted)
                if role == "AG3":
                    self.assertEqual(self.record(candidate["result_ref"]["id"])["adoption"]["status"], "recheck")
                    self.assertEqual(self.record(candidate["result_ref"]["id"])["unhandled_scope"], definition["scope"])
        self.assertEqual(len([o for o in self.objects().values() if o["type"] == "PerformanceEvent"]), before_count)
        self.assertEqual(self.record("FIX-need")["disposition"]["status"], "pending")

    def test_ordinary_reliable_short_path_creates_no_network_orders_or_professional_calls(self):
        self.claim()
        before = self.state()
        with patch.object(self.host, "dispatch", side_effect=AssertionError("unnecessary delegation")), \
             patch.object(self.host, "run", side_effect=AssertionError("unnecessary network review")):
            result = self.host.execute(self.roles["AG0"], self.mutation("direct-open", operation="teaching.run",
                professional_request=teach("open", self.material_context)))
        self.assertEqual(result["status"], "ready", result)
        self.assertNotIn("learner_packet", result)
        self.assertNotIn("按假言推理得到 Q", json.dumps(result, ensure_ascii=False))
        self.assertEqual(self.state(), before)

    def test_resume_without_summary_preserves_original_help_and_adds_no_required_check(self):
        self.assertEqual(PersonalLearningEntry(self.store).execute(flow_request(self.revision()))["status"], "completed")
        event_before = copy.deepcopy(self.record(EVENT_ID))
        self.claim()
        before = self.state()
        request = teach("resume", self.material_context, checkpoint_ref=None, event_ref=ref(event_before))
        result = self.host.execute(self.roles["AG0"], self.mutation("resume-without-summary", operation="teaching.run", professional_request=request))
        self.assertIn(result["status"], {"ready", "limited"}, result)
        recovery = result["learner_view"]["recovery"]
        self.assertEqual(recovery["last_trusted_event_ref"], ref(event_before))
        self.assertEqual(recovery["unrecorded_actions"]["status"], "unknown")
        self.assertEqual(self.record(EVENT_ID)["timeline"], event_before["timeline"])
        self.assertEqual(self.state(), before)

    def test_async_and_parallel_requests_are_disabled_in_capabilities_and_behavior(self):
        info = self.host.role_info(self.roles["AG0"])
        self.assertFalse(info["capabilities"]["asynchronous"])
        self.assertFalse(info["capabilities"]["parallel_presentation"])
        before = self.state()
        for field in ("async", "parallel"):
            fields = material_order(self.objects(), self.material_context, "FIX-b6-disabled-" + field)
            fields[field] = True
            result = self.host.dispatch(self.roles["AG0"], self.mutation("disabled", **fields))
            self.assertEqual(result["status"], "rejected", result)
            self.assertFalse(result["background_delegation"])
            self.assertEqual(self.state(), before)

    def test_deleted_typed_record_cannot_hide_personal_excerpt_inside_a_new_request(self):
        deleted = copy.deepcopy(self.record("FIX-need"))
        deleted["needed_work"] = "FIX-b6-DELETED-PRIVATE-EXCERPT"
        removal = self.host.control(self.roles["AG0"], self.mutation("delete-hidden-record",
            action="delete", scope_ids=[deleted["id"]], reason="删除虚构需求", intended_uses=[]))
        self.assertEqual(removal["status"], "committed", removal)
        fresh = self.host.bind("AG0")
        fields = material_order(self.objects(), self.material_context, "FIX-b6-hidden-payload-order")
        fields["professional_request"]["memo"] = deleted
        fields["context_refs"] += list(object_refs(deleted))
        before = self.state()
        result = self.host.dispatch(fresh, self.mutation("hidden-payload", **fields))
        self.assertEqual(result["status"], "rejected", result)
        self.assertEqual(self.state(), before)
        self.assertNotIn(deleted["needed_work"], json.dumps(result, ensure_ascii=False))
        self.assertNotIn("FIX-b6-hidden-payload-order", self.objects())

    def test_scope_partition_and_candidate_adoption_cannot_expand_handled_work(self):
        order = self.dispatch(scope=["FIX-material", "FIX-goal"], operation_scope=["FIX-material"])
        accepted = self.accepted(order, status="partially_accepted", handled=["FIX-material"], unhandled=["FIX-goal"])
        candidate = self.candidate(accepted)
        before = self.state()
        expanded = self.adoption(candidate["result_ref"], handled_scope=["FIX-material", "FIX-goal"], unhandled_scope=[])
        self.assertEqual(expanded["status"], "rejected", expanded)
        self.assertEqual(self.state(), before)
        partial = self.adoption(candidate["result_ref"], status="partially_adopted",
            handled_scope=["FIX-material"], unhandled_scope=["FIX-goal"])
        self.assertEqual(partial["status"], "committed", partial)
        pending = next(o for o in self.host.pending(self.roles["AG0"])["pending"] if o["order_ref"]["id"] == order["id"])
        self.assertEqual(pending["unhandled_scope"], ["FIX-goal"])
        self.assertEqual(pending["responsible_owner"], "AG2")

    def test_successful_run_same_operation_retry_returns_saved_candidate_without_second_review(self):
        accepted = self.accepted(self.dispatch())
        request = self.mutation("retry-professional-run", order_ref=accepted, result_id="FIX-b6-idempotent-result")
        first = self.host.run(self.roles["AG2"], request)
        self.assertEqual(first["status"], "committed", first)
        before = self.state()
        with patch("runtime.network_b6.SingleEntryService._dispatch", side_effect=AssertionError("duplicate professional run")):
            second = self.host.run(self.roles["AG2"], request)
        self.assertEqual(second["status"], "committed", second)
        self.assertEqual(second["result_ref"], first["result_ref"])
        self.assertEqual(self.state(), before)

    def test_demo_first_run_has_four_roles_and_takeover_then_reopens_without_replay_or_text_export(self):
        workspace = Path(self.temp.name) / "demo-workspace"
        report_path = Path(self.temp.name) / "demo-report.json"
        command = [sys.executable, "-X", "utf8", str(ROOT / "scripts/demo_b6.py"),
            "--workspace", str(workspace), "--report", str(report_path)]
        first = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["execution"]["status"], "completed")
        roles = {s["role"] for s in report["execution"]["steps"] if "role" in s}
        self.assertEqual(roles, {"AG0", "AG1", "AG2", "AG3"})
        takeover = report["execution"]["steps"][-1]
        self.assertEqual(takeover["old_executor_presentation"]["status"], "rejected")
        self.assertEqual(takeover["current_executor_presentation"]["status"], "ready")
        serialized = json.dumps(report, ensure_ascii=False) + first.stdout
        for secret in ("B3B-TEACHER-SECRET", "B3B-BACKUP-SECRET", "professional_request", "P→Q；P"):
            self.assertNotIn(secret, serialized)
        store = LearningStore(workspace)
        before = store.read_context()
        second = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        reopened = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertTrue(reopened["existing_workspace"])
        self.assertEqual(reopened["initialization"], [])
        self.assertIsNone(reopened["execution"])
        self.assertTrue(reopened["reopen_read_only"])
        self.assertEqual(store.read_context(), before)

    def test_delete_execution_control_including_indexes_requires_fresh_capability_before_new_claim(self):
        first = self.claim()
        old_request = self.display_request(first)
        self.assertEqual(self.host.present(self.roles["AG0"], old_request)["status"], "ready")
        deleted = self.host.control(self.roles["AG0"], self.mutation("delete-control-index",
            action="delete", scope_ids=[first["control_ref"]["id"]], reason="删除虚构执行控制及其索引",
            intended_uses=[], include_indexes=True))
        self.assertEqual(deleted["status"], "committed", deleted)
        self.assertIn("FIX-activity", self.objects())
        self.assertEqual(self.host.present(self.roles["AG0"], old_request)["status"], "rejected")
        fresh = self.host.bind("AG0")
        new = self.claim(fresh)
        self.assertEqual(self.host.present(self.roles["AG0"], self.display_request(new))["status"], "rejected")
        self.assertEqual(self.host.present(fresh, self.display_request(new))["status"], "ready")

    def test_business_limited_material_result_cannot_be_adopted_as_fully_handled(self):
        fields = material_order(self.objects(), self.material_context)
        fields["professional_request"]["material"]["verification"]["content"]["status"] = "pending"
        dispatched = self.host.dispatch(self.roles["AG0"], self.mutation("limited-dispatch", **fields))
        self.assertEqual(dispatched["status"], "committed", dispatched)
        accepted = self.accepted(dispatched["order_ref"])
        candidate = self.host.run(self.roles["AG2"], self.mutation("limited-run", order_ref=accepted,
            result_id="FIX-b6-limited-result"))
        self.assertEqual(candidate["status"], "committed", candidate)
        self.assertEqual(candidate["professional_status"], "limited", candidate)
        before = self.state()
        adopt = self.adoption(candidate["result_ref"])
        self.assertEqual(adopt["status"], "rejected", adopt)
        self.assertEqual(self.state(), before)

    def test_bounded_material_context_reads_only_declared_reference_segment(self):
        reference = self.record("FIX-material")["teacher_reference"][0]["artifact_ref"]
        reference = {key: reference[key] for key in ("path", "locator", "revision", "origin")}
        order = self.dispatch(context_segments=[{"artifact_ref": reference, "start_line": 3, "end_line": 4}])
        accepted = self.accepted(order)
        context = self.host.context(self.roles["AG2"], accepted)
        self.assertEqual(context["status"], "ok", context)
        self.assertEqual(len(context["segments"]), 1)
        text = context["segments"][0]["text"]
        self.assertIn("核验范围", text)
        self.assertNotIn("OUTSIDE-BEFORE-MARKER", text)
        self.assertNotIn("OUTSIDE-AFTER-MARKER", text)

    def test_context_segment_cannot_read_unrelated_original_from_shared_artifact_path(self):
        original = copy.deepcopy(self.record("FIX-event")["original_response"])
        lines = self.artifacts[original["path"]].splitlines()
        start = next(index for index, line in enumerate(lines, 1) if original["locator"] in line)
        fields = material_order(self.objects(), self.material_context, "FIX-b6-unrelated-segment")
        fields["context_segments"] = [{"artifact_ref": original, "start_line": start, "end_line": start + 2}]
        before = self.state()
        dispatched = self.host.dispatch(self.roles["AG0"], self.mutation("unrelated-original", **fields))
        self.assertEqual(dispatched["status"], "rejected", dispatched)
        self.assertEqual(self.state(), before)

    def test_work_order_scope_cannot_mislabel_another_professional_target(self):
        fields = material_order(self.objects(), self.material_context, "FIX-b6-mislabelled-scope")
        fields.update(scope=["FIX-goal"], operation_scope=["FIX-goal"])
        before = self.state()
        result = self.host.dispatch(self.roles["AG0"], self.mutation("wrong-target", **fields))
        self.assertEqual(result["status"], "rejected", result)
        self.assertEqual(self.state(), before)

    def test_material_context_cannot_expand_declared_reference_line_bounds(self):
        native = self.record("FIX-material")["teacher_reference"][0]["artifact_ref"]
        reference = {key: native[key] for key in ("path", "locator", "revision", "origin")}
        self.assertEqual((native["start_line"], native["end_line"]), (3, 4))
        fields = material_order(self.objects(), self.material_context, "FIX-b6-expanded-segment")
        fields["context_segments"] = [{"artifact_ref": reference, "start_line": 1,
            "end_line": len(self.artifacts[reference["path"]].splitlines())}]
        before = self.state()
        result = self.host.dispatch(self.roles["AG0"], self.mutation("expanded-segment", **fields))
        self.assertEqual(result["status"], "rejected", result)
        self.assertEqual(self.state(), before)
        self.assertNotIn("OUTSIDE-BEFORE-MARKER", json.dumps(result, ensure_ascii=False))

    def test_read_only_material_authorization_cannot_be_relabelled_to_review_operation(self):
        # A fresh isolated bootstrap declares the intentionally narrower grant.
        self.host.close()
        narrow_snapshot = copy.deepcopy(self.snapshot)
        narrow_grant = copy.deepcopy(next(o for o in narrow_snapshot["objects"] if o["id"] == "FIX-b2b-material-grant"))
        narrow_grant.update(id="FIX-b6-read-only-material-grant", decision_types=["material_read"])
        narrow_snapshot["objects"].append(narrow_grant)
        narrowed = LearningStore(Path(self.temp.name) / "read-only-grant-workspace")
        self.assertEqual(narrowed.init_workspace()["status"], "committed")
        self.assertEqual(narrowed.import_fixture(narrow_snapshot, self.artifacts)["status"], "committed")
        host = self.host_type(narrowed)
        self.addCleanup(host.close)
        caller = host.bind("AG0")
        objects = {o["id"]: o for o in narrowed.read_context()["objects"]}
        fields = material_order(objects, self.material_context, "FIX-b6-read-as-review-order")
        fields.update(decision_type="material_read", authorization_refs=[ref(narrow_grant)])
        before = narrowed.read_context()
        result = host.dispatch(caller, packet(before["state_revision"], "FIX-b6-read-as-review", **fields))
        self.assertEqual(result["status"], "rejected", result)
        self.assertEqual(narrowed.read_context(), before)

    def test_failed_delete_cleanup_ends_loaded_capabilities_and_keeps_persisted_stop_gate(self):
        order = self.accepted(self.dispatch())
        self.assertEqual(self.host.context(self.roles["AG2"], order)["status"], "ok")
        def fail(stage):
            if stage == "after_delete_gate":
                raise RuntimeError("fictional cleanup failure after persisted stop gate")
        self.host.store.failpoint = fail
        failed = self.host.control(self.roles["AG0"], self.mutation("failed-delete-cleanup",
            action="delete", scope_ids=["FIX-material"], reason="删除虚构材料", intended_uses=[]))
        self.host.store.failpoint = None
        self.assertEqual(failed["status"], "not_saved", failed)
        self.assertTrue(failed["pending_cleanup"], failed)
        self.assertEqual(self.host.role_info(self.roles["AG0"])["status"], "rejected")
        self.assertEqual(self.host.role_info(self.roles["AG2"])["status"], "rejected")
        self.assertEqual(self.store.validate_refs([{ "id": "FIX-material", "revision": 1}], "read")["status"], "rejected")
        fresh = self.host.bind("AG2")
        self.assertEqual(self.host.context(fresh, order)["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
