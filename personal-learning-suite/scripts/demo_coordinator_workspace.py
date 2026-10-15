"""A fabricated, isolated workflow exercising batch-two coordination gates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator.workspace import Coordinator


class Workflow:
    """Small CLI-use example; test data are generated locally, not learner copies."""
    def __init__(self, root, control_gate=None, *, coordinator_class=Coordinator):
        self.root = Path(root)
        self.coordinator = coordinator_class(root, control_gate)
        self.coordinator.initialize(evidence_kind="synthetic_demo")
        self.sessions = {r: self.coordinator.bind_local_operator(r) for r in ("AG0", "AG1", "AG2", "AG3")}
        self.sequence = 0
        self.trace = []

    def request(self, **fields):
        self.sequence += 1
        return {"operation_id": f"demo-operation-{self.sequence}",
                "expected_state_revision": self.coordinator.status(self.sessions["AG0"])["state_revision"], **fields}

    def op(self, role, action, *, expect="committed", **fields):
        request = self.request(**fields)
        result = self.coordinator.execute(self.sessions[role], action, request)
        self.trace.append({"role": role, "action": action, "request": request, "result": result})
        if result["status"] != expect:
            raise AssertionError(f"{action}: expected {expect}, got {result}")
        return result

    def register(self, task_id, artifact_id, *, role="AG2", kind="MaterialUse", scope=None, inputs=None, review=False):
        return self.op("AG0", "register", id=task_id, assignee=role, task_kind="production",
                       intended_use="teaching", scope=scope or ["whole"], inputs=inputs or [],
                       output={"id": artifact_id, "type": kind, "requires_ag3_review": review})

    def candidate(self, artifact_id, *, role="AG2", kind="MaterialUse", scope=None, inputs=None, review=False, changed_scope=None):
        task_id = f"task-{self.sequence + 1}"
        self.register(task_id, artifact_id, role=role, kind=kind, scope=scope, inputs=inputs, review=review)
        self.op(role, "start", task_id=task_id)
        return self.submit(task_id, role=role, changed_scope=changed_scope)

    def submit(self, task_id, *, role="AG2", changed_scope=None):
        path = f"artifacts/{task_id}.txt"
        (self.root / "artifacts").mkdir(exist_ok=True)
        (self.root / path).write_text(f"Fabricated demonstration artifact for {task_id}. Not a learner record.\n", encoding="utf-8")
        return self.op(role, "submit", task_id=task_id, path=path, changed_scope=changed_scope)

    def confirm(self, target, *, role="AG2", scope=None):
        receipt_id = f"confirmation-{self.sequence + 1}"
        self.op(role, "confirm", ref=target, receipt_id=receipt_id, scope=scope or ["whole"],
                intended_use="teaching", outcome="supported", rationale="Fabricated owner's professional confirmation.")
        return receipt_id

    def review(self, target, *, scope=None, base=None, checked=None, inherited=None):
        task_id = f"review-task-{self.sequence + 1}"
        self.op("AG0", "register", id=task_id, assignee="AG3", task_kind="review", scope=scope or ["whole"],
                intended_use="teaching", target_ref=target)
        self.op("AG3", "start", task_id=task_id)
        receipt_id = f"review-{self.sequence + 1}"
        fields = {"task_id": task_id, "receipt_id": receipt_id, "scope": scope or ["whole"],
                  "intended_use": "teaching", "outcome": "supported", "rationale": "Fabricated version-specific AG3 opinion."}
        if base:
            fields.update(base_receipt_id=base, directly_checked_scope=checked, inherited_scope=inherited,
                          compatibility_rationale="Fabricated AG3 assertion that the retained scope remains applicable.")
        self.op("AG3", "review", **fields)
        return receipt_id

    def adopt(self, target, receipts, *, scope=None, expect="committed"):
        return self.op("AG0", "adopt", expect=expect, bundle_id=f"bundle-{self.sequence + 1}",
                       members=[{"ref": target, "scope": scope or ["whole"], "intended_use": "teaching", "receipt_ids": receipts}])


def run_scenario(root, *, coordinator_class=Coordinator):
    w = Workflow(root, coordinator_class=coordinator_class)
    scope = ["M1", "M3"]
    first = w.candidate("material", scope=scope, review=True)["ref"]
    first_owner = w.confirm(first, scope=scope)
    first_review = w.review(first, scope=scope)
    w.adopt(first, [first_owner, first_review], scope=scope)
    w.register("updating-material", "material", scope=scope, review=True)
    w.op("AG2", "start", task_id="updating-material")
    # The revision task exists, but its draft has not changed the adopted pointer.
    for section in ("M1", "M3"):
        w.register(f"downstream-{section}", f"activity-{section}", role="AG1", kind="ActivitySpec", scope=[section],
                   inputs=[{"id": "material", "policy": "adopted", "scope": [section], "intended_use": "teaching"}])
        w.op("AG1", "start", task_id=f"downstream-{section}")
    second = w.submit("updating-material", changed_scope=["M3"])["ref"]
    second_owner = w.confirm(second, scope=scope)
    refused = w.adopt(second, [second_owner, first_review], scope=scope, expect="rejected")
    if refused["reasons"] != ["receipt_version_mismatch"]:
        raise AssertionError(refused)
    second_review = w.review(second, scope=scope, base=first_review, checked=["M3"], inherited=["M1"])
    w.adopt(second, [second_owner, second_review], scope=scope)
    snapshots = {part: [item["ref"] for item in w.coordinator.read_snapshot(w.sessions["AG1"], f"downstream-{part}")]
                 for part in ("M1", "M3")}
    independent = w.submit("downstream-M1", role="AG1", changed_scope=["M1"])
    independent_owner = w.confirm(independent["ref"], role="AG1", scope=["M1"])
    w.adopt(independent["ref"], [independent_owner], scope=["M1"])
    affected = w.submit("downstream-M3", role="AG1", changed_scope=["M3"])
    if not affected["input_issues"]:
        raise AssertionError("Affected old input was not detected")
    w.op("AG1", "recheck", ref=affected["ref"], recheck_id="local-M3-recheck", old_ref=first, new_ref=second,
         scope=["M3"], intended_use="teaching", rationale="Fabricated local comparison preserves this downstream result.")
    affected_owner = w.confirm(affected["ref"], role="AG1", scope=["M3"])
    w.adopt(affected["ref"], [affected_owner], scope=["M3"])
    return {"evidence_kind": "synthetic_demo", "authority_mode": "local_operator_attested", "trace": w.trace,
            "results": {"old_review_rejected": refused["reasons"], "pinned_snapshots_after_update": snapshots,
                        "unaffected_input_issues": independent["input_issues"], "affected_input_issues": affected["input_issues"],
                        "supplement_then_adoption": "committed", "local_recheck_then_adoption": "committed"},
            "final_state": w.coordinator.status(w.sessions["AG0"])}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Use a new directory; demonstration output never replaces existing data")
    args.output_dir.mkdir(parents=True)
    report = run_scenario(args.output_dir / "workspace")
    (args.output_dir / "scenario.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["results"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
