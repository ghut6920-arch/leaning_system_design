"""AI-authored teacher reference, revision 1, 2026-10-08.

Teaching-assumption data; no learner work or real video/model experiment.
Specs: sibling artifacts/preparation-tests/2026-10-08-video-interface-independent-02.
Standard-library row-major reference; optional torch comparison, no installation.
Prints verification JSON; does not write learning records.
"""

from dataclasses import dataclass
from itertools import product
from math import prod
import importlib.util
import json
import platform


@dataclass(frozen=True)
class Tensor:
    shape: tuple[int, ...]
    data: tuple[int, ...]

    def __post_init__(self):
        if prod(self.shape) != len(self.data):
            raise ValueError("element count")

    def at(self, *index):
        if len(index) != len(self.shape):
            raise ValueError("index rank")
        offset = 0
        for size, coordinate in zip(self.shape, index):
            if not 0 <= coordinate < size:
                raise IndexError(index)
            offset = offset * size + coordinate
        return self.data[offset]

    def reshape(self, *shape):
        return Tensor(tuple(shape), self.data)

    def permute(self, *axes):
        if sorted(axes) != list(range(len(self.shape))):
            raise ValueError("axis permutation")
        new_shape = tuple(self.shape[axis] for axis in axes)
        values = []
        for new_index in product(*(range(s) for s in new_shape)):
            old_index = [0] * len(axes)
            for new_axis, old_axis in enumerate(axes):
                old_index[old_axis] = new_index[new_axis]
            values.append(self.at(*old_index))
        return Tensor(new_shape, tuple(values))


TOP = (
    ((11, 12, 13), (21, 22, 23), (31, 32, 33), (41, 42, 43)),
    ((31, 32, 113), (11, 12, 123), (41, 42, 133), (21, 22, 143)),
)
ORDER = (5, 2, 7, 0, 6, 1, 4, 3)


def camera():
    return Tensor((2, 4, 2, 2, 3), tuple(
        TOP[b][t][c] + 5*h + 3*w
        for b, t, h, w, c in product(range(2), range(4), range(2), range(2), range(3))
    ))


def frame_input(x):
    return x.permute(0, 1, 4, 2, 3).reshape(8, 3, 2, 2)


def encode(i):
    return Tensor((8, 2), tuple(i.at(n, d, 0, 0) for n in range(8) for d in range(2)))


def tagged_restore(rows, tags):
    expected = {("batch-Q", b, t) for b in range(2) for t in range(4)}
    if len(rows) != 8 or len(tags) != 8 or len(set(tags)) != 8 or set(tags) != expected:
        raise ValueError("batch, coverage or unique-source condition")
    if any(len(row) != 2 for row in rows):
        raise ValueError("feature width")
    destination = [None] * 8
    for row, (_, b, t) in zip(rows, tags):
        destination[4*b+t] = tuple(row)
    return Tensor((2, 4, 2), tuple(value for row in destination for value in row))


def red_difference(u):
    return [u.at(b, 3, 0) - u.at(b, 0, 0) for b in range(2)]


