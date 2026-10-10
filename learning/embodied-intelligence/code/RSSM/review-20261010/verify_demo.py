"""Teacher numerical checks, v1, 2026-10-10.

AI authored from prep/rssm-review-20261010/10-model-spec.md.
No trained neural RSSM, environment experiment, or learner execution is implied.
N(mu, variance) convention. Python standard library only.
"""
import itertools
import json
import math
import random
from pathlib import Path


def kl_normal(mq, vq, mp, vp):
    if min(vq, vp) <= 0:
        raise ValueError("Variances must be positive")
    return .5 * (math.log(vp / vq) + (vq + (mq - mp) ** 2) / vp - 1)


def recognition(d, previous_action, observation, alpha=.8, kappa=0.):
    vp = .25 + kappa * previous_action ** 2
    if observation is None:
        return alpha * d, vp
    vq = 1 / (1 / vp + 4)
    return vq * (alpha * d / vp + 4 * observation), vq


def rollout(d_mean, z_mean, z_variance, actions, alpha=.8, kappa=0.):
    # d is fixed at the initial conditional filtering state.
    vd, cov = 0., 0.
    mz, vz, md = z_mean, z_variance, d_mean
    steps = []
    for action in actions:
        md_new = .5 * md + .5 * mz + action
        vd_new = .25 * vd + .25 * vz + .5 * cov
        mz_new = alpha * md_new
        vz_new = alpha ** 2 * vd_new + .25 + kappa * action ** 2
        cov_new = alpha * vd_new
        steps.append(dict(d_mean=md_new, d_variance=vd_new,
                          z_mean=mz_new, z_variance=vz_new,
                          covariance=cov_new))
        md, vd, mz, vz, cov = md_new, vd_new, mz_new, vz_new, cov_new
    return steps


def plan(d, mq, vq, horizon=2, kappa=0., mean_only=False):
    rows = []
    for actions in itertools.product((-1, 0, 1), repeat=horizon):
        steps = rollout(d, mq, vq, actions, kappa=kappa)
        cost = sum(s["z_mean"] ** 2 + (0 if mean_only else s["z_variance"])
                   for s in steps) + .1 * sum(a * a for a in actions)
        rows.append(dict(actions=list(actions), cost=cost, steps=steps))
    return sorted(rows, key=lambda row: (row["cost"], row["actions"]))


def gaussian_log_density(value, mean, variance):
    return -.5 * (math.log(2 * math.pi * variance) + (value - mean) ** 2 / variance)


