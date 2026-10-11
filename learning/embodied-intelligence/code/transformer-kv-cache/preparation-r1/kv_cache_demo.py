"""Teacher preparation r1: standard-library, two-layer causal decoder.

AI-authored teaching example, not a trained model or a learner submission.
All executable preparation code is stored under code/. See README.md.
"""
from __future__ import annotations

import copy
import csv
import io
import json
import math
import platform
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

REVISION = "preparation-r1"
ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1"
TOLERANCE = 1e-12
D_MODEL, H_Q, H_KV, D_HEAD, LAYERS, VOCAB = 4, 2, 2, 2, 2, 7
PROMPT = [1, 4, 2]
FORCED_CONTINUATION = [5, 0, 6, 3]


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def linear(x, weights):
    """weights[out_feature][in_feature], no bias."""
    return [dot(row, x) for row in weights]


def layer_norm(x):
    mean = sum(x) / len(x)
    variance = sum((item - mean) ** 2 for item in x) / len(x)
    denom = math.sqrt(variance + 1e-5)
    return [(item - mean) / denom for item in x]


def gelu(x):
    return 0.5 * x * (1.0 + math.erf(x / math.sqrt(2.0)))


def softmax(x):
    largest = max(x)
    exponentials = [math.exp(item - largest) for item in x]
    total = sum(exponentials)
    return [item / total for item in exponentials]


