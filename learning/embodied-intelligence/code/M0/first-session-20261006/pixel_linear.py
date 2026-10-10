"""AI teaching example, revision1, 2026-10-06.
v: floating RGB video tensor [B,C,T,H,W], C=3.
W uses [input_feature, output_feature] for this handwritten matmul.
Output [B,T,H,W,D], D=2; same shared matrix at every pixel.
Fixed teaching weights, not trained parameters; no spatial/temporal mixing.
Source checked: PyTorch2.14 torch.matmul documentation.
No learner implementation or PyTorch runtime execution is claimed.
"""


def pixel_features(v):
    pixels = v.permute(0, 2, 3, 4, 1)
    W = pixels.new_tensor([[1.0, 0.0],
                           [0.0, 1.0],
                           [1.0, 1.0]])
    features = pixels @ W
    return features
