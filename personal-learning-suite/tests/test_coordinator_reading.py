"""Reading and presentation invariants; all coordinator records are synthetic."""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
sys.path.insert(0, str(SUITE / "scripts"))
from coordinator.agent_api import AgentCoordinator
from coordinator.reading import text_page, verified_view
from coordinator.workspace import GateError
from coordinate_agents import input_view
from read_learning_resource import manifest_view, strategy_document, strategy_payload
from test_coordinator_complete import CompleteWorkflow


class ReadingViewsTests(unittest.TestCase):
    def test_unicode_pages_reconstruct_every_character_and_do_not_claim_full_read(self):
        text = "中文🙂\r\n条件\n" * 30
        offset, joined = 0, ""
        while offset < len(text):
            result = text_page(text, offset=offset, max_chars=17)
            joined += result["text"]
            coverage = result["coverage"]
            self.assertEqual(coverage["start"], offset)
            self.assertFalse(coverage["complete"])
            offset = coverage["end"]
        self.assertEqual(joined, text)
        self.assertFalse(coverage["has_more"])
        self.assertIsNone(coverage["next_offset"])

    def test_invalid_and_empty_page_boundaries(self):
        for options in ({"offset": -1}, {"offset": 4}, {"max_chars": -1}):
            with self.subTest(options=options), self.assertRaises(GateError):
                text_page("abc", **options)
        self.assertTrue(text_page("")["coverage"]["complete"])

    def test_uses_verified_bytes_without_reopening_a_mutable_path(self):
        item = {"ref": {"id": "fixed", "revision": 1}, "path": "not-present.md", "content": "原件🙂".encode()}
        result = verified_view(item, root=Path(tempfile.gettempdir()), view="text")
        self.assertEqual(result["text"], "原件🙂")
        self.assertNotIn("content", result)
        self.assertNotIn("content_base64", result)

    def test_fingerprint_and_expected_version_are_enforced(self):
        with self.assertRaises(GateError):
            verified_view({"path": "x", "content": b"new", "sha256": "bad"}, root=Path("."))
        with self.assertRaises(GateError) as error:
            verified_view({"path": "x", "content": b"new"}, root=Path("."), expected_sha256=hashlib.sha256(b"old").hexdigest())
        self.assertEqual(error.exception.code, "read_version_changed")

    def test_binary_data_is_located_not_injected_as_text(self):
        row = verified_view({"path": "exact.png", "content": b"\x00PNG"}, root=Path(tempfile.gettempdir()), view="text")
        self.assertTrue(Path(row["path"]).is_absolute())
        self.assertNotIn("text", row)
        self.assertIn("sha256", row)

    def test_multiple_inputs_share_the_return_budget_and_have_explicit_continuations(self):
        items = [{"ref": {"id": str(i), "revision": 1}, "path": str(i), "content": ("文" * 12).encode()} for i in range(2)]
        coordinator = SimpleNamespace(root=Path("."), read_snapshot=lambda session, task: items)
        result = input_view(coordinator, None, "task", max_chars=15)
        self.assertEqual(sum(len(row["text"]) for row in result["inputs"]), 15)
        self.assertTrue(result["inputs"][0]["coverage"]["complete"])
        second = result["inputs"][1]
        self.assertEqual(second["coverage"]["next_offset"], 3)
        tail = input_view(coordinator, None, "task", input_index=1, offset=3, expected_sha256=second["sha256"])
        self.assertEqual(second["text"] + tail["inputs"][0]["text"], "文" * 12)
        for options in ({"offset": 3}, {"input_index": 2}):
            with self.assertRaises(GateError):
                input_view(coordinator, None, "task", **options)


class ResourceReadingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="learning-resource-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    @staticmethod
    def restore(value, bodies):
        if isinstance(value, dict):
            if set(value) == {"$full_text"}:
                return bodies[value["$full_text"]]
            return {key: ResourceReadingTests.restore(item, bodies) for key, item in value.items()}
        if isinstance(value, list):
            return [ResourceReadingTests.restore(item, bodies) for item in value]
        return value

    def test_every_field_of_real_complete_packages_survives_conversion(self):
        paths = [SUITE / "resources/strategies" / name for name in (
            "post/retrieve-relation.json", "post/select-method.json", "encoding/S05.json", "encoding/D02.json")]
        files, bodies = strategy_payload(paths)
        for path, file in zip(paths, files):
            original = json.loads(path.read_text(encoding="utf-8-sig"))
            self.assertEqual(self.restore(file["fields"], bodies), original)
            self.assertEqual(file["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_identical_long_bodies_across_packages_are_displayed_once(self):
        body = "这是一份不能被摘要代替的完整正文。\n" * 20
        paths = [self.root / f"strategy-{i}.json" for i in range(2)]
        for path in paths:
            path.write_text(json.dumps({"content_markdown": body, "conditions": [body, True, None], "empty": [], "unknown": {}}), encoding="utf-8")
        files, bodies = strategy_payload(paths)
        self.assertEqual(len(bodies), 1)
        document, sources = strategy_document(paths)
        self.assertEqual(document.count(body), 1)
        self.assertEqual(len(sources), 2)
        self.assertEqual(self.restore(files[0]["fields"], bodies)["unknown"], {})

    def test_ambiguous_json_is_rejected_instead_of_dropping_a_condition(self):
        path = self.root / "duplicate.json"
        path.write_text('{"content_markdown":"x","conditions":["a"],"conditions":["b"]}', encoding="utf-8")
        with self.assertRaises(ValueError):
            strategy_payload([path])

    def test_manifest_display_filter_still_checks_unselected_entries(self):
        paths = [self.root / f"{i}.md" for i in range(2)]
        for path in paths:
            path.write_bytes(b"original")
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"entries": [{"path": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}), encoding="utf-8")
        paths[1].write_bytes(b"changed")
        result = manifest_view(manifest, selected=[paths[0].name])
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["checked_entries"], 2)
        self.assertEqual(result["problems"][0]["path"], paths[1].name)
        self.assertEqual(len(result["entries"]), 1)

    def test_resource_continuation_refuses_changed_source(self):
        path = self.root / "text.md"
        path.write_text("abc" * 100, encoding="utf-8")
        prefix = [sys.executable, "-B", str(SUITE / "scripts/read_learning_resource.py"), "--file", str(path), "--format", "json"]
        first = subprocess.run(prefix + ["--max-chars", "8"], capture_output=True, text=True, encoding="utf-8", timeout=20)
        page = json.loads(first.stdout)
        self.assertFalse(page["coverage"]["complete"])
        path.write_text("changed" * 100, encoding="utf-8")
        next_page = subprocess.run(prefix + ["--offset", "8", "--expect-view-sha256", page["coverage"]["view_sha256"]], capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(next_page.returncode, 1)
        self.assertEqual(json.loads(next_page.stdout)["problem"], "read_version_changed")

    def test_manifest_cannot_validate_a_missing_file_against_a_null_fingerprint(self):
        path = self.root / "invalid-manifest.json"
        path.write_text(json.dumps({"entries": [{"path": "missing.md", "sha256": None}]}), encoding="utf-8")
        with self.assertRaises(ValueError):
            manifest_view(path)

    def test_default_resource_view_prints_the_body_without_json_escape_inflation(self):
        path = self.root / "text.md"
        path.write_text("第一行\n第二行\n", encoding="utf-8")
        process = subprocess.run([sys.executable, "-B", str(SUITE / "scripts/read_learning_resource.py"), "--file", str(path)],
                                 capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(process.returncode, 0, process.stdout)
        self.assertIn("--- 阅读正文 ---\n\n第一行\n第二行", process.stdout)
        self.assertNotIn('"text":', process.stdout)


class ReadingCliGateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="reading-gate-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.control = {"state_revision": 0, "paused_ids": [], "deleted_ids": [], "restrictions": []}
        self.w = CompleteWorkflow(self.root, lambda: deepcopy(self.control))
        self.c = self.w.coordinator
        self.ref = self.w.candidate("material")["ref"]
        self.w.adopt(self.ref, [self.w.confirm(self.ref)])

    def cli_current(self, script="coordinate_agents.py", *extra):
        process = subprocess.run([sys.executable, "-B", str(SUITE / "scripts" / script), "--workspace", str(self.root), "--role", "AG0", "current",
                                  "--artifact-id", "material", "--intended-use", "teaching", "--scope", "whole", *extra],
                                 capture_output=True, text=True, encoding="utf-8", timeout=20)
        return process.returncode, json.loads(process.stdout)

    def test_daily_and_technical_current_default_to_verified_metadata(self):
        item = self.c.resolve(self.w.sessions["AG0"], "material", "teaching", ["whole"])
        for script in ("coordinate_agents.py", "coordinate_preparation.py"):
            code, result = self.cli_current(script)
            self.assertEqual(code, 0, result)
            self.assertEqual(result["ref"], self.ref)
            self.assertEqual(result["sha256"], item["sha256"])
            self.assertNotIn("content_base64", result)
            self.assertNotIn("text", result)

    def test_explicit_base64_retains_machine_client_bytes(self):
        code, result = self.cli_current("coordinate_preparation.py", "--view", "base64")
        self.assertEqual(code, 0, result)
        self.assertEqual(base64.b64decode(result["content_base64"]), (self.root / result["path"]).read_bytes())

    def test_explicit_text_pages_are_version_bound(self):
        code, first = self.cli_current("coordinate_agents.py", "--view", "text", "--max-chars", "8")
        self.assertEqual(code, 0, first)
        code, tail = self.cli_current("coordinate_agents.py", "--view", "text", "--offset", "8", "--expect-sha256", first["sha256"])
        self.assertEqual(code, 0, tail)
        self.assertEqual(first["text"] + tail["text"], (self.root / first["path"]).read_bytes().decode("utf-8-sig"))
        self.assertFalse(tail["coverage"]["complete"])

    def test_current_metadata_still_rejects_mutated_artifact(self):
        item = self.c.resolve(self.w.sessions["AG0"], "material", "teaching", ["whole"])
        (self.root / item["path"]).write_bytes(b"changed after adoption")
        for script in ("coordinate_agents.py", "coordinate_preparation.py"):
            code, result = self.cli_current(script)
            self.assertEqual(code, 1, result)
            self.assertEqual(result["status"], "rejected")

    def test_metadata_does_not_bypass_pause_or_delete(self):
        for field in ("paused_ids", "deleted_ids"):
            self.control.update(state_revision=self.control["state_revision"] + 1, paused_ids=[], deleted_ids=[])
            self.control[field] = ["material"]
            with self.subTest(field=field), self.assertRaises(GateError):
                self.c.resolve(self.w.sessions["AG0"], "material", "teaching", ["whole"])

    def test_candidate_does_not_replace_adopted_metadata_and_new_version_refuses_old_page(self):
        _, original = self.cli_current()
        candidate = self.w.candidate("material")["ref"]
        _, before = self.cli_current()
        self.assertEqual(before["ref"], original["ref"])
        self.w.adopt(candidate, [self.w.confirm(candidate)])
        code, result = self.cli_current("coordinate_agents.py", "--view", "text", "--offset", "8", "--expect-sha256", original["sha256"])
        self.assertEqual(code, 1, result)
        self.assertEqual(result["problem"], "read_version_changed")

    def test_desk_scope_filters_tasks_and_pending_decisions(self):
        self.w.register("M21-task", "M21-output", scope=["M2.1"])
        api = AgentCoordinator(self.c)
        result = api.desk(self.w.sessions["AG0"], intended_use="teaching", scope=["M2.1"])
        self.assertEqual([row["task"] for row in result["tasks"]], ["M21-task"])
        self.assertFalse(result["decisions"])
        result = api.desk(self.w.sessions["AG0"], intended_use="other-use")
        self.assertFalse(result["tasks"])
        self.assertFalse(result["decisions"])

    def start_dependent_stage(self):
        self.w.register("next-stage", "design", role="AG1", kind="ActivitySpec",
                        inputs=[{"id":"material", "policy":"adopted", "scope":["whole"], "intended_use":"teaching"}])
        self.w.op("AG1", "start", task_id="next-stage")

    def cli_inputs(self, role, *extra):
        process = subprocess.run([sys.executable, "-B", str(SUITE / "scripts/coordinate_agents.py"),
                                  "--workspace", str(self.root), "--role", role, "inputs", "--task", "next-stage", *extra],
                                 capture_output=True, text=True, encoding="utf-8", timeout=20)
        return process.returncode, json.loads(process.stdout)

    def test_main_entry_catalog_and_explicit_professional_body_bind_same_version(self):
        self.start_dependent_stage()
        code, catalog = self.cli_inputs("AG0")
        self.assertEqual(code, 0, catalog)
        self.assertEqual(catalog["view"], "metadata")
        row = catalog["inputs"][0]
        self.assertEqual(row["ref"], self.ref)
        self.assertNotIn("text", row)
        self.assertNotIn("coverage", row)
        self.assertNotIn("content_base64", row)
        code, body = self.cli_inputs("AG0", "--view", "text", "--input", "0", "--expect-sha256", row["sha256"])
        self.assertEqual(code, 0, body)
        self.assertEqual(body["inputs"][0]["ref"], row["ref"])
        self.assertEqual(body["inputs"][0]["sha256"], row["sha256"])
        self.assertTrue(body["inputs"][0]["coverage"]["complete"])
        self.assertEqual(body["inputs"][0]["text"], (self.root / row["path"]).read_bytes().decode("utf-8-sig"))

    def test_professional_stage_still_obtains_body_by_default(self):
        self.start_dependent_stage()
        code, result = self.cli_inputs("AG1")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["view"], "text")
        self.assertIn("Fabricated demonstration", result["inputs"][0]["text"])

    def test_catalog_does_not_bypass_owner_access(self):
        self.start_dependent_stage()
        code, result = self.cli_inputs("AG2", "--view", "metadata")
        self.assertEqual(code, 1, result)
        self.assertEqual(result["status"], "rejected")

    def test_catalog_still_rejects_modified_fixed_file(self):
        self.start_dependent_stage()
        _, result = self.cli_inputs("AG0")
        (self.root / result["inputs"][0]["path"]).write_bytes(b"different bytes at same path")
        code, result = self.cli_inputs("AG0")
        self.assertEqual(code, 1, result)
        self.assertEqual(result["status"], "rejected")

    def test_stage_resume_keeps_fixed_input_while_current_pointer_moves(self):
        self.start_dependent_stage()
        _, catalog = self.cli_inputs("AG0")
        original = catalog["inputs"][0]
        newer = self.w.candidate("material")["ref"]
        self.w.adopt(newer, [self.w.confirm(newer)])
        _, current = self.cli_current()
        self.assertEqual(current["ref"], newer)
        code, resumed = self.cli_inputs("AG1", "--input", "0", "--expect-sha256", original["sha256"])
        self.assertEqual(code, 0, resumed)
        self.assertEqual(resumed["inputs"][0]["ref"], original["ref"])
        self.assertEqual(resumed["inputs"][0]["sha256"], original["sha256"])
        self.assertNotEqual(resumed["inputs"][0]["ref"], current["ref"])

    def test_full_read_from_catalog_requires_explicit_text_selection(self):
        self.start_dependent_stage()
        for extra in (("--full",), ("--offset", "1")):
            code, result = self.cli_inputs("AG0", *extra)
            self.assertEqual(code, 1, result)
            self.assertEqual(result["problem"], "explicit_text_view_required")

    def test_inspecting_stage_catalog_is_read_only(self):
        self.start_dependent_stage()
        def records():
            with self.c.connect() as db:
                tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                return {name: sorted(tuple(row) for row in db.execute('SELECT * FROM "' + name + '"')) for name in tables}
        before = records()
        for role, extra in (("AG0", ()), ("AG1", ()), ("AG0", ("--view", "text"))):
            code, result = self.cli_inputs(role, *extra)
            self.assertEqual(code, 0, result)
        self.assertEqual(records(), before)


if __name__ == "__main__":
    unittest.main()
