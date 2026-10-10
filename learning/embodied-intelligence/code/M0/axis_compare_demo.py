import torch

# 两帧，每帧三个通道；每个通道只保留一个代表数值。
x = torch.tensor([[10, 11, 12],
                  [20, 21, 22]])  # [T, C]

print("reshape:", torch.reshape(x, (3, 2)))
print("permute:", torch.permute(x, (1, 0)))