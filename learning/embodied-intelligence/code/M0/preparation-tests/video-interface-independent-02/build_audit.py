"""AI preparation audit utility, revision 1. Writes only this preparation package.
No learning-event/state/goal writes. Existing records are read for hashes only.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
from reference import check_all

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "artifacts/preparation-tests/2026-10-08-video-interface-independent-02"
SUITE = "../../personal-learning-suite/"
DOCS = "../../docs/"
SOURCES = [
    ("AGENTS.md", "全部入口规则"),
    ("MODEL_ENTRY.md", "全部人工文件／接任规则"),
    ("FRAMEWORK.md", "全部路由"),
    ("INTERACTION.md", "全部节奏与等待规则"),
    ("framework-manifest.json", "117个登记指纹核对"),
    ("state/control.md", "当前revision11及范围；历史条目保留"),
    ("state/current.md", "最新revision22，近期历史断点；更早旧进度不纳入"),
    ("goals/M0-video-interface-first-20261006-02.md", "revision1全部R1/R2/R3与允许资源"),
    ("modules/M0/README.md", "M0.2范围与候选性质"),
    ("course/course-map.md", "当前方向、M0用途与候选排期边界"),
    ("plan/needs.md", "唯一R3主线承接区段"),
    ("sessions/2026-10-07-01/raw/M0-feature-sequence-001-initial.txt", "全部真实原答"),
    ("sessions/2026-10-07-01/raw/M0-feature-sequence-001-help-request.txt", "全部真实求助"),
    ("sessions/2026-10-07-01/raw/M0-feature-sequence-001-revision-001.txt", "全部最近真实修订"),
    ("sessions/2026-10-07-01/event-M0-feature-sequence-001.md", "revision3全部帮助顺序与判断边界"),
    ("sessions/2026-10-07-01/checkpoint.md", "revision4完整断点"),
    ("sessions/2026-10-06-02/raw/M0-video-interface-001-initial.txt", "全部真实初答"),
    ("sessions/2026-10-06-02/raw/M0-video-interface-002-initial.txt", "全部真实整体初答"),
    ("sessions/2026-10-06-02/raw/M0-video-interface-002-revision-001.txt", "全部真实修订"),
    ("questions/visible/M0-second-learning-20261007-001-v1.md", "已实际使用题面全文"),
    ("questions/backup/M0-frame-identity-plain-20261007-v1.md", "照片帮助全文，展示事实据事件"),
    ("questions/backup/M0-frame-encoding-order-20261008-v1.md", "已备帮助全文，保持prepared事实"),
    ("materials/M0-video-interface-20261006-02-sources.md", "原材料规格与核验范围全文"),
    ("materials/M0-video-feature-sequence-20261007-sources.md", "后续特征规格与原教师运行边界全文"),
    (SUITE + "contracts/shared-contracts.md", "共同人工对象／证据／职责语义"),
    (SUITE + "src/agents/AG0-coach.md", "完整会话入口职责"),
    (SUITE + "src/agents/AG1-design-planning.md", "完整设计职责"),
    (SUITE + "src/agents/AG2-materials.md", "完整材料职责"),
    (SUITE + "src/agents/AG3-assessment.md", "整体评审及同模型边界"),
    (SUITE + "src/skills/personal-learning/SKILL.md", "完整SK00入口"),
    (SUITE + "src/skills/personal-learning/references/session-entry.md", "完整开始、恢复与控制"),
    (SUITE + "src/skills/personal-learning/references/verification.md", "完整V1–V4边界"),
    (SUITE + "src/skills/learning-goals/SKILL.md", "完整SK01"),
    (SUITE + "src/skills/learning-goals/references/goal-design.md", "完整目标规则"),
    (SUITE + "src/skills/learning-materials/SKILL.md", "完整SK02"),
    (SUITE + "src/skills/learning-materials/references/materials-workflow.md", "完整材料功能与核验"),
    (SUITE + "src/skills/learning-materials/references/domain-checks.md", "完整领域核验规则"),
    (SUITE + "src/skills/learning-teaching/SKILL.md", "完整SK03"),
    (SUITE + "src/skills/learning-teaching/references/design-whole.md", "完整认知主线与整体准备"),
    (SUITE + "src/skills/learning-teaching/references/c0.md", "完整C0"),
    (SUITE + "src/skills/learning-teaching/references/encoding.md", "完整Encoding"),
    (SUITE + "src/skills/learning-teaching/references/post-encoding.md", "完整Post功能入口"),
    (SUITE + "src/skills/learning-assessment/references/product-review.md", "完整整体评审规则；未作新学习评价"),
    (SUITE + "src/skills/learning-planning/SKILL.md", "完整SK05；本次不改实际承诺"),
    (SUITE + "src/skills/learning-strategies/SKILL.md", "完整SK06"),
    (SUITE + "src/skills/learning-strategies/references/selection-adaptation.md", "完整选法适配"),
    (SUITE + "resources/strategies/strategy-index.json", "选中S05/S07/D02及三个Post条目"),
    (SUITE + "resources/strategies/common-constraints.json", "共用约束全文；相同内容按指纹跨包复用"),
    (SUITE + "resources/strategies/encoding/S05.json", "完整包，两载体、研究摘录与所有必要约束"),
    (SUITE + "resources/strategies/encoding/S07.json", "完整必要正文与两载体；共用约束核相同后复用"),
    (SUITE + "resources/strategies/encoding/D02.json", "完整必要正文与两载体；共用约束核相同后复用"),
    (SUITE + "resources/strategies/post/retrieve-relation.json", "完整包，11段源正文、证据条目与条件"),
    (SUITE + "resources/strategies/post/select-method.json", "完整必要正文及全部源段落；同指纹共享段复用"),
    (SUITE + "resources/strategies/post/conditional-update.json", "完整必要正文及全部源段落；同指纹共享段复用"),
    (DOCS + "research/01_Encoding研究报告.md", "§5–10相关结构属性、多维深度、接口、顺序、支架；所选包中的相关证据条目"),
    (DOCS + "designs/AI个人学习系统_工作包5_Encoding_设计方案_v0.md", "§4–5正文；其余所需相关内容按当前专业规则取得"),
    (DOCS + "designs/AI个人学习系统_工作包5_Post-Encoding_设计方案_v0.md", "通过所选完整Post包读取恢复、关系、选用、更新、返回、时间与证据原段落"),
    (DOCS + "designs/AI个人学习系统_工作包6_策略使用规则_设计方案_v0.md", "通过完整Post包读取§5–6，及SK06当前适配规则"),
    (DOCS + "research/Post-Encoding-Dynamics-深度增量研究.md", "通过完整Post包读取§5.3/5.5/7.3/8.1/9.4/10.3/13.1；不声称重读全部研究"),
    (DOCS + "research/Retrieval-Integration-快速矩阵.md", "通过Post包读取结果到操作、组合与边界原段落"),
    (DOCS + "research/post-encoding证据台账与参考文献.md", "所选包内E18/E35/E11–13/E15/E25/E38/E49原条目；未重新核外部研究"),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    teacher = check_all()
    save("teacher-check.json", teacher)
    manifest = json.loads((ROOT / "framework-manifest.json").read_text(encoding="utf-8-sig"))
    framework_bad = [entry["path"] for entry in manifest["entries"]
                     if sha(ROOT / entry["path"]) != entry["sha256"]]
    baseline = json.loads((OUT / "protected-baseline.json").read_text(encoding="utf-8-sig"))
    changed = [entry["path"] for entry in baseline if sha(ROOT / entry["path"]) != entry["sha256"]]
    names = ["01-mainline.md", "02-materials.md", "03-work.md", "04-teacher-reference.md",
             "05-support.md", "06-first-reply-draft.md", "07-self-review.md"]
    texts = {name: (OUT / name).read_text(encoding="utf-8") for name in names}
    expected = [(r, *teacher["packet_rows"][r], *teacher["packet_tags"][r][1:]) for r in range(8)]
    work_rows = [tuple(map(int, row)) for row in re.findall(
        r"^\|\s*(\d+)\s*\|\s*\[(\d+),(\d+)\]\s*\|\s*\(batch-Q,(\d+),(\d+)\)", texts["03-work.md"], re.M)]
    reply_rows = [tuple(map(int, row)) for row in re.findall(
        r"^\|\s*(\d+)\s*\|\s*\[(\d+),(\d+)\]\s*\|\s*\((\d+),(\d+)\)", texts["06-first-reply-draft.md"], re.M)]
    if work_rows != expected or reply_rows != expected:
        raise AssertionError("Printed packet differs from checked teacher data")
    source_data = {
        "date": "2026-10-08", "revision": 1, "mode": "single_model_preparation_only",
        "comparison_preparation_read": False,
        "sources": [{"path_from_learning_root": path, "read_scope": scope, "sha256": sha(ROOT / path)}
                    for path, scope in SOURCES],
        "web": [
            {"url": "https://docs.pytorch.org/docs/2.14/generated/torch.permute.html",
             "scope": "实际2026-10-08核对定义与dims；stable入口重定向此版本"},
            {"url": "https://docs.pytorch.org/docs/2.14/generated/torch.reshape.html",
             "scope": "实际2026-10-08核对同元素数、指定形状与view/copy边界"},
        ],
        "not_claimed": ["研究全文和全部外部引文重核", "全部课程已核", "独立复核", "新原答或教学进度"],
    }
    save("sources.json", source_data)
    title = "# 视频接口单元完整备课 · 单模型独立测试\n\n"
    title += "2026-10-08 · revision1 · 仅供审查，首回复亦为草稿，此次无需作答。\n\n"
    title += "编写与自查为本次同一模型；当前真实进度未修改。依据及有限检查见 sources.json、verification.json。\n\n"
    (OUT / "完整备课.md").write_text(title + "\n\n---\n\n".join(texts[name] for name in names) + "\n", encoding="utf-8")
    save("verification.json", {"status": "audit_in_progress"})
    broken = []
    for document in OUT.glob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if target.startswith(("https://", "http://", "#")):
                continue
            if not (document.parent / target.split("#")[0]).exists():
                broken.append({"file": document.name, "target": target})
    report = {
        "date": "2026-10-08", "revision": 1,
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "executor_and_checker": "same_model; no independent or blind review",
        "framework": {"checked": len(manifest["entries"]), "mismatches": framework_bad},
        "protected_existing_learning_files": {"checked": len(baseline), "changed": changed},
        "teacher_reference": {"passed": teacher["passed"], "failed": teacher["failed"], "details": "teacher-check.json", "torch": teacher["torch"]},
        "printed_packet": {"task_matches": work_rows == expected, "first_reply_matches": reply_rows == expected},
        "local_links": {"broken": broken},
        "prepared_documents": [{"path": name, "sha256": sha(OUT / name)} for name in names + ["完整备课.md"]],
        "code_versions": [{"path": str(path.relative_to(ROOT)), "sha256": sha(path)}
                          for path in Path(__file__).parent.glob("*.py")],
        "validation_scope": {"V1": "teacher content checks plus semantic self-review; finite examples do not prove all model behavior",
                             "V2": "draft prepared; formal teaching/feedback not executed",
                             "V3": "not_executed; no new learner response",
                             "V4": "not_executed; no comparator read or learning-effect/cost comparison"},
    }
    save("verification.json", report)
    print(json.dumps({"passed": teacher["passed"], "framework_checked": len(manifest["entries"]),
                      "protected_checked": len(baseline), "changed": changed, "broken_links": broken}, ensure_ascii=False))
    if framework_bad or changed or broken:
        raise AssertionError("Preparation audit requires review")


if __name__ == "__main__":
    main()
