"""Reviewer counterexamples for deeper M7.2 relation analysis, not lesson edits."""
from pathlib import Path
import json
import numpy as np

out = Path(__file__).resolve().parents[3] / "reviews/2026-10-10-flow-matching-relation-depth-checks.json"
mu, z = np.array([2., 0.]), np.array([-1., 1.])
rows = []
for t in [0., .25, .5, .75, 1.]:
    scale = 1-.5*t
    y = t*mu + scale*z
    velocity = mu-.5*(y-t*mu)/scale
    np.testing.assert_allclose(velocity, mu-.5*z)
    rows.append({"t": t, "coupled_path_state": y.tolist(), "velocity": velocity.tolist(), "variance_per_coordinate": scale**2})
for n in [1, 2, 4, 16]:
    y = z.copy()
    for k in range(n):
        t = k/n
        y = y + (mu-.5*(y-t*mu)/(1-.5*t))/n
    np.testing.assert_allclose(y, mu+.5*z, atol=1e-14)

j = np.array([[0., -1.], [1., 0.]])
np.testing.assert_allclose(j @ j.T, np.eye(2))
paired_mse = float(.25*np.sum((j-np.eye(2))**2)/2)
np.testing.assert_allclose(paired_mse, .5)

def a(t, sigma):
    return ((sigma*sigma+1)*t-1)/((1-t)**2+sigma*sigma*t*t)
slopes = [a(.5, s) for s in [.5, 1.]]
np.testing.assert_allclose(slopes, [-1.2, 0.])

# This weighted finite example already exists in the lesson; L1 is a proposed
# comparison. It is not an ODE proof for a discrete target distribution.
labels = np.array([[3., -2.], [-1., 2.]])
weights = np.array([.75, .25])
mean = weights @ labels
median = labels[0]
mean_l1 = float(weights @ np.abs(labels-mean).sum(1))
median_l1 = float(weights @ np.abs(labels-median).sum(1))
np.testing.assert_allclose([mean_l1, median_l1], [3., 2.])

result = {
    "status": "passed", "scope": "reviewer derivations; these comparisons are not present as learner work in the original preparation",
    "coupled_same_endpoints": {"path": rows, "conditional_label_variance": 0, "euler_exact_for_tested_steps": [1, 2, 4, 16], "qualification": "affine Gaussian special case; no claim that every changed coupling is easier or one-step exact"},
    "rotated_noise": {"endpoint_covariance_both": (.25*np.eye(2)).tolist(), "expected_paired_coordinate_mse": paired_mse, "qualification": "same Gaussian output law, different mapping of a shared noise sample; paired error is not a distribution metric"},
    "condition_specific_variance": {"sigma": [.5, 1.], "required_slopes_at_t_half": slopes, "qualification": "original affine model has a common x coefficient for both c values, so cannot exactly represent both fields"},
    "loss_contrast": {"squared_loss_minimizer": mean.tolist(), "coordinate_L1_minimizer": median.tolist(), "L1_at_mean": mean_l1, "L1_at_median": median_l1, "qualification": "local finite regression example only; mean-to-transport argument cannot automatically be reused for a median"}}
out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"status": "passed", "output": str(out), "paired_coordinate_mse": paired_mse, "condition_slopes": slopes}, ensure_ascii=False))
