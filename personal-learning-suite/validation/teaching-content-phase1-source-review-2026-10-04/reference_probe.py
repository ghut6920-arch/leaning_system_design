"""Check new synthetic mathematical references; not a teaching/learning trial.

Finite examples supplement the written general proof. They do not prove the
general theorem or independently validate instructional decisions.
"""
from fractions import Fraction as F
import json
from pathlib import Path


def mul(matrix, vector):
    return tuple(sum(a*b for a, b in zip(row, vector)) for row in matrix)


def dot(left, right):
    return sum(a*b for a, b in zip(left, right))


def objective(matrix, target, penalty, lam, point):
    residual = tuple(a-b for a, b in zip(mul(matrix, point), target))
    return dot(residual, residual) + lam*dot(point, mul(penalty, point))


def hessian_half(matrix, penalty, lam):
    return tuple(tuple(
        sum(row[i]*row[j] for row in matrix) + lam*penalty[i][j]
        for j in range(2)) for i in range(2))


def determinant(matrix):
    return matrix[0][0]*matrix[1][1] - matrix[0][1]*matrix[1][0]


def run():
    pairs = ((F(1), F(3, 5)), (F(2), F(3, 10)))
    tracks = []
    for a, k in pairs:
        assert a*k == F(3, 5)
        state, r = F(0), F(10)
        track = [state]
        for _ in range(6):
            state += a*k*(r-state)
            track.append(state)
        tracks.append(track)
        command = F(2)
        delta = a*command
        recovered_a = delta/command
        recovered_k = F(3, 5)/recovered_a
        assert (recovered_a, recovered_k) == (a, k)
    assert tracks[0] == tracks[1]

    matrix = ((1, 1), (2, 2))
    target = (1, 2)
    difference_penalty = ((1, -1), (-1, 1))
    sum_penalty = ((1, 1), (1, 1))
    assert mul(matrix, (1, -1)) == (0, 0)
    assert mul(sum_penalty, (1, -1)) == (0, 0)
    assert mul(difference_penalty, (1, -1)) == (2, -2)
    cases = []
    for lam in (F(1, 2), F(1), F(3)):
        good_h = hessian_half(matrix, difference_penalty, lam)
        bad_h = hessian_half(matrix, sum_penalty, lam)
        assert determinant(good_h) == 20*lam > 0
        assert determinant(bad_h) == 0
        point = (F(1, 2), F(1, 2))
        assert objective(matrix, target, difference_penalty, lam, point) == 0
        s = 5/(5+lam)
        flat_values = []
        for d in (F(-3), F(0), F(2)):
            point = ((s+d)/2, (s-d)/2)
            value = objective(matrix, target, sum_penalty, lam, point)
            assert value == 5*lam/(5+lam)
            flat_values.append(str(value))
        assert len(set(flat_values)) == 1

        return_matrix, return_target = ((1, 0),), (2,)
        assert objective(return_matrix, return_target,
                         difference_penalty, lam, (2, 2)) == 0
        assert determinant(hessian_half(return_matrix, difference_penalty, lam)) == lam
        diagonal_penalty = ((1, 0), (0, 0))
        for x2 in (F(-3), F(0), F(2)):
            value = objective(return_matrix, return_target, diagonal_penalty,
                              lam, (2/(1+lam), x2))
            assert value == 4*lam/(1+lam)
        assert determinant(hessian_half(return_matrix, diagonal_penalty, lam)) == 0
        cases.append({'lambda': str(lam), 'good_determinant': str(determinant(good_h)),
                      'bad_determinant': str(determinant(bad_h)),
                      'flat_minimum': flat_values[0]})
    return {'completed_on': '2026-10-05', 'synthetic_only': True,
            'check_kind': 'reference_arithmetic_and_finite_model_examples',
            'closed_loop_parameter_pairs': [[str(v) for v in p] for p in pairs],
            'matching_track_points': len(tracks[0]),
            'ideal_known_command_calibration': 'verified_in_given_model',
            'quadratic_cases': cases, 'result': 'pass',
            'general_proof': 'written_argument_in_teaching_reference_not_proved_by_this_probe',
            'independent_teacher_validation': 'not_executed',
            'real_learning_outcomes': 'not_executed'}


if __name__ == '__main__':
    result = run()
    Path(__file__).with_name('reference-probe-result.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
