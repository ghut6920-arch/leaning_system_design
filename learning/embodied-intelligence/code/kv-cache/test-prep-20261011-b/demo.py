"""AI-authored teacher demonstration, version 1.0.0 (2026-10-11).

Two fixed causal attention layers, logical-position RoPE, and a position-wise
tanh residual. Standard library only. This is a numeric illustration, not a
trained language model, a GPU benchmark, or evidence of learner performance.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform


VERSION = "1.0.0"
DIMENSION = 4
TOLERANCE = 1e-10

# Each triple contains W_Q, W_K, W_V; vectors are column-vector coordinates.
WEIGHTS = (
    (
        ((0.5, 0.2, 0.0, 0.1), (0.0, 0.6, 0.1, -0.2),
         (0.2, 0.0, 0.7, 0.1), (0.1, 0.3, 0.0, 0.5)),
        ((0.7, 0.0, 0.1, -0.1), (0.1, 0.5, 0.2, 0.0),
         (0.0, -0.2, 0.6, 0.1), (0.2, 0.1, 0.0, 0.8)),
        ((0.5, 0.2, 0.0, 0.0), (0.0, 0.6, 0.1, 0.0),
         (0.1, 0.0, 0.7, 0.2), (0.0, 0.1, 0.2, 0.5)),
    ),
    (
        ((0.6, 0.1, -0.1, 0.0), (0.2, 0.5, 0.0, 0.1),
         (0.0, 0.2, 0.6, 0.0), (0.1, 0.0, 0.2, 0.7)),
        ((0.5, 0.2, 0.0, 0.1), (0.0, 0.7, 0.1, 0.0),
         (0.1, 0.0, 0.8, -0.1), (0.0, 0.2, 0.1, 0.6)),
        ((0.6, 0.0, 0.1, 0.0), (0.1, 0.5, 0.0, 0.2),
         (0.0, 0.1, 0.6, 0.1), (0.2, 0.0, 0.1, 0.5)),
    ),
)

TOKENS = (
    (0.2, 0.8, -0.3, 0.4),
    (0.6, -0.2, 0.4, 0.9),
    (-0.4, 0.5, 0.7, -0.1),
    (0.9, 0.3, -0.2, 0.5),
    (-0.1, 0.7, 0.3, 0.6),
    (0.5, -0.4, 0.8, 0.2),
)


@dataclass
class LayerCache:
    # Keys already contain RoPE at the original logical token positions.
    keys: list[list[float]] = field(default_factory=list)
    values: list[list[float]] = field(default_factory=list)
    positions: list[int] = field(default_factory=list)


def matrix_vector(matrix, vector):
    return [sum(a * b for a, b in zip(row, vector)) for row in matrix]


def rope(vector, logical_position):
    """Adjacent coordinate pairs; frequencies 1 and 0.01 for d=4/base=10000."""
    result = []
    for pair in range(len(vector) // 2):
        frequency = 10000.0 ** (-2 * pair / len(vector))
        angle = logical_position * frequency
        cosine, sine = math.cos(angle), math.sin(angle)
        first, second = vector[2 * pair:2 * pair + 2]
        result.extend((first * cosine - second * sine,
                       first * sine + second * cosine))
    return result


def attend(query, keys, values):
    # The caller supplies only allowed causal keys, equivalent to adding -inf
    # to prohibited logits before softmax. No multiplicative 0/1 logit mask.
    scores = [sum(a * b for a, b in zip(query, key)) / math.sqrt(DIMENSION)
              for key in keys]
    maximum = max(scores)
    unnormalized = [math.exp(score - maximum) for score in scores]
    total = sum(unnormalized)
    weights = [value / total for value in unnormalized]
    return [sum(weight * value[coordinate]
                for weight, value in zip(weights, values))
            for coordinate in range(DIMENSION)]


def residual_nonlinearity(hidden, attention):
    return [math.tanh(before + added) for before, added in zip(hidden, attention)]


def full_recompute(tokens, positions=None):
    """Rebuild every token's states at both layers for one complete prefix."""
    positions = list(range(len(tokens))) if positions is None else list(positions)
    hidden = [list(token) for token in tokens]
    states = []
    for wq, wk, wv in WEIGHTS:
        queries = [rope(matrix_vector(wq, row), position)
                   for row, position in zip(hidden, positions)]
        keys = [rope(matrix_vector(wk, row), position)
                for row, position in zip(hidden, positions)]
        values = [matrix_vector(wv, row) for row in hidden]
        next_hidden = []
        for index, query in enumerate(queries):
            # The complete input is known but future positions remain masked.
            attention = attend(query, keys[:index + 1], values[:index + 1])
            next_hidden.append(residual_nonlinearity(hidden[index], attention))
        states.append(LayerCache(keys, values, positions.copy()))
        hidden = next_hidden
    return hidden[-1], states


