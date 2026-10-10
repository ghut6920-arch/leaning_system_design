"""AI teacher reference, revision 1, 2026-10-08.

Origin: explicit teaching contract in this preparation's materials.md.
Contributor: Codex single model. No learner code or learner execution.
Standard library only. This checks finite example semantics, not PyTorch
runtime, visual-model performance, or learning outcomes.
"""
import argparse
import itertools
import json
import math
import platform
from pathlib import Path

RGB = ((11, 12, 13), (21, 22, 23), (11, 12, 99), (41, 42, 43),
       (51, 52, 53), (61, 62, 63), (71, 72, 73), (81, 82, 83))
B, T, C, H, W, D = 2, 4, 3, 2, 2, 2
PERMUTATION = (5, 2, 7, 0, 6, 3, 1, 4)


def indices(shape):
    return itertools.product(*(range(size) for size in shape))


def offset(shape, coordinate):
    result = 0
    for size, index in zip(shape, coordinate, strict=True):
        if not 0 <= index < size:
            raise IndexError(coordinate)
        result = result * size + index
    return result


class Tensor:
    def __init__(self, shape, values):
        self.shape = tuple(shape)
        self.values = tuple(values)
        if math.prod(self.shape) != len(self.values):
            raise ValueError("element count")

    def at(self, *coordinate):
        return self.values[offset(self.shape, coordinate)]

    def reshape(self, shape):
        return Tensor(shape, self.values)

    def permute(self, axes):
        if sorted(axes) != list(range(len(self.shape))):
            raise ValueError("axes")
        new_shape = tuple(self.shape[axis] for axis in axes)
        values = []
        for new_coordinate in indices(new_shape):
            old_coordinate = [0] * len(axes)
            for axis, index in zip(axes, new_coordinate, strict=True):
                old_coordinate[axis] = index
            values.append(self.at(*old_coordinate))
        return Tensor(new_shape, values)


def make_input():
    shape = (B, T, H, W, C)
    return Tensor(shape, (RGB[b * T + t][c] + 100 * h + 10 * w
                          for b, t, h, w, c in indices(shape)))


def encode(frames):
    # No shuffle, no cross-frame mixing, no blue or other spatial positions.
    return [tuple(frames.at(k, c, 0, 0) for c in (0, 1))
            for k in range(B * T)]


def restore_by_order(rows, *, order_verified):
    if not order_verified:
        raise ValueError("missing order correspondence")
    if len(rows) != B * T or any(len(row) != D for row in rows):
        raise ValueError("incomplete rows or feature length")
    return [list(rows[b * T:(b + 1) * T]) for b in range(B)]


def restore_by_labels(rows, labels):
    if len(rows) != B * T or len(labels) != B * T:
        raise ValueError("incomplete records")
    if any(len(row) != D for row in rows):
        raise ValueError("feature length")
    expected = set(indices((B, T)))
    if len(set(labels)) != B * T or set(labels) != expected:
        raise ValueError("labels must cover every target exactly once")
    sequence = [[None] * T for _ in range(B)]
    for row, (b, t) in zip(rows, labels, strict=True):
        sequence[b][t] = row
    return sequence


