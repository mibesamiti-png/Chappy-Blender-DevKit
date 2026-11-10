"""R10 development-only tests; never use new R10 holdout in unit tests."""
import unittest
import numpy as np
from cbdk_geometry import quality
from cbdk_geometry.tapered_loft import tapered_radial_loft
from cbdk_geometry.flip_loft import conservative_flip_loft
from cbdk_geometry.quality_router import conditional_flip_loft, _fast_min_triangle_quality
from cycles.r9.fixtures import cases


class R10QualityDispatch(unittest.TestCase):
    def test_all_seen_cases_match_frozen_baselines_by_route(self):
        fast = repaired = 0
        for case in cases():
            a = case["a"].astype(np.float32).astype(float)
            b = case["b"].astype(np.float32).astype(float)
            old = tapered_radial_loft(a, b)["mesh"]
            routed = conditional_flip_loft(a, b)
            new = routed["mesh"]
            self.assertEqual(routed["approved"], False)
            self.assertTrue(np.array_equal(new.vertices, old.vertices))
            self.assertEqual(len(new.faces), len(old.faces))
            self.assertAlmostEqual(_fast_min_triangle_quality(old),
                                   quality(old)["min_triangle_quality"], places=12)
            if routed["path"] == "fast":
                fast += 1
                self.assertGreaterEqual(quality(old)["min_triangle_quality"], .1)
                np.testing.assert_array_equal(new.faces, old.faces)
            else:
                repaired += 1
                self.assertLess(quality(old)["min_triangle_quality"], .1)
                reference = conservative_flip_loft(a, b)["mesh"]
                np.testing.assert_array_equal(new.faces, reference.faces)
            self.assertLessEqual(routed["passes"], 3)
            np.testing.assert_array_equal(conditional_flip_loft(a, b)["mesh"].faces,
                                          new.faces)
        self.assertGreater(fast, 0)
        self.assertGreater(repaired, 0)

    def test_known_prior_failure_repaired(self):
        case = next(x for x in cases() if x["name"] == "r8_slender_opposite")
        a, b = case["a"].astype(np.float32).astype(float), case["b"].astype(np.float32).astype(float)
        result = conditional_flip_loft(a, b)
        self.assertEqual(result["path"], "repair")
        self.assertGreaterEqual(quality(result["mesh"])["min_triangle_quality"], .1)

    def test_invalid_input(self):
        c = next(x for x in cases() if x["name"] == "dev_gentle_circle")
        for kwargs in ({"cuts": 2}, {"seconds": 0}, {"seconds": 100}):
            with self.assertRaises(ValueError):
                conditional_flip_loft(c["a"], c["b"], **kwargs)
        with self.assertRaises(ValueError):
            conditional_flip_loft(c["a"], c["a"])


if __name__ == "__main__":
    unittest.main()
