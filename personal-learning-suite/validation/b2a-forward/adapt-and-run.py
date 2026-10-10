"""Adapt independently authored fictional candidates without changing their goals."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SUITE = HERE.parents[1]


def known(value):
    return {"status": "known", "value": value}


semantic = json.loads((HERE / "candidate.semantic.json").read_text(encoding="utf-8"))
sources = copy.deepcopy(semantic["objects"][:2])
for source in sources:
    read = source["read_scope"]
    source["read_scope"] = known("；".join(f"{key}: {value}" for key, value in read.items()))
    if isinstance(source["claims"], dict):
        source["claims"] = [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in source["claims"].items()]
    old_verification = copy.deepcopy(source["verification"])
    source["verification"] = known({
        "recorded_status": "supported_for_fixture",
        "method": "开发夹具人工声明；A 与虚构用户输入对照，B 按给定定义手工枚举四种布尔输入",
        "scope": "只支持本虚构开发试用的个人用途和两个布尔输入异或语义，不支持正式课程标准或具体配置语言执行",
        "limitations": "不是实际 AG2 身份、部署、独立专业回执、宿主绑定或正式采用；程序不核验学科真伪",
        "raw_declaration": old_verification,
    })

goal = copy.deepcopy(semantic["objects"][2])
goal["scope"] = ["a、b 均为布尔量", "个人近期配置校验用途的语言无关异或规则草稿及同输入解释"]
goal["excluded_scope"] = copy.deepcopy(goal["evidence_requirements"][0]["cannot_infer"])
goal["allowed_resources"] = known(goal["allowed_resources"])
goal["context_conditions"] = known(goal["context_conditions"])
for requirement in goal["requirements"]:
    requirement["object_scope"] = ["a、b ∈ {false,true}", "当前同一规则草稿与同输入说明"]
for prerequisite in goal["prerequisites"]:
    prerequisite["dependency_kind"] = {"necessary": "necessary", "accompanying": "companion"}[prerequisite.pop("kind")]
    prerequisite["requirement_ids"] = prerequisite.pop("affected_requirement_ids")
    prerequisite["capability"] = prerequisite.pop("text")
    prerequisite["task_resource_reason"] = prerequisite.pop("missing_consequence")
    prerequisite["tool_substitution"] = "定义和许可布尔语法文档可伴随查阅；工具不代替学习者组织规则与解释理由"
    prerequisite["sufficiency_and_return"] = prerequisite.pop("sufficiency")
    prerequisite["learner_state"] = {"status": "unknown", "reason": "虚构用户未提供学习表现；没有学习历史不能推断此前置不会"}

joint = goal["evidence_requirements"][0]
goal["evidence_requirements"] = []
for requirement in goal["requirements"]:
    rid = requirement["requirement_id"]
    goal["evidence_requirements"].append({
        "requirement_id": rid,
        "support_claim": joint["intended_conclusion"] + "；此项只检查 " + rid,
        "required_operations": copy.deepcopy(requirement["key_operations"]),
        "observable_product": requirement["product"] + "。两项仍引用同一综合草稿；分字段不新增独立样本。",
        "allowed_help": known(joint["resource_and_help_conditions"]),
        "task_coverage": [joint["coverage"], "每项按自己 criterion 检查；一项成功不抵消另一项关键错误"],
        "cannot_infer": copy.deepcopy(joint["cannot_infer"]),
        "requirement_source_refs": copy.deepcopy(joint["requirement_source_refs"]),
        "content_basis_refs": copy.deepcopy(joint["content_basis_refs"]),
    })
goal["adoption"] = copy.deepcopy(semantic["p_goal_view"]["adoption"])

course_map = {
    "topics": [{"topic": node["title"], "final_task": node["coverage"], "status": node["depth"]} for node in semantic["coarse_map"]["nodes"]],
    "deferred_goals": [{"topic": node["title"], "provisional_scope": node["coverage"] + "；" + node["depth"], "refine_when": semantic["coarse_map"]["refinement_trigger"]} for node in semantic["coarse_map"]["nodes"][2:]],
    "refine_triggers": [semantic["coarse_map"]["refinement_trigger"]],
    "dependencies_and_unknowns": copy.deepcopy(semantic["coarse_map"]),
}
unresolved = [{
    "decision_needed": item["item"] + "：" + item["impact"],
    "owner": item["owner"],
    "next_trigger": item["trigger"],
    "scope_requirement_ids": [],
    "scope_reason": "当前仅是受手工内容声明支持的虚构语义目标候选；此项限制正式使用/具体执行，不堵住已明确的候选语义范围",
} for item in semantic["pending_items"]]
package = {
    "input_version": "pl-goals-input/0.1.0",
    "synthetic_only": True,
    "mode": "design",
    "goal": goal,
    "sources": sources,
    "course_map": course_map,
    "unresolved_items": unresolved,
    "original_semantic_candidate": "validation/b2a-forward/candidate.semantic.json",
    "adaptation_notes": [
        "只按公开接口转换 read_scope、claims、Fact、scope、逐要求证据与前置键名；原始虚构请求未改",
        "supported_for_fixture 仅是原手工开发核验声明的适配，不是 AG2 采用或程序生成的新事实",
        "原 A claims 路径提示保留为语义 locator；输入适配为有原键标签的列表后 locator 不是严格 JSON Pointer",
        "不采用任何既有 b2a fixture 的预设目标或判据",
    ],
}
changed = copy.deepcopy(package)
changed["mode"] = "revise"
changed["previous_goal"] = copy.deepcopy(goal)
changed["change"] = {
    "kind": "session_budget_only",
    "reason": "虚构用户今天只有 3 分钟，明确继续相同目标，并请求先看示范；预算交 SK05，示范接触交 AG0/AG2 记录，目标和判据保持原文原修订",
    "requirement_mapping": [{"from_requirement_ids": [req["requirement_id"]], "to_requirement_ids": [req["requirement_id"]], "relation": "unchanged"} for req in goal["requirements"]],
}
changed["session_change_view"] = json.loads((HERE / "session-change.semantic.json").read_text(encoding="utf-8"))

for filename, value in [("input.json", package), ("input-session-change.json", changed)]:
    (HERE / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

runs = []
for input_name, output_name in [("input.json", "raw-output.json"), ("input-session-change.json", "raw-session-output.json")]:
    command = [sys.executable, "-X", "utf8", str(SUITE / "src/runtime/learning_goals.py"), "--input", str(HERE / input_name)]
    result = subprocess.run(command, capture_output=True, encoding="utf-8", check=False)
    (HERE / output_name).write_text(result.stdout, encoding="utf-8")
    (HERE / (output_name + ".stderr.txt")).write_text(result.stderr, encoding="utf-8")
    output = json.loads(result.stdout)
    runs.append({"input": input_name, "output": output_name, "exit_code": result.returncode, "review_state": output["review_state"], "errors": output["errors"], "reliable_requirement_ids": output["reliable_requirement_ids"], "compatibility": output["compatibility"], "planning_handoff": output["planning_handoff"], "boundaries": output["boundaries"]})

checks = {
    "synthetic_only": package["synthetic_only"] and changed["synthetic_only"],
    "exact_goal_reused_after_change": changed["goal"] == changed["previous_goal"] == package["goal"],
    "goal_revision": changed["goal"]["revision"],
    "criterion_revisions": {req["requirement_id"]: req["criterion_revision"] for req in goal["requirements"]},
    "time_requirement_after_change": changed["goal"]["time_requirements"],
    "demonstration_visibility": changed["session_change_view"]["demo_request_view"]["visibility"],
    "demonstration_actual_display": changed["session_change_view"]["demo_request_view"]["actual_display"],
    "performance_or_judgment_objects_created": any(obj["type"] in {"PerformanceEvent", "Judgment", "PlanCommitment"} for obj in semantic["objects"]),
    "cli_candidate_matches_input_exactly": all(json.loads((HERE / output_name).read_text(encoding="utf-8"))["goal_candidate"] == input_value["goal"] for input_value, output_name in [(package, "raw-output.json"), (changed, "raw-session-output.json")]),
    "joint_product_and_original_two_requirement_ids_retained": {req["requirement_id"] for req in goal["requirements"]} == {req["requirement_id"] for req in semantic["objects"][2]["requirements"]},
}
(HERE / "actual-checks.json").write_text(json.dumps({"runs": runs, "local_checks": checks}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"runs": runs, "local_checks": checks}, ensure_ascii=False, indent=2))
