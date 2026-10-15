"""Explicit BC historical metadata onboarding and real preparation-navigation trial.

This is a maintenance integration, not learner activity or a new independent
review. Run from the project root; existing source bodies are never modified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
from coordinator.complete import TaskArtifactCoordinator, COMPLETE_VERSION
from coordinator.workspace import FileControlGate, sha
from coordinator.publication import publish_file

SCOPE = ["BC-first-stage"]
NOTES = "EMB-BC-CLOSED-LOOP-SOURCES-20261012"
RESEARCH = "EMB-BC-CLOSED-LOOP-DISCIPLINARY-20261012"
GOAL = "EMB-G-BC-CLOSED-LOOP-20261012"
DESIGN = "EMB-D-BC-CLOSED-LOOP-20261012"
MATERIAL = "EMB-M-BC-CLOSED-LOOP-20261012"
PLAN = "EMB-P-BC-CLOSED-LOOP-20261012"
NAVIGATION = "EMB-M-BC-COORDINATION-ENTRY-20261013"
NAV_SCOPE = ["version-routing", "review-boundaries"]


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def baseline(root):
    source = "sessions/2026-10-12-bc-preparation-01/preparation-result.md"
    compatibility_source = "materials/bc-closed-loop-20261012/material-uses-v3.md"
    anchor = "AG0已全文读回审查原件并采用有限纸面准备范围，AG1已另存最终安排，保留所有旧版。"
    compatible_anchor = "两者与v1实质内容相同，唯一专业稿修订是Diffusion Policy三个时域的定位"
    evidence = [{"path": source, "sha256": sha((root / source).read_bytes()), "anchor": anchor}]
    compatibility_evidence = [{"path": compatibility_source, "sha256": sha((root / compatibility_source).read_bytes()), "anchor": compatible_anchor}]
    def basis(artifact_id, revision):
        return {"id": artifact_id, "revision": revision, "scope": SCOPE, "intended_use": "teaching"}
    entries = []
    def add(artifact_id, revision, kind, path, *, dependencies=None, adopted=False, reconcile=False):
        entry = {"id": artifact_id, "revision": revision, "type": kind, "path": path,
                 "sha256": sha((root / path).read_bytes()), "intended_use": "teaching", "scope": SCOPE,
                 "basis_refs": dependencies or [], "requires_ag3_review": True, "adopted": adopted,
                 "adoption_evidence": evidence if adopted else [],
                 "adoption_rationale": "登记2026-10-12既有有限纸面备课采用，非新的专业确认或授课事实" if adopted else None}
        if reconcile:
            entry["basis_compatibility"] = [
                {"recheck_id": f"historical-{artifact_id}-{upstream}", "old_ref": {"id": upstream, "revision": 1}, "new_ref": {"id": upstream, "revision": 2},
                 "scope": SCOPE, "intended_use": "teaching", "rationale": "登记原MaterialUse-v3及AG3原意见明确保留的v1→v2定位/读取回执相容；不冒称新独立复核", "evidence": compatibility_evidence}
                for upstream in (RESEARCH, NOTES)]
        entries.append(entry)
    for revision in (1, 2):
        add(NOTES, revision, "SourceFragment", f"materials/bc-closed-loop-20261012/source-notes-v{revision}.md", adopted=revision == 2)
        add(RESEARCH, revision, "SourceFragment", f"materials/bc-closed-loop-20261012/disciplinary-research-v{revision}.md", dependencies=[basis(NOTES, revision)], adopted=revision == 2)
    add(GOAL, 1, "GoalSpec", "goals/bc-closed-loop-20261012/goal-v1.md", dependencies=[basis(RESEARCH, 1), basis(NOTES, 1)], adopted=True, reconcile=True)
    add(DESIGN, 1, "ActivitySpec", "artifacts/bc-closed-loop-20261012/cognitive-design-v1.md", dependencies=[basis(GOAL, 1), basis(RESEARCH, 1)], adopted=True, reconcile=True)
    add(MATERIAL, 3, "MaterialUse", compatibility_source, dependencies=[basis(GOAL, 1), basis(DESIGN, 1), basis(RESEARCH, 2)], adopted=True, reconcile=True)
    add(PLAN, 2, "PlanCommitment", "plan/bc-closed-loop-20261012/first-stage-plan-v2.md", dependencies=[basis(GOAL, 1), basis(DESIGN, 1), basis(MATERIAL, 3), basis(RESEARCH, 2)], adopted=True, reconcile=True)
    return entries


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    root = args.workspace.resolve()
    folder = root / "coordination"
    if not (folder / "maintenance-authorization.md").is_file():
        raise ValueError("Explicit maintenance authorization source missing")
    entries = baseline(root)
    # Before first install record original bytes. Re-runs retain the original
    # baseline and fail if controls change, rather than erase new restrictions.
    projection = folder / "control.json"
    if not projection.exists():
        source_refs = [{"path": p, "sha256": sha((root / p).read_bytes())} for p in ("state/control.md", "coordination/maintenance-authorization.md")]
        save_json(projection, {"state_revision": 11, "paused_ids": [], "deleted_ids": [], "restrictions": [],
                               "source_refs": source_refs, "interpretation": "explicit_current_maintenance_request_and_existing_controls; not_learning_progress"})
    config = {"version": COMPLETE_VERSION, "mode": "manual_files_with_coordination", "evidence_kind": "real_file_metadata",
              "database": ".coordinator/records.sqlite3", "control_projection": "coordination/control.json",
              "entry_artifact_id": PLAN, "entry_intended_use": "teaching", "entry_scope": SCOPE,
              "registered_collection": "BC_closed_loop_preparation_and_coordination_navigation",
              "authority": {"registered_versions_tasks_receipts_pointers": "coordinator_sqlite", "user_controls": "state/control.md",
                            "learning_facts": "state/current.md", "learning_arrangements": "plan/current.md", "professional_semantics": "shared_contract_and_existing_AG0_AG1_AG2_AG3"},
              "role_binding": "trusted_local_operator_attested", "independent_review": False,
              "key_boundaries": ["task_start", "candidate_submit", "review_return", "final_adoption"], "events": "host_pull_then_ack_no_background_agent"}
    if not (folder / "entry.json").exists():
        save_json(folder / "entry.json", config)
    c = TaskArtifactCoordinator(root, FileControlGate(root, projection))
    roles = {r: c.bind_local_operator(r) for r in ("AG0", "AG1", "AG2", "AG3")}
    if not c.db_path.exists():
        c.initialize(evidence_kind="real_file_metadata")
    if (folder / "integration-trace.json").is_file():
        prior = json.loads((folder / "integration-trace.json").read_text(encoding="utf-8"))
        original_entries = prior["trace"][0]["request"]["entries"]
        if any(sha((root / entry["path"]).read_bytes()) != entry["sha256"] for entry in original_entries):
            raise ValueError("Historical integration source changed; do not replay professional decisions")
        c.status(roles["AG0"])
        print(json.dumps({"status": "already_integrated", "coordinator": str(c.db_path), "professional_decisions_replayed": False}, ensure_ascii=False))
        return 0
    trace = []
    def perform(role, action, operation, *, expected="committed", **body):
        request = {"operation_id": operation, "expected_state_revision": c.status(roles["AG0"])["state_revision"], **body}
        result = c.execute(roles[role], action, request)
        trace.append({"role": role, "action": action, "request": request, "result": result})
        if result["status"] != expected:
            raise AssertionError(f"{action}: {result}")
        return result
    perform("AG0", "bootstrap", "integration-baseline", entries=entries)
    baseline_hashes = {entry["path"]: entry["sha256"] for entry in entries}
    inputs = [{"id": item, "policy": "adopted", "scope": SCOPE, "intended_use": "teaching"} for item in (RESEARCH, GOAL, DESIGN, MATERIAL, PLAN)]
    nav_path = "artifacts/coordinator-integration/bc-preparation-navigation-v1.md"
    target = {"id": NAVIGATION, "revision": 1}
    content = """# BC第一阶段备课：协作版本入口 v1

