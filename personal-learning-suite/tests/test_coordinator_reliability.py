"""Actual multi-process and hard-exit tests, exclusively in fabricated temporary roots."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
from demo_coordinator_workspace import Workflow
from coordinator.workspace import Coordinator, GateError
from coordinator.reliability import ReliableCoordinator


class CoordinatorReliabilityTests(unittest.TestCase):
    # The acceptance driver records metrics from these real subprocess scenarios.
    observations = []

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tac-reliability-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.control = {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []}
        self.w = Workflow(self.root, lambda: deepcopy(self.control), coordinator_class=ReliableCoordinator)
        self.c = self.w.coordinator
        self.now = 1000
        self.c.clock_ms = lambda: self.now

    def seed(self, name="source"):
        target = self.w.candidate(name)["ref"]
        owner = self.w.confirm(target)
        self.w.adopt(target, [owner])
        return target, owner

    def wait_task(self, producer="producer", *, timeout=500, name="waiter"):
        self.w.register(producer, "source")
        self.w.op("AG2", "start", task_id=producer)
        self.w.op("AG0", "register", id=name, assignee="AG1", task_kind="production", scope=["whole"],
                  intended_use="teaching", output={"id": name + "-output", "type": "ActivitySpec", "requires_ag3_review": False},
                  inputs=[{"id": "source", "policy": "after_task", "producer_task_id": producer, "scope": ["whole"], "intended_use": "teaching"}],
                  wait_timeout_ms=timeout)
        result = self.w.op("AG1", "start", task_id=name)
        self.assertEqual(result["phase"], "waiting")
        return result

    def task(self, name):
        return next(t for t in self.c.status(self.w.sessions["AG0"])["tasks"] if t["id"] == name)

    def launch(self, request, role, action, *, label="worker", point=None, go=None, retry=False, count=1):
        path = self.root / f"{label}-request.json"
        path.write_text(json.dumps(request), encoding="utf-8")
        argv = [sys.executable, "-B", "-X", "utf8", str(SUITE / "scripts/coordinator_fault_worker.py"),
                "--workspace", str(self.root), "--request", str(path), "--role", role, "--action", action]
        ready = None
        if point:
            argv += ["--failpoint", point]
        if go:
            ready = self.root / f"{label}.ready"
            argv += ["--ready", str(ready), "--go", str(go)]
        if retry:
            argv += ["--retry-factual-register", "--register-count", str(count)]
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        def reap():
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)
        self.addCleanup(reap)
        return process, ready

    def collect(self, process, expected_code=0):
        out, err = process.communicate(timeout=40)
        self.assertEqual(process.returncode, expected_code, err + out)
        return json.loads(out) if out else None

    def release(self, go, ready):
        deadline = time.monotonic() + 15
        while not all(path.exists() for path in ready):
            if time.monotonic() >= deadline:
                self.fail("Workers did not reach the barrier")
            time.sleep(.01)
        go.write_text("go", encoding="ascii")

    def test_specific_result_waits_until_adopted_without_global_lock(self):
        old, _ = self.seed()
        start = self.wait_task()
        self.w.register("independent", "independent-output", role="AG1", kind="ActivitySpec",
                        inputs=[{"id": "source", "policy": "adopted", "scope": ["whole"], "intended_use": "teaching"}])
        snapshot = self.w.op("AG1", "start", task_id="independent")["snapshot"]
        self.assertEqual(snapshot[0]["revision"], old["revision"])
        candidate = self.w.submit("producer")["ref"]
        self.assertEqual(self.task("waiter")["phase"], "waiting")
        owner = self.w.confirm(candidate)
        self.w.adopt(candidate, [owner])
        self.assertEqual(self.task("waiter")["phase"], "registered")
        self.w.op("AG1", "start", task_id="waiter")
        actual = self.c.read_snapshot(self.w.sessions["AG1"], "waiter")[0]["ref"]
        self.assertEqual(actual, candidate)
        self.assertEqual(start["wait_deadline_ms"], 1500)

    def test_upstream_failure_releases_wait_and_preserves_old_adoption(self):
        old, _ = self.seed()
        self.wait_task()
        self.w.op("AG2", "finish", task_id="producer", phase="failed", reason="Fabricated upstream failure")
        waiter = self.task("waiter")
        self.assertEqual(waiter["phase"], "blocked")
        self.assertEqual(waiter["stop_reason"], "upstream_failed")
        self.assertEqual(waiter["next_owner"], "AG0")
        self.assertEqual(self.c.status(self.w.sessions["AG0"])["adopted_pointers"][0]["revision"], old["revision"])
        events = self.c.events(self.w.sessions["AG0"])["events"]
        self.assertTrue(any(e["kind"] == "wait_blocked" and e["task_id"] == "waiter" for e in events))

    def test_cancellation_is_explicit_and_does_not_fall_back_to_old_input(self):
        self.seed()
        self.wait_task()
        self.w.op("AG0", "finish", task_id="producer", phase="cancelled", reason="Fabricated explicit stop")
        self.assertEqual(self.task("waiter")["stop_reason"], "upstream_cancelled")
        refusal = self.w.op("AG1", "start", expect="rejected", task_id="waiter")
        self.assertEqual(refusal["reasons"], ["task_not_registered"])

    def test_wait_deadline_is_not_reset_by_repeated_start(self):
        self.wait_task()
        self.now = 1200
        second = self.w.op("AG1", "start", task_id="waiter")
        self.assertEqual(second["wait_deadline_ms"], 1500)
        self.now = 1501
        self.assertEqual(self.task("waiter")["effective_phase"], "blocked")
        result = self.w.op("AG0", "refresh", task_id="waiter")
        self.assertEqual(result["reason"], "wait_timeout")
        self.assertEqual(self.task("waiter")["phase"], "blocked")

    def test_late_publication_cannot_resurrect_timed_out_wait(self):
        self.wait_task()
        self.now = 1600
        candidate = self.w.submit("producer")["ref"]
        owner = self.w.confirm(candidate)
        self.w.adopt(candidate, [owner])
        self.assertEqual(self.task("waiter")["phase"], "blocked")
        self.assertEqual(self.task("waiter")["stop_reason"], "wait_timeout")

    def test_wait_requires_explicit_timeout_and_matching_producer_scope(self):
        self.w.register("producer", "source")
        request = self.w.request(id="waiter", assignee="AG1", task_kind="production", scope=["whole"], intended_use="teaching",
                                 output={"id": "output", "type": "ActivitySpec", "requires_ag3_review": False},
                                 inputs=[{"id": "source", "policy": "after_task", "producer_task_id": "producer", "scope": ["whole"], "intended_use": "teaching"}])
        self.assertEqual(self.c.execute(self.w.sessions["AG0"], "register", request)["reasons"], ["bounded_wait_timeout_required"])
        request["wait_timeout_ms"] = 1000
        request["inputs"][0]["id"] = "another-output"
        self.assertEqual(self.c.execute(self.w.sessions["AG0"], "register", request)["reasons"], ["wait_producer_output_mismatch"])

    def test_events_are_incremental_and_idempotent_retry_adds_no_event(self):
        self.w.register("task", "source")
        cursor = self.c.events(self.w.sessions["AG0"])["next_sequence"]
        request = self.w.request(task_id="task")
        first = self.c.execute(self.w.sessions["AG2"], "start", request)
        self.assertEqual(self.c.execute(self.w.sessions["AG2"], "start", request), first)
        new = self.c.events(self.w.sessions["AG0"], after_sequence=cursor)
        self.assertEqual(len(new["events"]), 1)
        self.assertEqual(self.c.events(self.w.sessions["AG0"], after_sequence=new["next_sequence"])["events"], [])

    def test_event_and_commit_receipt_are_filtered_after_deletion(self):
        self.w.register("task", "source")
        operation = self.w.trace[-1]["request"]["operation_id"]
        self.control["deleted_ids"] = ["source"]
        self.assertEqual(self.c.events(self.w.sessions["AG0"])["events"], [])
        with self.assertRaisesRegex(GateError, "deleted_scope"):
            self.c.operation(self.w.sessions["AG0"], operation)

    def test_two_adopters_conflict_and_refreshing_state_cannot_override_pointer_intent(self):
        self.seed()
        second = self.w.candidate("source")["ref"]
        owner2 = self.w.confirm(second)
        third = self.w.candidate("source")["ref"]
        owner3 = self.w.confirm(third)
        revision = self.c.status(self.w.sessions["AG0"])["state_revision"]
        requests = []
        for n, target, owner in ((2, second, owner2), (3, third, owner3)):
            requests.append({"operation_id": f"race-adopt-{n}", "expected_state_revision": revision, "bundle_id": f"race-bundle-{n}",
                             "members": [{"ref": target, "scope": ["whole"], "intended_use": "teaching", "receipt_ids": [owner]}],
                             "expected_pointers": [{"id": "source", "scope": "whole", "intended_use": "teaching", "revision": 1}]})
        go = self.root / "go"
        workers = [self.launch(r, "AG0", "adopt", label=f"adopt-{i}", go=go) for i, r in enumerate(requests)]
        self.release(go, [ready for _, ready in workers])
        results = [self.collect(p)["result"] for p, _ in workers]
        self.assertCountEqual([r["status"] for r in results], ["committed", "conflict"])
        loser = next(i for i, r in enumerate(results) if r["status"] == "conflict")
        requests[loser]["expected_state_revision"] = self.c.status(self.w.sessions["AG0"])["state_revision"]
        rejected = self.c.execute(self.w.sessions["AG0"], "adopt", requests[loser])
        self.assertEqual(rejected["reasons"], ["pointer_conflict"])
        self.observations.append({"scenario": "competing_adoption", "processes": 2, "results": results, "fresh_state_retry": rejected})

    def test_parallel_duplicate_submission_is_committed_exactly_once(self):
        self.w.register("task", "source")
        self.w.op("AG2", "start", task_id="task")
        path = self.root / "candidate.txt"
        path.write_text("Fabricated complete candidate", encoding="utf-8")
        request = self.w.request(task_id="task", path="candidate.txt", changed_scope=None)
        before = self.c.status(self.w.sessions["AG0"])["state_revision"]
        cursor = self.c.events(self.w.sessions["AG0"])["next_sequence"]
        go = self.root / "go"
        workers = [self.launch(request, "AG2", "submit", label=f"duplicate-{i}", go=go) for i in range(4)]
        self.release(go, [ready for _, ready in workers])
        results = [self.collect(p)["result"] for p, _ in workers]
        self.assertTrue(all(result == results[0] for result in results))
        self.assertEqual(self.c.status(self.w.sessions["AG0"])["state_revision"], before + 1)
        self.assertEqual(len(self.c.status(self.w.sessions["AG0"])["artifacts"]), 1)
        self.assertEqual(len(self.c.events(self.w.sessions["AG0"], after_sequence=cursor)["events"]), 1)
        self.observations.append({"scenario": "duplicate_submit", "processes": 4, "logical_commits": 1, "results": results})

    def test_parallel_new_revisions_are_unique_and_do_not_replace_adoption(self):
        self.seed()
        requests = []
        for i in range(2):
            self.w.register(f"parallel-task-{i}", "source")
            self.w.op("AG2", "start", task_id=f"parallel-task-{i}")
            (self.root / f"candidate-{i}.txt").write_text(f"Fabricated candidate {i}", encoding="utf-8")
        revision = self.c.status(self.w.sessions["AG0"])["state_revision"]
        for i in range(2):
            requests.append({"operation_id": f"new-revision-{i}", "expected_state_revision": revision,
                             "task_id": f"parallel-task-{i}", "path": f"candidate-{i}.txt", "changed_scope": None})
        go = self.root / "go"
        workers = [self.launch(r, "AG2", "submit", label=f"new-{i}", go=go) for i, r in enumerate(requests)]
        self.release(go, [ready for _, ready in workers])
        results = [self.collect(p)["result"] for p, _ in workers]
        self.assertCountEqual([r["status"] for r in results], ["committed", "conflict"])
        loser = next(i for i, r in enumerate(results) if r["status"] == "conflict")
        requests[loser]["expected_state_revision"] = self.c.status(self.w.sessions["AG0"])["state_revision"]
        self.assertEqual(self.c.execute(self.w.sessions["AG2"], "submit", requests[loser])["ref"]["revision"], 3)
        state = self.c.status(self.w.sessions["AG0"])
        self.assertEqual([a["revision"] for a in state["artifacts"]], [1, 2, 3])
        self.assertEqual(state["adopted_pointers"][0]["revision"], 1)

    def test_multi_process_registration_stress_has_no_lost_commits(self):
        go = self.root / "go"
        workers = []
        for i in range(8):
            request = self.w.request(id=f"stress-task-{i}", assignee="AG2", task_kind="production", scope=["whole"],
                                     intended_use="teaching", inputs=[], output={"id": f"stress-output-{i}", "type": "MaterialUse", "requires_ag3_review": False})
            workers.append(self.launch(request, "AG0", "register", label=f"stress-{i}", go=go, retry=True, count=8))
        self.release(go, [ready for _, ready in workers])
        results = [self.collect(p) for p, _ in workers]
        self.assertTrue(all(r["result"]["status"] == "committed" for worker in results for r in worker["results"]))
        state = self.c.status(self.w.sessions["AG0"])
        self.assertEqual(len(state["tasks"]), 64)
        self.assertEqual(state["state_revision"], 64)
        self.assertEqual(len(self.c.events(self.w.sessions["AG0"])["events"]), 64)
        self.observations.append({"scenario": "registration_stress", "processes": 8, "logical_commits": 64,
                                  "total_attempts": sum(r["attempts"] for worker in results for r in worker["results"])})

    def test_database_lock_has_bounded_busy_response_and_clean_retry(self):
        request = self.w.request(id="task", assignee="AG2", task_kind="production", scope=["whole"], intended_use="teaching", inputs=[],
                                 output={"id": "source", "type": "MaterialUse", "requires_ag3_review": False})
        blocker = sqlite3.connect(self.c.db_path, isolation_level=None)
        self.addCleanup(blocker.close)
        blocker.execute("BEGIN IMMEDIATE")
        self.c.lock_timeout = .05
        result = self.c.execute(self.w.sessions["AG0"], "register", request)
        self.assertEqual(result["status"], "busy")
        self.assertIsNone(result["state_revision"])
        blocker.rollback()
        self.assertEqual(self.c.execute(self.w.sessions["AG0"], "register", request)["status"], "committed")

    def test_process_exit_before_candidate_commit_keeps_old_adopted_version(self):
        self.seed()
        self.w.register("candidate-task", "source")
        self.w.op("AG2", "start", task_id="candidate-task")
        (self.root / "orphan.txt").write_text("Fabricated staged candidate", encoding="utf-8")
        request = self.w.request(task_id="candidate-task", path="orphan.txt", changed_scope=None)
        before = self.c.status(self.w.sessions["AG0"])
        process, _ = self.launch(request, "AG2", "submit", point="after_candidate_insert")
        self.collect(process, 91)
        self.assertEqual(self.c.status(self.w.sessions["AG0"]), before)
        self.assertEqual(self.c.operation(self.w.sessions["AG0"], request["operation_id"])["status"], "not_committed")
        self.assertEqual(self.c.recover(self.w.sessions["AG0"])["integrity"], "ok")
        self.assertEqual(self.c.execute(self.w.sessions["AG2"], "submit", request)["ref"]["revision"], 2)
        self.observations.append({"scenario": "exit_after_candidate_insert", "exit_code": 91, "old_pointer_preserved": True})

    def test_process_exit_mid_bundle_rolls_back_all_pointers_and_events(self):
        targets, owners = [], []
        for name in ("one", "two"):
            self.seed(name)
            target = self.w.candidate(name)["ref"]
            targets.append(target)
            owners.append(self.w.confirm(target))
        request = self.w.request(bundle_id="crash-bundle", members=[{"ref": r, "scope": ["whole"], "intended_use": "teaching", "receipt_ids": [o]}
                                                                  for r, o in zip(targets, owners)])
        before = self.c.status(self.w.sessions["AG0"])
        cursor = self.c.events(self.w.sessions["AG0"])["next_sequence"]
        process, _ = self.launch(request, "AG0", "adopt", point="after_pointer_write")
        self.collect(process, 91)
        self.assertEqual(self.c.status(self.w.sessions["AG0"]), before)
        self.assertEqual(self.c.events(self.w.sessions["AG0"], after_sequence=cursor)["events"], [])
        self.assertEqual(self.c.execute(self.w.sessions["AG0"], "adopt", request)["status"], "committed")
        self.observations.append({"scenario": "exit_mid_bundle", "exit_code": 91, "partial_publication": False})

    def test_commit_success_with_lost_ack_replays_receipt_without_duplicate_event(self):
        self.w.register("task", "source")
        self.w.op("AG2", "start", task_id="task")
        (self.root / "candidate.txt").write_text("Fabricated complete candidate", encoding="utf-8")
        request = self.w.request(task_id="task", path="candidate.txt", changed_scope=None)
        cursor = self.c.events(self.w.sessions["AG0"])["next_sequence"]
        process, _ = self.launch(request, "AG2", "submit", point="after_commit")
        self.collect(process, 91)
        receipt = self.c.operation(self.w.sessions["AG0"], request["operation_id"])["receipt"]
        revision = self.c.status(self.w.sessions["AG0"])["state_revision"]
        self.assertEqual(self.c.execute(self.w.sessions["AG2"], "submit", request), receipt)
        self.assertEqual(self.c.status(self.w.sessions["AG0"])["state_revision"], revision)
        self.assertEqual(len(self.c.events(self.w.sessions["AG0"], after_sequence=cursor)["events"]), 1)
        self.observations.append({"scenario": "lost_ack_after_commit", "exit_code": 91, "logical_commits": 1})

    def test_before_commit_exit_does_not_publish_transactional_event(self):
        request = self.w.request(id="task", assignee="AG2", task_kind="production", scope=["whole"], intended_use="teaching", inputs=[],
                                 output={"id": "source", "type": "MaterialUse", "requires_ag3_review": False})
        process, _ = self.launch(request, "AG0", "register", point="before_commit")
        self.collect(process, 91)
        self.assertEqual(self.c.status(self.w.sessions["AG0"])["tasks"], [])
        self.assertEqual(self.c.events(self.w.sessions["AG0"])["events"], [])
        self.assertEqual(self.c.execute(self.w.sessions["AG0"], "register", request)["status"], "committed")

    def test_recovery_lists_unregistered_files_and_preserves_running_tasks(self):
        self.w.register("task", "source")
        self.w.op("AG2", "start", task_id="task")
        (self.root / "staging").mkdir()
        path = self.root / "staging/orphan.txt"
        path.write_text("Fabricated incomplete candidate", encoding="utf-8")
        before = path.read_bytes()
        report = self.c.recover(self.w.sessions["AG0"], scan_roots=["staging"])
        self.assertEqual(report["unregistered_files"], ["staging/orphan.txt"])
        self.assertEqual(report["running_task_ids"], ["task"])
        self.assertFalse(report["automatic_file_deletion"])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.task("task")["phase"], "running")

    def test_recovery_reports_missing_registered_source_without_rebuilding_it(self):
        target, _ = self.seed()
        artifact = self.c.status(self.w.sessions["AG0"])["artifacts"][0]
        (self.root / artifact["path"]).unlink()
        report = self.c.recover(self.w.sessions["AG0"])
        self.assertEqual(report["artifact_issues"], [{"ref": target, "reason": "artifact_file_unavailable"}])
        self.assertFalse((self.root / artifact["path"]).exists())

    def test_legacy_workspace_is_readable_and_requires_explicit_upgrade_to_mutate(self):
        legacy = Workflow(self.root / "legacy")
        target = legacy.candidate("source")["ref"]
        owner = legacy.confirm(target)
        legacy.adopt(target, [owner])
        c = ReliableCoordinator(legacy.root)
        session = c.bind_local_operator("AG0")
        before = c.status(session)
        self.assertTrue(before["reliability_upgrade_required"])
        upgrade = {"operation_id": "upgrade", "expected_state_revision": before["state_revision"]}
        self.assertEqual(c.execute(session, "upgrade", upgrade)["status"], "committed")
        self.assertEqual(c.status(session)["adopted_pointers"], before["adopted_pointers"])
        self.assertEqual(c.execute(session, "upgrade", upgrade)["status"], "committed")
        self.assertEqual(len(c.events(session)["events"]), 1)
        with self.assertRaisesRegex(GateError, "legacy_operation_requires_original_request"):
            c.operation(session, legacy.trace[0]["request"]["operation_id"])

    def test_upgrade_process_exit_rolls_back_extensions_without_losing_legacy_data(self):
        # A legacy fixture lives in a separate root, never in the recorded batch-two output.
        legacy = Workflow(self.root / "legacy")
        target = legacy.candidate("source")["ref"]
        owner = legacy.confirm(target)
        legacy.adopt(target, [owner])
        before = legacy.coordinator.status(legacy.sessions["AG0"])
        request_path = legacy.root / "upgrade-request.json"
        request = {"operation_id": "upgrade", "expected_state_revision": before["state_revision"]}
        request_path.write_text(json.dumps(request), encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SUITE / "scripts/coordinator_fault_worker.py"),
                                 "--workspace", str(legacy.root), "--request", str(request_path), "--role", "AG0", "--action", "upgrade",
                                 "--failpoint", "before_extension_commit"], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 91)
        c = ReliableCoordinator(legacy.root)
        session = c.bind_local_operator("AG0")
        self.assertTrue(c.status(session)["reliability_upgrade_required"])
        self.assertEqual(c.status(session)["adopted_pointers"], before["adopted_pointers"])
        self.assertEqual(c.execute(session, "upgrade", request)["status"], "committed")
        self.observations.append({"scenario": "exit_during_upgrade", "exit_code": 91, "legacy_pointer_preserved": True})

    def test_post_commit_error_reports_unknown_instead_of_false_not_saved(self):
        request = self.w.request(id="task", assignee="AG2", task_kind="production", scope=["whole"], intended_use="teaching", inputs=[],
                                 output={"id": "source", "type": "MaterialUse", "requires_ag3_review": False})
        def fault(point):
            if point == "after_commit":
                raise RuntimeError("Fabricated return failure")
        self.c.failpoint = fault
        self.assertEqual(self.c.execute(self.w.sessions["AG0"], "register", request)["status"], "commit_status_unknown")
        self.c.failpoint = None
        self.assertEqual(self.c.operation(self.w.sessions["AG0"], request["operation_id"])["status"], "committed")

    def test_failure_propagates_through_wait_chain_in_same_commit(self):
        self.wait_task(name="z-middle")
        self.w.op("AG0", "register", id="a-tail", assignee="AG2", task_kind="production", scope=["whole"], intended_use="teaching",
                  output={"id": "tail-output", "type": "MaterialUse", "requires_ag3_review": False},
                  inputs=[{"id": "z-middle-output", "policy": "after_task", "producer_task_id": "z-middle", "scope": ["whole"], "intended_use": "teaching"}],
                  wait_timeout_ms=500)
        self.w.op("AG2", "start", task_id="a-tail")
        self.w.op("AG2", "finish", task_id="producer", phase="failed", reason="Fabricated upstream failure")
        self.assertEqual(self.task("z-middle")["phase"], "blocked")
        self.assertEqual(self.task("a-tail")["phase"], "blocked")
        events = self.c.events(self.w.sessions["AG0"])["events"]
        self.assertTrue(any(e["kind"] == "wait_blocked" and e["task_id"] == "a-tail" for e in events))

    def test_concurrent_reader_never_sees_half_published_bundle(self):
        targets, owners = [], []
        for name in ("one", "two"):
            self.seed(name)
            target = self.w.candidate(name)["ref"]
            targets.append(target)
            owners.append(self.w.confirm(target))
        request = self.w.request(bundle_id="reader-bundle", members=[{"ref": r, "scope": ["whole"], "intended_use": "teaching", "receipt_ids": [o]}
                                                                  for r, o in zip(targets, owners)])
        path = self.root / "reader-request.json"
        path.write_text(json.dumps(request), encoding="utf-8")
        marker, resume = self.root / "pointer-paused", self.root / "resume"
        process = subprocess.Popen([sys.executable, "-B", "-X", "utf8", str(SUITE / "scripts/coordinator_fault_worker.py"),
                                    "--workspace", str(self.root), "--request", str(path), "--role", "AG0", "--action", "adopt",
                                    "--pause-at", "after_pointer_write", "--pause-marker", str(marker), "--resume", str(resume)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        def reap():
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)
        self.addCleanup(reap)
        deadline = time.monotonic() + 15
        while not marker.exists():
            if time.monotonic() >= deadline:
                self.fail("Writer did not reach pointer checkpoint")
            time.sleep(.01)
        during = self.c.status(self.w.sessions["AG0"])["adopted_pointers"]
        self.assertEqual([p["revision"] for p in during], [1, 1])
        resume.write_text("resume", encoding="ascii")
        self.assertEqual(self.collect(process)["result"]["status"], "committed")
        after = self.c.status(self.w.sessions["AG0"])["adopted_pointers"]
        self.assertEqual([p["revision"] for p in after], [2, 2])
        self.observations.append({"scenario": "reader_during_bundle", "during_revisions": [1, 1], "after_revisions": [2, 2]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
