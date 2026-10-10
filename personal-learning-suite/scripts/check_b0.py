"""B0 静态检查。只读取设计源和虚构快照；不是记录服务或授权执行器。"""
from __future__ import annotations

import argparse
import copy
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def contract_definition():
    text = (ROOT / "contracts/shared-contracts.md").read_text(encoding="utf-8-sig")
    match = re.search(r"<!-- b0-contract-definition -->\s*```json\s*(.*?)\s*```", text, re.S)
    if not match:
        raise ValueError("缺少共用契约内唯一字段定义")
    return json.loads(match.group(1))


def walk(value, path=""):
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item, f"{path}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, f"{path}/{index}")


def validate_snapshot(data, definition):
    """检查虚构快照的明确字段关系；不决定学习结论或真实提交资格。"""
    errors = []

    def fail(code, detail):
        errors.append({"code": code, "detail": detail})

    if data.get("synthetic") is not True:
        fail("SYNTHETIC_REQUIRED", "脚本拒绝当作真实个人记录验证")
    if data.get("protocol_version") != definition["protocol_version"]:
        fail("PROTOCOL_VERSION", "夹具协议不匹配")
    objects = data.get("objects", [])
    by_ref = {}
    for obj in objects:
        key = (obj.get("id"), obj.get("revision"))
        if key in by_ref:
            fail("DUPLICATE_OBJECT", str(key))
        by_ref[key] = obj

    def resolve(ref, expected_type=None):
        if not isinstance(ref, dict):
            return None
        found = by_ref.get((ref.get("id"), ref.get("revision")))
        if found and expected_type and found.get("type") != expected_type:
            fail("REF_TYPE", f"{ref.get('id')} 应为 {expected_type}")
            return None
        return found

    def grant_covers(grant, actor, decision, object_refs, criterion_refs):
        if not grant or grant.get("grantee") != actor or decision not in grant.get("decision_types", []):
            return False
        patterns = grant.get("object_scope", [])
        if not patterns or not all(any(fnmatchcase(ref.get("id", ""), pattern) for pattern in patterns) for ref in object_refs):
            return False
        allowed = grant.get("criterion_refs", [])
        for requested in criterion_refs:
            matches = [ref for ref in allowed if ref.get("id") == requested.get("id") and ref.get("revision") == requested.get("revision")]
            if requested.get("locator"):
                matches = [ref for ref in matches if ref.get("locator") == requested["locator"]]
            if not matches:
                return False
        return True

    samples, operations = {}, {}
    for obj in objects:
        name, kind = obj.get("id", "?"), obj.get("type")
        spec = definition["objects"].get(kind)
        if not spec:
            fail("UNKNOWN_OBJECT", str(kind))
            continue
        for field in definition["base_required"] + spec["required"]:
            if field not in obj:
                fail("REQUIRED_FIELD", f"{name}/{field}")
        if type(obj.get("revision")) is not int or obj["revision"] < 1:
            fail("REVISION", name)
        if obj.get("schema_version") != definition["protocol_version"]:
            fail("PROTOCOL_VERSION", name)
        if obj.get("owner") not in spec["owners"]:
            fail("OWNER_SCOPE", f"{name}: {obj.get('owner')}")
        if not str(name).startswith("FIX-"):
            fail("SYNTHETIC_ID", str(name))

        for path, value in walk(obj):
            if not isinstance(value, dict):
                continue
            if "id" in value and "type" not in value:
                if type(value.get("revision")) is not int or value.get("revision", 0) < 1:
                    fail("REFERENCE_SHAPE", f"{name}{path}: ObjectRef 缺合法修订")
                elif not resolve(value):
                    fail("BROKEN_REF", f"{name}{path}: {value}")
            if "type" not in value and value.get("status") in definition["fact_statuses"]:
                if set(value) - {"status", "value", "reason"}:
                    fail("FACT_STATUS", f"{name}{path}: Fact 包含额外载荷")
                if value["status"] == "known":
                    if "value" not in value:
                        fail("FACT_STATUS", f"{name}{path}: known 无 value")
                elif "value" in value or not value.get("reason"):
                    fail("FACT_STATUS", f"{name}{path}: 未知等状态带 value 或缺原因")
            if {"path", "locator", "origin"}.issubset(value):
                if value["origin"] != "synthetic_fixture":
                    fail("SYNTHETIC_ARTIFACT", f"{name}{path}")
                artifact = (ROOT / "fixtures" / value["path"]).resolve()
                if not artifact.is_relative_to((ROOT / "fixtures").resolve()) or not artifact.is_file():
                    fail("ARTIFACT_PATH", f"{name}{path}")
                elif value["locator"] not in artifact.read_text(encoding="utf-8-sig"):
                    fail("ARTIFACT_LOCATOR", f"{name}{path}")

        if kind == "GoalSpec":
            groups = [obj] + obj.get("requirements", []) + obj.get("prerequisites", [])
            groups += [item.get("criterion", {}) for item in obj.get("requirements", [])]
            for group in groups:
                for field in ("requirement_source_refs", "content_basis_refs"):
                    refs = group.get(field, [])
                    if not refs:
                        fail("GOAL_DUAL_SOURCE", f"{name}: {field} 缺失")
                    for ref in refs:
                        resolve(ref, "SourceFragment")
            ids = [item.get("requirement_id") for item in obj.get("requirements", [])]
            if not ids or None in ids or len(set(ids)) != len(ids):
                fail("REQUIREMENT_ID", name)

        elif kind == "PerformanceEvent":
            resolve(obj.get("activity_ref"), "ActivitySpec")
            original = obj.get("original_response", {})
            if not isinstance(original, dict) or not all(original.get(field) for field in ("path", "locator", "revision", "origin")):
                fail("ORIGINAL_ARTIFACT", name)
            timeline = obj.get("timeline", [])
            if not timeline or not any(item.get("kind") == "initial_response" for item in timeline):
                fail("TIMELINE_CONTENT", name)
            seqs = [item.get("sequence") for item in timeline]
            if any(type(x) is not int for x in seqs) or seqs != sorted(set(seqs)):
                fail("TIMELINE_ORDER", name)
            for event in timeline:
                needed = ("kind", "sequence", "visibility", "content", "target_operations", "substituted_operations", "time")
                if any(field not in event for field in needed):
                    fail("TIMELINE_FIELD", name)
                if event.get("visibility") not in ("planned", "requested", "displayed", "backend_reference", "unknown"):
                    fail("VISIBILITY", name)
            sample = obj.get("independent_sample_id")
            if sample in samples and samples[sample] != name:
                fail("SAMPLE_DUPLICATION", f"{sample}: {samples[sample]}, {name}")
            samples[sample] = name

        elif kind == "Judgment":
            if obj.get("support") not in definition["support_values"] or obj.get("eligibility") not in definition["eligibility_values"]:
                fail("JUDGMENT_AXIS", name)
            goal = resolve(obj.get("goal_ref"), "GoalSpec")
            req = next((r for r in (goal or {}).get("requirements", []) if r.get("requirement_id") == obj.get("requirement_id")), None)
            if not req or obj.get("criterion_revision") != req.get("criterion_revision"):
                fail("CRITERION_REVISION", name)
            for ref in obj.get("event_refs", []):
                resolve(ref, "PerformanceEvent")
            grant = resolve(obj.get("authorization_ref"), "AuthorizationGrant")
            decision = obj.get("decision_type")
            event_refs = obj.get("event_refs", [])
            scope_refs = event_refs + [event["activity_ref"] for ref in event_refs if (event := resolve(ref)) and "activity_ref" in event]
            requested_criterion = dict(obj.get("goal_ref", {}), locator=f"requirements/{obj.get('requirement_id')}")
            if not grant_covers(grant, obj.get("owner"), decision, scope_refs, [requested_criterion]):
                fail("AUTHORITY_SCOPE", name)
            elif grant.get("binding_status") != "verified_for_fixture":
                fail("FIXTURE_BINDING", name)
            if obj.get("owner") == "AG0" and decision != "routine_scoring":
                fail("AUTHORITY_SCOPE", f"{name}: AG0 不拥有重要复核权")

        elif kind == "PlanCommitment":
            resolve(obj.get("budget_ref"), "BudgetEnvelope")
            for ref in obj.get("adopted_basis_refs", []):
                basis = resolve(ref)
                if basis and "adoption" in basis and basis["adoption"].get("status") not in ("adopted", "partially_adopted"):
                    fail("UNADOPTED_BASIS", f"{name}: {basis['id']}")

        elif kind == "DiagnosticNote":
            grant = resolve(obj.get("authorization_ref"), "AuthorizationGrant")
            if obj.get("decision_type") != "limited_diagnosis" or not grant_covers(grant, obj.get("owner"), "limited_diagnosis", obj.get("observations", []), obj.get("goal_refs", [])):
                fail("DIAGNOSTIC_AUTHORITY", name)

        elif kind == "ActivitySpec":
            parent = obj.get("parent_task", {})
            if parent.get("status") == "known":
                value = parent.get("value", {})
                fields = ("parent_activity_ref", "parent_artifact", "blocker", "entry_basis_refs", "alternative_explanations", "local_sufficiency", "return_connection", "budget_ref")
                if not isinstance(value, dict) or any(field not in value for field in fields):
                    fail("PARENT_TASK", name)
                else:
                    resolve(value["parent_activity_ref"], "ActivitySpec")
                    if value["parent_activity_ref"].get("id") == name or not value["return_connection"] or value["budget_ref"] != obj.get("budget_ref"):
                        fail("PARENT_TASK", f"{name}: 父任务/返回/共同预算不相容")

        elif kind == "LearningNeed":
            disposition = obj.get("disposition", {})
            status = disposition.get("status")
            if status not in ("pending", "scheduled", "partially_scheduled", "merged", "deferred", "no_further_investment", "closed", "returned"):
                fail("NEED_DISPOSITION", name)
            if status != "pending" and (not disposition.get("reason") or not obj.get("uncovered_impact") or not obj.get("next_trigger")):
                fail("NEED_DISPOSITION", f"{name}: 未覆盖与触发缺失")
            if status in ("scheduled", "partially_scheduled"):
                refs = disposition.get("commitment_refs", [])
                if not refs or obj.get("acceptance", {}).get("status") not in ("accepted", "partially_accepted"):
                    fail("NEED_DISPOSITION", f"{name}: 安排未关联接责与承诺")
                for ref in refs:
                    plan = resolve(ref, "PlanCommitment")
                    if plan and plan.get("status") != "active":
                        fail("NEED_DISPOSITION", f"{name}: 承诺非有效")
            if status == "merged" and not disposition.get("requirement_mapping"):
                fail("NEED_DISPOSITION", f"{name}: 合并缺原要求映射")

        elif kind == "AuthorizationGrant":
            if obj.get("issuer") != obj.get("owner"):
                fail("AUTHORITY_ISSUER", name)
            if obj.get("binding_status") != "verified_for_fixture":
                fail("FIXTURE_BINDING", name)

        elif kind == "UseRestriction":
            if obj.get("status") == "lifted" and not obj.get("restoration_refs"):
                fail("RESTRICTION_RESTORE", name)

        elif kind == "WorkOrder":
            operation = obj.get("operation_id")
            if operation in operations and operations[operation] != name:
                fail("OPERATION_DUPLICATION", f"{operation}: {operations[operation]}, {name}")
            operations[operation] = name
            resolve(obj.get("shared_budget_ref"), "BudgetEnvelope")
            grants = [resolve(ref, "AuthorizationGrant") for ref in obj.get("authorization_refs", [])]
            scope_refs = obj.get("event_refs", []) + obj.get("material_refs", [])
            if not any(grant_covers(grant, obj.get("assignee"), obj.get("decision_type"), scope_refs, obj.get("goal_and_criteria_refs", [])) for grant in grants):
                fail("WORK_AUTHORITY", name)

    return errors


