"""Batch-three acceptance, preserving historical outputs and real learning records."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest

SUITE = Path(__file__).resolve().parents[1]
PROJECT = SUITE.parent
sys.path.insert(0, str(SUITE / "src"))
from coordinator.reliability import ReliableCoordinator, RELIABILITY_VERSION
from coordinator.replay import Replay, digest
from demo_coordinator_workspace import Workflow, run_scenario
from check_coordinator_replay import protected_snapshot
from check_coordinator_workspace import cli_smoke


def snapshot(replay):
    result = protected_snapshot(replay)
    extra = list(replay.case_path.parent.rglob("*")) + list((PROJECT / "maintenance/coordinator-batch2-20261013").rglob("*"))
    extra += [SUITE / "src/coordinator/replay.py", SUITE / "scripts/check_coordinator_replay.py",
              SUITE / "scripts/replay_coordination.py", SUITE / "tests/test_coordinator_replay.py"]
    for path in extra:
        if path.is_file():
            result[str(path)] = digest(path.read_bytes())
    return result


def persistent_wait_demo(root):
    w = Workflow(root, coordinator_class=ReliableCoordinator)
    c = w.coordinator
    c.clock_ms = lambda: 1000
    old = w.candidate("source")["ref"]
    owner = w.confirm(old)
    w.adopt(old, [owner])
    w.register("producer", "source")
    w.op("AG2", "start", task_id="producer")
    w.op("AG0", "register", id="waiter", assignee="AG1", task_kind="production", scope=["whole"], intended_use="teaching",
         output={"id": "dependent-output", "type": "ActivitySpec", "requires_ag3_review": False},
         inputs=[{"id": "source", "policy": "after_task", "producer_task_id": "producer", "scope": ["whole"], "intended_use": "teaching"}],
         wait_timeout_ms=500)
    waiting = w.op("AG1", "start", task_id="waiter")
    w.op("AG2", "finish", task_id="producer", phase="failed", reason="Fabricated execution failure")
    (root / "staging").mkdir()
    (root / "staging/unregistered.txt").write_text("Fabricated unregistered staged file; inspection must not adopt or delete it.", encoding="utf-8")
    return {"evidence_kind": "synthetic_demo", "clock": "injected_constant_1000_for_reproducibility",
            "trace": w.trace, "initial_wait": waiting, "state": c.status(w.sessions["AG0"]),
            "events": c.events(w.sessions["AG0"]), "recovery": c.recover(w.sessions["AG0"], scan_roots=["staging"])}


def extend_cli(output, transcript):
    root = output / "cli-workspace"
    prefix = [sys.executable, "-B", "-X", "utf8", str(SUITE / "scripts/coordinate_workspace.py"), "--workspace", str(root), "--role", "AG0"]
    cursor = 0
    for arguments in (["events"], ["events", "--after-sequence", "CURSOR"],
                      ["operation", "--operation-id", "cli-operation-5"], ["recover", "--scan-root", "materials"]):
        arguments = [str(cursor) if a == "CURSOR" else a for a in arguments]
        result = subprocess.run(prefix + arguments, capture_output=True, text=True, encoding="utf-8", timeout=30)
        if result.returncode != 0:
            raise AssertionError(f"Extended CLI failed: {result.stdout} {result.stderr}")
        response = json.loads(result.stdout)
        if arguments[0] == "events":
            if len(arguments) > 1 and response["events"]:
                raise AssertionError("Unchanged stream produced duplicate events")
            cursor = response["next_sequence"]
        transcript.append({"role": "AG0", "arguments": arguments, "response": response})
    return transcript


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    maintenance = (PROJECT / "maintenance").resolve()
    if output.exists() or output == maintenance or not output.is_relative_to(maintenance):
        parser.error("Use a new directory inside maintenance")
    replay = Replay(PROJECT / "learning/embodied-intelligence/experiments/coordinator-replay-20261013-bc-loop-01/replay-case.json")
    before = snapshot(replay)
    patterns = ["test_coordinator_reliability.py", "test_coordinator_workspace.py", "test_coordinator_replay.py"]
    suite = unittest.TestSuite([unittest.defaultTestLoader.discover(str(SUITE / "tests"), pattern=p) for p in patterns])
    from test_coordinator_reliability import CoordinatorReliabilityTests
    CoordinatorReliabilityTests.observations = []
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    if not result.wasSuccessful() or not result.testsRun or result.skipped:
        print(log.getvalue(), file=sys.stderr)
        return 1
    actual_replay = replay.run()
    recorded = json.loads((replay.case_path.parent / "validated-output/index.json").read_text(encoding="utf-8"))
    if actual_replay["summary"] != recorded["summary"]:
        raise AssertionError("Historical replay changed")
    output.mkdir(parents=True)
    scenario = run_scenario(output / "demo-workspace", coordinator_class=ReliableCoordinator)
    waiting = persistent_wait_demo(output / "wait-workspace")
    cli = extend_cli(output, cli_smoke(output))
    # Inspect the recorded batch-two database without upgrading or modifying it.
    legacy = ReliableCoordinator(PROJECT / "maintenance/coordinator-batch2-20261013/demo-workspace")
    legacy_state = legacy.status(legacy.bind_local_operator("AG0"))
    recorded_legacy = json.loads((PROJECT / "maintenance/coordinator-batch2-20261013/scenario.json").read_text(encoding="utf-8"))["final_state"]
    if legacy_state["adopted_pointers"] != recorded_legacy["adopted_pointers"]:
        raise AssertionError("Legacy adopted pointers changed")
    after = snapshot(replay)
    changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    observations = CoordinatorReliabilityTests.observations
    stress = next(row for row in observations if row["scenario"] == "registration_stress")
    programs = [SUITE / "src/coordinator/reliability.py", SUITE / "src/coordinator/workspace.py",
                SUITE / "scripts/coordinate_workspace.py", SUITE / "scripts/coordinator_fault_worker.py",
                SUITE / "scripts/demo_coordinator_workspace.py", Path(__file__), SUITE / "tests/test_coordinator_reliability.py"]
    validation = {"batch": "coordinator_batch_3", "status": "passed" if not changed else "failed",
                  "client_date": "2026-10-13", "client_timezone": "Asia/Shanghai", "version": RELIABILITY_VERSION,
                  "python": platform.python_version(), "platform": platform.platform(),
                  "evidence_kind": "fabricated_multiprocess_fault_injection_and_read_only_historical_regression",
                  "tests": {"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped)},
                  "multiprocess_observations": observations, "stress": stress, "cli_calls": len(cli),
                  "regressions": {"batch1_summary": actual_replay["summary"], "batch2_adopted_pointers": "unchanged",
                                  "legacy_database_not_upgraded": legacy_state["reliability_upgrade_required"]},
                  "protected_sources": {"files_checked": len(before), "changed_paths": changed,
                                        "before_digest": digest(encode_snapshot(before)), "after_digest": digest(encode_snapshot(after))},
                  "program_sources": [{"path": p.relative_to(PROJECT).as_posix(), "sha256": digest(p.read_bytes())} for p in programs],
                  "limitations": ["真实备课仅只读回放；进程、并发和故障数据均为隔离的虚构文件。",
                                  "硬退出测试不等于断电、磁盘故障或所有网络文件系统验证。",
                                  "通知是本地增量事件，需要宿主轮询/关键节点检查，没有外部消息或后台调度。",
                                  "恢复不推断进程存活、不自动采用、删除、重建专业内容或解除用途限制。",
                                  "仍为本地操作员声明角色，没有宿主身份认证或正式学习入口切换。"]}
    for name, value in (("validation.json", validation), ("scenario.json", scenario), ("wait-recovery-scenario.json", waiting), ("cli-transcript.json", cli)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "test-output.txt").write_text(log.getvalue(), encoding="utf-8")
    text = f"""# Task & Artifact Coordinator：第三批验收