def check_rejected(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except ValueError:
        return
    raise AssertionError("expected contract rejection")


def run_checks():
    passed = []
    x = make_input()
    y = x.permute((0, 4, 1, 2, 3))
    a = x.permute((0, 1, 4, 2, 3))
    z = a.reshape((B * T, C, H, W))
    alternate = x.reshape((B * T, H, W, C)).permute((0, 3, 1, 2))
    for b, t, h, w, c in indices(x.shape):
        original = x.at(b, t, h, w, c)
        assert y.at(b, c, t, h, w) == original
        assert z.at(b * T + t, c, h, w) == original
    assert z.values == alternate.values
    passed.append("all_96_pixel_correspondences_and_equivalent_routes")

    wrong = x.reshape((B * T, C, H, W))
    assert wrong.at(0, 1, 0, 0) == 22
    assert z.at(0, 1, 0, 0) == 12
    passed.append("shape_legal_direct_reshape_violates_color_correspondence")

    assert x.at(1, 2, 0, 0, 1) == y.at(1, 1, 2, 0, 0) == z.at(6, 1, 0, 0) == 72
    passed.append("worked_pixel_trace_72")

    f = encode(z)
    expected_f = [(11, 12), (21, 22), (11, 12), (41, 42),
                  (51, 52), (61, 62), (71, 72), (81, 82)]
    assert f == expected_f
    assert all(len(tensor.values) == 96 for tensor in (x, y, a, z))
    assert sum(map(len, f)) == 16
    passed.append("eight_feature_rows_and_96_to_16_only_at_encoder")

    assert RGB[0] != RGB[2] and f[0] == f[2]
    passed.append("different_blue_same_features_noninjective_example")

    sequence = restore_by_order(f, order_verified=True)
    assert sequence == [expected_f[:4], expected_f[4:]]
    passed.append("ordered_recovery_without_labels")

    labels = list(indices((B, T)))
    swap = (1, 0, 2, 3, 4, 5, 6, 7)
    swap_rows = [f[k] for k in swap]
    swap_labels = [labels[k] for k in swap]
    assert restore_by_labels(swap_rows, swap_labels) == sequence
    assert restore_by_order(swap_rows, order_verified=True) != sequence
    passed.append("two_row_swap_changes_order_not_feature_content")

    # The same swap can act on full images before encoding, preserving pixels.
    original_images = [tuple(z.at(k, c, h, w) for c, h, w in indices((C, H, W)))
                       for k in range(B * T)]
    swapped_images = [original_images[k] for k in swap]
    assert sorted(swapped_images) == sorted(original_images)
    assert all(len(image) == 12 for image in swapped_images)
    passed.append("row_swap_without_encoding_preserves_all_image_components")

    shuffled = [f[k] for k in PERMUTATION]
    shuffled_labels = [labels[k] for k in PERMUTATION]
    assert restore_by_labels(shuffled, shuffled_labels) == sequence
    row_orders = [[shuffled_labels.index((b, t)) for t in range(T)] for b in range(B)]
    assert row_orders == [[3, 6, 1, 5], [7, 0, 4, 2]]
    passed.append("record_B_all_eight_rows_and_teacher_row_orders")

    assert restore_by_order(shuffled, order_verified=True) != sequence
    passed.append("record_B_direct_reshape_is_not_correct_source_order")

    duplicate = list(shuffled_labels)
    duplicate[0] = duplicate[1]
    out_of_range = list(shuffled_labels)
    out_of_range[0] = (B, 0)
    check_rejected(restore_by_labels, shuffled, duplicate)
    check_rejected(restore_by_labels, shuffled, out_of_range)
    check_rejected(restore_by_labels, shuffled[:-1], shuffled_labels[:-1])
    passed.append("duplicate_out_of_range_and_missing_labels_rejected")

    check_rejected(restore_by_order, shuffled, order_verified=False)
    passed.append("unknown_order_not_assumed_correct_or_incorrect")

    alternative_labels = list(shuffled_labels)
    alternative_labels[1], alternative_labels[3] = alternative_labels[3], alternative_labels[1]
    assert shuffled[1] == shuffled[3] == (11, 12)
    assert alternative_labels != shuffled_labels
    assert restore_by_labels(shuffled, alternative_labels) == sequence
    passed.append("same_visible_values_two_possible_row_origins_numeric_result_can_match")

    return {
        "artifact_revision": 1,
        "status": "teacher_reference_checked",
        "executor": "single_model_teacher",
        "independent_review": False,
        "python_version": platform.python_version(),
        "checks_passed": len(passed),
        "checks": passed,
        "permuted_rows": shuffled,
        "target_row_orders": row_orders,
        "limitations": ["finite explicit toy contract only", "PyTorch runtime not executed",
                        "no learner execution or ability judgment", "no real model or robot experiment"]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_checks()
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