def mutate(data, mutation):
    changed = copy.deepcopy(data)
    target = next(obj for obj in changed["objects"] if obj["id"] == mutation["target"])
    if mutation["op"] == "clone":
        cloned = copy.deepcopy(target)
        cloned["id"] = mutation["new_id"]
        changed["objects"].append(cloned)
        return changed
    parent = target
    for key in mutation["path"][:-1]:
        parent = parent[key]
    key = mutation["path"][-1]
    if mutation["op"] == "set":
        parent[key] = mutation["value"]
    elif mutation["op"] == "delete":
        del parent[key]
    else:
        raise ValueError(f"未知夹具变更: {mutation['op']}")
    return changed


def check_sources():
    registry = read_json(ROOT / "resources/source-registry.json")
    results = []
    expected = {"N00"} | {f"D{i:02d}" for i in range(12)} | {f"R{i:02d}" for i in range(1, 7)}
    ids = [item["source_id"] for item in registry["sources"]]
    assert len(ids) == len(set(ids)) == registry["source_count"] == 19 and set(ids) == expected
    for item in registry["sources"]:
        path = (ROOT / item["project_relative_path"]).resolve()
        errors = []
        if not path.is_relative_to(ROOT.parent.resolve()) or not path.is_file():
            errors.append("路径不存在或超出项目")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"].lower():
            errors.append("指纹已变化，需要重新核对登记")
        if path.is_file():
            for loc in item["locators"]:
                if loc["kind"] == "markdown_heading":
                    lines = path.read_text(encoding="utf-8-sig").splitlines()
                    if not (1 <= loc["line"] <= len(lines)) or lines[loc["line"] - 1].strip() != loc["heading"].strip():
                        errors.append(f"章节定位失效: {loc.get('heading')}")
                elif loc["kind"] == "json_pointer":
                    value = read_json(path)
                    for token in loc["pointer"].strip("/").split("/"):
                        token = token.replace("~1", "/").replace("~0", "~")
                        value = value[int(token)] if isinstance(value, list) else value[token]
        results.append({"source_id": item["source_id"], "status": "pass" if not errors else "fail", "errors": errors})
    cards_path = (ROOT / next(s["project_relative_path"] for s in registry["sources"] if s["source_id"] == "R03")).resolve()
    cards = read_json(cards_path)
    operations = cards["operations"]
    assert len(operations) == 60 and len(cards["sources"]) == 46
    assert len({c["id"] for c in operations}) == 60
    assert {c["id"] for c in operations} == {f"{prefix}{i:02d}" for prefix in "OSRDIX" for i in range(1, 11)}
    assert {c["id"] for c in operations if not c["evidence_ids"]} == {"R09"}
    assert all(set(c) == {"id", "name", "category", "content_markdown", "template_status", "evidence_ids"} for c in operations)
    assert len({c["template_status"] for c in operations}) == 1
    markdown_path = (ROOT / next(s["project_relative_path"] for s in registry["sources"] if s["source_id"] == "R02")).resolve()
    markdown = markdown_path.read_text(encoding="utf-8-sig")
    for card in operations:
        assert re.search(rf"{re.escape(card['id'])}[^\n]*{re.escape(card['name'])}", markdown), card["id"]
        assert set(card["evidence_ids"]).issubset(cards["sources"]), card["id"]
    return results, {"encoding_cards": 60, "source_keys": 46, "empty_evidence_cards": ["R09"], "external_papers_reverified": False}


