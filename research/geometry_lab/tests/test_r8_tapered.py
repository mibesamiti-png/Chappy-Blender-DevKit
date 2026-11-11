"""R8 deterministic checks on SEEN development only; holdout stays hidden."""
import unittest
import numpy as np
from cbdk_geometry import quality
from cbdk_geometry.tapered_loft import tapered_radial_loft
from cycles.r7.fixtures import cases


class TaperedLoftTests(unittest.TestCase):
    def test_r7_seen_development_all_valid(self):
        for case in cases():
            a = case["a"].astype(np.float32).astype(float)
            b = case["b"].astype(np.float32).astype(float)
            orig_a, orig_b = a.copy(), b.copy()
            candidate = tapered_radial_loft(a,b)
            self.assertFalse(candidate["approved"])
            m = candidate["mesh"]
            q = quality(m)
            self.assertEqual(q["boundary_edges"], len(a)+len(b), case["name"])
            self.assertEqual(q["nonmanifold_edges"], 0, case["name"])
            self.assertEqual(q["components"], 1, case["name"])
            self.assertEqual(len(candidate["internal_counts"]),3)
            self.assertTrue(set(map(tuple,np.vstack((a,b)))).issubset(set(map(tuple,m.vertices))), case["name"])
            np.testing.assert_array_equal(a, orig_a)
            np.testing.assert_array_equal(b, orig_b)
            np.testing.assert_array_equal(tapered_radial_loft(a,b)["mesh"].faces,m.faces)

    def test_r7_slender_quality_rescued_on_seen(self):
        case = next(c for c in cases() if c["name"]=="r7_slender_offset")
        a,b=case["a"].astype(np.float32).astype(float),case["b"].astype(np.float32).astype(float)
        m=tapered_radial_loft(a,b)["mesh"]
        self.assertGreaterEqual(quality(m)["min_triangle_quality"], .1)

    def test_invalid_input_rejected(self):
        c=next(c for c in cases() if c["name"]=="dev_gentle_circle")
        a,b=c["a"],c["b"]
        for bad in (a[:2],np.full_like(a,float("nan")),np.vstack((a,a))):
            with self.assertRaises(ValueError):
                tapered_radial_loft(bad,b)
        for x,y,kw in ((a,a,{}),(a,b,{"cuts":2}),(a,b,{"seconds":0})):
            with self.assertRaises(ValueError):
                tapered_radial_loft(x,y,**kw)


if __name__=="__main__":
    unittest.main()
