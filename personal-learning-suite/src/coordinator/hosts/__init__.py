"""Bounded host operations; execution evidence never substitutes for business receipts.

Bindings and attempts are ordinary dictionaries so the scheduler can persist them.
Adapters only transport explicit professional results; they never invent or apply
an AgentCoordinator intent. ``result_saved`` is execution evidence, not adoption.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol


class HostAdapter(Protocol):
    def inspect(self, binding: dict) -> dict: ...
    def dispatch(self, binding: dict, prompt: str, dispatch_id: str) -> dict: ...
    def observe(self, binding: dict, attempt: dict) -> dict: ...
    def close(self) -> None: ...


def _intent(action: str, **fields: dict) -> dict:
    properties = {"action": {"type": "string", "enum": [action]}, **fields}
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


_STRING = {"type": "string"}
_STRINGS = {"type": "array", "items": _STRING}
_REF = {"type": "object", "properties": {"id": _STRING, "revision": {"type": "integer"}},
        "required": ["id", "revision"], "additionalProperties": False}
# Each entry is an explicit professional business decision. A workflow can pass
# a more specific schema for assignment or additional AgentCoordinator fields.
DEFAULT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "dispatch_id": _STRING,
        "output": _STRING,
        "intents": {"type": "array", "items": {"anyOf": [
            _intent("deliver", task=_STRING, path=_STRING),
            _intent("opinion", task=_STRING, outcome=_STRING, rationale=_STRING),
            _intent("opinion", task=_STRING, outcome=_STRING, rationale=_STRING,
                    allow_provisional={"type": "boolean"}),
            _intent("opinion", task=_STRING, outcome=_STRING, rationale=_STRING,
                    allow_provisional={"type": "boolean"}, supersedes_receipt_ids=_STRINGS),
            _intent("adopt", tasks=_STRINGS),
            _intent("stop", task=_STRING, outcome=_STRING, reason=_STRING),
            _intent("check_change", **{"task": _STRING, "from": _REF, "to": _REF,
                                      "scope": _STRINGS, "use": _STRING, "rationale": _STRING}),
        ]}},
    },
    "required": ["dispatch_id", "output", "intents"],
    "additionalProperties": False,
}


def structured_result(value, dispatch_id: str) -> dict | None:
    """Validate transport shape and correlation, leaving business gates to the API."""
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("```json\n") and value.endswith("\n```"):
            value = value[8:-4]
        try:
            value = json.loads(value)
        except ValueError:
            return None
    if (not isinstance(value, dict) or value.get("dispatch_id") != dispatch_id
            or not isinstance(value.get("output"), str)
            or not isinstance(value.get("intents"), list)):
        return None
    if any(not isinstance(i, dict) or not isinstance(i.get("action"), str)
           or not i["action"].strip() for i in value["intents"]):
        return None
    return value


def dispatch_prompt(prompt: str, dispatch_id: str, *, allow_persisted_result=False) -> str:
    persisted = ("\nIf the coordinator explicitly instructed persisting the structured result"
                 " with its result command, follow that protocol; after successful persistence"
                 " a normal user-facing final response is allowed. Otherwise, "
                 if allow_persisted_result else "\n")
    return (prompt + "\n\nCoordinator dispatch_id: " + dispatch_id + persisted
            + "Return a JSON object with dispatch_id exactly as above, output (string),"
              " and intents (array of explicit professional business intent objects)."
              " An empty intents array is allowed. Do not infer approval or adoption"
              " from execution completion. End this turn after delivering the result.")


def attempt_directory(run_root: Path, dispatch_id: str) -> Path:
    # Dispatch IDs are scheduler-generated identifiers, never filesystem paths.
    if (not isinstance(dispatch_id, str) or not dispatch_id or len(dispatch_id) > 160
            or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for c in dispatch_id)
            or dispatch_id in {".", ".."} or dispatch_id.endswith((".", " "))):
        raise ValueError("invalid_dispatch_id")
    path = (run_root / dispatch_id).resolve()
    if not path.is_relative_to(run_root.resolve()):
        raise ValueError("invalid_dispatch_path")
    return path


def save_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        output.write(json.dumps(value, ensure_ascii=False, indent=2))
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


# Import after the shared helpers to keep both adapters dependency-free.
from .desktop_mcp import DesktopMCPHost, StdioMCPClient  # noqa: E402
from .cli_resume import CLIResumeHost  # noqa: E402

__all__ = ["HostAdapter", "DesktopMCPHost", "CLIResumeHost", "StdioMCPClient", "DEFAULT_OUTPUT_SCHEMA"]
