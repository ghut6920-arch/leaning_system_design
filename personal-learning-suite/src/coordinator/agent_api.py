"""Small agent-facing surface over the detailed deterministic coordinator.

Read a compact desk, prepare a professional intent, apply its durable ticket.
Tickets freeze the exact request and pointer expectations; application never
silently refreshes a decision or automatically retries it against new state.
"""
from __future__ import annotations

import json
import os
import uuid

from .workspace import GateError, encode, identifier, ref, scopes, sha

API_VERSION = "tac-agent-api/0.2.0"
INTENTS = {"assign", "assign_readback", "assign_review", "begin", "deliver", "opinion", "check_change", "adopt", "stop", "ack"}
INTENT_REQUIRED = {
    "assign": {"task", "output", "scope", "use", "review_required", "inputs"},
    "assign_readback": {"task", "from_task", "output", "scope", "use", "review_required", "provisional_conditions"},
    "assign_review": {"task"}, "begin": {"task"}, "deliver": {"task", "path"},
    "opinion": {"task", "outcome", "rationale"},
    "check_change": {"task", "from", "to", "scope", "use", "rationale"},
    "adopt": {"tasks"}, "stop": {"task", "outcome", "reason"}, "ack": {"consumer", "through"},
}


def intent_shape(intent):
    """Shared syntax check; does not infer any professional decision or gate."""
    if not isinstance(intent, dict) or intent.get("action") not in INTENTS:
        raise GateError("unknown_agent_intent")
    required = INTENT_REQUIRED[intent["action"]]
    if not required <= intent.keys():
        raise GateError("explicit_agent_intent_fields_required", encode({"missing_fields": sorted(required - intent.keys())}))
    if intent["action"] == "assign_review" and not (intent.get("target") or intent.get("from_task")):
        raise GateError("explicit_agent_intent_fields_required")

ERROR_ACTIONS = {
    "state_revision_conflict": "状态已变化；查询当前任务后重新决定，原请求没有自动重试。",
    "pointer_conflict": "当前采用版本已变化；核对新旧版本后重新决定。",
    "receipt_version_mismatch": "审查对应另一个版本；补核或取得目标版本的意见。",
    "receipt_basis_or_use_mismatch": "意见依据或用途已变化；取得适用意见。",
    "input_recheck_required": "核对上游问题；仅input_not_adopted时作者可显式allow_provisional:true暂定确认，其他变化须复核或修订。暂定确认不授予采用资格。",
    "adopted_input_requires_recheck": "正式输入依据已变化；由专业负责人复核。",
    "professional_confirmation_required": "缺少覆盖所需范围的专业确认。",
    "ag3_review_required": "缺少覆盖所需范围的目标版本审查。",
    "conflicting_professional_receipts": "专业意见存在未处置冲突；由相应负责人明确解决。",
    "control_projection_stale": "用户控制来源已变化；读取实际控制并更新门禁投影。",
    "paused_scope": "相关范围已暂停；按用户控制处理。",
    "deleted_scope": "相关范围已删除或禁止读取；遵守当前控制。",
    "restricted_use": "当前用途受到限制；不能继续该用途。",
    "artifact_fingerprint_changed": "版本文件与登记内容不一致；寻找可信原件或另存修订。",
    "database_busy": "短写锁正忙；查原操作结果后有界重试同一请求。",
    "prepared_controls_changed": "用户控制与准备决定时不同；重新核对范围后决定。",
    "prepared_files_changed": "准备决定时的文件已变化；核对确切版本后重新决定。",
    "ambiguous_edit_base": "修改范围对应多个基版；明确选择基版或拆分任务。",
    "explicit_edit_base_required": "已有产物尚无唯一正式基版；明确指定要修订的版本。",
    "explicit_agent_intent_fields_required": "补齐这个动作需要的任务、范围、用途或专业决定；程序不会猜测。",
    "explicit_review_policy_and_inputs_required": "明确是否需要审查及实际输入；没有输入时填写空列表。",
    "explicit_professional_conclusion_required": "明确专业结论及判断理由。",
    "explicit_provisional_conditions_required": "精确输入尚非本用途/范围的采用版；明确provisional_conditions，不能把候选当正式输入。",
    "task_snapshot_not_available": "固定输入须由任务负责人或请求者在begin后读取；AG1候选功能读回由AG0先assign_readback，再AG1 begin/inputs，不借AG3审查取件。",
    "readback_scope_or_use_mismatch": "功能读回必须限于源任务成果的原用途/范围。",
    "readback_activity_spec_required": "功能读回生成AG1的ActivitySpec报告；明确output、review_required及候选条件。",
    "explicit_text_view_required": "目录不能当全文；取正文或分页时显式--view text。",
    "ag0_control_projection_required": "控制投影由AG0依据实际用户控制解释；其他角色不能更新。",
    "control_projection_changed": "投影已被其他操作替换；重新control-status核对，不覆盖新投影。",
    "control_projection_busy": "另一日常更新占有投影锁；核原结果后有界重试。遗留锁须确认旧执行已结束再处理，不自动抢占。",
    "control_revision_must_advance": "完整投影的state_revision须高于现投影；先核实际控制。",
    "explicit_control_interpretation_required": "填写interpretation_rationale说明实际控制解释；不能只更新来源指纹。",
    "control_sources_changed": "保持现投影全部原控制来源；此入口不授权换源。",
    "explicit_professional_boolean_required": "allow_provisional须显式布尔值true/false，不能用字符串或自动猜测。",
}


