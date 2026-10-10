"""AI reference v1: neural RSSM information flow, 2026-10-09.

Executable Python interface definitions, requiring a supplied neural backend.
No backend is trained or executed in this preparation. The numeric anchor is
separate. Event order: o_t -> a_t -> (o_{t+1}, r_{t+1}).
"""

from dataclasses import dataclass
from typing import Any, Protocol, Sequence


class Distribution(Protocol):
    def sample(self) -> Any: ...


@dataclass(frozen=True)
class StateSample:
    h: Any
    z: Any


class Backend(Protocol):
    def recur(self, h_previous: Any, z_previous: Any, action_previous: Any) -> Any: ...
    def prior(self, h: Any) -> Distribution: ...
    def posterior(self, h: Any, observation: Any) -> Distribution: ...
    def reward_mean(self, h: Any, z: Any) -> Any: ...


def observe_step(model: Backend, previous: StateSample, action_previous: Any,
                 observation: Any) -> tuple[StateSample, Distribution, Distribution]:
    h = model.recur(previous.h, previous.z, action_previous)
    prior = model.prior(h)
    posterior = model.posterior(h, observation)
    return StateSample(h, posterior.sample()), prior, posterior


def imagine(model: Backend, start: StateSample,
            candidate_actions: Sequence[Any]) -> list[tuple[StateSample, Any]]:
    state = start
    trajectory = []
    for action in candidate_actions:
        h = model.recur(state.h, state.z, action)
        state = StateSample(h, model.prior(h).sample())
        trajectory.append((state, model.reward_mean(state.h, state.z)))
    return trajectory


def evaluate_candidates(model: Backend, starts: Sequence[StateSample],
                        candidates: Sequence[Sequence[Any]], discount: float = 1.0) -> list[Any]:
    """Average trajectories over current-state samples and transition samples.

    Each candidate starts from the same given particle population. No real
    environment execution or future observations occur inside this function.
    Finite Monte Carlo averages approximate model expectations; they do not
    certify calibration or real-world return.
    """
    if not starts:
        raise ValueError("A nonempty population of current-state samples is required.")
    scores = []
    for actions in candidates:
        sample_returns = []
        for start in starts:
            sample_returns.append(sum(discount ** k * reward
                                      for k, (_, reward) in enumerate(imagine(model, start, actions))))
        scores.append(sum(sample_returns) / len(sample_returns))
    return scores
