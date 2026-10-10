"""Maintenance checks for two candidate teaching packets; no learner events.

Recomputes selected numerical claims directly from the printed input contracts,
without importing the candidate verification programs or overwriting their reports.
"""
from pathlib import Path
from itertools import product
import copy
import json

COURSE = Path(__file__).resolve().parents[2]
PACKS = COURSE / 'artifacts/preparation-tests'


def flatten(value):
    return [v for part in value for v in flatten(part)] if isinstance(value, list) else [value]


def main():
    checks = []

    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})

    x = json.loads((PACKS / '2026-10-08-video-interface-single-model/data.json').read_text(encoding='utf-8-sig'))['camera']
    tops = [
        [[11,12,13],[21,22,23],[31,32,33],[41,42,43]],
        [[31,32,113],[11,12,123],[41,42,133],[21,22,143]],
    ]
    ux = [[[[[tops[b][t][c]+5*h+3*w for c in range(3)] for w in range(2)]
             for h in range(2)] for t in range(4)] for b in range(2)]
    for label, camera in [('xhigh',x),('ultra',ux)]:
        video = [[[[[camera[b][t][h][w][c] for w in range(2)] for h in range(2)]
                    for t in range(4)] for c in range(3)] for b in range(2)]
        frames = [[[[camera[b][t][h][w][c] for w in range(2)] for h in range(2)]
                    for c in range(3)] for b in range(2) for t in range(4)]
        coords = list(product(range(2),range(4),range(2),range(2),range(3)))
        check(label+'_96_coordinates_both_routes', len(flatten(camera))==96 and all(
            video[b][c][t][h][w] == frames[4*b+t][c][h][w] == camera[b][t][h][w][c]
            for b,t,h,w,c in coords))
        encoded = [[camera[b][t][0][0][0],camera[b][t][0][0][1]] for b in range(2) for t in range(4)]
        expected = ([[11,12],[21,22],[31,32],[41,42],[51,52],[61,62],[11,12],[81,82]]
                    if label=='xhigh' else [[11,12],[21,22],[31,32],[41,42],[31,32],[11,12],[41,42],[21,22]])
        check(label+'_printed_encoded_rows', encoded==expected)
        order = [6,0,4,2,7,1,5,3] if label=='xhigh' else [5,2,7,0,6,1,4,3]
        rows = [encoded[n] for n in order]
        restored = [None]*8
        for row,n in zip(rows,order):
            restored[n] = row
        check(label+'_tags_restore_all_eight_frames', restored==encoded)
        changed = copy.deepcopy(camera)
        changed[0][1][0][0][2] = 99
        changed_encoded = [[changed[b][t][0][0][0],changed[b][t][0][0][1]] for b in range(2) for t in range(4)]
        check(label+'_same_source_blue_change_preserves_features', changed_encoded==encoded and changed!=camera)
        if label=='xhigh':
            logical = flatten(video)
            check('xhigh_wrong_Y_reshape_coordinate',logical[4]==21 and frames[0][1][0][0]==12)
            check('xhigh_G_order_sensitive',encoded[1][0]-encoded[0][0]==10 and encoded[0][0]-encoded[1][0]==-10)
            check('xhigh_source_collision',encoded[0]==encoded[6] and camera[0][0]!=camera[1][2])
        else:
            correct = [encoded[3][0]-encoded[0][0],encoded[7][0]-encoded[4][0]]
            wrong = [rows[3][0]-rows[0][0],rows[7][0]-rows[4][0]]
            check('ultra_S_correct_and_wrong_outputs',correct==[30,-10] and wrong==[0,0])
            check('ultra_K_same_features_opposite_answers',
                  camera[0][1][0][0][2]-camera[0][0][0][0][2]<=50 and
                  changed[0][1][0][0][2]-changed[0][0][0][0][2]>50)
            check('ultra_printed_row_lookup',[order.index(n) for n in range(4)]==[3,5,1,7] and
                  [order.index(n) for n in range(4,8)]==[6,0,4,2])
    result = {'client_date':'2026-10-08','status':'pass' if all(c['passed'] for c in checks) else 'fail',
              'passed':sum(c['passed'] for c in checks),'total':len(checks),'checks':checks,
              'teacher_review_only':True,'independent_agent':False,'pytorch_executed':False,
              'learner_execution':False,'learning_effect_verified':False,
              'limits':['Selected finite claims under printed contracts','Separate maintenance calculation; original candidate checks not rerun or overwritten']}
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result['status']=='pass' else 1


if __name__=='__main__':
    raise SystemExit(main())
