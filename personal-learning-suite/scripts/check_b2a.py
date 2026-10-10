"""从任意 cwd 运行 B2a 有限虚构行为检查，保存精简报告和原始输出。"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import platform
import sqlite3
import sys
import unittest

from check_b1 import CaseResult, output_path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="validation/b2a-runtime-report.json")
    parser.add_argument("--output", default="validation/b2a-runtime-output.txt")
    args = parser.parse_args()
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_b2a_goals.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CaseResult).run(tests)
    report_path, raw_path = output_path(args.report), output_path(args.output)
    for path in (report_path, raw_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(stream.getvalue(), encoding="utf-8")
    from runtime.learning_goals import INPUT_VERSION, REPORT_VERSION
    from runtime.learning_store import SCHEMA_VERSION, STORE_VERSION
    report = {
        "batch": "B2a",
        "client_date": "2026-10-03",
        "client_timezone": "Asia/Shanghai",
        "executor": "scripts/check_b2a.py; Python unittest",
        "checker": "B2a 独立测试开发子代理（负责测试与报告，不编辑目标程序）",
        "versions": {"shared": SCHEMA_VERSION, "store": STORE_VERSION, "input": INPUT_VERSION, "report": REPORT_VERSION},
        "synthetic_only": True,
        "status": "passed" if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else "failed",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "cases": result.cases,
        "host_versions": {
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "sqlite": sqlite3.sqlite_version,
        },
        "raw_output_path": str(raw_path),
        "limitations": [
            "只使用 FIX 虚构目标、来源、授权和隔离临时目录，没有真实课程、学习者或原答。",
            "检查的是候选结构、输入核验声明、要求作用域、版本规则和 B1 保存接缝；程序不核学科内容真伪。",
            "preview 的 complete 和 reliable 只表示所给记录支持当前候选；专业采用、学习者判断、承诺生效与实际限制均不由预览执行。",
            "保存测试显式模拟 FIX AG1 人工核对、授权与采用依据；角色配置和夹具授权不是宿主身份认证或真实授权。",
            "版本保留与重核只是候选建议，不复制 Judgment，不自动生成补测或倒判旧答。",
            "本次未验证真实 Skill 学习效果、完整 B10 情境、V1—V4 或四 Agent／七 Skill 运行网络。",
            "本报告与原始输出单独保存为 B2a 文件，不覆盖 B0/B1 历史校验报告。",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B2a: {report['status']}; {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped.")
    print(f"Report: {report_path}")
    print(f"Test output: {raw_path}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
