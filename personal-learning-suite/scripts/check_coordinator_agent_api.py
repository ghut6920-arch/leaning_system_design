"""Verify the small daily surface without changing real coordination records."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

SUITE = Path(__file__).resolve().parents[1]
PROJECT = SUITE.parent
sys.path.insert(0, str(SUITE / "src"))
from coordinator.agent_api import AgentCoordinator, API_VERSION
from coordinator.complete import TaskArtifactCoordinator
from coordinator.workspace import FileControlGate, encode, sha
from check_coordinator_complete import link_check


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    root = PROJECT / "learning/embodied-intelligence"
    # Preserve every actual learning file and all saved earlier acceptance.
    protected = [p for directory in [root, *[PROJECT / "maintenance" / name for name in (
        "coordinator-batch2-20261013", "coordinator-batch3-20261013", "coordinator-completion-20261013",
        "coordinator-report-20261013", "coordinator-task-status-20261013")]] for p in directory.rglob("*") if p.is_file()]
    before = {str(p): sha(p.read_bytes()) for p in protected}
    tests = unittest.TestLoader().discover(str(SUITE / "tests"), pattern="test_coordinator_*.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(tests)
    (output / "test-output.txt").write_text(stream.getvalue(), encoding="utf-8")
    if not result.wasSuccessful():
        print(stream.getvalue())
        raise AssertionError("Coordinator tests failed")
    process = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SUITE / "scripts/check_b0.py")],
                             capture_output=True, text=True, encoding="utf-8", timeout=40,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if process.returncode:
        raise AssertionError(process.stdout + process.stderr)
    save(output / "shared-contract-check.json", json.loads(process.stdout))
    c = TaskArtifactCoordinator(root, FileControlGate(root, root / "coordination/control.json"))
    session = c.bind_local_operator("AG0")
    api = AgentCoordinator(c)
    state = c.status(session)
    task = "bc-navigation-v2"
    detailed = c.boundary(session, task)
    daily = api.desk(session, task_id=task)
    # Character counts describe returned views, not model tokens, cost or speed.
    sizes = {"measurement": "canonical_JSON_characters_no_whitespace_ensure_ascii_false",
             "whole_registered_state": len(encode(state)), "whole_daily_desk": len(encode(api.desk(session))),
             "same_task_detailed_boundary": len(encode(detailed)), "same_task_daily_desk": len(encode(daily)),
             "guide_characters": len((SUITE / "specs/coordinator-agent-guide.md").read_text(encoding="utf-8")),
             "internal_protocol_characters": len((SUITE / "specs/coordinator-protocol.md").read_text(encoding="utf-8")),
             "limits": "每日摘要省略内部证据，详细视图保留；不同用途的数据量比较，不代表全部上下文或耗时降低。"}
    calls = []
    targets = [(role, ["desk"]) for role in ("AG0", "AG1", "AG2", "AG3")]
    targets += [("AG0", ["desk", "--task", task]), ("AG0", ["alerts", "--consumer", "agent-api-acceptance"]),
                ("AG2", ["inputs", "--task", task]), ("AG0", ["inspect", "--task", task])]
    for role, arguments in targets:
        prefix = [sys.executable, "-B", "-X", "utf8", str(SUITE / "scripts/coordinate_agents.py"), "--workspace", str(root), "--role", role]
        cli = subprocess.run(prefix + arguments, capture_output=True, text=True, encoding="utf-8", timeout=40,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        response = json.loads(cli.stdout)
        if cli.returncode or response["status"] != "ok":
            raise AssertionError(f"Actual daily CLI failed: {response} {cli.stderr}")
        if arguments[0] == "inputs":
            # No duplicate professional text in a maintenance report.
            for item in response["inputs"]:
                content = item.pop("text", None)
                if content is not None:
                    item["text_characters"] = len(content)
                    item["text_sha256"] = sha(content.encode("utf-8"))
        calls.append({"role": role, "arguments": arguments, "response": response})
    manifest = json.loads((root / "framework-manifest.json").read_text(encoding="utf-8-sig"))
    drift = [e["path"] for e in manifest["entries"] if sha((root / e["path"]).read_bytes()) != e["sha256"]]
    paths = [root / n for n in ("COORDINATION.md", "AGENTS.md", "MODEL_ENTRY.md", "FRAMEWORK.md")]
    paths += [SUITE / "specs/coordinator-agent-guide.md", SUITE / "specs/coordinator-protocol.md", *list((SUITE / "src/agents").glob("*.md"))]
    links = link_check(paths)
    changed = [str(Path(p).relative_to(PROJECT)) for p, digest in before.items() if not Path(p).is_file() or sha(Path(p).read_bytes()) != digest]
    if drift or links or changed:
        raise AssertionError({"manifest_drift": drift, "links": links, "protected_changes": changed})
    validation = {"status": "passed", "version": API_VERSION,
                  "tests": {"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped)},
                  "actual_readonly_cli_calls": len(calls), "actual_state_revision": state["state_revision"],
                  "actual_tasks": len(state["tasks"]), "actual_artifact_versions": len(state["artifacts"]), "unresolved_impacts": len(state["impacts"]),
                  "protected_files_checked": len(before), "protected_changed_paths": changed,
                  "actual_database_sha256_before": before[str(c.db_path)], "actual_database_sha256_after": sha(c.db_path.read_bytes()),
                  "framework_entries_checked": len(manifest["entries"]), "link_errors": links, "returned_view_sizes": sizes,
                  "program_sources": [{"path": str(p.relative_to(PROJECT)), "sha256": sha(p.read_bytes())} for p in (
                      SUITE / "src/coordinator/agent_api.py", SUITE / "src/coordinator/workspace.py",
                      SUITE / "scripts/coordinate_agents.py", SUITE / "scripts/check_coordinator_agent_api.py", SUITE / "tests/test_coordinator_agent_api.py")],
                  "limits": ["日常写入闭环和故障测试使用明确标记的虚构资料。", "实际学习目录仅只读核对，不重放专业意见或改变采用。", "没有实测完整模型上下文、时间、费用或学习效果。", "提示仍通过宿主拉取，不自动进入正在推理的上下文。"]}
    save(output / "validation.json", validation)
    save(output / "cli-transcript.json", calls)
    save(output / "daily-desk.json", api.desk(session))
    save(output / "returned-view-sizes.json", sizes)
    (output / "report.md").write_text(f"# 协调器日常接口优化验收\n\n状态：通过。{result.testsRun}项检查通过，错误/失败/跳过均为0。{len(calls)}次实际目录只读CLI查询成功，{len(manifest['entries'])}份框架指纹及入口链接通过。\n\n日常只看desk、alerts和固定inputs，明确意图通过do提交；程序填写状态号、指纹、指针及回执匹配，职业判断仍由原AG0–AG3负责。prepare/apply可选；提交结果不明查saved。工作状态保持running/submitted/blocked及实际回执。\n\n保留原版本、依赖、审查、冲突、事务与恢复门禁；冻结控制/正文在实际写事务内核对，原提交成功不依赖后续状态查询。提示按角色及任务依赖过滤，读取不自动ack。\n\n验收时真实状态revision {state['state_revision']}，任务{len(state['tasks'])}项、版本{len(state['artifacts'])}份、未解决影响{len(state['impacts'])}项；真实数据库及{len(before)}份受保护文件字节未变。这是工具调用时的登记集合快照。\n\n返回数据字符计数见returned-view-sizes.json：同一任务详细边界{sizes['same_task_detailed_boundary']}字符，日常摘要{sizes['same_task_daily_desk']}字符。计数只描述返回数据，不代表总模型上下文、时间、费用或学习效果。详细证据仍可按需读取。\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "tests": result.testsRun, "actual_readonly_cli_calls": len(calls), "report": str(output / "report.md")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
