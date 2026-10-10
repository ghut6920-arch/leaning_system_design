#!/usr/bin/env python3
"""Compile all Encoding cards and Post resources from unchanged local sources.

Only the standard library is used. --check compares a fresh deterministic build
without writing. File/body fingerprints detect drift; they prove neither domain
correctness nor teaching efficacy. No external reference is visited by this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = SUITE_ROOT.parent
DEFAULT_OUTPUT = SUITE_ROOT / "resources" / "strategies"
RESOURCE_REVISION = "pl-strategies/0.1.0"
SCHEMA_VERSION = "pl-strategy-resources/1"
COMPILED_IDS = tuple(prefix + f"{number:02d}" for prefix in "OSRDIX" for number in range(1, 11))
INPUT_IDS = ("N00", "D04", "D05", "D06", "D07", "R01", "R02", "R03", "R04", "R05", "R06")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_hash(text: str) -> str:
    return sha256(text.encode("utf-8"))


def json_bytes(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


class Sources:
    def __init__(self) -> None:
        self.registry_path = SUITE_ROOT / "resources" / "source-registry.json"
        self.registry_bytes = self.registry_path.read_bytes()
        self.registry = json.loads(self.registry_bytes.decode("utf-8-sig"))
        self.rows = {row["source_id"]: row for row in self.registry["sources"]}
        self.texts: dict[str, str] = {}
        self.fingerprints = []
        for source_id in INPUT_IDS:
            row = self.rows[source_id]
            path = (SUITE_ROOT / row["project_relative_path"]).resolve()
            raw = path.read_bytes()
            actual = sha256(raw)
            if actual != row["sha256"]:
                raise ValueError(f"Source drift against B0 registration: {source_id}")
            self.texts[source_id] = raw.decode("utf-8-sig").replace("\r\n", "\n")
            self.fingerprints.append({
                "source_id": source_id,
                "project_relative_path": row["project_relative_path"],
                "workspace_relative_path": path.relative_to(WORKSPACE_ROOT).as_posix(),
                "declared_revision": row["declared_version"],
                "sha256": actual,
                "registered_sha256": row["sha256"],
                "fingerprint_purpose": "检测本地通用来源变化；不证明内容、方法收益或外部文献已核验。",
            })

    def ref(self, source_id: str, locator: dict, identity_kind: str = "document_section") -> dict:
        row = self.rows[source_id]
        return {
            "source_id": source_id,
            "declared_revision": row["declared_version"],
            "project_relative_path": row["project_relative_path"],
            "workspace_relative_path": self.fingerprint(source_id)["workspace_relative_path"],
            "locator": locator,
            "identity_kind": identity_kind,
        }

    def fingerprint(self, source_id: str) -> dict:
        return next(row for row in self.fingerprints if row["source_id"] == source_id)

    def excerpt(self, source_id: str, heading: str, identity_kind: str = "document_section") -> dict:
        text = self.texts[source_id]
        lines = text.splitlines(keepends=True)
        starts = [i for i, line in enumerate(lines) if line.rstrip("\n") == heading]
        if len(starts) != 1:
            raise ValueError(f"Ambiguous/missing source heading: {source_id} {heading}")
        start = starts[0]
        level = len(heading) - len(heading.lstrip("#"))
        end = next((i for i in range(start + 1, len(lines))
                    if re.match(r"^#{1," + str(level) + r"} ", lines[i])), len(lines))
        markdown = "".join(lines[start:end])
        return {
            "source_ref": self.ref(source_id, {"kind": "markdown_heading", "heading": heading,
                                               "start_line": start + 1, "end_line": end}, identity_kind),
            "content_markdown": markdown,
            "body_sha256": text_hash(markdown),
            "body_normalization": "UTF-8；仅把CRLF统一为LF；保留原文及原链接。",
        }

    def table_row(self, source_id: str, evidence_id: str) -> dict:
        lines = self.texts[source_id].splitlines(keepends=True)
        hits = [(i, line) for i, line in enumerate(lines)
                if re.match(r"^\|\s*\[" + re.escape(evidence_id) + r"\]\(", line)]
        if len(hits) != 1:
            raise ValueError(f"Missing/ambiguous ledger row: {source_id} {evidence_id}")
        index, line = hits[0]
        return {"source_ref": self.ref(source_id, {"kind": "markdown_table_row", "evidence_id": evidence_id,
                                                   "line": index + 1}, "literature_entry"),
                "content_markdown": line, "body_sha256": text_hash(line)}

    def evidence_excerpt(self, evidence_id: str) -> dict:
        """R01 uses both ledger rows and whole evidence sections; retain either in full."""
        headings = re.findall(r"^### " + re.escape(evidence_id) + r"\b.*$", self.texts["R01"], re.M)
        if headings:
            if len(headings) != 1:
                raise ValueError(f"Ambiguous evidence section: {evidence_id}")
            return self.excerpt("R01", headings[0], "literature_entry")
        return self.table_row("R01", evidence_id)


def condition(key: str, explanation: str, *, independent: bool = False, exclusion: bool = False) -> dict:
    return {"key": key, "required_for": ["independent"] if independent else ["teaching", "independent"],
            "scope": "exclusion" if exclusion else "requirement", "explanation": explanation,
            "origin": "suite_added",
            "unknown_policy": "保持待核；未知不按满足/未触发处理。"}


def common_conditions() -> list[dict]:
    return [
        condition("goal_work_defined", "本次目标内工作、用途和允许资源可引用；不由选卡改写目标。"),
        condition("materials_reliable", "本次内容、题面和参考在拟定用途内有核验依据；研究引文不代替内容核验。"),
        condition("feedback_available", "能兑现必要的可靠纠正、反馈、修订与收束；成本包含这些工作。"),
        condition("learner_operation_preserved", "明确仍留给学习者的关键工作；模板槽已按当前内容实例化。"),
        condition("unaided_observation_preserved", "目标允许输入与真实暴露条件下，拟观察的关键操作未被提示或材料代做；不等于一律闭卷。", independent=True),
    ]


def base_resource(key: str, name: str, kind: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "resource_revision": RESOURCE_REVISION,
        "resource_key": key,
        "name": name,
        "resource_kind": kind,
        "compiled": True,
        "conditions": common_conditions(),
        "local_adaptations": ["结构化条件、标签与资源键为本套件新增整理；不视为经验证的调度算法。"],
        "review_status": {
            "status": "local_source_text_checked",
            "scope": "核对本地选中正文、完整必要约束、源定位与指纹；按正式方案处理冲突。",
            "external_references_verified": False,
            "course_applicability_verified": False,
            "learning_effect_verified": False,
            "personal_data_included": False,
        },
        "evidence_limits": [
            "研究组件、学科内容正确性、任务与帮助条件、真实学习收益分别核验。",
            "目标所需独立、整体、迁移与时间条件不由方法名称或卡片验收代替。",
            "未知接触保持未知；隐藏答案、更换措辞或执行者不能重置暴露历史。",
            "索引命中与本地资源正文核对不证明当前任务已可执行。",
        ],
        "help_and_feedback_constraints": [
            "记录可见输入、备用帮助与教师参考；备用内容未展示不计暴露。",
            "保存帮助前原答以及实际帮助内容、作用、顺序与相关发生时间。",
            "允许提供足以继续的可靠帮助；帮助后的成功按实际条件解释。",
            "用户请求示范或答案时可以转教学；不为维持独立证据拒绝必要帮助。",
        ],
        "stop_or_return_conditions": [
            "目标内当前工作已有充分证据时结束；不为展示策略制造额外活动。",
            "预算结束、用户暂停、无新增信息或参考争议时保存已做/未做与恢复点。",
            "局部可用即回同一父任务；保留父任务卡点、已有支持、局部够用条件、返回位置与预算。",
            "局部成功而父任务仍失败时重审接口、整体组织、额外前置或诊断；不无限下钻。",
            "目标只缺未来时间条件时收束，给同一目标内需求；不即时加题补未来证据。",
        ],
        "time_constraints": {
            "fixed_spacing_interval": None,
            "fixed_retrieval_first": False,
            "follows_goal_spec": True,
            "required_events": "按相关学习、练习、帮助/反馈与已知再接触事件解释；不编造时间。",
        },
        "cost": {"preparation": "unknown", "execution": "unknown", "feedback": "unknown",
                 "review": "unknown", "basis": "通用资源无具体课程和用时；实例化时引用实际预算/估计依据。"},
    }


def build_common_rules(sources: Sources) -> dict:
    text = sources.texts["R02"]
    first_category = text.index("## Orient / 定向")
    opening = text[:first_category]
    end_line = opening.count("\n")
    closing = sources.excerpt("R02", "## 添加例子与停止的规则")
    return {
        "schema_version": SCHEMA_VERSION, "resource_revision": RESOURCE_REVISION,
        "opening": {"source_ref": sources.ref("R02", {"kind": "markdown_line_range", "start_line": 1,
                                                       "end_line": end_line}),
                    "content_markdown": opening, "body_sha256": text_hash(opening)},
        "closing": closing,
        "governing_overrides": [
            "N00 第七节与D07/D04/D05/D06优先：原卡完整训练设想按实际借用部分使用。",
            "R01的两三项默认、诊断步骤及延迟建议不编译为固定流程；无错误模型也可可靠输入。",
            "R02的撤提示/新例/长期保持不自动成为新增课程目标；是否需要由GoalSpec决定。",
            "不按六类走完，不固定候选/卡数，不设置统一间隔、失败次数或神经机制状态。",
        ],
        "carrier_relationship": "R02/R03是同一卡库的两个载体，不计为两份独立证据。",
        "single_performance_rule": "S07与X02对同一材料、关键补全与可观察变化重合时，只执行一次任务、保存一份原答；分别注明借用部分。",
        "source_refs": [sources.excerpt("N00", "## 七、策略资源怎样从原文变成运行资源")["source_ref"],
                        sources.excerpt("D07", "## 六、从通用卡片到可执行任务")["source_ref"],
                        sources.excerpt("D05", "### 2. 从卡片到任务，需要完成内容实例化")["source_ref"]],
    }


def parse_cards(sources: Sources) -> tuple[dict, dict, list]:
    library = json.loads(sources.texts["R03"])
    operations = library["operations"]
    headings = re.findall(r"^### ([OSRDIX]\d{2}) (.+)$", sources.texts["R02"], re.M)
    if len(operations) != 60 or len(headings) != 60:
        raise ValueError("The registered library must have exactly 60 cards per carrier")
    if len({row["id"] for row in operations}) != 60:
        raise ValueError("Duplicate Encoding IDs")
    if [(op["id"], op["name"]) for op in operations] != headings:
        raise ValueError("Encoding ID/name/order carrier mismatch")
    counts = Counter(op["category"] for op in operations)
    if sorted(counts.values()) != [10] * 6:
        raise ValueError("Encoding category counts mismatch")
    if library["version"] != sources.rows["R03"]["declared_version"]:
        raise ValueError("R03 declared version changed")
    markdown = {card_id: sources.excerpt("R02", f"### {card_id} {name}", "card")
                for card_id, name in headings}
    categories = re.findall(r"^## (.+)$", sources.texts["R02"], re.M)[:6]
    for index, operation in enumerate(operations):
        if operation["category"] != categories[index // 10]:
            raise ValueError(f"Category carrier mismatch: {operation['id']}")
        if not operation["content_markdown"].strip() or not operation["template_status"].startswith("H"):
            raise ValueError(f"Empty body/missing H: {operation['id']}")
        cited = set(re.findall(r"\b(?:OS|DI|RR|F|U)\d{2}\b", markdown[operation["id"]]["content_markdown"]))
        if cited != set(operation["evidence_ids"]):
            raise ValueError(f"Evidence carrier mismatch: {operation['id']}")
        if any(key not in library["sources"] for key in operation["evidence_ids"]):
            raise ValueError(f"Evidence locator missing: {operation['id']}")
    selected_checks = []
    for card_id in COMPILED_IDS:
        operation = next(row for row in operations if row["id"] == card_id)
        body = markdown[card_id]["content_markdown"].split("\n", 1)[1].strip()
        without_links = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
        if normalize_citations(without_links) != normalize_citations(operation["content_markdown"].strip()):
            raise ValueError(f"Selected card body mismatch beyond link targets: {card_id}")
        selected_checks.append({"card_id": card_id,
                                "equal_after_removing_link_targets": without_links == operation["content_markdown"].strip(),
                                "equal_after_link_and_citation_normalization": True})
    if next(op for op in operations if op["id"] == "R09")["evidence_ids"] != []:
        raise ValueError("R09 evidence_ids must remain the original empty list")
    return library, markdown, selected_checks


def normalize_citations(text: str) -> str:
    """Only expand same-family citation shorthand, e.g. OS01/04 or DI01–03."""
    def expand(match):
        prefix, first, tail = match.groups()
        start = int(first)
        numbers = [start] + [int(x) for x in tail.split("/")[1:]] if tail.startswith("/") else list(range(start, int(tail[1:]) + 1))
        return "、".join(prefix + f"{x:02d}" for x in numbers)
    return re.sub(r"(?<![A-Z0-9])(OS|DI|RR|F|U)(\d{2})((?:/\d{2})+|[–—-]\d{2})", expand, text)


def compile_encoding(sources: Sources, library: dict, markdown: dict, common: dict) -> dict[str, dict]:
    outputs = {}
    specifications = {
        "S07": {
            "intended_work": "可靠范例后局部补全关键步骤，降低程序执行/步骤搜索负担。",
            "prerequisites": ["有可靠范例、必要上下文及其余正确步骤。", "可定位本次尚需承担的关键步骤与条件。"],
            "exclusions": ["不让新手重建一堆空白或全部推导。", "只靠相邻符号/文字猜中不能证明组件可自主调用。"],
            "required_learner_operations": ["补出选定关键步骤，说明其依据与应检查条件。", "目标需要组件独立性时，另在不保留相邻答案线索的合法变式观察同一组件。"],
            "conditions": [condition("example_context_available", "可靠范例及保留上下文/其余步骤当前可用。"),
                           condition("key_step_identified", "选中的关键步骤是当前目标内必要工作，未要求从零重建整体。")],
            "evidence": ("OS10", "OS12"),
            "difference": "S07主要处理步骤补全和搜索负担；理由链独立性借X02；重合只做一次。",
        },
        "X02": {
            "intended_work": "给定可靠标准推理及局部支架，补出理由链关键关系，按目标观察撤除相关线索后的解释。",
            "prerequisites": ["已有可学、可核验的标准推理。", "必要知识可通过合法先验或可靠允许输入获得；先验不足不是已确认能力标签。"],
            "exclusions": ["不要求从零发明整个知识体系。", "填词猜中与仍可见答案不能被解释为理由链独立形成。"],
            "required_learner_operations": ["在给定句干/节点中补出关键理由，说明条件。", "记录仍可见的规则、选项和答案；目标需要独立理由链时，撤去相关线索并在结构近例解释。"],
            "conditions": [condition("standard_reasoning_available", "本次有可靠标准推理，不把开放猜想写成核验参考。"),
                           condition("prerequisites_available", "理由关系所需前提当前可用或作为允许的可靠输入提供。"),
                           condition("visible_clues_recorded", "仍可见规则/选项/答案和实际撤除部分明确，按它们解释表现。")],
            "evidence": ("RR06",),
            "difference": "X02关注理由链重建与解释独立性；S07关注步骤执行/搜索；共享补全不能重复计证。",
        },
        "R09": {
            "intended_work": "按目标、范围与条件分解重要性标准，并给有依据的排名、条件序关系或待测信息。",
            "prerequisites": ["比较标准与范围明确。", "模型/数据与共同尺度须足够支持所声称排名；不足时只作条件判断。"],
            "exclusions": ["上游位置、必要性、最大边际收益与因果效应不能互相代替。", "不编造40/35/25%等贡献权重，不要求总有唯一主因。"],
            "required_learner_operations": ["明确选择效应量/必要性/干预收益/上游位置/瓶颈/本情境边际作用中的实际标准。", "固定比较范围与条件再比较；说明条件或指标变化如何改变排名，缺信息时保留待测。"],
            "conditions": [condition("comparison_standard_defined", "本次重要性的标准明确且不混淆多个标准。"),
                           condition("comparison_range_fixed", "比较范围、保持条件与共同尺度明确。"),
                           condition("comparison_basis_bounded", "有足够模型/数据支持所声称排名；否则明确限定条件序关系与待测信息。"),
                           condition("unsupported_numeric_weights", "本配置含无依据的贡献百分比或伪精确权重。", exclusion=True)],
            "evidence": (),
            "difference": "R09是设计推论，原evidence_ids为空；空引用不自动禁用，内容与用途仍须核验。",
        },
    }
    for card_id in COMPILED_IDS:
        op_index, operation = next((i, op) for i, op in enumerate(library["operations"]) if op["id"] == card_id)
        sections = card_sections(operation)
        spec = specifications.get(card_id) or {
            "intended_work": sections["purpose"],
            "prerequisites": [sections["purpose"], "按正文前置和当前目标核对可用对象；未知不补成已满足。"],
            "exclusions": [sections["risk"], sections["acceptance"]],
            "required_learner_operations": [sections["prompt"], sections["deepening"]],
            "conditions": [condition("card_scope_and_constraints_checked",
                "已把本卡目的/前置、风险、约束与实际任务核对，并说明保留的学习者操作和返回点；不是仅按卡名采用。")],
            "evidence": tuple(operation["evidence_ids"]),
            "difference": "按本卡实际认知工作与近邻方法区别取舍；分类不是必经阶段，深化建议按原目标需要借用。",
        }
        bundle = base_resource("encoding/" + card_id, operation["name"], "encoding-card-bundle")
        bundle.update({key: spec[key] for key in ("intended_work", "prerequisites", "exclusions", "required_learner_operations")})
        bundle["conditions"].extend(spec["conditions"])
        json_ref = sources.ref("R03", {"kind": "json_pointer", "pointer": f"/operations/{op_index}",
                                       "select_field": "id", "select_value": card_id}, "card")
        bundle.update({"original_id": card_id, "source_version": library["version"],
                       "category": operation["category"], "evidence_ids": operation["evidence_ids"],
                       "template_status": operation["template_status"],
                       "original_claim_status": {"template_status": operation["template_status"],
                                                 "status": "H：设计综合", "per_template_experimentally_verified": False},
                       "content_markdown": operation["content_markdown"],
                       "source_body_sections": sections,
                       "section_extraction": "从R03原正文按已存在标签提取，未新增研究主张；全文与两载体同时保留。",
                       "full_carriers": {"R02": markdown[card_id],
                                         "R03": {"source_ref": json_ref,
                                                  "content_markdown": operation["content_markdown"],
                                                  "body_sha256": text_hash(operation["content_markdown"])}},
                       "common_rules": common,
                       "nearby_method_difference": spec["difference"],
                       "evidence_refs": [{"evidence_id": evidence_id,
                                          "source_ref": sources.evidence_excerpt(evidence_id)["source_ref"],
                                          "original_url": library["sources"][evidence_id],
                                          "externally_reverified_in_b3c": False}
                                         for evidence_id in operation["evidence_ids"]],
                       "research_excerpts": [sources.evidence_excerpt(evidence_id) for evidence_id in operation["evidence_ids"]]})
        bundle["source_refs"] = [markdown[card_id]["source_ref"], json_ref,
                                 *common["source_refs"], *[x["source_ref"] for x in bundle["research_excerpts"]]]
        bundle["evidence_limits"].extend([
            "完整两载体正文保留；链接目标差异不构成第二份证据，未来实质冲突先限制相关用途。",
            "原文H针对教学设计与收益外推，不把可核验数学定义/合法推导降为猜测。",
            spec["difference"],
        ])
        outputs[f"encoding/{card_id}.json"] = bundle
    return outputs


def card_sections(operation: dict) -> dict[str, str]:
    """Extract existing pedagogical fields, failing rather than dropping a card's constraints."""
    aliases = {
        "purpose": ("目的与适用", "目的/条件"),
        "prompt": ("提示模板", "Prompt", "Prompt（学习前）"),
        "risk": ("风险与校正", "风险/校正", "风险"),
        "representation_change": ("目标表征变化与证据", "表征变化", "表征改变"),
        "deepening": ("深化任务（H）",),
        "acceptance": ("约束与验收",),
    }
    original = {}
    for line in operation["content_markdown"].splitlines():
        match = re.match(r"^-\s*(?:\*\*)?([^：:]+)[：:](?:\*\*)?\s*(.+)$", line)
        if not match:
            raise ValueError(f"Unrecognized card line: {operation['id']}")
        label, body = match.group(1).strip(" *"), match.group(2)
        if label in original:
            raise ValueError(f"Duplicate card field: {operation['id']} {label}")
        original[label] = body
    sections = {}
    for key, labels in aliases.items():
        hits = [original[label] for label in labels if label in original]
        if len(hits) != 1:
            raise ValueError(f"Missing/ambiguous card field: {operation['id']} {key}")
        sections[key] = hits[0]
    sections["examples"] = "\n".join(body for label, body in original.items() if label in {"好/坏问题", "好例", "坏例"})
    if not sections["examples"]:
        raise ValueError(f"Missing examples: {operation['id']}")
    return sections


