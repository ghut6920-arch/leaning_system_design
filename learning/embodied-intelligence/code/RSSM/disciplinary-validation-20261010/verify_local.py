"""AI-authored teacher verification, v1.0, 2026-10-10.

Scope: M1 trajectory counterexample and M4 fixed-q local update only.
No learner data, trained RSSM, performance experiment, or teaching event.
Run from the embodied-intelligence workspace:
  python code/RSSM/disciplinary-validation-20261010/verify_local.py
"""
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
checks = []


def check(name, passed, detail):
    checks.append({"name": name, "passed": bool(passed), "detail": detail})
    if not passed:
        raise AssertionError(name)


def close(actual, expected, tolerance=1e-9):
    return abs(actual - expected) <= tolerance


def kl(alpha, fixed_q_mean):
    return 0.5 * (math.log(0.25 / 0.125)
                  + (0.125 + (fixed_q_mean - 2 * alpha)**2) / 0.25 - 1)


cases = []
for observation, expected_gradient, expected_alpha in [(0, 8, 0.8), (2, 0, 1), (-1, 12, 0.7)]:
    q_old_mean = (2 + observation) / 2
    gradient = (2 - q_old_mean) * 2 / 0.25
    step = 1e-6
    finite_difference = (kl(1 + step, q_old_mean) - kl(1 - step, q_old_mean)) / (2 * step)
    alpha_new = 1 - 0.025 * gradient
    q_new_mean = (2 * alpha_new + observation) / 2
    future_mean = alpha_new * (1 + 0.5 * q_new_mean)
    check(f"o={observation}: analytic gradient", close(gradient, expected_gradient), gradient)
    check(f"o={observation}: fixed-q finite difference", close(gradient, finite_difference, 1e-7), finite_difference)
    check(f"o={observation}: parameter step", close(alpha_new, expected_alpha), alpha_new)
    check(f"o={observation}: fixed-block nonincrease", kl(alpha_new, q_old_mean) <= kl(1, q_old_mean) + 1e-10,
          {"before": kl(1, q_old_mean), "after": kl(alpha_new, q_old_mean)})
    cases.append({"observation": observation, "q_old_mean": q_old_mean, "gradient": gradient,
                  "alpha_new": alpha_new, "same_h_prior_mean": 2 * alpha_new,
                  "q_new_mean": q_new_mean, "future_marginal_mean": future_mean,
                  "fixed_old_q_kl_before": kl(1, q_old_mean),
                  "fixed_old_q_kl_after": kl(alpha_new, q_old_mean)})

by_observation = {c["observation"]: c for c in cases}
check("o=2: zero mean gradient does not imply zero KL", by_observation[2]["gradient"] == 0 and kl(1, 2) > 0,
      kl(1, 2))
check("E main-chain future mean preserved", close(by_observation[0]["future_marginal_mean"], 1.12), 1.12)
check("o=-1: posterior recomputation", close(by_observation[-1]["q_new_mean"], 0.2), by_observation[-1]["q_new_mean"])
check("o=-1: optimized future marginal", close(by_observation[-1]["future_marginal_mean"], 0.77), by_observation[-1]["future_marginal_mean"])
no_update_mean = 1 * (1 + 0.5 * by_observation[-1]["q_old_mean"])
check("o=-1: filtering without parameter learning", close(no_update_mean, 1.25), no_update_mean)

legal_pairs = {(1, 2), (-1, -2)}
independent_pairs = list(itertools.product((-1, 1), (-2, 2)))
illegal_pairs = [pair for pair in independent_pairs if pair not in legal_pairs]
check("M1 coherent pairs satisfy dynamics", all(second == 2 * first for first, second in legal_pairs), sorted(legal_pairs))
check("M1 independent heads have same one-time marginals",
      all(sum(first == value for first, second in independent_pairs) == 2 for value in (-1, 1))
      and all(sum(second == value for first, second in independent_pairs) == 2 for value in (-2, 2)), independent_pairs)
check("M1 independent illegal probability", close(len(illegal_pairs) / 4, 0.5), illegal_pairs)
coherent_additive_cost = sum(first**2 + second**2 for first, second in legal_pairs) / 2
independent_additive_cost = sum(first**2 + second**2 for first, second in independent_pairs) / 4
check("M1 same marginals can preserve additive expected cost", coherent_additive_cost == independent_additive_cost == 5,
      {"coherent": coherent_additive_cost, "independent": independent_additive_cost})

manifest = json.loads((ROOT / "prep/rssm-review-20261010/delivery-manifest.json").read_text(encoding="utf-8-sig"))
protected = []
for item in manifest["files"] + manifest["protected_files"]:
    path = Path(item["path"])
    expected = item.get("sha256", item.get("hash")).lower()
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    protected.append({"path": str(path), "unchanged": actual == expected})
check("original delivery and protected files unchanged", all(item["unchanged"] for item in protected), len(protected))

basis = []
for path in [ROOT / "prep/rssm-review-20261010/03-learner-materials.md",
             ROOT.parents[1] / "docs/research/2026-10-10-disciplinary-analysis/研究报告.md",
             ROOT.parents[1] / "docs/research/2026-10-10-disciplinary-analysis/单元学科分析工作底稿.md"]:
    basis.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

result = {"version": "1.0", "date": "2026-10-10", "scope": "teacher_model_mechanism_only",
          "teaching": "not_executed", "neural_training": "not_executed", "learner_results": "none",
          "check_count": len(checks), "all_passed": all(c["passed"] for c in checks),
          "checks": checks, "observation_cases": cases, "protected_files": protected, "basis_files": basis}
(HERE / "verification-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"check_count": len(checks), "all_passed": result["all_passed"],
                  "original_files_unchanged": len(protected)}, ensure_ascii=False))
