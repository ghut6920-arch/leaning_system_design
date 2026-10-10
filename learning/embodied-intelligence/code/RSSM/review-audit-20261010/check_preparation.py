"""Review checks only. Keep the preparation, its original outputs and learner state intact."""
from pathlib import Path
from fractions import Fraction as F
import hashlib
import itertools
import json
import math
import re
import runpy
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
COURSE = HERE.parents[2]
PREP = COURSE / "prep/rssm-review-20261010"
AUTHOR_CODE = COURSE / "code/RSSM/review-20261010"
REPORT = COURSE / "reviews/2026-10-10-rssm-preparation-quality-review.md"
OUTPUT = COURSE / "reviews/2026-10-10-rssm-preparation-quality-checks.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def direct_candidates(d, mq, vq=F(1, 8), kappa=F(0)):
    """Expand independent noises directly, without the author's covariance recurrence."""
    alpha = F(4, 5)
    rows = []
    for a, b in itertools.product((-1, 0, 1), repeat=2):
        d1 = d / 2 + mq / 2 + a
        m1 = alpha * d1
        m2 = alpha * ((1 + alpha) * d1 / 2 + b)
        noise1, noise2 = F(1, 4) + kappa * a * a, F(1, 4) + kappa * b * b
        v1 = (alpha / 2) ** 2 * vq + noise1
        v2 = (alpha * (1 + alpha) / 4) ** 2 * vq + (alpha / 2) ** 2 * noise1 + noise2
        cost = m1 * m1 + m2 * m2 + v1 + v2 + F(1, 10) * (a * a + b * b)
        rows.append((cost, (a, b)))
    return sorted(rows)


def main():
    manifest = json.loads((PREP / "delivery-manifest.json").read_text(encoding="utf-8"))
    retained = [Path(row["path"]) for row in manifest["files"] + manifest["protected_files"]]
    before = {str(path): sha(path) for path in retained}
    manifest_errors = [row["path"] for row in manifest["files"] + manifest["protected_files"]
                       if sha(Path(row["path"])).lower() != row.get("sha256", row.get("hash", "")).lower()]
    # Load without executing __main__, which would overwrite the author's result JSON.
    author = runpy.run_path(str(AUTHOR_CODE / "verify_demo.py"), run_name="review_import")
    rerun = author["run_checks"]()
    independent = []

    def check(name, condition, details):
        independent.append({"name": name, "passed": bool(condition), "details": details})

    for name, d, mq, kappa, actions, cost in [
        ("E initial", F(2), F(4, 5), F(0), (-1, 0), F(".861544")),
        ("E action-dependent noise", F(2), F(4, 5), F(2), (0, 0), F("2.846664")),
        ("E replan", F(2, 5), F(-9, 100), F(0), (0, 0), F(".60403056")),
        ("W initial", F(-1), F(-1, 2), F(0), (1, 0), F(".7486")),
        ("W replan", F(1, 4), F(27, 20), F(0), (-1, 0), F(".722536"))]:
        best_cost, best_actions = direct_candidates(d, mq, kappa=kappa)[0]
        check(name, best_cost == cost and best_actions == actions,
              {"best_actions": list(best_actions), "best_cost": float(best_cost)})
    gradient = (F(4, 5) - F(1, 2)) / F(1, 4)
    check("W parameter block", gradient == F(6, 5) and F(4, 5) - F(1, 20) * gradient == F(37, 50),
          {"gradient": float(gradient), "new_alpha": .74})
    # Reconstruct the missing-observation path's moments and expected ELBO terms.
    d2_mean, d2_var = F(5, 4), F(1, 32)
    z2_mean, z2_var = F(1), F(27, 100)
    cov_d2_z2 = F(1, 40)
    d3_mean = (d2_mean + z2_mean) / 2 - F(1, 2)
    d3_var = (d2_var + z2_var + 2 * cov_d2_z2) / 4
    z3_mean = F(2, 5) * d3_mean - F(1, 10)
    z3_var = F(4, 25) * d3_var + F(1, 8)
    check("W missing-step marginal", d3_var == F(".0878125") and z3_mean == F(".15") and z3_var == F(".13905"),
          {"d3_mean": float(d3_mean), "d3_variance": float(d3_var), "z3_mean": float(z3_mean), "z3_variance": float(z3_var)})
    constant = -.5 * math.log(2 * math.pi * .25)
    kl1 = .5 * (math.log(2) + .5 + .3 ** 2 / .25 - 1)
    expected_difference_square = F(4, 25) * (d3_var + d3_mean ** 2) + F(2, 25) * d3_mean + F(1, 100)
    kl3 = .5 * (math.log(2) + .5 + float(expected_difference_square / F(1, 4)) - 1)
    elbo = 2 * constant - .43 - .5231 - kl1 - kl3
    check("W missing-step ELBO", abs(elbo - (-2.0509298858)) < 1e-10,
          {"ELBO": elbo, "KL1": kl1, "expected_KL3": kl3})
    # Exact evidence here follows the specified linear model, not the environment.
    log_normal = lambda value, mean, var: -.5 * (math.log(2 * math.pi * var) + (value - mean) ** 2 / var)
    exact_evidence = log_normal(.2, .8, .5) + log_normal(-.2, .5, .3062 + .25)
    check("W lower bound vs exact model evidence", elbo <= exact_evidence,
          {"ELBO": elbo, "exact_model_log_evidence": exact_evidence, "gap": exact_evidence - elbo})
    # This illustrates the limit of means; it is not part of the prepared lesson.
    check("nonlinear mean counterexample", (F(-1) ** 2 + F(1) ** 2) / 2 != ((F(-1) + F(1)) / 2) ** 2,
          {"E_Z_squared": 1, "squared_E_Z": 0, "role": "review improvement example only"})
    docs = list(PREP.glob("*.md")) + ([REPORT] if REPORT.is_file() else [])
    broken, link_count = [], 0
    for path in docs:
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = target.strip().strip("<>").split("#")[0]
            if not target or "://" in target:
                continue
            target = re.sub(r":\d+$", "", unquote(target))
            link_count += 1
            if not (path.parent / target).resolve().is_file():
                broken.append({"file": path.name, "target": target})
    after_errors = [str(path) for path in retained if sha(path) != before[str(path)]]
    payload = {"date": "2026-10-10", "thread_id": "01a121ab-ab17-78c3-a5d3-73eb99693324",
        "author_checks_rerun": {"checks": rerun["check_count"], "passed": rerun["all_passed"]},
        "direct_formula_review_checks": independent,
        "delivery_fingerprints_checked": len(manifest["files"]), "protected_fingerprints_checked": len(manifest["protected_files"]),
        "manifest_errors": manifest_errors, "originals_changed_during_review": after_errors,
        "local_links_checked": link_count, "broken_links": broken,
        "limits": ["No real teaching, learner outputs, neural training or environment rollout",
        "Reviewer's direct derivation is not an independent model or blind review",
        "Finite mathematical checks do not establish teaching effects", "No browser rendering check performed"]}
    payload["status"] = "pass" if rerun["all_passed"] and all(x["passed"] for x in independent) and not (manifest_errors or after_errors or broken) else "fail"
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "author_checks": rerun["check_count"], "direct_checks": len(independent),
        "manifest_errors": manifest_errors, "originals_changed": after_errors, "broken_links": broken}, ensure_ascii=False))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
