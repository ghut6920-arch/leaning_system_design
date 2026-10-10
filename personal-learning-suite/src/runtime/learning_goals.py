"""B2a 目标候选的确定性检查与版本比较；只读输入，不作专业采用。"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.contract_rules import PROTOCOL, load_definition, object_refs, walk

INPUT_VERSION = "pl-goals-input/0.1.0"
REPORT_VERSION = "pl-goals-review/0.1.0"
NATURES = {"course_explicit", "user_purpose", "system_suggestion", "pending_clarification"}
CHANGE_KINDS = {"equivalent", "split", "merge", "substantive", "correction", "purpose_change", "session_budget_only"}
FACT_STATES = {"known", "unknown", "not_required", "not_applicable", "not_executed", "deleted"}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive(value: Any) -> bool:
    return type(value) is int and value > 0


def _strings(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value)


def _description(value: Any) -> bool:
    return _text(value) or _strings(value)


def _fact(value: Any) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get("status"), str) or value["status"] not in FACT_STATES:
        return False
    if set(value) - {"status", "value", "reason"}:
        return False
    return "value" in value and value["value"] is not None if value["status"] == "known" else "value" not in value and _text(value.get("reason"))


def _usable_value(value: Any) -> bool:
    """不将已知 0/False 视为缺失；容器和文字需要实际内容。"""
    return value is not None and (bool(value) if isinstance(value, (str, list, dict)) else isinstance(value, (int, float, bool)))


def _ref(value: Any) -> bool:
    return isinstance(value, dict) and _text(value.get("id")) and _positive(value.get("revision")) and ("locator" not in value or _text(value["locator"]))


def _goal_ref(goal: dict[str, Any]) -> dict[str, Any]:
    return {"id": goal["id"], "revision": goal["revision"]}


def _criterion_content(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return {key: item for key, item in value.items() if key not in {"requirement_source_refs", "content_basis_refs"}}


def _strip_locators(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip_locators(item) for item in value]
    if isinstance(value, dict):
        return {key: _strip_locators(item) for key, item in value.items() if key != "locator"}
    return value


def _semantic_goal(goal: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in goal.items() if key not in {"revision", "version_compatibility", "description", "change_reason"}}


def _source_anchor(value: Any) -> bool:
    return _ref(value) or (isinstance(value, dict) and _text(value.get("path"))
                          and _text(value.get("locator")) and _positive(value.get("revision"))
                          and value.get("origin") == "synthetic_fixture")


def _source_state(source: dict[str, Any]) -> tuple[bool, bool]:
    """Read canonical declarations or the unchanged B2a legacy carrier.

    No conversion is performed: a legacy read claim does not establish any
    modality, and supported metadata never establishes subject truth.
    """
    scopes, verification = source.get("read_scope"), source.get("verification")
    common = _fact(source.get("unread_parts")) and _strings(source.get("claims"))
    if isinstance(scopes, dict) and "status" not in scopes:
        complete = common and all(_fact(scopes.get(key)) for key in ("text", "formula", "figure"))
        content = verification.get("content") if isinstance(verification, dict) else None
        complete = (complete and isinstance(content, dict) and _text(content.get("status"))
                    and content["status"] in {"supported", "partial", "pending", "error"})
        if not complete:
            return False, False
        modalities = content.get("required_modalities")
        usable = (_strings(modalities) and set(modalities).issubset({"text", "formula", "figure"})
                  and all(scopes[key]["status"] == "known"
                          and (_description(scopes[key]["value"]) or isinstance(scopes[key]["value"], dict) and bool(scopes[key]["value"]))
                          for key in modalities)
                  and content.get("status") == "supported" and _positive(content.get("checked_revision"))
                  and content["checked_revision"] == source.get("revision")
                  and content.get("reviewer") == "AG2" and _text(content.get("method"))
                  and content["method"] in {"source_comparison", "derivation", "test", "expert_review"}
                  and _text(content.get("scope")) and _strings(content.get("conditions"))
                  and isinstance(content.get("anchor_refs"), list) and bool(content["anchor_refs"])
                  and all(_source_anchor(anchor) for anchor in content["anchor_refs"])
                  and isinstance(content.get("unchecked_scope"), list)
                  and all(_text(item) for item in content["unchecked_scope"]))
        return True, usable
    complete = common and _fact(scopes) and _fact(verification)
    recorded = verification.get("value") if isinstance(verification, dict) else None
    usable = (complete and scopes["status"] == "known" and _text(scopes["value"])
              and verification["status"] == "known" and isinstance(recorded, dict)
              and recorded.get("recorded_status") == "supported_for_fixture"
              and all(_text(recorded.get(key)) for key in ("method", "scope", "limitations")))
    return complete, usable


def review_goal_package(package: Any) -> dict[str, Any]:
    """返回候选报告。可靠子范围仅指输入声明的 FIX 核验记录，非程序内容核验。"""
    report: dict[str, Any] = {
        "report_version": REPORT_VERSION, "input_version": INPUT_VERSION, "schema_version": PROTOCOL,
        "status": "candidate", "synthetic_only": True, "review_state": "invalid",
        "goal_candidate": None, "course_map_candidate": None,
        "reliable_requirement_ids": [], "unresolved_items": [], "errors": [],
        "compatibility": {"status": "not_compared", "preserve_requirement_ids": [], "recheck_requirement_ids": [], "judgment_transfer": "not_executed"},
        "change_notice_candidate": None, "planning_handoff": None,
        "boundaries": {
            "content_verification": "not_executed", "learner_judgment": "not_executed",
            "professional_adoption": "not_executed", "persistence": "not_executed",
            "new_test": "not_proposed", "valid_plan": "not_created",
            "source_record_interpretation": "Existing FIX verification declarations only; this script does not establish content truth.",
        },
    }
    report["work_result_view"] = {
        "view_kind": "local_preview_not_persistable_WorkResult",
        "work_order_ref": {"status": "not_applicable", "reason": "No formal WorkOrder supplied; this is a local read-only preview."},
        "handled_scope": ["FIX目标候选结构与记录条件检查", "有限版本兼容建议"],
        "unhandled_scope": ["实际内容核验", "学习者判断", "真实授权与专业采用", "承诺生效与实际限制执行"],
        "result_refs": [], "limitations": ["仅FIX输入；源核验记录不等于本脚本核验内容；开发检查不等于学习效果。"],
        "adoption_needed": True, "next_owner": "AG1; AG2/AG3 for unresolved professional scopes",
        "next_trigger": "当前控制与授权复核后，由对应专业责任方决定采用或返回具体缺项",
        "compatibility": report["compatibility"], "adoption": {"status": "candidate"},
    }

    def error(code: str, path: str, detail: str) -> None:
        report["errors"].append({"code": code, "path": path, "detail": detail})

    def pending(code: str, path: str, detail: str, scope: list[str] | None = None, owner: str = "AG1") -> None:
        report["unresolved_items"].append({"code": code, "path": path, "decision_needed": detail, "owner": owner, "next_trigger": "提供可定位依据或完成相应专业澄清后重新审阅", "scope_requirement_ids": scope or []})

    if not isinstance(package, dict):
        error("input_shape", "/", "Input must be a JSON object.")
        return report
    if package.get("input_version") != INPUT_VERSION:
        error("input_version", "/input_version", "Unsupported input protocol.")
    if package.get("synthetic_only") is not True:
        error("synthetic_only", "/synthetic_only", "This development slice accepts explicitly fictional data only.")
    if not isinstance(package.get("mode"), str) or package["mode"] not in {"design", "revise", "reuse"}:
        error("mode", "/mode", "Expected design, revise or reuse.")
    if report["errors"]:
        return report

    sources = package.get("sources")
    if not isinstance(sources, list):
        error("sources_shape", "/sources", "sources must be a list of SourceFragment objects.")
        return report
    definition = load_definition()
    source_index: dict[tuple[str, int], dict[str, Any]] = {}

    def public_header(record: Any, kind: str, path: str) -> bool:
        if not isinstance(record, dict):
            error("object_shape", path, f"Expected {kind} object.")
            return False
        if record.get("type") != kind or not _text(record.get("id")) or not str(record.get("id", "")).startswith("FIX-") or not _positive(record.get("revision")):
            error("object_identity", path, "A typed FIX object with positive integer revision is required.")
            return False
        if record.get("schema_version") != PROTOCOL or record.get("owner") not in definition["objects"][kind]["owners"]:
            error("public_contract", path, "Shared protocol and responsible owner must match the shared field source.")
        if not isinstance(record.get("basis_refs"), list):
            error("basis_refs", path + "/basis_refs", "basis_refs must be an explicit list.")
        for field in definition["objects"][kind]["required"]:
            if field not in record:
                pending("missing_public_field", path + "/" + field, f"补齐 {kind} 公共字段 {field}。")
        for item in walk(record):
            if isinstance(item, dict) and "type" not in item and isinstance(item.get("status"), str) and item["status"] in FACT_STATES and not _fact(item):
                error("fact_shape", path, "Fact states require an explicit value or a reason without guessed value.")
        return True

    for i, source in enumerate(sources):
        path = f"/sources/{i}"
        if not public_header(source, "SourceFragment", path):
            continue
        key = source["id"], source["revision"]
        if key in source_index:
            error("duplicate_source", path, "A source revision must appear once.")
        source_index[key] = source
        source_ref = source.get("source_ref")
        if not isinstance(source_ref, dict) or any(not _text(source_ref.get(field)) for field in ("source_id", "declared_revision", "locator", "identity_kind")):
            error("source_ref", path + "/source_ref", "Source identity, declared revision and locator are required.")
        elif source_ref["identity_kind"] != "synthetic" or not source_ref["source_id"].startswith("FIX-"):
            error("synthetic_source", path + "/source_ref", "Only synthetic FIX source identities are accepted.")
        if not _source_state(source)[0]:
            pending("source_record_incomplete", path, "补齐读清范围、主张、既有核验记录和未读部分，打开资料不代表核验。", owner="AG2")

    course_map = package.get("course_map")
    if not isinstance(course_map, dict) or not isinstance(course_map.get("topics"), list) or not course_map["topics"] or not isinstance(course_map.get("deferred_goals"), list) or not _strings(course_map.get("refine_triggers")):
        pending("course_map", "/course_map", "粗地图需有主题/最终任务、暂定远期范围和明确细化触发。")
    else:
        for index, topic in enumerate(course_map["topics"]):
            if not isinstance(topic, dict) or any(not _text(topic.get(field)) for field in ("topic", "final_task", "status")):
                pending("map_topic", f"/course_map/topics/{index}", "主题只提供地图线索；列明对应任务及暂定程度。")
        for index, item in enumerate(course_map["deferred_goals"]):
            if not isinstance(item, dict) or any(not _text(item.get(field)) for field in ("topic", "provisional_scope", "refine_when")):
                pending("deferred_refinement", f"/course_map/deferred_goals/{index}", "远期目标须说明暂定范围与何时细化。")
        report["course_map_candidate"] = copy.deepcopy(course_map)

    supplied_unresolved = package.get("unresolved_items")
    if not isinstance(supplied_unresolved, list):
        error("unresolved_shape", "/unresolved_items", "An explicit unresolved_items list is required.")
        supplied_unresolved = []
    else:
        for index, item in enumerate(supplied_unresolved):
            if not isinstance(item, dict) or any(not _text(item.get(field)) for field in ("decision_needed", "owner", "next_trigger")) or not isinstance(item.get("scope_requirement_ids"), list) or any(not _text(rid) for rid in item["scope_requirement_ids"]):
                error("unresolved_owner", f"/unresolved_items/{index}", "Each unknown needs its decision, owner, trigger and explicit requirement scope.")
            else:
                report["unresolved_items"].append(copy.deepcopy(item))

    goal = package.get("goal")
    if goal is None:
        pending("recent_goal_missing", "/goal", "只有主题地图无法确定近期判据：提供近期内容、具体用途及代表性任务或评分依据。")
        report["review_state"] = "invalid" if report["errors"] else "map_only"
        return report
    if not public_header(goal, "GoalSpec", "/goal"):
        return report
    report["goal_candidate"] = copy.deepcopy(goal)
    report["work_result_view"]["result_refs"] = [_goal_ref(goal)]
    if "adoption" in goal and (not isinstance(goal["adoption"], dict) or goal["adoption"].get("status") != "candidate"):
        error("adoption_not_supported", "/goal/adoption", "The preview cannot announce an adopted professional result.")
    requirements = goal.get("requirements")
    if not isinstance(requirements, list) or not requirements or any(not isinstance(item, dict) for item in requirements):
        error("requirements_shape", "/goal/requirements", "A recent goal needs explicit requirement objects.")
        return report
    ids = [item.get("requirement_id") for item in requirements]
    if any(not _text(rid) for rid in ids) or len(set(ids)) != len(ids):
        error("requirement_identity", "/goal/requirements", "Requirements need unique stable requirement_id values.")
        return report
    all_ids: list[str] = ids
    blocked: set[str] = set()
    for index, item in enumerate(supplied_unresolved):
        if isinstance(item, dict) and isinstance(item.get("scope_requirement_ids"), list):
            if any(rid not in all_ids for rid in item["scope_requirement_ids"]):
                error("unresolved_scope", f"/unresolved_items/{index}/scope_requirement_ids", "Unknown scopes must name current requirements; use an explicit empty list for deferred scopes.")
    available_refs = set(source_index) | {(goal["id"], goal["revision"])}
    prior = package.get("previous_goal")
    if isinstance(prior, dict) and _text(prior.get("id")) and _positive(prior.get("revision")):
        available_refs.add((prior["id"], prior["revision"]))
    for record in sources + [goal]:
        if not isinstance(record, dict):
            continue
        for ref in object_refs(record):
            if not _ref(ref) or (ref["id"], ref["revision"]) not in available_refs:
                pending("object_reference_pending", "/sources-or-goal", "实际依赖引用未能定位准确修订；不能从缺记录推断无依赖。", all_ids)
                blocked.update(all_ids)

    def require(condition: bool, code: str, path: str, detail: str, scope: list[str]) -> None:
        if not condition:
            pending(code, path, detail, scope)
            blocked.update(scope)

    # 顶层双来源是逐要求来源的聚合。只有未在具体要求/判据/前置定位的
    # 顶层引用才按共用依赖处理，避免一个专属缺项封锁其他可靠要求。
    source_scopes: dict[tuple[str, int], set[str]] = {}
    scoped_groups = [(req, [req["requirement_id"]]) for req in requirements]
    scoped_groups += [(req.get("criterion"), [req["requirement_id"]]) for req in requirements]
    if isinstance(goal.get("prerequisites"), list):
        for item in goal["prerequisites"]:
            if isinstance(item, dict):
                item_scope = item.get("requirement_ids", all_ids)
                if not isinstance(item_scope, list) or not item_scope or any(rid not in all_ids for rid in item_scope):
                    item_scope = all_ids
                scoped_groups.append((item, item_scope))
    for group, item_scope in scoped_groups:
        if not isinstance(group, dict):
            continue
        for field in ("requirement_source_refs", "content_basis_refs"):
            for ref in group.get(field, []) if isinstance(group.get(field), list) else []:
                if _ref(ref):
                    source_scopes.setdefault((ref["id"], ref["revision"]), set()).update(item_scope)

    def dual(group: dict[str, Any], path: str, scope: list[str], aggregate: bool = False) -> None:
        for field in ("requirement_source_refs", "content_basis_refs"):
            refs = group.get(field)
            if not isinstance(refs, list) or not refs:
                require(False, "dual_source_missing", path + "/" + field, "要求来源与内容依据须分别引用可定位的 SourceFragment。", scope)
                continue
            for ref in refs:
                ref_scope = scope
                if aggregate and _ref(ref) and (ref["id"], ref["revision"]) in source_scopes:
                    ref_scope = [rid for rid in all_ids if rid in source_scopes[(ref["id"], ref["revision"])]]
                source = source_index.get((ref.get("id"), ref.get("revision"))) if _ref(ref) else None
                if source is None:
                    require(False, "source_reference", path + "/" + field, "来源引用缺失或不能定位所声明修订；不能猜造来源。", ref_scope)
                    continue
                usable = _source_state(source)[1]
                # 读到了哪里与核验支持什么是不同语义，不能用字面相等替代用途核对。
                if not usable:
                    pending("source_verification_pending", path + "/" + field, "相应来源没有足以支持本候选范围的既有核验记录，交 AG2 澄清。", ref_scope, "AG2")
                    blocked.update(ref_scope)

    dual(goal, "/goal", all_ids, aggregate=True)
    for field in ("scope", "excluded_scope"):
        require(_strings(goal.get(field)), "goal_scope", "/goal/" + field, "近期目标须分别列明覆盖与不覆盖范围。", all_ids)
    require(_fact(goal.get("allowed_resources")), "resources", "/goal/allowed_resources", "列明允许工具和资源；独立完成关键操作不自动意味着闭卷。", all_ids)
    require(_fact(goal.get("context_conditions")), "context", "/goal/context_conditions", "明确当前情境条件或未知原因。", all_ids)
    require(_fact(goal.get("time_requirements")), "time_requirements", "/goal/time_requirements", "时间条件必须明确；无延迟/迁移要求可以使用 not_required。", all_ids)
    for field in ("allowed_resources", "context_conditions", "time_requirements"):
        value = goal.get(field)
        if _fact(value) and value["status"] in {"unknown", "not_executed", "deleted"}:
            require(False, "goal_condition_pending", "/goal/" + field, "必要条件尚未明确或可用，保留未决与候选范围。", all_ids)
        if _fact(value) and value["status"] == "known" and not _usable_value(value["value"]):
            require(False, "goal_condition_empty", "/goal/" + field, "known条件需要可用内容，空值不能代表条件已经落实。", all_ids)
    for field in ("allowed_resources", "context_conditions"):
        value = goal.get(field)
        if _fact(value) and value["status"] == "known":
            require(_description(value["value"]), "goal_condition_shape", "/goal/" + field, "资源/情境known值需有非空说明文字或说明列表。", all_ids)

    for index, req in enumerate(requirements):
        rid, path = req["requirement_id"], f"/goal/requirements/{index}"
        scope = [rid]
        for field in ("object_scope", "key_operations"):
            require(_strings(req.get(field)), "requirement_observable", path + "/" + field, "按对象范围与学习者关键操作表达要求。", scope)
        require(_text(req.get("product")), "requirement_product", path + "/product", "列明可检查产物。", scope)
        require(_positive(req.get("criterion_revision")), "criterion_revision", path + "/criterion_revision", "判据必须有正整数内容修订。", scope)
        require(_text(req.get("nature")) and req["nature"] in NATURES, "requirement_nature", path + "/nature", "区分课程明确、用户用途、系统建议与待澄清。", scope)
        if req.get("nature") == "pending_clarification":
            require(False, "requirement_pending", path + "/nature", "待澄清要求保留为候选，不能当作正式课程标准。", scope)
        dual(req, path, scope)
        criterion = req.get("criterion")
        require(isinstance(criterion, dict) and _text(criterion.get("text")), "criterion_text", path + "/criterion", "关键标准须可检验，流畅度、篇幅或运行成功不能替代另一项能力要求。", scope)
        if isinstance(criterion, dict):
            dual(criterion, path + "/criterion", scope)

    prerequisites = goal.get("prerequisites")
    if not isinstance(prerequisites, list):
        require(False, "prerequisites_shape", "/goal/prerequisites", "前置关系须显式列出；确知无前置时可以为空。", all_ids)
    else:
        for index, item in enumerate(prerequisites):
            path = f"/goal/prerequisites/{index}"
            if not isinstance(item, dict):
                require(False, "prerequisite_shape", path, "前置项需有类型、任务/资源理由、替代与返回说明。", all_ids)
                continue
            scope = item.get("requirement_ids", all_ids)
            if not isinstance(scope, list) or not scope or any(rid not in all_ids for rid in scope):
                scope = all_ids
                require(False, "prerequisite_scope", path, "定位本目标版本的具体要求。", scope)
            require(_text(item.get("dependency_kind")) and item["dependency_kind"] in {"necessary", "companion", "background"}, "prerequisite_kind", path, "区分必要、伴随补充与有益背景；背景不能作为进入门槛。", scope)
            for field in ("capability", "task_resource_reason", "tool_substitution", "sufficiency_and_return"):
                require(_text(item.get(field)), "prerequisite_basis", path + "/" + field, "前置必要性针对任务与允许资源说明，并保留补足后的返回连接。", scope)
            require(_fact(item.get("learner_state")), "prerequisite_learner_state", path + "/learner_state", "学习者是否会此前置与此前置是否必要分别表达；未知不等于不足。", scope)
            if item.get("necessity_basis") == "single_failure":
                require(False, "single_failure_dependency", path, "单次失败不能独自证明必要前置关系。", scope)
            dual(item, path, scope)

    evidence = goal.get("evidence_requirements")
    evidence_index: dict[str, dict[str, Any]] = {}
    if not isinstance(evidence, list):
        require(False, "evidence_shape", "/goal/evidence_requirements", "证据要求按 requirement_id 分开表达。", all_ids)
    else:
        for index, item in enumerate(evidence):
            path = f"/goal/evidence_requirements/{index}"
            if not isinstance(item, dict) or item.get("requirement_id") not in all_ids:
                require(False, "evidence_scope", path, "证据要求必须对应近期要求。", all_ids)
                continue
            rid = item["requirement_id"]
            if rid in evidence_index:
                require(False, "duplicate_evidence", path, "每项要求有唯一的证据要求。", [rid])
            evidence_index[rid] = item
            for field in ("support_claim", "observable_product"):
                require(_text(item.get(field)), "evidence_observable", path + "/" + field, "说明要支持的有限结论与可观察产物。", [rid])
            for field in ("required_operations", "task_coverage", "cannot_infer"):
                require(_strings(item.get(field)), "evidence_limit", path + "/" + field, "列明实际调用操作、任务覆盖及不能推出的结论。", [rid])
            require(_fact(item.get("allowed_help")), "evidence_help", path + "/allowed_help", "允许帮助须明确或保持未知，空字段不能等于无帮助。", [rid])
            target = next(req for req in requirements if req["requirement_id"] == rid)
            if _strings(item.get("required_operations")) and _strings(target.get("key_operations")):
                require(set(target["key_operations"]).issubset(set(item["required_operations"])), "evidence_operation_coverage", path + "/required_operations", "证据操作需逐字引用目标关键操作，确保每项关键操作都有可定位证据要求；未对齐处交专业方澄清。", [rid])
            if _fact(item.get("allowed_help")) and item["allowed_help"]["status"] in {"unknown", "not_executed", "deleted"}:
                require(False, "evidence_help_pending", path + "/allowed_help", "未知帮助条件影响该项证据含义，不能默认为独立。", [rid])
            if _fact(item.get("allowed_help")) and item["allowed_help"]["status"] == "known":
                require(_description(item["allowed_help"]["value"]), "evidence_help_empty", path + "/allowed_help", "帮助known值需有非空说明文字或列表；无帮助须明确写出。", [rid])
        for rid in all_ids:
            require(rid in evidence_index, "evidence_missing", "/goal/evidence_requirements", "每项近期要求必须有对应的证据要求。", [rid])

    # 缺失前置依据不说明用户不会；远期未知不封锁不依赖它的当前子范围。
    for item in supplied_unresolved or []:
        if isinstance(item, dict) and isinstance(item.get("scope_requirement_ids"), list):
            blocked.update(rid for rid in item["scope_requirement_ids"] if rid in all_ids)
    report["reliable_requirement_ids"] = [rid for rid in all_ids if rid not in blocked]
    previous = package.get("previous_goal")
    mode = package["mode"]
    if mode in {"revise", "reuse"} and previous is None:
        pending("previous_goal_missing", "/previous_goal", "版本修订/复用须提供准确旧 GoalSpec；否则兼容范围保持待核。", all_ids)
        report["compatibility"]["status"] = "recheck"
        report["compatibility"]["recheck_requirement_ids"] = all_ids
    elif previous is not None:
        if public_header(previous, "GoalSpec", "/previous_goal"):
            _compare(previous, goal, package.get("change"), mode, report, error, pending)
            if mode == "revise" and isinstance(package.get("change"), dict) and package["change"].get("kind") != "session_budget_only" and not report["errors"]:
                report["goal_candidate"]["version_compatibility"] = {"status": "known", "value": copy.deepcopy(report["compatibility"])}
    elif goal["revision"] != 1:
        error("initial_revision", "/goal/revision", "A new fixture goal starts at revision 1; later revisions need previous_goal.")

    report["review_state"] = "invalid" if report["errors"] else "partial" if report["unresolved_items"] else "complete"
    if report["errors"]:
        report["reliable_requirement_ids"] = []
    return report


def _compare(previous, goal, change, mode, report, error, pending):
    current_ids = [item["requirement_id"] for item in goal["requirements"]]
    compatibility = report["compatibility"]
    compatibility.update(status="recheck", previous_goal_ref=None, current_goal_ref=_goal_ref(goal), preserve_requirement_ids=[], recheck_requirement_ids=current_ids, reasons=[])
    if not isinstance(previous, dict) or previous.get("type") != "GoalSpec" or not _text(previous.get("id")) or not _positive(previous.get("revision")) or not isinstance(previous.get("requirements"), list) or any(not isinstance(item, dict) or not _text(item.get("requirement_id")) for item in previous["requirements"]):
        error("previous_goal_shape", "/previous_goal", "An exact prior GoalSpec with stable requirement IDs is required.")
        return
    compatibility["previous_goal_ref"] = _goal_ref(previous)
    if previous["id"] != goal["id"]:
        error("stable_goal_identity", "/goal/id", "This finite revision adapter maintains one stable goal ID.")
    if mode == "reuse":
        if goal != previous:
            error("reuse_changed", "/goal", "Reuse must retain the exact goal and revision; changes require revise.")
        else:
            compatibility.update(status="preserve", preserve_requirement_ids=current_ids, recheck_requirement_ids=[], reasons=["Exact unchanged goal; existing judgments are not copied or adopted."])
        return
    if mode != "revise":
        error("previous_mode", "/mode", "A supplied previous_goal requires revise or reuse mode.")
        return
    if not isinstance(change, dict) or not _text(change.get("kind")) or change["kind"] not in CHANGE_KINDS or not _text(change.get("reason")):
        error("change_declaration", "/change", "Revision needs a declared nature and explicit reason.")
        return
    kind = change["kind"]
    if kind == "session_budget_only":
        if goal != previous:
            error("budget_changed_goal", "/goal", "Session time reduction cannot alter GoalSpec, formal time conditions or its revision.")
        else:
            compatibility.update(status="preserve", preserve_requirement_ids=current_ids, recheck_requirement_ids=[], reasons=["Only session budget changes; goal remains exact."])
            report["planning_handoff"] = {"status": "candidate", "owner": "SK05/AG1", "decision_needed": "保留原目标规范；目标仍为候选时先按授权决定采用。已有承诺在资源授权内缩减本次范围并保留未覆盖影响；超范围交用户决定。", "goal_ref": _goal_ref(goal), "reason": change["reason"], "goal_revision_changed": False, "valid_commitment": "not_created"}
        return
    if goal["revision"] != previous["revision"] + 1:
        error("goal_revision_monotonic", "/goal/revision", "Goal content revisions must advance by exactly one.")
    old_reqs = {item["requirement_id"]: item for item in previous["requirements"]}
    new_reqs = {item["requirement_id"]: item for item in goal["requirements"]}
    mapping = change.get("requirement_mapping")
    mapping_valid = isinstance(mapping, list) and bool(mapping)
    old_covered, new_covered = set(), set()
    if mapping_valid:
        for item in mapping:
            if not isinstance(item, dict) or not isinstance(item.get("from_requirement_ids"), list) or not isinstance(item.get("to_requirement_ids"), list) or not _text(item.get("relation")):
                mapping_valid = False
                break
            before, after = item["from_requirement_ids"], item["to_requirement_ids"]
            if not before and not after or any(not _text(rid) or rid not in old_reqs for rid in before) or any(not _text(rid) or rid not in new_reqs for rid in after):
                mapping_valid = False
                break
            old_covered.update(before)
            new_covered.update(after)
    if not mapping_valid or old_covered != set(old_reqs) or new_covered != set(new_reqs):
        pending("requirement_mapping", "/change/requirement_mapping", "显式映射所有新旧要求，包括新增、删除、拆分/合并；不能自动搬运 Judgment。", current_ids)
    else:
        compatibility["requirement_mapping"] = copy.deepcopy(mapping)
    for rid in old_reqs.keys() & new_reqs.keys():
        old, new = old_reqs[rid], new_reqs[rid]
        old_cr, new_cr = old.get("criterion_revision"), new.get("criterion_revision")
        if _positive(old_cr) and _positive(new_cr):
            changed = _criterion_content(old.get("criterion")) != _criterion_content(new.get("criterion"))
            if new_cr < old_cr or changed and new_cr <= old_cr:
                error("criterion_revision_change", f"/goal/requirements/{rid}/criterion_revision", "Changed criterion content requires a greater criterion revision; revisions cannot decrease.")
    equivalent = kind == "equivalent" and _text(change.get("equivalence_reason"))
    semantics_equal = _semantic_goal(previous) == _semantic_goal(goal)
    locator_only = _strip_locators(_semantic_goal(previous)) == _strip_locators(_semantic_goal(goal))
    self_mapping = mapping_valid and all(item["from_requirement_ids"] == item["to_requirement_ids"] and len(item["from_requirement_ids"]) == 1 for item in mapping)
    if equivalent and (semantics_equal or locator_only) and self_mapping and old_covered == set(old_reqs) and new_covered == set(new_reqs):
        compatibility.update(status="preserve", preserve_requirement_ids=current_ids, recheck_requirement_ids=[], reasons=["Explicit equivalence rationale; only description/locator differences detected. Professional confirmation remains required."])
    else:
        compatibility["reasons"] = ["Operations, criteria, resources, scope, formal time, dependencies or source revision may differ; previous support retains its old conditions only."]
        if kind == "equivalent" and not _text(change.get("equivalence_reason")):
            pending("equivalence_reason", "/change/equivalence_reason", "措辞或定位等价须有明确理由，不由脚本猜测语义等价。", current_ids)
        if kind == "equivalent" and mapping_valid and not self_mapping:
            pending("equivalence_mapping", "/change/requirement_mapping", "等价保留要求稳定requirement_id逐项自身映射，能力交换不能算等价。", current_ids)
        if kind in {"split", "merge"}:
            compatibility["reasons"].append("Only explicitly observed parts may later be linked by AG3; new coordination remains unobserved.")
    if kind == "purpose_change":
        pending("purpose_authorization", "/change", "最终用途/正式范围选择须由现有授权判断；本报告保持候选等待 AG1/用户决定。", current_ids)
    if kind == "correction":
        report["change_notice_candidate"] = {
            "status": "candidate", "changed_refs": [_goal_ref(previous), _goal_ref(goal)], "reason": change["reason"],
            "immediate_restriction_refs": {"status": "not_executed", "reason": "Preview has no control authority; responsible entry must apply actual restrictions before use."},
            "direct_dependencies": copy.deepcopy(change.get("direct_dependencies", [])),
            "unchecked_scope": {"status": "unknown", "reason": "Unknown content-chain and requirement-chain dependencies remain limited pending tracing."},
            "restoration_conditions": ["AG2 核内容/材料用途", "AG1 核判据和目标", "AG3 先看原答是否足以重评，必要补证由其判断", "AG0/SK05 分别处理实际误导与承诺影响"],
            "return_owner": "AG1; AG2/AG3/AG0 by affected responsibility", "restriction_execution": "not_executed", "new_test": "not_proposed",
        }


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="明确虚构的 JSON 目标候选输入")
    args = parser.parse_args(argv)
    try:
        package = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        print(json.dumps({"status": "candidate", "review_state": "invalid", "errors": [{"code": "input_unreadable", "detail": "Could not read a valid UTF-8 JSON input."}]}, ensure_ascii=False, indent=2))
        return 2
    result = review_goal_package(package)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["review_state"] == "invalid" else 0


if __name__ == "__main__":
    raise SystemExit(main())
