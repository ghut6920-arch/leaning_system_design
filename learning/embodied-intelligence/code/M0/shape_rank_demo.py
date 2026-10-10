shape = (2, 8, 3, 32, 32)  # B, T, C, H, W

total = 1
for size in shape:
    total = total * size

print("shape:", shape)
print("total:", total)
print("len(shape):", len(shape))
