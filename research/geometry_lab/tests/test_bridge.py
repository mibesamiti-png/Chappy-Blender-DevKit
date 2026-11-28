import unittest
import numpy as np
from cbdk_geometry.bridge import bridge_loops
from cbdk_geometry import quality
from cycles.r4.fixtures import cases

class BridgeTests(unittest.TestCase):
    def test_development_boundaries_and_topology(self):
        for c in cases():
            a,b=c['a'],c['b'];before=a.copy()
            for method in ('index','phase','dp'):
                m=bridge_loops(a,b,method)['mesh'];q=quality(m)
                np.testing.assert_array_equal(m.vertices,np.vstack((a,b)))
                self.assertEqual(len(m.faces),len(a)+len(b))
                self.assertEqual(q['boundary_edges'],len(a)+len(b))
                self.assertEqual(q['nonmanifold_edges'],0)
                self.assertEqual(q['components'],1)
            np.testing.assert_array_equal(a,before)
    def test_limits(self):
        c=next(cases());a,b=c['a'],c['b']
        for bad in (a[:2],np.full_like(a,np.nan),np.vstack((a,a))):
            with self.assertRaises(ValueError):bridge_loops(bad,b)
        with self.assertRaises(TimeoutError):bridge_loops(a,b,seconds=1e-100)
    def test_proposal_not_approval(self):
        c=next(cases());r=bridge_loops(c['a'],c['b']);self.assertFalse(r['approved'])
