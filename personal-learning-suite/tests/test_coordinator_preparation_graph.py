"""Preparation compilation uses fabricated requests and no model processes."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
from coordinator.agent_api import AgentCoordinator, intent_shape
from coordinator.preparation_graph import compile_preparation
from coordinator.runtime_scheduler import RuntimeScheduler
from coordinator.runtime_store import RuntimeStore
from coordinator.workspace import GateError
from test_coordinator_complete import CompleteWorkflow


def request():
    return {"workflow_id": "fabricated-preparation", "authorization_ref": "fabricated-authorization",
            "purpose": "Check whether the fictional user can distinguish the declared fictional cases. Original evidence is intentionally synthetic.",
            "stages": [
                {"id": "research", "role": "AG2", "output": {"id": "fictional-source", "type": "SourceFragment", "validation": "utf8"},
                 "prompt": "Investigate the supplied fictional case and identify its actual limitations.",
                 "scope": ["whole"], "use": "teaching", "inputs": [], "review_required": False},
                {"id": "design", "role": "AG1", "output": {"id": "fictional-design", "type": "ActivitySpec", "validation": "utf8"},
                 "prompt": "Design a bounded check using only the actual fictional source.", "scope": ["whole"], "use": "teaching",
                 "inputs": [{"artifact": "fictional-source", "after_task": "research", "scope": ["whole"], "use": "teaching"}],
                 "after": ["research"], "review_required": True}]}


class CoordinatorPreparationGraphTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tac-preparation-graph-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def compile(self, value=None):
        return compile_preparation(value or request(), thread_id="actual-parent-thread", workspace=self.root)

    @staticmethod
    def nodes(compiled):
        return {node["id"]: node for node in compiled["plan"]["nodes"]}

    def test_deterministic_compile_preserves_request_and_has_no_side_effects(self):
        source = request()
        original = deepcopy(source)
        first = self.compile(source)
        self.assertEqual(first, self.compile(source))
        self.assertEqual(source, original)
        self.assertEqual(list(self.root.iterdir()), [])
        bindings = {b["role"]: b for b in first["bindings"]}
        self.assertEqual(bindings["AG0"]["thread_id"], "actual-parent-thread")
        self.assertEqual(bindings["AG0"]["host_kind"], "desktop")
        for role in ("AG1", "AG2", "AG3"):
            self.assertEqual(bindings[role]["host_kind"], "cli")
            self.assertIsNone(bindings[role]["thread_id"])
        self.assertTrue(all(b["cwd"] == str(self.root.resolve()) for b in first["bindings"]))

    def test_compiled_assignments_and_plan_register_through_existing_gates(self):
        compiled = self.compile()
        workflow = CompleteWorkflow(self.root)
        api = AgentCoordinator(workflow.coordinator)
        ag0 = workflow.sessions["AG0"]
        for assignment in compiled["assignments"]:
            intent_shape(assignment)
            result = api.do(ag0, assignment, request_key="test-" + assignment["task"])
            self.assertEqual(result["status"], "committed", result)
        runtime = RuntimeStore(workflow.coordinator)
        runtime.migrate(ag0)
        for binding in compiled["bindings"]:
            runtime.bind(ag0, binding)
        result = runtime.register_plan(ag0, compiled["plan"])
        self.assertEqual(result["status"], "committed")
        runtime.reconcile(ag0)
        works = {w["node"]["id"]: w for w in runtime.status()["works"]}
        self.assertEqual(works["fabricated-preparation-research-work"]["state"], "ready")
        self.assertNotEqual(works["fabricated-preparation-design-work"]["state"], "ready")
        self.assertEqual(works["fabricated-preparation-attention"]["state"], "blocked")
        self.assertEqual(compiled["assignments"][1]["inputs"][0]["after_task"], "fabricated-preparation-research")

    def test_compiled_full_role_plan_finishes_through_real_business_gates(self):
        value = request()
        value["stages"][1]["review_required"] = False
        value["stages"].extend([
            {"id": "materials", "role": "AG2", "output": {"id": "fictional-materials", "type": "MaterialUse", "validation": "preparation_sources"},
             "prompt": "Produce the declared complete fictional materials from the actual adopted design.",
             "scope": ["whole"], "use": "teaching", "review_required": True, "review_after": ["readback"],
             "inputs": [{"artifact": "fictional-design", "after_task": "design", "scope": ["whole"], "use": "teaching"}],
             "output_spec": {"kind": "preparation_sources", "members": [
                 {"id": kind, "kind": kind, "path": "artifacts/fictional-" + kind + ".md"}
                 for kind in ("formal_task", "mainline", "teacher_reference", "material_report")]}},
            {"id": "readback", "role": "AG1", "output": {"id": "fictional-readback", "type": "ActivitySpec", "validation": "utf8"},
             "prompt": "Read the actual candidate material inventory members and check the intended function.",
             "scope": ["whole"], "use": "teaching", "inputs": [], "from_stage": "materials", "review_required": False}])
        compiled = self.compile(value)
        workflow = CompleteWorkflow(self.root)
        api = AgentCoordinator(workflow.coordinator)
        runtime = RuntimeStore(workflow.coordinator)
        ag0 = workflow.sessions["AG0"]
        for assignment in compiled["assignments"]:
            self.assertEqual(api.do(ag0, assignment, request_key=assignment["task"])["status"], "committed")
        runtime.migrate(ag0)
        for binding in compiled["bindings"]:
            runtime.bind(ag0, binding)
        runtime.register_plan(ag0, compiled["plan"])

        class FabricatedHost:
            def __init__(self):
                self.packets = {}

            def inspect(self, binding):
                return {"state": "idle"}

            def dispatch(self, binding, prompt, dispatch_id):
                self.packets[dispatch_id] = json.loads(prompt.rsplit("\n", 1)[-1])
                if binding["role"] == "AG0":
                    runtime.begin_dispatch(self.packets[dispatch_id]["context"], "AG0")
                return {"status": "accepted", "thread_id": binding["thread_id"] or "fixture-" + binding["id"]}

            def observe(self, binding, attempt):
                packet = self.packets[attempt["dispatch_id"]]
                node = packet["node_id"]
                output, intents = "Explicit fabricated completion, not learning evidence.", []
                if node.endswith("-work"):
                    output = "A unique synthetic work product for " + packet["task"]
                    if "output_spec" in packet:
                        output = json.dumps({"files": [{"id": member["id"],
                                                         "content": "Unique synthetic " + member["kind"] + " for this isolated fixture."}
                                                        for member in packet["output_spec"]["members"]]})
                    intents = [{"action": "deliver", "task": packet["task"], "path": "$output"},
                               {"action": "opinion", "task": packet["task"], "outcome": "supported",
                                "rationale": "Explicit fabricated owner conclusion in this isolated test."}]
                    if node.endswith("-readback-work"):
                        intents[1]["allow_provisional"] = True
                elif node.endswith("-questions"):
                    output = "Independent fictional question: does the fixture cover the declared case?"
                elif node.endswith("-review"):
                    intents = [{"action": "opinion", "task": packet["task"], "outcome": "supported",
                                "rationale": "Explicit fabricated exact-version review in this isolated test."}]
                elif node.endswith("-adopt"):
                    intents = [{"action": "adopt", "tasks": packet["allowed_tasks"]}]
                return {"status": "result_saved", "thread_id": binding["thread_id"], "turn_ended": True,
                        "result": {"dispatch_id": attempt["dispatch_id"], "output": output, "intents": intents}}

        host = FabricatedHost()
        scheduler = RuntimeScheduler(workflow.coordinator, {"cli": host, "desktop": host}, instance_id="fixture-scheduler")
        self.addCleanup(lambda: runtime.release_supervisor("fixture-scheduler"))
        for _ in range(60):
            scheduler.tick()
            states = {w["node"]["id"]: w["state"] for w in runtime.status()["works"]}
            if all(states[node["id"]] == "done" for node in compiled["plan"]["nodes"] if not node.get("handling_attention")):
                break
        self.assertEqual(states, {node["id"]: "blocked" if node.get("handling_attention") else "done"
                                  for node in compiled["plan"]["nodes"]},
                         {w["node"]["id"]: (w["state"], w.get("reason")) for w in runtime.status()["works"]})
        packets = {packet["node_id"]: packet for packet in host.packets.values()}
        questions = packets["fabricated-preparation-materials-questions"]
        self.assertEqual(questions["inputs"], [])
        self.assertEqual(questions["task_snapshot"], [])
        review = packets["fabricated-preparation-materials-review"]
        self.assertEqual(len(review["prior_results"]), 1)
        self.assertIn("Independent fictional question", review["prior_results"][0]["text"])
        self.assertTrue(review["task_snapshot"])
        self.assertTrue(packets["fabricated-preparation-readback-work"]["task_snapshot"])
        self.assertEqual(len(workflow.coordinator.status(ag0)["adopted_pointers"]), 4)
        tasks = {task["id"]: task for task in workflow.coordinator.status(ag0)["tasks"]}
        self.assertEqual(tasks[review["task"]]["target_ref"], tasks["fabricated-preparation-materials"]["result_ref"])

    def test_questions_precede_author_exposure_and_review_uses_exact_source(self):
        nodes = self.nodes(self.compile())
        questions = nodes["fabricated-preparation-design-questions"]
        review = nodes["fabricated-preparation-design-review"]
        self.assertEqual(questions["completion"], "result")
        self.assertFalse(questions.get("task"))
        self.assertFalse(questions.get("setup_intents"))
        self.assertTrue(all(c["kind"] == "work_done" for c in questions["conditions"]))
        self.assertNotIn("Design a bounded check", questions["prompt"])
        self.assertIn(request()["purpose"], questions["prompt"])
        self.assertEqual(review["binding"], questions["binding"])
        self.assertEqual(review["include_prior_results"], [questions["id"]])
        self.assertIn({"kind": "work_done", "node": questions["id"]}, review["conditions"])
        self.assertEqual(review["setup_intents"], [{"action": "assign_review", "task": review["task"],
                                                    "from_task": "fabricated-preparation-design"}])
        self.assertNotIn("target", review["setup_intents"][0])

    def test_each_review_pair_has_a_fresh_independent_cli_binding(self):
        value = request()
        value["stages"][0]["review_required"] = True
        compiled = self.compile(value)
        nodes = self.nodes(compiled)
        first, second = (nodes["fabricated-preparation-" + name + "-review"] for name in ("research", "design"))
        self.assertNotEqual(first["binding"], second["binding"])
        bindings = {b["id"]: b for b in compiled["bindings"]}
        for node in (first, second):
            self.assertEqual(bindings[node["binding"]]["role"], "AG3")
            self.assertIsNone(bindings[node["binding"]]["thread_id"])

    def test_worker_requires_actual_delivery_and_explicit_owner_opinion(self):
        compiled = self.compile()
        for node in compiled["plan"]["nodes"]:
            if node["id"].endswith("-work"):
                self.assertEqual(node["required_intents"], ["deliver", "opinion"])
                self.assertIn(node["task"], node["prompt"])
                self.assertIn("'$output'", node["prompt"])
                self.assertIn("partial or rejected", node["prompt"])
            if node["id"].endswith("-adopt"):
                self.assertTrue(node["result_via_file"])
                self.assertIn("actual AG0 adoption decision", node["prompt"])
                self.assertEqual(node["conditions"][0]["kind"], "adoption_ready")
        final = self.nodes(compiled)["fabricated-preparation-report"]
        self.assertEqual(final["completion"], "result")
        self.assertTrue(final["result_via_file"])
        self.assertEqual(final["required_intents"], [])
        self.assertIn("intents:[]", final["prompt"])
        self.assertIn("end this turn", final["prompt"])
        self.assertEqual({c["task"] for c in final["conditions"] if c["kind"] == "adopted"},
                         {a["task"] for a in compiled["assignments"]})

    def test_attention_returns_to_original_ag0_without_blocking_success_report(self):
        compiled = self.compile()
        nodes = self.nodes(compiled)
        attention = nodes["fabricated-preparation-attention"]
        report = nodes["fabricated-preparation-report"]
        self.assertIs(compiled["plan"]["nodes"][-1], attention)
        self.assertTrue(attention["handling_attention"])
        self.assertEqual(attention["binding"], "fabricated-preparation-AG0")
        self.assertEqual(attention["scope"], ["whole"])
        self.assertEqual(attention["allowed_tasks"], [a["task"] for a in compiled["assignments"]])
        self.assertEqual(attention["conditions"], [{"kind": "workflow_attention"}])
        self.assertEqual(attention["completion"], "result")
        self.assertEqual(attention["required_intents"], [])
        self.assertTrue(attention["result_via_file"])
        self.assertIn("decision_basis", attention["prompt"])
        self.assertIn("intents:[]", attention["prompt"])
        self.assertNotIn({"kind": "work_done", "node": attention["id"]}, report["conditions"])

    def test_unresolved_send_reports_once_to_original_ag0_without_resending_worker(self):
        compiled = self.compile()
        workflow = CompleteWorkflow(self.root)
        api, ag0 = AgentCoordinator(workflow.coordinator), workflow.sessions["AG0"]
        runtime = RuntimeStore(workflow.coordinator)
        for assignment in compiled["assignments"]:
            self.assertEqual(api.do(ag0, assignment, request_key=assignment["task"])["status"], "committed")
        runtime.migrate(ag0)
        for binding in compiled["bindings"]:
            runtime.bind(ag0, binding)
        runtime.register_plan(ag0, compiled["plan"])

        class UnresolvedHost:
            def __init__(self):
                self.sent = []
                self.packets = {}

            def inspect(self, binding):
                return {"state": "idle"}

            def dispatch(self, binding, prompt, dispatch_id):
                self.sent.append(deepcopy(binding))
                self.packets[dispatch_id] = packet = json.loads(prompt.rsplit("\n", 1)[-1])
                if binding["role"] == "AG2":
                    raise TimeoutError("Fabricated ambiguous send; never retry.")
                runtime.begin_dispatch(packet["context"], "AG0")
                return {"status": "accepted", "thread_id": binding["thread_id"]}

            def observe(self, binding, attempt):
                if binding["role"] == "AG2":
                    return {"status": "dispatch_unknown"}
                packet = self.packets[attempt["dispatch_id"]]
                return {"status": "result_saved", "thread_id": binding["thread_id"], "turn_ended": True,
                        "result": {"dispatch_id": attempt["dispatch_id"], "intents": [],
                                   "output": "Synthetic attention report from actual facts: " + json.dumps(packet["decision_basis"])}}

        host = UnresolvedHost()
        scheduler = RuntimeScheduler(workflow.coordinator, {"cli": host, "desktop": host}, instance_id="fixture-attention-scheduler")
        self.addCleanup(lambda: runtime.release_supervisor("fixture-attention-scheduler"))
        for _ in range(8):
            scheduler.tick()
        states = {work["node"]["id"]: work["state"] for work in runtime.status()["works"]}
        self.assertEqual(states["fabricated-preparation-research-work"], "dispatch_unknown")
        self.assertEqual(states["fabricated-preparation-attention"], "done")
        self.assertEqual(states["fabricated-preparation-report"], "blocked")
        self.assertEqual([binding["role"] for binding in host.sent], ["AG2", "AG0"])
        self.assertEqual(host.sent[1]["thread_id"], "actual-parent-thread")
        packet = next(p for p in host.packets.values() if p["node_id"].endswith("-attention"))
        self.assertEqual(packet["decision_basis"][0]["problems"][0]["state"], "dispatch_unknown")
        self.assertEqual(packet["decision_basis"][0]["problems"][0]["reason"], "TimeoutError")

    def test_candidate_readback_is_deferred_and_cannot_broaden_its_source(self):
        value = request()
        value["stages"][1].update(from_stage="research", inputs=[], after=[], review_after=[])
        compiled = self.compile(value)
        self.assertEqual(len(compiled["assignments"]), 1)
        nodes = self.nodes(compiled)
        work = nodes["fabricated-preparation-design-work"]
        setup = work["setup_intents"][0]
        intent_shape(setup)
        self.assertEqual(setup["action"], "assign_readback")
        self.assertEqual(setup["from_task"], "fabricated-preparation-research")
        self.assertEqual(work["conditions"], [{"kind": "submitted", "task": setup["from_task"]}])
        self.assertIn("allow_provisional:true", work["prompt"])
        self.assertIn({"kind": "adopted", "task": setup["from_task"]}, nodes["fabricated-preparation-design-adopt"]["conditions"])
        value["stages"][1]["scope"] = ["outside"]
        with self.assertRaisesRegex(GateError, "readback_scope_or_use_mismatch"):
            self.compile(value)

    def test_review_can_wait_for_readback_without_deadlocking_source_adoption(self):
        value = request()
        value["stages"][0].update(review_required=True, review_after=["design"])
        value["stages"][1].update(from_stage="research", inputs=[], after=[], review_required=False)
        nodes = self.nodes(self.compile(value))
        self.assertIn({"kind": "work_done", "node": "fabricated-preparation-design-work"},
                      nodes["fabricated-preparation-research-questions"]["conditions"])
        value["stages"][0]["adopt_after"] = ["design"]
        with self.assertRaisesRegex(GateError, "cyclic_preparation_dependencies"):
            self.compile(value)

    def test_rejects_unknown_refs_cycles_missing_roles_and_thread_overrides(self):
        invalid = []
        value = request(); value["stages"][1]["after"] = ["missing"]; invalid.append(value)
        value = request(); value["stages"][0]["after"] = ["design"]; invalid.append(value)
        value = request(); value["stages"][1]["inputs"][0]["after_task"] = "missing"; invalid.append(value)
        value = request(); value["stages"] = value["stages"][:1]; invalid.append(value)
        value = request(); value["thread_id"] = "other"; invalid.append(value)
        value = request(); value["stages"][0]["binding"] = "other"; invalid.append(value)
        value = request(); value["stages"][0]["review_required"] = "false"; invalid.append(value)
        value = request(); value["stages"][0]["adopt"] = False; invalid.append(value)
        value = request(); value["stages"][1]["inputs"][0]["scope"] = ["outside"]; invalid.append(value)
        value = request(); value["stages"][1]["id"] = "research-review"; value["stages"][0]["review_required"] = True; invalid.append(value)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(GateError):
                self.compile(value)

    def test_deadlines_and_report_prompt_are_explicit_and_output_specs_stay_scoped(self):
        value = request()
        value.update(deadline_ms=1700000000000, run_timeout_ms=90000, report_prompt="State the actual fictional status in one sentence.")
        material = value["stages"][0]
        material["output"].update(type="MaterialUse", validation="preparation_sources")
        material["output_spec"] = {"kind": "preparation_sources", "members": [
            {"id": kind, "kind": kind, "path": "artifacts/" + kind + ".md"}
            for kind in ("formal_task", "mainline", "teacher_reference", "material_report")]}
        original = deepcopy(material["output_spec"])
        compiled = self.compile(value)
        nodes = self.nodes(compiled)
        self.assertEqual(nodes["fabricated-preparation-research-work"]["output_spec"], original)
        self.assertTrue(all(n["deadline_ms"] == value["deadline_ms"] and n["run_timeout_ms"] == 90000
                            for n in nodes.values()))
        self.assertIn(value["report_prompt"], nodes["fabricated-preparation-report"]["prompt"])
        material["output_spec"]["members"][0]["path"] = "../outside.md"
        with self.assertRaisesRegex(GateError, "unsafe_preparation_source_path"):
            self.compile(value)


if __name__ == "__main__":
    unittest.main()
