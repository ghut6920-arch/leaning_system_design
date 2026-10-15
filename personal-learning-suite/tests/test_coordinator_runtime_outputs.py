"""Real multi-file preparation through the runtime; synthetic data, no models."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
from coordinator.agent_api import AgentCoordinator
from coordinator.preparation_sources import load_map
from coordinator.runtime_outputs import materialize_output, validate_output_spec
from coordinator.runtime_scheduler import RuntimeScheduler
from coordinator.runtime_store import RuntimeStore
from coordinator.workspace import GateError, encode
from test_coordinator_complete import CompleteWorkflow
from test_coordinator_runtime import FakeRuntimeHost


class RuntimeOutputTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="runtime-bundle-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.control = {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []}
        self.w = CompleteWorkflow(self.root, lambda: deepcopy(self.control))
        self.c = self.w.coordinator
        self.api = AgentCoordinator(self.c)
        self.store = RuntimeStore(self.c)
        assigned = self.api.do(self.w.sessions["AG0"], {
            "action": "assign", "task": "material", "output": {"id": "lesson", "type": "MaterialUse", "validation": "preparation_sources"},
            "scope": ["whole"], "use": "teaching", "inputs": [], "review_required": False}, request_key="test-assignment")
        self.assertEqual(assigned["status"], "committed", assigned)
        self.store.migrate(self.w.sessions["AG0"])
        self.binding = self.store.bind(self.w.sessions["AG0"], {
            "id": "author", "role": "AG2", "host_kind": "fake", "thread_id": "actual-test-author",
            "authorized": True, "authorization_ref": "synthetic-authorized"})
        self.members = [{"id": key, "kind": kind, "path": path} for key, kind, path in [
            ("task", "formal_task", "questions/fabricated/task.md"),
            ("lesson", "mainline", "materials/fabricated/mainline.md"),
            ("reference", "teacher_reference", "materials/fabricated/teacher-reference.md"),
            ("report", "material_report", "artifacts/fabricated/report.md")]]
        self.node = {"id": "author", "binding": "author", "task": "material", "allowed_tasks": ["material"],
                     "manage_tasks": ["material"], "allowed_actions": ["start", "submit", "confirm"], "conditions": [],
                     "prompt": "Author a fictional complete teaching bundle.", "use": "teaching", "completion": "business",
                     "required_intents": ["deliver", "opinion"], "expected_output_contains": ["完整教师参考"],
                     "output_spec": {"kind": "preparation_sources", "members": self.members}}
        self.contents = {"task": "Fictional task: explain the supplied example.",
                         "lesson": "Fictional main lesson with worked steps.",
                         "reference": "完整教师参考：逐步解释和答案。", "report": "Fictional material quality report."}
        self.output = encode({"files": [{"id": key, "content": value} for key, value in self.contents.items()]})
        self.store.register_plan(self.w.sessions["AG0"], {"id": "preparation", "revision": 1,
            "authorization_ref": "synthetic-authorized", "nodes": [self.node]})
        self.host = FakeRuntimeHost()
        self.scheduler = RuntimeScheduler(self.c, {"fake": self.host}, instance_id="bundle-scheduler")

    def work(self):
        return self.store.status()["works"][0]

    def save_ready(self, output=None):
        self.scheduler.tick()
        work = self.work()
        self.host.result = {"dispatch_id": work["dispatch_id"], "output": self.output if output is None else output,
                            "intents": [{"action": "deliver", "task": "material", "path": "$output"},
                                        {"action": "opinion", "task": "material", "outcome": "supported",
                                         "rationale": "I checked the authored task, lesson, full reference and report."}]}
        self.scheduler.tick()
        self.assertEqual(self.work()["state"], "result_saved")
        return self.work()

    def output_path(self, work):
        return self.root / "artifacts/runtime" / (work["dispatch_id"] + ".txt")

    def test_actual_multi_file_sources_submit_and_owner_opinion(self):
        work = self.save_ready()
        self.scheduler.tick()
        self.assertEqual(self.work()["state"], "done", self.work())
        state = self.c.status(self.w.sessions["AG0"])
        artifact = state["artifacts"][0]
        manifest, verified = load_map(self.c, artifact, exact=artifact, scope=["whole"], intended_use="teaching")
        self.assertEqual(len(verified), 4)
        self.assertEqual(manifest["artifact_ref"], {"id": "lesson", "revision": 1})
        for member in self.members:
            self.assertEqual((self.root / member["path"]).read_text(encoding="utf-8"), self.contents[member["id"]])
        self.assertEqual(json.loads(self.output_path(work).read_text(encoding="utf-8")), manifest)
        self.assertNotIn("files", manifest)
        self.assertIn("preparation_sources", self.host.dispatches[0]["prompt"])
        self.assertEqual(state["tasks"][0]["phase"], "submitted")

    def test_malformed_or_missing_members_reject_before_any_file_write(self):
        for bad in ("not json", encode({"files": []}),
                    encode({"files": [{"id": "task", "content": "a", "path": "forbidden"}]}),
                    encode({"files": [{"id": "task", "content": "a"}] * 4})):
            with self.subTest(output=bad):
                with self.assertRaises(GateError):
                    materialize_output(self.c, self.w.sessions["AG2"], self.node, bad,
                                       "artifacts/runtime/output.txt", assert_current=lambda: None)
                self.assertFalse((self.root / "questions").exists())
                self.assertFalse((self.root / "materials").exists())

    def test_declared_paths_reject_traversal_duplicates_and_windows_aliases(self):
        for path in ("materials/../escape.md", "materials/.hidden.md", "materials/CON/reference.md",
                     "materials/name./reference.md", self.members[0]["path"].upper()):
            spec = deepcopy(self.node["output_spec"])
            spec["members"][-1]["path"] = path
            with self.subTest(path=path), self.assertRaises(GateError):
                validate_output_spec(spec)
        spec = deepcopy(self.node["output_spec"])
        spec["members"][-1]["path"] = self.members[0]["path"]
        with self.assertRaises(GateError):
            validate_output_spec(spec)

    def test_late_member_conflict_does_not_write_earlier_members(self):
        work = self.save_ready()
        conflict = self.root / self.members[-1]["path"]
        conflict.parent.mkdir(parents=True)
        conflict.write_text("Existing unrelated immutable bytes.", encoding="utf-8")
        self.scheduler.tick()
        self.assertEqual(self.work()["state"], "needs_user")
        self.assertEqual(self.work()["reason"], "runtime_output_changed")
        self.assertFalse((self.root / self.members[0]["path"]).exists())
        self.assertFalse(self.output_path(work).exists())
        self.assertEqual(conflict.read_text(encoding="utf-8"), "Existing unrelated immutable bytes.")

    def test_stale_dispatch_is_checked_before_any_bundle_write(self):
        work = self.save_ready()
        attempt = self.store.lookup("runtime_attempts", work["dispatch_id"])
        context = {"dispatch_id": work["dispatch_id"], "thread_id": self.binding["thread_id"],
                   "claim_epoch": attempt["claim_epoch"] + 1}
        session = self.c.bind_local_operator("AG2", dispatch=context)
        with self.assertRaisesRegex(GateError, "stale_dispatch"):
            materialize_output(self.c, session, self.node, self.output,
                               self.output_path(work).relative_to(self.root).as_posix(),
                               assert_current=lambda: self.store.assert_dispatch(context, "AG2"))
        self.assertFalse((self.root / "questions").exists())
        self.assertFalse((self.root / "materials").exists())

    def test_acceptance_checks_authored_content_before_any_write(self):
        output = json.loads(self.output)
        for item in output["files"]:
            if item["id"] == "reference":
                item["content"] = "An incomplete reference without the required marker."
        work = self.save_ready(encode(output))
        self.scheduler.tick()
        self.assertEqual(self.work()["reason"], "runtime_output_acceptance_failed")
        self.assertFalse((self.root / "questions").exists())
        self.assertFalse(self.output_path(work).exists())

    def test_recovery_after_deliver_reuses_exact_bundle_and_original_receipt(self):
        work = self.save_ready()
        def crash_after_first_commit(name):
            if name == "runtime_after_publish":
                raise KeyboardInterrupt("synthetic loss after deliver")
        with patch.object(self.c, "checkpoint", side_effect=crash_after_first_commit):
            with self.assertRaises(KeyboardInterrupt):
                self.scheduler.tick()
        self.assertEqual(self.work()["state"], "result_saved")
        before = self.output_path(work).read_bytes()
        self.scheduler.tick()
        self.assertEqual(self.work()["state"], "done", self.work())
        self.assertEqual(self.output_path(work).read_bytes(), before)
        self.assertEqual(len(self.c.status(self.w.sessions["AG0"])["artifacts"]), 1)

    def test_readback_setup_retry_keeps_exact_candidate_input(self):
        self.save_ready()
        self.scheduler.tick()
        self.store.bind(self.w.sessions["AG0"], {"id": "reader", "role": "AG1", "host_kind": "fake",
            "thread_id": "actual-test-reader", "authorized": True, "authorization_ref": "synthetic-authorized"})
        setup = {"action": "assign_readback", "task": "readback", "from_task": "material",
                 "output": {"id": "readback-output", "type": "ActivitySpec", "validation": "utf8"},
                 "scope": ["whole"], "use": "teaching", "review_required": False,
                 "provisional_conditions": "Functional readback of the exact unadopted candidate only."}
        node = {"id": "readback", "binding": "reader", "task": "readback", "allowed_tasks": ["readback", "material"],
                "allowed_actions": ["register", "start", "submit"], "manage_tasks": ["readback"],
                "conditions": [{"kind": "submitted", "task": "material"}], "setup_intents": [setup],
                "prompt": "Read the exact fictional candidate.", "use": "teaching", "completion": "business"}
        self.store.register_plan(self.w.sessions["AG0"], {"id": "readback-workflow", "revision": 1,
            "authorization_ref": "synthetic-authorized", "nodes": [node]})
        inspections = 0
        def busy_after_packet(binding):
            nonlocal inspections
            inspections += 1
            return {"state": "idle" if inspections == 1 else "active", "last_turn_id": "before"}
        with patch.object(self.host, "inspect", side_effect=busy_after_packet):
            self.scheduler.tick()
        readback = next(work for work in self.store.status()["works"] if work["node"]["id"] == "readback")
        self.assertEqual(readback["state"], "ready", readback)
        self.scheduler.tick()
        self.assertEqual(len(self.host.dispatches), 2)
        packet = json.loads(self.host.dispatches[-1]["prompt"].rsplit("\n", 1)[-1])
        self.assertEqual(packet["task_snapshot"][0]["ref"], {"id": "lesson", "revision": 1})
        self.assertEqual(packet["task_snapshot"][0]["text"], self.output_path(self.store.status()["works"][0]).read_text(encoding="utf-8"))
        tasks = self.c.status(self.w.sessions["AG0"])["tasks"]
        self.assertEqual(len([task for task in tasks if task["id"] == "readback"]), 1)

    def test_prior_questions_are_explicit_correlated_and_not_author_output(self):
        self.store.bind(self.w.sessions["AG0"], {"id": "reviewer", "role": "AG3", "host_kind": "fake",
            "thread_id": "actual-test-reviewer", "authorized": True, "authorization_ref": "synthetic-authorized"})
        common = {"binding": "reviewer", "allowed_tasks": ["material"], "allowed_actions": ["start"],
                  "use": "teaching", "completion": "result"}
        nodes = [{**common, "id": "questions", "conditions": [], "prompt": "Write independent questions."},
                 {**common, "id": "review-questions", "conditions": [{"kind": "work_done", "node": "questions"}],
                  "include_prior_results": ["questions"], "prompt": "Continue using only your prior questions."}]
        self.store.register_plan(self.w.sessions["AG0"], {"id": "reviewer-context", "revision": 1,
            "authorization_ref": "synthetic-authorized", "nodes": nodes})
        self.scheduler.tick()
        first = next(work for work in self.store.status()["works"] if work["node"]["id"] == "questions")
        # Keep the unrelated author turn pending while finishing the questions.
        def result_for_questions(binding, attempt):
            if binding["id"] != "reviewer":
                return {"status": "running", "thread_id": binding["thread_id"]}
            return {"status": "result_saved", "thread_id": binding["thread_id"], "turn_ended": True,
                    "result": {"dispatch_id": attempt["dispatch_id"], "output": "Independent question: what evidence verifies the answer?", "intents": []}}
        with patch.object(self.host, "observe", side_effect=result_for_questions):
            self.scheduler.tick()
            self.scheduler.tick()
            self.scheduler.tick()
        packet = json.loads(self.host.dispatches[-1]["prompt"].rsplit("\n", 1)[-1])
        self.assertEqual(packet["node_id"], "review-questions")
        self.assertEqual(len(packet["prior_results"]), 1)
        prior = packet["prior_results"][0]
        self.assertEqual(prior["node_id"], "questions")
        self.assertEqual(prior["dispatch_id"], first["dispatch_id"])
        self.assertIn("what evidence verifies", prior["text"])
        self.assertEqual(packet["inputs"], [])
        self.assertEqual(packet["task_snapshot"], [])


if __name__ == "__main__":
    unittest.main()
