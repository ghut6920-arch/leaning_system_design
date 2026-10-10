"""Teacher arithmetic checks for preparation DS-LWM-20261010, revision 1.

AI-authored verification code. Sources: DA-2 sections 4-6 and CD-1 M3,
in artifacts/preparation-tests/2026-10-10-decision-sufficient/.
Uses only Python's standard library; no neural model, robot, or learner run.
Run from the learning root: python code/decision-sufficient/preparation-20261010/verify_examples.py
Exact rational checks support the specified examples, not general theorems.
"""

import json
import platform
import sys
from fractions import Fraction as F
from typing import NamedTuple


class State(NamedTuple):
    stage: str
    mode: str
    background: int = 0


def transition(state, action, bonus=F(0)):
    if state.mode not in ("good", "bad") or state.background not in (0, 1):
        raise ValueError("Invalid environment state")
    terminal = State("terminal", state.mode, state.background)
    if state.stage == "start" and action == "safe":
        return F(4), terminal, True
    if state.stage == "start" and action == "shortcut":
        return F(0), State("post", state.mode, state.background), False
    if state.stage == "post" and action == "collect":
        payoff = F(10) if state.mode == "good" else F(-6)
        return payoff + bonus * state.background, terminal, True
    raise ValueError("Action is not legal at this stage")


def score(state, first_action, horizon=2, gamma=F(9, 10), bonus=F(0), tail=None):
    if horizon < 1 or not F(0) <= gamma <= F(1):
        raise ValueError("Use a positive finite horizon and discount in [0, 1]")
    total = F(0)
    current = state
    ended = False
    for t in range(horizon):
        action = first_action if t == 0 else "collect"
        reward, current, ended = transition(current, action, bonus)
        total += gamma**t * reward
        if ended:
            break
    if not ended and tail is not None:
        total += gamma**horizon * tail(current)
    return total


def best_actions(values):
    top = max(values.values())
    return sorted(k for k, v in values.items() if v == top)


def decision_regret(true_values, action):
    return max(true_values.values()) - true_values[action]


def expected_shortcut(p, gamma=F(9, 10)):
    return gamma * (F(10) * p - F(6) * (F(1) - p))


def inspection_value(p, feedback=True, fixed="safe", cost=F(1, 2)):
    branch = {}
    for mode in ("good", "bad"):
        action = ("shortcut" if mode == "good" else "safe") if feedback else fixed
        branch[mode] = score(State("start", mode), action, horizon=2)
    return -cost + F(9, 10) * (p * branch["good"] + (1 - p) * branch["bad"])


def serial(value):
    if isinstance(value, F):
        return {"exact": str(value), "decimal": float(value)}
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return value


checks = []


def check(name, actual, expected):
    if actual != expected:
        raise AssertionError(f"{name}: {actual!r} != {expected!r}")
    checks.append({"name": name, "actual": serial(actual), "expected": serial(expected), "passed": True})


good = {a: score(State("start", "good"), a) for a in ("shortcut", "safe")}
bad = {a: score(State("start", "bad"), a) for a in ("shortcut", "safe")}
check("base_good_returns", good, {"shortcut": F(9), "safe": F(4)})
check("base_bad_returns", bad, {"shortcut": F(-27, 5), "safe": F(4)})
check("base_good_choice", best_actions(good), ["shortcut"])
check("base_bad_choice", best_actions(bad), ["safe"])

actual_pixels = [1] * 99 + [0]
model_a_pixels = [1] * 100
model_b_pixels = [0] * 100
mse = lambda predicted: sum(F((x - y) ** 2) for x, y in zip(actual_pixels, predicted)) / 100
check("diagnostic_pixel_mse_A", mse(model_a_pixels), F(1, 100))
check("diagnostic_pixel_mse_B", mse(model_b_pixels), F(99, 100))
check("model_A_bad_route_regret", decision_regret(bad, "shortcut"), F(47, 5))
check("model_B_bad_route_regret", decision_regret(bad, "safe"), F(0))

check("merged_start_mixture_return", expected_shortcut(F(1, 2)), F(9, 5))
check("merged_start_good_regret", decision_regret(good, "safe"), F(5))
check("H1_without_tail", score(State("start", "good"), "shortcut", horizon=1), F(0))
correct_tail = lambda s: F(10) if s.mode == "good" else F(-6)
check("H1_correct_good_tail", score(State("start", "good"), "shortcut", horizon=1, tail=correct_tail), F(9))
check("H1_correct_bad_tail", score(State("start", "bad"), "shortcut", horizon=1, tail=correct_tail), F(-27, 5))
check("H1_incorrect_good_tail", score(State("start", "good"), "shortcut", horizon=1, tail=lambda s: F(3)), F(27, 10))
check("no_tail_after_true_terminal", score(State("start", "good"), "safe", horizon=1, tail=lambda s: F(999)), F(4))
check("discount_change", score(State("start", "good"), "shortcut", gamma=F(3, 10)), F(3))
check("finite_horizon_gamma_1", score(State("start", "good"), "shortcut", gamma=F(1)), F(10))
check("discount_zero", score(State("start", "good"), "shortcut", gamma=F(0)), F(0))

