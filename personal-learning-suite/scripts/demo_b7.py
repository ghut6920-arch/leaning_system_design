"""Inspect artificial B7 pilot inputs in memory; never create a learner store."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from runtime.pilot_b7 import PilotService, VERSION
from test_b7_pilot import fixture, validation


def metadata(result):
    selected = {key: result[key] for key in ("status", "inputs_ready", "can_start_automated",
        "live_execution_status", "mutated", "needed_inputs") if key in result}
    selected["reason_codes"] = [item.get("code", "unknown") for item in result.get("reasons", [])]
    if "reviews" in result:
        selected["reviews"] = {layer: {
            "reported_status": review.get("reported_status", "unknown"),
            "review_refs": review.get("review_refs", []),
            "reason_codes": [item.get("code", "unknown") for item in review.get("reasons", [])]
        } for layer, review in result["reviews"].items()}
    return selected


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="validation/b7-demo-report.json")
    args = parser.parse_args()
    candidate = Path(args.report)
    path = candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
    if re.match(r"^b[0-6][abc]?[-_]", path.name.casefold()):
        parser.error("B7 demo must not replace a historical batch report")
    existed = path.exists()
    service = PilotService()
    request = fixture()
    # Artificial canonical reviews exercise the report surface without implying
    # real learning, gain, retention or organizational comparison.
    for layer in ("V1", "V2", "V3"):
        validation(request, layer)
    prepared = service.preflight(request)
    reviewed = service.report(request)
    report = {
        "batch": "B7", "pilot_version": VERSION, "client_date": "2026-10-04",
        "client_timezone": "Asia/Shanghai", "synthetic_only": True,
        "existing_report": existed, "data_kind": "synthetic",
        "input_origin": "Artificial B1/B5 canonical objects copied and extended only in memory.",
        "preflight": metadata(prepared), "report": metadata(reviewed),
        "real_validation": {layer: "not_executed" for layer in ("V1", "V2", "V3", "V4")},
        "store_created": False, "learning_executed": False, "can_start_automated": False,
        "replay_existing_workspace": False,
        "limitations": [
            "All objects, responses, reviewer findings and controls are artificial; no real learner or course was used.",
            "This demo inspects supplied objects in memory and writes only the explicitly requested metadata report.",
            "No SQLite store, personal record directory, teaching execution, adoption or workspace replay occurs.",
            "Real V1–V4 remain not_executed; software behavior cannot establish learning or organizational benefit.",
            "Input original text and original answers are omitted from both the report and stdout."]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B7 synthetic: preflight {prepared.get('status', 'unknown')}; real V1–V4 not_executed; store created false.")
    print(f"Report: {path}")
    return 0 if not prepared.get("can_start_automated", False) and not reviewed.get("mutated", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
