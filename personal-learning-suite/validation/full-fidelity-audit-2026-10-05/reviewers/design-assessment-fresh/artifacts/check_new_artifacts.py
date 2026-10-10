from itertools import combinations_with_replacement
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent

def original(a, target):
    lo, hi = 0, len(a) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo

def teacher_reference(a, target):
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo

def expected(a, target):
    return next((i for i, value in enumerate(a) if value >= target), len(a))

checks = []
for n in range(6):
    for values in combinations_with_replacement([-1, 0, 1], n):
        for target in range(-2, 3):
            a = list(values)
            before = a[:]
            want = expected(a, target)
            got_original = original(a, target)
            got_reference = teacher_reference(a, target)
            checks.append(dict(a=a, target=target, expected=want,
                               original=got_original, teacher_reference=got_reference,
                               original_pass=got_original == want,
                               reference_pass=got_reference == want,
                               preserved_input=a == before))
result = dict(synthetic=True, scope="sorted integer arrays, length 0..5, values -1/0/1, targets -2..2; finite implementation checks only",
              count=len(checks), original_failures=sum(not c['original_pass'] for c in checks),
              reference_failures=sum(not c['reference_pass'] for c in checks),
              changed_inputs=sum(not c['preserved_input'] for c in checks),
              first_failures=[c for c in checks if not c['original_pass']][:10],
              named_cases=[dict(a=a, target=t, expected=expected(a,t), original=original(a,t), reference=teacher_reference(a,t))
                           for a,t in [([],4),([1],2),([1,3],4),([1,2,2],2),([2,4,7],8)]],
              learner_revision="not_executed; teacher reference is not learner code")
(ROOT / 'R2-execution.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k:result[k] for k in ['count','original_failures','reference_failures','changed_inputs']}, ensure_ascii=False))

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    xs = [-1, 0, 1, 2, 3, 4, 5]
    fig, ax = plt.subplots(figsize=(7,5), dpi=140)
    ax.plot(xs, [3]*len(xs), label='y = 3 (m=0, c=3)', linewidth=2)
    ax.plot(xs, [x+1 for x in xs], label='y = x + 1 (m=1, c=1)', linewidth=2)
    ax.scatter([2], [3], color='black', s=60, zorder=5)
    ax.annotate('(2, 3)', (2,3), xytext=(2.2,3.4))
    ax.set_xlim(-1,5); ax.set_ylim(-1,7)
    ax.set_xticks(range(-1,6)); ax.set_yticks(range(-1,8))
    ax.axhline(0, color='black', linewidth=.6); ax.axvline(0,color='black',linewidth=.6)
    ax.set_xlabel('x'); ax.set_ylabel('y'); ax.grid(alpha=.25)
    ax.set_title('One point is compatible with different affine functions')
    ax.legend(loc='upper left'); fig.tight_layout()
    fig.savefig(ROOT / 'R3-affine-comparison.png')
    plt.close(fig)
    print('R3 graph created with exact formula samples; graphical review remains separate.')
except ImportError:
    print('matplotlib unavailable; no graph claimed.')
