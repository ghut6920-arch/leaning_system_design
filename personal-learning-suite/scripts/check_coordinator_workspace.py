"""Batch-two acceptance: behavior tests, CLI smoke, isolated scenario and batch-one regression."""
from __future__ import annotations

import argparse
from contextlib import closing
import io
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import unittest

SUITE = Path(__file__).resolve().parents[1]
PROJECT = SUITE.parent
sys.path.insert(0, str(SUITE / "src"))
from coordinator.replay import Replay, digest
from demo_coordinator_workspace import run_scenario
from check_coordinator_replay import protected_snapshot


def cli_smoke(output):
    workspace = output / "cli-workspace"
    requests = output / "cli-requests"
    requests.mkdir()
    program = SUITE / "scripts/coordinate_workspace.py"
    transcript = []

    def call(role, arguments):
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(program), "--workspace", str(workspace),
                                 "--role", role, *arguments], capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            raise AssertionError(f"CLI failed: {result.stdout} {result.stderr}")
        value = json.loads(result.stdout)
        transcript.append({"role": role, "arguments": arguments, "response": value})
        return value

    state = call("AG0", ["init", "--evidence-kind", "synthetic_demo"])
    sequence = 0

    def execute(role, action, fields):
        nonlocal sequence, state
        sequence += 1
        request = {"operation_id": f"cli-operation-{sequence}", "expected_state_revision": state["state_revision"], **fields}
        path = requests / f"{sequence:02d}-{action}.json"
        path.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        state = call(role, ["execute", "--action", action, "--request-file", str(path)])
        return state

    execute("AG0", "register", {"id": "cli-task", "assignee": "AG2", "task_kind": "production", "scope": ["whole"],
                                "intended_use": "teaching", "inputs": [], "output": {"id": "cli-material", "type": "MaterialUse", "requires_ag3_review": False}})
    execute("AG2", "start", {"task_id": "cli-task"})
    (workspace / "materials").mkdir()
    (workspace / "materials/material-v1.txt").write_text("Fabricated CLI demonstration, not a learner artifact.\n", encoding="utf-8")
    target = execute("AG2", "submit", {"task_id": "cli-task", "path": "materials/material-v1.txt", "changed_scope": None})["ref"]
    execute("AG2", "confirm", {"ref": target, "receipt_id": "cli-confirmation", "scope": ["whole"], "intended_use": "teaching",
                               "outcome": "supported", "rationale": "Fabricated CLI professional assertion"})
    execute("AG0", "adopt", {"bundle_id": "cli-bundle", "members": [{"ref": target, "scope": ["whole"], "intended_use": "teaching", "receipt_ids": ["cli-confirmation"]}]})
    final = call("AG0", ["state"])
    if final["adopted_pointers"] != [{"id": "cli-material", "intended_use": "teaching", "scope": "whole", "revision": 1}]:
        raise AssertionError("CLI did not publish the qualified version")
    return transcript


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    maintenance = (PROJECT / "maintenance").resolve()
    if not output.is_relative_to(maintenance) or output == maintenance or output.exists():
        parser.error("Use a new directory inside project maintenance; existing outputs are preserved")
    case = PROJECT / "learning/embodied-intelligence/experiments/coordinator-replay-20261013-bc-loop-01/replay-case.json"
    replay = Replay(case)
    before = protected_snapshot(replay)
    extra_paths = list(case.parent.rglob("*")) + [SUITE / "src/coordinator/replay.py", SUITE / "scripts/check_coordinator_replay.py",
                  SUITE / "scripts/replay_coordination.py", SUITE / "tests/test_coordinator_replay.py"]
    for path in extra_paths:
        if path.is_file():
            before[str(path)] = digest(path.read_bytes())
    tests = unittest.TestSuite([
        unittest.defaultTestLoader.discover(str(SUITE / "tests"), pattern="test_coordinator_workspace.py"),
        unittest.defaultTestLoader.discover(str(SUITE / "tests"), pattern="test_coordinator_replay.py")])
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(tests)
    if not result.wasSuccessful() or result.testsRun == 0 or result.skipped:
        print(stream.getvalue(), file=sys.stderr)
        return 1
    historical = replay.run()
    recorded = json.loads((case.parent / "validated-output/index.json").read_text(encoding="utf-8"))
    if historical["summary"] != recorded["summary"]:
        raise AssertionError("Batch-one historical replay changed")
    output.mkdir(parents=True)
    scenario = run_scenario(output / "demo-workspace")
    cli = cli_smoke(output)
    with closing(sqlite3.connect(f"file:{(output / 'demo-workspace/.coordinator/records.sqlite3').as_posix()}?mode=ro", uri=True)) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    after = protected_snapshot(replay)
    for path in extra_paths:
        if path.is_file():
            after[str(path)] = digest(path.read_bytes())
    changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    programs = [SUITE / "src/coordinator/workspace.py", SUITE / "scripts/coordinate_workspace.py",
                SUITE / "scripts/demo_coordinator_workspace.py", Path(__file__), SUITE / "tests/test_coordinator_workspace.py"]
    validation = {"batch": "coordinator_batch_2", "status": "passed" if not changed and integrity == "ok" else "failed",
                  "client_date": "2026-10-13", "client_timezone": "Asia/Shanghai", "evidence_kind": "synthetic_behavior_and_read_only_historical_regression",
                  "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                  "tests": {"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped)},
                  "scenario": scenario["results"], "cli_calls": len(cli), "sqlite_integrity": integrity,
                  "batch1_regression": {"status": "unchanged", "summary": historical["summary"]},
                  "protected_sources": {"files_checked": len(before), "changed_paths": changed,
                                        "before_digest": digest(json.dumps(before, sort_keys=True).encode("utf-8")),
                                        "after_digest": digest(json.dumps(after, sort_keys=True).encode("utf-8"))},
                  "program_sources": [{"path": p.relative_to(PROJECT).as_posix(), "sha256": digest(p.read_bytes())} for p in programs],
                  "limitations": ["演示与行为测试是虚构文件；真实备课只读回放，未切换正式学习入口。",
                                  "本地操作员声明角色；没有宿主身份认证或恶意共享文件系统隔离。",
                                  "未验证并发压力、崩溃恢复、自动通知、删除清理或学习效果。"]}
    for name, value in (("validation.json", validation), ("scenario.json", scenario), ("cli-transcript.json", cli)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "test-output.txt").write_text(stream.getvalue(), encoding="utf-8")
    markdown = f"""# Task & Artifact Coordinator：第二批验收

结果：{validation['status']}。{result.testsRun}项行为检查通过，命令行{len(cli)}次跨进程调用通过，SQLite完整性{integrity}。
{len(before)}份受保护文件前后指纹一致，第一批真实历史回放结论未变。

| 检查情境 | 结果 |
|---|---|
| 草稿和候选出现 | 旧采用版仍可用 |
| 上游更新时已有下游任务 | M1、M3均保留开始时的v1快照 |
| 用v1审查采用v2 | 拒绝：receipt_version_mismatch |
| AG3对v2局部补核并明确继承M1范围 | v2采用成功；M3直接检查与M1继承分开记录 |
| 上游只改M3 | M1无输入复核事项，正常提交和采用 |
| M3旧输入输出 | 标记upstream_changed；局部相容确认、专业确认后采用 |
| 多产物整组采用中一项不合格 | 所有指针均不更新 |
| 新输入与下游候选同组采用 | 依据最终集合检查，合格后一次提交 |
| 专业回执冲突、用途受限、删除或控制变化 | 检查并拒绝相关操作 |

详细记录：[验收JSON](validation.json)、[演示交接与请求](scenario.json)、[命令行交接](cli-transcript.json)、[测试输出](test-output.txt)。

本批提供可调用的文件协调接口，元数据位于显式初始化工作区的.coordinator目录。原专业文件保存原路径，内容不复制进数据库。
专业角色确认与AG0交付集合采用分开；所有权限检查基于可信本地操作员的角色绑定，不声称宿主认证。
真实文件模式要求外部控制门禁，控制来源变化时旧投影失效；现有学习state/control/current/plan没有切换到本工具。
第三批的并发压力、故障注入和恢复尚未执行；没有自动派发Agent或生成专业审查结论。
"""
    (output / "report.md").write_text(markdown, encoding="utf-8")
    print(f"{validation['status']}: {result.testsRun} tests; {len(cli)} CLI calls; {len(before)} protected files unchanged.")
    print(f"Report: {output / 'report.md'}")
    return 0 if validation["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