def check_specs(version):
    agents = sorted((ROOT / "src/agents").glob("*.md"))
    skills = sorted((ROOT / "specs/skills").glob("*.md"))
    assert len(agents) == 4 and len(skills) == 7
    for path in agents + skills:
        assert version in path.read_text(encoding="utf-8-sig"), path
    broken_links = []
    for path in ROOT.rglob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8-sig")):
            target = target.strip("<>").split("#")[0]
            if not target or "://" in target:
                continue
            if not (path.parent / target).resolve().is_file():
                broken_links.append(f"{path.relative_to(ROOT)}: {target}")
    assert not broken_links, broken_links
    deps = read_json(ROOT / "resources/runtime-dependencies.json")
    b3c_paths = {"strategy-index": "resources/strategies/strategy-index.json",
                  "encoding-card-bundle": "resources/strategies/encoding",
                  "post-method-note": "resources/strategies/post",
                  "method-config": "contracts/strategies-b3c.md"}
    for resource in deps["runtime_resources"]:
        assert resource["created_in_b0"] is False
        if resource["status"] == "pending_b3c":
            assert resource["path"] is None
        else:
            assert resource["status"] == "implemented_b3c_synthetic"
            assert resource["path"] == b3c_paths[resource["dependency_id"]]
            assert resource["resource_revision"] == "pl-strategies/0.1.0"
            assert (ROOT / resource["path"]).exists()
    # B0 记录保持历史结论；只放行已有批次的明确开发包，不当成安装。
    allowed_skills = {
        ROOT / "src/skills/personal-learning/SKILL.md",
        ROOT / "src/skills/learning-goals/SKILL.md",
        ROOT / "src/skills/learning-materials/SKILL.md",
        ROOT / "src/skills/learning-assessment/SKILL.md",
        ROOT / "src/skills/learning-teaching/SKILL.md",
        ROOT / "src/skills/learning-strategies/SKILL.md",
        ROOT / "src/skills/learning-planning/SKILL.md",
    }
    assert set(ROOT.rglob("SKILL.md")) <= allowed_skills, "只允许已明确创建的 B1—B4 七个开发包"
    return {"agent_specs": len(agents), "skill_specs": len(skills), "broken_local_links": len(broken_links),
            "runtime_resources_created": any(r["status"] == "implemented_b3c_synthetic" for r in deps["runtime_resources"]),
            "created_in_b0": False, "skills_installed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="可选，将真实静态检查输出写入 suite 内指定位置")
    args = parser.parse_args()
    definition = contract_definition()
    baseline = read_json(ROOT / "fixtures/synthetic-baseline.json")
    cases = read_json(ROOT / "fixtures/static-cases.json")
    assert cases["synthetic"] is True and cases["protocol_version"] == definition["protocol_version"]
    assert set(o["type"] for o in baseline["objects"]) == set(definition["objects"]), "正向快照需覆盖所有共用对象"
    base_errors = validate_snapshot(baseline, definition)
    static_results = [{"case_id": "B0-positive", "status": "pass" if not base_errors else "fail", "errors": base_errors}]
    for case in cases["cases"]:
        errors = validate_snapshot(mutate(baseline, case["mutation"]), definition)
        passed = case["expected_error"] in {error["code"] for error in errors}
        static_results.append({"case_id": case["case_id"], "name": case["name"], "expected_error": case["expected_error"], "status": "pass" if passed else "fail", "observed_errors": errors})
    sources, structure = check_sources()
    specs = check_specs(definition["protocol_version"])
    runtime = read_json(ROOT / "fixtures/runtime-scenarios.json")
    assert runtime["synthetic"] is True
    scenarios = runtime["scenarios"] + runtime["network_additions"]
    assert {s["case_id"] for s in runtime["scenarios"]} == {f"B10-{i:02d}" for i in range(1, 13)}
    assert all(s["runtime_status"] == "not_executed" for s in scenarios)
    passed = all(r["status"] == "pass" for r in sources + static_results)
    report = {
        "baseline": "B0", "client_date": "2026-10-02", "protocol_version": definition["protocol_version"],
        "validation_layer": "static_contract_and_source_integrity", "host": f"Python {sys.version.split()[0]} / {sys.platform}",
        "executor": "scripts/check_b0.py", "status": "pass" if passed else "fail", "source_checks": sources,
        "resource_structure": structure, "spec_checks": specs, "synthetic_objects": len(baseline["objects"]), "static_cases": static_results,
        "runtime_scenarios": [{"case_id": s["case_id"], "status": "not_executed"} for s in scenarios],
        "limitations": ["非运行记录服务，未验证真实身份/写隔离/原子保存/接管/删除/迟到拒绝", "字段检查并非完整嵌套 schema 或专业核验", "虚构数据不构成真实试用，不支持 V1—V4 通过或学习效果/组织净价值结论"]
    }
    if args.report:
        destination = (ROOT / args.report).resolve() if not args.report.is_absolute() else args.report.resolve()
        if not destination.is_relative_to(ROOT):
            parser.error("报告必须保存于本开发套件内")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "sources": len(sources), "synthetic_objects": len(baseline["objects"]), "static_cases_passed": sum(r["status"] == "pass" for r in static_results), "static_cases_total": len(static_results), "runtime_not_executed": len(scenarios), "spec_checks": specs, "failures": [r for r in sources + static_results if r["status"] == "fail"]}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
