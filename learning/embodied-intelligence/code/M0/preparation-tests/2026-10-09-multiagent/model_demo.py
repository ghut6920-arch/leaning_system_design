"""AI teacher demonstration v1; preparation only, not learner code or execution.

Python standard-library audit of a didactic video-interface example.
This is an index/value model, not an implementation of PyTorch storage/strides.
No real camera data, learned network, training or robot execution is involved.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import platform
from pathlib import Path


VERSION = "2026-10-09-model-demo-v1"
SOURCE_SHAPE = (2, 4, 2, 2, 3)  # B,T,H,W,C; original unit specification
VIDEO_SHAPE = (2, 3, 4, 2, 2)  # B,C,T,H,W
FRAME_SHAPE = (8, 3, 2, 2)  # N,C,H,W
BACKGROUND = (2, 3, 5)
BLOCK = (80, 20, 10)
GRIPPER = (10, 70, 90)
EPISODE_NAMES = ("甲", "乙")
# Each item is (block_position, gripper_position); p = 2*h+w.
POSITIONS = (
    ((0, 2), (0, 1), (1, 3), (3, 2)),
    ((3, 2), (3, 0), (1, 3), (0, 2)),
)
# Processing row j comes from these original (b,t) identities.
QUEUE_LABELS = ((1, 2), (0, 0), (1, 0), (0, 3), (0, 1), (1, 3), (0, 2), (1, 1))


def indices(shape):
    return itertools.product(*(range(size) for size in shape))


def make_source():
    result = {}
    for b, t, h, w, c in indices(SOURCE_SHAPE):
        block, gripper = POSITIONS[b][t]
        p = 2 * h + w
        rgb = BLOCK if p == block else GRIPPER if p == gripper else BACKGROUND
        result[b, t, h, w, c] = rgb[c]
    return result


def permute(data, shape, axes):
    if sorted(axes) != list(range(len(shape))):
        raise ValueError("axes must be a permutation")
    new_shape = tuple(shape[axis] for axis in axes)
    return {tuple(old[axis] for axis in axes): data[old] for old in indices(shape)}, new_shape


def reshape(data, shape, new_shape):
    if math.prod(shape) != math.prod(new_shape):
        raise ValueError("element count differs")
    values = (data[index] for index in indices(shape))
    return dict(zip(indices(new_shape), values))


def encode_left_rg(frames):
    """Same f for each frame: retain upper-left R,G only; D=2."""
    return [
        [frames[n, c, 0, 0] for c in (0, 1)]
        for n in range(8)
    ]


def restore_by_labels(rows, labels, b_count=2, t_count=4):
    if len(rows) != b_count * t_count or len(labels) != len(rows):
        raise ValueError("one output row and one source label per expected frame required")
    expected = set(indices((b_count, t_count)))
    if any(not isinstance(label, tuple) or len(label) != 2 for label in labels):
        raise ValueError("malformed source label")
    if set(labels) != expected or len(set(labels)) != len(labels):
        raise ValueError("source labels must cover every expected (b,t) exactly once")
    result = [[None for _ in range(t_count)] for _ in range(b_count)]
    for row, (b, t) in zip(rows, labels):
        result[b][t] = list(row)
    return result


def run_audit():
    source = make_source()
    video, video_shape = permute(source, SOURCE_SHAPE, (0, 4, 1, 2, 3))
    btchw, btchw_shape = permute(source, SOURCE_SHAPE, (0, 1, 4, 2, 3))
    frames = reshape(btchw, btchw_shape, FRAME_SHAPE)
    encoded = encode_left_rg(frames)
    sequence = [encoded[4 * b : 4 * b + 4] for b in range(2)]
    queue = [encoded[4 * b + t] for b, t in QUEUE_LABELS]
    restored = restore_by_labels(queue, QUEUE_LABELS)
    wrong_video = reshape(source, SOURCE_SHAPE, VIDEO_SHAPE)

    checks = []

    def check(name, condition, detail):
        if not condition:
            raise AssertionError(name)
        checks.append({"name": name, "passed": True, "detail": detail})

    check("source_full_spec", len(source) == 96 and len(encoded) == 8 and all(len(row) == 2 for row in encoded), "96 RGB scalars; 8 feature rows, D=2")
    check("video_all_pixel_mappings", video_shape == VIDEO_SHAPE and all(video[b, c, t, h, w] == source[b, t, h, w, c] for b, t, h, w, c in indices(SOURCE_SHAPE)), "all 96 index/value equalities")
    check("frame_all_pixel_mappings", all(frames[4*b+t, c, h, w] == source[b, t, h, w, c] for b, t, h, w, c in indices(SOURCE_SHAPE)), "all 96 equalities, n=4*b+t")
    inverse_video, inverse_shape = permute(video, VIDEO_SHAPE, (0, 2, 3, 4, 1))
    check("video_inverse", inverse_shape == SOURCE_SHAPE and inverse_video == source, "inverse axes (0,2,3,4,1)")
    inverse_btchw = reshape(frames, FRAME_SHAPE, btchw_shape)
    inverse_frames, inverse_frame_shape = permute(inverse_btchw, btchw_shape, (0, 1, 3, 4, 2))
    check("frame_inverse_with_metadata", inverse_frame_shape == SOURCE_SHAPE and inverse_frames == source, "requires B=2,T=4 and n=4*b+t")
    check("reshape_shape_is_not_semantics", wrong_video[0, 1, 0, 0, 0] == 70 and video[0, 1, 0, 0, 0] == 20, "same (2,3,4,2,2) shape; expected green=20, incorrect reshape gives 70")
    check("all_rg_feature_mappings", all(encoded[4*b+t][c] == source[b,t,0,0,c] for b in range(2) for t in range(4) for c in (0,1)), "all 16 retained upper-left R/G equalities; d=0:R00, d=1:G00")
    check("ordered_feature_sequence", sequence[1][2] == encoded[6] and sequence == restored, "Z[b,t,d]=E[4*b+t,d], same as trusted-label recovery")
    naive_shuffled = [queue[4*b:4*b+4] for b in range(2)]
    check("shuffled_reshape_fails", naive_shuffled != sequence and naive_shuffled[0][0] == sequence[1][2], "blind grouping puts 乙2 into 甲0 slot")
    check("same_content_not_source_id", encoded[2] == encoded[6] and encoded[0] == encoded[7], "甲2/乙2 and 甲0/乙3 have equal feature values but different source identities")
    check("other_pixels_not_retained", encoded[0] == encoded[1] and any(source[0,0,h,w,c] != source[0,1,h,w,c] for h in range(2) for w in range(2) for c in range(3)), "甲0/甲1 differ outside upper-left pixel but have the same f output")
    altered = dict(source)
    altered[0,0,0,0,2] = 11  # Upper-left blue changes: 10 -> 11.
    alt_btchw, alt_shape = permute(altered, SOURCE_SHAPE, (0,1,4,2,3))
    alt_frames = reshape(alt_btchw, alt_shape, FRAME_SHAPE)
    check("blue_collision_noninjective", altered != source and encode_left_rg(alt_frames) == encoded, "different source RGB arrays (one upper-left blue value 10 vs 11), exactly equal A; f cannot uniquely restore RGB on this allowed domain")

    invalid_cases = [
        ("missing_label", QUEUE_LABELS[:-1]),
        ("duplicate_label", QUEUE_LABELS[:-1] + (QUEUE_LABELS[0],)),
        ("out_of_range_label", QUEUE_LABELS[:-1] + ((2,0),)),
    ]
    for name, invalid_labels in invalid_cases:
        try:
            restore_by_labels(queue, invalid_labels)
        except ValueError:
            check(name + "_rejected", True, "ValueError raised before restoration")
        else:
            raise AssertionError(name)

    # Swap two distinct, internally legal labels; coverage still appears complete.
    lying_labels = list(QUEUE_LABELS)
    lying_labels[0], lying_labels[1] = lying_labels[1], lying_labels[0]
    lying_result = restore_by_labels(queue, tuple(lying_labels))
    check("label_coverage_does_not_prove_truth", lying_result != sequence, "swapped source labels pass coverage validation but restore incorrectly; trusted lineage is an external precondition")

    rgb_frames = [
        {"b": b, "t": t, "name": EPISODE_NAMES[b] + str(t), "rgb_grid": [[tuple(source[b,t,h,w,c] for c in range(3)) for w in range(2)] for h in range(2)], "feature_rg": encoded[4*b+t]}
        for b in range(2) for t in range(4)
    ]
    code_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return {
        "version": VERSION,
        "purpose": "AI teacher preparation audit; not learner performance or execution",
        "python_version": platform.python_version(),
        "code_sha256": code_hash,
        "spec": {"X_BTHWC": SOURCE_SHAPE, "V_BCTHW": VIDEO_SHAPE, "J_NCHW": FRAME_SHAPE, "A_ND": (8,2), "S_BTD": (2,4,2)},
        "frames": rgb_frames,
        "queue": [{"j":j,"source_label":label,"name":EPISODE_NAMES[label[0]]+str(label[1]),"feature_rg":queue[j]} for j,label in enumerate(QUEUE_LABELS)],
        "collision": {"source_index": [0,0,0,0,2], "original_blue":10,"altered_blue":11,"equal_features":True},
        "checks": checks,
        "passed_count": len(checks),
        "limitations": ["PyTorch API checked against official 2.14 documentation; no PyTorch runtime executed", "finite full-input mapping audit, not a proof of arbitrary software implementations", "toy encoder and artificial RGB grids, not learned features or real robot observations", "restoration requires trustworthy per-output source identity, one result per input, known expected frame set and feature convention"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-output", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    audit = run_audit()
    if args.check_output:
        args.check_output.parent.mkdir(parents=True, exist_ok=True)
        args.check_output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    else:
        print(VERSION)
        print("teacher checks passed:", audit["passed_count"])
        for frame in audit["frames"]:
            print(frame["name"], "feature:", frame["feature_rg"])
        print("incorrect reshape witness: expected green=20, got=70")
        print("blue collision: X[0,0,0,0,2] is 10 vs 11; all features equal")


if __name__ == "__main__":
    main()
