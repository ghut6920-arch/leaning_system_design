"""One budget for the final serialized read response, with receiver-verifiable framing."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .workspace import GateError

DEFAULT_RETURN_BYTES = 8192
MAX_RETURN_BYTES = 65536
VERSION = "read-delivery/0.1.0"
SEPARATOR = "\n\n--- 阅读正文 ---\n\n"
END = "\nREAD_END "


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value):
    return hashlib.sha256(value).hexdigest()


def body_nodes(value):
    if isinstance(value, dict):
        if isinstance(value.get("text"), str) and isinstance(value.get("coverage"), dict):
            yield value
        for child in value.values():
            yield from body_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from body_nodes(child)


def render(payload, *, plain_text=False):
    if plain_text and "text" in payload:
        metadata = {k: v for k, v in payload.items() if k != "text"}
        prefix = json.dumps(metadata, ensure_ascii=False, separators=(",", ":")) + SEPARATOR + payload["text"]
        return prefix + END + fingerprint(prefix.encode("utf-8")) + "\n"
    framed = {**payload, "delivery": {"version": VERSION, "payload_sha256": fingerprint(canonical(payload)),
                                      "end": "READ_END"}}
    return json.dumps(framed, ensure_ascii=False, indent=2) + "\n"


def bounded_output(result, *, budget=DEFAULT_RETURN_BYTES, plain_text=False):
    if type(budget) is not int or not 1024 <= budget <= MAX_RETURN_BYTES:
        raise GateError("invalid_return_budget")
    original = deepcopy(result)
    original.pop("delivery", None)
    full = render(original, plain_text=plain_text)
    if len(full.encode("utf-8")) <= budget:
        return full
    originals = list(body_nodes(original))
    if not originals:
        raise GateError("return_metadata_exceeds_budget")

    def limited(limit):
        candidate = deepcopy(original)
        remaining = limit
        for row in body_nodes(candidate):
            text = row["text"]
            if row["coverage"]["end"] - row["coverage"]["start"] != len(text):
                raise GateError("invalid_page_coverage")
            length = min(len(text), remaining)
            remaining -= length
            if length == len(text):
                continue
            row["text"] = text[:length]
            coverage = row["coverage"]
            end = coverage["start"] + length
            coverage.update(end=end, complete=coverage["start"] == 0 and end == coverage["total"],
                            has_more=end < coverage["total"], next_offset=end if end < coverage["total"] else None)
            row["next_action"] = "总返回预算限制了本页；核结束标记后按同版本next_offset补取缺口。"
        candidate["return_limited"] = True
        return render(candidate, plain_text=plain_text)

    zero = limited(0)
    if len(zero.encode("utf-8")) > budget:
        raise GateError("return_metadata_exceeds_budget")
    low, high, best = 0, sum(len(r["text"]) for r in originals), zero
    while low <= high:
        mid = (low + high) // 2
        output = limited(mid)
        if len(output.encode("utf-8")) <= budget:
            best, low = output, mid + 1
        else:
            high = mid - 1
    return best


def verify_delivery(raw):
    """Validate the exact captured response. Never validate a reconstructed transcript."""
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if raw.lstrip().startswith("{") and SEPARATOR not in raw:
            payload = json.loads(raw)
            delivery = payload.pop("delivery")
            if (delivery.get("version") != VERSION or delivery.get("end") != "READ_END"
                    or delivery.get("payload_sha256") != fingerprint(canonical(payload))):
                raise ValueError("mismatch")
        else:
            prefix, final = raw.rsplit(END, 1)
            if final != fingerprint(prefix.encode("utf-8")) + "\n":
                raise ValueError("incomplete or changed")
            header, text = prefix.split(SEPARATOR, 1)
            payload = {**json.loads(header), "text": text}
        for row in body_nodes(payload):
            coverage = row["coverage"]
            start, end, total = coverage["start"], coverage["end"], coverage["total"]
            if (any(type(v) is not int for v in (start, end, total)) or not 0 <= start <= end <= total
                    or len(row["text"]) != end - start
                    or coverage["complete"] != (start == 0 and end == total)
                    or coverage["has_more"] != (end < total)
                    or coverage["next_offset"] != (end if end < total else None)):
                raise ValueError("coverage")
        return payload
    except (ValueError, KeyError, TypeError, UnicodeError, AttributeError):
        raise GateError("read_delivery_incomplete_or_changed") from None
