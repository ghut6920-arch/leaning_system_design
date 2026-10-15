"""Model-facing views of already verified bytes; no state or pointer changes."""
from __future__ import annotations

import base64
import hashlib

from .workspace import GateError

DEFAULT_TEXT_CHARS = 8000


def text_page(text, *, offset=0, max_chars=DEFAULT_TEXT_CHARS):
    if type(offset) is not int or not 0 <= offset <= len(text):
        raise GateError("invalid_read_offset")
    if max_chars is not None and (type(max_chars) is not int or max_chars < 0):
        raise GateError("invalid_read_limit")
    end = len(text) if max_chars is None else min(len(text), offset + max_chars)
    return {"text": text[offset:end], "coverage": {
        "unit": "unicode_characters", "start": offset, "end": end, "total": len(text),
        "complete": offset == 0 and end == len(text), "has_more": end < len(text),
        "next_offset": end if end < len(text) else None,
        "view_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }}


def verified_view(item, *, root, view="metadata", offset=0,
                  max_chars=DEFAULT_TEXT_CHARS, expected_sha256=None):
    """Never reopen item.path: use exactly the bytes validated by the gate."""
    if view not in {"metadata", "text", "base64"}:
        raise GateError("invalid_read_view")
    data = item["content"]
    fingerprint = hashlib.sha256(data).hexdigest()
    if item.get("sha256") is not None and fingerprint != item["sha256"]:
        raise GateError("artifact_fingerprint_changed")
    if expected_sha256 is not None and fingerprint != expected_sha256:
        raise GateError("read_version_changed")
    row = {key: value for key, value in item.items() if key != "content"}
    row.update(sha256=fingerprint, byte_length=len(data))
    if view == "base64":
        row["content_base64"] = base64.b64encode(data).decode("ascii")
        return row
    if view == "metadata":
        return row
    try:
        text = data.decode("utf-8-sig")
        if any(ord(char) < 32 and char not in "\t\r\n" for char in text):
            raise UnicodeError("binary_controls")
    except UnicodeError:
        row["path"] = str((root / item["path"]).resolve())
        row["next_action"] = "该确切版本为非文本；查看此路径时仍需核对sha256，不改用最新文件。"
        return row
    row.update(text_page(text, offset=offset, max_chars=max_chars))
    if row["coverage"]["has_more"]:
        row["next_action"] = "按同一版本及next_offset续读；已输出的区间不能冒称全文已读。"
    return row


def add_read_arguments(parser, *, default_view, allow_base64=False):
    parser.add_argument("--view", choices=["metadata", "text"] + (["base64"] if allow_base64 else []), default=default_view)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_TEXT_CHARS)
    parser.add_argument("--full", action="store_true", help="请求完整必要正文；只读入口仍受总返回预算约束，按实际coverage续读")
    parser.add_argument("--expect-sha256", help="分段续读时绑定前次取得的字节指纹")


def read_options(args):
    if args.max_chars < 1:
        raise GateError("invalid_read_limit")
    if args.offset < 0:
        raise GateError("invalid_read_offset")
    if args.view == "metadata" and (args.full or args.offset):
        raise GateError("explicit_text_view_required")
    return {"view": args.view, "offset": args.offset,
            "max_chars": None if args.full else args.max_chars,
            "expected_sha256": args.expect_sha256}
