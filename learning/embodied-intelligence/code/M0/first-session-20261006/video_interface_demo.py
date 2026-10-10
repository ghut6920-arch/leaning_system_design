"""AI teaching demonstration, revision 1, 2026-10-06.
Input convention: [B,T,C,H,W]. Artificial arange values are labels,
not real camera observations. No learner execution is claimed.
Sources checked: PyTorch 2.14 documentation for Tensor indexing,
torch.permute and torch.reshape (see lesson teacher reference).
"""
import torch


def demonstrate():
    x = torch.arange(2 * 6 * 3 * 64 * 64).reshape(2, 6, 3, 64, 64)

    # Integer indices select the first video and the third frame.
    # Each ":" retains the whole remaining axis.
    frame = x[0, 2, :, :, :]
    green = frame[1, :, :]
    pixel_rgb = frame[:, 10, 20]
    print("video batch:", tuple(x.shape))
    print("one frame:", tuple(frame.shape))
    print("green channel:", tuple(green.shape))
    print("one RGB pixel:", tuple(pixel_rgb.shape))

    # New axes refer to OLD AXIS NUMBERS, rather than axis lengths.
    y = x.permute(0, 2, 1, 3, 4)
    print("B,C,T,H,W:", tuple(y.shape))
    print("same frame values:", torch.equal(y[0, :, 2, :, :], frame))

    # Rows: frames 1 and 2; columns: R, G, B.
    tiny = torch.tensor([[101, 102, 103], [201, 202, 203]])
    print("tiny T,C:", tiny.tolist())
    print("tiny C,T via permute:", tiny.permute(1, 0).tolist())
    print("tiny reshape(3,2):", tiny.reshape(3, 2).tolist())


if __name__ == "__main__":
    demonstrate()
