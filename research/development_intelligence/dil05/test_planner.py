import unittest
from planner import simulate

def event(t,team,head=None,ci='success',scope=True,base='d0'):
    return {'time':t,'team':team,'head':head or team+'1','ci':ci,'scope_ok':scope,'base_sha':base}

def case(events,heads=None):
    return {'dev_sha':'d0','events':events,'final_heads':heads or {t:t+'1' for t in 'BCD'}}

class PlannerTests(unittest.TestCase):
    def test_stagger_can_prestage(self):
        r=simulate(case([event(1,'B'),event(10,'C'),event(20,'D')]))
        self.assertEqual(r['post_ready_review_units'],1)
        self.assertEqual(r['overlap_window_seconds_sum'],29)
    def test_late_only_cannot_prestage(self):
        r=simulate(case([event(1,'B'),event(10,'C'),event(20,'D')]),'late_only')
        self.assertEqual(r['post_ready_review_units'],3)
    def test_no_auto_merge(self):
        r=simulate(case([event(1,'B'),event(2,'C'),event(3,'D')]))
        self.assertFalse(r['merge_authorized'])
        self.assertEqual(r['dispatched_ci'],0)
        self.assertTrue(r['required_combined_ci_still_due'])
    def test_stale_head_unreused(self):
        r=simulate(case([event(1,'B'),event(2,'C'),event(3,'D'),event(4,'B','B2',ci='pending')],dict(B='B2',C='C1',D='D1')))
        self.assertFalse(r['batch_all_green'])
        self.assertNotIn('B',r['current_valid'])
    def test_unpinned_stale_work(self):
        r=simulate(case([event(1,'B'),event(2,'C'),event(3,'D'),event(4,'B','B2')],dict(B='B2',C='C1',D='D1')),'eager_unpinned')
        self.assertEqual(r['unsafe_reuse_count'],1)
    def test_pinned_new_head_rechecked(self):
        r=simulate(case([event(1,'B'),event(2,'C'),event(3,'D'),event(4,'B','B2')],dict(B='B2',C='C1',D='D1')))
        self.assertEqual(r['unsafe_reuse_count'],0)  # obsolete snapshot is replaced, never reused
        self.assertEqual(r['post_ready_review_units'],1)
        self.assertEqual(r['review_units_total'],4)
    def test_missing_B(self):
        r=simulate(case([event(2,'C'),event(3,'D')]))
        self.assertEqual(r['current_valid'],['C','D'])
        self.assertIsNone(r['post_ready_review_units'])
    def test_failed_C(self):
        r=simulate(case([event(1,'B'),event(2,'C',ci='failed'),event(3,'D')]))
        self.assertEqual(r['current_valid'],['B','D'])
    def test_wrong_base(self):
        r=simulate(case([event(1,'B'),event(2,'C',base='wrong'),event(3,'D')]))
        self.assertEqual(r['current_valid'],['B','D'])
    def test_scope(self):
        r=simulate(case([event(1,'B'),event(2,'C',scope=False),event(3,'D')]))
        self.assertEqual(r['current_valid'],['B','D'])
    def test_future_final_head_not_observed(self):
        r=simulate(case([event(1,'B'),event(2,'C'),event(3,'D')],dict(B='B2',C='C1',D='D1')))
        self.assertEqual(r['current_valid'],['C','D'])
    def test_order_rejected(self):
        with self.assertRaises(ValueError):simulate(case([event(3,'B'),event(2,'C')]))
    def test_bool_time_rejected(self):
        with self.assertRaises(ValueError):simulate(case([event(True,'B')]))
    def test_bad_policy(self):
        with self.assertRaises(ValueError):simulate(case([]),'fast_bypass')
    def test_input_immutable(self):
        c=case([event(1,'B'),event(2,'C'),event(3,'D')]);before=repr(c);simulate(c);self.assertEqual(before,repr(c))

if __name__=='__main__':unittest.main()
