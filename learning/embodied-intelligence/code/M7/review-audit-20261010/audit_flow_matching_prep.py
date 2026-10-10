"""Read-only mathematical audit of M7.2 prep; writes only review results.

This is reviewer work, not learner code or an additional teaching requirement.
It reconstructs the fixed affine model's sampler via matrix composition instead
of importing or calling the teacher's sampling loop.
"""
from pathlib import Path
import csv
import hashlib
import json
import sys

import numpy as np

COURSE = Path(__file__).resolve().parents[3]
PREP = COURSE / "artifacts/preparation-tests/2026-10-10-M7-2-flow-matching/teacher-run"
CODE = COURSE / "code/M7/flow-matching-prep-20261010"
REVIEWS = COURSE / "reviews"
BASELINE = REVIEWS / "2026-10-10-flow-matching-review-baseline.json"
OUT = REVIEWS / "2026-10-10-flow-matching-preparation-checks.json"
checks = []


def record(name, detail):
    checks.append({"name": name, "status": "passed", "detail": detail})


def close(actual, expected, atol=1e-11):
    np.testing.assert_allclose(actual, expected, atol=atol, rtol=1e-11)


def q(t):
    return (1 - t)**2 + 0.25 * t**2


def gaussian_field(x, t, mu):
    return mu + ((1.25 * t - 1) / q(t)) * (x - t * mu)


def feature_matrix(x, t, c):
    blocks = []
    base = np.column_stack((np.ones(len(x)), x, 2 * c - 1))
    for j in range(17):
        hat = np.maximum(1 - np.abs(16 * t - j), 0)
        blocks.append(hat[:, None] * base)
    return np.concatenate(blocks, axis=1)


def learned_endpoint_by_affine_composition(z, c, weights, steps):
    """Compose affine Euler maps once per class, then apply to all initial z."""
    blocks = weights.reshape(17, 4, 2)
    h = 1 / steps
    transform = np.eye(2)
    offsets = np.zeros((2, 2))
    for n in range(steps):
        t = n / steps
        hat = np.maximum(1 - np.abs(16 * t - np.arange(17)), 0)
        coeff = np.tensordot(hat, blocks, axes=1)
        local_map = np.eye(2) + h * coeff[1:3]
        intercepts = coeff[0] + np.array([-1, 1])[:, None] * coeff[3]
        transform = transform @ local_map
        offsets = offsets @ local_map + h * intercepts
    return z @ transform + offsets[c]


