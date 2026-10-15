"""Validate batch one against temporary tests and the actual BC archive, read-only."""
from __future__ import annotations

import argparse
from contextlib import closing
import io
import json
from pathlib import Path
import platform
import sqlite3
import sys
import unittest

SUITE = Path(__file__).resolve().parents[1]
PROJECT = SUITE.parent
sys.path.insert(0, str(SUITE / "src"))
from coordinator.replay import Replay, ReplayError, digest, write_outputs


def protected_snapshot(replay):
    roots = [replay.resolve(path) for path in replay.case.get("protected_roots", [])]
    roots += [SUITE / "src/agents", SUITE / "src/skills", SUITE / "src/runtime", SUITE / "contracts"]
    values = {}
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                values[str(path)] = digest(path.read_bytes())
    return values


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        replay = Replay(args.case)
        before = protected_snapshot(replay)
        test_log = io.StringIO()
        tests = unittest.defaultTestLoader.discover(str(SUITE / "tests"), pattern="test_coordinator_replay.py")
        result = unittest.TextTestRunner(stream=test_log, verbosity=2).run(tests)
        if not result.wasSuccessful() or result.testsRun < 1 or result.skipped:
            print(test_log.getvalue(), file=sys.stderr)
            return 1
        report = replay.run()
        if report["case_id"] != "bc-loop-20261012-review-binding-replay":
            raise ReplayError("this acceptance checker is scoped to the actual BC case")
        expected = {"artifact_versions": 37, "archived_active_entries": 21,
                    "candidate_inventory_entries": 27, "handoffs": 16,
                    "original_review_bindings": 14, "baseline_version_differences": 2,
                    "recorded_supplements": 1, "post_review_closeouts_not_ag3_reviewed": 1,
                    "unresolved_version_differences": 0}
        if report["summary"] != expected:
            raise ReplayError(f"historical counts changed: {report['summary']}")
        without = Replay(args.case).run(apply_recorded_treatments=False)
        material = next(f for f in without["findings"] if f["reviewed_path"].endswith("/material-uses-v1.md"))
        if material["status"] != "needs_recheck" or not material["final_path"].endswith("/material-uses-v3.md"):
            raise ReplayError("old review incorrectly covers final material without a supplement")
        bound = {b["artifact_path"] for b in report["review_bindings"]}
        if any(path.endswith("/material-uses-v2.md") for path in bound):
            raise ReplayError("unread intermediate version was counted as reviewed")
        # Both historical review files are active: preserve the cumulative pair.
        active_reviews = [a for a in report["artifacts"] if a["archived_active"] and a["file_family"].endswith("/review.md")]
        if len(active_reviews) != 2:
            raise ReplayError("cumulative review receipts were collapsed")
        output = write_outputs(replay, report, args.output_dir)
        with closing(sqlite3.connect(f"file:{(output / 'index.sqlite3').as_posix()}?mode=ro", uri=True)) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ReplayError("SQLite output failed integrity check")
            if db.execute("SELECT COUNT(*) FROM review_bindings").fetchone()[0] != 14:
                raise ReplayError("SQLite review binding count differs")
        after = protected_snapshot(replay)
        changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
        programs = [SUITE / "src/coordinator/replay.py", SUITE / "scripts/replay_coordination.py",
                    Path(__file__), SUITE / "tests/test_coordinator_replay.py"]
        validation = {
            "status": "passed" if not changed else "failed",
            "batch": "coordinator_batch_1", "client_date": "2026-10-13", "client_timezone": "Asia/Shanghai",
            "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
            "unit_tests": {"evidence_kind": "fabricated_temporary_files", "tests_run": result.testsRun,
                           "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped)},
            "historical_replay": {"evidence_kind": report["evidence_kind"], "summary": report["summary"]},
            "counterfactual": {"meaning": "程序不应用已记录处置；原文件均保留。这不是实际历史状态。",
                               "material_change_status": material["status"], "summary": without["summary"]},
            "protected_sources": {"files_checked": len(before), "changed_paths": changed,
                                  "before_digest": digest(json.dumps(before, sort_keys=True).encode("utf-8")),
                                  "after_digest": digest(json.dumps(after, sort_keys=True).encode("utf-8"))},
            "sqlite_integrity": "ok", "sqlite_json_binding_count": 14,
            "program_sources": [{"path": p.relative_to(PROJECT).as_posix(), "sha256": digest(p.read_bytes())} for p in programs],
            "limitations": ["没有改造后真实备课对照，没有运行任务调度或采用门禁。",
                            "测试与执行由同一维护会话完成，不宣称独立审查、教学效果或效率增益。"]}
        with (output / "validation.json").open("x", encoding="utf-8") as stream:
            json.dump(validation, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        with (output / "test-output.txt").open("x", encoding="utf-8") as stream:
            stream.write(test_log.getvalue())
        if changed:
            (output / "INVALID.txt").write_text("Protected sources changed: " + repr(changed), encoding="utf-8")
            raise ReplayError(f"protected sources changed: {changed}")
        print(f"Passed: {result.testsRun} behavior tests; {len(before)} protected files unchanged.")
        print(json.dumps(report["summary"], ensure_ascii=False))
        print(f"Report: {output / 'report.md'}")
        return 0
    except (ReplayError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"Validation rejected: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