2026-10-13，AG2材料职能，由当前维护模型顺序兼任；只核准备导航与版本路由，不称独立论文复核或教学发生。

用途：preparation_navigation；范围：version-routing、review-boundaries。原学科关系、目标R1–R4、认知M1–M5及备课充分性保持原件中的有限结论。

正式准备入口由协调器按稳定产物ID EMB-P-BC-CLOSED-LOOP-20261012、用途teaching、范围BC-first-stage解析。当前使用者先查询current或在任务开始取得snapshot，不能把正文文件名当永远最新。

本次实际锁定专业研究revision2、Goal revision1、认知设计revision1、材料用途revision3、最终安排revision2；原Goal/认知对研究v1的依据保留，原v1→v2定位相容声明在协调索引中有原文锚点。该登记不把历史AG3审查扩成新发生。

当前主线、可见材料、备用支持与教师参考由原first-stage-plan-v2原件连接，完整正文留在原位置。本导航只提供路由，不复制全套研究或学习记录。

AG1/AG2工作开始锁定输入；新候选提醒依赖方，当前采用版保持；AG3返回确切版本/依据的意见；AG0最后核对回执、变化与预期旧指针再采用。确实依赖新设计才等待，其他工作按原范围继续。

未授课、未展示、无学习者原答或能力判断、未运行训练/仿真/机器人实验，无安装、收费或外部消息。原学习控制和断点不改。
"""
    perform("AG0", "register", "integration-register-navigation-v1", id="bc-navigation-v1", assignee="AG2", task_kind="production", scope=NAV_SCOPE,
            intended_use="preparation_navigation", inputs=inputs, output={"id": NAVIGATION, "type": "MaterialUse", "requires_ag3_review": True, "validation_profile": "utf8"})
    perform("AG2", "start", "integration-start-navigation-v1", task_id="bc-navigation-v1")
    snapshots = c.read_snapshot(roles["AG2"], "bc-navigation-v1")
    # Read actual original bytes through the program, not infer from file names.
    decoded_inputs = [i["content"].decode("utf-8-sig") for i in snapshots]
    if not all(decoded_inputs):
        raise AssertionError("Missing preparation input")
    draft_path = "artifacts/coordinator-integration/drafts/bc-navigation-v1.md"
    (root / draft_path).parent.mkdir(parents=True, exist_ok=True)
    if not (root / draft_path).exists():
        (root / draft_path).write_text(content, encoding="utf-8")
    perform("AG2", "draft", "integration-draft-navigation-v1", task_id="bc-navigation-v1", draft_path=draft_path, planned_changed_scope=NAV_SCOPE)
    request = {"operation_id": "integration-publish-navigation-v1", "expected_state_revision": c.status(roles["AG0"])["state_revision"], "task_id": "bc-navigation-v1", "changed_scope": NAV_SCOPE}
    result = publish_file(c, roles["AG2"], source_path=draft_path, version_path=nav_path, request=request)
    if result["status"] != "committed":
        raise AssertionError(result)
    trace.append({"role": "AG2", "action": "publish", "request": {**request, "path": nav_path}, "result": result})
    perform("AG2", "confirm", "integration-confirm-navigation-v1", ref=target, receipt_id="bc-navigation-owner-v1", scope=NAV_SCOPE, intended_use="preparation_navigation",
            outcome="supported", rationale="当前模型按AG2职能实际读取锁定原件，核对导航版本、原v1/v2相容来源和未执行边界；仅支持备课导航，不新增学科正确性、完整论文复核或学习表现")
    perform("AG0", "register", "integration-register-review-v1", id="bc-navigation-review-v1", assignee="AG3", task_kind="review", scope=NAV_SCOPE, intended_use="preparation_navigation", target_ref=target)
    perform("AG3", "start", "integration-start-review-v1", task_id="bc-navigation-review-v1")
    review_inputs = c.read_snapshot(roles["AG3"], "bc-navigation-review-v1")
    if not any(i["ref"] == target and i["content"].decode("utf-8").startswith("# BC第一阶段备课") for i in review_inputs):
        raise AssertionError("Review target not actually read")
    perform("AG3", "review", "integration-review-navigation-v1", task_id="bc-navigation-review-v1", receipt_id="bc-navigation-review-v1", scope=NAV_SCOPE, intended_use="preparation_navigation",
            outcome="supported", rationale="当前模型顺序兼任AG3，实际读取navigation-v1与锁定依据；从备课入口用途核路由、原版本相容证据和未教学边界，范围充分；不是独立复核，未重新裁定原学科内容或能力")
    pointers = [{"id": NAVIGATION, "intended_use": "preparation_navigation", "scope": s, "revision": None} for s in NAV_SCOPE]
    perform("AG0", "adopt", "integration-adopt-navigation-v1", bundle_id="bc-navigation-adoption-v1", expected_pointers=pointers,
            members=[{"ref": target, "scope": NAV_SCOPE, "intended_use": "preparation_navigation", "receipt_ids": ["bc-navigation-owner-v1", "bc-navigation-review-v1"]}])
    # A genuine second preparation-navigation version demonstrates scoped
    # supplement without pretending that the 2026-10-12 review read new content.
    second = {"id": NAVIGATION, "revision": 2}
    perform("AG0", "register", "integration-register-navigation-v2", id="bc-navigation-v2", assignee="AG2", task_kind="production", base_ref=target,
            planned_changed_scope=["review-boundaries"], scope=NAV_SCOPE, intended_use="preparation_navigation", inputs=inputs,
            output={"id": NAVIGATION, "type": "MaterialUse", "requires_ag3_review": True, "validation_profile": "utf8"})
    perform("AG2", "start", "integration-start-navigation-v2", task_id="bc-navigation-v2")
    c.read_snapshot(roles["AG2"], "bc-navigation-v2")
    second_content = content.replace("协作版本入口 v1", "协作版本入口 v2") + "\n补充审查边界：原AG3 review-v1针对其表列原件；review-v2仅新增读取MaterialUse-v3。后续论文补取失败、未读图表及未知预算继续按原意见限制，不把历史局部补核或本导航核对当完整独立论文验证。\n"
    second_draft = "artifacts/coordinator-integration/drafts/bc-navigation-v2.md"
    if not (root / second_draft).exists():
        (root / second_draft).write_text(second_content, encoding="utf-8")
    second_path = "artifacts/coordinator-integration/bc-preparation-navigation-v2.md"
    request = {"operation_id": "integration-publish-navigation-v2", "expected_state_revision": c.status(roles["AG0"])["state_revision"], "task_id": "bc-navigation-v2", "changed_scope": ["review-boundaries"]}
    result = publish_file(c, roles["AG2"], source_path=second_draft, version_path=second_path, request=request)
    if result["status"] != "committed":
        raise AssertionError(result)
    trace.append({"role": "AG2", "action": "publish", "request": {**request, "path": second_path}, "result": result})
    perform("AG2", "confirm", "integration-confirm-navigation-v2", ref=second, receipt_id="bc-navigation-owner-v2", scope=NAV_SCOPE, intended_use="preparation_navigation", outcome="supported",
            rationale="实际读回v2及原review-v1/v2来源限制；补充仅说明审查读取范围，版本路由不变，支持有限导航；同模型职能核对，不是独立研究或学习表现")
    pointers = [{"id": NAVIGATION, "intended_use": "preparation_navigation", "scope": s, "revision": 1} for s in NAV_SCOPE]
    perform("AG0", "adopt", "integration-reject-old-review-v2", expected="rejected", bundle_id="bc-navigation-old-review-refused", expected_pointers=pointers,
            members=[{"ref": second, "scope": NAV_SCOPE, "intended_use": "preparation_navigation", "receipt_ids": ["bc-navigation-owner-v2", "bc-navigation-review-v1"]}])
    perform("AG0", "register", "integration-register-review-v2", id="bc-navigation-review-v2", assignee="AG3", task_kind="review", scope=NAV_SCOPE, intended_use="preparation_navigation", target_ref=second)
    perform("AG3", "start", "integration-start-review-v2", task_id="bc-navigation-review-v2")
    c.read_snapshot(roles["AG3"], "bc-navigation-review-v2")
    # Original historical review limitations are actually read here.
    original_reviews = [(root / f"assessment/bc-closed-loop-20261012/review-v{i}.md").read_text(encoding="utf-8-sig") for i in (1, 2)]
    if not all(original_reviews):
        raise AssertionError("Missing original review limits")
    perform("AG3", "review", "integration-review-navigation-v2", task_id="bc-navigation-review-v2", receipt_id="bc-navigation-review-v2", scope=NAV_SCOPE, intended_use="preparation_navigation", outcome="supported",
            directly_checked_scope=["review-boundaries"], inherited_scope=["version-routing"], base_receipt_id="bc-navigation-review-v1",
            compatibility_rationale="实际比较导航v1/v2，既有版本路由与依赖没有变化；本次补读原AG3限制并核新增边界段，保留v1路由结论，不把继承部分登记为独立重新阅读",
            rationale="同模型顺序兼任AG3，新增边界与原review-v1/v2实际读取限制一致，只支持准备导航；不扩大原学科核验、教学表现或独立性")
    perform("AG0", "adopt", "integration-adopt-navigation-v2", bundle_id="bc-navigation-adoption-v2", expected_pointers=pointers,
            members=[{"ref": second, "scope": NAV_SCOPE, "intended_use": "preparation_navigation", "receipt_ids": ["bc-navigation-owner-v2", "bc-navigation-review-v2"]}])
    inbox = c.inbox(roles["AG0"], "integration-maintenance")
    perform("AG0", "ack_events", "integration-ack-events", consumer_id="integration-maintenance", through_sequence=inbox["next_sequence"])
    unchanged = [p for p, expected in baseline_hashes.items() if sha((root / p).read_bytes()) != expected]
    if unchanged:
        raise AssertionError(f"Historical originals changed: {unchanged}")
    save_json(folder / "integration-trace.json", {"evidence_kind": "real_file_metadata_and_actual_preparation_navigation", "role_mode": "same_model_sequential_functions_not_independent_review",
              "historical_files_checked": len(baseline_hashes), "historical_changed_paths": unchanged, "trace": trace,
              "actual_read_refs": [i["ref"] for i in snapshots], "final_summary": c.status(roles["AG0"])["summary"],
              "legacy_review_rewritten": False, "learner_activity_created": False})
    (folder / "status.md").write_text("<!-- Generated view; query brief for live state. Not an independent editable pointer source. -->\n" + c.brief(roles["AG0"]), encoding="utf-8")
    print(json.dumps({"status": "completed", "historical_versions": len(entries), "new_navigation_versions": 2,
                      "coordinator": str(c.db_path), "trace": str(folder / "integration-trace.json"), "independent_review": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
