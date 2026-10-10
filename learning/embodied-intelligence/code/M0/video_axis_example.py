"""AI demonstration, revision 1. Input x is a 5-D PyTorch tensor [B,T,C,H,W].
No learner implementation or execution is claimed.
"""
import torch


def time_channels_to_channels_time(x):
    # Output axes: [B,C,T,H,W], preserving each value's frame/channel identity.
    y = torch.permute(x, (0, 2, 1, 3, 4))
    return y