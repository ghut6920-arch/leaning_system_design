"""Sequential explicit intents, durable recovery, one bounded control return.

This is a CLI batch, not an agent scheduler or an atomic multi-action transaction.
The existing coordinator tickets and commit receipts remain authoritative.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3

from .agent_api import AgentCoordinator, intent_shape
from .delivery import bounded_output
from .workspace import GateError, encode, identifier, sha

VERSION = "control-batch/0.1.0"
MAX_STEPS = 16


def validate_plan(value):
    if (not isinstance(value, dict) or set(value) != {"version", "steps"}
            or value["version"] != VERSION or not isinstance(value["steps"], list)
            or not 1 <= len(value["steps"]) <= MAX_STEPS):
        raise GateError("invalid_control_batch")
    seen = set()
    for step in value["steps"]:
        if not isinstance(step, dict) or set(step) != {"id", "intent"}:
            raise GateError("invalid_control_batch")
        key = identifier(step["id"])
        if len(key) > 64 or key in seen:
            raise GateError("duplicate_or_long_batch_step")
        seen.add(key)
        intent_shape(step["intent"])
    if len(encode(value).encode("utf-8")) > 131072:
        raise GateError("control_batch_too_large")


def store_journal(path, value):
    value = {**value}
    value["journal_sha256"] = sha(encode(value).encode("utf-8"))
    # Append complete checksummed snapshots. Unlike rename/replace this works
    # in restricted Windows hosts. A partial tail fails closed on recovery;
    # the original coordinator alias/receipt is still available separately.
    data = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    with path.open("ab" if path.exists() else "xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def batch_lock(path):
    try:
        stream = path.open("x", encoding="utf-8")
    except FileExistsError as error:
        raise GateError("control_batch_busy") from error
    try:
        with stream:
            stream.write(str(os.getpid()))
            stream.flush()
            os.fsync(stream.fileno())
        yield
    finally:
        path.unlink()


def run_batch(api, session, plan_path, *, retry_stopped=False, budget=8192):
    source = Path(plan_path).resolve()
    raw = source.read_bytes()
    if len(raw) > 131072:
        raise GateError("control_batch_too_large")
    plan = json.loads(raw.decode("utf-8-sig"))
    validate_plan(plan)  # Entire syntax is checked before any action.
    role = api.c.role(session)
    identity = {"role": role, "source": str(source)}
    batch_id = sha(encode(identity).encode("utf-8"))
    fingerprint = sha(encode(plan).encode("utf-8"))
    folder = api.ticket_root / "batches"
    journal_path = folder / (batch_id + ".jsonl")

    def summary(journal):
        results = journal["results"]
        committed = sum(row["result"]["status"] == "committed" for row in results)
        stopped = next((row for row in results if row["result"]["status"] != "committed"), None)
        return {"status": "committed" if committed == len(plan["steps"]) else "blocked",
                "batch_sha256": fingerprint, "receipts_path": str(journal_path),
                "committed_steps": committed, "total_steps": len(plan["steps"]),
                "not_started": [s["id"] for s in plan["steps"][len(results):]],
                **({"stopped": {"step": stopped["id"], **{k: stopped["result"][k] for k in ("status", "problem", "ticket") if k in stopped["result"]}}} if stopped else {}),
                "meaning": "原ticket/回执为准；已提交步骤不回滚，历史回执不代表当前可用。",
                "next_action": "阶段程序动作已提交；按原件接下一责任。" if committed == len(plan["steps"]) else
                               "查停止步骤的原回执；未知提交先查saved，拒绝不自动重定决定。"}

    if type(budget) is not int or not 2048 <= budget <= 65536:
        raise GateError("invalid_control_batch_budget")
    # Validate the largest normal envelope before mutations; full receipts stay
    # on disk, never replace a successful commit by a response-budget rejection.
    probe = {"results": [{"id": max((s["id"] for s in plan["steps"]), key=len), "result": {
        "status": "commit_status_unknown", "problem": "p" * 96, "ticket": "request-" + "0" * 32}}]}
    bounded_output(summary(probe), budget=budget)
    folder.mkdir(parents=True, exist_ok=True)
    with batch_lock(journal_path.with_suffix(".lock")):
        if journal_path.exists():
            content = journal_path.read_bytes()
            if not content.endswith(b"\n"):
                raise GateError("control_batch_changed_or_corrupt")
            for line in content.splitlines():
                try:
                    journal = json.loads(line)
                    digest = journal.pop("journal_sha256", None)
                    rows = journal["results"]
                    if (sha(encode(journal).encode("utf-8")) != digest or journal.get("identity") != identity
                            or journal.get("plan_sha256") != fingerprint or journal.get("plan") != plan
                            or not isinstance(rows, list) or len(rows) > len(plan["steps"])
                            or any(row["id"] != plan["steps"][i]["id"] for i, row in enumerate(rows))):
                        raise GateError("control_batch_changed_or_corrupt")
                except (ValueError, KeyError, TypeError) as error:
                    raise GateError("control_batch_changed_or_corrupt") from error
        else:
            journal = {"version": VERSION, "identity": identity, "plan_sha256": fingerprint,
                       "plan": plan, "results": []}
            store_journal(journal_path, journal)
        for index, step in enumerate(plan["steps"]):
            prior = journal["results"][index] if index < len(journal["results"]) else None
            key = "batch:" + str(source) + ":" + step["id"]
            try:
                saved = api.saved_intent(session, step["intent"], request_key=key)
                if saved["status"] == "committed":
                    result = saved
                elif prior and prior["result"]["status"] == "committed":
                    raise GateError("control_batch_receipt_missing")
                elif saved["status"] == "commit_status_unknown":
                    result = saved
                elif prior and prior["result"]["status"] not in {"not_started", "executing"}:
                    # A stopped attempt is not a new decision. Retry requires
                    # explicit intent and an existing frozen original ticket.
                    if not retry_stopped or not saved.get("ticket"):
                        return summary(journal)
                    result = api.do(session, step["intent"], request_key=key)
                else:
                    # Write the boundary before calling any business mutation;
                    # loss after commit recovers through the existing alias.
                    row = {"id": step["id"], "result": {"status": "executing"}}
                    if prior:
                        journal["results"][index] = row
                    else:
                        journal["results"].append(row)
                    store_journal(journal_path, journal)
                    result = api.do(session, step["intent"], request_key=key)
            except GateError as error:
                result = AgentCoordinator.error(error.code)
            except (ValueError, KeyError, TypeError, UnicodeError):
                result = {"status": "rejected", "problem": "invalid_request_data"}
            except sqlite3.Error:
                result = {"status": "commit_status_unknown", "problem": "coordinator_storage_unavailable"}
            except OSError:
                result = {"status": "commit_status_unknown", "problem": "file_access_failed"}
            row = {"id": step["id"], "result": result}
            if index < len(journal["results"]):
                journal["results"][index] = row
            else:
                journal["results"].append(row)
            if row != prior:
                store_journal(journal_path, journal)
            if result["status"] != "committed":
                break
        return summary(journal)
