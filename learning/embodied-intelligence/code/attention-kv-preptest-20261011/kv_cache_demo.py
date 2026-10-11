"""Revision 1: finite teacher demonstration, not a trained Transformer.

AI-authored for the 2026-10-11 preparation review. Standard library only.
Source for attention/masking: Vaswani et al., Attention Is All You Need,
https://arxiv.org/abs/1706.03762, sections 3.1 and 3.2.1.
The cache argument and numerical counterexamples below are derived here.

Two layers, one head, d=2; row-vector convention x W; fixed parameters;
no positional encoding, dropout, training, LayerNorm, FFN, or language head.
Each layer returns x + Attention(q, K, V) W_O. Its K/V are projections of
THAT layer's input, not projections of a shared initial embedding.
No timing, model quality, hardware capacity, or long-context recall claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path


Vector = tuple[float, ...]
Matrix = tuple[Vector, ...]
TOLERANCE = 1e-12
TOKENS: tuple[Vector, ...] = (
    (1.0, 0.0),
    (0.0, 1.0),
    (1.0, 1.0),
    (-0.5, 0.8),
    (0.3, -0.6),
)


@dataclass(frozen=True)
class Layer:
    wq: Matrix
    wk: Matrix
    wv: Matrix
    wo: Matrix


LAYERS: tuple[Layer, ...] = (
    Layer(
        wq=((0.7, -0.2), (0.3, 0.8)),
        wk=((0.5, 0.4), (-0.3, 0.9)),
        wv=((0.6, -0.1), (0.2, 0.7)),
        wo=((0.8, 0.1), (-0.2, 0.5)),
    ),
    Layer(
        wq=((0.6, 0.2), (-0.4, 0.7)),
        wk=((0.8, -0.1), (0.2, 0.6)),
        wv=((0.4, 0.3), (-0.1, 0.8)),
        wo=((0.7, -0.2), (0.3, 0.6)),
    ),
)


@dataclass
class Cache:
    keys: list[Vector] = field(default_factory=list)
    values: list[Vector] = field(default_factory=list)


def project(x: Vector, matrix: Matrix) -> Vector:
    """Row vector x times matrix; kept explicit for inspection."""
    assert len(x) == len(matrix)
    width = len(matrix[0])
    assert all(len(row) == width for row in matrix)
    return tuple(sum(x[i] * matrix[i][j] for i in range(len(x))) for j in range(width))


def add(a: Vector, b: Vector) -> Vector:
    assert len(a) == len(b)
    return tuple(x + y for x, y in zip(a, b))


def attention(query: Vector, keys: list[Vector], values: list[Vector]) -> tuple[Vector, Vector]:
    """Stable softmax(q K^T / sqrt(d)) V; no attention scores cached."""
    assert keys and len(keys) == len(values)
    assert all(len(k) == len(query) for k in keys)
    assert len({len(v) for v in values}) == 1
    scores = [sum(q * k for q, k in zip(query, key)) / math.sqrt(len(query)) for key in keys]
    maximum = max(scores)
    unnormalized = [math.exp(score - maximum) for score in scores]
    denominator = sum(unnormalized)
    weights = tuple(value / denominator for value in unnormalized)
    output = tuple(sum(weights[i] * values[i][j] for i in range(len(values))) for j in range(len(values[0])))
    return output, weights


def full_prefix(tokens: tuple[Vector, ...], *, causal: bool = True) -> dict:
    """Recompute ALL positions at ALL layers from the raw token vectors."""
    hidden = list(tokens)
    traces = []
    for layer in LAYERS:
        layer_inputs = list(hidden)
        keys = [project(x, layer.wk) for x in layer_inputs]
        values = [project(x, layer.wv) for x in layer_inputs]
        outputs = []
        weights = []
        queries = []
        for position, x in enumerate(layer_inputs):
            query = project(x, layer.wq)
            stop = position + 1 if causal else len(layer_inputs)
            attended, row_weights = attention(query, keys[:stop], values[:stop])
            outputs.append(add(x, project(attended, layer.wo)))
            weights.append(row_weights)
            queries.append(query)
        traces.append({"inputs": layer_inputs, "queries": queries, "keys": keys, "values": values,
                       "weights": weights, "outputs": outputs})
        hidden = outputs
    return {"outputs": hidden, "layers": traces}


def append_token(token: Vector, caches: list[Cache]) -> tuple[Vector, list[dict]]:
    """Only the appended token is propagated through the two layers."""
    assert len(caches) == len(LAYERS)
    assert len({len(c.keys) for c in caches}) == 1
    hidden = token
    traces = []
    for layer, cache in zip(LAYERS, caches):
        layer_input = hidden
        query = project(layer_input, layer.wq)
        new_key = project(layer_input, layer.wk)
        new_value = project(layer_input, layer.wv)
        cache.keys.append(new_key)
        cache.values.append(new_value)
        attended, weights = attention(query, cache.keys, cache.values)
        hidden = add(layer_input, project(attended, layer.wo))
        traces.append({"input": layer_input, "query": query, "appended_key": new_key,
                       "appended_value": new_value, "weights": weights, "output": hidden})
    return hidden, traces


def build_cache(tokens: tuple[Vector, ...]) -> list[Cache]:
    caches = [Cache() for _ in LAYERS]
    for token in tokens:
        append_token(token, caches)
    return caches


def max_error(a, b) -> float:
    """Maximum absolute error between identically shaped numeric sequences."""
    if isinstance(a, (int, float)):
        return abs(a - b)
    assert len(a) == len(b)
    return max((max_error(x, y) for x, y in zip(a, b)), default=0.0)


def kv_cache_bytes(layers: int, lengths: list[int], kv_heads: int, head_dim: int, bytes_per_element: int) -> int:
    """Logical KV payload; no padding, metadata, weights, activations, or workspace.

    lengths lists the cached token counts of distinct resident sequences.
    For shared physical prefixes, physical allocation requires a separate count.
    """
    assert all(type(value) is int and value > 0 for value in (layers, kv_heads, head_dim, bytes_per_element))
    assert all(type(length) is int and length >= 0 for length in lengths)
    return 2 * layers * sum(lengths) * kv_heads * head_dim * bytes_per_element


def gibibytes(byte_count: int) -> float:
    return byte_count / 2**30


def finite_checks() -> tuple[dict, list[str]]:
    lines = ["Teacher toy, revision 1: 2 layers, 1 head, d=2, fixed parameters, no position encoding.",
             "No training, model quality test, benchmark, GPU measurement, or learner performance record."]
    checks = {}

    # 1. The numerical trace checks every cached prefix, not only the final token.
    caches = [Cache() for _ in LAYERS]
    cached_outputs = []
    prefix_rows = []
    for length, token in enumerate(TOKENS, start=1):
        output, step = append_token(token, caches)
        cached_outputs.append(output)
        recomputed = full_prefix(TOKENS[:length])
        output_error = max_error(cached_outputs, recomputed["outputs"])
        kv_error = max(max_error(cache.keys, trace["keys"]) for cache, trace in zip(caches, recomputed["layers"]))
        kv_error = max(kv_error, max(max_error(cache.values, trace["values"]) for cache, trace in zip(caches, recomputed["layers"])))
        assert output_error <= TOLERANCE and kv_error <= TOLERANCE
        prefix_rows.append({"tokens": length, "output_max_abs_error": output_error, "kv_max_abs_error": kv_error,
                            "cached_new_output": output, "recomputed_new_output": recomputed["outputs"][-1],
                            "appended_layer_traces": step})
        lines.append(f"[PASS] prefix {length}: all outputs max error={output_error:.3e}, all layer KV max error={kv_error:.3e}")
    checks["causal_cached_vs_recomputed"] = {"passed": True, "tolerance": TOLERANCE, "prefixes": prefix_rows}

    # 2. Isolate the read operation: two candidate new Q read the SAME old KV.
    old_cache = build_cache(TOKENS[:3])[0]
    original_keys = tuple(old_cache.keys)
    original_values = tuple(old_cache.values)
    q_a = project(TOKENS[4], LAYERS[0].wq)
    q_b = project((-0.8, 0.2), LAYERS[0].wq)
    read_a, weights_a = attention(q_a, old_cache.keys, old_cache.values)
    read_b, weights_b = attention(q_b, old_cache.keys, old_cache.values)
    query_read_error = max_error(read_a, read_b)
    assert tuple(old_cache.keys) == original_keys and tuple(old_cache.values) == original_values
    assert query_read_error > TOLERANCE
    checks["new_query_same_old_kv"] = {"passed": True, "scope": "attention readout over the old prefix only; current token KV excluded to isolate Q",
                                         "old_keys": old_cache.keys, "old_values": old_cache.values,
                                         "query_a": q_a, "query_b": q_b, "weights_a": weights_a, "weights_b": weights_b,
                                         "readout_a": read_a, "readout_b": read_b, "readout_max_abs_difference": query_read_error,
                                         "old_kv_unchanged": True}
    lines.append(f"[PASS] new Q / same old KV: readout difference={query_read_error:.6f}; old KV unchanged")

    # 3. Deleting one KV pair changes this readout and softmax normalization.
    read_deleted, weights_deleted = attention(q_a, old_cache.keys[1:], old_cache.values[1:])
    delete_error = max_error(read_a, read_deleted)
    assert delete_error > TOLERANCE
    checks["delete_old_kv"] = {"passed": True, "removed_original_position": 0, "query": q_a,
                              "full_readout": read_a, "deleted_readout": read_deleted,
                              "weights_before": weights_a, "weights_after": weights_deleted,
                              "readout_max_abs_difference": delete_error}
    lines.append(f"[PASS] delete old KV pair at position 0: readout difference={delete_error:.6f}")

    # 4. Editing an early token: initial projections are local; deeper ones are contextual.
    original_prefix = TOKENS[:3]
    edited_prefix = ((1.3, -0.4),) + original_prefix[1:]
    before = full_prefix(original_prefix)
    after = full_prefix(edited_prefix)
    first_layer_unchanged = [max_error(before["layers"][0]["keys"][j], after["layers"][0]["keys"][j]) for j in (1, 2)]
    second_layer_changed = [max_error(before["layers"][1]["keys"][j], after["layers"][1]["keys"][j]) for j in (1, 2)]
    assert all(error <= TOLERANCE for error in first_layer_unchanged)
    assert all(error > TOLERANCE for error in second_layer_changed)
    stale_output, _ = append_token(TOKENS[3], build_cache(original_prefix))
    repaired_output, _ = append_token(TOKENS[3], build_cache(edited_prefix))
    correct_output = full_prefix(edited_prefix + (TOKENS[3],))["outputs"][-1]
    stale_error = max_error(stale_output, correct_output)
    repaired_error = max_error(repaired_output, correct_output)
    assert stale_error > TOLERANCE and repaired_error <= TOLERANCE
    checks["early_edit_invalidation"] = {"passed": True, "edited_position": 0,
                                         "old_token": original_prefix[0], "new_token": edited_prefix[0],
                                         "unedited_positions": [1, 2],
                                         "first_layer_unedited_key_errors": first_layer_unchanged,
                                         "second_layer_unedited_key_differences": second_layer_changed,
                                         "first_layer_inputs_before": before["layers"][0]["inputs"],
                                         "first_layer_inputs_after": after["layers"][0]["inputs"],
                                         "second_layer_inputs_before": before["layers"][1]["inputs"],
                                         "second_layer_inputs_after": after["layers"][1]["inputs"],
                                         "second_layer_keys_before": before["layers"][1]["keys"],
                                         "second_layer_keys_after": after["layers"][1]["keys"],
                                         "next_output_with_stale_cache": stale_output,
                                         "next_output_after_prefix_rebuild": repaired_output,
                                         "next_output_full_recompute": correct_output,
                                         "stale_max_abs_error": stale_error, "repaired_max_abs_error": repaired_error}
    lines.append("[PASS] early edit: unedited layer 1 K differences=" + str(first_layer_unchanged))
    lines.append("[PASS] early edit: unedited downstream layer 2 K differences=" + ", ".join(f"{error:.6f}" for error in second_layer_changed))
    lines.append(f"[PASS] stale cache error={stale_error:.6f}; rebuilt cache error={repaired_error:.3e}")

    # 5. Counterexample when the causal invariant is removed.
    bidirectional_before = full_prefix(TOKENS[:3], causal=False)
    bidirectional_after = full_prefix(TOKENS[:4], causal=False)
    old_output_difference = max_error(bidirectional_before["outputs"][0], bidirectional_after["outputs"][0])
    downstream_key_difference = max_error(bidirectional_before["layers"][1]["keys"][0], bidirectional_after["layers"][1]["keys"][0])
    assert old_output_difference > TOLERANCE and downstream_key_difference > TOLERANCE
    checks["bidirectional_append_counterexample"] = {"passed": True, "old_position": 0,
                                                      "old_output_before_append": bidirectional_before["outputs"][0],
                                                      "old_output_after_append": bidirectional_after["outputs"][0],
                                                      "old_output_max_abs_difference": old_output_difference,
                                                      "layer_2_old_key_max_abs_difference": downstream_key_difference}
    lines.append(f"[PASS] bidirectional append: old output difference={old_output_difference:.6f}, layer 2 old K difference={downstream_key_difference:.6f}")

    # 6. Capacity arithmetic. Query-head count is recorded, never substituted for KV heads.
    capacity_rows = []
    for length, expected_bf16 in ((16384, 2.0), (32768, 4.0), (65536, 8.0)):
        bf16 = kv_cache_bytes(32, [length], 8, 128, 2)
        batch4 = kv_cache_bytes(32, [length] * 4, 8, 128, 2)
        ideal_int8 = kv_cache_bytes(32, [length], 8, 128, 1)
        assert gibibytes(bf16) == expected_bf16
        assert gibibytes(batch4) == 4 * expected_bf16
        assert gibibytes(ideal_int8) == expected_bf16 / 2
        capacity_rows.append({"cached_tokens_per_sequence": length, "bf16_batch1_bytes": bf16,
                              "bf16_batch1_GiB": gibibytes(bf16), "bf16_batch4_GiB": gibibytes(batch4),
                              "ideal_int8_batch1_GiB": gibibytes(ideal_int8)})
        lines.append(f"[PASS] KV payload T={length}: BF16 B=1 {gibibytes(bf16):g} GiB, B=4 {gibibytes(batch4):g} GiB; ideal INT8 B=1 {gibibytes(ideal_int8):g} GiB")
    ragged = kv_cache_bytes(32, [16384, 32768], 8, 128, 2)
    padded = kv_cache_bytes(32, [32768, 32768], 8, 128, 2)
    mha64k = kv_cache_bytes(32, [65536], 32, 128, 2)
    assert gibibytes(ragged) == 6.0 and gibibytes(padded) == 8.0 and gibibytes(mha64k) == 32.0
    checks["capacity_arithmetic"] = {"passed": True, "formula": "2 * L * sum(T_i) * n_kv * d_h * bytes_per_element",
                                     "layers": 32, "query_heads": 32, "kv_heads": 8, "head_dim": 128,
                                     "bf16_bytes_per_element": 2, "GiB_divisor": 2**30,
                                     "bytes_per_token": kv_cache_bytes(32, [1], 8, 128, 2), "rows": capacity_rows,
                                     "ragged_lengths": [16384, 32768], "ragged_payload_GiB": gibibytes(ragged),
                                     "padded_payload_GiB": gibibytes(padded), "mha_32_kv_heads_at_65536_GiB": gibibytes(mha64k),
                                     "scope": "logical payload only, no quantization metadata, padding unless specified, fragmentation, weights, activations, workspace, or physical prefix sharing"}
    lines.append(f"[PASS] ragged [16384,32768]: {gibibytes(ragged):g} GiB; padded [32768,32768]: {gibibytes(padded):g} GiB; 32-KV-head MHA at T=65536: {gibibytes(mha64k):g} GiB")
    lines.append(f"All 6 finite checks passed; tolerance={TOLERANCE:g}.")
    return checks, lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="optional explicit report path; overwritten only when requested")
    args = parser.parse_args()
    checks, lines = finite_checks()
    script = Path(__file__).resolve()
    report = {"artifact_kind": "teacher_preparation_finite_numerical_verification",
              "revision": 1, "author_contribution": "AI wrote and ran the entire demonstration; no learner implementation or run",
              "environment": {"python_version": sys.version, "python_executable": sys.executable,
                              "platform": platform.platform(), "standard_library_only": True},
              "code": {"path": str(script), "sha256": hashlib.sha256(script.read_bytes()).hexdigest()},
              "source": {"attention_and_causal_mask": "https://arxiv.org/abs/1706.03762, sections 3.1 and 3.2.1",
                         "cache_reasoning": "derived from fixed-parameter causal dependency invariance; paper is not cited as a KV-cache implementation"},
              "specification": {"layers": 2, "heads": 1, "d": 2, "causal": True, "position_encoding": "none",
                                "layer_output": "x + softmax(q K^T / sqrt(2)) V W_O",
                                "layer_kv": "K,V projected from this layer's input", "tokens": TOKENS,
                                "parameters": [{"wq": layer.wq, "wk": layer.wk, "wv": layer.wv, "wo": layer.wo} for layer in LAYERS],
                                "omitted": ["training", "real token semantics", "FFN", "LayerNorm", "dropout", "language head"]},
              "checks": checks, "stdout": "\n".join(lines) + "\n",
              "limits": ["finite arithmetic checks do not prove equality for every possible model or input",
                         "the causal invariant additionally requires unchanged prefix, weights, positions, visibility rules, and deterministic prefix-local computation",
                         "no latency, GPU throughput, long-context quality, or real-model INT8 accuracy measured",
                         "this run is teacher preparation, not actual teaching or a learner performance event"]}
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report["stdout"], end="")


if __name__ == "__main__":
    main()
