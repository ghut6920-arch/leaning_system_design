"""Verify finite anchors used in the fictional content walkthrough, not skill behavior."""
from fractions import Fraction
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent

expected_transitions = {
    (0, -1): 0, (0, 0): 0, (0, 1): 1,
    (1, -1): 0, (1, 0): 1, (1, 1): 2,
    (2, -1): 1, (2, 0): 2, (2, 1): 2,
}
for (p, a), expected in expected_transitions.items():
    assert min(2, max(0, p+a)) == expected

weighted = Fraction(1*2 + 3*4, 1+3)
unweighted = Fraction(2+4, 2)
assert weighted == Fraction(7, 2) and unweighted == 3

def precision(truth, predicted):
    predicted_positive = sum(p == 1 for p in predicted)
    if not predicted_positive:
        return None
    true_positive = sum(t == 1 and p == 1 for t, p in zip(truth, predicted))
    return Fraction(true_positive, predicted_positive)

precision_cases = [
    ([1, 1, 0], [1, 0, 0], Fraction(1)),
    ([1, 0], [1, 1], Fraction(1, 2)),
    ([1, 0], [0, 0], None),
    ([], [], None),
]
for truth, predicted, expected in precision_cases:
    assert precision(truth, predicted) == expected
assert Fraction(1, sum(t == 1 for t in [1, 1, 0])) == Fraction(1, 2)

result = {
    'status': 'pass', 'finite_transition_pairs_checked': len(expected_transitions),
    'weighted_average_values': {'correct': str(weighted), 'direct_average': str(unweighted)},
    'precision_cases_checked': len(precision_cases),
    'precision_bad_denominator_counterexample_checked': True,
    'real_user_code_executed': False,
    'limits': ['Finite reference anchors only.', 'Not skill execution, independent review, general proof, experiment validation or learning efficacy.'],
}
(OUT/'reference-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
