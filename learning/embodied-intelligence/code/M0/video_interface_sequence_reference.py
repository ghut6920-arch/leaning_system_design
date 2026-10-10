"""AI teaching reference: BTHWC -> BCTHW / NCHW -> ND -> BTD.

Standard-library example, not learner code or a trained visual/world model.
Toy values and features are supplied to check identity and metadata conditions.
"""
from dataclasses import dataclass
import json


@dataclass(frozen=True)
class Spec:
    batch: int = 2
    time: int = 4
    height: int = 2
    width: int = 2
    channels: int = 3

    def __post_init__(self):
        if any(type(x) is not int or x < 1 for x in vars(self).values()):
            raise ValueError("Axis lengths must be positive integers")


def make_camera(spec):
    # B,T,H,W,C; distinct integer labels for this teaching input only.
    return [[[[[(b * spec.time + t) * spec.height * spec.width * spec.channels
                + (h * spec.width + w) * spec.channels + c
                for c in range(spec.channels)] for w in range(spec.width)]
              for h in range(spec.height)] for t in range(spec.time)]
            for b in range(spec.batch)]


def to_video(camera, spec):
    # Read original roles, then give the consumer B,C,T,H,W.
    return [[[[[camera[b][t][h][w][c] for w in range(spec.width)]
               for h in range(spec.height)] for t in range(spec.time)]
             for c in range(spec.channels)] for b in range(spec.batch)]


def to_frames(camera, spec):
    # N,C,H,W; row k=b*T+t, metadata retained separately.
    frames, frame_ids = [], []
    for b in range(spec.batch):
        for t in range(spec.time):
            frames.append([[[camera[b][t][h][w][c] for w in range(spec.width)]
                            for h in range(spec.height)] for c in range(spec.channels)])
            frame_ids.append((b, t))
    return frames, frame_ids


def toy_encode(frames):
    # D=2: two values from each frame, no row mixing or row reordering.
    # This is a specified toy function, not learned semantic features.
    if any(len(frame) < 2 for frame in frames):
        raise ValueError("This specified toy encoder requires two channels")
    return [[frame[0][0][0], frame[1][0][0]] for frame in frames]


def restore_sequence(features, batch, time, *, order_confirmed=False, frame_ids=None):
    if type(batch) is not int or type(time) is not int or batch < 1 or time < 1:
        raise ValueError("Known positive B and T are required")
    if len(features) != batch * time or not features or not features[0]:
        raise ValueError("Feature row count must equal B*T, and D must be positive")
    depth = len(features[0])
    if any(len(row) != depth for row in features):
        raise ValueError("Every row must have the same D")
    if frame_ids is None:
        if order_confirmed is not True:
            raise ValueError("Need confirmed b-major/t-minor row order or trustworthy frame IDs")
        frame_ids = [(b, t) for b in range(batch) for t in range(time)]
    expected = {(b, t) for b in range(batch) for t in range(time)}
    if (len(frame_ids) != len(features)
            or any(not isinstance(item, (tuple, list)) or len(item) != 2
                   or any(type(x) is not int for x in item) for item in frame_ids)):
        raise ValueError("Each row needs one integer (b,t) ID")
    identities = [tuple(item) for item in frame_ids]
    if set(identities) != expected or len(set(identities)) != len(identities):
        raise ValueError("IDs must cover every frame once; no missing/duplicate/out-of-range frames")
    result = [[None for _ in range(time)] for _ in range(batch)]
    for row, (b, t) in zip(features, identities):
        result[b][t] = list(row)
    return result


def demo():
    spec = Spec()
    camera = make_camera(spec)
    video = to_video(camera, spec)
    frames, frame_ids = to_frames(camera, spec)
    features = toy_encode(frames)
    sequence = restore_sequence(features, spec.batch, spec.time, order_confirmed=True)
    return {"camera_shape": [2,4,2,2,3], "video_shape": [2,3,4,2,2],
            "frames_shape": [8,3,2,2], "features_shape": [8,2], "sequence_shape": [2,4,2],
            "frame_ids": frame_ids, "features": features, "sequence": sequence,
            "video_identity_example": video[1][1][2][0][0],
            "teacher_reference_only": True, "trained_encoder": False}


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
