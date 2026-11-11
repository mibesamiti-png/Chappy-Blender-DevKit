"""Development-only R9 tests; R9 fresh holdouts are never used in unit tests."""
import unittest
import numpy as np
from cbdk_geometry import quality
from cbdk_geometry.tapered_loft import tapered_radial_loft
from cbdk_geometry.flip_loft import conservative_flip_loft
from cycles.r8.fixtures import cases


class ConservativeR9Tests(unittest.TestCase):
    def test_seen_inputs_deterministic_and_face_only(self):
        for case in cases():
            a = case["a"].astype(np.float32).astype(float)
            b = case["b"].astype(np.float32).astype(float)
            previous = tapered_radial_loft(a,b)["mesh"]
            candidate = conservative_flip_loft(a,b)
            new = candidate["mesh"]
            self.assertFalse(candidate["approved"])
            self.assertTrue(np.array_equal(new.vertices,previous.vertices))
            self.assertEqual(len(new.faces),len(previous.faces))
            self.assertGreaterEqual(quality(new)["min_triangle_quality"]+1e-10,
                                    quality(previous)["min_triangle_quality"],case["name"])
            self.assertEqual(quality(new)["boundary_edges"],len(a)+len(b))
            self.assertEqual(quality(new)["nonmanifold_edges"],0)
            self.assertLessEqual(candidate["passes"],3)
            again = conservative_flip_loft(a,b)["mesh"]
            np.testing.assert_array_equal(again.faces,new.faces)

    def test_prior_reverse_slender_geometric_quality(self):
        c = next(x for x in cases() if x["name"]=="r8_slender_opposite")
        a = c["a"].astype(np.float32).astype(float)
        b = c["b"].astype(np.float32).astype(float)
        baseline = tapered_radial_loft(a,b)["mesh"]
        result = conservative_flip_loft(a,b)["mesh"]
        self.assertLess(quality(baseline)["min_triangle_quality"],.1)
        self.assertGreaterEqual(quality(result)["min_triangle_quality"],.1)

    def test_invalid_inputs(self):
        c=next(x for x in cases() if x["name"]=="dev_gentle_circle")
        a,b=c["a"],c["b"]
        with self.assertRaises(ValueError):conservative_flip_loft(a,b,cuts=2)
        with self.assertRaises(ValueError):conservative_flip_loft(a,b,seconds=0)
        with self.assertRaises(ValueError):conservative_flip_loft(a,a)
        with self.assertRaises(ValueError):conservative_flip_loft(np.full_like(a,np.nan),b)


if __name__ == "__main__":
    unittest.main()
