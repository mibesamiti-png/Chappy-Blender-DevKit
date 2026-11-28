"""R22 limited measurements; zero samples never certify physical geometry."""
import unittest
from r22_geometry_fixtures import cases, flatten, inspect_case, summarize
from cbdk.glb_surface_distance import SurfaceDistanceError
from cbdk.glb_multires_surface import compare_expanded_triangle_surfaces

class GeometryLimitsR22(unittest.TestCase):
    def test_preregistered_matrix(self):
        results = []
        for case in cases():
            with self.subTest(case=case["name"]):
                ref,rc = flatten(case["left"])
                cand,cc = flatten(case["right"])
                results.append(inspect_case(case,ref,cand,rc,cc))
        summary = summarize(results)["classification"]
        self.assertEqual(sum(summary.values()),16)
        self.assertEqual(summary["information_absent"],1)
        self.assertEqual(summary["not_measured"],0)
        # Do not require the sparse sampler to find every known aperture.
        self.assertEqual(summary["detected"]+summary["missed"],10)
        self.assertEqual(summary["negative_control"]+summary["false_warning"],5)

    def test_degenerate_is_not_clean(self):
        invalid = [((0.,0.,0.),(1.,0.,0.),(2.,0.,0.))]
        with self.assertRaises(SurfaceDistanceError):
            compare_expanded_triangle_surfaces(invalid,invalid)

if __name__ == "__main__":
    unittest.main()
