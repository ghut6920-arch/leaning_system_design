"""Lossless source-bound runtime contracts. Mixed passages stay mandatory."""
from copy import deepcopy
import hashlib
import json
import re

LAYER_REVISION = "pl-strategy-runtime/0.1.0"
LAYER_SCHEMA = "pl-strategy-runtime/1"
SPECIAL = {"content_markdown", "source_refs", "full_carriers", "common_rules", "source_body_sections",
           "research_excerpts", "evidence_refs", "source_excerpts"}
DIRECT = {"category", "compiled", "conditions", "cost", "evidence_ids", "evidence_limits", "exclusions",
          "help_and_feedback_constraints", "identity_kind", "intended_work", "local_adaptations", "name",
          "navigation_limits", "nearby_method_difference", "original_claim_status", "original_id", "prerequisites",
          "required_learner_operations", "resource_key", "resource_kind", "resource_revision", "review_status",
          "schema_version", "section_extraction", "source_version", "stop_or_return_conditions", "template_status", "time_constraints"}
REQUIRED = {"resource_key", "resource_kind", "conditions", "intended_work", "prerequisites", "exclusions",
            "required_learner_operations", "help_and_feedback_constraints", "stop_or_return_conditions",
            "evidence_limits", "original_claim_status", "review_status", "time_constraints", "content_markdown"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def normalized_citations(text):
    def expand(match):
        prefix, first, tail = match.groups()
        start = int(first)
        numbers = ([start] + [int(x) for x in tail.split("/")[1:]] if tail.startswith("/")
                   else list(range(start, int(tail[1:]) + 1)))
        return "、".join(prefix + f"{x:02d}" for x in numbers)
    return re.sub(r"(?<![A-Z0-9])(OS|DI|RR|F|U)(\d{2})((?:/\d{2})+|[–—-]\d{2})", expand, text)


def checked_part(part):
    allowed = {"source_ref", "content_markdown", "body_sha256", "body_normalization"}
    if set(part) - allowed or not isinstance(part.get("content_markdown"), str):
        raise ValueError("unknown_or_missing_source_part_field")
    text = part["content_markdown"]
    if digest(text.encode()) != part.get("body_sha256"):
        raise ValueError("source_part_body_changed")
    return text


def compile_contract(resource, *, bundle_path, bundle_sha256, source_texts=None):
    if set(resource) - (DIRECT | SPECIAL):
        raise ValueError("unknown_strategy_field:" + ",".join(sorted(set(resource) - (DIRECT | SPECIAL))))
    if not REQUIRED <= resource.keys() or not resource["conditions"] or resource.get("compiled") is not True:
        raise ValueError("incomplete_runtime_obligations")
    mandatory = {key: deepcopy(value) for key, value in resource.items() if key in DIRECT}
    coverage = {"/" + key: "mandatory" if key in DIRECT else "provenance" for key in resource}
    research = []
    source_spans = []
    kind = resource["resource_kind"]
    if kind == "encoding-card-bundle":
        carriers = resource["full_carriers"]
        if set(carriers) != {"R02", "R03"}:
            raise ValueError("unknown_or_missing_carrier")
        r02, r03 = checked_part(carriers["R02"]), checked_part(carriers["R03"])
        without_links = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", r02.split("\n", 1)[1].strip())
        if normalized_citations(without_links) != normalized_citations(r03.strip()):
            raise ValueError("carrier_substantive_conflict")
        if resource["content_markdown"] != r03:
            raise ValueError("canonical_card_body_conflict")
        if any(not isinstance(v, str) for v in resource["source_body_sections"].values()):
            raise ValueError("untyped_card_section")
        additional = {k: v for k, v in resource["source_body_sections"].items() if v.strip() not in r03}
        if additional:
            mandatory["additional_card_sections"] = deepcopy(additional)
        mandatory["canonical_card_body"] = r03
        common = deepcopy(resource["common_rules"])
        opening, closing = checked_part(common["opening"]), checked_part(common["closing"])
        common.pop("source_refs")
        common["opening"], common["closing"] = opening, closing
        mandatory["common_rules"] = common
        coverage.update({"/content_markdown": "equivalent_to_full_R03", "/full_carriers": "checked_equivalent_carriers",
                         "/common_rules": "mandatory_except_provenance", "/source_body_sections": "full_R03_plus_preserved_additional_sections"})
        if len(resource["research_excerpts"]) != len(resource["evidence_refs"]):
            raise ValueError("evidence_excerpt_mapping_missing")
        evidence = []
        for i, (excerpt, reference) in enumerate(zip(resource["research_excerpts"], resource["evidence_refs"])):
            text = checked_part(excerpt)
            if set(reference) - {"evidence_id", "source_ref", "original_url", "externally_reverified_in_b3c"}:
                raise ValueError("unknown_evidence_field")
            # Preserve the complete grade, population, outcome and limits cells.
            # Only the ID/link and bibliographic title cells become on-demand.
            cells = re.split(r"(?<!\\)\|", text)
            if len(cells) == 1:
                prefix, suffix, retained = "", text, [{"role": "完整混合研究段", "value": text}]
            elif len(cells) in (6, 7) and not cells[0] and not cells[-1].strip():
                source_ref = excerpt["source_ref"]
                if source_texts is None or source_ref["source_id"] not in source_texts:
                    raise ValueError("source_table_header_required")
                lines = source_texts[source_ref["source_id"]].splitlines()
                line = source_ref["locator"]["line"] - 1
                if lines[line].strip() != text.strip():
                    raise ValueError("evidence_source_line_changed")
                separator = next((i for i in range(line - 1, -1, -1) if re.match(r"^\s*\|\s*:?-", lines[i])), None)
                if separator is None:
                    raise ValueError("source_table_header_required")
                if any(not line_text.lstrip().startswith("|") for line_text in lines[separator + 1:line] if line_text.strip()):
                    raise ValueError("ambiguous_source_table_context")
                header = re.split(r"(?<!\\)\|", lines[separator - 1])
                if len(header) != len(cells) or len(set(h.strip() for h in header[3:-1])) != len(header[3:-1]):
                    raise ValueError("ambiguous_evidence_columns")
                prefix, suffix = "|".join(cells[:3]) + "|", "|".join(cells[3:])
                retained = [{"role": h.strip(), "value": v} for h, v in zip(header[3:-1], cells[3:-1])]
            else:
                raise ValueError("unrecognized_evidence_table_layout")
            assert prefix + suffix == text
            evidence.append({"evidence_id": reference["evidence_id"],
                             "externally_reverified_in_b3c": reference["externally_reverified_in_b3c"],
                             "grade_population_outcome_limits": retained})
            pointer = f"/research_excerpts/{i}"
            source_spans.append({"pointer": pointer + "/content_markdown", "mandatory_start": len(prefix), "end": len(text)})
            research.append({"section": pointer, "evidence_id": reference["evidence_id"], "body_sha256": digest(text.encode())})
        mandatory["evidence_boundaries"] = evidence
        coverage["/research_excerpts"] = "all_nonbibliographic_cells_mandatory"
        coverage["/evidence_refs"] = "evidence_identity_and_verification_mandatory_locator_on_demand"
    elif kind == "post-method-note":
        known = {resource["intended_work"], *resource["required_learner_operations"], *resource["evidence_limits"]}
        if any(paragraph not in known for paragraph in resource["content_markdown"].split("\n\n")):
            raise ValueError("post_summary_contains_unmapped_obligation")
        passages = []
        for i, excerpt in enumerate(resource["source_excerpts"]):
            text = checked_part(excerpt)
            passages.append({"source_id": excerpt["source_ref"]["source_id"],
                             "heading": excerpt["source_ref"]["locator"]["heading"], "text": text})
        mandatory["source_passages"] = passages
        evidence = []
        for i, item in enumerate(resource["evidence_refs"]):
            if set(item) - {"evidence_id", "source_ref", "content_markdown", "body_sha256", "body_normalization",
                           "historical_verification_only", "externally_reverified_in_b3c"}:
                raise ValueError("unknown_evidence_field")
            part = {k: item[k] for k in ("source_ref", "content_markdown", "body_sha256", "body_normalization")}
            text = checked_part(part)
            paragraphs = text.split("\n\n")
            if len(paragraphs) < 3 or not paragraphs[0].startswith("### " + item["evidence_id"] + "｜") or not paragraphs[1].startswith("*"):
                raise ValueError("unrecognized_literature_layout")
            # Any suspicious mixed bibliographic paragraph stays mandatory.
            citation_mixed = bool(re.search(r"不能|不支持|不证明|风险|边界|因果|限制", paragraphs[1]))
            start = len(paragraphs[0]) + 2 if citation_mixed else len("\n\n".join(paragraphs[:2])) + 2
            evidence.append({"evidence_id": item["evidence_id"], "historical_verification_only": item["historical_verification_only"],
                             "externally_reverified_in_b3c": item["externally_reverified_in_b3c"], "study_and_limits": text[start:]})
            source_spans.append({"pointer": f"/evidence_refs/{i}/content_markdown", "mandatory_start": start, "end": len(text)})
            research.append({"section": f"/evidence_refs/{i}", "evidence_id": item["evidence_id"], "body_sha256": digest(text.encode())})
        mandatory["evidence_boundaries"] = evidence
        coverage["/source_excerpts"] = "full_mixed_and_operational_passages_mandatory"
        coverage["/evidence_refs"] = "full_study_scope_grade_and_limits_mandatory_bibliography_on_demand"
        coverage["/content_markdown"] = "exactly_covered_by_direct_fields"
    else:
        raise ValueError("unsupported_runtime_resource_kind")
    return {"schema_version": LAYER_SCHEMA, "layer_revision": LAYER_REVISION, "resource_key": resource["resource_key"],
            "archive_binding": {"path": bundle_path, "sha256": bundle_sha256}, "mandatory": mandatory,
            "research_on_demand": research, "field_disposition": coverage, "evidence_spans": source_spans,
            "expansion_rule": "引用研究效应/样本/时间作具体决策、来源争议、跨域外推或需要论证比较时，先展开相关原研究条目及必要原始依据；指纹和本地台账不证明外部论文已核。"}


def pointer_value(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("explicit_research_section_required")
    for part in pointer[1:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9]\d*", key):
                raise ValueError("invalid_research_index")
            value = value[int(key)]
        else:
            value = value[key]
    return value