def position_encoding(position):
    values = []
    for pair in range(D_MODEL // 2):
        angle = position / (10000.0 ** (2.0 * pair / D_MODEL))
        values.extend([math.sin(angle), math.cos(angle)])
    return values


def split_heads(x):
    return [x[h * D_HEAD:(h + 1) * D_HEAD] for h in range(H_Q)]


def max_difference(a, b):
    if isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            raise ValueError("Comparison shape mismatch")
        return max((max_difference(x, y) for x, y in zip(a, b)), default=0.0)
    return abs(a - b)


@dataclass
class Cache:
    # keys[row][kv_head][feature], same layout for values.
    keys: list
    values: list
    positions: list


def empty_cache():
    return [Cache([], [], []) for _ in range(LAYERS)]


def empty_counts():
    return {"projected_rows_per_Q_K_V": 0, "Q_K_V_rows_total": 0,
            "dense_scores": 0, "valid_causal_scores": 0}


class ToyDecoder:
    def __init__(self):
        rng = random.Random(20261011)

        def matrix(rows, columns, scale=0.55):
            return [[rng.uniform(-scale, scale) for _ in range(columns)]
                    for _ in range(rows)]

        self.embeddings = matrix(VOCAB, D_MODEL, 0.7)
        self.layers = [{"q": matrix(D_MODEL, D_MODEL),
                        "k": matrix(D_MODEL, D_MODEL),
                        "v": matrix(D_MODEL, D_MODEL),
                        "o": matrix(D_MODEL, D_MODEL),
                        "ff1": matrix(8, D_MODEL),
                        "ff2": matrix(D_MODEL, 8)} for _ in range(LAYERS)]
        self.output = matrix(VOCAB, D_MODEL)

    def forward(self, tokens, cache=None, start_position=0,
                embedding_position_override=None, wrong_local_mask=False):
        """Compute only supplied token rows; old cache rows are reused.

        Full reference supplies the complete prefix and empty caches. Incremental
        supplies new tokens only and the per-layer caches from prior calls.
        Every new query uses absolute key_position <= query_position masking,
        including q_len > 1 with a nonempty cache (a rectangular mask).
        """
        caches = empty_cache() if cache is None else copy.deepcopy(cache)
        positions = list(range(start_position, start_position + len(tokens)))
        pe_positions = positions if embedding_position_override is None else embedding_position_override
        hidden = [add(self.embeddings[token], position_encoding(pos))
                  for token, pos in zip(tokens, pe_positions)]
        counts = empty_counts()
        masks = []
        for layer_index, weights in enumerate(self.layers):
            normalized = [layer_norm(row) for row in hidden]
            queries = [split_heads(linear(row, weights["q"])) for row in normalized]
            new_keys = [split_heads(linear(row, weights["k"])) for row in normalized]
            new_values = [split_heads(linear(row, weights["v"])) for row in normalized]
            current = caches[layer_index]
            current.keys.extend(new_keys)
            current.values.extend(new_values)
            current.positions.extend(positions)
            key_len = len(current.positions)
            layer_mask = [[(j <= i if wrong_local_mask else key_pos <= query_pos)
                           for j, key_pos in enumerate(current.positions)]
                          for i, query_pos in enumerate(positions)]
            masks.append(layer_mask)
            attention_outputs = []
            for i, query in enumerate(queries):
                concatenated = []
                allowed = [j for j, flag in enumerate(layer_mask[i]) if flag]
                for head in range(H_Q):
                    # This toy uses MHA (H_Q = H_KV); no implicit GQA broadcast.
                    scores = [dot(query[head], current.keys[j][head]) / math.sqrt(D_HEAD)
                              for j in allowed]
                    probabilities = softmax(scores)
                    concatenated.extend([sum(prob * current.values[j][head][feature]
                                             for prob, j in zip(probabilities, allowed))
                                         for feature in range(D_HEAD)])
                attention_outputs.append(linear(concatenated, weights["o"]))
            hidden = [add(row, attention) for row, attention in zip(hidden, attention_outputs)]
            ff_output = [linear([gelu(v) for v in linear(layer_norm(row), weights["ff1"])],
                                weights["ff2"]) for row in hidden]
            hidden = [add(row, ff) for row, ff in zip(hidden, ff_output)]
            counts["projected_rows_per_Q_K_V"] += len(tokens)
            counts["Q_K_V_rows_total"] += 3 * len(tokens)
            counts["dense_scores"] += H_Q * len(tokens) * key_len
            counts["valid_causal_scores"] += H_Q * sum(sum(row) for row in layer_mask)
        logits = [linear(layer_norm(row), self.output) for row in hidden]
        return logits, caches, counts, masks

    def full(self, tokens):
        return self.forward(tokens, cache=None, start_position=0)


def old_cache_unchanged(before, after):
    return all(a.keys == b.keys[:len(a.keys)]
               and a.values == b.values[:len(a.values)]
               and a.positions == b.positions[:len(a.positions)]
               for a, b in zip(before, after))


def sum_counts(counts):
    return {key: sum(row[key] for row in counts) for key in empty_counts()}


def gib(byte_count):
    return byte_count / (1024 ** 3)


def kv_bytes(layers, batch, length, kv_heads, head_dim, bytes_per_element):
    return 2 * layers * batch * length * kv_heads * head_dim * bytes_per_element


def svg_document(width, height, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}"><style>'
            'text{font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#17212b}'
            '.title{font-size:24px;font-weight:700}.body{font-size:17px}.small{font-size:14px}'
            '.blue{fill:#d9ecff;stroke:#438bca}.green{fill:#ddf4df;stroke:#559265}'
            '.orange{fill:#fff0cf;stroke:#c69331}.gray{fill:#f0f3f6;stroke:#9aa7b3}'
            '</style><defs><marker id="arrow" markerWidth="8" markerHeight="8" '
            'refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#547184"/>'
            '</marker></defs><rect width="100%" height="100%" fill="white"/>' + body + '</svg>')


