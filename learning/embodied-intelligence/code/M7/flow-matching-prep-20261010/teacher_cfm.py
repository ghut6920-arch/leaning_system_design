"""M7.2 preparation, revision 1: real NumPy CFM fit and paired Euler review.

AI-authored teacher example, 2026-10-10. Sources/limits: README.md.
Training labels are independently sampled X1-X0, never an oracle velocity.
All losses named coordinate_mse average over batch AND the two coordinates.
This affine-in-x family cannot represent a same-condition multimodal field.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np

REVISION = "M7.2-teacher-cfm-r1-20261010"
SIGMA = 0.5
MU = np.array([[-2.0, 0.0], [2.0, 0.0]])
N_KNOTS = 17
SEEDS = {"train": 20261010, "heldout": 20261011, "generation": 20261012}
N_LIST = (1, 4, 16, 64, 128)
PREP_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "preparation-tests" / "2026-10-10-M7-2-flow-matching"


def validate_state(x, c):
    """Validate x[B,2], binary c[B]; return float64 x and int64 c."""
    x = np.asarray(x)
    c = np.asarray(c)
    if x.ndim != 2 or x.shape[1] != 2 or x.shape[0] < 1:
        raise ValueError("state must have shape [B,2], B>=1")
    if c.shape != (x.shape[0],) or not np.issubdtype(c.dtype, np.integer):
        raise ValueError("condition must have integer shape [B]")
    if not np.all((c == 0) | (c == 1)):
        raise ValueError("condition must be 0 or 1")
    if not np.issubdtype(x.dtype, np.number) or np.iscomplexobj(x) or not np.all(np.isfinite(x)):
        raise ValueError("state must be finite real numbers")
    return x.astype(np.float64, copy=False), c.astype(np.int64, copy=False)


def validate_time(t, batch):
    t = np.asarray(t, dtype=np.float64)
    if t.ndim == 0:
        t = np.full(batch, float(t))
    if t.shape != (batch,) or not np.all(np.isfinite(t)) or np.any((t < 0) | (t > 1)):
        raise ValueError("time must be scalar or [B], finite, in [0,1]")
    return t


def balanced_conditions(batch, rng):
    """Exactly half each class, then shuffled; B must be positive and even."""
    if isinstance(batch, (bool, np.bool_)) or not isinstance(batch, (int, np.integer)) or batch < 2 or batch % 2:
        raise ValueError("batch must be a positive even integer")
    return rng.permutation(np.repeat(np.arange(2, dtype=np.int64), batch // 2))


def draw_training_records(batch, seed):
    rng = np.random.default_rng(seed)
    c = balanced_conditions(batch, rng)
    x0 = rng.normal(size=(batch, 2))
    x1 = MU[c] + SIGMA * rng.normal(size=(batch, 2))
    t = rng.uniform(0.0, 1.0, size=batch)
    xt = (1.0 - t[:, None]) * x0 + t[:, None] * x1
    u = x1 - x0
    return {"x0": x0, "x1": x1, "t": t, "c": c, "xt": xt, "u": u}


def hats(t):
    """17 triangular hats at j/16, including both endpoint nodes."""
    t = np.asarray(t, dtype=np.float64)
    if t.ndim != 1 or not np.all(np.isfinite(t)) or np.any((t < 0) | (t > 1)):
        raise ValueError("hats need time [B] in [0,1]")
    return np.maximum(1.0 - np.abs(16.0 * t[:, None] - np.arange(N_KNOTS)), 0.0)


def features(x, t, c):
    x, c = validate_state(x, c)
    tt = validate_time(t, len(x))
    # x[:,0]/x[:,1] are CURRENT STATE COORDINATES, not endpoint x0/x1.
    base = np.column_stack((np.ones(len(x)), x[:, 0], x[:, 1], 2 * c - 1))
    return (hats(tt)[:, :, None] * base[:, None, :]).reshape(len(x), 68)


class LearnedField:
    """Shared W[68,2]. Scalar-time fast path exactly evaluates Phi @ W."""
    def __init__(self, weights):
        self.W = np.asarray(weights, dtype=np.float64)
        if self.W.shape != (68, 2) or not np.all(np.isfinite(self.W)):
            raise ValueError("W must be finite [68,2]")

    def __call__(self, x, t, c):
        x, c = validate_state(x, c)
        if np.asarray(t).ndim == 0:
            ts = float(t)
            if not np.isfinite(ts) or not 0 <= ts <= 1:
                raise ValueError("time must be in [0,1]")
            # Only the two neighboring hats are active; no oracle coefficients.
            position = 16.0 * ts
            left = min(int(np.floor(position)), 15)
            fraction = position - left
            blocks = self.W.reshape(17, 4, 2)
            coefficients = (1 - fraction) * blocks[left] + fraction * blocks[left + 1]
            base = np.column_stack((np.ones(len(x)), x, 2 * c - 1))
            return base @ coefficients
        return features(x, t, c) @ self.W


def coordinate_mse(prediction, target):
    prediction = np.asarray(prediction)
    target = np.asarray(target)
    if prediction.shape != target.shape or prediction.ndim != 2 or prediction.shape[1] != 2:
        raise ValueError("MSE inputs must be matching [B,2]")
    return float(np.mean((prediction - target) ** 2))


def empirical_gradient(phi, weights, target):
    """For L = (1/(2B)) sum ||Phi W - U||^2, grad = Phi.T residual / B."""
    return phi.T @ (phi @ weights - target) / len(phi)


def q_variance(t):
    return (1.0 - t) ** 2 + SIGMA**2 * t**2


def oracle_field(x, t, c):
    x, c = validate_state(x, c)
    tt = validate_time(t, len(x))
    mu = MU[c]
    a = (SIGMA**2 * tt - (1.0 - tt)) / q_variance(tt)
    return mu + a[:, None] * (x - tt[:, None] * mu)


def oracle_exact(z, t, c):
    z, c = validate_state(z, c)
    tt = validate_time(t, len(z))
    return tt[:, None] * MU[c] + np.sqrt(q_variance(tt))[:, None] * z


def oracle_euler_coefficient(n_steps):
    validate_steps(n_steps)
    t = np.arange(n_steps, dtype=np.float64) / n_steps
    a = (SIGMA**2 * t - (1.0 - t)) / q_variance(t)
    return float(np.prod(1 + a / n_steps))


def validate_steps(n_steps):
    if isinstance(n_steps, (bool, np.bool_)) or not isinstance(n_steps, (int, np.integer)) or n_steps < 1:
        raise ValueError("n_steps must be an integer >=1")


def euler_sample(field, z, c, n_steps):
    """Return state at t=1 after N updates; query times are 0,...,(N-1)/N."""
    validate_steps(n_steps)
    z, c = validate_state(z, c)
    y = z.copy()
    h = 1.0 / n_steps
    for n in range(n_steps):
        velocity = np.asarray(field(y, n / n_steps, c), dtype=np.float64)
        if velocity.shape != y.shape or not np.all(np.isfinite(velocity)):
            raise ValueError("field must return finite velocity [B,2]")
        y = y + h * velocity
    return y


def same_condition_mixture(x, t):
    """Analytic same-c two-mode contrast only, never trained by this model."""
    x = np.asarray(x, dtype=np.float64)
    centers = MU
    q = q_variance(t)
    logits = -np.sum((x[None, :] - t * centers) ** 2, axis=1) / (2 * q)
    weights = np.exp(logits - np.max(logits))
    weights /= np.sum(weights)
    a = (SIGMA**2 * t - (1 - t)) / q
    component_velocities = centers + a * (x[None, :] - t * centers)
    return weights, component_velocities, weights @ component_velocities


def error_pair(prediction, reference):
    mse = coordinate_mse(prediction, reference)
    return {"coordinate_mse": mse, "coordinate_rmse": float(np.sqrt(mse)),
            "norm_rms_2d": float(np.sqrt(2 * mse))}


def class_statistics(y, c):
    stats = {}
    for label in (0, 1):
        selected = y[c == label]
        stats[str(label)] = {"count": len(selected), "mean": selected.mean(axis=0).tolist(),
                            "covariance_ddof1": np.cov(selected, rowvar=False, ddof=1).tolist()}
    return stats


def timed_sample(field, z, c, n_steps):
    started = time.perf_counter()
    result = euler_sample(field, z, c, n_steps)
    return result, time.perf_counter() - started


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def run(out_dir, train_size=100000, heldout_size=25000, generation_size=8192, reference_steps=2048):
    started = time.perf_counter()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    train = draw_training_records(train_size, SEEDS["train"])
    heldout = draw_training_records(heldout_size, SEEDS["heldout"])
    rng = np.random.default_rng(SEEDS["generation"])
    gen_c = balanced_conditions(generation_size, rng)
    z = rng.normal(size=(generation_size, 2))

    phi = features(train["xt"], train["t"], train["c"])
    fit_started = time.perf_counter()
    zero = LearnedField(np.zeros((68, 2)))
    W, residual_sums, rank, singular_values = np.linalg.lstsq(phi, train["u"], rcond=None)
    fit_seconds = time.perf_counter() - fit_started
    learned = LearnedField(W)
    query_x = np.array([[0.0, 0.5]])
    query_c = np.array([1], dtype=np.int64)
    query_t = 0.25
    heldout_prediction = learned(heldout["xt"], heldout["t"], heldout["c"])
    heldout_oracle = oracle_field(heldout["xt"], heldout["t"], heldout["c"])
    exact_endpoint = oracle_exact(z, 1.0, gen_c)

    reference, ref_seconds = timed_sample(learned, z, gen_c, reference_steps)
    double_reference, double_seconds = timed_sample(learned, z, gen_c, 2 * reference_steps)
    reference_change = error_pair(reference, double_reference)
    reference_to_exact = error_pair(double_reference, exact_endpoint)
    sample_results = []
    endpoints = {"z": z, "c": gen_c, "oracle_exact": exact_endpoint,
                 "learned_reference": reference, "learned_double_reference": double_reference}
    for n_steps in N_LIST:
        oracle_y, oracle_seconds = timed_sample(oracle_field, z, gen_c, n_steps)
        learned_y, learned_seconds = timed_sample(learned, z, gen_c, n_steps)
        coefficient = oracle_euler_coefficient(n_steps)
        oracle_stats = class_statistics(oracle_y, gen_c)
        learned_stats = class_statistics(learned_y, gen_c)
        rows = {"n_steps": n_steps, "nfe_per_sample": n_steps,
                "oracle_theory_coefficient": coefficient,
                "oracle_theory_coordinate_variance": coefficient**2,
                "oracle_theory_coordinate_rmse": abs(coefficient - SIGMA),
                "oracle_theory_norm_rms_2d": np.sqrt(2) * abs(coefficient - SIGMA),
                "oracle_euler_vs_exact": error_pair(oracle_y, exact_endpoint),
                "learned_vs_oracle_exact": error_pair(learned_y, exact_endpoint),
                "learned_vs_double_reference": error_pair(learned_y, double_reference),
                "oracle_class_statistics": oracle_stats, "learned_class_statistics": learned_stats,
                "oracle_seconds": oracle_seconds, "learned_seconds": learned_seconds}
        sample_results.append(rows)
        endpoints[f"oracle_n{n_steps}"] = oracle_y
        endpoints[f"learned_n{n_steps}"] = learned_y

    cfm_mse = coordinate_mse(heldout_prediction, heldout["u"])
    field_mse = coordinate_mse(heldout_prediction, heldout_oracle)
    oracle_cfm_mse = coordinate_mse(heldout_oracle, heldout["u"])
    cross_term = float(2 * np.mean((heldout_prediction - heldout_oracle) * (heldout_oracle - heldout["u"])))
    import matplotlib
    summary = {
        "revision": REVISION, "purpose": "AI teacher preparation run; no learner run or progress",
        "config": {"seeds": SEEDS, "train_size": train_size, "heldout_size": heldout_size,
                   "generation_size": generation_size, "class_counts": "exactly half each, shuffled",
                   "sigma": SIGMA, "mu": MU.tolist(), "n_time_knots": 17,
                   "features": "h_j(t)*[1,x_coord0,x_coord1,2*c-1], raw current x coordinates",
                   "training_labels": "independent X1-X0, NO oracle targets/features",
                   "loss": "coordinate MSE = (1/(2B))*sum_b ||prediction-U||^2",
                   "solver": "numpy.linalg.lstsq(Phi,U,rcond=None), no regularization",
                   "n_list": list(N_LIST), "reference_steps": reference_steps,
                   "double_reference_steps": 2 * reference_steps},
        "environment": {"python": sys.version, "executable": sys.executable, "numpy": np.__version__,
                        "matplotlib": matplotlib.__version__, "platform": platform.platform(),
                        "processor": platform.processor(), "threads_env": {
                            k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
                        "timing": "single wall-clock observation, vectorized batch, no benchmark guarantee"},
        "shapes": {k: list(v.shape) for k, v in train.items()} | {"Phi": list(phi.shape), "W": list(W.shape)},
        "fit": {"rank": int(rank), "seconds": fit_seconds,
                "singular_min": float(singular_values.min()), "singular_max": float(singular_values.max()),
                "W_l2": float(np.linalg.norm(W)), "W_min": float(W.min()), "W_max": float(W.max()),
                "W_changed_entries": int(np.count_nonzero(W)),
                "training_zero_coordinate_mse": coordinate_mse(np.zeros_like(train["u"]), train["u"]),
                "training_fitted_coordinate_mse": coordinate_mse(phi @ W, train["u"]),
                "normal_equation_gradient_maxabs": float(np.max(np.abs(empirical_gradient(phi, W, train["u"])))),
                "query": {"x": query_x.tolist(), "t": query_t, "c": query_c.tolist(),
                          "sample_target": [[4.0, -2.0]], "before": zero(query_x, query_t, query_c).tolist(),
                          "after": learned(query_x, query_t, query_c).tolist(),
                          "oracle_for_evaluation": oracle_field(query_x, query_t, query_c).tolist()}},
        "heldout": {"learned_cfm_coordinate_mse": cfm_mse, "learned_field_coordinate_mse": field_mse,
                    "oracle_cfm_coordinate_mse": oracle_cfm_mse,
                    "population_irreducible_coordinate_cfm_risk": float(np.pi / 4),
                    "sample_mean_conditional_variance": float(np.mean(SIGMA**2 / q_variance(heldout["t"]))),
                    "finite_sample_cross_term": cross_term,
                    "finite_sample_decomposition_residual": cfm_mse - field_mse - oracle_cfm_mse - cross_term},
        "learned_reference": {"steps": reference_steps, "double_steps": 2 * reference_steps,
                              "N_vs_double_N": reference_change,
                              "double_reference_vs_oracle_exact": reference_to_exact,
                              "seconds": ref_seconds, "double_seconds": double_seconds,
                              "warning": "finite Euler reference, not exact; small double-N change does not bound all remaining error"},
        "generation_input_statistics": class_statistics(z, gen_c),
        "target_class_statistics": {str(c): {"mean": MU[c].tolist(), "covariance": (SIGMA**2 * np.eye(2)).tolist()} for c in (0, 1)},
        "samples": sample_results,
        "limits": ["fixed t,c field is affine in x; same-c multimodal example is analytic only",
                   "finite OLS, one seed, no optimizer/neural/robot benchmark",
                   "moments do not identify general distributions",
                   "paired noise comparisons, not independent repeats",
                   "more integration steps keep the same W"],
    }
    np.savez_compressed(out_dir / "model-r1.npz", W=W)
    np.savez_compressed(out_dir / "heldout-inputs-r1.npz", **heldout)
    np.savez_compressed(out_dir / "paired-generation-r1.npz", **endpoints)
    columns = ["n_steps", "nfe_per_sample", "oracle_theory_coordinate_variance", "oracle_coordinate_rmse",
               "oracle_norm_rms_2d", "learned_vs_exact_coordinate_rmse", "learned_vs_reference_coordinate_rmse",
               "learned_vs_reference_norm_rms_2d", "class", "class_count", "learned_mean_coord0",
               "learned_mean_coord1", "learned_cov00", "learned_cov01", "learned_cov11", "learned_seconds"]
    with (out_dir / "metrics-r1.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in sample_results:
            for label in (0, 1):
                s = row["learned_class_statistics"][str(label)]
                writer.writerow({"n_steps": row["n_steps"], "nfe_per_sample": row["nfe_per_sample"],
                    "oracle_theory_coordinate_variance": row["oracle_theory_coordinate_variance"],
                    "oracle_coordinate_rmse": row["oracle_euler_vs_exact"]["coordinate_rmse"],
                    "oracle_norm_rms_2d": row["oracle_euler_vs_exact"]["norm_rms_2d"],
                    "learned_vs_exact_coordinate_rmse": row["learned_vs_oracle_exact"]["coordinate_rmse"],
                    "learned_vs_reference_coordinate_rmse": row["learned_vs_double_reference"]["coordinate_rmse"],
                    "learned_vs_reference_norm_rms_2d": row["learned_vs_double_reference"]["norm_rms_2d"],
                    "class": label, "class_count": s["count"], "learned_mean_coord0": s["mean"][0],
                    "learned_mean_coord1": s["mean"][1], "learned_cov00": s["covariance_ddof1"][0][0],
                    "learned_cov01": s["covariance_ddof1"][0][1], "learned_cov11": s["covariance_ddof1"][1][1],
                    "learned_seconds": row["learned_seconds"]})
    summary["total_seconds_before_output_review"] = time.perf_counter() - started
    summary["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    write_json(out_dir / "summary-r1.json", summary)
    # Actual read-back of saved model/JSON/CSV, then re-query stored model.
    saved = json.loads((out_dir / "summary-r1.json").read_text(encoding="utf-8"))
    with np.load(out_dir / "model-r1.npz") as model:
        stored_prediction = LearnedField(model["W"])(query_x, query_t, query_c)
    with (out_dir / "metrics-r1.csv").open(encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    if not np.allclose(stored_prediction, summary["fit"]["query"]["after"]) or len(csv_rows) != 10:
        raise RuntimeError("saved output read-back mismatch")
    print(json.dumps({"revision": saved["revision"], "fit_rank": saved["fit"]["rank"],
          "fit_query": saved["fit"]["query"], "heldout": saved["heldout"],
          "learned_reference": saved["learned_reference"], "total_seconds": saved["total_seconds_before_output_review"],
          "read_back": {"json": "ok", "model_query": "ok", "csv_rows": len(csv_rows)}}, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=PREP_DIR / "teacher-run")
    args = parser.parse_args()
    run(args.out_dir)
