"""Execute fictional source code and finite content anchors; no learner data.

Mathematical proof and instruction behavior are reviewed separately. These
finite checks do not establish general theorems or independent learning.
"""
from fractions import Fraction as F
from pathlib import Path
import json
import platform

OUT = Path(__file__).resolve().parent

# P3's original code is preserved exactly in behavior; not repaired in place.
def original_mean(xs):
    return sum(xs) / len(xs)

# An AI repair fixture, not a learner revision or evidence of autonomous coding.
def ai_repair_mean(xs):
    if not xs:
        raise ValueError('empty input')
    return sum(xs) / len(xs)

def outcome(fn, xs):
    try:
        return {'value': fn(xs)}
    except Exception as exc:
        return {'exception': type(exc).__name__}

mean_results = []
for label, fn in [('P3_original', original_mean), ('AI_repair_fixture', ai_repair_mean)]:
    for xs, expected in [([2, 4], {'value': 3.0}), ([5], {'value': 5.0}),
                         ([], {'exception': 'ValueError'})]:
        observed = outcome(fn, xs)
        mean_results.append({'code': label, 'input': xs, 'expected': expected,
                             'observed': observed, 'meets_spec': observed == expected})

def trajectory(q, steps=8, target=F(1), initial=F(0)):
    x = initial
    rows = [(0, x, target - x)]
    for t in range(steps):
        x += q * (target - x)
        rows.append((t + 1, x, target - x))
    return rows

trajectories = []
for q in [F(1, 5), F(6, 5), F(2), F(11, 5)]:
    rows = trajectory(q)
    assert all(error == (1-q)**t for t, _, error in rows)
    trajectories.append({'q': str(q), 'rows': [
        {'t': t, 'state': str(x), 'error': str(e)} for t, x, e in rows]})
assert all(e == 0 for _, _, e in trajectory(F(11, 5), initial=F(1)))

def mv(matrix, vector):
    return [sum(a*b for a, b in zip(row, vector)) for row in matrix]

A = [[1, 1, 0], [0, 1, 1]]
n = [1, -1, 1]
valid_Q = [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
invalid_Q = [[1, 1, 0], [1, 1, 0], [0, 0, 0]]
assert mv(A, n) == [0, 0]
assert mv(valid_Q, n) == [1, 0, 0]
assert mv(invalid_Q, n) == [0, 0, 0]
assert original_mean([20*90, 60*70]) == 3000  # means of totals is not the group mean
merged_mean = F(20*90 + 60*70, 20+60)
assert merged_mean == 75
assert F(10*80 + 30*60, 10+30) == 65
assert F(80+60, 2) == 70

result = {'status': 'pass', 'fictional_only': True,
          'executor': 'phase6/content_probe.py', 'python_version': platform.python_version(),
          'execution_date': '2026-10-05',
          'mean_results': mean_results,
          'P3_original_spec_failure_expected': mean_results[2]['observed'] == {'exception': 'ZeroDivisionError'},
          'AI_repair_is_not_learner_revision': True,
          'matrix_anchors': {'A_n': mv(A, n), 'valid_Q_n': mv(valid_Q, n),
                             'invalid_Q_n': mv(invalid_Q, n)},
          'merged_mean': str(merged_mean), 'trajectories': trajectories,
          'trajectory_closed_form_points_checked': sum(len(t['rows']) for t in trajectories),
          'limits': ['Finite exact anchors do not prove general theorems.',
                     'Expected specification violation is a teaching input, not a failed probe.',
                     'No real learner answers, code or private file contents are used.',
                     'No inference about autonomous coding, physical experiments or retention.']}
assert all(row['meets_spec'] for row in mean_results[3:])
assert [row['meets_spec'] for row in mean_results[:3]] == [True, True, False]
(OUT/'content-probe-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Finite content probe passed: original empty-input violation reproduced; 36 exact trajectory points checked.')
