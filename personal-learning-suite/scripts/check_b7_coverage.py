"""Index actual software checks against D11 without declaring complete B10 cases."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Each item is a deliberately limited slice, not a full scenario assertion.
SLICES = {
    "B10-01": ([
        ("test_b4_teaching", "test_reuse_existing_adopted_judgment_can_end_simple_scope_without_new_work"),
        ("test_b4_planning", "test_natural_evidence_closes_simple_need_without_new_check_or_mastery_object"),
    ], "已有采用判断的简单收束与需求闭合", "真实简单目标的正常教学与实际停止理由"),
    "B10-02": ([
        ("test_b3a_assessment", "test_help_after_initial_response_does_not_contaminate_initial_point"),
        ("test_b3a_assessment", "test_only_substituted_operation_is_limited_and_axis_aggregates_mixed"),
        ("test_b3a_assessment", "test_assisted_revision_can_support_only_assisted_scope_and_same_sample"),
    ], "响应点、实际帮助与同题样本解释", "真实题面中全部提示和原答的专业复核"),
    "B10-03": ([
        ("test_b4_planning", "test_ag0_shrink_changes_only_current_scope_not_goal_or_budget"),
        ("test_b2a_goals", "test_operations_resources_scope_and_formal_time_change_are_recheck"),
    ], "授权缩时与正式目标版本分离", "用户真实改目标后的全链采用与安排"),
    "B10-04": ([
        ("test_b2b_materials", "test_two_source_chains_trace_separately_and_four_recoveries_stay_pending"),
        ("test_b2b_materials", "test_unknown_semantic_dependencies_and_sufficient_original_do_not_create_extra_work"),
    ], "双来源纠错与四项待恢复责任", "四恢复面全部完成及撤回错误补课的贯通重放"),
    "B10-05": ([
        ("test_b1_runtime", "test_pause_keeps_confirmed_independent_scope_writable"),
        ("test_b2b_materials", "test_unknown_semantic_dependencies_and_sufficient_original_do_not_create_extra_work"),
    ], "有据无关范围继续、未知语义依赖不推无影响", "缺边依赖与专业结论及计划的组合异常"),
    "B10-06": ([
        ("test_b1_runtime", "test_entry_without_summary_recovers_same_parent_and_unknown_actions"),
        ("test_b4_planning", "test_missing_summary_resume_does_not_invent_success_or_require_whole_restart"),
        ("test_b6_network", "test_resume_without_summary_preserves_original_help_and_adds_no_required_check"),
    ], "可信原答、父任务与未知动作恢复", "真实跨会话恢复成本与用户实际体验"),
    "B10-07": ([
        ("test_b6_network", "test_takeover_allows_only_current_executor_epoch_to_present_learner_packet"),
        ("test_b6_network", "test_takeover_revokes_old_executor_epoch_and_old_claim_receipt"),
    ], "本地串行宿主接管与旧展示拒绝", "外部聊天、真实模型与并行宿主展示拦截"),
    "B10-08": ([
        ("test_b1_runtime", "test_delete_cleans_histories_originals_summary_candidate_validation_and_keeps_unrelated"),
        ("test_b1_runtime", "test_late_deleted_payload_is_rejected_before_payload_can_land"),
        ("test_b6_network", "test_delete_rejects_cached_dispatch_run_and_result_adoption_without_reviving_payload"),
        ("test_b6_network", "test_failed_delete_cleanup_ends_loaded_capabilities_and_keeps_persisted_stop_gate"),
    ], "受管数据库清理、失败停用门与迟到拒绝", "剩余 B 充分/部分/无效三分支及真实外部副本清理边界"),
    "B10-09": ([
        ("test_b4_planning", "test_acceptance_is_pending_and_has_owner_trigger_without_plan"),
        ("test_b6_network", "test_received_is_read_only_and_unaccepted_work_stays_sender_responsibility"),
        ("test_b6_network", "test_partial_acceptance_keeps_unhandled_scope_and_does_not_schedule"),
    ], "已读、接责、处置和未接责任分离", "真实高层不可用、改派与无新依据循环的组合场景"),
    "B10-10": ([
        ("test_b3a_assessment", "test_unknown_last_contact_is_not_inferred_from_current_calendar"),
        ("test_b3a_assessment", "test_displayed_contact_cannot_be_erased_by_declared_no_contact"),
        ("test_b4_teaching", "test_twenty_eight_calendar_days_do_not_override_yesterdays_relevant_help"),
    ], "严格时间与接触条件、当前支持保留", "真实目标内后续使用时点及可核查接触史"),
    "B10-11": ([
        ("test_b3a_assessment", "test_conflicting_prior_judgment_requires_original_review_not_arrival_order"),
        ("test_b3a_assessment", "test_same_id_revision_cannot_overwrite_conflicting_adopted_judgment"),
        ("test_b6_network", "test_upstream_source_revision_change_invalidates_execution_even_if_caller_omits_it"),
    ], "冲突、过期依据与采用门", "完整目标/预算版本建议在真实路径中的联合复核"),
    "B10-12": ([
        ("test_b1_runtime", "test_export_originals_vs_summary_expresses_review_limit"),
        ("test_b1_runtime", "test_failed_delete_keeps_durable_gate_after_restart_until_cleanup"),
        ("test_b3a_assessment", "test_important_review_requires_ag3_and_its_professional_grant"),
    ], "可定位证据导出、删除停用、重要复核权限", "真实查看/质疑交互及可控与不可控副本的实际说明"),
}


def build_index(report_path: Path):
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    if report.get("synthetic_only") is not True or not isinstance(report.get("cases"), list):
        raise ValueError("software_report_required")
    raw = Path(report.get("raw_output_path", ""))
    if not raw.is_file():
        raise ValueError("raw_output_missing")
    raw_text = raw.read_text(encoding="utf-8-sig")
    cases = report["cases"]
    indexed = []
    missing = []
    for case_id, (references, covered, remaining) in SLICES.items():
        selected = []
        for module, method in references:
            found = [case for case in cases if isinstance(case, dict)
                     and isinstance(case.get("case"), str)
                     and case["case"].startswith(module + ".")
                     and case["case"].endswith("." + method)]
            if len(found) != 1:
                selected.append({"test": module + ".*." + method, "status": "not_executed"})
                missing.append(module + ".*." + method)
            else:
                selected.append({"test": found[0]["case"], "status": found[0].get("status", "unknown"),
                                 "raw_output_locatable": method in raw_text})
        executed = all(item["status"] == "passed" and item.get("raw_output_locatable") is True for item in selected)
        indexed.append({"case_id": case_id, "full_scenario_status": "not_executed",
                        "slice_status": "passed" if executed else "incomplete_or_failed",
                        "covered_slice": covered, "remaining_scope": remaining,
                        "tests": selected})
    ready = not missing and all(case["slice_status"] == "passed" for case in indexed)
    return {"batch": "B7", "client_date": "2026-10-04", "client_timezone": "Asia/Shanghai",
            "scope": "B10 software slice traceability", "synthetic_only": True,
            "status": "indexed" if ready else "incomplete",
            "source_report": str(report_path.resolve()), "source_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
            "raw_output_path": str(raw.resolve()), "raw_output_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            "source_versions": report.get("versions", {}), "cases": indexed, "missing_tests": missing,
            "real_validation": {layer: "not_executed" for layer in ("V1", "V2", "V3", "V4")},
            "limitations": ["Indexing checks names, recorded results and raw-output locations; it is not a new execution or independent truth check.",
                            "Passed software slices never declare complete B10 scenarios or real learning efficacy.",
                            "Historical B0 scenario specifications and prior validation reports remain unchanged."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, default=ROOT / "validation/b7-all-runtime-report.json")
    parser.add_argument("--report", type=Path, default=ROOT / "validation/b7-b10-coverage.json")
    args = parser.parse_args()
    try:
        result = build_index(args.source_report)
    except (OSError, ValueError, TypeError):
        print("B7 coverage: input report or raw output unavailable.")
        return 1
    path = args.report.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"B7 coverage: {result['status']}; 12 partial scenarios; full B10 and real V1-V4 not executed.")
    return 0 if result["status"] == "indexed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