def make_figures(folder, selected=None):
    folder.mkdir(parents=True, exist_ok=True)
    timeline = ['<text x="36" y="44" class="title">Cache 时间线：预测 token 与写入 KV 是两个时刻</text>',
                '<text x="36" y="78" class="body">两层均缓存各自 K/V；行数按“已被模型处理的 token 位置”增长</text>']
    rows = [(130, "Prefill", [0, 1, 2], "最后一行 logits → 预测位置 3 的 token", "此刻位置 3 尚未进入 cache"),
            (240, "Decode 1", [0, 1, 2, 3], "把位置 3 的 token 输入模型并追加其 KV", "这次 logits → 预测位置 4"),
            (350, "Chunk分支", [0, 1, 2, 3, 4], "一次处理位置 3、4：Q 长度 2，K/V 长度 5", "mask：第 3 行可见 0…3；第 4 行可见 0…4")]
    for y, label, positions, line1, line2 in rows:
        timeline.append(f'<text x="36" y="{y}" class="body">{label}</text>')
        for i, pos in enumerate(positions):
            cls = "blue" if pos < 3 else "green"
            timeline.extend([f'<rect x="{155+i*57}" y="{y-26}" width="48" height="40" rx="5" class="{cls}"/>',
                             f'<text x="{173+i*57}" y="{y}" class="body">{pos}</text>'])
        timeline.extend([f'<text x="490" y="{y-8}" class="small">{line1}</text>',
                         f'<text x="490" y="{y+19}" class="small">{line2}</text>'])
        if label == "Chunk分支":
            timeline.append('<text x="490" y="392" class="small">从 Prefill 长度 3 另起，不承接 Decode 1</text>')
    timeline.extend(['<text x="36" y="446" class="body">已有 cache 长度 3 的 chunk mask（1 = 可见；0 = 屏蔽）</text>',
                     '<text x="110" y="480" class="body">query 位置 3 → [1, 1, 1, 1, 0]</text>',
                     '<text x="110" y="515" class="body">query 位置 4 → [1, 1, 1, 1, 1]</text>'])
    if selected is None or "cache-timeline" in selected:
        (folder / "cache-timeline.svg").write_text(svg_document(960, 545, ''.join(timeline)), encoding="utf-8")

    dependency = ['<text x="36" y="44" class="title">两层因果依赖：第 2 层 KV 已携带前缀上下文</text>',
                  '<text x="36" y="78" class="body">每个位置的 LayerNorm / FFN 独立按行；attention 只向前看</text>']
    xs = [270, 430, 590, 750]
    for row, y in [(0, 150), (1, 270), (2, 390)]:
        labels = ["Embedding + 绝对位置", "第 1 层后 h¹", "第 2 层后 h²"]
        dependency.append(f'<text x="36" y="{y+25}" class="body">{labels[row]}</text>')
        for i, x in enumerate(xs):
            cls = ["gray", "blue", "green"][row]
            dependency.extend([f'<rect x="{x}" y="{y}" width="95" height="52" rx="5" class="{cls}"/>',
                               f'<text x="{x+25}" y="{y+32}" class="body">位置 {i}</text>'])
    for source_y, target_y in [(202, 270), (322, 390)]:
        for target in range(4):
            for source in range(target+1):
                dependency.append(f'<path d="M{xs[source]+48},{source_y} L{xs[target]+48},{target_y}" '
                                  'stroke="#b8c8d4" stroke-width="1.1" fill="none" marker-end="url(#arrow)"/>')
    dependency.extend(['<text x="36" y="478" class="body">第 1 层 K/V：投影当前 token 的输入状态；第 2 层 K/V：投影 h¹</text>',
                       '<text x="36" y="514" class="body">改动较早 token 后，后面位置的第 2 层 KV 通常需要重算。</text>',
                       '<text x="36" y="549" class="small">原前缀未变时，追加未来 token 不改变旧位置状态；每层旧 KV 可复用。</text>'])
    if selected is None or "two-layer-dependency" in selected:
        (folder / "two-layer-dependency.svg").write_text(svg_document(960, 575, ''.join(dependency)), encoding="utf-8")

    capacity = ['<text x="36" y="44" class="title">逻辑 KV 容量：L=32，B=1，T=32768，dₕ=128，FP16</text>',
                '<text x="36" y="83" class="body">M = 2 × L × B × T × Hkv × dₕ × 2 bytes（只计 K/V 元素）</text>']
    for i, (label, value, cls) in enumerate([("MHA：Hkv = 32", 16, "blue"),
                                             ("GQA：Hkv = 8", 4, "green"),
                                             ("MQA：Hkv = 1", 0.5, "orange")]):
        y = 145 + i * 90
        capacity.extend([f'<text x="36" y="{y+27}" class="body">{label}</text>',
                         f'<rect x="260" y="{y}" width="{value/16*560}" height="44" rx="4" class="{cls}"/>',
                         f'<text x="{272+value/16*560}" y="{y+28}" class="body">{value:g} GiB</text>'])
    capacity.extend(['<text x="36" y="435" class="body">同一 GQA 配置：T=65536 且 B=2 → 16 GiB</text>',
                     '<text x="36" y="472" class="small">此图不是性能基准：未计参数、激活、allocator、padding、页/元数据、量化尺度。</text>',
                     '<text x="36" y="505" class="small">Hq 决定 query/attention 头数；公式的缓存头数使用 Hkv。</text>'])
    if selected is None or "kv-capacity" in selected:
        (folder / "kv-capacity.svg").write_text(svg_document(960, 535, ''.join(capacity)), encoding="utf-8")
    for path in folder.glob("*.svg"):
        if selected is None or path.stem in selected:
            ElementTree.fromstring(path.read_text(encoding="utf-8"))


