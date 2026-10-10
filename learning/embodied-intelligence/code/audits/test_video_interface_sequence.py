"""Teacher/auditor checks, not learner experiments or a world-model evaluation."""
import importlib.util
import json
from pathlib import Path
import random
import sys
import unittest

COURSE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(COURSE / "code/M0"))
from video_interface_sequence_reference import Spec, make_camera, to_video, to_frames, toy_encode, restore_sequence, demo


class InterfaceChecks(unittest.TestCase):
    def test_all_pixel_identities_in_both_consumers(self):
        for b_size in range(1, 4):
            for t_size in range(1, 6):
                s = Spec(batch=b_size, time=t_size)
                x = make_camera(s); y = to_video(x, s); frames, ids = to_frames(x, s)
                for b in range(s.batch):
                    for t in range(s.time):
                        for h in range(s.height):
                            for w in range(s.width):
                                for c in range(s.channels):
                                    self.assertEqual(y[b][c][t][h][w], x[b][t][h][w][c])
                                    self.assertEqual(frames[b*s.time+t][c][h][w], x[b][t][h][w][c])
                self.assertEqual(ids, [(b,t) for b in range(s.batch) for t in range(s.time)])

    def test_features_preserve_frame_rows_and_known_order_restores(self):
        s=Spec(); frames,ids=to_frames(make_camera(s),s); f=toy_encode(frames)
        seq=restore_sequence(f,2,4,order_confirmed=True)
        self.assertEqual(seq[1][2],[72,73])
        self.assertEqual(seq,restore_sequence(f,2,4,frame_ids=ids))

    def test_shuffled_rows_with_ids_restore_same_sequences(self):
        s=Spec();frames,ids=to_frames(make_camera(s),s);f=toy_encode(frames)
        order=[6,0,4,2,5,3,7,1]
        self.assertEqual(restore_sequence([f[i] for i in order],2,4,frame_ids=[ids[i] for i in order]),
                         restore_sequence(f,2,4,order_confirmed=True))
        self.assertNotEqual(restore_sequence([f[i] for i in order],2,4,order_confirmed=True),
                            restore_sequence(f,2,4,order_confirmed=True))

    def test_varied_shapes_and_shuffles_preserve_identities(self):
        rng=random.Random(0)
        for b in range(1,4):
            for t in range(1,6):
                s=Spec(batch=b,time=t);frames,ids=to_frames(make_camera(s),s);f=toy_encode(frames)
                order=list(range(b*t));rng.shuffle(order)
                self.assertEqual(restore_sequence([f[i] for i in order],b,t,frame_ids=[ids[i] for i in order]),
                                 restore_sequence(f,b,t,order_confirmed=True))

    def test_unknown_row_order_is_not_guessed(self):
        with self.assertRaises(ValueError):restore_sequence([[0,1]]*8,2,4)

    def test_duplicate_missing_and_out_of_range_ids_rejected(self):
        ids=[(b,t) for b in range(2) for t in range(4)]
        for bad in [ids[:-1],ids[:-1]+[ids[0]],ids[:-1]+[(2,0)],ids[:-1]+[(True,0)]]:
            with self.assertRaises(ValueError):restore_sequence([[0,1]]*8,2,4,frame_ids=bad)

    def test_lengths_and_vector_dimension_checked(self):
        for f in [[],[[]]*8,[[1,2]]*7,[[1]]+[[1,2]]*7]:
            with self.assertRaises(ValueError):restore_sequence(f,2,4,order_confirmed=True)

    def test_projection_cannot_restore_every_original_pixel(self):
        s=Spec();x=make_camera(s);frames,_=to_frames(x,s);f=toy_encode(frames)
        x[0][0][0][0][2]+=7  # change a legal unselected blue value
        changed,_=to_frames(x,s)
        self.assertEqual(f,toy_encode(changed))

    def test_N_alone_does_not_determine_B_T(self):
        f=[[0,1]]*8
        a=restore_sequence(f,2,4,order_confirmed=True)
        b=restore_sequence(f,4,2,order_confirmed=True)
        self.assertEqual((len(a),len(a[0])),(2,4));self.assertEqual((len(b),len(b[0])),(4,2))

    @unittest.skipUnless(importlib.util.find_spec("torch") is not None, "PyTorch is absent; no installation requested")
    def test_optional_torch_matches_stated_coordinate_map(self):
        import torch
        from video_interface_sequence_torch import bridge
        x=torch.arange(96).reshape(2,4,2,2,3)
        video,frames,features,seq=bridge(x)
        for b in range(2):
            for t in range(4):
                self.assertTrue(torch.equal(frames[b*4+t],x[b,t].permute(2,0,1)))
                self.assertTrue(torch.equal(video[b,:,t],frames[b*4+t]))
        self.assertEqual(list(seq.shape),[2,4,2]);self.assertEqual(seq[1,2].tolist(),[72,73])


if __name__ == "__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(InterfaceChecks)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    out=COURSE / "experiments/M0/video-interface-sequence-teacher-check-20261007.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    report={"status":"pass" if result.wasSuccessful() else "fail","teacher_checks_only":True,
            "tests_run":result.testsRun,"passed":result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
            "failures":len(result.failures),"errors":len(result.errors),"skipped":[reason for _,reason in result.skipped],
            "python_version":sys.version,"pytorch_executed":importlib.util.find_spec("torch") is not None,
            "demo":demo(),"learner_run_observed":False,"learning_effect_verified":False}
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