def check_all():
    checks = []

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append({"name": name, "status": "passed"})

    def rejects(name, rows, tags):
        try:
            tagged_restore(rows, tags)
        except ValueError:
            check(name, True)
        else:
            check(name, False)

    x = camera()
    y = x.permute(0, 4, 1, 2, 3)
    i = frame_input(x)
    f = encode(i)
    u = f.reshape(2, 4, 2)
    coordinates = list(product(range(2), range(4), range(2), range(2), range(3)))
    check("all_96_video_coordinates", all(
        y.at(b, c, t, h, w) == x.at(b, t, h, w, c)
        for b, t, h, w, c in coordinates))
    check("all_96_frame_coordinates", all(
        i.at(4*b+t, c, h, w) == x.at(b, t, h, w, c)
        for b, t, h, w, c in coordinates))
    # Unique diagnostic coordinate IDs independently check mapping, not pixel identity inference.
    identity = Tensor(x.shape, tuple(range(96)))
    identity_i = frame_input(identity)
    check("unique_coordinate_mapping", all(
        identity_i.at(4*b+t, c, h, w) == identity.at(b, t, h, w, c)
        for b, t, h, w, c in coordinates))
    alternative = x.reshape(8, 2, 2, 3).permute(0, 3, 1, 2)
    check("equivalent_merge_first_route", alternative == i)
    check("wrong_camera_reshape_detected", x.reshape(2, 3, 4, 2, 2) != y)
    check("green_pixel_trace", x.at(0, 2, 0, 0, 1) == y.at(0, 1, 2, 0, 0) == i.at(2, 1, 0, 0) == 32)
    expected_rows = [tuple(TOP[b][t][:2]) for b in range(2) for t in range(4)]
    check("all_eight_encoded_rows", f.data == tuple(v for row in expected_rows for v in row))
    check("same_features_different_sources", expected_rows[0] == expected_rows[5] and TOP[0][0] != TOP[1][1])
    rows = [expected_rows[n] for n in ORDER]
    tags = [("batch-Q", n//4, n % 4) for n in ORDER]
    restored = tagged_restore(rows, tags)
    check("trusted_tags_restore_whole_sequence", restored == u)
    current = Tensor((8, 2), tuple(v for row in rows for v in row)).reshape(2, 4, 2)
    check("same_shape_wrong_sequence", current.shape == u.shape and current != u)
    check("ordered_consumer_result", red_difference(u) == [30, -10])
    check("wrong_order_changes_consumer", red_difference(current) == [0, 0])
    # Both assignments satisfy count/shape when the current-to-source mapping is absent.
    check("missing_mapping_is_not_identifiable", sorted(current.data) == sorted(u.data) and red_difference(current) != red_difference(u))
    changed_values = list(x.data)
    changed_values[14] = 99  # X[0,1,0,0,2], only this blue scalar changes.
    changed = Tensor(x.shape, tuple(changed_values))
    changed_f = encode(frame_input(changed))
    check("only_blue_changed", sum(a != b for a, b in zip(x.data, changed.data)) == 1 and changed.at(0, 1, 0, 0, 2) == 99)
    check("blue_counterexample_same_full_features", changed_f == f)
    blue_old = x.at(0, 1, 0, 0, 2) - x.at(0, 0, 0, 0, 2) > 50
    blue_new = changed.at(0, 1, 0, 0, 2) - changed.at(0, 0, 0, 0, 2) > 50
    check("same_features_opposite_blue_answer", not blue_old and blue_new)
    rejects("duplicate_tag_rejected", rows, tags[:7] + [tags[0]])
    rejects("missing_row_rejected", rows[:7], tags[:7])
    rejects("wrong_batch_rejected", rows, [("other", b, t) for _, b, t in tags])
    rejects("out_of_domain_tag_rejected", rows, tags[:7] + [("batch-Q", 0, 4)])
    rejects("wrong_feature_width_rejected", [(1,)] + rows[1:], tags)
    torch_result = {"status": "not_executed", "reason": "torch not installed in teacher runtime"}
    if importlib.util.find_spec("torch") is not None:
        import torch
        tx = torch.tensor(x.data).reshape(x.shape)
        ty = tx.permute(0, 4, 1, 2, 3)
        ti = tx.permute(0, 1, 4, 2, 3).reshape(8, 3, 2, 2)
        tf = ti[:, :2, 0, 0]
        check("torch_matches_paper_video", tuple(ty.reshape(-1).tolist()) == y.data)
        check("torch_matches_paper_frames", tuple(ti.reshape(-1).tolist()) == i.data)
        check("torch_matches_toy_encoding", tuple(tf.reshape(-1).tolist()) == f.data)
        torch_result = {"status": "executed", "version": torch.__version__}
    return {
        "revision": 1, "date": "2026-10-08", "executor": "same_model_teacher",
        "python_version": platform.python_version(), "torch": torch_result,
        "checks": checks, "passed": len(checks), "failed": 0,
        "correct_red_difference": red_difference(u), "wrong_red_difference": red_difference(current),
        "packet_rows": rows, "packet_tags": tags,
        "limits": "Finite teacher-reference checks; no learner run, learning-effect result or real robot/model evidence.",
    }


if __name__ == "__main__":
    print(json.dumps(check_all(), ensure_ascii=False, indent=2))
