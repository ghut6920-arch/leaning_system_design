"""Refresh only the declared coordination and bounded-reading entries."""
from __future__ import annotations

import json
from pathlib import Path
import sys

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
from coordinator.workspace import sha


def main():
    root = SUITE.parent / "learning/embodied-intelligence"
    manifest_path = root / "framework-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    allowed = {"AGENTS.md", "MODEL_ENTRY.md", "FRAMEWORK.md", "START_PROMPT.md", "templates/checkpoint.md"} | {f"../../personal-learning-suite/src/agents/{name}" for name in ("AG0-coach.md", "AG1-design-planning.md", "AG2-materials.md", "AG3-assessment.md")}
    new = ["COORDINATION.md", "../../personal-learning-suite/specs/coordinator-protocol.md", "../../personal-learning-suite/specs/coordinator-agent-guide.md"]
    new += [f"../../personal-learning-suite/src/coordinator/{name}.py" for name in ("__init__", "workspace", "reliability", "complete", "publication", "agent_api", "reading", "control_projection", "delivery", "control_batch", "preparation_sources")]
    new += ["../../personal-learning-suite/scripts/coordinate_preparation.py", "../../personal-learning-suite/scripts/coordinate_agents.py",
            "../../personal-learning-suite/scripts/read_learning_resource.py", "../../personal-learning-suite/scripts/read_learning_batch.py",
            "../../personal-learning-suite/scripts/check_read_delivery.py", "../../personal-learning-suite/specs/preparation-execution.md",
            "../../personal-learning-suite/src/skills/learning-strategies/references/selection-adaptation.md"]
    new += ["../../personal-learning-suite/scripts/build_b3c_resources.py", "../../personal-learning-suite/src/runtime/strategy_layers.py",
            "../../personal-learning-suite/src/runtime/learning_strategies.py", "../../personal-learning-suite/src/skills/learning-strategies/SKILL.md",
            "../../personal-learning-suite/src/skills/learning-teaching/references/post-encoding.md", "../../personal-learning-suite/contracts/strategies-b3c.md",
            "../../personal-learning-suite/specs/skills/SK06-learning-strategies.md"]
    new += ["../../personal-learning-suite/scripts/build_preparation_sources.py",
            "../../personal-learning-suite/src/skills/learning-teaching/references/design-whole.md",
            "../../personal-learning-suite/src/skills/learning-materials/references/materials-workflow.md",
            "../../personal-learning-suite/src/skills/learning-assessment/references/product-review.md"]
    new += ["../../personal-learning-suite/specs/coordinator-runtime.md",
            "../../personal-learning-suite/scripts/coordinate_runtime.py",
            "../../personal-learning-suite/scripts/start_coordinator_runtime.ps1"]
    new += [f"../../personal-learning-suite/src/coordinator/{name}.py" for name in ("runtime_store", "runtime_scheduler", "hosts/__init__", "hosts/desktop_mcp", "hosts/cli_resume")]
    new += ["../../personal-learning-suite/specs/preparation-runtime-start.md", "../../personal-learning-suite/scripts/start_preparation.py"]
    new += [f"../../personal-learning-suite/src/coordinator/{name}.py" for name in ("preparation_start", "preparation_graph", "runtime_companion", "runtime_outputs")]
    new += [f"../../personal-learning-suite/resources/strategies/{name}" for name in ("strategy-index.json", "manifest.json", "README.md")]
    strategy_index = json.loads((SUITE / "resources/strategies/strategy-index.json").read_text(encoding="utf-8-sig"))
    for entry in strategy_index["entries"]:
        runtime_path = entry.get("runtime_path")
        if runtime_path is not None:
            if runtime_path != "runtime/" + entry["bundle_path"] or ".." in runtime_path.split("/"):
                raise ValueError("Invalid declared runtime layer path")
            new.append("../../personal-learning-suite/resources/strategies/" + runtime_path)
    # Never silently bless unrelated instruction/resource drift.
    allowed.update(new)
    unexpected = [e["path"] for e in manifest["entries"] if e["path"] not in allowed and sha((root / e["path"]).read_bytes()) != e["sha256"]]
    if unexpected:
        raise ValueError(f"Unrelated framework drift: {unexpected}")
    paths = [e["path"] for e in manifest["entries"]]
    paths += [p for p in new if p not in paths]
    manifest["entries"] = [{"path": p, "sha256": sha((root / p).read_bytes())} for p in paths]
    # Policy is persistent; actual listener health comes only from its live
    # receipt and DB lease, never this generated framework snapshot.
    policy = {"default": "real_specialist_agents", "roles": ["AG2", "AG1", "AG3"], "user_entry": "AG0",
              "routing": "automatic_event_runtime_on_preparation_start",
              "guide": "../../personal-learning-suite/specs/preparation-runtime-start.md",
              "startup_command": "start-preparation", "automatic_current_chat_binding": True,
              "automatic_project_runtime_initialization": True, "failure_policy": "report_no_model_polling_fallback"}
    entry_path = root / "coordination/entry.json"
    entry = json.loads(entry_path.read_text(encoding="utf-8-sig"))
    entry.update(events="python_persistent_events_for_preparation", preparation_dispatch_policy=policy)
    entry["agent_interface"]["preparation_start"] = "start-preparation --request-file FILE"
    entry["event_runtime"] = {"startup_script": "../../personal-learning-suite/scripts/start_preparation.py",
                              "runtime_status_script": "../../personal-learning-suite/scripts/coordinate_runtime.py",
                              "listener_health": "query_live_runtime_lease_and_receipt", "initialization_scope": "once_per_project",
                              "ordinary_feedback": "existing_manual_file_protocol"}
    entry_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest.update(generated_at="2026-10-15", coordination_binding={"mode": "event_runtime_for_preparation", "entry": "coordination/entry.json", "identity": "local_operator_attested", "llm_dispatch": True, "event_runtime_available": True, "activation": "automatic_per_preparation_start", "listener_health": "query_runtime_not_manifest", "context_updates": "python_event_wakeup_and_business_gates"},
                    preparation_dispatch_policy=policy)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "synchronized", "entries": len(paths), "unrelated_drift": unexpected}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
