import copy
import unittest
from cbdk.joint_integration import proposals,review,score,verified_write


def measure(d=5):
    return dict(dimensions=[[d,d,3.5],[d,d,6.2]], protected_sha='a'*64,
                gl=[dict(status='measured',pairs=[])]*2,closed=True)


class IntegrationReviewTests(unittest.TestCase):
    def test_bounded_order_locks_and_preferences(self):
        self.assertEqual(proposals(5,4,'LOCKED'),[])
        self.assertEqual([v for _,v in proposals(5,4,'FREE')],[5.5,4.5,4.])
        self.assertEqual(proposals(5,4,'FREE'),proposals(5,4,'PREFERRED'))
        for x in (True,float('nan'),0):
            with self.assertRaises(ValueError): proposals(x,4,'FREE')

    def test_real_measurement_required_and_protected_veto(self):
        base=measure();best=score(base,4)
        for d,decision in [(5.5,'regression'),(4.5,'observed_improvement'),(4.,'target_reached'),(5.,'uncertain')]:
            self.assertEqual(review(base,measure(d),4,best)['decision'],decision)
        altered=measure(4);altered['protected_sha']='b'*64
        self.assertEqual(review(base,altered,4,best)['decision'],'protected_part_regression')
        altered=measure(4);altered['dimensions'][1][2]=7
        self.assertEqual(review(base,altered,4,best)['decision'],'axial_dimension_regression')
        for bad in [None, [], [('0','1')]]:
            altered=measure(4);altered['gl'][0]=dict(status='budget_exceeded',pairs=bad)
            with self.assertRaises(ValueError): review(base,altered,4,best)
        for key,value in [('closed',1),('dimensions',[[True,4,3],[4,4,6]]),('protected_sha','x')]:
            altered=measure(4);altered[key]=value
            with self.assertRaises(ValueError): review(base,altered,4,best)

    def test_success_rounding_rollback_and_rollback_failure(self):
        box=[5.]
        verified_write(lambda:box[0],lambda v:box.__setitem__(0,v),5.,4.,lambda:None)
        self.assertEqual(box,[4.])
        def rounded(v): box[0]=5. if v==5. else 4.1
        with self.assertRaisesRegex(RuntimeError,'rna_readback'):
            verified_write(lambda:box[0],rounded,5.,4.,lambda:None)
        self.assertEqual(box,[5.])
        def broken(v): box[0]=0.
        with self.assertRaisesRegex(RuntimeError,'rollback_failed'):
            verified_write(lambda:box[0],broken,5.,4.,lambda:None)

    def test_keyboard_interrupt_restores_and_cannot_be_success(self):
        box=[5.]
        def stop(): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            verified_write(lambda:box[0],lambda v:box.__setitem__(0,v),5.,4.,stop)
        self.assertEqual(box,[5.])

    def test_invalid_history_score_does_not_authorize_acceptance(self):
        for invalid in (True,False,float('nan'),float('inf'),-1):
            with self.assertRaises(ValueError): review(measure(),measure(4),4,invalid)
        base,candidate=measure(),measure(4)
        before=copy.deepcopy((base,candidate))
        result=review(base,candidate,4,1.)
        self.assertEqual((base,candidate),before)
        self.assertFalse(result['approved'])
        self.assertFalse(result['auto_apply'])
