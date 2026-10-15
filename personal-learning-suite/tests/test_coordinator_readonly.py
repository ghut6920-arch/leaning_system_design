"""Live SQLite lock regression using fabricated preparation, without models."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
sys.path.insert(0, str(SUITE / "scripts"))
from coordinator.agent_api import AgentCoordinator
from coordinator.complete import TaskArtifactCoordinator
from coordinator.delivery import verify_delivery
from coordinator.preparation_sources import build_map
from coordinator.workspace import GateError, sha
import coordinate_agents
from test_coordinator_complete import CompleteWorkflow


class ReadOnlyCoordinatorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="coordinator-readonly-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.control = {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []}
        self.w = CompleteWorkflow(self.root, lambda: deepcopy(self.control))
        self.c = self.w.coordinator
        self.api = AgentCoordinator(self.c)
        self.call("AG0", {"action": "assign", "task": "material", "output": {"id": "material-output", "type": "MaterialUse", "validation": "preparation_sources"},
                          "scope": ["whole"], "use": "teaching", "inputs": [], "review_required": False})
        self.call("AG2", {"action": "begin", "task": "material"})
        members = []
        for key, kind, path, text in [
            ("task", "formal_task", "questions/fake/task.md", "A fictional complete task."),
            ("lesson", "mainline", "materials/fake/lesson.md", "A fictional full lesson."),
            ("reference", "teacher_reference", "materials/fake/reference.md", "完整教师参考及评分依据。"),
            ("report", "material_report", "artifacts/fake/report.md", "A fictional specific material report.")]:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            members.append({"id": key, "kind": kind, "path": path})
        manifest = build_map(self.c, self.w.sessions["AG2"], "material", members)
        (self.root / "artifacts/sources.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        self.call("AG2", {"action": "deliver", "task": "material", "path": "artifacts/sources.json"})
        self.call("AG2", {"action": "opinion", "task": "material", "outcome": "supported", "rationale": "Checked the exact fictional material."})
        self.call("AG0", {"action": "assign_readback", "task": "readback", "from_task": "material",
                          "output": {"id": "readback-output", "type": "ActivitySpec", "validation": "utf8"},
                          "scope": ["whole"], "use": "teaching", "review_required": False,
                          "provisional_conditions": "Functional readback only, not adopted teaching."})
        self.call("AG1", {"action": "begin", "task": "readback"})
        self.reader = TaskArtifactCoordinator(self.root, lambda: deepcopy(self.control), lock_timeout=.15)
        self.reader.read_only = True
        self.session = self.reader.bind_local_operator("AG1")

    def call(self, role, intent):
        result = self.api.do(self.w.sessions[role], intent, request_key="readonly-test:" + json.dumps(intent, sort_keys=True))
        self.assertEqual(result["status"], "committed", result)
        return result

    def source(self):
        return self.reader.preparation_source(self.session, "reference", task_id="readback", input_index=0)

    def files(self):
        return {path.relative_to(self.root).as_posix(): sha(path.read_bytes()) for path in self.root.rglob("*") if path.is_file()}

    def test_actual_source_read_survives_pending_writer_and_nested_validation(self):
        """A fresh nested reader deadlocks behind this pending writer; reuse does not."""
        for read_only in (False, True):
            with self.subTest(read_only=read_only):
                self.reader.read_only = read_only
                self.assert_source_with_pending_writer()

    def assert_source_with_pending_writer(self):
        committing, writer_done = threading.Event(), threading.Event()
        writer_errors, pending_proved = [], []
        writer_thread = None

        def writer():
            try:
                with closing(sqlite3.connect(self.c.db_path, timeout=4, isolation_level=None)) as db:
                    db.execute("BEGIN IMMEDIATE")
                    db.execute("UPDATE meta SET value=value WHERE key='state_revision'")
                    db.set_trace_callback(lambda statement: committing.set() if statement == "COMMIT" else None)
                    db.execute("COMMIT")
            except BaseException as error:
                writer_errors.append(error)
            finally:
                writer_done.set()

        original_verify = self.reader.verify_file
        def verify_while_writer_pending(artifact):
            nonlocal writer_thread
            if writer_thread is None:
                writer_thread = threading.Thread(target=writer)
                writer_thread.start()
                self.assertTrue(committing.wait(1), "writer did not reach COMMIT")
                deadline = time.monotonic() + 1
                while time.monotonic() < deadline:
                    probe = sqlite3.connect(self.c.db_path.as_uri() + "?mode=ro", uri=True, timeout=.01)
                    try:
                        probe.execute("SELECT value FROM meta LIMIT 1").fetchone()
                    except sqlite3.OperationalError as error:
                        if "locked" in str(error).lower():
                            pending_proved.append(True)
                            break
                        raise
                    finally:
                        probe.close()
                self.assertTrue(pending_proved, "writer must block a fresh reader before nested validation")
                self.assertFalse(writer_done.is_set(), "writer must still wait for the outer actual source read")
            return original_verify(artifact)

        with patch.object(self.reader, "verify_file", side_effect=verify_while_writer_pending):
            item = self.source()
        writer_thread.join(5)
        self.assertTrue(writer_done.is_set())
        self.assertEqual(writer_errors, [])
        self.assertEqual(item["content"], "完整教师参考及评分依据。".encode("utf-8"))
        self.assertEqual(item["ref"], {"id": "material-output", "revision": 1})

    def test_readonly_views_preserve_all_files_controls_and_member_hash_checks(self):
        before = self.files()
        self.source()
        self.reader.status(self.reader.bind_local_operator("AG0"))
        AgentCoordinator(self.reader).alerts(self.session, "readonly-observer")
        self.assertEqual(self.files(), before)
        self.control["paused_ids"] = ["material-output"]
        with self.assertRaisesRegex(GateError, "paused_scope"):
            self.source()
        self.control["paused_ids"] = []
        (self.root / "materials/fake/reference.md").write_text("Changed bytes.", encoding="utf-8")
        with self.assertRaisesRegex(GateError, "preparation_source_fingerprint_changed"):
            self.source()

    def test_sqlite_uri_and_query_only_both_enforce_readonly(self):
        with self.reader.connect() as db:
            self.assertEqual(db.execute("PRAGMA query_only").fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("UPDATE meta SET value='999' WHERE key='state_revision'")
            # Even if application code disables query_only, mode=ro still wins.
            db.execute("PRAGMA query_only=OFF")
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("UPDATE meta SET value='999' WHERE key='state_revision'")

    def test_nested_read_handles_reuse_only_within_one_thread(self):
        barrier = threading.Barrier(2)
        def read_thread():
            with self.reader.connect() as outer:
                outer.execute("BEGIN")
                outer.execute("SELECT value FROM meta LIMIT 1").fetchone()
                with self.reader.connect() as inner:
                    self.assertIs(inner, outer)
                    barrier.wait(timeout=2)
                    return outer
        with ThreadPoolExecutor(max_workers=2) as executor:
            first, second = [future.result(timeout=4) for future in [executor.submit(read_thread), executor.submit(read_thread)]]
        self.assertIsNot(first, second)
        with self.reader.connect() as fresh:
            self.assertIsNot(fresh, first)
            self.assertIsNot(fresh, second)
        with self.c.connect() as outer, self.c.connect() as independent:
            self.assertIsNot(outer, independent)
            self.assertEqual(outer.execute("PRAGMA query_only").fetchone()[0], 0)
            with self.c.validation_connection() as validation:
                self.assertIs(validation, independent)
        with self.c.connect() as outer:
            with self.c.connect() as independent:
                with self.c.validation_connection() as validation:
                    self.assertIs(validation, independent)
            with self.c.validation_connection() as validation:
                self.assertIs(validation, outer)

    def test_cli_selects_readonly_storage_for_actual_source_command(self):
        before = self.files()
        opened = []
        original_connect = sqlite3.connect
        def connect(*args, **kwargs):
            opened.append((args[0], kwargs.get("uri")))
            return original_connect(*args, **kwargs)
        output = io.StringIO()
        with patch("coordinator.workspace.sqlite3.connect", side_effect=connect), redirect_stdout(output):
            code = coordinate_agents.main(["--workspace", str(self.root), "--role", "AG1", "inputs", "--task", "readback", "--input", "0", "--source", "reference", "--view", "text"])
        self.assertEqual(code, 0, output.getvalue())
        result = verify_delivery(output.getvalue().encode("utf-8"))
        self.assertEqual(result["inputs"][0]["text"], "完整教师参考及评分依据。")
        self.assertTrue(opened)
        self.assertTrue(all(str(path).endswith("?mode=ro") and uri is True for path, uri in opened), opened)
        self.assertEqual(self.files(), before)


if __name__ == "__main__":
    unittest.main()
