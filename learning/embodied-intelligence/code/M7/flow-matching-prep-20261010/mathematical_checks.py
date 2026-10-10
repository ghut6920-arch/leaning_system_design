"""Independent mathematical/interface checks for teacher preparation r1.

AI-authored, 2026-10-10. Checks use derivatives, exact solutions, hand values and
function contracts. They do not claim learner performance or general FM proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

from teacher_cfm import (
    LearnedField, MU, PREP_DIR, SIGMA, coordinate_mse, empirical_gradient,
    euler_sample, features, hats, oracle_euler_coefficient, oracle_exact,
    oracle_field, q_variance, same_condition_mixture, write_json,
)


def run_checks(out_dir):
    started = time.perf_counter()
    checks = []

    def record(name, detail):
        checks.append({"name": name, "status": "passed", "detail": detail})

    x0 = np.array([-1.0, 1.0])
    x1 = np.array([3.0, -1.0])
    xt = 0.75 * x0 + 0.25 * x1
    u = x1 - x0
    b = np.array([2.0, 0.0])
    loss = coordinate_mse(b[None, :], u[None, :])
    gradient = b - u
    updated = b - 0.1 * gradient
    updated_loss = coordinate_mse(updated[None, :], u[None, :])
    np.testing.assert_allclose(xt, [0.0, 0.5])
    np.testing.assert_allclose(u, [4.0, -2.0])
    np.testing.assert_allclose(gradient, [-2.0, 2.0])
    np.testing.assert_allclose(updated, [2.2, -0.2])
    np.testing.assert_allclose([loss, updated_loss], [4.0, 3.24])
    record("single-record derivative/loss/gradient/update", {
        "xt": xt.tolist(), "u": u.tolist(), "old_loss": loss,
        "gradient": gradient.tolist(), "updated_b": updated.tolist(), "new_loss": updated_loss})

    times = np.r_[np.linspace(0, 1, 257), 0.123456789]
    h = hats(times)
    np.testing.assert_allclose(h.sum(axis=1), 1, atol=1e-14)
    assert np.max(np.count_nonzero(h, axis=1)) <= 2
    np.testing.assert_allclose(hats(np.array([0.0, 1.0]))[:, [0, 16]], np.eye(2))
    query_features = features(xt[None, :], 0.25, np.array([1]))
    np.testing.assert_allclose(query_features[0, 16:20], [1.0, 0.0, 0.5, 1.0])
    assert np.count_nonzero(query_features[0]) == 3
    record("hat partition/endpoint/query active block", {"sum_range": [float(h.sum(1).min()), float(h.sum(1).max())],
        "max_active_hats": int(np.count_nonzero(h, axis=1).max()), "query_block_j4": query_features[0, 16:20].tolist()})

    rng = np.random.default_rng(19)
    state = rng.normal(size=(8, 2))
    tt = rng.uniform(size=8)
    cc = np.array([0, 1] * 4)
    phi = features(state, tt, cc)
    weights = rng.normal(scale=0.3, size=(68, 2))
    targets = rng.normal(size=(8, 2))
    analytic_grad = empirical_gradient(phi, weights, targets)
    entries = [(0, 0), (4, 1), (17, 0), (32, 1), (44, 0), (63, 1), (67, 0)]
    epsilon = 1e-6
    grad_errors = []
    for row, col in entries:
        upper = weights.copy()
        lower = weights.copy()
        upper[row, col] += epsilon
        lower[row, col] -= epsilon
        numerical = (coordinate_mse(phi @ upper, targets) - coordinate_mse(phi @ lower, targets)) / (2 * epsilon)
        grad_errors.append(abs(numerical - analytic_grad[row, col]))
    assert max(grad_errors) < 2e-9
    for scalar_t in (0.0, 0.1234567, 0.25, 1.0):
        np.testing.assert_allclose(LearnedField(weights)(state, scalar_t, cc),
                                   features(state, scalar_t, cc) @ weights, atol=1e-13)
    record("W gradient central finite-difference and fast evaluation", {
        "entries": entries, "epsilon": epsilon, "max_abs_gradient_error": max(grad_errors)})

    z = rng.normal(size=(8, 2))
    derivative_errors = []
    for time_point in (0.1, 0.25, 0.5, 0.75, 0.9):
        numerical = (oracle_exact(z, time_point + epsilon, cc) - oracle_exact(z, time_point - epsilon, cc)) / (2 * epsilon)
        analytic = oracle_field(oracle_exact(z, time_point, cc), time_point, cc)
        derivative_errors.append(float(np.max(np.abs(numerical - analytic))))
    np.testing.assert_allclose(oracle_exact(z, 0, cc), z)
    np.testing.assert_allclose(oracle_exact(z, 1, cc), MU[cc] + 0.5 * z)
    assert max(derivative_errors) < 1e-8
    query_m = oracle_field(xt[None, :], 0.25, np.array([1]))[0]
    np.testing.assert_allclose(query_m, [96 / 37, -22 / 37])
    grid = np.linspace(0, 1, 200001)
    floor_quadrature = np.trapz(SIGMA**2 / q_variance(grid), grid)
    assert abs(floor_quadrature - np.pi / 4) < 1e-9
    record("Gaussian exact derivative/initial/endpoints and risk floor", {
        "max_derivative_abs_error": max(derivative_errors), "query_oracle": query_m.tolist(),
        "risk_floor_quadrature": float(floor_quadrature), "risk_floor_analytic": float(np.pi / 4)})

    known_variances = {1: 0.0, 4: 0.1159678597516435, 16: 0.20764708160296838, 64: 0.2386862759670217}
    for n_steps, value in known_variances.items():
        coefficient = oracle_euler_coefficient(n_steps)
        np.testing.assert_allclose(coefficient**2, value, atol=1e-14)
        y = euler_sample(oracle_field, z, cc, n_steps)
        np.testing.assert_allclose(y, MU[cc] + coefficient * z, atol=1e-13)
    np.testing.assert_allclose(euler_sample(oracle_field, z, cc, 1), MU[cc])
    record("oracle Euler variance and analytic recurrence", {str(n): v for n, v in known_variances.items()})

    queries = []
    def instrumented_decay(x, t, c):
        queries.append((t, x.copy()))
        return -x
    untouched = z.copy()
    result = euler_sample(instrumented_decay, z, cc, 4)
    assert len(queries) == 4
    np.testing.assert_allclose([a[0] for a in queries], [0, 0.25, 0.5, 0.75])
    np.testing.assert_allclose(result, (3 / 4)**4 * z)
    np.testing.assert_allclose(queries[1][1], 0.75 * z)
    np.testing.assert_array_equal(z, untouched)
    def time_field(x, t, c):
        return np.full_like(x, t)
    np.testing.assert_allclose(euler_sample(time_field, z, cc, 4), z + 3 / 8)
    def constant_field(x, t, c):
        return np.full_like(x, 2.0)
    np.testing.assert_allclose(euler_sample(constant_field, z, cc, 7), z + 2.0)
    record("Euler count/time/current-state/no input mutation", {"queries": [a[0] for a in queries],
        "last_query": 0.75, "updates_to_final_time": 4})

    rejected = 0
    for illegal_n in (0, -1, 1.5, True, False, "4"):
        try:
            euler_sample(oracle_field, z, cc, illegal_n)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError(f"invalid N accepted: {illegal_n!r}")
    illegal_pairs = [(z[:, :1], cc), (z, cc[:, None]), (z, cc.astype(float)),
                     (z, np.full(8, 2)), (np.full((8, 2), np.nan), cc)]
    for invalid_z, invalid_c in illegal_pairs:
        try:
            euler_sample(oracle_field, invalid_z, invalid_c, 4)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("invalid shape/value accepted")
    try:
        euler_sample(lambda x, t, c: np.zeros((len(x), 1)), z, cc, 4)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("wrong field output shape accepted")
    record("illegal N/state/condition/field output", {"rejected_cases": rejected})

    mixture_w, components, mixture_v = same_condition_mixture(np.array([0.5, 0]), 0.5)
    np.testing.assert_allclose(mixture_w[1], 0.9608342772032357, atol=1e-14)
    np.testing.assert_allclose(components[:, 0], [-3.8, 2.6])
    np.testing.assert_allclose(mixture_v, [2.3493393741007083, 0], atol=1e-14)
    independent_cost = float(np.dot(MU[1], MU[1]) + 2 * (1 + SIGMA**2))
    coupled_cost = float(np.dot(MU[1], MU[1]) + 2 * (SIGMA - 1)**2)
    np.testing.assert_allclose([independent_cost, coupled_cost], [6.5, 4.5])
    record("same-c mixture local posterior and OT counterexample", {
        "component_weights_minus_plus": mixture_w.tolist(), "velocities": components.tolist(),
        "local_velocity": mixture_v.tolist(), "global_terminal_mean": [0, 0],
        "independent_cost": independent_cost, "legal_coupling_cost": coupled_cost})

    output = {"revision": "M7.2-math-checks-r1-20261010", "status": "passed", "count": len(checks),
              "seconds": time.perf_counter() - started, "checks": checks,
              "scope": "teacher mathematics and interface; no learner evidence; not a proof for arbitrary fields"}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "mathematical-checks-r1.json", output)
    read_back = json.loads((out_dir / "mathematical-checks-r1.json").read_text(encoding="utf-8"))
    assert read_back["count"] == len(checks)
    print(json.dumps(output, indent=2))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=PREP_DIR / "teacher-run")
    run_checks(parser.parse_args().out_dir)
