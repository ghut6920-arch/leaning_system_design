"""AI preparation QA v1: independent closed-form arithmetic and local links.
No learner evidence, trained neural model, or real environment execution.
"""

from fractions import Fraction as F
from itertools import product
import importlib.util
import json
from pathlib import Path
import re


WORKSPACE = Path(__file__).resolve().parents[3]
PACKAGE = WORKSPACE / "artifacts/preparation-tests/2026-10-09-rssm-01a11fef"
data = json.loads((PACKAGE / "teacher-numeric-output-v1.json").read_text(encoding="utf-8-sig"))


def closed_score(mean, variance, actions):
    # Closed form: no call to the teaching predict/evaluate implementations.
    return -sum((mean + sum(actions[:k + 1]) - 2) ** 2
                + variance + F(k + 1, 4) + F(1, 10) * action ** 2
                for k, action in enumerate(actions))


expected = {tuple(a): closed_score(F(4, 9), F(5, 9), a)
            for a in product((-1, 0, 1), repeat=2)}
for row in data["planning1"]:
    assert abs(row["score"] - float(expected[tuple(row["actions"])])) < 1e-12
assert max(expected, key=expected.get) == (1, 1)
example_text = (PACKAGE / "03-worked-example.md").read_text(encoding="utf-8")
for value in expected.values():
    assert f"{float(value):.6f}" in example_text

# Exact rational Kalman update, independent arithmetic.
prior_m, prior_p = F(13, 9), F(29, 36)
gain = prior_p / (prior_p + 1)
m2 = prior_m + gain * (F(5, 2) - prior_m)
p2 = (1 - gain) * prior_p
assert m2 == F(249, 130) and p2 == F(29, 65)
assert max(product((-1, 0, 1), repeat=2), key=lambda a: closed_score(m2, p2, a)) == (0, 0)
gain9 = F(5, 4) / (F(5, 4) + 9)
m9, p9 = 1 - gain9, (1 - gain9) * F(5, 4)
assert m9 == F(36, 41) and p9 == F(45, 41)
assert closed_score(m9, p9, (1, 0)) > closed_score(m9, p9, (1, 1))

# Instrument the protocol using tags; this checks data path, not neural behavior.
spec = importlib.util.spec_from_file_location("rssm_protocol_v1", Path(__file__).with_name("rssm_protocol_v1.py"))
protocol = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = protocol
spec.loader.exec_module(protocol)


class TaggedDistribution:
    def __init__(self, name):
        self.name = name

    def sample(self):
        return f"{self.name}_sample"


class TaggedBackend:
    def __init__(self):
        self.calls = []

    def recur(self, h, z, action):
        self.calls.append(("recur", h, z, action))
        return "next_h"

    def prior(self, h):
        self.calls.append(("prior", h))
        return TaggedDistribution("prior")

    def posterior(self, h, observation):
        self.calls.append(("posterior", h, observation))
        return TaggedDistribution("posterior")

    def reward_mean(self, h, z):
        self.calls.append(("reward", h, z))
        return 1.0


backend = TaggedBackend()
state, _, _ = protocol.observe_step(backend, protocol.StateSample("h0", "z0"), "a0", "o1")
assert state.z == "posterior_sample"
backend.calls.clear()
imagined = protocol.imagine(backend, state, ["a1", "a2"])
assert len(imagined) == 2
assert all(call[0] != "posterior" for call in backend.calls)
recurs = [call for call in backend.calls if call[0] == "recur"]
assert recurs[0][2] == "posterior_sample" and recurs[1][2] == "prior_sample"

broken = []
count = 0
for path in PACKAGE.glob("*.md"):
    text = path.read_text(encoding="utf-8")
    for href in re.findall(r"\]\(([^)]+)\)", text):
        if href.startswith(("http:", "https:", "#")):
            continue
        destination = href.split("#", 1)[0]
        if not (path.parent / destination).resolve().exists():
            broken.append((path.name, href))
        count += 1
assert not broken, broken

print(json.dumps({"exact_rational_numeric_checks": "passed",
                  "protocol_tag_information_flow": "passed",
                  "markdown_local_links_checked": count,
                  "broken_local_links": broken,
                  "scope": "teacher_material_QA_only_no_neural_training_or_learning_effect"}, ensure_ascii=False))