check("belief_p_0_8", expected_shortcut(F(4, 5)), F(153, 25))
check("belief_p_0_2", expected_shortcut(F(1, 5)), F(-63, 25))
check("belief_threshold_tie", expected_shortcut(F(47, 72)), F(4))
check("belief_MAP_good_can_still_prefer_safe", best_actions({"shortcut": expected_shortcut(F(11, 20)), "safe": F(4)}), ["safe"])
check("inspection_feedback", inspection_value(F(1, 2)), F(107, 20))
check("inspection_fixed_safe", inspection_value(F(1, 2), feedback=False, fixed="safe"), F(31, 10))
check("inspection_fixed_shortcut", inspection_value(F(1, 2), feedback=False, fixed="shortcut"), F(28, 25))
check("new_background_reward_bad_bg1", score(State("start", "bad", 1), "shortcut", bonus=F(20)), F(63, 5))
check("new_background_reward_bad_bg0", score(State("start", "bad", 0), "shortcut", bonus=F(20)), F(-27, 5))
check("background_preserved_through_transition", transition(State("start", "bad", 1), "shortcut")[1].background, 1)
check("risk_constraint_rejects_p_0_8_shortcut", F(1, 1) - F(4, 5) <= F(1, 10), False)
check("candidate_only_safe_gap", max(good.values()) - good["safe"], F(5))
check("biased_scores_preserve_current_ranking", best_actions({"shortcut": F(109), "safe": F(104)}), ["shortcut"])
check("biased_scores_absolute_error", max(abs(F(109) - good["shortcut"]), abs(F(104) - good["safe"])), F(100))

dyn_loss = lambda theta: ((theta - 1) ** 2 + (-theta + 1) ** 2) / 2
theta_old, alpha = F(0), F(1, 2)
gradient = 2 * (theta_old - 1)
theta_new = theta_old - alpha * gradient
check("theta_gradient_at_0", gradient, F(-2))
check("theta_update", theta_new, F(1))
check("theta_loss_before", dyn_loss(theta_old), F(1))
check("theta_loss_after", dyn_loss(theta_new), F(0))
predicted_shortcut = lambda theta, k: F(9, 10) * (2 + 8 * theta * k)
check("theta0_good_return", predicted_shortcut(theta_old, 1), F(9, 5))
check("theta0_bad_return", predicted_shortcut(theta_old, -1), F(9, 5))
check("theta1_good_return", predicted_shortcut(theta_new, 1), F(9))
check("theta1_bad_return", predicted_shortcut(theta_new, -1), F(-27, 5))
check("merged_input_deterministic_best_MSE", ((F(0) - 1) ** 2 + (F(0) + 1) ** 2) / 2, F(1))
check("merged_input_theta_gradient", 2 * (F(0) * F(0) - F(1)) * F(0), F(0))

p_support, q_support = [(F(-1), F(1, 2)), (F(1), F(1, 2))], [(F(-2), F(1, 2)), (F(2), F(1, 2))]
moment = lambda dist, fn: sum(prob * fn(z) for z, prob in dist)
check("same_latent_means", [moment(p_support, lambda z: z), moment(q_support, lambda z: z)], [F(0), F(0)])
check("nonlinear_tail_values", [moment(p_support, lambda z: z*z), moment(q_support, lambda z: z*z)], [F(1), F(4)])
check("affine_tail_same_expectation", [moment(p_support, lambda z: 3*z+2), moment(q_support, lambda z: 3*z+2)], [F(2), F(2)])
check("certificate_epsilon_eta_bound", 2 * F(2, 5) + F(3, 10), F(11, 10))

# Supplemental finite boundary checks; the general proof remains in the text.
bound_cases = 0
epsilon, eta = F(2, 5), F(3, 10)
for j0 in (F(-1), F(0), F(1, 5), F(1)):
    for j1 in (F(-1), F(0), F(1, 5), F(1)):
        for e0 in (-epsilon, F(0), epsilon):
            for e1 in (-epsilon, F(0), epsilon):
                real, estimated = [j0, j1], [j0 + e0, j1 + e1]
                for chosen in (0, 1):
                    if max(estimated) - estimated[chosen] <= eta:
                        assert max(real) - real[chosen] <= 2 * epsilon + eta
                        bound_cases += 1
checks.append({"name": "candidate_bound_finite_boundary_cases", "cases": bound_cases, "passed": True, "scope": "finite arithmetic supplement, not a universal proof"})

print(json.dumps({
    "preparation_id": "DS-LWM-20261010", "revision": 1,
    "origin": "AI-authored teacher verification", "learner_execution": "not_executed",
    "runtime": {"python": platform.python_version(), "executable": sys.executable},
    "summary": {"checks": len(checks), "passed": len(checks), "failed": 0},
    "checks": checks,
    "limitations": ["Not a neural-model training experiment", "Not a robotics or deployment result", "Not a learner response or capability assessment", "Finite numerical checks do not replace the written general proofs"]
}, ensure_ascii=False, indent=2))
