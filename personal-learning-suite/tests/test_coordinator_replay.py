"""Behavior checks use fabricated files in temporary roots, never learner copies."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from coordinator.replay import Replay, ReplayError, VERSION, write_outputs


class CoordinatorReplayTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="tac-replay-test-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.case_path = self.root / "replay" / "case.json"
        self.case_path.parent.mkdir()
        bodies = {
            "materials/item-v1.md": "Fabricated old material.\n",
            "materials/item-v2.md": "Fabricated new material.\n",
            "plan/plan-v1.md": "Fabricated old plan.\n",
            "plan/plan-v2.md": "Fabricated plan-v2.md: post-review closeout only.\n",
            "assessment/review-v1.md": (
                "# Fabricated review\n\n## Exact reviewed versions\n\n"
                "| 1 | `materials/item-v1.md` | Fabricated full read |\n"
                "| 2 | `plan/plan-v1.md` | Fabricated full read |\n"
                "\n## Other mentions\nmaterials/item-v2.md was not read here.\n"),
            "assessment/review-v2.md": (
                "Fabricated follow-up to review-v1.md.\n"
                "Fabricated item-v2.md read and found compatible in this example.\n"),
            "sessions/result.md": "Fabricated final plan-v2.md closeout.\n",
        }
        active = {"materials/item-v2.md", "plan/plan-v2.md", "assessment/review-v1.md",
                  "assessment/review-v2.md", "sessions/result.md"}
        entries = []
        for path, text in bodies.items():
            data = text.encode("utf-8")
            self.put(path, data)
            entries.append(self.entry(path, data, active=path in active))
        candidate = []
        for path in ("materials/item-v1.md", "materials/item-v2.md", "plan/plan-v1.md"):
            data = bodies[path].encode("utf-8")
            self.put("archive/candidate/" + path, data)
            candidate.append(self.entry(path, data))
        self.put_json("archive/deliverables.json", entries)
        self.put_json("archive/candidate.json", candidate)
        self.put_json("archive/order.json", {"order": 1, "target": "fabricated-reviewer",
            "mode": "fabricated-dispatch", "message": "Fabricated historical instruction"})
        archive_entries = []
        for path in sorted((self.root / "archive").rglob("*")):
            if path.is_file():
                archive_entries.append(self.entry(path.relative_to(self.root / "archive").as_posix(), path.read_bytes()))
        self.put_json("archive/inventory.json", archive_entries)
        self.put("state/control.md", b"Fabricated controls\n")
        self.case = {
            "schema_version": VERSION, "case_id": "fabricated-test", "evidence_kind": "synthetic_test",
            "workspace_root": "..", "artifact_manifest": "archive/deliverables.json",
            "archive_inventory": {"root": "archive", "manifest": "archive/inventory.json"},
            "inventories": [{"id": "candidate", "manifest": "archive/candidate.json", "root": "archive/candidate"}],
            "handoff_sources": ["archive/order.json"],
            "original_review": {"path": "assessment/review-v1.md", "section": "## Exact reviewed versions", "expected_binding_count": 2},
            "treatments": [
                {"kind": "supplementary_review", "from": "materials/item-v1.md", "to": "materials/item-v2.md",
                 "receipt_path": "assessment/review-v2.md", "scope": "Fabricated material-only review",
                 "assertions": [
                     {"path": "assessment/review-v2.md", "quote": "Fabricated follow-up to review-v1.md."},
                     {"path": "assessment/review-v2.md", "quote": "Fabricated item-v2.md read and found compatible in this example."}]},
                {"kind": "post_review_closeout", "from": "plan/plan-v1.md", "to": "plan/plan-v2.md",
                 "receipt_path": "plan/plan-v2.md", "scope": "Fabricated closeout, not reviewed",
                 "assertions": [{"path": "plan/plan-v2.md", "quote": "Fabricated plan-v2.md: post-review closeout only."}]}
            ],
            "protected_paths": ["state/control.md"], "protected_roots": ["archive", "materials", "assessment", "plan", "sessions", "state"]}
        self.save_case()

    @staticmethod
    def entry(path, data, **fields):
        return {"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), **fields}

    def put(self, path, data):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def put_json(self, path, value):
        self.put(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    def save_case(self):
        self.case_path.write_text(json.dumps(self.case, ensure_ascii=False, indent=2), encoding="utf-8")

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_replay_detects_drift_and_distinguishes_supplement_from_closeout(self):
        before = self.snapshot()
        report = Replay(self.case_path).run()
        self.assertEqual(report["summary"]["baseline_version_differences"], 2)
        self.assertEqual(report["summary"]["recorded_supplements"], 1)
        self.assertEqual(report["summary"]["post_review_closeouts_not_ag3_reviewed"], 1)
        self.assertEqual(report["summary"]["unresolved_version_differences"], 0)
        self.assertEqual([f["baseline_status"] for f in report["findings"]], ["needs_recheck"] * 2)
        self.assertEqual(before, self.snapshot())

    def test_candidate_inventory_and_other_mentions_do_not_establish_reading(self):
        report = Replay(self.case_path).run()
        paths = {b["artifact_path"] for b in report["review_bindings"]}
        self.assertNotIn("materials/item-v2.md", paths)
        self.assertEqual(report["summary"]["candidate_inventory_entries"], 3)
        self.assertEqual(report["summary"]["original_review_bindings"], 2)

    def test_missing_adapter_supplement_remains_unresolved_even_if_receipt_exists(self):
        self.case["treatments"] = self.case["treatments"][1:]
        self.save_case()
        report = Replay(self.case_path).run()
        finding = next(f for f in report["findings"] if f["reviewed_path"] == "materials/item-v1.md")
        self.assertEqual(finding["status"], "needs_recheck")
        self.assertEqual(report["summary"]["unresolved_version_differences"], 1)

    def test_source_tampering_rejects_replay_without_output(self):
        self.put("materials/item-v2.md", b"Tampered bytes")
        with self.assertRaisesRegex(ReplayError, "fingerprint mismatch"):
            Replay(self.case_path).run()
        self.assertFalse((self.case_path.parent / "output").exists())

    def test_archive_handoff_tampering_is_detected(self):
        self.put_json("archive/order.json", {"order": 1, "target": "other", "mode": "dispatch", "message": "altered"})
        with self.assertRaisesRegex(ReplayError, "fingerprint mismatch"):
            Replay(self.case_path).run()

    def test_missing_evidence_anchor_is_not_treated_as_confirmation(self):
        self.case["treatments"][0]["assertions"][1]["quote"] = "Fabricated claim not present"
        self.save_case()
        with self.assertRaisesRegex(ReplayError, "anchor missing"):
            Replay(self.case_path).run()

    def test_wrong_receipt_cannot_cover_a_different_final_version(self):
        self.case["treatments"][0]["to"] = "plan/plan-v2.md"
        self.save_case()
        with self.assertRaisesRegex(ReplayError, "match an observed version change"):
            Replay(self.case_path).run()

    def test_multiple_active_revisions_are_unknown_not_latest_wins(self):
        rows = json.loads((self.root / "archive/deliverables.json").read_text())
        next(r for r in rows if r["path"] == "materials/item-v1.md")["active"] = True
        self.put_json("archive/deliverables.json", rows)
        inventory = json.loads((self.root / "archive/inventory.json").read_text())
        inventory = [r for r in inventory if r["path"] != "deliverables.json"]
        inventory.append(self.entry("deliverables.json", (self.root / "archive/deliverables.json").read_bytes()))
        self.put_json("archive/inventory.json", inventory)
        self.case["treatments"] = self.case["treatments"][1:]
        self.save_case()
        report = Replay(self.case_path).run()
        finding = next(f for f in report["findings"] if f["reviewed_path"] == "materials/item-v1.md")
        self.assertEqual(finding["status"], "unknown_or_ambiguous_final_pointer")
        self.assertIsNone(finding["final_path"])

    def test_path_escape_is_rejected(self):
        self.case["protected_paths"] = ["../outside.md"]
        self.save_case()
        with self.assertRaisesRegex(ReplayError, "unsafe relative path"):
            Replay(self.case_path).run()

    def test_read_only_outputs_and_sqlite_match_json(self):
        before = self.snapshot()
        replay = Replay(self.case_path)
        report = replay.run()
        output = write_outputs(replay, report, self.case_path.parent / "output")
        with closing(sqlite3.connect(f"file:{(output / 'index.sqlite3').as_posix()}?mode=ro", uri=True)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0], report["summary"]["artifact_versions"])
            self.assertEqual(db.execute("SELECT status FROM findings WHERE reviewed_path=?", ("plan/plan-v1.md",)).fetchone()[0], "post_review_closeout_not_ag3_reviewed")
        self.assertEqual(json.loads((output / "index.json").read_text(encoding="utf-8")), report)
        after = self.snapshot()
        for path, data in before.items():
            self.assertEqual(after[path], data)
        self.assertFalse(any("Fabricated historical instruction" in p.read_text(encoding="utf-8") for p in output.glob("*.json")))

    def test_output_cannot_replace_history_or_write_to_domain_tree(self):
        replay = Replay(self.case_path)
        report = replay.run()
        write_outputs(replay, report, self.case_path.parent / "output")
        with self.assertRaisesRegex(ReplayError, "already exists"):
            write_outputs(replay, report, self.case_path.parent / "output")
        with self.assertRaisesRegex(ReplayError, "beside the replay case"):
            write_outputs(replay, report, self.root / "materials/new")

    def test_source_change_between_replay_and_export_is_detected(self):
        replay = Replay(self.case_path)
        report = replay.run()
        self.put("state/control.md", b"New fabricated restriction")
        with self.assertRaisesRegex(ReplayError, "source changed before output"):
            write_outputs(replay, report, self.case_path.parent / "output")
        self.assertFalse((self.case_path.parent / "output").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
