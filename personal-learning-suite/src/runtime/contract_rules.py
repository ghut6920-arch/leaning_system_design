"""共享字段源的 B1 确定性检查；不替代内容核验、专业采用或宿主身份认证。"""
from __future__ import annotations

from fnmatch import fnmatchcase
import json
from pathlib import Path, PurePosixPath
import re

SUITE_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = "pl-contracts/0.1.0"


def load_definition():
    text = (SUITE_ROOT / "contracts/shared-contracts.md").read_text(encoding="utf-8-sig")
    match = re.search(r"<!-- b0-contract-definition -->\s*```json\s*(.*?)\s*```", text, re.S)
    if not match:
        raise ValueError("shared contract definition missing")
    return json.loads(match.group(1))


def walk(value):
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def object_refs(value):
    for item in walk(value):
        if isinstance(item, dict) and "id" in item and "type" not in item:
            yield item


def artifact_paths(value):
    return {item["path"] for item in walk(value) if isinstance(item, dict) and {"path", "locator", "origin"}.issubset(item) and isinstance(item["path"], str)}


def safe_artifact_path(path):
    if not isinstance(path, str) or not path or "\\" in path or ":" in path or "\x00" in path:
        return False
    logical = PurePosixPath(path)
    return not logical.is_absolute() and all(part not in ("..", ".") for part in path.split("/")) and "//" not in path


