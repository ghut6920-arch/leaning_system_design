"""Small daily entry for agents using the task and artifact coordinator."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator.agent_api import AgentCoordinator
from coordinator.complete import TaskArtifactCoordinator
from coordinator.reading import DEFAULT_TEXT_CHARS, add_read_arguments, read_options, verified_view
from coordinator.workspace import FileControlGate, GateError
from coordinator.control_projection import diagnose, replace_projection
from coordinator.delivery import DEFAULT_RETURN_BYTES, bounded_output
from coordinator.control_batch import run_batch


def parser():
    entry = argparse.ArgumentParser(description="查看必要状态，提交明确的专业意图。")
    entry.add_argument("--workspace", required=True, type=Path)
    entry.add_argument("--role", required=True, choices=["AG0", "AG1", "AG2", "AG3"])
    entry.add_argument("--control-projection", type=Path)
    entry.add_argument("--dispatch-id", help="由调度器发出的当前派发ID")
    entry.add_argument("--claim-epoch", type=int, help="当前执行权代次；线程ID取实际宿主环境")
    entry.add_argument("--max-return-bytes", type=int, default=DEFAULT_RETURN_BYTES, help="只读视图含封装的总UTF-8返回预算")
    commands = entry.add_subparsers(dest="command")
    start = commands.add_parser("start-preparation", help="正常备课入口：自动初始化、登记原聊天、保存计划并取得Python接管回执")
    start.add_argument("--request-file", type=Path, required=True)
    commands.add_parser("control-status", help="核投影及原控制指纹；陈旧时列出需要重新解释的来源")
    update = commands.add_parser("control-update", help="AG0提交完整且显式解释过的控制投影；不自动解释正文")
    update.add_argument("--projection-file", type=Path, required=True)
    update.add_argument("--expect-projection-sha256", required=True)
    desk = commands.add_parser("desk", help="角色相关的短状态；默认入口")
    desk.add_argument("--task")
    desk.add_argument("--limit", type=int, default=12)
    desk.add_argument("--use", help="限定用途，避免无关历史进入当前决定")
    desk.add_argument("--scope", action="append", help="限定范围，可重复")
    alerts = commands.add_parser("alerts", help="取得新提示，不自动确认")
    alerts.add_argument("--consumer", required=True)
    alerts.add_argument("--limit", type=int, default=12)
    for command in ("prepare", "do"):
        intent = commands.add_parser(command, help="准备决定" if command == "prepare" else "准备并提交明确意图")
        intent.add_argument("--intent-file", required=True, type=Path)
    batch = commands.add_parser("batch", help="顺序执行同角色已明确的意图；遇错停止，原回执可恢复")
    batch.add_argument("--plan-file", required=True, type=Path)
    batch.add_argument("--retry-stopped", action="store_true", help="明确重试已拒绝步骤的原ticket；不自动重新决定")
    request = commands.add_parser("apply", help="提交原请求")
    request.add_argument("--ticket", required=True)
    saved = commands.add_parser("saved", help="查询原请求实际回执")
    source = saved.add_mutually_exclusive_group(required=True)
    source.add_argument("--ticket")
    source.add_argument("--intent-file", type=Path)
    for command in ("inputs", "inspect"):
        task = commands.add_parser(command, help="查看固定输入；AG0默认目录，专业角色默认正文" if command == "inputs" else "按需查看任务详细依据")
        task.add_argument("--task", required=True)
        if command == "inputs":
            add_read_arguments(task, default_view=None)
            task.add_argument("--input", type=int, help="只显示一个固定输入，编号从0起")
            task.add_argument("--source", help="从所选固定材料清单取确切成员id，不复制正文")
    current = commands.add_parser("current", help="查询当前采用版；默认只显示经门禁验证的元数据")
    current.add_argument("--artifact-id", required=True)
    current.add_argument("--intended-use", required=True)
    current.add_argument("--scope", action="append", required=True)
    add_read_arguments(current, default_view="metadata")
    current.add_argument("--source", help="从当前采用的材料清单取确切成员id")
    return entry


def input_view(coordinator, session, task_id, *, input_index=None, view="text", offset=0,
               max_chars=DEFAULT_TEXT_CHARS, expected_sha256=None):
    """Decode only the bytes returned by the verified task snapshot."""
    items = coordinator.read_snapshot(session, task_id)
    if input_index is not None and (type(input_index) is not int or not 0 <= input_index < len(items)):
        raise GateError("invalid_input_index")
    if input_index is None and (offset or expected_sha256):
        raise GateError("select_input_for_continuation")
    rows, remaining = [], max_chars
    for index, item in enumerate(items):
        if input_index is not None and index != input_index:
            continue
        row = verified_view(item, root=coordinator.root, view=view, offset=offset,
                            max_chars=remaining, expected_sha256=expected_sha256)
        row.update(input_index=index, kind=item.get("kind", "input"))
        if remaining is not None:
            remaining -= len(row.get("text", ""))
        rows.append(row)
    return {"status": "ok", "task": task_id, "inputs": rows,
            "view": view,
            **({"next_action": "此处仅返回固定输入目录；需要专业正文时显式用--view text，可先用--input选择必要原件。"} if view == "metadata" else {}),
            "meaning": "本任务固定且已验证的版本；修订基版以edit_base标明。正文按coverage续读，未完整输出不算全文已读。"}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", newline="")
    args = parser().parse_args(argv)
    ticket = None
    try:
        projection = args.control_projection or args.workspace / "coordination/control.json"
        gate = FileControlGate(args.workspace, projection) if projection.is_file() else None
        coordinator = TaskArtifactCoordinator(args.workspace, gate)
        command = args.command or "desk"
        coordinator.read_only = command in {"desk", "inputs", "current", "alerts", "inspect", "saved", "control-status"}
        dispatch = None
        if args.dispatch_id is not None or args.claim_epoch is not None:
            if not args.dispatch_id or args.claim_epoch is None or not os.environ.get("CODEX_THREAD_ID"):
                raise GateError("actual_dispatch_context_required")
            dispatch = {"dispatch_id": args.dispatch_id, "claim_epoch": args.claim_epoch, "thread_id": os.environ["CODEX_THREAD_ID"]}
        session = coordinator.bind_local_operator(args.role, dispatch=dispatch)
        api = AgentCoordinator(coordinator)
        if command == "start-preparation":
            if args.role != "AG0" or dispatch is not None:
                raise GateError("ag0_preparation_start_required")
            bounded_output({"status": "ok"}, budget=args.max_return_bytes)
            from coordinator.preparation_start import start_preparation
            result = start_preparation(coordinator, json.loads(args.request_file.read_text(encoding="utf-8-sig")))
        elif command == "batch":
            result = run_batch(api, session, args.plan_file, retry_stopped=args.retry_stopped, budget=args.max_return_bytes)
        elif command in {"control-status", "control-update"}:
            if args.role != "AG0":
                raise GateError("ag0_control_projection_required")
            if gate is None:
                raise GateError("control_source_unavailable")
            result = (diagnose(gate) if command == "control-status" else
                      replace_projection(gate, args.projection_file, expected_projection_sha256=args.expect_projection_sha256))
        elif command == "desk":
            result = api.desk(session, task_id=getattr(args, "task", None), limit=getattr(args, "limit", 12),
                              intended_use=getattr(args, "use", None), scope=getattr(args, "scope", None))
        elif command == "alerts":
            result = api.alerts(session, args.consumer, limit=args.limit)
        elif command in {"prepare", "do"}:
            intent = json.loads(args.intent_file.read_text(encoding="utf-8-sig"))
            result = (api.do(session, intent, request_key=str(args.intent_file.resolve())) if command == "do"
                      else api.prepare(session, intent))
            ticket = result.get("ticket")
        elif command == "apply":
            ticket = args.ticket
            result = api.apply(session, ticket)
        elif command == "saved":
            ticket = args.ticket
            if ticket:
                result = api.saved(session, ticket)
            else:
                intent = json.loads(args.intent_file.read_text(encoding="utf-8-sig"))
                result = api.saved_intent(session, intent, request_key=str(args.intent_file.resolve()))
        elif command == "inputs":
            if args.view is None:
                args.view = "metadata" if args.role == "AG0" else "text"
            if args.source:
                item = coordinator.preparation_source(session, args.source, task_id=args.task, input_index=args.input)
                result = {"status": "ok", "task": args.task, "inputs": [{**verified_view(item, root=coordinator.root, **read_options(args)), "input_index": args.input}]}
            else:
                result = input_view(coordinator, session, args.task, input_index=args.input, **read_options(args))
        elif command == "current":
            item = (coordinator.preparation_source(session, args.source, artifact_id=args.artifact_id, intended_use=args.intended_use, scope=args.scope)
                    if args.source else coordinator.resolve(session, args.artifact_id, args.intended_use, args.scope))
            result = {"status": "ok", **verified_view(item, root=coordinator.root, **read_options(args))}
        else:
            result = coordinator.boundary(session, args.task)
    except GateError as error:
        result = AgentCoordinator.error(error.code)
        if getattr(error, "receipt", None):
            result["listener"] = error.receipt
        if str(error) != error.code:
            result["detail"] = str(error)
    except FileNotFoundError as error:
        result = {"status": "rejected", "problem": "required_file_missing", "path": str(error.filename),
                  "next_action": "检查意图、原ticket或协调数据库的路径；不要创建替代版本冒充原件。"}
    except (ValueError, KeyError, TypeError, UnicodeError):
        result = {"status": "rejected", "problem": "invalid_request_data",
                  "next_action": "按日常指南检查JSON及必要专业字段；修正后重新决定。"}
    except sqlite3.Error as error:
        reason = "database_busy" if "locked" in str(error).lower() or "busy" in str(error).lower() else "coordinator_storage_unavailable"
        result = AgentCoordinator.error(reason)
    except OSError:
        result = {"status": "rejected", "problem": "file_access_failed",
                  "next_action": "检查工作区文件是否可读写；已有ticket先查saved，不能虚称已提交。"}
    if ticket:
        result.setdefault("ticket", ticket)
    if (args.command or "desk") in {"inputs", "current", "desk", "inspect", "alerts", "saved", "control-status", "batch", "start-preparation"}:
        try:
            output = bounded_output(result, budget=args.max_return_bytes)
        except GateError as error:
            result = {"status": "rejected", "problem": error.code,
                      "next_action": "缩小task、limit、input或条目批次；需要更大返回时明确设置--max-return-bytes。"}
            output = bounded_output(result)
        print(output, end="")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"ok", "prepared", "committed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
