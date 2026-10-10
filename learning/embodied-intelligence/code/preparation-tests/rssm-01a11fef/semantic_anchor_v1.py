"""AI-authored teaching reference v1, 2026-10-09.

An exact scalar Gaussian state-space anchor for information boundaries and MPC.
This is not a trained neural RSSM or a learner submission. All inputs are
declared teaching assumptions. Standard library only; no environment actions.
Canonical artifact: artifacts/preparation-tests/2026-10-09-rssm-01a11fef.
"""

from dataclasses import asdict, dataclass
from itertools import product
import json
import math


@dataclass(frozen=True)
class Belief:
    mean: float
    variance: float


def predict(belief: Belief, action: float, process_variance: float = 0.25) -> Belief:
    return Belief(belief.mean + action, belief.variance + process_variance)


def correct(prior: Belief, observation: float, measurement_variance: float = 1.0) -> Belief:
    if prior.variance <= 0 or measurement_variance <= 0:
        raise ValueError("This reference assumes positive variances.")
    gain = prior.variance / (prior.variance + measurement_variance)
    return Belief(prior.mean + gain * (observation - prior.mean), (1 - gain) * prior.variance)


def expected_reward(belief: Belief, action: float, target: float = 2.0) -> float:
    # Reward r_{t+1} = -(z_{t+1}-target)^2 - 0.1*a_t^2.
    return -((belief.mean - target) ** 2 + belief.variance + 0.1 * action ** 2)


def evaluate(start: Belief, actions: tuple[float, ...]) -> dict:
    belief = start
    total = 0.0
    trajectory = []
    for action in actions:
        belief = predict(belief, action)
        reward = expected_reward(belief, action)
        total += reward
        trajectory.append({"action": action, **asdict(belief), "expected_reward": reward})
    return {"actions": list(actions), "score": total, "trajectory": trajectory}


def plan(start: Belief, horizon: int = 2) -> list[dict]:
    candidates = [evaluate(start, actions) for actions in product((-1.0, 0.0, 1.0), repeat=horizon)]
    return sorted(candidates, key=lambda item: item["score"], reverse=True)


def gaussian_kl(q: Belief, p: Belief) -> float:
    return 0.5 * (math.log(p.variance / q.variance)
                  + (q.variance + (q.mean - p.mean) ** 2) / p.variance - 1)


def reference() -> dict:
    # Filtering context starts at t=0, after observing o_0.
    start = Belief(0.0, 1.0)
    prior1 = predict(start, 1.0)
    posterior1 = correct(prior1, 0.0)
    candidates1 = plan(posterior1)
    first_action = candidates1[0]["actions"][0]
    prior2 = predict(posterior1, first_action)
    posterior2 = correct(prior2, 2.5)
    candidates2 = plan(posterior2)
    changed_noise = correct(prior1, 0.0, 9.0)
    changed_candidates = plan(changed_noise)

    # Local ELBO check for fixed past state: p(z)=N(1,1), o=0, R=1.
    p = Belief(1.0, 1.0)
    q = correct(p, 0.0)
    expected_log_likelihood = -0.5 * (math.log(2 * math.pi) + q.variance + q.mean ** 2)
    kl = gaussian_kl(q, p)
    log_evidence = -0.5 * (math.log(4 * math.pi) + 0.5)
    assert math.isclose(expected_log_likelihood - kl, log_evidence, abs_tol=1e-12)
    assert math.isclose(prior1.variance, 1.25)
    assert math.isclose(posterior1.mean, 4 / 9)
    assert math.isclose(posterior1.variance, 5 / 9)
    assert candidates1[0]["actions"] == [1.0, 1.0]
    assert candidates2[0]["actions"] == [0.0, 0.0]
    assert changed_candidates[0]["actions"] == [1.0, 0.0]

    # A discriminating check: no observation means no variance-reducing correction.
    free_step = predict(prior1, 0.0)
    repeated_fake_correction = correct(prior1, prior1.mean)
    assert free_step.variance > prior1.variance > repeated_fake_correction.variance
    # Mean-only reward omits variance, even though in this toy it cancels in rankings.
    assert math.isclose(expected_reward(prior1, 1.0), -2.35)

    return {
        "status": "teacher_reference_executed_no_learner_event",
        "model": {"process_variance": 0.25, "measurement_variance": 1.0,
                  "target": 2.0, "horizon": 2, "discount": 1.0},
        "filtering": {"start0": asdict(start), "action0": 1.0, "observation1": 0.0,
                      "prior1": asdict(prior1), "posterior1": asdict(posterior1)},
        "planning1": candidates1,
        "new_observation": {"executed_action1": first_action, "observation2": 2.5,
                            "prior2": asdict(prior2), "posterior2": asdict(posterior2)},
        "planning2": candidates2,
        "changed_R9": {"posterior1": asdict(changed_noise), "candidates": changed_candidates},
        "local_ELBO": {"posterior": asdict(q), "expected_log_likelihood": expected_log_likelihood,
                       "kl_q_p": kl, "elbo": expected_log_likelihood - kl,
                       "log_evidence": log_evidence},
        "checks": "analytic_equality_indexed_reward_free_rollout_and_replanning_passed"
    }


if __name__ == "__main__":
    print(json.dumps(reference(), ensure_ascii=False, indent=2))
