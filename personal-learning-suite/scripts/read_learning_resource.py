"""Bounded local reading of complete strategies, text and framework fingerprints."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator.reading import DEFAULT_TEXT_CHARS, text_page
from coordinator.delivery import DEFAULT_RETURN_BYTES, bounded_output
from coordinator.workspace import GateError
from runtime.learning_strategies import StrategyCatalog
from runtime.strategy_layers import pointer_value


def digest(data):
    return hashlib.sha256(data).hexdigest()


def outline_view(path, *, start=0, limit=12, expected=None):
    """Literal ATX headings and exact text ranges; no current-state inference."""
    if type(start) is not int or start < 0 or type(limit) is not int or not 1 <= limit <= 24:
        raise GateError("invalid_heading_window")
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    if any(ord(c) < 32 and c not in "\t\r\n" for c in text):
        raise GateError("text_file_required")
    fingerprint = digest(text.encode("utf-8"))
    if expected is not None and expected != fingerprint:
        raise GateError("read_version_changed")
    headings, position, fence = [], 0, None
    for line_number, line in enumerate(text.splitlines(keepends=True), 1):
        candidate = line.rstrip("\r\n")
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", candidate)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not marker[2].strip():
                fence = None
        elif marker:
            fence = (marker[1][0], len(marker[1]))
        else:
            match = re.match(r"^ {0,3}(#{1,6})[ \t]+(.+)$", candidate)
            if match:
                headings.append({"index": len(headings), "heading": candidate,
                                 "level": len(match[1]), "start": position, "start_line": line_number})
        position += len(line)
    if fence:
        raise GateError("unclosed_markdown_fence_use_text")
    if start > len(headings):
        raise GateError("invalid_heading_window")
    for index, row in enumerate(headings):
        boundary = next((other for other in headings[index + 1:] if other["level"] <= row["level"]), None)
        row["end"] = boundary["start"] if boundary else len(text)
        row["end_line"] = boundary["start_line"] - 1 if boundary else len(text.splitlines())
    return {"status": "ok", "view": "outline", "source": {"path": str(path.resolve()), "sha256": digest(raw),
            "view_sha256": fingerprint, "text_characters": len(text)}, "headings": headings[start:start + limit],
            "heading_total": len(headings), "next_heading_start": start + limit if start + limit < len(headings) else None,
            "preface_end": headings[0]["start"] if headings else len(text),
            "meaning": "仅ATX标题目录，未读正文、不推断有效状态；取完整所需段用text/offset=start/max-chars=end-start及expect-view-sha256。"}


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def strategy_payload(paths):
    """Retain every JSON field; exact long strings share one displayed body."""
    bodies, files, body_ids = {}, [], {}

    def replace(value):
        if isinstance(value, dict):
            if "$full_text" in value:
                raise ValueError("reserved_strategy_view_field")
            return {key: replace(item) for key, item in value.items()}
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, str) and len(value) >= 200:
            fingerprint = digest(value.encode("utf-8"))
            key = body_ids.setdefault(fingerprint, "T" + str(len(body_ids) + 1))
            bodies.setdefault(key, value)
            return {"$full_text": key}
        return value

    for path in paths:
        data = path.read_bytes()
        source = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_keys)
        if not isinstance(source, dict) or "content_markdown" not in source:
            raise ValueError("complete_strategy_object_required")
        files.append({"path": str(path.resolve()), "sha256": digest(data), "fields": replace(source)})
    return files, bodies


def strategy_document(paths):
    files, bodies = strategy_payload(paths)
    headings = ["# 完整策略阅读视图", "全部字段保留；$full_text指向下方完整正文，同一正文只显示一次。",
                "本视图不是摘要；输出覆盖不证明模型已读，也不代替原JSON版本依据。",
                json.dumps({"files": files}, ensure_ascii=False, separators=(",", ":"))]
    headings.extend("## 完整正文 " + key + "\n" + value for key, value in bodies.items())
    return "\n\n".join(headings), [{"path": f["path"], "sha256": f["sha256"]} for f in files]


def layer_payload(paths, *, research_sections=None):
    documents, sources = [], []
    for path in paths:
        path = path.resolve()
        root = next((p for p in path.parents if (p / "strategy-index.json").is_file() and (p / "manifest.json").is_file()), None)
        if root is None:
            raise ValueError("registered_strategy_root_required")
        catalog = StrategyCatalog(root)
        index = catalog.index()
        if index["status"] != "ok":
            raise ValueError("strategy_source_integrity_unavailable")
        relative = path.relative_to(root).as_posix()
        entry = next((e for e in index["entries"] if relative in (e["bundle_path"], e.get("runtime_path"))), None)
        if entry is None:
            raise ValueError("registered_strategy_path_required")
        loaded = catalog.load_runtime(entry["resource_key"])
        if loaded["status"] != "ok":
            raise ValueError("runtime_contract_integrity_unavailable")
        contract = loaded["runtime"]
        sources.extend([{"path": loaded["archive_path"], "sha256": contract["archive_binding"]["sha256"]},
                        {"path": loaded["runtime_path"], "sha256": digest(Path(loaded["runtime_path"]).read_bytes())}])
        if research_sections is None:
            documents.append({"resource_key": entry["resource_key"], "mandatory": contract["mandatory"],
                              "research_sections": contract["research_on_demand"], "expansion_rule": contract["expansion_rule"]})
        else:
            original = catalog.load(entry["resource_key"])["resource"]
            for section in research_sections:
                if not isinstance(section, str) or not section.startswith("/") or section.split("/")[1] not in {"research_excerpts", "evidence_refs", "source_excerpts", "full_carriers", "common_rules", "source_refs"}:
                    raise ValueError("source_section_required")
                documents.append({"resource_key": entry["resource_key"], "section": section, "original_value": pointer_value(original, section)})
    return documents, sources


def shared_layer_payload(documents):
    counts, values = {}, {}
    def key(value):
        return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
    def scan(value):
        if isinstance(value, dict) and "$shared" in value:
            raise ValueError("reserved_runtime_display_field")
        if isinstance(value, (str, list, dict)):
            token = key(value)
            counts[token] = counts.get(token, 0) + 1
            values[token] = value
        if isinstance(value, dict):
            for child in value.values(): scan(child)
        elif isinstance(value, list):
            for child in value: scan(child)
    for document in documents: scan(document)
    blocks, ids = {}, {}
    def replace(value, *, children=False):
        if isinstance(value, (str, list, dict)) and not children:
            token = key(value)
            size = len(json.dumps(value, ensure_ascii=False))
            if (isinstance(value, str) and len(value) >= 200) or (counts[token] > 1 and size >= 160):
                if token not in ids:
                    ident = "V" + str(len(ids) + 1)
                    ids[token] = ident
                    blocks[ident] = {"type": "text" if isinstance(value, str) else "json", "value": replace(value, children=True)}
                return {"$shared": ids[token]}
        if isinstance(value, dict): return {k: replace(v) for k, v in value.items()}
        if isinstance(value, list): return [replace(v) for v in value]
        return value
    mapped = [replace(d) for d in documents]
    return mapped, blocks


def layer_document(paths, *, research_sections=None):
    documents, sources = layer_payload(paths, research_sections=research_sections)
    mapped, blocks = shared_layer_payload(documents)
    title = "# 完整运行契约阅读视图" if research_sections is None else "# 按需原研究/来源阅读视图"
    parts = [title, "mandatory字段及其共享块均为必读正文；$shared指向完整原值，共用一次，不是摘要。研究展开保持原条目。",
             json.dumps({"documents": mapped, "sources": sources}, ensure_ascii=False, separators=(",", ":"))]
    for ident, block in blocks.items():
        body = block["value"] if block["type"] == "text" else json.dumps(block["value"], ensure_ascii=False, separators=(",", ":"))
        parts.append("## 完整共享值 " + ident + " (" + block["type"] + ")\n" + body)
    return "\n\n".join(parts), sources


def manifest_view(path, *, selected=None, changes_only=False):
    raw = path.read_bytes()
    manifest = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_keys)
    wanted = set(selected or [])
    entries, problems = [], []
    found = set()
    for item in manifest["entries"]:
        name = item["path"]
        if not isinstance(name, str) or not name or not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValueError("invalid_manifest_entry")
        if name in found:
            raise ValueError("duplicate_manifest_path")
        found.add(name)
        target = (path.parent / name).resolve()
        actual = digest(target.read_bytes()) if target.is_file() else None
        matches = actual == item["sha256"]
        if not matches:
            problems.append({"path": name, "problem": "missing" if actual is None else "fingerprint_changed"})
        if (not wanted or name in wanted) and (not changes_only or not matches):
            entries.append({"path": name, "expected_sha256": item["sha256"], "actual_sha256": actual, "matches": matches})
    absent = sorted(wanted - found)
    problems.extend({"path": name, "problem": "not_in_manifest"} for name in absent)
    return {"status": "ok" if not problems else "rejected", "manifest_sha256": digest(raw),
            "checked_entries": len(found), "problems": problems, "entries": entries,
            "meaning": "校验覆盖全部清单；筛选只改变显示，不缩小校验，不证明专业内容正确。"}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", newline="")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, action="append", required=True)
    parser.add_argument("--view", choices=["text", "outline", "strategy", "strategy-runtime", "strategy-research", "manifest"], default="text")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="默认直接呈现正文；机器读取可选JSON")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_TEXT_CHARS)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--expect-view-sha256", help="绑定前次视图指纹；任一原件变化即拒绝续读")
    parser.add_argument("--entry", action="append", help="manifest显示的确切条目路径，可重复")
    parser.add_argument("--section", action="append", help="研究/来源视图的确切JSON指针；可重复，不自动展开全文")
    parser.add_argument("--changes-only", action="store_true", help="manifest仅显示变化，仍检查全部条目")
    parser.add_argument("--heading-start", type=int, default=0, help="outline标题目录的起始编号")
    parser.add_argument("--heading-limit", type=int, default=12, help="outline标题目录数量，最多24")
    parser.add_argument("--max-return-bytes", type=int, default=DEFAULT_RETURN_BYTES, help="含元数据和结束标记的总UTF-8返回预算")
    args = parser.parse_args(argv)
    try:
        if args.max_chars < 1:
            raise GateError("invalid_read_limit")
        if args.section and args.view != "strategy-research":
            raise ValueError("research_view_required_for_sections")
        if args.view == "outline":
            if len(args.file) != 1 or args.full or args.offset:
                raise GateError("one_outline_file_without_body_required")
            result = outline_view(args.file[0], start=args.heading_start, limit=args.heading_limit, expected=args.expect_view_sha256)
        elif args.view == "manifest":
            if len(args.file) != 1:
                raise ValueError("one_manifest_required")
            result = manifest_view(args.file[0], selected=args.entry, changes_only=args.changes_only or not args.entry)
        else:
            if args.view == "strategy":
                text, sources = strategy_document(args.file)
            elif args.view == "strategy-runtime":
                text, sources = layer_document(args.file)
            elif args.view == "strategy-research":
                if len(args.file) != 1 or not args.section:
                    raise ValueError("one_archive_and_explicit_sections_required")
                text, sources = layer_document(args.file, research_sections=args.section)
            else:
                if len(args.file) != 1:
                    raise ValueError("one_text_file_required")
                raw = args.file[0].read_bytes()
                text = raw.decode("utf-8-sig")
                if any(ord(char) < 32 and char not in "\t\r\n" for char in text):
                    raise ValueError("text_file_required")
                sources = [{"path": str(args.file[0].resolve()), "sha256": digest(raw)}]
            page = text_page(text, offset=args.offset, max_chars=None if args.full else args.max_chars)
            if args.expect_view_sha256 and page["coverage"]["view_sha256"] != args.expect_view_sha256:
                raise GateError("read_version_changed")
            result = {"status": "ok", "view": args.view, "sources": sources, **page,
                      "meaning": "覆盖区间仅指本次返回；全文已读需实际取得并核全区间。"}
    except (OSError, UnicodeError, ValueError, KeyError, IndexError, TypeError, GateError) as error:
        result = {"status": "rejected", "problem": getattr(error, "code", str(error) if isinstance(error, ValueError) else type(error).__name__)}
    try:
        output = bounded_output(result, budget=args.max_return_bytes,
                                plain_text=result["status"] == "ok" and "text" in result and args.format == "text")
    except GateError as error:
        result = {"status": "rejected", "problem": error.code,
                  "next_action": "缩小条目/文件批次或明确增加总返回预算；不得把缺失尾标记当完整阅读。"}
        output = bounded_output(result)
    print(output, end="")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
