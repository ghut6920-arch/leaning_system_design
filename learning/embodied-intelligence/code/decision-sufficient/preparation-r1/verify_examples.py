"""Revision 1, 2026-10-11; AI-authored preparation verification.

Source: the explicit toy specifications in this lesson's disciplinary analysis.
No trained world model, user implementation, or real control experiment is run.
Python standard library only. JSON is written to stdout; no learning state is read.
"""

from fractions import Fraction
import json


def transition(x, action):
    return max(0, min(2, x + action))


def reward(x, c, action, task):
    next_x = transition(x, action)
    return -(next_x - 2) ** 2 - (6 * c * (next_x == 2) if task == 1 else 0)


def main():
    actions = {"L": -1, "R": 1}
    decisions = []
    for task in (0, 1):
        for c in (0, 1):
            values = {name: reward(1, c, action, task) for name, action in actions.items()}
            decisions.append({"task": task, "x": 1, "c": c, "values": values,
                              "best_action": max(values, key=values.get)})

    # Exhaustive congruence checks over this finite toy's entire state/action domain.
    conflicts = {}
    for task in (0, 1):
        witnesses = []
        for x in range(3):
            for name, action in actions.items():
                r0, r1 = reward(x, 0, action, task), reward(x, 1, action, task)
                if r0 != r1:
                    witnesses.append({"z": x, "action": name, "rewards": [r0, r1]})
        conflicts[str(task)] = witnesses
    assert not conflicts["0"]
    assert decisions[2]["best_action"] != decisions[3]["best_action"]

    # 102 equally weighted coordinates. x prediction reverses the action ranking.
    real_values = {"L": -4, "R": 0}
    pixel_model_values = {"L": 0, "R": -4}
    decision_model_values = dict(real_values)
    pixel_mse = Fraction(4, 102)
    decision_mse = Fraction(50, 102)
    assert pixel_mse < decision_mse
    assert max(pixel_model_values, key=pixel_model_values.get) == "L"
    assert max(decision_model_values, key=decision_model_values.get) == "R"

    # Generic action-gap illustration; not a theorem proved by finite enumeration.
    gap = real_values["R"] - real_values["L"]
    errors = {"0.4": {"L": -3.6, "R": -0.4},
              "2.5": {"L": -1.5, "R": -2.5}}
    assert max(errors["0.4"], key=errors["0.4"].get) == "R"
    assert max(errors["2.5"], key=errors["2.5"].get) == "L"

    # Independent enumeration of the additional explicitly specified cases.
    expanded_actions = []
    for c in (0, 1):
        values = {name: reward(0, c, action, 0) for name, action in actions.items()}
        next_j = 2 if c == 0 else 0
        values["J"] = -(next_j - 2) ** 2
        expanded_actions.append({"c": c, "values": values,
                                 "best_action": max(values, key=values.get)})
    assert expanded_actions[0]["values"] == {"L": -4, "R": -1, "J": 0}
    assert expanded_actions[1]["values"] == {"L": -4, "R": -1, "J": -4}

    outcomes = {"U": [(0, Fraction(1, 2)), (2, Fraction(1, 2))],
                "V": [(1, Fraction(1))]}
    stochastic = {}
    for name, distribution in outcomes.items():
        mean = sum(y * p for y, p in distribution)
        expected_reward = sum(-(y - 1) ** 2 * p for y, p in distribution)
        second_moment = sum(y ** 2 * p for y, p in distribution)
        assert expected_reward == -second_moment + 2 * mean - 1
        stochastic[name] = {"mean": float(mean), "expected_reward": float(expected_reward),
                            "reward_of_mean": float(-(mean - 1) ** 2),
                            "second_moment": float(second_moment)}
    assert stochastic["U"]["expected_reward"] == -1
    assert stochastic["V"]["expected_reward"] == 0
    linear_mean = Fraction(1, 4) * 2 + Fraction(3, 4) * 6
    linear_reward = Fraction(1, 4) * 7 + Fraction(3, 4) * 19
    assert linear_mean == 5 and linear_reward == 16

    gamma = Fraction(9, 10)
    planning = {"H1_zero_terminal": {"M": -2, "S": 1},
                "H1_wrong_terminal": {"M": float(-2 + gamma * 2), "S": 1},
                "H2": {"M": float(-2 + gamma * 8), "S": 1}}
    assert planning["H1_wrong_terminal"]["M"] == -0.2
    assert planning["H2"]["M"] == 5.2

    history = []
    for previous_position in (-1, 1):
        velocity = -previous_position
        values = {str(a): -(velocity + a) ** 2 for a in (-1, 1)}
        history.append({"previous_x": previous_position, "current_x": 0,
                        "velocity": velocity, "action_values": values,
                        "best_action": max(values, key=values.get)})
    assert history[0]["best_action"] == "-1"
    assert history[1]["best_action"] == "1"

    # A concrete witness that V_x is not closed for all c-dependent policies.
    updated_zero_value = {str(c): reward(1, c, -1 if c == 0 else 1, 0) for c in (0, 1)}
    assert updated_zero_value == {"0": -4, "1": 0}

    output = {
        "status": "teacher_preparation_verification_only",
        "specification": {"H": 1, "gamma": 0.9, "reward_timing": "after_action",
                          "termination": "after_one_action", "representation": "z=x"},
        "reward_change_decisions": decisions,
        "exhaustive_reward_aliasing_witnesses": conflicts,
        "pixel_comparison": {
            "coordinates": 102,
            "low_pixel_error_model": {"mse": str(pixel_mse), "decimal": float(pixel_mse),
                                      "estimated_values": pixel_model_values,
                                      "chosen_action": "L", "actual_reward": -4},
            "task_focused_model": {"mse": str(decision_mse), "decimal": float(decision_mse),
                                   "estimated_values": decision_model_values,
                                   "chosen_action": "R", "actual_reward": 0}},
        "action_gap_example": {"true_gap": gap, "strict_safe_error_threshold": gap / 2,
                               "illustrative_estimates": errors},
        "new_action_case": expanded_actions,
        "random_outcome_case": stochastic,
        "linear_tool_example": {"mean": float(linear_mean),
                                "expected_reward": float(linear_reward)},
        "planning_case": planning,
        "history_case": history,
        "value_equivalence_bridge": {"gamma_times_next_c_difference": float(gamma),
                                    "updated_zero_value_at_x1": updated_zero_value},
        "limits": ["Does not establish neural trainability or benchmark superiority.",
                   "No deployment or learner performance occurred.",
                   "The action-gap theorem still requires its algebraic proof.",
                   "No numerical ground truth is available for the T5 deployment."]
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
