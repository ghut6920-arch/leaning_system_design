"""Synthetic AG0 entry: B1 inspection/controls and B5 sequential integration.

B1 start/resume/route remain read-only. B5 execute connects explicit professional
requests through the existing services; it does not generate their decisions or
start background agents. LearningStore owns every mutation. Actor strings remain
fixture configurations rather than authenticated host identities.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import fnmatch
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .learning_store import LearningStore
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime.learning_store import LearningStore


ROUTES = {
    "SK01": {"name": "learning-goals", "owner": "AG1", "inputs": ["purpose", "course_requirements", "content_basis", "user_constraints"], "aliases": ["learning-goals", "goals", "goal", "目标", "判据", "前置"]},
    "SK02": {"name": "learning-materials", "owner": "AG2", "inputs": ["material_refs", "source_versions", "intended_use", "goal_refs"], "aliases": ["learning-materials", "materials", "material", "材料", "参考", "内容核验"]},
    "SK03": {"name": "learning-teaching", "owner": "AG0", "inputs": ["activity_ref", "verified_material_refs", "goal_and_criteria_refs", "execution_authorization", "shared_budget_ref"], "aliases": ["learning-teaching", "teaching", "teach", "教学", "讲解", "练习", "编码", "提取"]},
    "SK04": {"name": "learning-assessment", "owner": "AG3", "inputs": ["event_refs", "original_response", "actual_help_conditions", "criterion_refs", "assessment_authorization"], "aliases": ["learning-assessment", "assessment", "assess", "评估", "评分", "诊断", "复核", "证据"]},
    "SK05": {"name": "learning-planning", "owner": "AG1", "inputs": ["goal_refs", "learning_need_refs", "shared_budget_ref", "current_commitment", "planning_authorization"], "aliases": ["learning-planning", "planning", "plan", "计划", "预算", "缩时", "排期"]},
    "SK06": {"name": "learning-strategies", "owner": "AG1", "inputs": ["intended_work", "complete_method_config", "source_revision", "local_conditions", "cost_and_evidence_limits"], "aliases": ["learning-strategies", "strategies", "strategy", "策略", "方法配置"]},
}
CONTROL_ALIASES = {
    "start": ["start", "开始"],
    "resume": ["resume", "continue", "继续", "恢复"],
    "pause": ["pause", "暂停"],
    "restrict": ["restrict", "限制", "停用", "纠错"],
    "delete": ["delete", "删除"],
    "export": ["export", "导出"],
    "status": ["status", "状态"],
    "integrity": ["integrity", "完整性"],
}
LIMITATIONS = [
    "B1 只处理显式选定工作区的虚构开发记录；未执行真实教学或学习评价。",
    "宿主身份、输出拦截和角色写入隔离未绑定；本外壳只按单入口顺序调用共享组件。",
    "路由只是候选去向，尚未启动专业 Agent、创建工作回执或改变正式计划。",
]


def _unknown(reason: str) -> dict[str, Any]:
    return {"status": "unknown", "reason": reason}


def _ref(obj: dict[str, Any]) -> dict[str, Any]:
    return {"id": obj["id"], "revision": obj["revision"]}


def _known(value: Any) -> Any:
    if isinstance(value, dict) and "status" in value:
        return value.get("value") if value["status"] == "known" else None
    return value


def _matches(text: str, alias: str) -> bool:
    if any("\u4e00" <= char <= "\u9fff" for char in alias):
        return alias in text
    # English aliases are whole tokens; "plan" must not match "explanation".
    import re
    return re.search(r"(?<![a-z0-9-])" + re.escape(alias) + r"(?![a-z0-9-])", text) is not None


class PersonalLearningEntry:
    """Read-only start/resume/route views; controls go directly to LearningStore."""

    def __init__(self, store: LearningStore):
        self.store = store

    @staticmethod
    def inspect_pilot(request: dict[str, Any], action: str = "preflight") -> dict[str, Any]:
        """B7 read-only preparation; never opens a fixture or personal store."""
        if __package__:
            from .pilot_b7 import PilotService
        else:
            from runtime.pilot_b7 import PilotService
        if action not in {"preflight", "report"}:
            return {"status": "rejected", "reasons": [{"code": "unknown_pilot_action"}],
                    "can_start_automated": False, "live_execution_status": "not_enabled"}
        return getattr(PilotService(), action)(request)

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        """B5 explicit sequential calls; B1 inspection methods remain read-only."""
        if __package__:
            from .entry_b5 import SingleEntryService
        else:
            from runtime.entry_b5 import SingleEntryService
        return SingleEntryService(self.store).execute(request)

    def open_network(self):
        """Create the B6 local serial host; the trusted caller binds its roles.

        Use it as a context manager so its OS workspace lock is released. B5
        APIs remain independent fixture tools, outside the host channel boundary.
        """
        if __package__:
            from .network_b6 import NetworkHost
        else:
            from runtime.network_b6 import NetworkHost
        return NetworkHost(self.store)

    def _base(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "not_ready",
            "state_revision": context.get("state_revision"),
            "synthetic_only": context.get("synthetic_only", False),
            "teaching": False,
            "needed_inputs": [],
            "controls": context.get("controls", {}),
            "limitations": list(LIMITATIONS),
            "capabilities": context.get("capabilities", {}),
            "mutated": False,
        }

    def status(self) -> dict[str, Any]:
        context = self.store.read_context()
        result = self._base(context)
        result["status"] = context.get("status", "not_ready")
        result["object_refs"] = [dict(_ref(obj), type=obj["type"]) for obj in context.get("objects", [])]
        if "reasons" in context:
            result["reasons"] = context["reasons"]
        return result

    def route(self, intent: str) -> dict[str, Any]:
        context = self.store.read_context()
        result = self._base(context)
        if context.get("status") != "ok":
            result.update(status="blocked", reasons=context.get("reasons", []))
            return result
        text = intent.strip().casefold()
        controls = [command for command, aliases in CONTROL_ALIASES.items() if any(_matches(text, alias) for alias in aliases)]
        skill_ids = [key for key, route in ROUTES.items() if key.casefold() == text or any(_matches(text, alias) for alias in route["aliases"])]
        result["intent"] = intent
        result["work_order_created"] = False
        if len(controls) == 1:
            command = controls[0]
            fields = ["scope_ids"] if command in ("pause", "restrict", "delete", "export") else []
            if command in ("pause", "restrict", "delete"):
                fields += ["expected_state_revision", "operation_id"]
            if command in ("pause", "restrict"):
                fields += ["reason"]
            if command == "restrict":
                fields += ["intended_uses"]
            result.update(status="control_request", command=command, needed_inputs=fields)
        elif len(controls) > 1 or len(skill_ids) != 1:
            result.update(status="needs_input", needed_inputs=["one_specific_decision"], candidate_commands=controls, candidate_skills=skill_ids)
        else:
            key = skill_ids[0]
            route = ROUTES[key]
            result.update(
                status="candidate",
                readiness="not_ready",
                target_skill={"id": key, "name": route["name"], "owner": route["owner"]},
                needed_inputs=route["inputs"] + ["current_controls", "recipient_authorization"],
                adoption={"status": "candidate", "reason": "当前入口只给候选去向；专业开发资源不等于已授权执行、接责或采用。"},
            )
        return result

    def start(self, course_id: str | None = None, activity_id: str | None = None) -> dict[str, Any]:
        return self._inspect("start", course_id, activity_id)

    def resume(self, course_id: str | None = None, activity_id: str | None = None) -> dict[str, Any]:
        # Locating a break is not lifting a user pause or a professional restriction.
        return self._inspect("resume", course_id, activity_id)

    def _inspect(self, mode: str, course_id: str | None, activity_id: str | None) -> dict[str, Any]:
        context = self.store.read_context()
        result = self._base(context)
        result["mode"] = mode
        result["current_context"] = {}
        result["recovery"] = {
            "source": "none",
            "activity_ref": _unknown("尚未找到可核查的活动。"),
            "last_trusted_event_ref": _unknown("尚未找到可信事件。"),
            "parent_artifact": _unknown("尚未找到父产物位置。"),
            "original_response": _unknown("尚未找到原答位置。"),
            "help_history": _unknown("没有可核查的帮助记录；不能解释为无帮助。"),
            "unrecorded_actions": _unknown("未记录动作不能从摘要或没有记录推断。"),
            "next_connection": _unknown("尚未找到原有返回连接。"),
            "new_test_created": False,
        }
        if context.get("status") != "ok" or not context.get("synthetic_only"):
            result.update(status="blocked", reasons=context.get("reasons", [{"code": "synthetic_workspace_required", "detail": "B1 只支持虚构开发工作区。"}]))
            return result

        objects = context.get("objects", [])
        inspection_use = "resume" if mode == "resume" else "use"
        index = {(obj["id"], obj["revision"]): obj for obj in objects}
        needed: list[str] = result["needed_inputs"]

        def resolve(ref: Any, expected_type: str | None = None) -> dict[str, Any] | None:
            if not isinstance(ref, dict) or "id" not in ref or "revision" not in ref:
                return None
            obj = index.get((ref["id"], ref["revision"]))
            if obj is None:
                # A checkpoint may legitimately name an older event revision.
                # Resolve its exact reference through the controlled store,
                # never substitute the latest content or read SQLite directly.
                historical = self.store.read_refs([ref], intended_use="read")
                if historical.get("status") == "ok" and historical.get("state_revision") == context.get("state_revision"):
                    for item in historical.get("objects", []):
                        index[(item["id"], item["revision"])] = item
                    obj = index.get((ref["id"], ref["revision"]))
                else:
                    reasons = historical.get("reasons", [])
                    if historical.get("state_revision") != context.get("state_revision"):
                        reasons = reasons + [{"code": "context_changed", "detail": "上下文读取后状态已改变；请重新读取。"}]
                    result.setdefault("blocked_refs", []).append({"refs": [ref], "reasons": reasons})
            if expected_type and obj and obj["type"] != expected_type:
                return None
            return obj

        def check(refs: list[dict[str, Any]], use: str = "read") -> bool:
            if not refs:
                return True
            validation = self.store.validate_refs(refs, intended_use=use)
            if validation.get("state_revision", context.get("state_revision")) != context.get("state_revision"):
                result.setdefault("blocked_refs", []).append({"refs": refs, "reasons": [{"code": "context_changed", "detail": "上下文读取后状态已改变；请重新读取。"}]})
                return False
            if validation.get("status") not in ("ok", "valid"):
                result.setdefault("blocked_refs", []).append({"refs": refs, "reasons": validation.get("reasons", [])})
                return False
            return True

        instances = [obj for obj in objects if obj["type"] == "LearningInstance" and (course_id is None or obj["id"] == course_id)]
        instance = instances[0] if len(instances) == 1 else None
        if instance is None:
            needed.append("course_id" if len(instances) > 1 else "learning_instance")
        elif check([_ref(instance)]):
            result["current_context"]["learning_instance_ref"] = _ref(instance)
            result["current_context"]["course"] = instance["course"]
            if _known(instance["course"]) in (None, ""):
                needed.append("course")

        active_plans = [obj for obj in objects if obj["type"] == "PlanCommitment" and obj.get("status") in ("active", "current", "executable")]
        plan = active_plans[0] if len(active_plans) == 1 else None
        if plan is None:
            needed.append("unique_current_commitment")
        elif check([_ref(plan)]):
            result["current_context"]["plan_ref"] = _ref(plan)

        activity = None
        if activity_id:
            candidates = [obj for obj in objects if obj["type"] == "ActivitySpec" and obj["id"] == activity_id]
            activity = candidates[0] if len(candidates) == 1 else None
        else:
            control_objects = [obj for obj in objects if obj["type"] == "ControlState"]
            control_activities = [resolve(obj.get("execution", {}).get("activity_ref"), "ActivitySpec") for obj in control_objects]
            unique = {obj["id"]: obj for obj in control_activities if obj}
            if len(unique) == 1:
                activity = next(iter(unique.values()))
            elif len(unique) > 1:
                needed.append("activity_id")
            else:
                activities = [obj for obj in objects if obj["type"] == "ActivitySpec"]
                if len(activities) == 1:
                    activity = activities[0]
        if activity is None:
            needed.append("activity_ref")
            result["status"] = "needs_input"
            return result
        activity_ref = _ref(activity)
        if not check([activity_ref], inspection_use):
            result["status"] = "blocked"
            return result
        result["current_context"]["activity_ref"] = activity_ref
        recovery = result["recovery"]
        recovery["activity_ref"] = activity_ref

        goal_refs = activity.get("goal_refs", [])
        goals = [resolve(ref, "GoalSpec") for ref in goal_refs]
        if not goal_refs or any(obj is None for obj in goals):
            needed.append("goal_and_criteria_refs")
        elif check(goal_refs, inspection_use):
            result["current_context"]["goal_refs"] = goal_refs
            result["current_context"]["criterion_refs"] = activity.get("criterion_refs", [])

        budget = resolve(activity.get("budget_ref"), "BudgetEnvelope")
        if budget and check([_ref(budget)], inspection_use):
            result["current_context"]["budget_ref"] = _ref(budget)
            # Preserve unknown and measured/estimated facts exactly, including non-active costs.
            result["current_context"]["budget"] = {key: budget[key] for key in ("user_active_time", "blocked_wait", "system_effort", "fees", "accounting_notes")}
            active_time = _known(budget["user_active_time"])
            if active_time is None:
                needed.append("current_active_time_budget")
            elif isinstance(active_time, dict) and isinstance(active_time.get("minutes"), (int, float)) and active_time["minutes"] <= 0:
                needed.append("remaining_active_time_budget")
        else:
            needed.append("shared_budget_ref")

        grants = [resolve(ref, "AuthorizationGrant") for ref in activity.get("authority_refs", [])]
        grants = [grant for grant in grants if grant and grant.get("grantee") == "AG0" and grant.get("binding_status") == "verified_for_fixture" and any(decision in ("teaching_execution", "teaching_execute", "execute_activity", "teaching", "execute") for decision in grant.get("decision_types", [])) and any(fnmatch.fnmatchcase(activity["id"], scope) for scope in grant.get("object_scope", []) if isinstance(scope, str))]
        if grants and check([_ref(grant) for grant in grants], inspection_use):
            result["current_context"]["fixture_execution_authorization_refs"] = [_ref(grant) for grant in grants]
        else:
            needed.append("execution_authorization")

        checkpoints = [obj for obj in objects if obj["type"] == "SessionCheckpoint" and obj.get("activity_ref") == activity_ref]
        checkpoint = None
        if plan:
            candidate = resolve(plan.get("checkpoint_ref"), "SessionCheckpoint")
            if candidate in checkpoints:
                checkpoint = candidate
        if checkpoint is None and len(checkpoints) == 1:
            checkpoint = checkpoints[0]
        if len(checkpoints) > 1 and checkpoint is None:
            needed.append("trusted_checkpoint_ref")

        event = None
        if checkpoint and check([_ref(checkpoint)], inspection_use):
            event = resolve(checkpoint.get("last_trusted_event_ref"), "PerformanceEvent")
            recovery.update(source="checkpoint", checkpoint_ref=_ref(checkpoint), next_connection=checkpoint.get("next_connection", _unknown("断点无返回连接。")), unrecorded_actions=checkpoint.get("unrecorded_actions", _unknown("断点没有记录额外动作。")))
            parent = checkpoint.get("parent_artifact")
            if isinstance(parent, dict) and "path" in parent and check([parent], inspection_use):
                recovery["parent_artifact"] = parent
        elif checkpoint:
            checkpoint = None

        if event is None and checkpoint is None:
            events = [obj for obj in objects if obj["type"] == "PerformanceEvent" and obj.get("activity_ref") == activity_ref and check([_ref(obj)], inspection_use)]
            if len(events) == 1:
                event = events[0]
            elif len(events) > 1:
                # read_context's ID order and object revision are not occurrence order.
                known_times = []
                for obj in events:
                    value = _known(obj.get("occurred_at"))
                    if not isinstance(value, str):
                        continue
                    try:
                        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    if timestamp.tzinfo is not None:
                        known_times.append((timestamp, obj))
                if len(known_times) == len(events) and len({value for value, _ in known_times}) == len(events):
                    event = max(known_times, key=lambda item: item[0])[1]
                else:
                    needed.append("last_trusted_event_ref")
                    recovery["candidate_event_refs"] = [_ref(obj) for obj in events]
            if event:
                recovery["source"] = "last_trusted_event"

        if event and event.get("activity_ref") == activity_ref and check([_ref(event)], inspection_use):
            recovery["last_trusted_event_ref"] = _ref(event)
            original = event.get("original_response")
            if isinstance(original, dict) and "path" in original and check([original], inspection_use):
                recovery["original_response"] = original
            recovery["help_history"] = {
                "status": "known",
                "value": event.get("timeline", []),
                "scope": "仅此事件已记录的顺序与可见性；没有记录的帮助保持未知。",
            }
            recovery["actual_resources"] = event.get("actual_resources", _unknown("没有实际资源记录。"))
            recovery["contact_history"] = event.get("contact_history", _unknown("没有接触历史记录。"))
            recovery["occurred_at"] = event.get("occurred_at", _unknown("没有发生时间记录。"))
        elif mode == "resume":
            needed.append("trusted_event_or_checkpoint")

        if recovery["parent_artifact"].get("status") == "unknown":
            parent_task = _known(activity.get("parent_task"))
            if isinstance(parent_task, dict):
                parent = parent_task.get("parent_artifact")
                if isinstance(parent, dict) and "path" in parent and check([parent], inspection_use):
                    recovery["parent_artifact"] = parent
                recovery["next_connection"] = parent_task.get("return_connection", _unknown("父任务无返回连接。"))

        result["needed_inputs"] = list(dict.fromkeys(needed))
        if result.get("blocked_refs"):
            result["status"] = "blocked"
        else:
            result["status"] = "needs_input" if needed else "not_ready"
        result["readiness_reason"] = "B1 仅提供检查与恢复位置；教学执行留待后续批次。"
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="虚构记录的 AG0 单入口；B1 检查控制与 B5 显式专业串接。")
    parser.add_argument("--workspace", type=Path, help="除只读 B7 pilot 外均必填：显式虚构开发记录目录")
    commands = parser.add_subparsers(dest="command", required=True)
    pilot = commands.add_parser("pilot", help="B7 只读试用配置与 V1—V4 引用检查；不启动教学或保存记录")
    pilot.add_argument("--action", choices=["preflight", "report"], default="preflight")
    pilot.add_argument("--request", required=True, type=Path, help="UTF-8 B7 请求；正文仅内存核查")
    commands.add_parser("init", help="初始化仅虚构记录的开发工作区，不载入学习数据")
    commands.add_parser("status", help="读取当前对象引用和控制")
    execute = commands.add_parser("execute", help="B5 顺序执行明确专业请求，条件不满足即停止")
    execute.add_argument("--request", required=True, type=Path, help="UTF-8 B5 JSON 请求；只接受虚构输入")
    for name in ("start", "resume"):
        item = commands.add_parser(name, help="只读检查开始条件或恢复位置")
        item.add_argument("--course-id")
        item.add_argument("--activity-id")
        if name == "resume":
            item.add_argument("--unpause", action="store_true", help="显式解除用户暂停；不解除专业限制")
            item.add_argument("--expected-state-revision", type=int)
            item.add_argument("--operation-id")
            item.add_argument("--scope-id", action="append", default=[])
    route = commands.add_parser("route", help="输出候选专业去向或控制命令，不执行路由结果")
    route.add_argument("--intent", required=True)
    for name in ("pause", "restrict", "delete"):
        item = commands.add_parser(name, help="经共享保存组件执行受控记录变更")
        item.add_argument("--expected-state-revision", required=True, type=int)
        item.add_argument("--operation-id", required=True)
        item.add_argument("--scope-id", action="append", required=True)
        if name in ("pause", "restrict"):
            item.add_argument("--reason", required=True)
        if name == "restrict":
            item.add_argument("--intended-use", action="append", default=None)
        if name == "delete":
            item.add_argument("--include-indexes", action="store_true")
    export = commands.add_parser("export", help="向 stdout 导出显式对象范围；不生成受管导出文件")
    export.add_argument("--scope-id", action="append", required=True)
    export.add_argument("--without-artifacts", action="store_true")
    commands.add_parser("integrity", help="检查当前受管记录完整性")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "pilot":
        try:
            result = PersonalLearningEntry.inspect_pilot(
                json.loads(args.request.read_text(encoding="utf-8-sig")), args.action)
        except (OSError, ValueError, TypeError):
            result = {"status": "rejected", "reasons": [{"code": "pilot_input_unavailable"}],
                      "can_start_automated": False, "live_execution_status": "not_enabled"}
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 1 if result.get("status") == "rejected" else 0
    if args.workspace is None:
        parser.error("该命令需要 --workspace；只有 B7 pilot 可无工作区只读核查")
    store = LearningStore(args.workspace, entry_actor="AG0")
    entry = PersonalLearningEntry(store)
    try:
        if args.command == "init":
            result = store.init_workspace()
        elif args.command == "status":
            result = entry.status()
        elif args.command == "execute":
            result = entry.execute(json.loads(args.request.read_text(encoding="utf-8-sig")))
        elif args.command in ("start", "resume"):
            if args.command == "resume" and args.unpause:
                if args.expected_state_revision is None or not args.operation_id or not args.scope_id:
                    parser.error("resume --unpause 需要 --expected-state-revision、--operation-id、--scope-id")
                result = store.resume(args.expected_state_revision, args.operation_id, args.scope_id)
            else:
                if args.command == "resume" and (args.expected_state_revision is not None or args.operation_id or args.scope_id):
                    parser.error("resume 的变更参数仅用于 --unpause；只读恢复使用 --activity-id 或 --course-id")
                result = getattr(entry, args.command)(args.course_id, args.activity_id)
        elif args.command == "route":
            result = entry.route(args.intent)
        elif args.command == "pause":
            result = store.pause(args.expected_state_revision, args.operation_id, args.scope_id, args.reason)
        elif args.command == "restrict":
            result = store.restrict(args.expected_state_revision, args.operation_id, args.scope_id, args.reason, intended_uses=args.intended_use or ["*"])
        elif args.command == "delete":
            result = store.delete_scope(args.expected_state_revision, args.operation_id, args.scope_id, include_indexes=args.include_indexes)
        elif args.command == "export":
            result = store.export_scope(args.scope_id, include_artifacts=not args.without_artifacts)
            result["export_notice"] = {
                "selected_scope_ids": args.scope_id,
                "evidence_scope": "仅导出的原始对象及其记录条件，不扩展成掌握、达成或学习效果。",
                "destination": "stdout",
                "uncontrolled_copies": ["调用者保存的 stdout、副本、宿主历史和外部备份不在本组件删除控制范围。"],
            }
        else:
            result = store.check_integrity()
        result.setdefault("teaching", False)
        result.setdefault("synthetic_only", True)
    except (OSError, ValueError, sqlite3.Error) as error:
        result = {"status": "not_saved", "teaching": False, "reasons": [{"code": "entry_error"}]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    failures = {"blocked", "conflict", "rejected", "not_saved"}
    if args.command == "execute":
        return 0 if result.get("status") == "completed" else 1
    return 1 if result.get("status") in failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
