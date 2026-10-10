"""Check only self-contained fictional teaching anchors used in phase3 walkthrough."""
from pathlib import Path
import json

output = Path(__file__).resolve().parent
states = []
for p in range(3):
    for a in (-1, 0, 1):
        value = min(2, max(0, p+a))
        expected = {0: {-1: 0, 0: 0, 1: 1}, 1: {-1: 0, 0: 1, 1: 2},
                    2: {-1: 1, 0: 2, 1: 2}}[p][a]
        assert value == expected
        states.append({'p': p, 'a': a, 'next': value})

sequences = []
for actions, expected in [((-1, 1), 1), ((1, -1), 0)]:
    p = 0
    trajectory = [p]
    for a in actions:
        p = min(2, max(0, p+a))
        trajectory.append(p)
    assert p == expected
    sequences.append({'actions': actions, 'trajectory': trajectory})

truth = [1, 1, 0]
prediction = [1, 0, 0]
tp = sum(t == 1 and p == 1 for t, p in zip(truth, prediction))
fp = sum(t == 0 and p == 1 for t, p in zip(truth, prediction))
wrong = tp / sum(truth)
correct = tp / (tp+fp)
assert wrong == 0.5 and correct == 1.0
assert all(x*x == x for x in (0, 1))

result = {'status': 'pass', 'fictional_only': True, 'grid_states': states,
          'sequence_examples': sequences,
          'existing_code_counterexample': {'tp': tp, 'fp': fp, 'wrong': wrong, 'correct': correct},
          'quadratic_roots_substitution': [0, 1],
          'limits': ['Finite anchors only; not general proof or learning efficacy.',
                     'No real learning record was read or written.',
                     'General parity and full quadratic solution arguments are reviewed in prose.']}
(output/'reference-probe-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': result['status'], 'grid_states': len(states),
                  'sequence_examples': len(sequences), 'wrong_precision': wrong,
                  'correct_precision': correct}, ensure_ascii=False))
