"""AI teaching example, revision1, 2026-10-06.
y: floating RGB tensor [B,T,C,H,W], C=3, already scaled to [0,1].
baseline/scale are explicit teaching parameters, not measured dataset stats.
PyTorch2.14 broadcasting and new_tensor specifications were checked.
No learner implementation or PyTorch runtime validation is claimed.
"""


def channel_shift_scale(y):
    baseline = y.new_tensor([0.5, 0.25, 0.75]).reshape(1, 1, 3, 1, 1)
    scale = y.new_tensor([0.25, 0.5, 0.25]).reshape(1, 1, 3, 1, 1)
    z = (y - baseline) / scale
    return z
