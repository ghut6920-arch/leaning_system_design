"""AI-authored RSSM preparation verifier, v1, 2026-10-09.

Educational model invented for this review; not PlaNet parameters or a learner
implementation. Python standard library only. All normal variances use variance,
not standard deviation. Outputs are teacher checks, not training or robot tests.

h_1=0; h_t=.5*h_(t-1)+.5*z_(t-1)+a_(t-1)
p(z_t|h_t)=N(h_t,1); p(o_t|z_t)=N(z_t,.25)
q(z_t|h_t,o_t)=N(.2*h_t+.8*o_t,.2)
"""

import itertools
import json
import math


def representative_trace(obs, actions):
    """One chosen mean path for tracing; not E_q of the complete computation."""
    h, previous_z = 0.0, None
    rows = []
    for index, observation in enumerate(obs):
        if index:
            h = .5 * h + .5 * previous_z + actions[index - 1]
        posterior_mean = .2 * h + .8 * observation
        rows.append(dict(t=index + 1, h=h, prior_mean=h,
                         prior_variance=1.0, observation=observation,
                         posterior_mean=posterior_mean,
                         posterior_variance=.2))
        previous_z = posterior_mean
    return rows


def exact_variational_elbo(obs, actions):
    """Analytic expectations under the entire forward variational q path."""
    mh, mz, vh, vz, chz = 0., 0., 0., 0., 0.
    rows = []
    for index, observation in enumerate(obs):
        if index:
            mh = .5 * mh + .5 * mz + actions[index - 1]
            vh = .25 * (vh + 2 * chz + vz)
        mz = .2 * mh + .8 * observation
        vz = .04 * vh + .2
        chz = .2 * vh
        expected_log_observation = (
            -.5 * math.log(2 * math.pi * .25)
            -.5 * ((observation - mz) ** 2 + vz) / .25)
        expected_kl = .5 * (
            math.log(1 / .2) + .2
            + .64 * ((observation - mh) ** 2 + vh) - 1)
        rows.append(dict(t=index + 1, mean_h=mh, variance_h=vh,
                         mean_z=mz, variance_z=vz,
                         expected_log_observation=expected_log_observation,
                         expected_kl=expected_kl))
    return sum(r['expected_log_observation'] - r['expected_kl']
               for r in rows), rows


def exact_log_evidence(obs, actions):
    """Kalman computation of log p(o_1:T|a), independent of variational q."""
    mh, mz, vh, vz, chz = 0., 0., 0., 1., 0.
    log_evidence = 0.
    for index, observation in enumerate(obs):
        if index:
            mh = .5 * mh + .5 * mz + actions[index - 1]
            mz = mh
            vh = .25 * (vh + 2 * chz + vz)
            chz, vz = vh, vh + 1.
        innovation = observation - mz
        innovation_variance = vz + .25
        log_evidence += -.5 * (math.log(2 * math.pi * innovation_variance)
                               + innovation ** 2 / innovation_variance)
        kh, kz = chz / innovation_variance, vz / innovation_variance
        mh += kh * innovation
        mz += kz * innovation
        vh, chz, vz = (vh - kh * chz,
                       chz - kh * vz,
                       vz - kz * vz)
    return log_evidence


def rollout(h, z_mean, z_variance, actions, goal=1.):
    """Prior-only future rollout, conditional on fixed h and a q root for z.

    No observation is accepted by this interface. h becomes uncertain marginally
    after propagating root z. A^2=A in this toy; covariance is still propagated.
    """
    mh, mz, vh, vz, chz = h, z_mean, 0., z_variance, 0.
    costs, rows = [], []
    for action in actions:
        mh = .5 * mh + .5 * mz + action
        mz = mh
        vh = .25 * (vh + 2 * chz + vz)
        chz, vz = vh, vh + 1.
        cost = (mz - goal) ** 2 + vz + .1 * action ** 2
        costs.append(cost)
        rows.append(dict(action=action, mean_h=mh, variance_h=vh,
                         mean_z=mz, variance_z=vz, expected_cost=cost))
    return sum(costs), rows


def candidate_table(h, z_mean, z_variance):
    rows = []
    for actions in itertools.product((-.5, 0., .5), repeat=2):
        cost, trajectory = rollout(h, z_mean, z_variance, actions)
        rows.append(dict(actions=actions, expected_cost=cost,
                         trajectory=trajectory))
    return sorted(rows, key=lambda r: r['expected_cost'])


def work_scenario(observations, actions, new_observation):
    trace = representative_trace(observations, actions)
    elbo, expectation_rows = exact_variational_elbo(observations, actions)
    evidence = exact_log_evidence(observations, actions)
    table = candidate_table(trace[-1]['h'], trace[-1]['posterior_mean'], .2)
    first_action = table[0]['actions'][0]
    h_next = .5 * trace[-1]['h'] + .5 * trace[-1]['posterior_mean'] + first_action
    new_z_mean = .2 * h_next + .8 * new_observation
    next_table = candidate_table(h_next, new_z_mean, .2)
    assert evidence + 1e-12 >= elbo
    return dict(observations=observations, history_actions=actions,
                representative_trace=trace, exact_q_elbo=elbo,
                exact_model_log_evidence=evidence, gap=evidence - elbo,
                elbo_expectation_rows=expectation_rows,
                first_candidate_table=table, new_observation=new_observation,
                next_h=h_next, new_posterior_mean=new_z_mean,
                replanned_candidate_table=next_table)


def main():
    obs, actions = (1., 1.5, .7), (.5, -.5)
    trace = representative_trace(obs, actions)
    elbo, elbo_rows = exact_variational_elbo(obs, actions)
    evidence = exact_log_evidence(obs, actions)
    first = candidate_table(trace[-1]['h'], trace[-1]['posterior_mean'], .2)
    chosen_first_action = first[0]['actions'][0]
    h4 = .5 * trace[-1]['h'] + .5 * trace[-1]['posterior_mean'] + chosen_first_action
    new_observation = -.5
    new_z_mean = .2 * h4 + .8 * new_observation
    replanned = candidate_table(h4, new_z_mean, .2)

    # Mathematical anchors: lower bound, covariance propagation, MPC interface.
    assert evidence + 1e-12 >= elbo
    assert all(r['expected_kl'] >= 0 for r in elbo_rows)
    assert all(abs(row['trajectory'][0]['variance_z'] - 1.05) < 1e-12
               and abs(row['trajectory'][1]['variance_z'] - 1.3) < 1e-12
               for row in first)
    assert first[0]['actions'] == (.5, 0.)
    assert replanned[0]['actions'][0] == .5 != first[0]['actions'][1]
    work_scenarios = dict(
        W1=work_scenario((.5, 0., -.2), (0., .5), -1.),
        W3=work_scenario((.2, .9, -.4), (-.5, .5), -.8))

    print(json.dumps(dict(
        version='teacher-toy-v1', observations=obs, history_actions=actions,
        representative_trace=trace, exact_q_elbo=elbo,
        exact_model_log_evidence=evidence, gap=evidence - elbo,
        elbo_expectation_rows=elbo_rows, first_candidate_table=first,
        new_observation=new_observation, h4=h4, new_posterior_mean=new_z_mean,
        replanned_candidate_table=replanned,
        work_scenarios=work_scenarios,
        checks='lower-bound, KL nonnegativity, prior variance, changed MPC action'),
        ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