def compile_post(sources: Sources) -> dict[str, dict]:
    specifications = [
        {
            "slug": "retrieve-relation", "name": "按目标恢复并形成关系",
            "intended_work": "恢复目标所需的前提、条件或关系，完成连接/推理；允许输入与原目标相容时可直接开卷加工。",
            "prerequisites": ["关系两端与必要原理当前可用，可来自记忆或允许的可靠材料。", "目标说明恢复本身是否必要，并有关系参考。"],
            "exclusions": ["两端未可用时不由一次讲不清关系认定结构丢失。", "单项事实恢复、流畅因果故事或更大图不等于整体关系成立。"],
            "required_learner_operations": ["完成目标关系连接、方向、条件与所需论证；允许可靠重建而非逐字复现原证明。", "必要帮助后回同一父工作，分别解释访问、局部推理与整体结果。"],
            "conditions": [condition("relation_endpoints_available", "需要连接的两端前提当前可用或通过允许的可靠输入补足。"),
                           condition("relationship_basis_reliable", "连接、方向、成立条件和整体参考有本次内容依据。"),
                           condition("access_and_relation_separated", "恢复前/后支持与关系推理范围分别解释，不倒算帮助前恢复成功。")],
            "d06": ["### 1. 恢复：确定恢复对象与合法入口", "### 2. 关系整合：同时处理连接、区分与整体组织", "### 3. 返回 Encoding 的最小范围"],
            "r05": ["### 5.3 更适合 relational / causal integration：恢复关系前提与约束", "### 7.3 Successful、partial、failed 与 erroneous retrieval", "### 13.1 最小但有区分力的测量组合"],
            "evidence": ["E18", "E35"],
            "limits": ["E35是基础物理具体任务的局部直接证据；E18保留前提检索损害传递推理的反例，不外推全部关系学习有害。"],
        },
        {
            "slug": "select-method", "name": "在实际线索条件下选择、拒用并执行",
            "intended_work": "目标需要时观察方法自主选择、角色映射与执行，接受有依据拒用或信息不足。",
            "prerequisites": ["候选方法与其适用条件可跟踪，任务没有非必要新增前置。", "若要支持更广自主选择，任务包含合格方法竞争情境。"],
            "exclusions": ["标题、题组、邻题、笔记、刚发生讲解和工具默认也可能代选。", "同题仅换数字不支持广泛远迁移；提示后执行不补记自主选择。"],
            "required_learner_operations": ["识别当前适用知识、说明接受/拒用/信息不足依据，完成角色映射及执行。", "必要时先保存未提示表现，再用最少支持缩小失败范围。"],
            "conditions": [condition("candidate_methods_available", "可竞争的方法和必要条件当前可用，陌生源域不直接当迁移缺口。"),
                           condition("selection_task_conditions_defined", "实际变化、保持条件、新前置与近期线索明确，观察范围相称。"),
                           condition("method_choice_preprovided", "题面/标题/题组/邻题/笔记/工具或已发生帮助已经提供拟观察的方法选择。", independent=True, exclusion=True)],
            "d06": ["### 3. 自主选用与迁移：把识别、映射和执行分别看清", "### 1. 检查应对应原目标声称的能力"],
            "r05": ["### 5.5 更可能促进 transfer：练习发现何时用，再练如何用", "### 9.4 两个值得保留的非正向结果", "### 13.1 最小但有区分力的测量组合"],
            "evidence": ["E11", "E12", "E13", "E15"],
            "limits": ["变式与检索贡献未完全分离；源知识选择、映射、执行分别支持，近迁移证据不保证广泛自发远迁移。", "E15中的aptitude不是当前领域先验知识，不据此固化个人身份标签。"],
        },
        {
            "slug": "conditional-update", "name": "保留合法旧域的条件化更新",
            "intended_work": "按可靠版本/条件依据修订目标内错误连接或选择，保留仍成立的旧规则与不确定性。",
            "prerequisites": ["更新原因可定位，新旧依据及合法域可核验。", "原系统参考争议先走内容纠错与历史重评；学习者可能原本正确。"],
            "exclusions": ["不把所有旧版本禁用，不自动取最新或补造版本条件。", "即时改答、旧答案暂不可访问或时间过去不证明旧痕迹擦除/再巩固。"],
            "required_learner_operations": ["说明哪条依据改变哪处关系/条件以及当前判断；同时处理仍有效旧情境。", "只有目标需要或旧错复发有依据时才提出相应跨时间/线索检查。"],
            "conditions": [condition("old_new_bases_reliable", "新旧事实/规则/版本与合法域均有可核验依据。"),
                           condition("valid_old_scope_preserved", "保留仍正确旧情境，未知版本不默认取最新。"),
                           condition("update_reason_identified", "更新原因来自可定位依据/版本/原答，不制造错误模型或凭目标扩大倒算旧错。"),
                           condition("reference_dispute_unresolved", "当前所依赖内容/参考存在未解除实质争议。", exclusion=True)],
            "d06": ["### 1. 先确定哪一类变化有依据", "### 2. 更新成功应能排除哪些假象", "### 4. 系统纠错与学习者更新分开完成", "### 4. Consolidation 与 Reconsolidation 的位置"],
            "r05": ["### 7.3 Successful、partial、failed 与 erroneous retrieval", "### 8.1 反馈信息与目标状态的对应", "### 10.3 Reconsolidation：须区分三个层级", "### 13.1 最小但有区分力的测量组合"],
            "evidence": ["E25", "E38", "E49"],
            "limits": ["E38为实验室关联更新，新旧内容可共存；不能直接证明概念模型整体重构或分子再巩固。", "E25非全部检索后反馈；E49限制教育中普遍可控再巩固归因，不否定生物机制存在。"],
        },
        {
            "slug": "retrieve-generate-order", "name": "按前提、可见输入与证据用途选择恢复/生成顺序",
            "intended_work": "比较恢复与生成/解释的条件化组合；第二项只承担尚未完成的必要工作，顺序保护实际证据用途。",
            "prerequisites": ["各项增加的目标内工作明确，必要前提/生成支架与可靠反馈可用。", "每阶段材料可见性、允许查阅、反馈/修订与预算可引用。"],
            "exclusions": ["不固定检索在先，不以未发现稳定差异声称所有顺序等效。", "任务次数相同不等于等时，组合超过单策略不等于超加成协同。"],
            "required_learner_operations": ["执行当前选定恢复/生成/解释中的实际关键工作，记录采用部分与顺序理由。", "无提示表现本身属于所需证据时，先保存它再展示会代做关键操作的前项信息。"],
            "conditions": [condition("combination_adds_necessary_work", "第二项增加未完成必要工作；已覆盖时合并或省略。"),
                           condition("sequence_visibility_defined", "前后项的材料可见、允许查阅、反馈与修订条件明确。"),
                           condition("prerequisites_available", "本次恢复/生成/解释所需前提可用或可靠允许支持已准备。"),
                           condition("preceding_step_leaks_required_operation", "前项已泄露后项拟独立观察的关键答案/规则/关系。", independent=True, exclusion=True)],
            "d06": ["### 3. 活动顺序由功能决定", "### 4. 反馈：修复目标需要的那一层"],
            "r05": ["### 9.1 先界定 synergy", "### 9.2 六种目标组合的证据地图", "### 9.3 顺序效应的最新证据需要改写默认流程", "### 9.4 两个值得保留的非正向结果", "### 9.5 哪些“生成在前”证据不能直接移植"],
            "evidence": ["E29", "E30", "E31", "E33", "E34"],
            "limits": ["E29只支持特定R→G配置；E30生成可开卷、有反馈修订且非等时；E31未发现稳定差异不证明普遍等效。", "E33保留概念图组合未增益的局部反例；E34的初始编码→检索与编码后RG/GR不是同一问题。"],
        },
    ]
    outputs = {}
    for spec in specifications:
        note = base_resource("post/" + spec["slug"], spec["name"], "post-method-note")
        for key in ("intended_work", "prerequisites", "exclusions", "required_learner_operations"):
            note[key] = spec[key]
        note["conditions"].extend(spec["conditions"])
        excerpts = [sources.excerpt("D06", heading) for heading in spec["d06"]]
        excerpts.extend(sources.excerpt("R05", heading) for heading in spec["r05"])
        excerpts.extend(sources.excerpt("R04", heading) for heading in ("## 从结果倒推操作", "## 六种组合如何判断", "## 三个使用边界"))
        excerpts.extend(sources.excerpt("D07", heading) for heading in ("## 五、组合、顺序与相互干扰", "## 六、从通用卡片到可执行任务"))
        excerpts.append(sources.excerpt("D06", "## 七、时间与证据：教学进展、当前可用和持久可用分别成立"))
        ledger = []
        for evidence_id in spec["evidence"]:
            heading = next(line for line in sources.texts["R06"].splitlines() if line.startswith("### " + evidence_id + "｜"))
            entry = sources.excerpt("R06", heading, "literature_entry")
            ledger.append({"evidence_id": evidence_id, **entry,
                           "historical_verification_only": True, "externally_reverified_in_b3c": False})
        note.update({"original_id": None, "identity_kind": "suite_added_method_key", "source_version": None,
                     "original_claim_status": {"status": "H：本套件条件化设计综合",
                                               "no_original_post_card_id": True,
                                               "research_claim_ratings_not_method_score": True},
                     "source_excerpts": excerpts, "evidence_refs": ledger,
                     "source_refs": [x["source_ref"] for x in [*excerpts, *ledger]],
                     "navigation_limits": {"matrix_is_task_matching": True, "matrix_is_effect_ranking": False,
                                           "operations_non_exclusive": True,
                                           "E01_E49_are_literature_ids": True,
                                           "D06_P1_P5_are_acceptance_ids": True},
                     "content_markdown": "\n\n".join([spec["intended_work"], *spec["required_learner_operations"], *spec["limits"]])})
        note["evidence_limits"].extend(spec["limits"])
        note["evidence_limits"].append("台账核查深度为原文历史声明；B3c只回查本地条目，未重新读或核验外部论文。")
        note["local_adaptations"].append("post/键为本套件新增方法说明；R06的E编号只作文献定位，D06的P1—P5只作验收定位。")
        outputs[f"post/{spec['slug']}.json"] = note
    return outputs


