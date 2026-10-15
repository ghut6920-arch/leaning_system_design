"""Read-only historical replay, with explicit adapters for narrative evidence.

The input case is a traceable projection, not an independent professional verdict.
Only an explicitly selected review table establishes original review bindings.
Candidate inventories and archived active flags never establish review coverage.
"""
from __future__ import annotations

import hashlib
import json
from contextlib import closing
from pathlib import Path, PurePosixPath
import re
import sqlite3
from typing import Any

VERSION = "tac-replay/0.1.0"


class ReplayError(ValueError):
    """Unavailable, ambiguous, changed or unsupported historical evidence."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative_path(value: str) -> str:
    if not isinstance(value, str):
        raise ReplayError("path must be a string")
    value = value.replace("\\", "/")
    if not value or ":" in value or "\0" in value:
        raise ReplayError(f"unsafe relative path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ReplayError(f"unsafe relative path: {value!r}")
    return value


def file_identity(path: str) -> tuple[str, int | None]:
    """A file-family key, not a claim to recover missing domain object IDs."""
    match = re.search(r"-v([1-9][0-9]*)(\.[^/]+)$", path)
    if match:
        return path[:match.start()] + match[2], int(match[1])
    return path, None


class Replay:
    def __init__(self, case_path: str | Path):
        self.case_path = Path(case_path).resolve()
        self.case_bytes = self.case_path.read_bytes()
        self.case = json.loads(self.case_bytes.decode("utf-8-sig"))
        if self.case.get("schema_version") != VERSION:
            raise ReplayError("unsupported replay case version")
        self.root = (self.case_path.parent / self.case["workspace_root"]).resolve()
        self.sources: dict[str, dict[str, Any]] = {}
        self._bytes: dict[str, bytes] = {}

    def resolve(self, path: str) -> Path:
        normalized = relative_path(path)
        target = (self.root / normalized).resolve()
        if not target.is_relative_to(self.root):
            raise ReplayError(f"path escapes workspace: {path}")
        return target

    def read(self, path: str, expected: dict | None = None) -> bytes:
        path = relative_path(path)
        if path not in self._bytes:
            try:
                data = self.resolve(path).read_bytes()
            except OSError as error:
                raise ReplayError(f"source unavailable: {path}") from error
            self._bytes[path] = data
            self.sources[path] = {"path": path, "bytes": len(data), "sha256": digest(data)}
        data = self._bytes[path]
        if expected is not None:
            if expected.get("sha256") != digest(data) or expected.get("bytes") != len(data):
                raise ReplayError(f"manifest fingerprint mismatch: {path}")
        return data

    def text(self, path: str) -> str:
        return self.read(path).decode("utf-8-sig")

    def manifest(self, path: str) -> list[dict]:
        rows = json.loads(self.read(path).decode("utf-8-sig"))
        if not isinstance(rows, list):
            raise ReplayError(f"manifest must contain a list: {path}")
        seen = set()
        for row in rows:
            normalized = relative_path(row["path"])
            if normalized in seen:
                raise ReplayError(f"duplicate manifest path: {normalized}")
            seen.add(normalized)
        return rows

    def anchor(self, source: str, quote: str) -> dict:
        if not isinstance(quote, str) or not quote.strip():
            raise ReplayError("empty evidence anchor")
        text = self.text(source)
        if text.count(quote) != 1:
            raise ReplayError(f"evidence anchor missing or ambiguous: {source}: {quote}")
        start = text.index(quote)
        return {"path": relative_path(source), "start_line": text[:start].count("\n") + 1,
                "end_line": text[:start + len(quote)].count("\n") + 1,
                "source_sha256": self.sources[relative_path(source)]["sha256"], "quote": quote}

    def unchanged(self) -> list[str]:
        changed = []
        for path, data in self._bytes.items():
            try:
                if self.resolve(path).read_bytes() != data:
                    changed.append(path)
            except OSError:
                changed.append(path)
        if self.case_path.read_bytes() != self.case_bytes:
            changed.append("replay_case")
        return changed

    def run(self, *, apply_recorded_treatments: bool = True) -> dict:
        artifacts = {}
        for row in self.manifest(self.case["artifact_manifest"]):
            path = relative_path(row["path"])
            self.read(path, row)
            family, revision = file_identity(path)
            if type(row.get("active")) is not bool:
                raise ReplayError(f"archived active flag required: {path}")
            artifacts[path] = {"path": path, "file_family": family,
                               "filename_revision": revision, "bytes": row["bytes"],
                               "sha256": row["sha256"], "archived_active": row["active"]}

        # Archive manifests attest historical copies and handoffs. No body is exported.
        archive = self.case["archive_inventory"]
        archive_rows = self.manifest(archive["manifest"])
        archive_index = {relative_path(row["path"]): row for row in archive_rows}
        archive_root = relative_path(archive["root"])

        def archived(path: str) -> None:
            path = relative_path(path)
            prefix = archive_root + "/"
            if not path.startswith(prefix) or path[len(prefix):] not in archive_index:
                raise ReplayError(f"source absent from archive inventory: {path}")
            self.read(path, archive_index[path[len(prefix):]])

        archived(self.case["artifact_manifest"])
        inventories = []
        for inventory in self.case.get("inventories", []):
            archived(inventory["manifest"])
            for row in self.manifest(inventory["manifest"]):
                logical = relative_path(row["path"])
                source = relative_path(inventory["root"]) + "/" + logical
                archived(source)
                self.read(source, row)
                if logical not in artifacts or artifacts[logical]["sha256"] != row["sha256"]:
                    raise ReplayError(f"snapshot differs from registered original: {logical}")
                inventories.append({"inventory_id": inventory["id"], "artifact_path": logical,
                                    "source_path": source, "meaning": "available_copy_only_not_read_evidence"})

        handoffs = []
        orders = set()
        for source in self.case.get("handoff_sources", []):
            archived(source)
            value = json.loads(self.text(source))
            rows = value if isinstance(value, list) else value.get("tasks", [value])
            for row in rows:
                order = row["order"]
                if type(order) is not int or order in orders:
                    raise ReplayError("handoff order must be unique and integer")
                orders.add(order)
                handoffs.append({"order": order, "target": row["target"], "mode": row["mode"],
                                 "source_path": source, "message_sha256": digest(row["message"].encode("utf-8")),
                                 "meaning": "archived_dispatch_not_current_task_state"})
        handoffs.sort(key=lambda row: row["order"])

        review = self.case["original_review"]
        source = relative_path(review["path"])
        if source not in artifacts:
            raise ReplayError("review must be in artifact manifest")
        text = self.text(source)
        heading = review["section"]
        section_anchor = self.anchor(source, heading)
        start = text.index(heading) + len(heading)
        next_heading = text.find("\n## ", start)
        section = text[start:next_heading if next_heading >= 0 else len(text)]
        by_name: dict[str, list[str]] = {}
        for path in artifacts:
            by_name.setdefault(PurePosixPath(path).name, []).append(path)
        bindings = []
        seen_bindings = set()
        for line in section.splitlines():
            if not re.match(r"^\|\s*[0-9]+\s*\|", line):
                continue
            tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9._/-]*-v[1-9][0-9]*\.(?:md|svg|png)", line)
            for token in tokens:
                if "/" in token:
                    candidates = [token] if token in artifacts else []
                else:
                    candidates = by_name.get(token, [])
                if len(candidates) != 1:
                    raise ReplayError(f"ambiguous or unregistered review reference: {token}")
                path = candidates[0]
                if path in seen_bindings:
                    raise ReplayError(f"duplicate review binding: {path}")
                seen_bindings.add(path)
                bindings.append({"review_path": source, "artifact_path": path,
                                 "scope": line.split("|")[-2].strip(),
                                 "basis": self.anchor(source, line)})
        if len(bindings) != review["expected_binding_count"]:
            raise ReplayError("review binding count differs from explicit adapter expectation")
        bound_families = [artifacts[b["artifact_path"]]["file_family"] for b in bindings]
        if len(set(bound_families)) != len(bound_families):
            raise ReplayError("original review binds multiple revisions of one file family")

        active: dict[str, list[str]] = {}
        for path, artifact in artifacts.items():
            if artifact["archived_active"]:
                active.setdefault(artifact["file_family"], []).append(path)
        findings = []
        for binding in bindings:
            old = binding["artifact_path"]
            current = active.get(artifacts[old]["file_family"], [])
            if len(current) != 1:
                findings.append({"reviewed_path": old, "final_path": None,
                                 "baseline_status": "unknown_or_ambiguous_final_pointer",
                                 "status": "unknown_or_ambiguous_final_pointer", "active_paths": current,
                                 "original_review_basis": binding["basis"]})
            elif current[0] != old:
                findings.append({"reviewed_path": old, "final_path": current[0],
                                 "baseline_status": "needs_recheck", "status": "needs_recheck",
                                 "original_review_basis": binding["basis"]})

        treatments = []
        treatment_keys = set()
        for treatment in self.case.get("treatments", []) if apply_recorded_treatments else []:
            old, new = relative_path(treatment["from"]), relative_path(treatment["to"])
            if (old, new) in treatment_keys:
                raise ReplayError("duplicate treatment for version change")
            treatment_keys.add((old, new))
            matches = [f for f in findings if f["reviewed_path"] == old and f["final_path"] == new]
            if len(matches) != 1:
                raise ReplayError("treatment must match an observed version change")
            if artifacts[old]["file_family"] != artifacts[new]["file_family"]:
                raise ReplayError("treatment cannot change file identity")
            kind = treatment["kind"]
            if kind not in {"supplementary_review", "post_review_closeout"}:
                raise ReplayError("unsupported treatment kind")
            anchors = []
            for assertion in treatment["assertions"]:
                evidence_path = relative_path(assertion["path"])
                if evidence_path not in artifacts:
                    archived(evidence_path)
                anchors.append(self.anchor(evidence_path, assertion["quote"]))
            if not anchors or not any(PurePosixPath(new).name in a["quote"] for a in anchors):
                raise ReplayError("treatment must explicitly anchor the new version")
            receipt = relative_path(treatment["receipt_path"])
            if receipt not in artifacts or receipt not in {a["path"] for a in anchors}:
                raise ReplayError("treatment requires an anchored registered receipt")
            if kind == "supplementary_review":
                if not any(PurePosixPath(source).name in a["quote"] for a in anchors if a["path"] == receipt):
                    raise ReplayError("supplement must explicitly link the original review")
                status = "covered_by_recorded_supplement"
            else:
                status = "post_review_closeout_not_ag3_reviewed"
            projected = {"kind": kind, "from": old, "to": new, "receipt_path": receipt,
                         "scope": treatment["scope"], "anchors": anchors,
                         "meaning": "explicit_adapter_projection_of_historical_receipt"}
            treatments.append(projected)
            matches[0].update(status=status, treatment=projected)

        protections = []
        for path in self.case.get("protected_paths", []):
            self.read(path)
            protections.append(self.sources[relative_path(path)])
        changed = self.unchanged()
        if changed:
            raise ReplayError(f"source changed during replay: {changed}")
        summary = {
            "artifact_versions": len(artifacts),
            "archived_active_entries": sum(a["archived_active"] for a in artifacts.values()),
            "candidate_inventory_entries": len(inventories), "handoffs": len(handoffs),
            "original_review_bindings": len(bindings), "baseline_version_differences": len(findings),
            "recorded_supplements": sum(f["status"] == "covered_by_recorded_supplement" for f in findings),
            "post_review_closeouts_not_ag3_reviewed": sum(f["status"] == "post_review_closeout_not_ag3_reviewed" for f in findings),
            "unresolved_version_differences": sum(f["status"] in {"needs_recheck", "unknown_or_ambiguous_final_pointer"} for f in findings),
        }
        return {"schema_version": VERSION, "case_id": self.case["case_id"], "mode": "offline_read_only_replay",
                "scenario": "historical_as_recorded" if apply_recorded_treatments else "counterfactual_without_recorded_treatments",
                "evidence_kind": self.case["evidence_kind"], "status": "replayed",
                "case_sha256": digest(self.case_bytes), "workspace_root": str(self.root),
                "summary": summary, "artifacts": list(artifacts.values()), "inventories": inventories,
                "handoffs": handoffs, "original_review": {"path": source, "section_basis": section_anchor},
                "review_bindings": bindings, "findings": findings, "treatments": treatments,
                "source_integrity": {"verified_files": len(self.sources), "changed_files": [],
                                     "protected_files": protections, "sources": list(self.sources.values())},
                "limitations": [
                    "文件族由文件名推导，不替代共享契约的正式对象ID；无版本文件不猜造修订号。",
                    "active仅为历史清单标记，多条active保留，不自动选最大版本或创建当前采用指针。",
                    "审查读取事实来自原审查指定表格；候选库存不代表已读。",
                    "补核结论与收口类型由显式案例适配映射并核对原文锚点，程序不判断专业正确性。",
                    "只回放明确的审查版本关系；未自动恢复全部任务输入、语义依赖、精确时间或完整工具转录。",
                    "计划v2在审查后收口，不记成AG3对该版本的审查。",
                    "未创建或调度Agent、未执行采用、未改学习状态；不证明教学效果或协作收益。"]}


def render_markdown(report: dict) -> str:
    s = report["summary"]
    rows = ["# 任务与产物协调器：第一批只读回放", "",
            f"案例：`{report['case_id']}`。模式：历史证据回放。", "",
            f"场景：`{report['scenario']}`。", "",
            f"校验 {s['artifact_versions']} 个产物版本、{s['handoffs']} 条交接，取得 "
            f"{s['original_review_bindings']} 个原审查绑定。发现 {s['baseline_version_differences']} 项版本差异："
            f"{s['recorded_supplements']} 项有局部补核，"
            f"{s['post_review_closeouts_not_ag3_reviewed']} 项属于审查后收口，"
            f"{s['unresolved_version_differences']} 项版本差异尚无已记录处置。", "",
            "以上计数不是专业审查通过率，也不代表最终集合每个文件都已被AG3审查。", "",
            "| 原审查版本 | 历史最终版本 | 回放结果 |", "|---|---|---|"]
    labels = {"covered_by_recorded_supplement": "原审查不直接覆盖新版；已有明确局部补核",
              "post_review_closeout_not_ag3_reviewed": "审查后计划收口；未记为AG3已审",
              "needs_recheck": "待补核", "unknown_or_ambiguous_final_pointer": "最终指针未知或多义"}
    for f in report["findings"]:
        rows.append(f"| `{f['reviewed_path']}` | `{f['final_path']}` | {labels[f['status']]} |")
    rows += ["", "## 证据定位", ""]
    for f in report["findings"]:
        a = f["original_review_basis"]
        rows.append(f"- 原审查绑定：`{a['path']}:{a['start_line']}`。")
        for a in f.get("treatment", {}).get("anchors", []):
            rows.append(f"- 处置依据：`{a['path']}:{a['start_line']}`：{a['quote']}")
    rows += ["", "## 库存、历史状态与边界", "",
             f"候选快照库存 {s['candidate_inventory_entries']} 项，单独保存；未据库存推断AG3读过旧版。",
             f"历史active条目 {s['archived_active_entries']} 项，包括累积的审查/功能补充；未压成每族一个最新指针。",
             f"读取源文件 {report['source_integrity']['verified_files']} 份，回放结束复核字节无变化。",
             "完整索引见 index.json 与 index.sqlite3；两者是可重建的离线输出，不是运行状态权威源。", ""]
    rows += ["- " + limitation for limitation in report["limitations"]]
    return "\n".join(rows) + "\n"


def write_outputs(replay: Replay, report: dict, output: str | Path) -> Path:
    output = Path(output).resolve()
    # A fresh sibling of the case is the only allowed output destination.
    if output.parent != replay.case_path.parent:
        raise ReplayError("output must be a fresh directory beside the replay case")
    for root in replay.case.get("protected_roots", []):
        if output.is_relative_to(replay.resolve(root)):
            raise ReplayError("output cannot be inside a protected source tree")
    if output.exists():
        raise ReplayError("output already exists; use a new directory to preserve prior replay")
    changed = replay.unchanged()
    if changed:
        raise ReplayError(f"source changed before output: {changed}")
    output.mkdir()
    with closing(sqlite3.connect(output / "index.sqlite3")) as db, db:
        db.executescript("""
            CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE artifacts(path TEXT PRIMARY KEY, family TEXT NOT NULL, revision INTEGER,
                archived_active INTEGER NOT NULL, body TEXT NOT NULL);
            CREATE TABLE inventories(inventory_id TEXT NOT NULL, artifact_path TEXT NOT NULL,
                body TEXT NOT NULL, PRIMARY KEY(inventory_id, artifact_path));
            CREATE TABLE handoffs(order_number INTEGER PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE review_bindings(review_path TEXT NOT NULL, artifact_path TEXT NOT NULL,
                body TEXT NOT NULL, PRIMARY KEY(review_path, artifact_path));
            CREATE TABLE findings(reviewed_path TEXT PRIMARY KEY, status TEXT NOT NULL, body TEXT NOT NULL);
            CREATE TABLE sources(path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL);
        """)
        encode = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True)
        db.executemany("INSERT INTO meta VALUES(?,?)", [("schema_version", VERSION),
            ("mode", report["mode"]), ("scenario", report["scenario"]),
            ("case_id", report["case_id"]), ("case_sha256", report["case_sha256"])])
        db.executemany("INSERT INTO artifacts VALUES(?,?,?,?,?)", [(a["path"], a["file_family"],
            a["filename_revision"], int(a["archived_active"]), encode(a)) for a in report["artifacts"]])
        db.executemany("INSERT INTO inventories VALUES(?,?,?)", [(a["inventory_id"], a["artifact_path"], encode(a)) for a in report["inventories"]])
        db.executemany("INSERT INTO handoffs VALUES(?,?)", [(a["order"], encode(a)) for a in report["handoffs"]])
        db.executemany("INSERT INTO review_bindings VALUES(?,?,?)", [(a["review_path"], a["artifact_path"], encode(a)) for a in report["review_bindings"]])
        db.executemany("INSERT INTO findings VALUES(?,?,?)", [(a["reviewed_path"], a["status"], encode(a)) for a in report["findings"]])
        db.executemany("INSERT INTO sources VALUES(?,?,?)", [(a["path"], a["sha256"], a["bytes"]) for a in report["source_integrity"]["sources"]])
    (output / "index.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "report.md").write_text(render_markdown(report), encoding="utf-8")
    changed = replay.unchanged()
    if changed:
        # Leave diagnostic outputs for inspection, but explicitly invalidate them.
        (output / "INVALID.txt").write_text("Source changed: " + repr(changed), encoding="utf-8")
        raise ReplayError(f"source changed while writing output: {changed}")
    return output
