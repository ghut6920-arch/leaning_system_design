"""AI correction snippet, revision1, 2026-10-06.
Precondition: camera is the specified RGB uint8 PyTorch tensor
[B,T,H,W,C]=[2,6,64,64,3], values 0..255.
Target [B,T,C,H,W] float32 values 0..1.
Source: current lesson, PyTorch2.14 permute/float/indexing specifications.
This snippet needs an existing camera tensor; runtime not executed.
Learner original remains in submissions/preprocess-001-initial.py.
"""
y = camera.permute(0, 1, 4, 2, 3).float() / 255.0  # [2,6,3,64,64]
frame = y[1, 4, :, :, :]                         # [3,64,64]
rgb = frame[:, 10, 20]                           # [3]
