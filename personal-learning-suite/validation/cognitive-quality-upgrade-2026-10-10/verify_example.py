"""Finite mathematical checks for the synthetic lesson; no pedagogy/effect grader."""
from fractions import Fraction as F
from pathlib import Path
import json
import math

OUT = Path(__file__).resolve().parent
checks = []


def check(name, condition, details):
    checks.append({"name": name, "passed": bool(condition), "details": details})


def update(alpha, h, m, eta):
    gradient = (alpha * h - m) * h
    return gradient, alpha - eta * gradient


def scores(alpha, h, variances=(F(1), F(1, 100))):
    actions = (F(0), F(-1, 2))
    means = [alpha * h + a for a in actions]
    point = [(mu - 1) ** 2 for mu in means]
    expected = [p + v for p, v in zip(point, variances)]
    return {"means": means, "point": point, "expected": expected}


def best(values):
    return min(range(len(values)), key=values.__getitem__)


def public(row):
    return {key: [float(x) for x in value] for key, value in row.items()}


def main():
    histories = [(F(-1), F(0)), (F(1), F(0))]
    velocity_next = [current + (current - previous) for previous, current in histories]
    current_next = [current for previous, current in histories]
    check("history_required_under_velocity_model", velocity_next == [F(1), F(-1)],
          {"same_current": 0, "next_positions": [float(x) for x in velocity_next]})
    check("current_only_sufficient_under_changed_model", current_next == [F(0), F(0)],
          {"changed_rule": "next=current", "next_positions": [float(x) for x in current_next]})
    gradient, alpha = update(F(1), F(9, 10), F(138, 100), F(1, 10))
    check("demo_gradient_and_update", gradient == F(-432, 1000) and alpha == F(10432, 10000),
          {"gradient": float(gradient), "alpha": float(alpha)})
    old_error = (F(138, 100) - F(9, 10)) ** 2
    new_error = (F(138, 100) - alpha * F(9, 10)) ** 2
    check("local_fixed_reference_kl_decreases", new_error < old_error,
          {"before_parameter_square": float(old_error), "after_parameter_square": float(new_error)})
    h, m, v, a, delta = .9, 1.38, .2, 1., 1e-5
    def kl(param):
        return .5 * (v + (m - param * h) ** 2 - 1 - math.log(v))
    finite_diff = (kl(a + delta) - kl(a - delta)) / (2 * delta)
    check("analytic_gradient_matches_finite_difference", abs(finite_diff + .432) < 1e-8,
          {"finite_difference": finite_diff, "analytic": -.432})
    # Check the identity against exact expectation on several finite distributions.
    for index, (values, weights, goal) in enumerate([
        ([F(0), F(2)], [F(1, 2), F(1, 2)], F(1)),
        ([F(-2), F(1), F(4)], [F(1, 4), F(1, 2), F(1, 4)], F(3, 2)),
        ([F(3)], [F(1)], F(-1))]):
        mean = sum(x * w for x, w in zip(values, weights))
        variance = sum(w * (x - mean) ** 2 for x, w in zip(values, weights))
        exact = sum(w * (x - goal) ** 2 for x, w in zip(values, weights))
        check(f"expectation_identity_{index}", exact == (mean - goal) ** 2 + variance,
              {"exact": float(exact), "mean": float(mean), "variance": float(variance)})
    initial = scores(F(1), F(1))
    check("variance_can_reverse_action_choice", best(initial["point"]) == 0 and best(initial["expected"]) == 1,
          public(initial))
    equal = scores(F(1), F(1), (F(1), F(1)))
    check("equal_variance_need_not_reverse_choice", best(equal["point"]) == best(equal["expected"]) == 0,
          public(equal))
    demo = scores(alpha, F(1))
    demo_new = scores(alpha, F(1, 10))
    check("demo_uses_updated_parameter", demo["expected"] == [F("1.00186624"), F(".21866624")], public(demo))
    check("demo_reassessment_uses_new_input", demo_new["expected"] == [F("1.8022426624"), F("1.9579226624")], public(demo_new))
    whole_gradient, whole_alpha = update(F(1), F(1, 2), F(9, 10), F(1, 5))
    first = scores(whole_alpha, F(1))
    second = scores(whole_alpha, F(1, 10))
    check("whole_update_and_first_choice", whole_gradient == F(-1, 5) and whole_alpha == F(26, 25)
          and first["expected"] == [F("1.0016"), F(".2216")] and best(first["expected"]) == 1,
          {"gradient": float(whole_gradient), "alpha": float(whole_alpha), "first": public(first)})
    check("whole_reassessment_choice", second["expected"] == [F("1.802816"), F("1.958816")]
          and best(second["expected"]) == 0, public(second))
    # The two errors under review change observable behavior on this lesson.
    check("dropping_variance_detected_by_choice", best(first["point"]) != best(first["expected"]),
          {"point_choice": best(first["point"]), "expected_choice": best(first["expected"])})
    check("reusing_stale_input_detected_by_choice", best(first["expected"]) != best(second["expected"]),
          {"stale_choice": best(first["expected"]), "updated_choice": best(second["expected"])})
    # Means alone are compatible with either preferred action.
    other = scores(F(1), F(1), (F(1, 100), F(1)))
    check("means_alone_do_not_identify_choice", initial["means"] == other["means"]
          and best(initial["expected"]) != best(other["expected"]),
          {"first": public(initial), "other": public(other)})
    payload = {"date": "2026-10-10", "status": "pass" if all(x["passed"] for x in checks) else "fail",
               "checks": checks, "limits": ["Finite mathematical and error-discrimination checks only",
               "General expectation identity is proved in the material, not by these samples",
               "No neural training, environment rollout, learner performance or learning effect measured"]}
    (OUT / "example-checks.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "checks": len(checks)}, ensure_ascii=False))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
