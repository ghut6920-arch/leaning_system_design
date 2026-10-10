"""Check teaching reference content only; all data and code are synthetic.

This probe is not a teaching agent or a learning-efficacy test. No personal
records, program contracts, or source fingerprints are modified.
"""
from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path


def original_locate(values, target):
    lo, hi = 0, len(values)
    while lo <= hi:
        mid = (lo + hi) // 2
        if values[mid] == target:
            return mid
        if values[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def reference_locate(values, target):
    lo, hi = 0, len(values) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if values[mid] == target:
            return mid
        if values[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def main():
    frames = [
        [[10, 20, 30], [11, 21, 31]],
        [[40, 50, 60], [41, 51, 61]],
    ]
    channel_rows = [
        [[pixel[c] for pixel in frame] for c in range(3)]
        for frame in frames
    ]
    mapping_checks = 0
    for t in range(2):
        for w in range(2):
            for c in range(3):
                assert channel_rows[t][c][w] == frames[t][w][c]
                mapping_checks += 1
    flat = [value for pixel in frames[0] for value in pixel]
    reshape_channel_rows = [flat[i:i + 2] for i in range(0, 6, 2)]
    assert channel_rows[0][0] == [10, 11]
    assert reshape_channel_rows[0] == [10, 20]
    assert channel_rows[1][1][1] == 51

    q_values = [Fraction(1, 5), Fraction(6, 5), Fraction(2), Fraction(11, 5)]
    trajectories = {}
    for q in q_values:
        e = Fraction(1)
        values = [e]
        for _ in range(5):
            e *= 1 - q
            values.append(e)
        trajectories[str(q)] = [str(value) for value in values]
        if 0 < q < 1:
            assert all(value > 0 for value in values)
            assert all(abs(values[i + 1]) < abs(values[i]) for i in range(5))
        elif 1 < q < 2:
            assert all(values[i] * values[i + 1] < 0 for i in range(5))
            assert all(abs(values[i + 1]) < abs(values[i]) for i in range(5))
        elif q == 2:
            assert all(abs(value) == 1 for value in values)
        else:
            assert all(values[i] * values[i + 1] < 0 for i in range(5))
            assert all(abs(values[i + 1]) > abs(values[i]) for i in range(5))

    assert Fraction(3 * 6 + 2 * 9, 3 + 2) == Fraction(36, 5)
    assert Fraction(3 * 6 + 4 * 9, 3 + 4) == Fraction(54, 7)
    assert original_locate([1, 3, 5], 3) == 1
    observed_errors = []
    for values, target in [([], 1), ([1, 3, 5], 6)]:
        try:
            original_locate(values, target)
        except IndexError:
            observed_errors.append({"values": values, "target": target, "error": "IndexError"})
        else:
            raise AssertionError("Expected supplied code to expose its invalid upper bound")

    search_checks = 0
    for size in range(7):
        values = list(range(1, size * 2 + 1, 2))
        for target in range(0, size * 2 + 1):
            expected = values.index(target) if target in values else -1
            assert reference_locate(values, target) == expected
            search_checks += 1

    report = {
        "executed_on": "2026-10-04",
        "synthetic_only": True,
        "status": "passed",
        "tensor_value_mapping_checks": mapping_checks,
        "reshape_counterexample": {"correct_red": channel_rows[0][0], "direct_reshape_red": reshape_channel_rows[0]},
        "dynamic_trajectories": trajectories,
        "weighted_mean_original": "36/5",
        "weighted_mean_variation": "54/7",
        "supplied_binary_search_errors": observed_errors,
        "reference_binary_search_checks": search_checks,
        "limitations": [
            "Finite synthetic arithmetic and program behavior only; no learner event or learning-effect conclusion.",
            "General recurrence limits require the stated mathematical argument, not these finite trajectories.",
            "Search enumeration covers length 0..6 strictly increasing lists; it is not a proof for all inputs.",
            "The executing model is also the modifier; no independent forward validation occurred.",
        ],
    }
    destination = Path(__file__).with_name("reference-probe-result.json")
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