def main():
    x0, x1, b = np.array([-1., 1.]), np.array([3., -1.]), np.array([2., 0.])
    xt, u = .75 * x0 + .25 * x1, x1 - x0
    updated = b - .1 * (b - u)
    close(xt, [0, .5]); close(u, [4, -2]); close(updated, [2.2, -.2])
    close([np.mean((b-u)**2), np.mean((updated-u)**2)], [4, 3.24])
    close(gaussian_field(xt, .25, np.array([2., 0.])), [96/37, -22/37])
    new_x = .25 * np.array([1., -1.]) + .75 * np.array([-3., 1.])
    close(new_x, [-2, .5])
    close(gaussian_field(new_x, .75, np.array([-2., 0.])), [-24/13, -2/13])
    record("old/new sample calculations and label-versus-field", {"label": u.tolist(), "updated": updated.tolist()})

    ts = np.linspace(0, 1, 200001)
    covariance = .25 * ts - (1 - ts)
    conditional_variance = 1.25 - covariance**2 / q(ts)
    close(conditional_variance, .25 / q(ts))
    floor = float(np.trapz(conditional_variance, ts))
    close(floor, np.pi/4, atol=1e-9)
    close(float(q(ts).min()), .2)
    z = np.array([-1., 1.]); mu = np.array([2., 0.])
    table = []
    for t in [0, .25, .5, .75, 1]:
        y = t * mu + np.sqrt(q(t)) * z
        derivative = mu + ((1.25*t - 1) / np.sqrt(q(t))) * z
        close(derivative, gaussian_field(y, t, mu))
        table.append({"t": t, "y": y.tolist()})
    record("Gaussian covariance conditioning, exact ODE and irreducible risk", {"trajectory": table, "risk_floor": floor})

    with np.load(PREP / "model-r1.npz", allow_pickle=False) as data:
        weights = data["W"].copy()
    with np.load(PREP / "heldout-inputs-r1.npz", allow_pickle=False) as data:
        heldout = {k: data[k].copy() for k in data.files}
    summary = json.loads((PREP / "summary-r1.json").read_text(encoding="utf-8"))
    close(heldout["u"], heldout["x1"] - heldout["x0"])
    close(heldout["xt"], (1-heldout["t"][:, None])*heldout["x0"] + heldout["t"][:, None]*heldout["x1"])
    prediction = feature_matrix(heldout["xt"], heldout["t"], heldout["c"]) @ weights
    mus = np.array([[-2., 0.], [2., 0.]])[heldout["c"]]
    times = heldout["t"][:, None]
    oracle = gaussian_field(heldout["xt"], times, mus)
    cfm = float(np.mean((prediction - heldout["u"])**2))
    field = float(np.mean((prediction - oracle)**2))
    oracle_risk = float(np.mean((oracle - heldout["u"])**2))
    cross = float(2*np.mean((prediction-oracle)*(oracle-heldout["u"])))
    close([cfm, field, oracle_risk, cross], [summary["heldout"][k] for k in (
        "learned_cfm_coordinate_mse", "learned_field_coordinate_mse",
        "oracle_cfm_coordinate_mse", "finite_sample_cross_term")])
    close(cfm, field + oracle_risk + cross)
    record("saved held-out data and risk decomposition", {"cfm": cfm, "field": field, "oracle_label_risk": oracle_risk, "cross": cross})

    # Seed reconstruction also checks that the stored W really fits sampled U.
    rng = np.random.default_rng(20261010)
    classes = rng.permutation(np.repeat(np.arange(2), 50000))
    noise = rng.normal(size=(100000, 2))
    targets = np.array([[-2., 0.], [2., 0.]])[classes] + .5*rng.normal(size=(100000, 2))
    train_t = rng.uniform(0, 1, size=100000)
    train_x = (1-train_t[:, None])*noise + train_t[:, None]*targets
    phi = feature_matrix(train_x, train_t, classes)
    rebuilt, _, rank, _ = np.linalg.lstsq(phi, targets-noise, rcond=None)
    close(rebuilt, weights, atol=1e-10)
    fitted_risk = float(np.mean((phi @ rebuilt - (targets-noise))**2))
    close(fitted_risk, summary["fit"]["training_fitted_coordinate_mse"])
    record("training seed, features and shared W refit", {"rank": int(rank), "maximum_weight_difference": float(np.max(np.abs(rebuilt-weights))), "fitted_risk": fitted_risk})

    with np.load(PREP / "paired-generation-r1.npz", allow_pickle=False) as data:
        generated = {k: data[k].copy() for k in data.files}
    gen_mu = np.array([[-2., 0.], [2., 0.]])[generated["c"]]
    close(generated["oracle_exact"], gen_mu + .5*generated["z"])
    endpoint_errors = []
    for n in [1, 4, 16, 64, 128, 2048, 4096]:
        ours = learned_endpoint_by_affine_composition(generated["z"], generated["c"], weights, n)
        key = f"learned_n{n}" if n < 2048 else ("learned_reference" if n == 2048 else "learned_double_reference")
        close(ours, generated[key], atol=1e-10)
        if n < 2048:
            tt = np.arange(n)/n
            coefficient = float(np.prod(1 + (1.25*tt-1)/q(tt)/n))
            close(generated[f"oracle_n{n}"], gen_mu + coefficient*generated["z"])
        endpoint_errors.append({"N": n, "maximum_saved_endpoint_difference": float(np.max(np.abs(ours-generated[key])))})
    close(generated["oracle_n1"], gen_mu)
    with (PREP / "metrics-r1.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 10
    for row in rows:
        n, c = int(row["n_steps"]), int(row["class"])
        selected = generated[f"learned_n{n}"][generated["c"] == c]
        close(selected.mean(0), [float(row["learned_mean_coord0"]), float(row["learned_mean_coord1"])])
        cov = np.cov(selected, rowvar=False, ddof=1)
        close([cov[0,0], cov[0,1], cov[1,1]], [float(row[k]) for k in ["learned_cov00", "learned_cov01", "learned_cov11"]])
    record("sampler via independent affine-map composition and per-class CSV", {"comparisons": endpoint_errors, "csv_rows": len(rows)})

    positions = np.array([-.5, 0., .5])
    right_weight = 1/(1+np.exp(-6.4*positions))
    local_v = -1.2*positions + 3.2*(2*right_weight-1)
    close(local_v, [-2.3493393741007083, 0, 2.3493393741007083])
    # Extra reviewer calculation, NOT a figure/experiment present in the prep.
    center_derivative = -1.2 + 3.2**2
    close(center_derivative, 9.04)
    close([4 + 2*(1+.25), 4 + 2*(1-.5)**2], [6.5, 4.5])
    record("same-c mixture and legal coupling contrast", {"positions": positions.tolist(), "local_velocity": local_v.tolist(), "extra_review_calculation_center_derivative": center_derivative, "qualification": "analytic contrast; no nonlinear-model training or new teaching material"})

    source_hash = hashlib.sha256((CODE / "teacher_cfm.py").read_bytes()).hexdigest()
    assert source_hash == summary["source_sha256"]
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    changed = []
    for item in baseline:
        path = Path(item["Path"])
        current = hashlib.sha256(path.read_bytes()).hexdigest().upper() if path.is_file() else None
        if current != item["SHA256"]:
            changed.append(str(path))
    assert not changed, changed
    record("original files unchanged", {"baseline_files": len(baseline), "changed": changed, "teacher_source_sha256": source_hash})
    result = {"date": "2026-10-10", "thread_id": "01a1254d-06da-7ad3-818c-da728be768a6", "status": "passed", "checks": checks, "environment": {"python": sys.version, "numpy": np.__version__}, "scope": "read-only reviewer mathematics, saved outputs, seed reproduction and original-byte preservation; no learner evidence or general learning-effect validation"}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "count": len(checks), "output": str(OUT), "heldout_field_mse": field, "originals_unchanged": len(baseline)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