def incremental(token, logical_position, caches):
    """Compute only the new token at each layer and append layer-specific KV."""
    hidden = list(token)
    for layer_index, (wq, wk, wv) in enumerate(WEIGHTS):
        query = rope(matrix_vector(wq, hidden), logical_position)
        key = rope(matrix_vector(wk, hidden), logical_position)
        value = matrix_vector(wv, hidden)
        cache = caches[layer_index]
        cache.keys.append(key)
        cache.values.append(value)
        cache.positions.append(logical_position)
        hidden = residual_nonlinearity(hidden, attend(query, cache.keys, cache.values))
    return hidden


def build_cache(tokens):
    caches = [LayerCache() for _ in WEIGHTS]
    for position, token in enumerate(tokens):
        incremental(token, position, caches)
    return caches


def maximum_error(first, second):
    return max(abs(a - b) for a, b in zip(first, second))


def flattened_kv(caches):
    return [coordinate for cache in caches
            for rows in (cache.keys, cache.values)
            for row in rows for coordinate in row]


def failure_record(name, reference, changed, detail):
    error = maximum_error(reference, changed)
    # Each negative example must actually differ; do not label a mere setup
    # change a failure if the fixed numeric example does not show divergence.
    assert error > 1e-5, (name, error)
    return {"case": name, "reference_last_hidden": reference,
            "changed_last_hidden": changed, "max_abs_error": error,
            "condition_broken": detail, "divergence_observed": True}


def numeric_checks():
    caches = [LayerCache() for _ in WEIGHTS]
    prefixes = []
    for position, token in enumerate(TOKENS):
        cached = incremental(token, position, caches)
        recomputed, full_caches = full_recompute(TOKENS[:position + 1])
        hidden_error = maximum_error(cached, recomputed)
        cache_error = maximum_error(flattened_kv(caches), flattened_kv(full_caches))
        assert hidden_error <= TOLERANCE, (position, hidden_error)
        assert cache_error <= TOLERANCE, (position, cache_error)
        prefixes.append({"prefix_length": position + 1,
                         "logical_positions": list(range(position + 1)),
                         "last_hidden": cached,
                         "hidden_max_abs_error": hidden_error,
                         "all_layers_kv_max_abs_error": cache_error})

    reference, _ = full_recompute(TOKENS[:5])
    edited_prefix = [list(token) for token in TOKENS[:5]]
    edited_prefix[0][0] += 0.9
    edited_reference, _ = full_recompute(edited_prefix)
    stale_result = incremental(TOKENS[4], 4, build_cache(TOKENS[:4]))

    reset_result = incremental(TOKENS[4], 0, build_cache(TOKENS[:4]))

    truncated = build_cache(TOKENS[:4])
    for cache in truncated:
        cache.keys = cache.keys[-2:]
        cache.values = cache.values[-2:]
        cache.positions = cache.positions[-2:]
    truncate_result = incremental(TOKENS[4], 4, truncated)

    failures = [
        failure_record("edited_old_prefix_with_stale_cache", edited_reference,
                       stale_result,
                       "Token 0 changed but old per-layer KV was reused."),
        failure_record("reset_new_logical_position_to_zero", reference,
                       reset_result,
                       "Cached keys retain positions 0..3, while new query/key use 0 instead of 4."),
        failure_record("truncate_global_attention_cache", reference,
                       truncate_result,
                       "Deleted positions 0..1 from both layer caches without changing the global-attention reference model."),
    ]
    return {"comparison_tolerance": TOLERANCE, "all_prefixes_passed": True,
            "prefix_comparisons": prefixes, "negative_examples": failures,
            "maximum_hidden_error": max(row["hidden_max_abs_error"] for row in prefixes),
            "maximum_all_layers_kv_error": max(row["all_layers_kv_max_abs_error"] for row in prefixes)}


