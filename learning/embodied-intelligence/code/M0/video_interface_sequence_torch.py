"""Optional PyTorch teacher reference; runtime availability checked separately.

API source: PyTorch 2.14 permute/reshape docs verified during maintenance.
Values are toy labels; no training, real camera, learner run or model effect.
"""


def bridge(camera):
    b, t, h, w, c = camera.shape  # Explicit contract: B,T,H,W,C
    if c < 2:
        raise ValueError("This toy encoder needs two channels")
    video = camera.permute(0, 4, 1, 2, 3)
    frames = camera.permute(0, 1, 4, 2, 3).reshape(b * t, c, h, w)
    features = frames[:, :2, 0, 0]  # ND, D=2; row order unchanged
    sequence = features.reshape(b, t, 2)  # Only valid under the stated row-order contract
    return video, frames, features, sequence


if __name__ == "__main__":
    import torch
    camera = torch.arange(96).reshape(2, 4, 2, 2, 3)
    for name, value in zip(["video", "frames", "features", "sequence"], bridge(camera)):
        print(name, list(value.shape), value.tolist() if name == "sequence" else "")
