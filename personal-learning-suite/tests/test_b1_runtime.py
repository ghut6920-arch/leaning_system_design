"""B1 的真实存储行为测试；所有记录来自人工夹具，工作区用 tempfile 隔离。

这里只覆盖 B10-05/06/08/12 与 N-B0-03 的存储、控制、恢复有限切片。
通过不代表教学正确、专业结论正确、宿主身份绑定或完整 B10 情境通过。
"""
from __future__ import annotations

import copy
import gc
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from runtime.learning_store import LearningStore
from runtime.personal_learning import PersonalLearningEntry


def fixture():
    snapshot = json.loads((ROOT / "fixtures/synthetic-baseline.json").read_text(encoding="utf-8-sig"))
    snapshot["synthetic_only"] = True
    originals = (ROOT / "fixtures/originals.md").read_text(encoding="utf-8-sig")
    return snapshot, {"originals.md": originals}


def objects_by_id(context):
    return {obj["id"]: obj for obj in context["objects"]}


def rewrite_independent(value):
    """独立复制完整关系网，既没有共享 ObjectRef，也没有共享原件路径。"""
    if isinstance(value, str):
        if value == "originals.md":
            return "unrelated-originals.md"
        return value.replace("FIX-", "FIX-unrelated-").replace("originals.md#", "unrelated-originals.md#")
    if isinstance(value, list):
        return [rewrite_independent(item) for item in value]
    if isinstance(value, dict):
        return {key: rewrite_independent(item) for key, item in value.items()}
    return value


