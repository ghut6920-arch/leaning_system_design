"""创建或查看明确标记的 B1 虚构演示空间；不会安装 Skill 或执行教学。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from runtime.learning_store import LearningStore
from runtime.personal_learning import PersonalLearningEntry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--report", type=Path, help="可选精简演示报告，只写入套件 validation 目录")
    arguments = parser.parse_args()
    workspace = arguments.workspace.resolve()
    if workspace == ROOT or workspace.is_relative_to(ROOT):
        parser.error("演示工作区须独立于可分发套件")
    store = LearningStore(workspace)
    initialized = store.init_workspace()
    if initialized["status"] not in ("committed", "ok"):
        print(json.dumps(initialized, ensure_ascii=False))
        return 1
    if initialized["state_revision"] == 0:
        snapshot = json.loads((ROOT / "fixtures/synthetic-baseline.json").read_text(encoding="utf-8-sig"))
        if snapshot.get("synthetic") is not True:
            print(json.dumps({"status": "rejected", "reason": "B0 fixture must be explicitly synthetic."}, ensure_ascii=False))
            return 1
        snapshot["synthetic_only"] = True
        originals = (ROOT / "fixtures/originals.md").read_text(encoding="utf-8-sig")
        saved = store.import_fixture(snapshot, {"originals.md": originals})
        if saved["status"] != "committed":
            print(json.dumps(saved, ensure_ascii=False))
            return 1
    # 新建适配器并读回已经保存的数据，不依赖先前 Python 内存快照。
    reopened = LearningStore(workspace)
    context = reopened.read_context()
    entry = PersonalLearningEntry(reopened)
    resume = entry.resume(activity_id="FIX-activity")
    route = entry.route("评分")
    integrity = reopened.check_integrity()
    result = {
        "batch": "B1", "synthetic_only": True, "teaching": False,
        "workspace": str(workspace), "state_revision": context.get("state_revision"),
        "persisted_current_objects": len(context.get("objects", [])),
        "read_after_reopen": context.get("status"), "integrity": integrity.get("status"),
        "resume": {"status": resume.get("status"), "source": resume.get("recovery", {}).get("source"), "needed_inputs": resume.get("needed_inputs", []), "teaching": False},
        "route": {"status": route.get("status"), "readiness": route.get("readiness"), "target_skill": route.get("target_skill"), "work_order_created": route.get("work_order_created", False)},
        "limitations": ["26 个对象来自人工夹具，不是用户的课程/表现/预算/授权。", "演示保存与定位，不执行教学、评分或排期；真实宿主未绑定。", "已存在的演示空间只查看，不重填或覆写；已删除的数据不会由此重新导入。"]
    }
    if arguments.report:
        destination = arguments.report.resolve() if arguments.report.is_absolute() else (ROOT / arguments.report).resolve()
        if not destination.is_relative_to((ROOT / "validation").resolve()):
            parser.error("演示报告只写入本套件 validation 目录")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if context.get("status") == "ok" and integrity.get("status") == "ok" else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
