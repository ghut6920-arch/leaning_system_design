"""Check public fictional example anchors; never read personal learning records.

Finite computations check these fixtures only, not general proofs or pedagogy.
Run --render once to produce the two static teaching assets.
"""
from pathlib import Path
import argparse
import json
from fractions import Fraction

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ASSETS = ROOT / 'personal-learning-suite/src/skills/learning-materials/assets'
checks = []


def check(name, condition):
    checks.append({'name': name, 'passed': bool(condition)})


def render():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ASSETS.mkdir(parents=True, exist_ok=True)
    for with_answer in (False, True):
        fig, ax = plt.subplots(figsize=(6, 9.5), dpi=150)
        ax.set_xlim(-1, 5)
        ax.set_ylim(-2, 9)
        ax.set_xticks(np.arange(-1, 6))
        ax.set_yticks(np.arange(-2, 10))
        ax.set_aspect('equal', adjustable='box')
        ax.grid(color='#dce3ea', linewidth=0.65)
        ax.axhline(0, color='#324558', linewidth=1)
        ax.axvline(0, color='#324558', linewidth=1)
        ax.set_xlabel('x')
        ax.set_ylabel('f(x)' if with_answer else 'y')
        if with_answer:
            x = np.linspace(-1, 5, 601)
            ax.plot(x, x*x - 4*x + 3, color='#2069ba', linewidth=2.1)
            ax.axvline(2, color='#a2601a', linestyle='--', linewidth=1)
            for (px, py), delta in [((2, -1), (9, -15)), ((1, 0), (-45, 10)),
                                    ((3, 0), (10, 10)), ((0, 3), (10, 5))]:
                ax.scatter([px], [py], color='#a2601a', zorder=5, s=28)
                ax.annotate(f'({px}, {py})', (px, py), xytext=delta,
                            textcoords='offset points', fontsize=10)
            ax.set_title('Feedback reference: f(x) = x^2 - 4x + 3', pad=16)
            name = 'quadratic-reference.png'
        else:
            ax.set_title('Coordinate grid', pad=16)
            name = 'quadratic-grid.png'
        fig.tight_layout()
        fig.savefig(ASSETS / name, facecolor='white')
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args()
    if args.render:
        render()
    for x, y in [(-1, 8), (0, 3), (1, 0), (2, -1), (3, 0), (4, 3), (5, 8)]:
        check(f'quadratic anchor x={x}', x*x - 4*x + 3 == y == (x-2)**2-1)
    check('reverse reconstruction coefficient', Fraction(10-2, (1+1)**2) == 2)
    check('reverse reconstruction vertex and point', 2*(-1+1)**2+2 == 2 and 2*(1+1)**2+2 == 10)
    check('zero must remain in y^2=3y', all(y*y == 3*y for y in [0, 3]))
    check('fraction domain and valid solution', (1*1-1)/1 == 0)
    check('provided mean fixtures', all(Fraction(sum(xs), len(xs)) == expected
          for xs, expected in [([2, 4], 3), ([-2, 2], 0), ([5], 5)]))
    check('empty mean has no valid denominator', len([]) == 0)
    A = np.array([[1., 1.], [2., 2.]])
    b = np.array([1., 2.])
    null = np.array([1., -1.])
    Q_difference = np.array([[1., -1.], [-1., 1.]])
    Q_sum = np.array([[1., 1.], [1., 1.]])
    for lam in [.1, 1., 3.]:
        for label, Q, expected in [('identity', np.eye(2), np.full(2, 5/(10+lam))),
                                    ('difference', Q_difference, np.full(2, .5))]:
            H = A.T@A + lam*Q
            check(f'{label} finite solution lambda={lam}', np.allclose(np.linalg.solve(H, A.T@b), expected))
            check(f'{label} finite positive curvature lambda={lam}', np.linalg.eigvalsh(H).min() > 0)
        H = A.T@A + lam*Q_sum
        x0 = np.full(2, (5/(5+lam))/2)
        check(f'sum penalty free direction lambda={lam}', np.allclose(H@null, 0))
        check(f'sum penalty optimum finite check lambda={lam}', np.allclose(H@x0, A.T@b))
    A3 = np.array([[1., 1., 0.], [0., 1., 1.]])
    n = np.array([1., -1., 1.])
    u = np.array([1., 1., 0.])
    check('three-dimensional null direction', np.allclose(A3@n, 0) and np.linalg.matrix_rank(A3) == 2)
    for label, Q in [('projection', np.outer(n, n)/3), ('alternative diagonal', np.diag([1., 0., 0.]))]:
        check(f'{label} symmetric PSD rank-one fixture', np.allclose(Q, Q.T) and
              np.linalg.eigvalsh(Q).min() >= -1e-12 and np.linalg.matrix_rank(Q) == 1)
        check(f'{label} covers kernel fixture', n@Q@n > 0 and np.linalg.eigvalsh(A3.T@A3+Q).min() > 0)
    wrong = np.outer(u, u)
    check('wrong rank-one construction misses direction', np.allclose(wrong@n, 0) and np.linalg.matrix_rank(wrong) == 1)
    for name, parts, total in [('shared week', [5, 10, 25, 15, 20, 10, 5, 30], 120),
                                ('relationship session', [4, 2, 10, 5, 2, 2], 25),
                                ('whole product session', [2, 6, 8, 4, 2, 3], 25),
                                ('remaining five minutes', [1, 2, 2], 5),
                                ('candidate backlog', [55, 35, 45, 90, 40], 265),
                                ('chosen backlog scope', [55, 35, 5, 25], 120)]:
        check(name + ' arithmetic', sum(parts) == total)
    check('defined toy model forward value', 2*1 + .5*4 == 4)
    check('defined toy identification a', Fraction(2, 1) == 2)
    check('defined toy identification b', Fraction(3-2*1, 2) == Fraction(1, 2))
    check('zero actions do not determine b', all(2*1 + coef*0 == 2 for coef in [-3, .5, 8]))
    check('specified seven-day interval not met at day seven', 7-5 < 7 and 12-5 == 7)
    for name in ['quadratic-grid.png', 'quadratic-reference.png']:
        check(f'actual asset exists: {name}', (ASSETS/name).is_file())
    result = {'scope': 'public fictional content anchors and asset existence',
              'checks': checks, 'passed': sum(c['passed'] for c in checks), 'total': len(checks),
              'finite_computations_are_not_general_proofs': True,
              'teaching_effectiveness_tested': False, 'personal_records_read': False}
    (OUT/'reference-checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'checks'}, ensure_ascii=False))
    raise SystemExit(0 if all(c['passed'] for c in checks) else 1)


if __name__ == '__main__':
    main()