def main():
    model = ToyDecoder()
    prompt_logits, cache, prompt_counts, _ = model.full(PROMPT)
    steps = [{"phase": "prefill", "processed_positions": [0, 1, 2],
              "cache_lengths": [len(c.keys) for c in cache],
              "last_logits_predict_position": 3,
              "pending_forced_token": FORCED_CONTINUATION[0],
              "pending_position_in_cache": False,
              "max_logit_difference": 0.0, "old_KV_invariant": True}]
    reference_counts = [prompt_counts]
    cached_counts = [prompt_counts]
    processed = list(PROMPT)
    for token in FORCED_CONTINUATION:
        before = copy.deepcopy(cache)
        next_position = len(processed)
        logits, cache, counts, _ = model.forward([token], cache, next_position)
        processed.append(token)
        reference, full_cache, full_counts, _ = model.full(processed)
        difference = max_difference(logits[-1], reference[-1])
        cache_difference = max(max_difference(a.keys, b.keys) for a, b in zip(cache, full_cache))
        cache_difference = max(cache_difference, max(max_difference(a.values, b.values) for a, b in zip(cache, full_cache)))
        invariant = old_cache_unchanged(before, cache)
        assert all(a.positions == b.positions == list(range(len(processed)))
                   for a, b in zip(cache, full_cache))
        assert difference <= TOLERANCE and cache_difference <= TOLERANCE and invariant
        steps.append({"phase": "decode", "input_token": token,
                      "processed_position": next_position,
                      "cache_lengths": [len(c.keys) for c in cache],
                      "last_logits_predict_position": next_position + 1,
                      "max_logit_difference": difference,
                      "max_full_cache_difference": cache_difference,
                      "old_KV_invariant": invariant,
                      "last_logits": logits[-1]})
        cached_counts.append(counts)
        reference_counts.append(full_counts)

    _, prefix_cache, _, _ = model.full(PROMPT)
    chunk_logits, chunk_cache, _, chunk_masks = model.forward(FORCED_CONTINUATION[:2], prefix_cache, 3)
    full_chunk, _, _, _ = model.full(PROMPT + FORCED_CONTINUATION[:2])
    chunk_difference = max_difference(chunk_logits, full_chunk[3:5])
    correct_mask = [[True, True, True, True, False], [True, True, True, True, True]]
    assert chunk_masks == [correct_mask, correct_mask]
    assert chunk_difference <= TOLERANCE and old_cache_unchanged(prefix_cache, chunk_cache)
    wrong_chunk_logits, _, _, _ = model.forward(FORCED_CONTINUATION[:2], prefix_cache, 3, wrong_local_mask=True)

    edited_prompt = [1, 6, 2]
    _, edited_cache, _, _ = model.full(edited_prompt)
    stale_logits, _, _, _ = model.forward([5], prefix_cache, 3)
    edited_full, _, _, _ = model.full(edited_prompt + [5])
    rebuilt_logits, _, _, _ = model.forward([5], edited_cache, 3)
    first_layer_later_kv_difference = max(max_difference(prefix_cache[0].keys[2], edited_cache[0].keys[2]),
                                          max_difference(prefix_cache[0].values[2], edited_cache[0].values[2]))
    second_layer_later_kv_difference = max(max_difference(prefix_cache[1].keys[2], edited_cache[1].keys[2]),
                                           max_difference(prefix_cache[1].values[2], edited_cache[1].values[2]))
    correct_next, _, _, _ = model.full(PROMPT + [5])
    wrong_position_logits, _, _, _ = model.forward([5], prefix_cache, 3, embedding_position_override=[0])
    shortened = copy.deepcopy(prefix_cache)
    for layer in shortened:
        layer.keys = layer.keys[1:]
        layer.values = layer.values[1:]
        layer.positions = layer.positions[1:]
    dropped_logits, _, _, _ = model.forward([5], shortened, 3)
    negatives = {
        "edited_prefix_with_stale_cache_max_logit_diff": max_difference(stale_logits[-1], edited_full[-1]),
        "edited_prefix_rebuilt_cache_max_logit_diff": max_difference(rebuilt_logits[-1], edited_full[-1]),
        "position_2_layer_1_KV_diff_after_editing_position_1": first_layer_later_kv_difference,
        "position_2_layer_2_KV_diff_after_editing_position_1": second_layer_later_kv_difference,
        "wrong_PE_0_instead_of_3_with_correct_causal_positions_max_logit_diff": max_difference(wrong_position_logits[-1], correct_next[-1]),
        "drop_position_0_KV_retain_absolute_positions_max_logit_diff": max_difference(dropped_logits[-1], correct_next[-1]),
        "chunk_wrong_local_square_mask_max_logit_diff": max_difference(wrong_chunk_logits, full_chunk[3:5]),
        "interpretation": "Counterexamples for these fixed inputs only; no claim every edit/drop must change every model output."
    }
    for key in ["edited_prefix_with_stale_cache_max_logit_diff",
                "position_2_layer_2_KV_diff_after_editing_position_1",
                "wrong_PE_0_instead_of_3_with_correct_causal_positions_max_logit_diff",
                "drop_position_0_KV_retain_absolute_positions_max_logit_diff",
                "chunk_wrong_local_square_mask_max_logit_diff"]:
        assert negatives[key] > 1e-8, key
    assert negatives["edited_prefix_rebuilt_cache_max_logit_diff"] <= TOLERANCE
    assert first_layer_later_kv_difference == 0.0

    probabilities = softmax([math.log(2), 0.0, math.log(2)])
    scalar_output = dot(probabilities, [2, 6, 10])
    old_probabilities = softmax([math.log(2), 0.0])
    old_output = dot(old_probabilities, [2, 6])
    assert max_difference(probabilities, [0.4, 0.2, 0.4]) <= TOLERANCE
    assert abs(scalar_output - 6.0) <= TOLERANCE and abs(old_output - 10/3) <= TOLERANCE
    capacities = {"MHA_Hkv32_B1_T32768_GiB": gib(kv_bytes(32, 1, 32768, 32, 128, 2)),
                  "GQA_Hkv8_B1_T32768_GiB": gib(kv_bytes(32, 1, 32768, 8, 128, 2)),
                  "MQA_Hkv1_B1_T32768_GiB": gib(kv_bytes(32, 1, 32768, 1, 128, 2)),
                  "GQA_Hkv8_B2_T65536_GiB": gib(kv_bytes(32, 2, 65536, 8, 128, 2))}
    assert list(capacities.values()) == [16.0, 4.0, 0.5, 16.0]
    result = {"revision": REVISION, "status": "teacher_preparation_only",
              "learner_execution": False, "trained_model": False,
              "environment": {"python": sys.version, "executable": sys.executable,
                              "platform": platform.platform(), "dependencies": "Python standard library only",
                              "numeric_type": "Python float (binary64 on this runtime)",
                              "float_radix": sys.float_info.radix, "float_mantissa_bits": sys.float_info.mant_dig},
              "configuration": {"layers": LAYERS, "d_model": D_MODEL, "Hq": H_Q,
                                "Hkv": H_KV, "head_dim": D_HEAD, "vocab": VOCAB,
                                "seed": 20261011, "normalization": "per-token pre-LayerNorm + final LayerNorm",
                                "position": "absolute sinusoidal; positions start at 0", "dropout": False},
              "prompt": PROMPT, "forced_continuation": FORCED_CONTINUATION,
              "tolerance": TOLERANCE, "incremental_steps": steps,
              "chunked_append": {"old_cache_len": 3, "query_len": 2, "key_len": 5,
                                 "absolute_positions": [3, 4], "mask": correct_mask,
                                 "max_logit_difference": chunk_difference,
                                 "old_KV_invariant": old_cache_unchanged(prefix_cache, chunk_cache)},
              "logical_counts": {"definition": "Five forward observations: lengths 3,4,5,6,7; counts aggregated across two layers and two query heads; not elapsed time, FLOPs, physical bytes, or kernel benchmark.",
                                 "projected_rows_per_Q_K_V_note": "Sum over layers; each Q/K/V separately has this many token rows.",
                                 "full_prefix_recompute": sum_counts(reference_counts),
                                 "incremental_cache": sum_counts(cached_counts)},
              "negative_examples": negatives,
              "scalar_attention_example": {"scope": "local one-head attention, head_dim=1; separate parameters from decoder",
                                           "q": math.log(2), "K": [1, 0, 1], "V": [2, 6, 10],
                                           "all_weights": probabilities, "all_output": scalar_output,
                                           "old_two_weights": old_probabilities, "old_two_output": old_output},
              "capacity_formula": "2 * L * B * T * Hkv * dh * bytes_per_element",
              "capacities": capacities, "all_checks_passed": True}
    teacher_run = OUTPUT / "teacher-run"
    teacher_run.mkdir(parents=True, exist_ok=True)
    (teacher_run / "checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_lines = ["Transformer KV Cache teacher preparation r1; standard library; two-layer fixed toy.",
                    "Prefill length 3: final logits predict position 3; forced token 5 at position 3 is not yet cached."]
    for step in steps:
        output_lines.append(f"{step['phase']}: cache_lengths={step['cache_lengths']}, logits_diff={step['max_logit_difference']:.3e}, old_KV_invariant={step['old_KV_invariant']}")
    output_lines.append(f"Chunk q_len=2, old_cache=3: mask={correct_mask}, logits_diff={chunk_difference:.3e}.")
    output_lines.append("Logical counts: " + json.dumps(result["logical_counts"], ensure_ascii=False))
    output_lines.append("Fixed-input negative examples: " + json.dumps(negatives, ensure_ascii=False))
    output_lines.append(f"Scalar example: weights={probabilities}, output={scalar_output}; old-only output={old_output}.")
    output_lines.append("Capacity GiB: " + json.dumps(capacities))
    output_lines.append("All checks passed. Teacher run only; no learning progress changed.")
    stdout = "\n".join(output_lines) + "\n"
    (teacher_run / "stdout.txt").write_text(stdout, encoding="utf-8")
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["phase", "cache_lengths", "max_logit_difference", "old_KV_invariant", "next_predict_position"])
    for step in steps:
        writer.writerow([step["phase"], str(step["cache_lengths"]), step["max_logit_difference"], step["old_KV_invariant"], step["last_logits_predict_position"]])
    (teacher_run / "trace.csv").write_text(csv_buffer.getvalue(), encoding="utf-8")
    make_figures(OUTPUT / "figures")
    read_back = json.loads((teacher_run / "checks.json").read_text(encoding="utf-8"))
    assert read_back == result
    assert (teacher_run / "stdout.txt").read_text(encoding="utf-8") == stdout
    print(stdout, end="")


if __name__ == "__main__":
    if sys.argv[1:] == ["--refresh-cache-timeline"]:
        make_figures(OUTPUT / "figures", selected={"cache-timeline"})
        print("Refreshed cache-timeline.svg only; mechanism results unchanged.")
    else:
        main()
