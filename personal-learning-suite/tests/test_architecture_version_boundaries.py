"""Current decision gates preserve historical facts without transferring support.

These public-API checks characterize audit risk R01. A compatibility declaration
alone is not an adopted assessment mapping or permission to reuse stale tasks.
"""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from test_b3a_assessment import fixture, objects_by_id
from runtime.learning_assessment import AssessmentService, fact, ref
from runtime.learning_store import LearningStore


class ArchitectureVersionBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="pl-version-boundary-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "workspace"
        snapshot, artifacts, self.judgment, self.context, _, _ = fixture()
        self.store = LearningStore(self.root, entry_actor="AG3")
        self.assertEqual(self.store.init_workspace()["status"], "committed")
        self.assertEqual(self.store.import_fixture(snapshot, artifacts)["status"], "committed")
        self.initial = objects_by_id(self.store.read_context())
        self.service = AssessmentService(self.store)
        self.assertEqual(self.service.inspect_judgment(self.judgment, self.context)["status"], "compatible")

    def revise_goal(self, *, compatibility=False, correction=False):
        goal = copy.deepcopy(self.initial["FIX-goal"])
        goal["revision"] += 1
        goal["audit_note"] = "Description-only maintenance of a fictional goal."
        if compatibility:
            goal["version_compatibility"] = fact("known", value={
                "status": "preserve",
                "preserve_requirement_ids": [r["requirement_id"] for r in goal["requirements"]],
                "judgment_transfer": "not_executed",
                "reason": "Explicit description equivalence; no assessment transfer adopted.",
            })
        if correction:
            goal["requirements"][0]["criterion_revision"] += 1
            goal["requirements"][0]["criterion"]["text"] = "Corrected fictional criterion; historical response unchanged."
        designer = LearningStore(self.root, entry_actor="AG1")
        grant = ref(self.initial["FIX-user-grant"])
        result = designer.commit(
            expected_state_revision=designer.read_context()["state_revision"],
            operation_id="FIX-version-boundary-maintenance", changes=[goal],
            authorization_refs=[grant], adoption_refs=[grant],
        )
        self.assertEqual(result["status"], "committed", result)
        return goal

    def assert_history_preserved_and_current_use_restricted(self):
        history = self.store.read_refs([
            ref(self.initial["FIX-goal"]), ref(self.initial["FIX-activity"]),
            ref(self.initial["FIX-event"]), ref(self.initial["FIX-judgment"]),
        ], "assessment")
        self.assertEqual(history["status"], "ok", history)
        for record in history["objects"]:
            self.assertEqual(record, self.initial[record["id"]])
        original = self.store.read_artifact_segment(
            self.initial["FIX-event"]["original_response"], 3, 4, "assessment")
        self.assertEqual(original["status"], "ok", original)
        before = self.store.read_context()
        result = self.service.inspect_judgment(self.judgment, self.context)
        self.assertEqual(result["status"], "rejected", result)
        self.assertIn("stale_assessment_dependency", {r["code"] for r in result["reasons"]})
        self.assertEqual(self.store.read_context(), before)

    def test_description_revision_does_not_erase_historical_task_or_response(self):
        self.revise_goal()
        self.assert_history_preserved_and_current_use_restricted()

    def test_compatibility_declaration_does_not_adopt_support_transfer(self):
        self.revise_goal(compatibility=True)
        self.assert_history_preserved_and_current_use_restricted()

    def test_corrected_criterion_does_not_rewrite_prior_conditions_or_judgment(self):
        self.revise_goal(correction=True)
        self.assert_history_preserved_and_current_use_restricted()


if __name__ == "__main__":
    unittest.main(verbosity=2)
