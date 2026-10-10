"""AI-authored preparation verifier, revision2, 2026-10-09.

Source: self-contained finite probability identities and hand-specified data.
No neural RSSM, parameter learning, learner submission, or control experiment.
Execute with the Python standard library only.
"""

from itertools import product
from math import isclose, log
from fractions import Fraction
import json


def sequence_elbo_check():
    """Enumerate a two-step causal variational family, not a smoothing oracle.

    z in {0,1}; arrival observations are o1=red, o2=blue.
    Initial generative probabilities: (.5,.5).
    Action a1=hold gives P(z2=z1)=.9.
    P(red|z=0)=.2; P(red|z=1)=.8.
    q1 is local Bayes at t1; q2 is local Bayes given z1 and o2.
    h2=z1 is a pedagogical deterministic history representation.
    """
    initial = (0.5, 0.5)
    obs1 = (0.2, 0.8)
    obs2 = (0.8, 0.2)

    def transition(z2, z1):
        return 0.9 if z2 == z1 else 0.1

    norm1 = sum(initial[z] * obs1[z] for z in (0, 1))
    q1 = tuple(initial[z] * obs1[z] / norm1 for z in (0, 1))
    q2 = {}
    for z1 in (0, 1):
        norm2 = sum(transition(z2, z1) * obs2[z2] for z2 in (0, 1))
        q2[z1] = tuple(transition(z2, z1) * obs2[z2] / norm2 for z2 in (0, 1))

    paths = list(product((0, 1), repeat=2))
    generative_joint = {
        (z1, z2): initial[z1] * obs1[z1] * transition(z2, z1) * obs2[z2]
        for z1, z2 in paths
    }
    q_joint = {(z1, z2): q1[z1] * q2[z1][z2] for z1, z2 in paths}
    evidence = sum(generative_joint.values())
    full_posterior = {path: probability / evidence for path, probability in generative_joint.items()}
    elbo_path = sum(q_joint[path] * log(generative_joint[path] / q_joint[path]) for path in paths)
    reconstruction = sum(q_joint[z1, z2] * (log(obs1[z1]) + log(obs2[z2])) for z1, z2 in paths)
    kl1 = sum(q1[z] * log(q1[z] / initial[z]) for z in (0, 1))
    kl2_conditional = {
        z1: sum(q2[z1][z2] * log(q2[z1][z2] / transition(z2, z1)) for z2 in (0, 1))
        for z1 in (0, 1)
    }
    expected_kl2 = sum(q1[z1] * kl2_conditional[z1] for z1 in (0, 1))
    elbo_terms = reconstruction - kl1 - expected_kl2
    gap = log(evidence) - elbo_path
    kl_to_full_posterior = sum(q_joint[path] * log(q_joint[path] / full_posterior[path]) for path in paths)

    assert isclose(sum(q_joint.values()), 1.0, abs_tol=1e-12)
    assert isclose(elbo_path, elbo_terms, abs_tol=1e-12)
    assert isclose(gap, kl_to_full_posterior, abs_tol=1e-12)
    assert gap > 0.0  # Causal q is not generally the full-sequence posterior.
    # Dropping the history expectation and evaluating only at z1=0 is incorrect.
    wrong_no_outer_expectation = reconstruction - kl1 - kl2_conditional[0]
    assert not isclose(wrong_no_outer_expectation, elbo_path, abs_tol=1e-12)
    return {
        "evidence": evidence,
        "log_evidence": log(evidence),
        "elbo_path": elbo_path,
        "elbo_reconstruction_minus_expected_kls": elbo_terms,
        "gap": gap,
        "kl_q_to_full_sequence_posterior": kl_to_full_posterior,
        "wrong_elbo_without_history_expectation": wrong_no_outer_expectation,
        "scope": "finite enumeration identity; not a general proof or trained RSSM",
    }


def mean_substitution_check():
    # A nonlinear deterministic map does not commute with expectation.
    states = (-1.0, 1.0)
    weights = (0.5, 0.5)
    expected_output = sum(w * z * z for w, z in zip(weights, states))
    output_at_expected_input = sum(w * z for w, z in zip(weights, states)) ** 2
    assert expected_output == 1.0
    assert output_at_expected_input == 0.0
    return {
        "E_f_z": expected_output,
        "f_E_z": output_at_expected_input,
        "scope": "explicit counterexample to substituting means through nonlinear transitions",
    }


def finite_bridge_check():
    """Exact belief propagation and receding-horizon planning bridge.

    L/H states, 0.1 action transition noise, red/blue noisy observations.
    Utility is a planning objective, not an observed reward revealing state.
    No neural h/z parameterization or learned reward model is claimed.
    """
    def predict(belief, action):
        if action == "S":
            return Fraction(1, 10) + Fraction(4, 5) * belief
        if action == "F":
            return Fraction(9, 10) - Fraction(4, 5) * belief
        raise ValueError(action)

    def update(belief, observation):
        likelihood_h = Fraction(4, 5) if observation == "R" else Fraction(1, 5)
        likelihood_l = 1 - likelihood_h
        return belief * likelihood_h / (belief * likelihood_h + (1 - belief) * likelihood_l)

    def candidates(belief):
        table = {}
        for first, second in product("SF", repeat=2):
            b1 = predict(belief, first)
            b2 = predict(b1, second)
            # Independent state enumeration checks the affine belief recursion.
            enumerated = 0
            for s0, s1, s2 in product((0, 1), repeat=3):
                initial = belief if s0 else 1 - belief
                p1_h = predict(Fraction(s0), first)
                p2_h = predict(Fraction(s1), second)
                path = initial * (p1_h if s1 else 1 - p1_h) * (p2_h if s2 else 1 - p2_h)
                enumerated += path * (s1 + s2)
            assert enumerated == b1 + b2
            table[first + second] = {"b1": str(b1), "b2": str(b2), "score": str(b1 + b2), "decimal": float(b1 + b2)}
        return table

    b_after_red = update(Fraction(1, 2), "R")
    assert b_after_red == Fraction(4, 5)
    first_table = candidates(b_after_red)
    assert max(first_table, key=lambda a: first_table[a]["decimal"]) == "SS"
    next_prior = predict(b_after_red, "S")
    assert next_prior == Fraction(37, 50)
    b_after_blue = update(next_prior, "B")
    assert b_after_blue == Fraction(37, 89)
    second_table = candidates(b_after_blue)
    assert max(second_table, key=lambda a: second_table[a]["decimal"]) == "FS"
    return {
        "posterior_after_red": str(b_after_red),
        "first_candidate_table": first_table,
        "executed_action": "S",
        "arrival_prior": str(next_prior),
        "actual_arrival_observation": "B",
        "posterior_after_blue": str(b_after_blue),
        "replanned_candidate_table": second_table,
        "new_first_action": "F",
        "scope": "exact constructed two-state bridge; utility is not observed reward; not neural RSSM or real control experiment",
    }


if __name__ == "__main__":
    print(json.dumps({"revision": 2, "sequence_elbo": sequence_elbo_check(), "nonlinear_mean": mean_substitution_check(), "finite_bridge": finite_bridge_check()}, indent=2, ensure_ascii=False))
