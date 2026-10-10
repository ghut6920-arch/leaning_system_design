"""AI teaching example, revision1, 2026-10-06.
Precondition: camera is a PyTorch RGB uint8 tensor [B,T,H,W,C],
C=3. Target: float32 [B,C,T,H,W], values in [0,1].
This is a specified teaching interface, not a universal model layout.
Sources: PyTorch 2.14 Tensor.float, permute and Tensor indexing docs.
No learner execution or PyTorch runtime validation is claimed.
"""


def prepare_video(camera):
    x = camera.permute(0, 4, 1, 2, 3)
    x = x.float() / 255.0
    return x


def inspect_video(camera):
    x = prepare_video(camera)
    frame = x[0, :, 2, :, :]
    rgb = frame[:, 10, 20]
    return x, frame, rgb
