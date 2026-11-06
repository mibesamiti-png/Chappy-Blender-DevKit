"""GLB-020: coordinate-welded edge observations are bounded and non-authoritative."""
from __future__ import annotations

import unittest

from cbdk.glb_boundary_audit import boundary_audit, local_boundary_segments

A, B, C, D = ((0., 0., 0.), (1., 0., 0.), (0., 1., 0.), (0., 0., 1.))
TETRA = [[A, B, C], [A, D, B], [A, C, D], [B, D, C]]


class BoundaryEdgeAuditTests(unittest.TestCase):
    def test_closed_tetra_has_no_observed_boundary(self):
        result = boundary_audit(TETRA, [4])
        p = result["parts"][0]
        self.assertEqual(p["boundary_edges"], 0)
        self.assertEqual(p["shared_edges"], 6)
        self.assertEqual(p["nonmanifold_edge_incidence"], 0)
        self.assertEqual(p["unique_edges"], 6)
        self.assertFalse(p["observed_boundary"])
        self.assertFalse(result["fully_watertight_proven"])
        self.assertFalse(result["internal_voids_verified"])
        self.assertFalse(p["topology_proven"])

    def test_removed_tetra_cap_creates_three_exposed_edges(self):
        result = boundary_audit(TETRA[1:], [3])
        self.assertEqual(result["parts"][0]["boundary_edges"], 3)
        self.assertTrue(result["parts"][0]["observed_boundary"])
        self.assertFalse(result["hole_locations_verified"])

    def test_anonymous_part_counts_remain_separate(self):
        open_tri = [[(5., 0., 0.), (6., 0., 0.), (5., 1., 0.)]]
        result = boundary_audit(TETRA + open_tri, [4, 1])
        self.assertEqual([p["part_id"] for p in result["parts"]],
                         ["part_001", "part_002"])
        self.assertEqual([p["boundary_edges"] for p in result["parts"]], [0, 3])
        self.assertEqual(result["summary"]["parts_with_observed_boundaries"], 1)
        self.assertNotIn("source_name", str(result))
        self.assertNotIn("coordinates", str(result))

    def test_close_but_distinct_vertices_are_welded_approximately(self):
        faces = [
            [A, B, C],
            [(1. + 2e-9, 0., 0.), (1., 1., 0.), (0., 1. + 2e-9, 0.)],
        ]
        result = boundary_audit(faces, [2])
        self.assertEqual(result["parts"][0]["boundary_edges"], 4)
        self.assertTrue(result["coordinate_welding_is_approximate"])

    def test_three_faces_share_edge_reports_nonmanifold_incidence(self):
        faces = [
            [A, B, C],
            [A, B, D],
            [A, B, (0., -1., 0.)],
        ]
        result = boundary_audit(faces, [3])
        self.assertEqual(result["parts"][0]["nonmanifold_edge_incidence"], 1)
        self.assertTrue(result["parts"][0]["observed_nonmanifold_edge"])

    def test_face_order_invariance_for_one_part(self):
        one = boundary_audit(TETRA, [4])["parts"][0]
        two = boundary_audit(list(reversed(TETRA)), [4])["parts"][0]
        self.assertEqual(one, two)

    def test_private_boundary_lines_closed_and_open_tetra(self):
        self.assertEqual(local_boundary_segments(TETRA, [4]), [])
        segments = local_boundary_segments(TETRA[1:], [3])
        self.assertEqual(len(segments), 3)
        self.assertTrue(all(len(line) == 7 and line[0] == 1
                            for line in segments))
        # The removed cap is the ABC plane. Its outline connects A/B/C.
        points = {tuple(round(value, 6) for value in line[i:i+3])
                  for line in segments for i in (1, 4)}
        self.assertEqual(points, {A, B, C})
        self.assertNotIn("vertex", str(boundary_audit(TETRA[1:], [3])))

    def test_private_lines_are_part_scoped_and_face_order_stable(self):
        other = [[(5., 0., 0.), (6., 0., 0.), (5., 1., 0.)]]
        faces = TETRA + other
        segments = local_boundary_segments(faces, [4, 1])
        self.assertEqual(len(segments), 3)
        self.assertTrue(all(line[0] == 2 for line in segments))
        self.assertEqual(
            local_boundary_segments(list(reversed(TETRA)) + other, [4, 1]),
            segments,
        )

    def test_boundary_overlay_rejects_invalid_part_layout(self):
        with self.assertRaises(ValueError):
            local_boundary_segments(TETRA, [1, 2])
        with self.assertRaises(ValueError):
            local_boundary_segments(TETRA * 129, [516])

    def test_nonfinite_degenerate_and_bad_part_layout_are_rejected(self):
        for faces, counts in (
            (TETRA, [2, 1]),
            (TETRA, [0, 4]),
            (TETRA, [True, 3]),
            (TETRA, [1] * 65),
            ([], []),
            ([[A, B, (float("nan"), 1., 0.)]], [1]),
            ([[A, A, B]], [1]),
        ):
            with self.subTest(counts=counts):
                with self.assertRaises(ValueError):
                    boundary_audit(faces, counts)


if __name__ == "__main__":
    unittest.main()