def capacity_checks():
    layers, kv_heads, head_dim = 32, 8, 128
    bytes_per_token = 2 * layers * kv_heads * head_dim * 2
    assert bytes_per_token == 128 * 1024
    length, concurrent = 32768, 4
    bf16 = bytes_per_token * length * concurrent
    fp8_payload = 2 * layers * kv_heads * head_dim * 1 * length * concurrent
    gib = 2 ** 30
    assert bf16 == 16 * gib
    assert fp8_payload == 8 * gib
    raw_budget = 11 * gib
    cap_bf16 = raw_budget // (bytes_per_token * length)
    cap_fp8_payload_only = raw_budget // (bytes_per_token * length // 2)
    assert cap_bf16 == 2
    assert cap_fp8_payload_only == 5
    return {"model_for_capacity_only": {"layers": layers, "kv_heads": kv_heads,
                                        "head_dimension": head_dim,
                                        "query_heads": 32, "max_cached_length": length,
                                        "target_active_concurrency": concurrent},
            "bf16_bytes_per_token": bytes_per_token,
            "bf16_KiB_per_token": bytes_per_token / 1024,
            "bf16_single_request_GiB": bytes_per_token * length / gib,
            "bf16_four_requests_GiB": bf16 / gib,
            "fp8_four_requests_payload_only_GiB": fp8_payload / gib,
            "snapshot_lengths": [4096, 8192, 16384, 32768],
            "snapshot_bf16_GiB": bytes_per_token * (4096 + 8192 + 16384 + 32768) / gib,
            "cache_system_budget_GiB": 12, "reserved_overhead_GiB": 1,
            "raw_payload_budget_GiB": 11,
            "bf16_floor_cap": cap_bf16,
            "fp8_payload_only_floor_cap": cap_fp8_payload_only,
            "page_tokens": 16, "bf16_page_MiB": bytes_per_token * 16 / (2 ** 20),
            "limits": ["Capacity arithmetic does not simulate a 32-layer trained model.",
                       "FP8 is payload arithmetic, not implemented quantization or measured quality.",
                       "Floor caps require the assumed 1 GiB overhead allowance to be sufficient; verify real peak memory.",
                       "No timing, hardware, bandwidth, throughput, or service-latency measurement was performed."]}


def main():
    workspace = Path(__file__).resolve().parents[3]
    default_output = workspace / "artifacts/test-prep/kv-cache-20261011-independent-b/teacher-check-output.json"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=default_output)
    args = parser.parse_args()
    result = {"artifact_kind": "AI_teacher_reference_execution",
              "author": "AI mechanism_audit subagent", "version": VERSION,
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "executed_at_utc": datetime.now(timezone.utc).isoformat(),
              "python_version": platform.python_version(),
              "specification": {"layers": 2, "attention_heads": 1,
                                "head_dimension": DIMENSION, "causal": True,
                                "rope_base": 10000,
                                "positionwise_operation": "tanh(hidden + attention)",
                                "trained_language_model": False},
              "numeric_checks": numeric_checks(), "capacity_checks": capacity_checks(),
              "learner_performance_evidence": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved_output": str(args.output.resolve()),
                      "version": VERSION,
                      "all_prefixes_passed": result["numeric_checks"]["all_prefixes_passed"],
                      "maximum_hidden_error": result["numeric_checks"]["maximum_hidden_error"],
                      "negative_example_errors": [row["max_abs_error"]
                          for row in result["numeric_checks"]["negative_examples"]],
                      "BF16_four_requests_GiB": result["capacity_checks"]["bf16_four_requests_GiB"],
                      "FP8_payload_only_four_requests_GiB": result["capacity_checks"]["fp8_four_requests_payload_only_GiB"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