结果：{validation['status']}。{result.testsRun}项检查通过，{len(cli)}次CLI调用通过。
真实多进程压力：{stress['processes']}个进程、{stress['logical_commits']}次独立登记成功，总尝试{stress['total_attempts']}次。
{len(before)}份受保护文件前后指纹一致，包含真实学习原件、第一批回放与第二批历史验收工作区。

| 情境 | 实际结果 |
|---|---|
| 两进程竞争同一采用指针 | 一个提交，一个冲突；仅刷新状态号仍不能绕过预期指针 |
| 四进程重复提交同一operation_id | 一个逻辑版本、一个事件；全部返回同一回执 |
| 不同候选同时提交 | 分配不同修订号；旧采用版保持 |
| 采用事务写完第一个指针时并发读取 | 读到两项旧版；提交后读到两项新版，没有混合集合 |
| 候选插入后、提交前或整组采用中途硬退出 | 事务回滚、旧采用版保留、未发布事件 |
| 提交后、返回前硬退出 | 查询已提交回执，重试不新增版本或事件 |
| 数据库被其他写者锁定 | 有界busy返回，释放后可重试 |
| 上游失败、取消或等待超时 | 相关等待转blocked并返回责任方，不自动降级到旧版 |
| 多层等待链 | 同一次提交中传播失败；无全局等待锁 |
| 未登记文件、仍running任务或源文件缺失 | 只报告，不自动采用/删除/重建/假定失败 |
| 旧工作区扩展升级中途退出 | 原数据保留；显式升级可重试 |

详细记录：[验收JSON](validation.json)、[进程测试输出](test-output.txt)、[提交闭环](scenario.json)、[等待与恢复示例](wait-recovery-scenario.json)、[CLI记录](cli-transcript.json)。

事件与回执在同一SQLite事务中提交，按游标增量查询；无变化返回空事件。正在推理的Agent不会因此自动收到新上下文，宿主仍需在开始、提交、采用等关键节点检查。
等待绑定具体上游任务并带期限；没有后台程序时，过期在状态查询中可见，在refresh/下一次写操作时落盘并生成事件。
本批完成本地并发与进程退出恢复验证，原正式学习入口、权限绑定和教学状态未切换。实际断电、磁盘损坏、网络盘、长期负载和学习收益未验证。
"""
    (output / "report.md").write_text(text, encoding="utf-8")
    print(f"{validation['status']}: {result.testsRun} tests; {len(cli)} CLI calls; {stress['processes']} processes/{stress['logical_commits']} stress commits; {len(before)} protected files unchanged.")
    print(f"Report: {output / 'report.md'}")
    return 0 if validation["status"] == "passed" else 1


def encode_snapshot(value):
    return json.dumps(value, sort_keys=True).encode("utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
