import unittest
import numpy as np

from cbdk_geometry import quality
from cbdk_geometry.radial_loft import radial_loft
from cbdk_geometry.warped_loft import warped_radial_loft
from cycles.r7.fixtures import cases


class R7WarpedTests(unittest.TestCase):
    def test_development_topology_and_exact_input(self):
        for c in cases():
            if c["split"] != "development":
                continue
            a = c["a"].astype(np.float32).astype(float)
            b = c["b"].astype(np.float32).astype(float)
            before_a, before_b = a.copy(), b.copy()
            result = warped_radial_loft(a, b)
            mesh = result["mesh"]
            self.assertFalse(result["approved"])
            expected = np.vstack((a, b))
            self.assertTrue(set(map(tuple, expected)).issubset(set(map(tuple, mesh.vertices))))
            q = quality(mesh)
            self.assertEqual(q["boundary_edges"], len(a) + len(b))
            self.assertEqual(q["nonmanifold_edges"], 0)
            self.assertEqual(q["components"], 1)
            np.testing.assert_array_equal(a, before_a)
            np.testing.assert_array_equal(b, before_b)
            with self.assertRaises(ValueError):
                radial_loft(a, b)

    def test_deterministic_development(self):
        c = next(c for c in cases() if c["split"] == "development")
        one = warped_radial_loft(c["a"], c["b"])["mesh"]
        two = warped_radial_loft(c["a"], c["b"])["mesh"]
        np.testing.assert_array_equal(one.vertices, two.vertices)
        np.testing.assert_array_equal(one.faces, two.faces)

    def test_invalid_and_disjoint_envelope(self):
        c = next(c for c in cases() if c["split"] == "development")
        a, b = c["a"], c["b"]
        for invalid in (a[:2], np.full_like(a, np.nan), np.vstack((a, a))):
            with self.assertRaises(ValueError):
                warped_radial_loft(invalid, b)
        with self.assertRaises(ValueError):
            warped_radial_loft(a, a)
        with self.assertRaises(ValueError):
            warped_radial_loft(a, b, cuts=2)
        with self.assertRaises(ValueError):
            warped_radial_loft(a, b, seconds=0)


if __name__ == "__main__":
    unittest.main()
