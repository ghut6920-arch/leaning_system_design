"""从任意 cwd 执行 B1 的人工夹具行为检查，保存精简报告与原始测试输出。"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import platform
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class CaseResult(unittest.TextTestResult):
    """精简报告只记录用例名称与结果，不复制任何记录正文。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.cases.append({"case": test.id(), "status": "passed"})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.cases.append({"case": test.id(), "status": "failed"})

    def addError(self, test, error):
        super().addError(test, error)
        self.cases.append({"case": test.id(), "status": "error"})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.cases.append({"case": test.id(), "status": "skipped"})

    def addSubTest(self, test, subtest, error):
        super().addSubTest(test, subtest, error)
        if error is not None:
            self.cases.append({"case": subtest.id(), "status": "failed"})


def output_path(value):
    candidate = Path(value)
    return candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="validation/b1-runtime-report.json")
    parser.add_argument("--output", default="validation/b1-runtime-output.txt")
    arguments = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_b1_runtime.py")
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CaseResult)
    result = runner.run(suite)
    report_path, raw_path = output_path(arguments.report), output_path(arguments.output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(stream.getvalue(), encoding="utf-8")
    from runtime.learning_store import SCHEMA_VERSION, STORE_VERSION
    report = {
        "batch": "B1",
        "client_date": "2026-10-03",
        "client_timezone": "Asia/Shanghai",
        "executor": "scripts/check_b1.py; Python unittest",
        "checker": "B1 独立测试开发子代理",
        "versions": {"shared": SCHEMA_VERSION, "store": STORE_VERSION},
        "synthetic_only": True,
        "status": "passed" if result.wasSuccessful() and not result.skipped else "failed",
        "tests_run": result.testsRun,
        "cases": result.cases,
        "host_versions": {
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "sqlite": sqlite3.sqlite_version,
        },
        "raw_output_path": str(raw_path),
        "limitations": [
            "只使用 B0 人工夹具与隔离临时目录，没有真实课程或学习者记录。",
            "覆盖 B1 存储、事务、控制和入口恢复；B10-05/06/08/12 与 N-B0-03 只执行相关有限切片，未判整个情境通过。",
            "专业角色为测试配置；未证明真实宿主身份、工具写隔离、旧输出拦截或多 Agent 运行网络。",
            "删除只验证本组件可控 SQLite 内容，不承诺删除外部会话历史、用户副本、备份或调用方已持有的内存。",
            "导出为内存返回；本次未创建外部导出文件或验证外部文件管理。",
            "并发检查仅两个线程、两个实际 SQLite 连接争同一 state_revision；未作长期并发或分布式压力测试。",
            "失败注入验证单事务回滚和重新打开；未模拟断电、操作系统崩溃或磁盘硬件故障。",
            "SK00 为骨架；教学、评分、计划、策略选择与 V1—V4 学习效果仍未实现或验证。",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B1: {report['status']}; {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped.")
    print(f"Report: {report_path}")
    print(f"Test output: {raw_path}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