class B1RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pl-b1-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        self.snapshot, self.artifacts = fixture()
        self.store = self.open_seeded(self.snapshot, self.artifacts)

    def open_seeded(self, snapshot, artifacts, name="workspace"):
        root = Path(self.temp.name) / name
        store = LearningStore(root)
        store.init_workspace()
        result = store.import_fixture(snapshot, artifacts)
        self.assertEqual(result["status"], "committed", "人工夹具初始化必须实际保存成功")
        self.assertEqual(result["state_revision"], 1)
        return store

    def context(self, store=None):
        result = (store or self.store).read_context()
        self.assertEqual(result["status"], "ok")
        return result

    def revision(self, store=None):
        return self.context(store)["state_revision"]

    def updated(self, object_id, store=None):
        obj = copy.deepcopy(objects_by_id(self.context(store))[object_id])
        obj["revision"] += 1
        return obj

    def commit(self, changes, operation="FIX-test-operation", store=None, **kwargs):
        store = store or self.store
        return store.commit(
            expected_state_revision=self.revision(store),
            operation_id=operation,
            changes=changes,
            **kwargs,
        )

    def assert_rejected(self, result):
        self.assertEqual(result["status"], "rejected")

    def database(self, store=None):
        root = Path(getattr(store or self.store, "root", self.root))
        candidates = list(root.rglob("*.sqlite3")) + list(root.rglob("*.sqlite")) + list(root.rglob("*.db"))
        self.assertEqual(len(candidates), 1, "B1 使用一份 SQLite 数据库保存对象与原件")
        return candidates[0]

    def database_dump(self, store=None):
        db = sqlite3.connect(self.database(store))
        try:
            return "\n".join(db.iterdump())
        finally:
            db.close()

    def test_init_fixture_bootstrap_cannot_overwrite_live_state(self):
        result = self.store.import_fixture(self.snapshot, self.artifacts)
        self.assert_rejected(result)
        self.assertEqual(self.revision(), 1)
        self.assertEqual(len(self.context()["objects"]), len(self.snapshot["objects"]))

    def test_save_destroy_store_and_reopen_preserves_originals_and_objects(self):
        changed = self.updated("FIX-event")
        changed["timeline"][-1]["content"] = "FIX-PERSISTENCE-MARKER"
        result = self.commit([changed])
        self.assertEqual(result["status"], "committed")
        expected_revision = result["state_revision"]
        self.store = None
        gc.collect()
        reopened = LearningStore(self.root)
        context = self.context(reopened)
        self.assertEqual(context["state_revision"], expected_revision)
        self.assertEqual(objects_by_id(context)["FIX-event"]["revision"], 2)
        export = reopened.export_scope(["FIX-event"], include_artifacts=True)
        self.assertEqual(export["status"], "ok")
        self.assertTrue(export["artifacts"].get("originals.md") == self.artifacts["originals.md"], "导出应含同一DB实际保存的完整原件")

    def test_synthetic_only_rejects_real_fixture(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["synthetic_only"] = False
        root = Path(self.temp.name) / "real-rejected"
        store = LearningStore(root)
        store.init_workspace()
        self.assert_rejected(store.import_fixture(snapshot, self.artifacts))
        self.assertEqual(self.revision(store), 0)

    def test_fixture_actor_is_reported_as_test_configuration(self):
        capabilities = self.context()["capabilities"]
        self.assertFalse(capabilities["host_identity_bound"])
        self.assertFalse(capabilities["output_interception_bound"])
        self.assertTrue(capabilities["entry_actor_is_test_config"])

    def test_state_revision_cas_rejects_stale_commit_without_write(self):
        expected = self.revision()
        first = self.updated("FIX-event")
        self.assertEqual(self.commit([first], "FIX-first")["status"], "committed")
        stale = self.updated("FIX-checkpoint")
        stale["next_connection"] = "FIX-STALE-PAYLOAD"
        result = self.store.commit(expected, "FIX-stale", [stale])
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(objects_by_id(self.context())["FIX-checkpoint"]["revision"], 1)
        self.assertNotIn("FIX-STALE-PAYLOAD", self.database_dump())

    def test_same_operation_same_payload_is_idempotent(self):
        expected = self.revision()
        changed = self.updated("FIX-event")
        first = self.store.commit(expected, "FIX-idempotent", [changed])
        second = self.store.commit(expected, "FIX-idempotent", copy.deepcopy([changed]))
        self.assertEqual(first["status"], "committed")
        self.assertEqual(second["status"], "committed")
        self.assertEqual(first["state_revision"], second["state_revision"])
        self.assertEqual(self.revision(), first["state_revision"])
        self.assertEqual(len([o for o in self.context()["objects"] if o["id"] == "FIX-event"]), 1)

    def test_same_operation_different_payload_is_rejected(self):
        expected = self.revision()
        changed = self.updated("FIX-event")
        first = self.store.commit(expected, "FIX-idempotent", [changed])
        changed["timeline"][-1]["content"] = "FIX-OP-MISMATCH"
        result = self.store.commit(expected, "FIX-idempotent", [changed])
        self.assertEqual(first["status"], "committed")
        self.assert_rejected(result)
        self.assertNotIn("FIX-OP-MISMATCH", self.database_dump())

    def test_ag0_cannot_write_goal_owned_by_ag1(self):
        goal = self.updated("FIX-goal")
        goal["requirements"][0]["criterion"]["text"] = "FIX-UNAUTHORIZED-GOAL"
        before = self.revision()
        self.assert_rejected(self.commit([goal], authorization_refs=[{"id": "FIX-user-grant", "revision": 1}]))
        self.assertEqual(self.revision(), before)
        self.assertNotIn("FIX-UNAUTHORIZED-GOAL", self.database_dump())

    def test_ag0_cannot_turn_routine_grant_into_professional_review(self):
        judgment = self.updated("FIX-judgment")
        judgment["decision_type"] = "professional_review"
        before = self.revision()
        self.assert_rejected(self.commit([judgment], authorization_refs=[{"id": "FIX-scoring-grant", "revision": 1}]))
        self.assertEqual(self.revision(), before)

    def test_authorized_routine_judgment_can_persist_without_expanding_conclusion(self):
        judgment = self.updated("FIX-judgment")
        judgment["rationale"] = "FIX-LIMITED-ROUTINE-REVIEW"
        grant = {"id": "FIX-scoring-grant", "revision": 1}
        result = self.commit([judgment], "FIX-routine-update", authorization_refs=[grant], adoption_refs=[grant])
        self.assertEqual(result["status"], "committed", "合法常规授权范围应可以写入有限判断")
        stored = objects_by_id(self.context())["FIX-judgment"]
        self.assertEqual(stored["revision"], 2)
        self.assertEqual(stored["decision_type"], "routine_scoring")
        self.assertTrue(stored["unsupported_scope"], "有限支持不能消除原有未支持范围")

    def test_grant_does_not_cover_new_event_scope(self):
        event = copy.deepcopy(objects_by_id(self.context())["FIX-event"])
        event["id"] = "FIX-new-event"
        event["revision"] = 1
        event["independent_sample_id"] = "FIX-new-sample"
        judgment = copy.deepcopy(objects_by_id(self.context())["FIX-judgment"])
        judgment["id"] = "FIX-new-judgment"
        judgment["revision"] = 1
        judgment["event_refs"] = [{"id": "FIX-new-event", "revision": 1}]
        judgment["basis_refs"][0] = {"id": "FIX-new-event", "revision": 1}
        self.assert_rejected(self.commit([event, judgment], authorization_refs=[{"id": "FIX-scoring-grant", "revision": 1}]))
        self.assertNotIn("FIX-new-event", objects_by_id(self.context()))

    def test_candidate_is_not_adopted_basis(self):
        result = objects_by_id(self.context())["FIX-result"]
        self.assertEqual(result["adoption"]["status"], "candidate")
        plan = self.updated("FIX-plan")
        plan["adopted_basis_refs"] = [{"id": "FIX-result", "revision": 1}]
        ag1 = LearningStore(self.root, entry_actor="AG1")
        self.assert_rejected(self.commit([plan], store=ag1, authorization_refs=[{"id": "FIX-user-grant", "revision": 1}]))
        self.assertEqual(objects_by_id(self.context())["FIX-result"]["adoption"]["status"], "candidate")

    def test_pause_immediately_blocks_related_commit_but_allows_read(self):
        result = self.store.pause(self.revision(), "FIX-pause", ["FIX-activity"], "fixture pause")
        self.assertEqual(result["status"], "committed")
        event = self.updated("FIX-event")
        event["timeline"][-1]["content"] = "FIX-PAUSED-PAYLOAD"
        self.assert_rejected(self.commit([event]))
        self.assertEqual(self.context()["status"], "ok")
        self.assertNotIn("FIX-PAUSED-PAYLOAD", self.database_dump())

    def test_pause_keeps_confirmed_independent_scope_writable(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["objects"].extend(rewrite_independent(copy.deepcopy(snapshot["objects"])))
        artifacts = dict(self.artifacts, **{"unrelated-originals.md": self.artifacts["originals.md"]})
        store = self.open_seeded(snapshot, artifacts, "independent-control")
        result = store.pause(self.revision(store), "FIX-local-pause", ["FIX-event"], "fixture local pause")
        self.assertEqual(result["status"], "committed")
        related = self.updated("FIX-event", store)
        self.assert_rejected(self.commit([related], "FIX-related-paused", store))
        independent = self.updated("FIX-unrelated-event", store)
        result = self.commit([independent], "FIX-independent-write", store)
        self.assertEqual(result["status"], "committed")

    def test_resume_preserves_professional_use_restriction(self):
        professional = LearningStore(self.root, entry_actor="AG3")
        result = professional.restrict(self.revision(), "FIX-professional-limit", ["FIX-goal"], "fixture professional restriction", intended_uses=["important_skip"])
        self.assertEqual(result["status"], "committed")
        self.store.pause(self.revision(), "FIX-pause", ["FIX-goal"], "fixture pause")
        result = self.store.resume(self.revision(), "FIX-resume", ["FIX-goal"])
        self.assertEqual(result["status"], "committed")
        active = self.context()["controls"]["restrictions"]
        self.assertTrue(any(r.get("issued_by") == "AG3" and r.get("scope_id") == "FIX-goal" for r in active))
        self.assert_rejected(self.store.validate_refs([{"id": "FIX-goal", "revision": 1}], "important_skip"))

    def test_original_artifact_cannot_be_overwritten_in_place(self):
        before = self.revision()
        self.assert_rejected(self.commit([], artifacts={"originals.md": "FIX-OVERWRITE"}))
        self.assertEqual(self.revision(), before)
        exported = self.store.export_scope(["FIX-event"], include_artifacts=True)
        self.assertTrue(exported["artifacts"].get("originals.md") == self.artifacts["originals.md"])

    def test_unreferenced_artifact_cannot_bypass_scope_ownership(self):
        before = self.revision()
        result = self.commit([], "FIX-orphan-artifact", artifacts={"unowned.md": "FIX-ORPHAN-CONTENT"})
        self.assert_rejected(result)
        self.assertEqual(self.revision(), before)
        self.assertNotIn("FIX-ORPHAN-CONTENT", self.database_dump())

    def test_path_traversal_and_absolute_artifact_paths_are_rejected(self):
        for index, path in enumerate(("../escape.md", "..\\escape.md", str(Path(self.temp.name) / "outside.md"), "C:\\fixture-escape.md")):
            with self.subTest(path_kind=index):
                before = self.revision()
                result = self.commit([], "FIX-unsafe-path-" + str(index), artifacts={path: "FIX-ESCAPE"})
                self.assert_rejected(result)
                self.assertEqual(self.revision(), before)
        self.assertFalse((Path(self.temp.name) / "outside.md").exists())
        self.assertNotIn("FIX-ESCAPE", self.database_dump())

    def test_missing_artifact_and_unknown_reference_do_not_save(self):
        event = self.updated("FIX-event")
        event["original_response"]["path"] = "missing-original.md"
        self.assert_rejected(self.commit([event], "FIX-missing-artifact"))
        event = self.updated("FIX-event")
        event["activity_ref"] = {"id": "FIX-absent", "revision": 1}
        self.assert_rejected(self.commit([event], "FIX-unknown-reference"))
        self.assertEqual(self.revision(), 1)

    def test_failure_after_sql_write_rolls_back_objects_artifacts_and_receipt(self):
        changed = self.updated("FIX-event")
        changed["timeline"][-1]["content"] = "FIX-FAILURE-MARKER"
        changed["original_response"]["path"] = "new-original.md"
        expected = self.revision()

        def injected(stage):
            if stage == "after_write":
                raise RuntimeError("synthetic failpoint")

        self.store.failpoint = injected
        result = self.store.commit(expected, "FIX-failed-commit", [changed], artifacts={"new-original.md": self.artifacts["originals.md"]})
        self.assertEqual(result["status"], "not_saved")
        self.store.failpoint = None
        reopened = LearningStore(self.root)
        self.assertEqual(self.revision(reopened), expected)
        self.assertNotIn("FIX-FAILURE-MARKER", self.database_dump(reopened))
        self.assertNotIn("new-original.md", self.database_dump(reopened))
        result = reopened.commit(expected, "FIX-failed-commit", [changed], artifacts={"new-original.md": self.artifacts["originals.md"]})
        self.assertEqual(result["status"], "committed", "回滚不得留下阻止正确重试的成功回执")
        self.assertEqual(reopened.check_integrity()["status"], "ok")

    def test_two_concurrent_connections_get_one_cas_winner(self):
        expected = self.revision()
        changes = [self.updated("FIX-event"), self.updated("FIX-checkpoint")]
        barrier = threading.Barrier(2)
        results, errors = [], []
        result_lock = threading.Lock()

        def write(index):
            store = LearningStore(self.root)
            try:
                barrier.wait(timeout=10)
                result = store.commit(expected, "FIX-parallel-" + str(index), [changes[index]])
                with result_lock:
                    results.append(result)
            except Exception as error:
                with result_lock:
                    errors.append(type(error).__name__)

        threads = [threading.Thread(target=write, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertFalse(any(thread.is_alive() for thread in threads), "有限并发应在超时内结束")
        self.assertEqual(errors, [])
        self.assertEqual(sorted(result["status"] for result in results), ["committed", "conflict"])
        self.assertEqual(self.revision(), expected + 1)
        self.assertEqual(self.store.check_integrity()["status"], "ok")

    def test_delete_cleans_histories_originals_summary_candidate_validation_and_keeps_unrelated(self):
        snapshot = copy.deepcopy(self.snapshot)
        unrelated = rewrite_independent(copy.deepcopy(snapshot["objects"]))
        snapshot["objects"].extend(unrelated)
        by_id = {obj["id"]: obj for obj in snapshot["objects"]}
        by_id["FIX-event"]["timeline"][-1]["content"] = "FIX-DELETE-EVENT-A"
        by_id["FIX-checkpoint"]["next_connection"] = "FIX-DELETE-SUMMARY-A"
        by_id["FIX-result"]["handled_scope"] = "FIX-DELETE-CANDIDATE-A"
        by_id["FIX-validation"]["basis_refs"] = [{"id": "FIX-event", "revision": 1}]
        by_id["FIX-validation"]["decision"] = "FIX-DELETE-VALIDATION-A"
        artifacts = copy.deepcopy(self.artifacts)
        artifacts["originals.md"] += "\nFIX-DELETE-ORIGINAL-A\n"
        artifacts["unrelated-originals.md"] = self.artifacts["originals.md"] + "\nFIX-KEEP-UNRELATED-B\n"
        store = self.open_seeded(snapshot, artifacts, "deletion")
        changed = self.updated("FIX-event", store)
        changed["timeline"][-1]["content"] = "FIX-DELETE-HISTORY-A"
        self.assertEqual(self.commit([changed], "FIX-history-A", store)["status"], "committed")
        unrelated_revision = self.revision(store)
        unrelated_change = self.updated("FIX-unrelated-event", store)
        unrelated_change["timeline"][-1]["content"] = "FIX-KEEP-UNRELATED-RECEIPT-B"
        self.assertEqual(store.commit(unrelated_revision, "FIX-independent-operation", [unrelated_change])["status"], "committed")
        result = store.delete_scope(self.revision(store), "FIX-delete-A", ["FIX-event"], include_indexes=True)
        self.assertEqual(result["status"], "committed")
        self.assertTrue(result["professional_review_required"])
        self.assertIn("external_backups", result["uncontrollable"])
        context = self.context(store)
        surviving = objects_by_id(context)
        for object_id in ("FIX-event", "FIX-checkpoint", "FIX-result", "FIX-validation"):
            self.assertNotIn(object_id, surviving)
        self.assertTrue("FIX-unrelated-event" in surviving, "确认独立的范围不得被一并删除")
        dump = self.database_dump(store)
        for marker in ("FIX-DELETE-EVENT-A", "FIX-DELETE-SUMMARY-A", "FIX-DELETE-CANDIDATE-A", "FIX-DELETE-VALIDATION-A", "FIX-DELETE-ORIGINAL-A", "FIX-DELETE-HISTORY-A", "FIX-history-A", "FIX-delete-A", "FIX-event", "FIX-checkpoint", "FIX-result", "FIX-validation"):
            self.assertNotIn(marker, dump)
        for path in self.database(store).parent.rglob("*"):
            if path.is_file():
                raw = path.read_bytes()
                for marker in (b"FIX-DELETE-ORIGINAL-A", b"FIX-DELETE-HISTORY-A", b"FIX-DELETE-CANDIDATE-A"):
                    self.assertNotIn(marker, raw, "可控数据库/临时文件不得留下被删正文")
        export = store.export_scope(["FIX-unrelated-event"], include_artifacts=True)
        self.assertEqual(export["status"], "ok")
        self.assertIn("FIX-KEEP-UNRELATED-B", export["artifacts"].get("unrelated-originals.md", ""))
        self.assertEqual(store.commit(unrelated_revision, "FIX-independent-operation", [unrelated_change])["status"], "committed", "清理相关回执不应抹掉无关范围的幂等回执")
        self.assertEqual(store.check_integrity()["status"], "ok")

    def test_late_deleted_payload_is_rejected_before_payload_can_land(self):
        late = self.updated("FIX-event")
        late["timeline"][-1]["content"] = "FIX-LATE-DELETED-CONTENT"
        late["original_response"]["path"] = "late-original.md"
        result = self.store.delete_scope(self.revision(), "FIX-delete", ["FIX-event"], include_indexes=True)
        self.assertEqual(result["status"], "committed")
        result = self.commit([late], "FIX-late-result", artifacts={"late-original.md": "FIX-LATE-DELETED-CONTENT"})
        self.assert_rejected(result)
        self.assertNotIn("FIX-LATE-DELETED-CONTENT", self.database_dump())
        self.assertNotIn("late-original.md", self.database_dump())

    def test_failed_delete_keeps_durable_gate_after_restart_until_cleanup(self):
        late = self.updated("FIX-event")
        late["timeline"][-1]["content"] = "FIX-FAILED-DELETE-LATE-PAYLOAD"

        def injected(stage):
            if stage == "after_write":
                raise RuntimeError("synthetic deletion failure")

        self.store.failpoint = injected
        result = self.store.delete_scope(self.revision(), "FIX-failed-delete", ["FIX-event"], include_indexes=True)
        self.assertEqual(result["status"], "not_saved")
        reopened = LearningStore(self.root)
        event_ref = {"id": "FIX-event", "revision": 1}
        self.assert_rejected(reopened.validate_refs([event_ref], "read"))
        self.assert_rejected(reopened.read_refs([event_ref], "read"))
        self.assert_rejected(reopened.export_scope(["FIX-event"], include_artifacts=True))
        self.assertNotIn("FIX-event", objects_by_id(self.context(reopened)))
        reopened.resume(self.revision(reopened), "FIX-resume-after-delete-failure", ["FIX-event"])
        self.assert_rejected(reopened.validate_refs([event_ref], "read"))
        self.assert_rejected(self.commit([late], "FIX-late-after-delete-failure", reopened))
        self.assertNotIn("FIX-FAILED-DELETE-LATE-PAYLOAD", self.database_dump(reopened))
        result = reopened.delete_scope(self.revision(reopened), "FIX-failed-delete", ["FIX-event"], include_indexes=True)
        self.assertEqual(result["status"], "committed")
        dump = self.database_dump(reopened)
        self.assertNotIn("FIX-event", dump)
        self.assertNotIn("FIX-failed-delete", dump)
        self.assertEqual(reopened.check_integrity()["status"], "ok")

    def test_export_originals_vs_summary_expresses_review_limit(self):
        full = self.store.export_scope(["FIX-event"], include_artifacts=True)
        summary = self.store.export_scope(["FIX-event"], include_artifacts=False)
        self.assertEqual(full["status"], "ok")
        self.assertEqual(summary["status"], "ok")
        self.assertTrue(full["artifacts"].get("originals.md") == self.artifacts["originals.md"])
        self.assertEqual(summary["artifacts"], {})
        text = json.dumps(summary.get("limitations", []), ensure_ascii=False)
        self.assertTrue(any(term in text for term in ("独立复核", "independent review", "independent_recheck", "cannot independently", "原件")), "仅对象导出必须说明无法靠摘要独立复核原件")

    def test_integrity_checks_after_persisted_state(self):
        self.assertEqual(self.store.check_integrity()["status"], "ok")
        event = self.updated("FIX-event")
        self.assertEqual(self.commit([event])["status"], "committed")
        reopened = LearningStore(self.root)
        report = reopened.check_integrity()
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["issues"], [])

    def test_entry_routes_unimplemented_capabilities_as_candidates(self):
        entry = PersonalLearningEntry(self.store)
        for intent in ("目标", "材料", "教学", "评估", "计划", "策略"):
            with self.subTest(intent=intent):
                result = entry.route(intent)
                self.assertEqual(result["status"], "candidate")
                self.assertEqual(result["readiness"], "not_ready")
                self.assertFalse(result["teaching"])
                self.assertFalse(result["work_order_created"])
        self.assertEqual(self.revision(), 1)

    def test_entry_start_does_not_claim_teaching_ready(self):
        result = PersonalLearningEntry(self.store).start(activity_id="FIX-activity")
        self.assertIn(result["status"], ("needs_input", "not_ready", "blocked"))
        self.assertFalse(result["teaching"])
        self.assertEqual(self.revision(), 1)

    def test_entry_without_summary_recovers_same_parent_and_unknown_actions(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["objects"] = [obj for obj in snapshot["objects"] if obj["id"] not in ("FIX-checkpoint", "FIX-plan")]
        store = self.open_seeded(snapshot, self.artifacts, "no-summary")
        result = PersonalLearningEntry(store).resume(activity_id="FIX-activity")
        recovery = result["recovery"]
        self.assertEqual(recovery["source"], "last_trusted_event")
        self.assertEqual(recovery["last_trusted_event_ref"], {"id": "FIX-event", "revision": 1})
        self.assertEqual(recovery["parent_artifact"]["path"], "originals.md")
        self.assertEqual(recovery["parent_artifact"]["locator"], "虚构父产物")
        self.assertEqual(recovery["unrecorded_actions"]["status"], "unknown")
        self.assertEqual(recovery["help_history"]["status"], "known")
        self.assertEqual([item["kind"] for item in recovery["help_history"]["value"]], ["initial_response", "help", "revision"])
        self.assertFalse(result["teaching"])

    def test_recovery_retains_exact_trusted_historical_revision(self):
        event = self.updated("FIX-event")
        event["timeline"][-1]["content"] = "FIX-LATER-EVENT-REVISION"
        self.assertEqual(self.commit([event], "FIX-later-event")["status"], "committed")
        result = PersonalLearningEntry(LearningStore(self.root)).resume(activity_id="FIX-activity")
        recovery = result["recovery"]
        self.assertEqual(recovery["source"], "checkpoint")
        self.assertEqual(recovery["last_trusted_event_ref"], {"id": "FIX-event", "revision": 1})
        self.assertEqual(recovery["help_history"]["status"], "known")
        self.assertNotIn("FIX-LATER-EVENT-REVISION", json.dumps(recovery["help_history"], ensure_ascii=False))
        self.assertFalse(result["teaching"])

    def test_recovery_absent_help_record_keeps_unrecorded_help_unknown(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["objects"] = [obj for obj in snapshot["objects"] if obj["id"] not in ("FIX-checkpoint", "FIX-plan")]
        event = next(obj for obj in snapshot["objects"] if obj["id"] == "FIX-event")
        event["timeline"] = event["timeline"][:1]
        event["revisions"] = []
        event["contributors"] = event["contributors"][:1]
        event["actual_resources"] = {"status": "unknown", "reason": "fixture history absent"}
        store = self.open_seeded(snapshot, self.artifacts, "no-help-record")
        recovery = PersonalLearningEntry(store).resume(activity_id="FIX-activity")["recovery"]
        self.assertEqual(recovery["unrecorded_actions"]["status"], "unknown")
        self.assertTrue(any(term in json.dumps(recovery["help_history"], ensure_ascii=False) for term in ("未知", "unknown")), "没有帮助条目不能解释成确定未帮助")
        self.assertFalse(recovery["new_test_created"])

    def test_recovery_unknown_budget_is_not_zero(self):
        result = PersonalLearningEntry(self.store).resume(activity_id="FIX-activity")
        budget = result["current_context"]["budget"]
        for field in ("blocked_wait", "system_effort", "fees"):
            self.assertEqual(budget[field]["status"], "unknown")
            self.assertNotIn("value", budget[field])
        self.assertFalse(result["teaching"])

    def test_entry_paused_activity_remains_readable_and_blocked(self):
        self.store.pause(self.revision(), "FIX-pause-entry", ["FIX-activity"], "fixture pause")
        result = PersonalLearningEntry(self.store).resume(activity_id="FIX-activity")
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["teaching"])
        self.assertEqual(self.context()["status"], "ok")


if __name__ == "__main__":
    unittest.main(verbosity=2)
