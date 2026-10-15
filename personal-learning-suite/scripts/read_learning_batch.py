"""Run only declared read jobs, then apply one budget to their combined response."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
from coordinator.delivery import DEFAULT_RETURN_BYTES, bounded_output, verify_delivery
from coordinator.workspace import GateError, sha


def path_at(base, value):
    if not isinstance(value, str) or not value:
        raise GateError("explicit_read_path_required")
    return str((base / value).resolve())


def arguments(job, base, budget):
    kind = job.get("kind")
    if kind == "resource":
        allowed = {"id", "kind", "files", "view", "offset", "max_chars", "full", "expect_view_sha256", "entries", "sections", "heading_start", "heading_limit"}
        if not isinstance(job.get("files"), list) or not job["files"]:
            raise GateError("explicit_read_files_required")
        args = [sys.executable, "-B", "-X", "utf8", str(SUITE / "scripts/read_learning_resource.py"), "--format", "json"]
        for name in job["files"]:
            args += ["--file", path_at(base, name)]
        args += ["--view", job.get("view", "text"), "--max-return-bytes", str(budget)]
        mapping = {"offset": "--offset", "max_chars": "--max-chars", "expect_view_sha256": "--expect-view-sha256",
                   "heading_start": "--heading-start", "heading_limit": "--heading-limit"}
        for entry in job.get("entries", []):
            args += ["--entry", entry]
        for section in job.get("sections", []):
            args += ["--section", section]
    elif kind == "coordinator":
        allowed = {"id", "kind", "workspace", "role", "command", "task", "input", "view", "offset", "max_chars",
                   "full", "expect_sha256", "artifact_id", "use", "scope", "limit", "consumer", "ticket", "source"}
        command = job.get("command")
        if command not in {"inputs", "current", "desk", "alerts", "saved", "control-status"}:
            raise GateError("read_only_batch_command_required")
        args = [sys.executable, "-B", "-X", "utf8", str(SUITE / "scripts/coordinate_agents.py"),
                "--workspace", path_at(base, job.get("workspace")), "--role", job.get("role", ""),
                "--max-return-bytes", str(budget), command]
        mapping = {"task": "--task", "input": "--input", "view": "--view", "offset": "--offset", "max_chars": "--max-chars",
                   "expect_sha256": "--expect-sha256", "artifact_id": "--artifact-id", "limit": "--limit",
                   "consumer": "--consumer", "ticket": "--ticket", "source": "--source"}
        if "use" in job:
            args += ["--intended-use" if command == "current" else "--use", job["use"]]
        for scope in job.get("scope", []):
            args += ["--scope", scope]
    else:
        raise GateError("unknown_read_job_kind")
    if set(job) - allowed:
        raise GateError("unknown_read_job_fields")
    for key, flag in mapping.items():
        if key in job:
            args += [flag, str(job[key])]
    if job.get("full") is True:
        args += ["--full"]
    return args


def run_batch(path, *, budget=DEFAULT_RETURN_BYTES):
    bounded_output({"status": "ok"}, budget=budget)
    raw = path.read_bytes()
    request = json.loads(raw.decode("utf-8-sig"))
    jobs = request.get("jobs")
    if (request.get("version") != "read-batch/0.1.0" or not isinstance(jobs, list) or not 1 <= len(jobs) <= 8
            or any(not isinstance(j, dict) or not isinstance(j.get("id"), str) or not j["id"] for j in jobs)
            or len({j["id"] for j in jobs}) != len(jobs)):
        raise GateError("invalid_read_batch")
    # Validate every command before any job runs. Subprocesses use argv, never a shell.
    commands = [arguments(job, path.parent, budget) for job in jobs]
    rows = []
    for job, args in zip(jobs, commands):
        process = subprocess.run(args, capture_output=True, timeout=30)
        try:
            payload = verify_delivery(process.stdout)
        except GateError:
            payload = {"status": "rejected", "problem": "upstream_read_delivery_incomplete_or_changed",
                       "next_action": "不要补造返回；缩小请求并重取该页。"}
        rows.append({"id": job["id"], "result": payload})
    return {"status": "ok" if all(r["result"].get("status") == "ok" for r in rows) else "rejected",
            "request_sha256": sha(raw), "jobs": rows,
            "meaning": "本批次只有读取；正文共享最终返回预算。尾标记/校验仅确认接收到的页，不证明专业内容已读或已采用。"}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", newline="")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--max-return-bytes", type=int, default=DEFAULT_RETURN_BYTES)
    args = parser.parse_args()
    try:
        result = run_batch(args.request_file.resolve(), budget=args.max_return_bytes)
        output = bounded_output(result, budget=args.max_return_bytes)
    except (GateError, OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as error:
        result = {"status": "rejected", "problem": getattr(error, "code", type(error).__name__),
                  "next_action": "仅声明只读命令；缩小文件/条目批次或明确调整总预算，按原版本续读。"}
        output = bounded_output(result)
    print(output, end="")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