def run_checks():
    checks = []

    def check(label, got, expected, tolerance=1e-10):
        passed = abs(got - expected) <= tolerance
        checks.append(dict(check=label, actual=got, expected=expected,
                           tolerance=tolerance, passed=passed))
        if not passed:
            raise AssertionError((label, got, expected))

    old_kl = kl_normal(1, .125, 2, .25)
    new_kl = kl_normal(1, .125, 1.6, .25)
    gradient = (2 - 1) * 2 / .25
    eps = 1e-6
    finite_diff = (kl_normal(1, .125, 2 * (1 + eps), .25)
                   - kl_normal(1, .125, 2 * (1 - eps), .25)) / (2 * eps)
    check("local prior gradient vs finite difference", finite_diff, gradient, 1e-8)
    check("alpha update", 1 - .025 * gradient, .8)
    check("old KL", old_kl, 2.0965735902799727)
    check("new frozen-q KL", new_kl, .816573590279973)
    # Expected log likelihood under frozen q, with o=0 and decoder variance=.25.
    recon = -.5 * (math.log(2 * math.pi * .25) + (1 ** 2 + .125) / .25)
    elbo_new = recon - new_kl
    evidence_new = gaussian_log_density(0, 1.6, .5)
    exact_mq, exact_vq = recognition(2, 0, 0)
    gap = kl_normal(1, .125, exact_mq, exact_vq)
    check("scalar evidence minus ELBO = KL(q || posterior)", evidence_new - elbo_new, gap)
    check("frozen-q bound improvement", (recon - new_kl) - (recon - old_kl), 1.28)
    check("recognition after parameter update mean", exact_mq, .8)
    check("recognition after parameter update variance", exact_vq, .125)

    base = plan(2, .8, .125)
    risk = plan(2, .8, .125, kappa=2)
    mean = plan(2, .8, .125, mean_only=True)
    check("base best cost", base[0]["cost"], .861544)
    assert base[0]["actions"] == [-1, 0]
    assert mean[0]["actions"] == [-1, 0]
    assert risk[0]["actions"] == [0, 0]
    check("action-dependent noise best cost", risk[0]["cost"], 2.846664)
    base_by = {tuple(row["actions"]): row for row in base}
    risk_by = {tuple(row["actions"]): row for row in risk}
    mean_by = {tuple(row["actions"]): row for row in mean}
    for a, row in base_by.items():
        check(f"constant variance offset {a}", row["cost"] - mean_by[a]["cost"], .5762)
        check(f"noise contribution {a}", risk_by[a]["cost"] - row["cost"],
              2.32 * a[0] ** 2 + 2 * a[1] ** 2)
    steps = base[0]["steps"]
    check("first prior variance", steps[0]["z_variance"], .27)
    check("first d-z covariance", steps[0]["covariance"], .025)
    check("second d variance", steps[1]["d_variance"], .0878125)
    check("second prior variance", steps[1]["z_variance"], .3062)
    # Omitting Cov(d,z) produces .2982, so this example detects that error.
    no_cov_vd = .25 * steps[0]["d_variance"] + .25 * steps[0]["z_variance"]
    check("variance lost when covariance omitted", .3062 - (.64 * no_cov_vd + .25), .008)

    d_next = .5 * 2 + .5 * .8 - 1  # specified epsilon=0 internal path
    q_next = recognition(d_next, -1, -.5)
    replan = plan(d_next, *q_next)
    check("conditional internal path d next", d_next, .4)
    check("new observation filter mean", q_next[0], -.09)
    check("new observation filter variance", q_next[1], .125)
    check("replan best cost", replan[0]["cost"], .60403056)
    assert replan[0]["actions"] == [0, 0]
    check("missing observation uses prior mean", recognition(.4, -1, None)[0], .32)
    check("missing observation uses prior variance", recognition(.4, -1, None)[1], .25)

    # New-condition W data from the task author: this is a separate candidate work.
    w_grad = (.8 - .5) / .25
    check("W local block gradient", w_grad, 1.2)
    check("W local alpha update", .8 - .05 * w_grad, .74)
    check("W old frozen-q KL", kl_normal(.5, .125, .8, .25), .27657359027997264)
    check("W new frozen-q KL", kl_normal(.5, .125, .74, .25), .21177359027997266)
    w_q = recognition(-1, 0, -.2)
    w_plan = plan(-1, *w_q)
    check("W first plan cost", w_plan[0]["cost"], .7486)
    assert w_plan[0]["actions"] == [1, 0]
    w_d_next = .5 * -1 + .5 * -.5 + 1
    w_q_next = recognition(w_d_next, 1, 2.5)
    w_replan = plan(w_d_next, *w_q_next)
    check("W new internal d", w_d_next, .25)
    check("W new conditional filter mean", w_q_next[0], 1.35)
    check("W second plan cost", w_replan[0]["cost"], .722536)
    assert w_replan[0]["actions"] == [-1, 0]

    # An independent simulation of the specified controlled process checks moments.
    rng = random.Random(20261010)
    n = 60000
    sums = [0., 0.]
    squares = [0., 0.]
    for _ in range(n):
        d, z = 2., rng.gauss(.8, math.sqrt(.125))
        for j, action in enumerate((-1, 0)):
            d = .5 * d + .5 * z + action
            z = rng.gauss(.8 * d, .5)
            sums[j] += z
            squares[j] += z * z
    simulation = []
    for j in range(2):
        m = sums[j] / n
        v = squares[j] / n - m * m
        check(f"Monte Carlo step {j+1} mean", m, steps[j]["z_mean"], .007)
        check(f"Monte Carlo step {j+1} variance", v, steps[j]["z_variance"], .007)
        simulation.append(dict(step=j+1, mean=m, variance=v, n=n))

    return dict(version="v1", role="AI teacher checks", checks=checks,
                check_count=len(checks), all_passed=True,
                assertions=dict(base_actions=[-1, 0], mean_actions=[-1, 0],
                                noisy_actions=[0, 0], replan_actions=[0, 0]),
                local_gradient=dict(old_kl=old_kl, new_kl=new_kl,
                                    elbo_gap=gap, gradient=gradient),
                base_candidates=base, noise_candidates=risk,
                replan_candidates=replan, simulation=simulation,
                w_candidates=w_plan, w_replan_candidates=w_replan,
                limitations=["No neural RSSM training", "No environment closed-loop experiment",
                             "Monte Carlo is a finite numerical check, not a general proof",
                             "Specified internal epsilon=0 path is conditional, not an exact history mixture"])


if __name__ == "__main__":
    result = run_checks()
    target = Path(__file__).with_name("verification-results.json")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(dict(all_passed=result["all_passed"], checks=result["check_count"],
                          output=str(target)), ensure_ascii=False))
