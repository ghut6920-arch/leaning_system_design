"""Read-only checks of live versions, resource fidelity and protected learning files."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import re
import sys

SUITE = Path(__file__).resolve().parents[1]
PROJECT = SUITE.parent
sys.path.insert(0, str(SUITE / "src"))
sys.path.insert(0, str(SUITE / "scripts"))
from coordinator.complete import TaskArtifactCoordinator
from coordinator.reading import verified_view
from coordinator.workspace import FileControlGate, sha
from read_learning_resource import manifest_view, strategy_document, strategy_payload


def restore(value, bodies):
    if isinstance(value, dict):
        if set(value) == {"$full_text"}:
            return bodies[value["$full_text"]]
        return {key: restore(item, bodies) for key, item in value.items()}
    if isinstance(value, list):
        return [restore(item, bodies) for item in value]
    return value


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to(PROJECT / "maintenance") or not (output / "learning-before.json").is_file():
        raise ValueError("Use the maintenance directory containing the preserved baseline")
    root = PROJECT / "learning/embodied-intelligence"
    c = TaskArtifactCoordinator(root, FileControlGate(root, root / "coordination/control.json"))
    session = c.bind_local_operator("AG0")
    item = c.resolve(session, "EMB-M21-MATERIAL-20261014-01", "teaching", ["M2.1"])
    short = {"status": "ok", **verified_view(item, root=root)}
    legacy = {"status": "ok", **{k: v for k, v in item.items() if k != "content"},
              "content_base64": base64.b64encode(item["content"]).decode("ascii")}
    assert "text" not in short and "content_base64" not in short
    assert short["ref"] == item["ref"] and short["sha256"] == sha(item["content"])
    paths = []
    for path in (SUITE / "resources/strategies").rglob("*.json"):
        source = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(source, dict) and source.get("compiled") and "content_markdown" in source:
            paths.append(path)
    files, bodies = strategy_payload(paths)
    for path, row in zip(paths, files):
        assert restore(row["fields"], bodies) == json.loads(path.read_text(encoding="utf-8-sig"))
    chosen = [SUITE / "resources/strategies/post" / name for name in ("retrieve-relation.json", "select-method.json")]
    document, _ = strategy_document(chosen)
    baseline = json.loads((output / "learning-before.json").read_text(encoding="utf-8"))
    allowed = {"AGENTS.md", "MODEL_ENTRY.md", "FRAMEWORK.md", "COORDINATION.md", "framework-manifest.json"}
    changes = []
    for name, expected in baseline.items():
        path = PROJECT / name
        actual = sha(path.read_bytes()) if path.is_file() else None
        if actual != expected:
            if path.name.endswith(("-shm", "-wal")):
                continue  # SQLite transient lock/cache bytes are not learning facts.
            changes.append(name)
            assert path.relative_to(root).as_posix() in allowed, "Unexpected learning modification: " + name
    manifest = manifest_view(root / "framework-manifest.json", changes_only=True)
    assert manifest["status"] == "ok", manifest
    modified_docs = [SUITE / "specs/coordinator-agent-guide.md", SUITE / "specs/preparation-execution.md",
                     SUITE / "src/agents/AG0-coach.md", SUITE / "src/agents/AG3-assessment.md",
                     SUITE / "src/skills/learning-strategies/references/selection-adaptation.md"]
    broken = []
    for path in modified_docs:
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8-sig")):
            if link.startswith(("http://", "https://", "#")):
                continue
            if not (path.parent / link.split("#")[0]).resolve().exists():
                broken.append({"path": str(path), "link": link})
    assert not broken, broken
    result = {"status": "pass", "measurement": "serialized JSON characters, not tokens or subscription savings",
              "current_material_ref": short["ref"], "current_material_sha256": short["sha256"],
              "legacy_encoded_current_chars": len(json.dumps(legacy, ensure_ascii=False, indent=2)),
              "metadata_current_chars": len(json.dumps(short, ensure_ascii=False, indent=2)),
              "all_complete_strategy_packages_roundtripped": len(paths),
              "selected_post_package_raw_json_chars": sum(len(p.read_text(encoding="utf-8-sig")) for p in chosen),
              "selected_post_package_full_view_chars": len(document),
              "manifest_entries_verified": manifest["checked_entries"], "broken_local_links": broken,
              "learning_originals_and_durable_database_unchanged": True,
              "only_learning_framework_edits": changes}
    (output / "read-only-checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
