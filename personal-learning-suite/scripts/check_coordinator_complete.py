"""Acceptance of original-proposal features and the real manual-file integration."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

SUITE = Path(__file__).resolve().parents[1]
PROJECT = SUITE.parent
sys.path.insert(0, str(SUITE / "src"))
from coordinator.complete import TaskArtifactCoordinator, COMPLETE_VERSION
from coordinator.workspace import FileControlGate, sha
from coordinator.replay import Replay
from check_coordinator_reliability import snapshot as previous_snapshot


def json_file(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def link_check(paths):
    errors = []
    for path in paths:
        for match in re.finditer(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8-sig")):
            value = match.group(1).split("#")[0]
            if not value or "://" in value or value.startswith("#"):
                continue
            if not (path.parent / value).resolve().exists():
                errors.append({"file": str(path.relative_to(PROJECT)), "target": value})
    return errors


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to(PROJECT / "maintenance") or output.exists():
        raise ValueError("Use a new maintenance output directory")
    output.mkdir(parents=True)
    replay = Replay(PROJECT / "learning/embodied-intelligence/experiments/coordinator-replay-20261013-bc-loop-01/replay-case.json")
    protected_before = previous_snapshot(replay)
    # Include all three saved historical output directories, including SQLite.
    for path in (PROJECT / "maintenance/coordinator-batch3-20261013").rglob("*"):
        if path.is_file():
            protected_before[str(path)] = sha(path.read_bytes())
    suite = unittest.TestLoader().discover(str(SUITE / "tests"), pattern="test_coordinator_*.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (output / "test-output.txt").write_text(stream.getvalue(), encoding="utf-8")
    if not result.wasSuccessful():
        print(stream.getvalue())
        raise AssertionError("Coordinator tests failed")
    baseline_check = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SUITE / "scripts/check_b0.py")], capture_output=True, text=True, encoding="utf-8", timeout=40,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if baseline_check.returncode:
        raise AssertionError(f"Shared contract/source baseline failed: {baseline_check.stdout} {baseline_check.stderr}")
    json_file(output / "shared-contract-check.json", json.loads(baseline_check.stdout))
    root = PROJECT / "learning/embodied-intelligence"
    c = TaskArtifactCoordinator(root, FileControlGate(root, root / "coordination/control.json"))
    session = c.bind_local_operator("AG0")
    state = c.status(session)
    trace = json.loads((root / "coordination/integration-trace.json").read_text(encoding="utf-8"))
    historical = trace["trace"][0]["request"]["entries"]
    changed = [e["path"] for e in historical if sha((root / e["path"]).read_bytes()) != e["sha256"]]
    refused = next(t for t in trace["trace"] if t["request"]["operation_id"] == "integration-reject-old-review-v2")
    if changed or refused["result"]["reasons"] != ["receipt_version_mismatch"]:
        raise AssertionError("Real historical bindings or refusal changed")
    nav = [a for a in state["artifacts"] if a["id"] == "EMB-M-BC-COORDINATION-ENTRY-20261013"]
    if [a["state"] for a in nav] != ["Superseded", "Adopted"] or state["impacts"]:
        raise AssertionError("Real preparation navigation not fully settled")
    # Fresh CLI processes use the actual control projection and database.
    prefix = [sys.executable, "-B", "-X", "utf8", str(SUITE / "scripts/coordinate_preparation.py"), "--workspace", str(root), "--role", "AG0"]
    calls = []
    for arguments in (["brief"], ["state"], ["inbox", "--consumer-id", "integration-maintenance"],
                      ["boundary", "--task-id", "bc-navigation-v2"],
                      ["current", "--artifact-id", "EMB-P-BC-CLOSED-LOOP-20261012", "--intended-use", "teaching", "--scope", "BC-first-stage"],
                      ["diff", "--artifact-id", "EMB-M-BC-COORDINATION-ENTRY-20261013", "--old-revision", "1", "--new-revision", "2"],
                      ["operation", "--operation-id", "integration-adopt-navigation-v2"],
                      ["receipt", "--receipt-id", "bc-navigation-review-v2"], ["recover"]):
        process = subprocess.run(prefix + arguments, capture_output=True, text=True, encoding="utf-8", timeout=40,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if process.returncode:
            raise AssertionError(f"Actual CLI failed: {process.stdout} {process.stderr}")
        if arguments[0] == "brief":
            response = {"status": "ok", "brief": process.stdout}
        else:
            response = json.loads(process.stdout)
            # Keep validation metadata, not another copy of professional bytes.
            response.pop("content_base64", None)
            if arguments[0] == "inbox" and response["events"]:
                raise AssertionError("Already acknowledged events reappeared")
        calls.append({"arguments": arguments, "response": response})
    links = [root / "COORDINATION.md", root / "AGENTS.md", root / "MODEL_ENTRY.md", root / "FRAMEWORK.md", SUITE / "specs/coordinator-protocol.md"]
    links += list((SUITE / "src/agents").glob("*.md"))
    link_errors = link_check(links)
    if link_errors:
        raise AssertionError(link_errors)
    manifest = json.loads((root / "framework-manifest.json").read_text(encoding="utf-8-sig"))
    mismatch = [e["path"] for e in manifest["entries"] if sha((root / e["path"]).read_bytes()) != e["sha256"]]
    if mismatch:
        raise AssertionError(f"Framework drift: {mismatch}")
    protected_changed = [str(Path(p).relative_to(PROJECT)) for p, digest in protected_before.items() if not Path(p).is_file() or sha(Path(p).read_bytes()) != digest]
    if protected_changed:
        raise AssertionError(f"Read-only acceptance changed sources: {protected_changed}")
    validation = {"status": "passed", "version": COMPLETE_VERSION, "evidence_kind": "fabricated_feature_tests_plus_actual_real_file_host_integration",
                  "tests": {"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped)},
                  "actual_cli_calls": len(calls), "historical_versions_registered": len(historical), "historical_changed_paths": changed,
                  "shared_contract_source_check": "passed",
                  "real_new_preparation_versions": 2, "old_review_refused": refused["result"]["reasons"], "unresolved_impacts": len(state["impacts"]),
                  "framework_entries_checked": len(manifest["entries"]), "relative_link_errors": link_errors,
                  "protected_files_during_acceptance": len(protected_before), "protected_changed_paths": protected_changed,
                  "database_integrity": c.recover(session)["integrity"], "role_mode": "trusted_local_operator_same_model_sequential_not_independent_review",
                  "program_sources": [{"path": str(p.relative_to(PROJECT)), "sha256": sha(p.read_bytes())} for p in [
                      SUITE / "src/coordinator/complete.py", SUITE / "src/coordinator/publication.py", SUITE / "scripts/coordinate_preparation.py",
                      SUITE / "scripts/integrate_coordinator.py", SUITE / "scripts/check_coordinator_complete.py", SUITE / "tests/test_coordinator_complete.py"]],
                  "limits": ["宿主工具调用及关键节点校验已接入，推理中模型不自动获得磁盘上下文。", "源文件覆写会拒绝，不提供恶意文件系统隔离或身份认证。", "专业语义、变更范围与相容性由既有角色明确判断。", "真实试运行仅备课导航，没有学习者表现或教学效果对照。"]}
    json_file(output / "validation.json", validation)
    json_file(output / "cli-transcript.json", calls)
    (output / "status.md").write_text(c.brief(session), encoding="utf-8")
    (output / "report.md").write_text(f"# 原方案完整功能及实际入口验收\n\n状态：通过。版本：{COMPLETE_VERSION}。\n\n{result.testsRun}项自动检查通过（含前三批72项），{len(calls)}次真实目录CLI读取成功。8个历史版本按原证据登记，原件未改；2份新备课导航实际完成候选、专业确认、版本审查与AG0采用。v1审查用于v2的尝试被拒绝，明确补核后采用；v1状态Superseded，v2 Adopted。未解决影响为0。\n\n框架{len(manifest['entries'])}份登记指纹及入口相对链接通过。验收期间{len(protected_before)}份来源/前三批历史输出字节未变。真实数据库完整性检查通过。\n\n角色为可信操作员声明，本维护模型顺序兼任，不称独立审查。真实接入的是人工文件工具入口与关键节点门禁，没有后台调度Agent或自动上下文注入；专业判断仍由原职责承担。没有新增教学展示、学习者能力或实验事实。\n\n详见validation.json、test-output.txt、cli-transcript.json及学习目录coordination/integration-trace.json。\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "tests": result.testsRun, "actual_cli_calls": len(calls), "report": str(output / "report.md")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