def validate_records(records, artifacts, synthetic_only=True):
    """records 包含可读取的确切历史修订，artifacts 为不可变逻辑路径→正文。"""
    definition = load_definition()
    errors = []

    def fail(code, detail):
        # 不把待提交正文写进错误、日志或回执。
        errors.append({"code": code, "detail": str(detail)})

    if not isinstance(records, list) or not isinstance(artifacts, dict):
        return [{"code": "FORMAT", "detail": "records/list and artifacts/dict required"}]
    by_ref = {}
    for record in records:
        if not isinstance(record, dict):
            fail("FORMAT", "record must be object")
            continue
        identifier, revision = record.get("id"), record.get("revision")
        if not isinstance(identifier, str) or not identifier or type(revision) is not int or revision < 1:
            fail("OBJECT_ID", "id or revision invalid")
            continue
        key = identifier, revision
        if key in by_ref:
            fail("DUPLICATE_OBJECT", identifier)
        by_ref[key] = record
    for path, text in artifacts.items():
        if not safe_artifact_path(path) or not isinstance(text, str):
            fail("ARTIFACT_PATH", "unsafe logical artifact key or non-text artifact")

    def resolve(ref, kind=None):
        if not isinstance(ref, dict) or not isinstance(ref.get("id"), str) or type(ref.get("revision")) is not int:
            return None
        found = by_ref.get((ref["id"], ref["revision"]))
        return found if found and (kind is None or found.get("type") == kind) else None

    def typed(ref, kind, identifier):
        found = resolve(ref, kind)
        if not found:
            fail("REF_TYPE", f"{identifier}: expected {kind}")
        return found

    def grant_covers(grant, actor, decision, refs, criteria):
        if not grant or grant.get("grantee") != actor or decision not in grant.get("decision_types", []):
            return False
        scopes = grant.get("object_scope", [])
        if not isinstance(scopes, list) or not scopes or not all(isinstance(s, str) for s in scopes):
            return False
        if not all(any(fnmatchcase(ref.get("id", ""), scope) for scope in scopes) for ref in refs if isinstance(ref, dict)):
            return False
        permitted = grant.get("criterion_refs", [])
        for ref in criteria:
            if not isinstance(ref, dict):
                return False
            matching = [item for item in permitted if isinstance(item, dict) and item.get("id") == ref.get("id") and item.get("revision") == ref.get("revision")]
            if ref.get("locator"):
                matching = [item for item in matching if item.get("locator") == ref["locator"]]
            if not matching:
                return False
        return True

    samples, operations = {}, {}
    for record in records:
        if not isinstance(record, dict):
            continue
        identifier = record.get("id", "invalid")
        kind = record.get("type")
        spec = definition["objects"].get(kind)
        if not spec:
            fail("OBJECT_TYPE", identifier)
            continue
        for field in definition["base_required"] + spec["required"]:
            if field not in record:
                fail("REQUIRED_FIELD", f"{identifier}/{field}")
        if record.get("schema_version") != PROTOCOL:
            fail("PROTOCOL", identifier)
        if record.get("owner") not in spec["owners"]:
            fail("OWNER_SCOPE", identifier)
        if not isinstance(record.get("basis_refs"), list):
            fail("REF_SHAPE", f"{identifier}/basis_refs")

        for ref in object_refs(record):
            if not isinstance(ref.get("id"), str) or type(ref.get("revision")) is not int or ref.get("revision", 0) < 1:
                fail("REF_SHAPE", identifier)
            elif not resolve(ref):
                fail("BROKEN_REF", identifier)
            if "locator" in ref and (not isinstance(ref["locator"], str) or not ref["locator"]):
                fail("REF_SHAPE", identifier)
            found = resolve(ref)
            if found and str(ref.get("locator", "")).startswith("requirements/"):
                requirement_id = ref["locator"].split("/", 1)[1]
                if found.get("type") != "GoalSpec" or not any(r.get("requirement_id") == requirement_id for r in found.get("requirements", []) if isinstance(r, dict)):
                    fail("CRITERION_REF", identifier)

        for value in walk(record):
            if not isinstance(value, dict):
                continue
            if "type" not in value and value.get("status") in definition["fact_statuses"]:
                if set(value) - {"status", "value", "reason"}:
                    fail("FACT", identifier)
                if value["status"] == "known":
                    if "value" not in value:
                        fail("FACT", identifier)
                elif "value" in value or not isinstance(value.get("reason"), str) or not value["reason"]:
                    fail("FACT", identifier)
            if {"path", "locator", "origin"}.issubset(value):
                path = value["path"]
                if not safe_artifact_path(path) or value.get("revision") != 1:
                    fail("ARTIFACT_PATH", identifier)
                elif path not in artifacts:
                    fail("ARTIFACT_MISSING", identifier)
                elif not isinstance(value["locator"], str) or not value["locator"] or value["locator"] not in artifacts[path]:
                    fail("ARTIFACT_LOCATOR", identifier)
                if synthetic_only and value["origin"] != "synthetic_fixture":
                    fail("SYNTHETIC_ONLY", identifier)

        if kind == "GoalSpec":
            requirements = record.get("requirements", [])
            prerequisites = record.get("prerequisites", [])
            if not isinstance(requirements, list) or not requirements or not isinstance(prerequisites, list):
                fail("GOAL_FORMAT", identifier)
                continue
            ids = [req.get("requirement_id") for req in requirements if isinstance(req, dict)]
            if len(ids) != len(requirements) or len(ids) != len(set(ids)) or any(not isinstance(i, str) or not i for i in ids):
                fail("GOAL_FORMAT", identifier)
            groups = [record] + requirements + prerequisites + [req.get("criterion", {}) for req in requirements if isinstance(req, dict)]
            for group in groups:
                if not isinstance(group, dict):
                    fail("GOAL_FORMAT", identifier)
                    continue
                for field in ("requirement_source_refs", "content_basis_refs"):
                    refs = group.get(field)
                    if not isinstance(refs, list) or not refs:
                        fail("GOAL_DUAL_SOURCE", identifier)
                    else:
                        for ref in refs:
                            typed(ref, "SourceFragment", identifier)
            for req in requirements:
                if isinstance(req, dict) and (type(req.get("criterion_revision")) is not int or not req.get("key_operations") or not req.get("product") or not req.get("nature")):
                    fail("GOAL_FORMAT", identifier)

        elif kind == "SourceFragment":
            ref = record.get("source_ref", {})
            if not isinstance(ref, dict) or not all(ref.get(field) for field in ("source_id", "declared_revision", "locator", "identity_kind")):
                fail("SOURCE_REF", identifier)
            elif synthetic_only and ref["identity_kind"] != "synthetic":
                fail("SYNTHETIC_ONLY", identifier)

        elif kind == "AuthorizationGrant":
            if record.get("issuer") != record.get("owner"):
                fail("GRANT_ISSUER", identifier)
            if synthetic_only and record.get("binding_status") != "verified_for_fixture":
                fail("SYNTHETIC_ONLY", identifier)
            for ref in record.get("criterion_refs", []):
                typed(ref, "GoalSpec", identifier)

        elif kind == "PerformanceEvent":
            typed(record.get("activity_ref"), "ActivitySpec", identifier)
            original = record.get("original_response", {})
            if not isinstance(original, dict) or not all(original.get(field) for field in ("path", "locator", "revision", "origin")):
                fail("ORIGINAL_ARTIFACT", identifier)
            timeline = record.get("timeline", [])
            if not isinstance(timeline, list) or not timeline or not all(isinstance(e, dict) for e in timeline):
                fail("TIMELINE", identifier)
                continue
            sequences = [e.get("sequence") for e in timeline]
            if any(type(seq) is not int for seq in sequences) or sequences != sorted(set(sequences)) or not any(e.get("kind") == "initial_response" for e in timeline):
                fail("TIMELINE", identifier)
            for event in timeline:
                if any(field not in event for field in ("kind", "sequence", "visibility", "content", "target_operations", "substituted_operations", "time")) or event.get("visibility") not in ("planned", "requested", "displayed", "backend_reference", "unknown"):
                    fail("TIMELINE", identifier)
            sample = record.get("independent_sample_id")
            if not isinstance(sample, str) or not sample:
                fail("SAMPLE", identifier)
            elif sample in samples and samples[sample] != identifier:
                fail("SAMPLE_DUPLICATION", identifier)
            samples[sample] = identifier

        elif kind in ("Judgment", "DiagnosticNote"):
            grant = typed(record.get("authorization_ref"), "AuthorizationGrant", identifier)
            if kind == "Judgment":
                goal = typed(record.get("goal_ref"), "GoalSpec", identifier)
                requirement_id = record.get("requirement_id")
                requirement = next((r for r in (goal or {}).get("requirements", []) if r.get("requirement_id") == requirement_id), None)
                if not requirement or record.get("criterion_revision") != requirement.get("criterion_revision"):
                    fail("CRITERION_REVISION", identifier)
                if record.get("support") not in definition["support_values"] or record.get("eligibility") not in definition["eligibility_values"]:
                    fail("JUDGMENT_AXIS", identifier)
                event_refs = record.get("event_refs", [])
                if not isinstance(event_refs, list) or not event_refs:
                    fail("JUDGMENT_EVENTS", identifier)
                    event_refs = []
                scope_refs = list(event_refs)
                for ref in event_refs:
                    event = typed(ref, "PerformanceEvent", identifier)
                    if event:
                        scope_refs.append(event["activity_ref"])
                criteria = [dict(record.get("goal_ref", {}), locator=f"requirements/{requirement_id}")]
                decision = record.get("decision_type")
                if record.get("owner") == "AG0" and decision != "routine_scoring":
                    fail("AUTHORITY_SCOPE", identifier)
            else:
                scope_refs = record.get("observations", [])
                criteria = record.get("goal_refs", [])
                decision = record.get("decision_type")
                if decision != "limited_diagnosis" or not record.get("decision_branches") or not record.get("alternatives"):
                    fail("DIAGNOSTIC_SCOPE", identifier)
            if not grant_covers(grant, record.get("owner"), decision, scope_refs, criteria):
                fail("AUTHORITY_SCOPE", identifier)

        elif kind == "ActivitySpec":
            for ref in record.get("goal_refs", []):
                typed(ref, "GoalSpec", identifier)
            parent = record.get("parent_task", {})
            if isinstance(parent, dict) and parent.get("status") == "known":
                value = parent.get("value", {})
                fields = ("parent_activity_ref", "parent_artifact", "blocker", "entry_basis_refs", "alternative_explanations", "local_sufficiency", "return_connection", "budget_ref")
                if not isinstance(value, dict) or any(field not in value for field in fields):
                    fail("PARENT_TASK", identifier)
                else:
                    typed(value["parent_activity_ref"], "ActivitySpec", identifier)
                    if value["parent_activity_ref"].get("id") == identifier or value["budget_ref"] != record.get("budget_ref") or not value["return_connection"]:
                        fail("PARENT_TASK", identifier)

        elif kind == "PlanCommitment":
            typed(record.get("budget_ref"), "BudgetEnvelope", identifier)
            for ref in record.get("adopted_basis_refs", []):
                basis = resolve(ref)
                if basis and "adoption" in basis and basis["adoption"].get("status") not in ("adopted", "partially_adopted"):
                    fail("UNADOPTED_BASIS", identifier)

        elif kind == "LearningNeed":
            disposition = record.get("disposition", {})
            if not isinstance(disposition, dict):
                fail("NEED_DISPOSITION", identifier)
                continue
            status = disposition.get("status")
            if status not in ("pending", "scheduled", "partially_scheduled", "merged", "deferred", "no_further_investment", "closed", "returned"):
                fail("NEED_DISPOSITION", identifier)
            if status != "pending" and (not disposition.get("reason") or not record.get("uncovered_impact") or not record.get("next_trigger")):
                fail("NEED_DISPOSITION", identifier)
            if status in ("scheduled", "partially_scheduled"):
                refs = disposition.get("commitment_refs", [])
                if not refs or record.get("acceptance", {}).get("status") not in ("accepted", "partially_accepted"):
                    fail("NEED_DISPOSITION", identifier)
                for ref in refs:
                    plan = typed(ref, "PlanCommitment", identifier)
                    if plan and plan.get("status") != "active":
                        fail("NEED_DISPOSITION", identifier)
            if status == "merged" and not disposition.get("requirement_mapping"):
                fail("NEED_DISPOSITION", identifier)

        elif kind == "WorkOrder":
            operation = record.get("operation_id")
            if not isinstance(operation, str) or not operation:
                fail("OPERATION_ID", identifier)
            elif operation in operations and operations[operation] != identifier:
                fail("OPERATION_DUPLICATION", identifier)
            operations[operation] = identifier
            grants = [typed(ref, "AuthorizationGrant", identifier) for ref in record.get("authorization_refs", [])]
            network = record.get("metadata", {}).get("network", {})
            unready = (network.get("version") == "pl-network/0.1.0"
                       and network.get("phase") == "proposed_unready"
                       and record.get("authorization_refs") == []
                       and record.get("acceptance", {}).get("status") == "proposed")
            if not unready and not any(grant_covers(grant, record.get("assignee"), record.get("decision_type"), record.get("event_refs", []) + record.get("material_refs", []), record.get("goal_and_criteria_refs", [])) for grant in grants):
                fail("AUTHORITY_SCOPE", identifier)

        elif kind == "UseRestriction":
            if record.get("status") == "lifted" and not record.get("restoration_refs"):
                fail("RESTRICTION_RESTORE", identifier)
    return errors