def body_fingerprints(value: object, path: str = "") -> list[dict]:
    result = []
    if isinstance(value, dict):
        for key, child in value.items():
            pointer = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key == "content_markdown" and isinstance(child, str):
                result.append({"json_pointer": pointer, "sha256": text_hash(child)})
            else:
                result.extend(body_fingerprints(child, pointer))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.extend(body_fingerprints(child, path + "/" + str(index)))
    return result


def build_files() -> dict[str, bytes]:
    sources = Sources()
    library, markdown, body_checks = parse_cards(sources)
    common = build_common_rules(sources)
    resources = {"common-constraints.json": common,
                 **compile_encoding(sources, library, markdown, common), **compile_post(sources)}
    entries = []
    for index, operation in enumerate(library["operations"]):
        card_id = operation["id"]
        compiled = card_id in COMPILED_IDS
        entries.append({"resource_key": "encoding/" + card_id, "original_id": card_id,
                        "identity_kind": "original_encoding_card_id", "name": operation["name"],
                        "category": operation["category"], "source_id": "R03", "source_version": library["version"],
                        "resource_revision": RESOURCE_REVISION, "compiled": compiled,
                        "bundle_path": f"encoding/{card_id}.json" if compiled else None,
                        "tags": [{"value": operation["category"], "origin": "original_field", "field": "category"},
                                 {"value": "encoding", "origin": "suite_added"},
                                 {"value": "checked_bundle" if compiled else "index_only", "origin": "suite_added"}],
                        "source_refs": [markdown[card_id]["source_ref"], sources.ref("R03", {"kind": "json_pointer",
                                         "pointer": f"/operations/{index}", "select_field": "id", "select_value": card_id}, "card")],
                        "evidence_ids": operation["evidence_ids"],
                        "original_claim_status": operation["template_status"],
                        "intended_work": resources[f"encoding/{card_id}.json"]["intended_work"],
                        "execution_limit": "完整包可直接读取；按当前理解目标实例化正文操作、前置、风险和反馈，不由compiled认定适配或学习效果。"})
    for path, resource in resources.items():
        if resource.get("resource_kind") != "post-method-note":
            continue
        entries.append({"resource_key": resource["resource_key"], "original_id": None,
                        "identity_kind": "suite_added_method_key", "name": resource["name"], "category": "Post",
                        "source_id": None, "source_version": None, "resource_revision": RESOURCE_REVISION,
                        "compiled": True, "bundle_path": path,
                        "tags": [{"value": "post", "origin": "suite_added"}],
                        "source_refs": resource["source_refs"],
                        "original_claim_status": resource["original_claim_status"],
                        "execution_limit": "套件新增条件说明，非原始P卡；当前内容/用途/帮助条件须另核对。"})
    resources["strategy-index.json"] = {
        "schema_version": SCHEMA_VERSION, "resource_revision": RESOURCE_REVISION,
        "source_version": library["version"], "encoding_card_count": 60,
        "compiled_encoding_card_count": len(COMPILED_IDS), "post_method_note_count": 4,
        "index_is_execution_config": False, "entries": entries,
        "selection_limits": ["分类只是导航，不是教学阶段、能力等级或自动评分。",
                             "不固定候选数量，不按证据数量、篇幅或家族评级算策略效用。",
                             "已有合法有效配置可复用；库中无合适卡时沿D07可靠直接教学路径。"],
    }
    files = {path: json_bytes(value) for path, value in resources.items()}
    manifest = {
        "schema_version": SCHEMA_VERSION, "resource_revision": RESOURCE_REVISION,
        "registry": {"path": "resources/source-registry.json", "sha256": sha256(sources.registry_bytes),
                     "modified": False},
        "builder": {"path": "scripts/build_b3c_resources.py", "sha256": sha256(Path(__file__).read_bytes()),
                    "standard_library_only": True, "deterministic_no_wallclock_fields": True},
        "source_path_base": "personal-learning-suite/ (project_relative_path); workspace root (workspace_relative_path)",
        "source_fingerprints": sources.fingerprints,
        "resources": [{"path": path, "sha256": sha256(files[path]),
                       "resource_key": value.get("resource_key"),
                       "resource_revision": RESOURCE_REVISION,
                       "body_fingerprints": body_fingerprints(value)} for path, value in sorted(resources.items())],
        "integrity_checks": {
            "registered_source_hashes_match": True, "encoding_card_count": 60,
            "all_id_name_category_order_matches": True, "all_evidence_id_sets_match": True,
            "all_card_bodies_nonempty": True, "all_template_status_H": True,
            "compiled_card_ids": list(COMPILED_IDS), "selected_body_checks": body_checks,
            "R09_evidence_ids_original_empty": True,
            "R02_opening_and_closing_in_all_encoding_bundles": True,
            "index_coverage_is_not_compilation_or_validation": True,
            "body_fingerprints_normalization": "UTF-8字符串；源Markdown只统一CRLF为LF。",
        },
        "legacy_link_mappings": [{"source_id": item["source_id"], "line": item["line"],
                                  "original_target": item["original_target"],
                                  "current_source_id": item["proposed_local_source_id"],
                                  "current_workspace_relative_path": sources.fingerprint(item["proposed_local_source_id"])["workspace_relative_path"],
                                  "resolution_status": "mapped_to_registered_current_local_source",
                                  "original_modified": False, "external_verification": False}
                                 for item in sources.registry["legacy_local_links"]],
        "verification_limits": {"external_references_verified": False, "actual_course_trial": False,
                                "learning_effect_verified": False, "personal_data_included": False},
    }
    files["manifest.json"] = json_bytes(manifest)
    files["README.md"] = ("# B3c 通用策略资源\n\n"
        f"运行资源修订 `{RESOURCE_REVISION}`，来源 Encoding 库 v2.0。60张Encoding卡全部编译为完整两载体卡包；"
        "另有4份携带完整来源段落的Post条件包。全部64个资源键可直接读取。\n\n"
        "先从理解目标与认知工作定位strategy-index.json，再读取选中完整包及conditions；无须一次加载全库。compiled不代表当前课程准入。"
        "conditions 为套件新增检查项，未知不按满足处理；exclusion 项已知 false 才表示未触发。"
        "教学可提供目标允许帮助；独立证据另核对未被代做的关键操作。\n\n"
        "Encoding 包携带 R02 文首与文末规则、D07/D05/N00 覆盖规则、R01 相关完整证据条目。"
        "S07/X02 共享补全只是一份实际表现；R09 保留空证据及 H 性质。Post 的有意义键为套件新增，"
        "E01—E49 为文献编号、D06 的 P1—P5 为验收编号。\n\n"
        "原文件和来源登记不修改。legacy_link_mappings 将旧 outputs 定位映射到当前登记本地来源；"
        "完整原文摘录保留原链接，运行按 source_id/locator 及当前映射解析，不依赖另一台机器上的旧绝对路径。\n\n"
        "`python scripts/build_b3c_resources.py` 可复现生成；追加 `--check` 只读比较当前产物、原文及登记指纹。"
        "manifest.json 含文件与正文指纹。指纹检查与本地正文核对只检测漂移；本轮未外网核论文、未真实教学、"
        "未验证方法效果。资源无个人记录，个人配置只进入独立学习工作区。\n").encode("utf-8")
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare reproducible resources without writing")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="resource output directory")
    args = parser.parse_args()
    try:
        files = build_files()
        differences = []
        for relative, content in sorted(files.items()):
            path = args.output / relative
            if args.check:
                if not path.is_file() or path.read_bytes() != content:
                    differences.append(relative)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        if differences:
            print(json.dumps({"passed": False, "differences": differences}, ensure_ascii=False))
            return 1
        print(json.dumps({"passed": True, "mode": "check" if args.check else "build",
                          "resource_revision": RESOURCE_REVISION, "files": len(files),
                          "encoding_index": 60, "compiled_encoding": list(COMPILED_IDS), "post_notes": 4,
                          "external_references_verified": False}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, StopIteration) as error:
        print(json.dumps({"passed": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
