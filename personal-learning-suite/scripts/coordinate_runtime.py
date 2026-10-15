"""Explicit local entry for durable plans and bounded coordinator turns."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator.complete import TaskArtifactCoordinator
from coordinator.delivery import DEFAULT_RETURN_BYTES, bounded_output
from coordinator.hosts import CLIResumeHost, DesktopMCPHost
from coordinator.runtime_scheduler import RuntimeScheduler
from coordinator.runtime_store import RuntimeStore
from coordinator.workspace import FileControlGate, GateError, encode


class RuntimeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise GateError("invalid_command_arguments", message)


def positive_seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("须为有限正秒数")
    return number


def parser():
    entry = RuntimeArgumentParser(description="显式登记运行计划，由程序等待，仅向就绪工作派发。")
    entry.add_argument("--workspace", required=True, type=Path)
    entry.add_argument("--control-projection", type=Path,
                       help="默认读取工作区 coordination/control.json（若存在）")
    entry.add_argument("--max-return-bytes", type=int, default=DEFAULT_RETURN_BYTES,
                       help="JSON返回的总UTF-8字节预算，默认8192，最多65536")
    commands = entry.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="显式备份并新增运行表；不初始化业务数据库")
    binding = commands.add_parser("bind", help="保存获用户授权的角色与宿主线程绑定")
    binding.add_argument("--binding-file", type=Path, required=True)
    plan = commands.add_parser("plan", help="持久保存明确计划；回执不代表监听器在线")
    plan.add_argument("--plan-file", type=Path, required=True)
    status = commands.add_parser("status", help="查看工作、绑定、监听器与阻断原因")
    status.add_argument("--limit", type=int, default=12, help="各类记录最多返回多少条，默认12")
    repair = commands.add_parser("reconcile-result", help="核对原CLI完成证据，修复已知接收缺陷；不重新派发模型")
    repair.add_argument("--dispatch-id", required=True)
    for name in ("shadow", "run"):
        runner = commands.add_parser(name, help="持久求值，不创建宿主连接或发送任务" if name == "shadow" else "显式启动调度；只处理已登记计划")
        runner.add_argument("--once", action="store_true", help="启动、求值一轮后释放监听器；run模式可以派发")
        runner.add_argument("--max-seconds", type=positive_seconds)
        runner.add_argument("--stop-when-done", action="store_true")
        runner.add_argument("--ready-file", type=Path, help="取得监听器租约后写入就绪记录")
    for name in ("enable", "disable"):
        control = commands.add_parser(name, help="显式启用计划" if name == "enable" else "停发此计划并拒绝新发布")
        control.add_argument("--workflow", required=True)
    for name in ("begin-dispatch", "result"):
        dispatch = commands.add_parser(name, help="接收本线程派发" if name == "begin-dispatch" else "保存本线程关联结果，随后可正常结束聊天轮次")
        dispatch.add_argument("--dispatch-id", required=True)
        dispatch.add_argument("--claim-epoch", type=int, required=True)
        dispatch.add_argument("--role", choices=["AG0", "AG1", "AG2", "AG3"], required=True)
        if name == "result":
            dispatch.add_argument("--result-file", type=Path, required=True)
    return entry


def read_object(path):
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise GateError("invalid_request_data")
    return value


def status_view(snapshot, *, limit=12):
    """Keep useful recovery metadata, without prompts or frozen source text."""
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise GateError("invalid_status_limit")
    bindings = {binding["id"]: binding for binding in snapshot["bindings"]}
    works = []
    for work in snapshot["works"][:limit]:
        node = work.get("node", {})
        binding = bindings.get(node.get("binding"), {})
        row = {key: work[key] for key in ("id", "workflow_id", "state", "reason", "dispatch_id", "claim_epoch") if key in work}
        row.update(node_id=node.get("id"), binding=node.get("binding"),
                   role=binding.get("role"), thread_id=binding.get("thread_id"))
        works.append(row)
    binding_rows = [{key: row[key] for key in ("id", "role", "host_kind", "host_id", "thread_id", "generation", "authorized") if key in row}
                    for row in snapshot["bindings"][:limit]]
    plans = [{"id": row["id"], "revision": row["revision"], "enabled": row["enabled"], "node_count": len(row["nodes"])}
             for row in snapshot["plans"][:limit]]
    counts = {key: len(snapshot[key]) for key in ("works", "bindings", "plans")}
    return {"status": "ok", **{key: snapshot[key] for key in ("runtime_version", "state_revision", "runtime_revision")},
            "counts": counts, "work_states": dict(Counter(row["state"] for row in snapshot["works"])),
            "works": works, "bindings": binding_rows, "plans": plans,
            "supervisor": snapshot["supervisor"], "limit": limit,
            "has_more": {key: counts[key] > limit for key in counts},
            "meaning": "runtime_state_not_business_adoption"}


def build_hosts(coordinator, snapshot):
    # A project companion can receive new plans after it starts. Keep both
    # supported adapters available; desktop connection itself is lazy.
    kinds = {"cli", "desktop"}
    run_root = coordinator.meta_root / "host-runs"
    hosts = {}
    if "cli" in kinds:
        hosts["cli"] = CLIResumeHost(run_root)
    if "desktop" in kinds:
        hosts["desktop"] = DesktopMCPHost(run_root)
    return hosts


def run_once(scheduler, *, ready_path=None):
    try:
        readiness = scheduler.start()
        if ready_path:
            Path(ready_path).write_text(encode({**readiness, "started_at_ms": scheduler.c.clock_ms()}), encoding="utf-8")
        outcome = scheduler.tick()
    finally:
        try:
            if scheduler.started:
                scheduler.store.release_supervisor(scheduler.instance_id)
        finally:
            for host in scheduler.hosts.values():
                host.close()
    return {"status": "ok", "mode": "shadow" if scheduler.shadow else "live", "outcome": outcome,
            "runtime": status_view(scheduler.store.status()), "meaning": "single_tick_not_completed_turn"}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", newline="")
    args = None
    try:
        args = parser().parse_args(argv)
        # Validate the output budget before any mutation or external dispatch.
        bounded_output({"status": "ok"}, budget=args.max_return_bytes)
        root = args.workspace.resolve()
        projection = args.control_projection or root / "coordination/control.json"
        gate = FileControlGate(root, projection) if projection.is_file() else None
        coordinator = TaskArtifactCoordinator(root, gate)
        store = RuntimeStore(coordinator)
        session = coordinator.bind_local_operator("AG0")
        command = args.command
        if command == "migrate":
            result = store.migrate(session)
        elif command == "bind":
            value = store.bind(session, read_object(args.binding_file))
            result = {"status": "committed", "binding": {key: value[key] for key in
                      ("id", "role", "host_kind", "host_id", "thread_id", "generation", "authorized", "authorization_ref") if key in value},
                      "identity": "trusted_local_attestation"}
        elif command == "plan":
            result = store.register_plan(session, read_object(args.plan_file))
        elif command == "status":
            result = status_view(store.status(), limit=args.limit)
        elif command == "reconcile-result":
            snapshot = store.status()
            supervisors = snapshot["supervisor"]
            if not supervisors or supervisors[0]["lease_until_ms"] <= coordinator.clock_ms():
                raise GateError("scheduler_lease_lost")
            hosts = build_hosts(coordinator, snapshot)
            try:
                scheduler = RuntimeScheduler(coordinator, hosts, instance_id=supervisors[0]["instance_id"])
                result = scheduler.reconcile_result(args.dispatch_id)
            finally:
                for host in hosts.values():
                    host.close()
        elif command in {"enable", "disable"}:
            result = store.set_enabled(session, args.workflow, command == "enable")
            result["workflow_id"] = args.workflow
        elif command in {"begin-dispatch", "result"}:
            thread_id = os.environ.get("CODEX_THREAD_ID", "").strip()
            if not thread_id or args.claim_epoch < 1:
                raise GateError("actual_dispatch_context_required")
            context = {"dispatch_id": args.dispatch_id, "claim_epoch": args.claim_epoch, "thread_id": thread_id}
            if command == "begin-dispatch":
                result = store.begin_dispatch(context, args.role)
            else:
                attempt, _, _ = store.assert_dispatch(context, args.role)
                if not attempt.get("agent_received"):
                    raise GateError("dispatch_not_received")
                saved = store.save_result(args.dispatch_id, read_object(args.result_file), context=context, role=args.role)
                result = {"status": "committed", "dispatch_id": args.dispatch_id,
                          "result_sha256": saved["result_sha256"], "meaning": "result_saved_not_business_commit"}
        else:
            snapshot = store.status()
            hosts = {} if command == "shadow" else build_hosts(coordinator, snapshot)
            scheduler = RuntimeScheduler(coordinator, hosts, shadow=command == "shadow")
            if args.once:
                result = run_once(scheduler, ready_path=args.ready_file)
            else:
                result = status_view(scheduler.run(max_seconds=args.max_seconds,
                                                  stop_when_done=args.stop_when_done, ready_path=args.ready_file))
    except GateError as error:
        result = {"status": "rejected", "problem": error.code}
        if error.code == "invalid_command_arguments":
            result["detail"] = str(error)
    except FileNotFoundError as error:
        result = {"status": "rejected", "problem": "required_file_missing", "path": str(error.filename)}
    except (ValueError, KeyError, TypeError, UnicodeError):
        result = {"status": "rejected", "problem": "invalid_request_data"}
    except sqlite3.Error as error:
        reason = "database_busy" if any(word in str(error).lower() for word in ("locked", "busy")) else "coordinator_storage_unavailable"
        result = {"status": "rejected", "problem": reason}
    except OSError:
        result = {"status": "rejected", "problem": "file_access_failed"}
    except KeyboardInterrupt:
        result = {"status": "rejected", "problem": "runtime_interrupted", "next_action": "查看status核对未决派发；未知结果不能直接重发。"}
    except Exception as error:
        # Host diagnostics and inherited connection details are never printed.
        result = {"status": "rejected", "problem": "runtime_entry_failed", "error_kind": type(error).__name__}
    try:
        output = bounded_output(result, budget=args.max_return_bytes if args else DEFAULT_RETURN_BYTES)
    except GateError as error:
        result = {"status": "rejected", "problem": error.code,
                  "next_action": "用status查询已保存记录；缩小--limit或明确提高--max-return-bytes，不能因返回过大重发任务。"}
        output = bounded_output(result)
    print(output, end="")
    return 0 if result["status"] in {"ok", "committed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
