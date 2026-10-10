shape = (2, 8, 3, 32, 32)  # B, T, C, H, W

total = 1
for size in shape:
    total = total * size

print("shape:", shape)
print("total:", total)

print("len(shape):", len(shape))

import torch

x = torch.tensor([[10, 11, 12],   # 第一帧
                  [20, 21, 22]]) # 第二帧

print("reshape:", torch.reshape(x, (3, 2)))
print("permute:", torch.permute(x, (1, 0)))