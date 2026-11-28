import unittest
import numpy as np
from cbdk_geometry import quality
from cbdk_geometry.radial_loft import radial_loft
from cycles.r4.fixtures import cases


class R5RadialLoftTests(unittest.TestCase):
    def test_r4_development_boundary_contract(self):
        for case in cases("development"):
            a = case["a"].astype(np.float32).astype(float)
            b = case["b"].astype(np.float32).astype(float)
            original_a, original_b = a.copy(), b.copy()
            result = radial_loft(a, b)
            mesh = result["mesh"]
            self.assertFalse(result["approved"])
            self.assertEqual(result["cuts"], 3)
            self.assertTrue(set(map(tuple, np.vstack((a, b)))).issubset(
                set(map(tuple, mesh.vertices))))
            q = quality(mesh)
            self.assertEqual(q["boundary_edges"], len(a)+len(b))
            self.assertEqual(q["nonmanifold_edges"], 0)
            self.assertEqual(q["components"], 1)
            np.testing.assert_array_equal(a, original_a)
            np.testing.assert_array_equal(b, original_b)

    def test_deterministic_proposal(self):
        case = next(cases("development"))
        a, b = case["a"], case["b"]
        m1, m2 = radial_loft(a, b)["mesh"], radial_loft(a, b)["mesh"]
        np.testing.assert_array_equal(m1.vertices, m2.vertices)
        np.testing.assert_array_equal(m1.faces, m2.faces)

    def test_input_rejections(self):
        case = next(cases("development"))
        a, b = case["a"], case["b"]
        invalid = [a[:2], np.full_like(a, np.nan), np.vstack((a, a)),
                   np.roll(a, 0, axis=0).copy()]
        invalid[-1][0, 2] = .1
        for bad in invalid:
            with self.assertRaises(ValueError):
                radial_loft(bad, b)
        with self.assertRaises(ValueError):
            radial_loft(a, b, cuts=2)
        with self.assertRaises(ValueError):
            radial_loft(a, b, seconds=0)
        with self.assertRaises(ValueError):
            radial_loft(a, a)


if __name__ == "__main__":
    unittest.main()