class AgentCoordinator:
    def __init__(self, coordinator):
        self.c = coordinator
        self.ticket_root = coordinator.meta_root / "requests"

    @staticmethod
    def error(reason, status="rejected"):
        return {"status": status, "problem": reason, "next_action": ERROR_ACTIONS.get(reason, "查看该任务的详细原因；明确修正后再操作。")}

    @staticmethod
    def receipt_view(receipt):
        if not receipt:
            return None
        keys = ("kind", "operation_id", "ref", "path", "receipt_id", "target_ref", "scope", "outcome", "adoption_state")
        return {k: receipt[k] for k in keys if k in receipt}

    def desk(self, session, *, task_id=None, limit=12, intended_use=None, scope=None):
        """Bounded, role-specific normal view; details remain explicit opt-in."""
        role = self.c.role(session)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise GateError("invalid_view_limit")
        state = self.c.status(session)
        tasks = [t for t in state["tasks"] if role == "AG0" or role in {t["assignee"], t["requester"]}]
        selected_use = identifier(intended_use) if intended_use is not None else None
        selected_scope = set(scopes(scope)) if scope is not None else None
        if selected_use is not None:
            tasks = [t for t in tasks if t["intended_use"] == selected_use]
        if selected_scope is not None:
            tasks = [t for t in tasks if selected_scope.intersection(t["scope"])]
        if task_id:
            tasks = [t for t in tasks if t["id"] == identifier(task_id)]
            if not tasks:
                raise GateError("task_unavailable_under_current_controls")
        # Unresolved work before old submissions; no history bodies by default.
        tasks.sort(key=lambda t: ({"blocked": 0, "running": 1, None: 2, "submitted": 3}[t["work_status"]], t["id"]))
        rows = []
        for task in tasks[:limit]:
            row = {"task": task["id"], "assigned_to": task["assignee"], "status": task["work_status"],
                   "scope": task["scope"], "use": task["intended_use"], "receipt": self.receipt_view(task["output_receipt"])}
            if row["status"] is None:
                row.pop("status")
                row["next_action"] = "开始任务，程序固定输入。"
            elif row["status"] == "blocked":
                row.update(reason=task["blocked_reason"], next_owner=task.get("next_owner", task["requester"]),
                           next_action="等待指定依赖；到期或失败交回请求者。" if task["blocked_reason"] == "waiting_for_dependency" else "处理阻塞原因或重新安排。")
            elif row["status"] == "running":
                row["next_action"] = "继续工作；完整保存后交付。"
            else:
                row["next_action"] = "已实际提交；专业意见与采用另行判断。"
            if task.get("target_ref"):
                row["review_target"] = task["target_ref"]
            if task.get("provisional_inputs"):
                row["provisional_inputs"] = task["provisional_inputs"]
            rows.append(row)
        ids = {t["id"] for t in tasks} | {t["result_ref"]["id"] for t in tasks if t.get("result_ref")}
        filtered = bool(task_id or selected_use is not None or selected_scope is not None)
        impacts = [i for i in state["impacts"] if i["target_id"] in ids or role == "AG0" and not filtered]
        decisions = [r for r in state["summary"] if r["kind"] == "artifact" and r["next_owner"] == role]
        if selected_use is not None:
            decisions = [r for r in decisions if r["intended_use"] == selected_use]
        if selected_scope is not None:
            decisions = [r for r in decisions if selected_scope.intersection(r["scope"])]
        if task_id:
            refs = {encode(t["result_ref"]) for t in tasks if t.get("result_ref")}
            decisions = [r for r in decisions if encode(r["ref"]) in refs]
        return {"status": "ok", "tasks": rows,
                "attention": [{"target": i["target_id"], "change": {"from": i["old_ref"], "to": i["new_ref"]}, "scope": i["scope"],
                               "kind": i["severity"], "next_owner": i["next_owner"], "next_action": i["next_action"]} for i in impacts[:limit]],
                "decisions": [{"ref": r["ref"], "scope": r["scope"], "use": r["intended_use"], "next_action": r["next_action"]} for r in decisions[:limit]],
                "remaining": {"tasks": max(0, len(tasks) - limit), "attention": max(0, len(impacts) - limit), "decisions": max(0, len(decisions) - limit)},
                "details": "需要更多依据时查inspect；固定正文用inputs；差异或意见证据按需查技术入口。"}

    def alerts(self, session, consumer_id, *, limit=12):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise GateError("invalid_view_limit")
        role = self.c.role(session)
        state = self.c.status(session)
        own_tasks = [t for t in state["tasks"] if role in {t["assignee"], t["requester"]}]
        relevant = {t["id"] for t in own_tasks}
        for task in own_tasks:
            if task.get("output"):
                relevant.add(task["output"]["id"])
            if task.get("target_ref"):
                relevant.add(task["target_ref"]["id"])
            relevant.update(i["id"] for i in task["inputs"])
            relevant.update(i["id"] for i in task.get("snapshot", []))
        stream = self.c.inbox(session, consumer_id, limit=limit)
        rows = []
        for event in stream["events"]:
            if role != "AG0" and not (event.get("next_owner") == role or set(event.get("scope_ids", [])) & relevant):
                continue
            row = {"event": event["sequence"], "kind": event["kind"]}
            for key in ("task_id", "ref", "target_id", "old_ref", "new_ref", "scope", "next_owner", "next_action", "reason", "bundle_id"):
                if event.get(key) is not None:
                    row[key] = event[key]
            phase = event.get("phase")
            work_status = "running" if phase == "running" else "submitted" if phase == "submitted" else "blocked" if phase in {"waiting", "blocked", "failed", "cancelled"} else None
            if work_status:
                row["work_status"] = work_status
            rows.append(row)
        return {"status": "ok", "consumer": consumer_id, "notifications": rows, "through": stream["next_sequence"],
                "next_action": "收到此页后提交ack意图；读取不自动确认，游标可跨过无关提示。" if stream["next_sequence"] > stream["acknowledged_sequence"] else "没有新提示。"}

    def task(self, db, task_id, role):
        task = self.c.get(db, "tasks", identifier(task_id))
        if role not in {"AG0", task["assignee"], task["requester"]}:
            raise GateError("task_assignee_required")
        return task

    def edit_base(self, db, output_id, use, coverage):
        revisions = []
        for part in coverage:
            row = db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?", (output_id, use, part)).fetchone()
            if row:
                revisions.append(row[0])
        if len(set(revisions)) > 1:
            raise GateError("ambiguous_edit_base")
        if len(revisions) == len(coverage):
            return {"id": output_id, "revision": revisions[0]}
        if db.execute("SELECT 1 FROM artifacts WHERE id=?", (output_id,)).fetchone():
            raise GateError("explicit_edit_base_required")
        return None

    def compile(self, db, role, intent, operation):
        intent_shape(intent)
        kind = intent.get("action")
        base = {"operation_id": operation, "expected_state_revision": self.c.state_revision(db)}
        if kind == "assign_readback":
            if role != "AG0":
                raise GateError("ag0_output_policy_required")
            source = self.task(db, intent["from_task"], role)
            if source["task_kind"] != "production" or source["phase"] != "submitted" or not source.get("result_ref"):
                raise GateError("submitted_artifact_required")
            artifact = self.c.artifact(db, source["result_ref"])
            coverage, use = scopes(intent["scope"]), identifier(intent["use"])
            if use != artifact["intended_use"] or not set(coverage) <= set(artifact["scope"]):
                raise GateError("readback_scope_or_use_mismatch")
            if (not isinstance(intent["output"], dict) or intent["output"].get("type") != "ActivitySpec"
                    or intent.get("to", "AG1") != "AG1"):
                raise GateError("readback_activity_spec_required")
            conditions = intent["provisional_conditions"]
            if not isinstance(conditions, str) or not conditions.strip():
                raise GateError("explicit_provisional_conditions_required")
            # Reuse ordinary production/snapshot gates; no new task kind, grants,
            # adoption rights, or synthetic AG3 review is introduced.
            normal = {**intent, "action": "assign", "to": "AG1", "inputs": [{
                "artifact": artifact["id"], "revision": artifact["revision"], "use": use,
                "scope": coverage, "provisional_conditions": conditions}]}
            return self.compile(db, role, normal, operation)
        if kind == "assign":
            output = intent["output"]
            if not isinstance(output, dict) or not {"id", "type"} <= output.keys():
                raise GateError("explicit_agent_intent_fields_required")
            coverage, use = scopes(intent["scope"]), identifier(intent["use"])
            policy = intent["review_required"]
            if type(policy) is not bool or not isinstance(intent["inputs"], list):
                raise GateError("explicit_review_policy_and_inputs_required")
            owner = intent.get("to") or self.c._primary_owner(output["type"])
            inputs = []
            for item in intent["inputs"]:
                if not isinstance(item, dict) or not {"artifact", "use", "scope"} <= item.keys():
                    raise GateError("explicit_agent_intent_fields_required")
                policy_name = "after_task" if item.get("after_task") else "exact" if "revision" in item else "adopted"
                normalized = {"id": identifier(item["artifact"]), "intended_use": identifier(item["use"]), "scope": scopes(item["scope"]), "policy": policy_name}
                if policy_name == "after_task":
                    normalized["producer_task_id"] = identifier(item["after_task"])
                elif policy_name == "exact":
                    normalized["revision"] = item["revision"]
                    if "provisional_conditions" in item:
                        normalized["provisional_conditions"] = item["provisional_conditions"]
                inputs.append(normalized)
            task = {"id": identifier(intent["task"]), "assignee": owner, "task_kind": "production", "scope": coverage,
                    "intended_use": use, "inputs": inputs,
                    "output": {"id": identifier(output["id"]), "type": output["type"], "requires_ag3_review": policy,
                               "validation_profile": output.get("validation", "file_integrity")},
                    "base_ref": ref(intent["base"]) if intent.get("base") else self.edit_base(db, output["id"], use, coverage)}
            if "changed_scope" in intent:
                task["planned_changed_scope"] = intent["changed_scope"]
            if any(i["policy"] == "after_task" for i in inputs):
                if "wait_ms" not in intent:
                    raise GateError("explicit_agent_intent_fields_required")
                task["wait_timeout_ms"] = intent["wait_ms"]
            return "register", {**base, **task}
        if kind == "assign_review":
            target = intent.get("target")
            if target is None:
                source = self.task(db, intent["from_task"], role)
                target = source.get("result_ref")
            if not target:
                raise GateError("submitted_artifact_required")
            artifact = self.c.artifact(db, target)
            return "register", {**base, "id": identifier(intent["task"]), "assignee": "AG3", "task_kind": "review",
                                "scope": scopes(intent.get("scope", artifact["scope"])), "intended_use": artifact["intended_use"], "target_ref": ref(target)}
        if kind == "ack":
            return "ack_events", {**base, "consumer_id": identifier(intent["consumer"]), "through_sequence": intent["through"]}
        if kind == "adopt":
            if role != "AG0":
                raise GateError("ag0_bundle_adoption_required")
            members, expected = [], []
            if not isinstance(intent.get("tasks"), list) or not intent["tasks"]:
                raise GateError("explicit_adoption_tasks_required")
            for item in intent["tasks"]:
                item = {"task": item} if isinstance(item, str) else item
                task = self.task(db, item["task"], role)
                if task["task_kind"] != "production" or not task.get("result_ref"):
                    raise GateError("submitted_artifact_required")
                a = self.c.artifact(db, task["result_ref"])
                use, coverage = a["intended_use"], scopes(item.get("scope", a["scope"]))
                # Select every current matching supported receipt; never pick the
                # last arrival or silently retire an opposing professional view.
                stamp, _ = self.c.basis_status(db, a)
                applicable, retired = self.c.active_opinions(db, a, use, stamp)
                receipts = item.get("receipts", [r["id"] for r in applicable if r["id"] not in retired and r["outcome"] == "supported" and set(r["scope"]) & set(coverage)])
                members.append({"ref": ref(a), "scope": coverage, "intended_use": use, "receipt_ids": receipts})
                for part in coverage:
                    pointer = db.execute("SELECT revision FROM adopted WHERE id=? AND intended_use=? AND scope=?", (a["id"], use, part)).fetchone()
                    expected.append({"id": a["id"], "intended_use": use, "scope": part, "revision": pointer[0] if pointer else None})
            # Evaluate receipt selection against the proposed whole collection.
            proposed = {(m["ref"]["id"], m["intended_use"], s): m["ref"]["revision"] for m in members for s in m["scope"]}
            for member, item in zip(members, intent["tasks"]):
                if not isinstance(item, dict) or "receipts" not in item:
                    a = self.c.artifact(db, member["ref"])
                    stamp, _ = self.c.basis_status(db, a, proposed)
                    opinions, retired = self.c.active_opinions(db, a, member["intended_use"], stamp)
                    member["receipt_ids"] = [r["id"] for r in opinions if r["id"] not in retired and r["outcome"] == "supported" and set(r["scope"]) & set(member["scope"])]
            request = {**base, "bundle_id": "bundle-" + operation, "members": members, "expected_pointers": expected}
            if "rollback_rationale" in intent:
                request["rollback_rationale"] = intent["rollback_rationale"]
            return "adopt", request
        task = self.task(db, intent["task"], role)
        if kind == "begin":
            return "start", {**base, "task_id": task["id"]}
        if kind == "deliver":
            request = {**base, "task_id": task["id"], "path": intent["path"]}
            if "changed_scope" in intent:
                request["changed_scope"] = intent["changed_scope"]
            return "submit", request
        if kind == "stop":
            return "finish", {**base, "task_id": task["id"], "phase": intent["outcome"], "reason": intent["reason"]}
        if kind == "check_change":
            if not task.get("result_ref"):
                raise GateError("submitted_artifact_required")
            return "recheck", {**base, "ref": task["result_ref"], "recheck_id": "recheck-" + operation,
                               "old_ref": ref(intent["from"]), "new_ref": ref(intent["to"]), "scope": scopes(intent["scope"]),
                               "intended_use": intent["use"], "rationale": intent["rationale"]}
        if kind == "opinion":
            if "allow_provisional" in intent and type(intent["allow_provisional"]) is not bool:
                raise GateError("explicit_professional_boolean_required")
            if task["task_kind"] == "review":
                action, exact = "review", task["target_ref"]
                body = {"task_id": task["id"]}
            else:
                action, exact = "confirm", task.get("result_ref")
                body = {"ref": exact}
            if not exact:
                raise GateError("submitted_artifact_required")
            a = self.c.artifact(db, exact)
            body.update(receipt_id="opinion-" + operation, scope=scopes(intent.get("scope", task["scope"])), intended_use=a["intended_use"],
                        outcome=intent["outcome"], rationale=intent["rationale"])
            # These are professional statements, never guessed or automatically
            # supplied. Most normal full reviews need only outcome + rationale.
            for key in ("allow_provisional", "supersedes_receipt_ids", "base_receipt_id", "directly_checked_scope", "inherited_scope", "compatibility_rationale"):
                if key in intent:
                    body[key] = intent[key]
            return action, {**base, **body}
        raise GateError("unknown_agent_intent")

    def prepare(self, session, intent):
        """Persist one frozen request; caller sees a concise concrete decision."""
        role = self.c.role(session)
        if not isinstance(intent, dict):
            raise GateError("agent_intent_required")
        ticket = "request-" + uuid.uuid4().hex
        operation = "agent-" + uuid.uuid4().hex
        with self.c.connect() as db:
            db.execute("BEGIN")
            control = self.c.controls(db)
            action, request = self.compile(db, role, intent, operation)
            if session.dispatch is not None:
                request["runtime_dispatch"] = session.dispatch
            if session.runtime_setup:
                request["runtime_setup"] = True
            self.c.execution_guard(db, session, action, request, control)
            file_infos = self.c.preflight(db, request, control)
            context = self.c.context(db, request)
            self.c.gate(control, context["scope_ids"], context["intended_uses"])
            # Verify the decision on a savepoint, then discard its writes. This
            # uses the existing gates rather than another weaker qualification.
            db.execute("SAVEPOINT preview")
            try:
                result = getattr(self.c, "_" + action)(db, role, request, control)
            finally:
                db.execute("ROLLBACK TO preview")
                db.execute("RELEASE preview")
            if encode(self.c.controls(db)) != encode(control):
                raise GateError("control_changed_during_read")
            request["prepared_preconditions"] = {"control": control, "files": file_infos}
            envelope = {"version": API_VERSION, "role": role, "action": action, "request": request,
                        "control": control, "files": file_infos, "context": context}
        self.ticket_root.mkdir(exist_ok=True)
        path = self.ticket_root / (ticket + ".json")
        value = {"envelope": envelope, "fingerprint": sha(encode(envelope).encode("utf-8"))}
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2))
            stream.flush()
            os.fsync(stream.fileno())
        preview = {"intent": intent["action"], "task": intent.get("task"), "scope": request.get("scope"), "use": request.get("intended_use")}
        if action == "adopt":
            preview["members"] = [{"ref": m["ref"], "scope": m["scope"], "use": m["intended_use"], "receipts": m["receipt_ids"]} for m in request["members"]]
        elif action in {"confirm", "review"}:
            preview.update(target=result["target_ref"],
                           outcome=request["outcome"], rationale=request["rationale"])
        elif action == "register":
            preview.update(assigned_to=request["assignee"], output=request.get("output"), inputs=intent.get("inputs", request.get("inputs")), base=request.get("base_ref"), target=request.get("target_ref"))
        elif action == "submit":
            preview.update(path=request["path"], ref=result["ref"], input_issues=result.get("input_issues", []))
        return {"status": "prepared", "ticket": ticket, "preview": {k: v for k, v in preview.items() if v is not None},
                "next_action": "核对这个具体决定后apply原ticket；不需要填写状态号、指纹或指针。"}

    def load_ticket(self, session, ticket):
        role = self.c.role(session)
        identifier(ticket)
        path = (self.ticket_root / (ticket + ".json")).resolve()
        if not path.is_relative_to(self.ticket_root.resolve()):
            raise GateError("invalid_request_ticket")
        value = json.loads(path.read_text(encoding="utf-8"))
        envelope = value["envelope"]
        if envelope["version"] != API_VERSION or envelope["role"] != role or sha(encode(envelope).encode("utf-8")) != value["fingerprint"]:
            raise GateError("request_ticket_mismatch")
        return envelope

    def apply(self, session, ticket):
        envelope = self.load_ticket(session, ticket)
        result = self.c.execute(session, envelope["action"], envelope["request"])
        return self.compact_result(session, ticket, envelope, result)

    def intent_alias(self, session, intent, request_key):
        """A host-owned stable key survives loss of the entire CLI response."""
        if not isinstance(request_key, str) or not request_key.strip() or not isinstance(intent, dict):
            raise GateError("stable_intent_source_required")
        identity = {"role": self.c.role(session), "source": request_key, "intent": intent}
        fingerprint = sha(encode(identity).encode("utf-8"))
        return self.ticket_root / ("intent-" + fingerprint + ".json"), fingerprint

    @staticmethod
    def alias_ticket(path, fingerprint):
        value = json.loads(path.read_text(encoding="utf-8"))
        recorded_hash = value.pop("record_sha256")
        if value["fingerprint"] != fingerprint or value["version"] != API_VERSION or sha(encode(value).encode("utf-8")) != recorded_hash:
            raise GateError("request_ticket_mismatch")
        return identifier(value["ticket"])

    def do(self, session, intent, *, request_key):
        path, fingerprint = self.intent_alias(session, intent, request_key)
        if path.exists():
            ticket = self.alias_ticket(path, fingerprint)
        else:
            prepared = self.prepare(session, intent)
            ticket = prepared["ticket"]
            # The alias is persisted before execution. If creation is interrupted,
            # no business operation has yet run. A corrupt alias fails closed.
            try:
                with path.open("x", encoding="utf-8") as stream:
                    value = {"version": API_VERSION, "fingerprint": fingerprint, "ticket": ticket}
                    value["record_sha256"] = sha(encode(value).encode("utf-8"))
                    stream.write(json.dumps(value))
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError:
                # A concurrent caller reserved the same intent. Use its original
                # frozen request; do not execute our newly prepared alternative.
                ticket = self.alias_ticket(path, fingerprint)
        return self.apply(session, ticket)

    def saved_intent(self, session, intent, *, request_key):
        path, fingerprint = self.intent_alias(session, intent, request_key)
        if not path.exists():
            return {"status": "not_committed", "next_action": "未找到此文件意图的原请求；这不是进程已经停止的证明。"}
        return self.saved(session, self.alias_ticket(path, fingerprint))

    def compact_result(self, session, ticket, envelope, result):
        if result["status"] != "committed":
            reason = (result.get("reasons") or [result["status"]])[0]
            return {**self.error(reason, result["status"]), "ticket": ticket,
                    "next_action": "先查原ticket的saved结果，再重试原ticket。" if result["status"] == "commit_status_unknown" else ERROR_ACTIONS.get(reason, "检查当前任务后明确修正；不要盲目刷新决定。")}
        output = {"status": "committed", "ticket": ticket, "action": envelope["action"]}
        for key in ("task_id", "ref", "receipt_id", "target_ref", "adoption", "input_issues", "covered_scope", "next_owner", "reason", "acknowledged_sequence"):
            if key in result:
                output[key] = result[key]
        if envelope["action"] == "adopt":
            output["adopted"] = [{"ref": m["ref"], "scope": m["scope"], "use": m["intended_use"]} for m in result["members"]]
        # The original commit receipt is authoritative for this operation.
        # Do not re-read a possibly changed/hidden current task after commit.
        action, request = envelope["action"], envelope["request"]
        if result.get("phase"):
            phase = result["phase"]
            status = "running" if phase == "running" else "submitted" if phase == "submitted" else "blocked" if phase in {"waiting", "blocked", "failed", "cancelled"} else None
            if status:
                output["work_status"] = status
            else:
                output["next_action"] = "任务已登记；开始时固定输入。"
        if action == "submit":
            output.update(work_status="submitted", task_id=request["task_id"],
                          receipt={"kind": "artifact_submission", "operation_id": result["operation_id"], "ref": result["ref"], "path": request["path"], "adoption_state": result["state"]})
        elif action == "review":
            output.update(work_status="submitted", receipt={"kind": "review_submission", "operation_id": result["operation_id"], "receipt_id": result["receipt_id"], "target_ref": result["target_ref"], "scope": request["scope"], "outcome": request["outcome"]})
        impacts = result.get("affected_downstream", [])
        if impacts:
            output["attention_count"] = len(impacts)
            output["next_action"] = "查看desk中相关依赖变化。"
        if envelope["action"] == "start" and result.get("phase") == "running":
            output["next_action"] = "通过inputs读取本任务固定正文，再继续专业工作。"
        return output

    def saved(self, session, ticket):
        envelope = self.load_ticket(session, ticket)
        result = self.c.operation(session, envelope["request"]["operation_id"])
        if result["status"] == "committed":
            compact = self.compact_result(session, ticket, envelope, result["receipt"])
            return {"status": "committed", "ticket": ticket, "action": envelope["action"], "result": {k: v for k, v in compact.items() if k not in {"status", "ticket", "action", "next_action"}},
                    "meaning": "原提交已保存；当前可用性仍按当前控制与版本判断。"}
        return {"status": result["status"], "ticket": ticket, "next_action": "当前未查到提交；确认原执行状态后再apply同一ticket。"}
