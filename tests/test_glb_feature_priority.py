"""Feature-aware exploration is a review hint, not a hole/shape proof."""
from __future__ import annotations

import unittest

from cbdk.glb_feature_priority import (
    geometry_feature_hints, choose_exploration_faces,
)
from cbdk.glb_surface_distance import (
    _validated_triangles, SurfaceDistanceError,
)
from cbdk.glb_multires_surface import compare_multires_triangle_surfaces


def square(x0, x1, y0, y1, z=0):
    corners = ((x0, y0, z), (x1, y0, z),
               (x1, y1, z), (x0, y1, z))
    return [[corners[i] for i in idx] for idx in ((0, 1, 2), (0, 2, 3))]


def square_with_hole(half_width=.22):
    o = ((-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0))
    h = half_width
    inner = ((-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0))
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.extend(((o[i], o[j], inner[j]), (o[i], inner[j], inner[i])))
    return [list(f) for f in faces]


def large_panels():
    return square(-30, -10, -8, 8) + square(10, 30, -8, 8)


class FeaturePriorityTests(unittest.TestCase):
    def test_small_center_opening_is_noticed_while_area_only_misses(self):
        reference = large_panels() + square(-1, 1, -1, 1)
        candidate = large_panels() + square_with_hole()
        old = compare_multires_triangle_surfaces(
            reference, candidate, feature_aware=False)
        new = compare_multires_triangle_surfaces(
            reference, candidate, feature_aware=True)
        self.assertEqual(old["refined_symmetric_sampled_max"], 0)
        self.assertGreater(new["refined_symmetric_sampled_max"], .01)
        self.assertTrue(new["new_nonzero_sample_after_refinement"])
        self.assertEqual(new["reference_to_candidate"]["feature_exploration_face_count"], 1)
        self.assertEqual(new["reference_to_candidate"]["area_fallback_face_count"], 1)
        self.assertGreaterEqual(
            new["reference_to_candidate"]["selected_feature_hint_categories"]
            ["bbox_interior_boundary_hint"], 1)

    def test_boundary_edges_can_be_outer_borders_not_holes(self):
        face = _validated_triangles(square(-1, 1, -1, 1), "test")
        hints = geometry_feature_hints(face)
        self.assertTrue(any(x["flags"]["open_boundary_hint"] for x in hints))
        self.assertTrue(all(not x["flags"]["bbox_interior_boundary_hint"]
                            for x in hints))

    def test_inner_opening_edges_receive_bbox_interior_hint(self):
        faces = _validated_triangles(square_with_hole(), "test")
        hints = geometry_feature_hints(faces)
        self.assertGreater(
            sum(x["flags"]["bbox_interior_boundary_hint"] for x in hints), 0)

    def test_sharp_shared_edge_detected(self):
        mesh = [
            [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
            [(0, 0, 0), (1, 0, 0), (0, 0, 1)],
        ]
        records = _validated_triangles(mesh, "test")
        flags = geometry_feature_hints(records)
        self.assertEqual(sum(bool(x["flags"]["sharp_shared_edge_hint"])
                             for x in flags), 2)

    def test_coplanar_triangulation_does_not_claim_sharp_crease(self):
        rows = _validated_triangles(square(-1, 1, -1, 1), "test")
        self.assertTrue(all(not x["flags"]["sharp_shared_edge_hint"]
                            for x in geometry_feature_hints(rows)))

    def test_small_face_preferred_to_larger_face_when_available(self):
        rows = _validated_triangles(
            large_panels() + square(-.2, .2, -.2, .2), "test")
        errors = [[0.0] * 8 for _ in rows]
        selected, reasons, hints = choose_exploration_faces(
            rows, set(), errors, feature_aware=True)
        self.assertEqual(len(selected), 2)
        self.assertEqual(reasons, ["geometry_feature_hint", "area_coverage_fallback"])
        self.assertTrue(hints[selected[0]]["flags"]["small_triangle_hint"])
        self.assertGreater(hints[selected[1]]["area"], hints[selected[0]]["area"])

    def test_area_only_mode_preserves_prior_selection(self):
        rows = _validated_triangles(
            large_panels() + square(-.2, .2, -.2, .2), "test")
        selected, reasons, _ = choose_exploration_faces(
            rows, set(), [[0.0] * 8 for _ in rows], feature_aware=False)
        self.assertEqual(reasons, ["area_coverage_fallback"] * 2)
        self.assertTrue(all(rows[i][1] > 100 for i in selected))

    def test_equal_geometry_order_and_winding_same_aggregate_report(self):
        reference = large_panels() + square(-1, 1, -1, 1)
        candidate = large_panels() + square_with_hole()
        a = compare_multires_triangle_surfaces(reference, candidate)
        b = compare_multires_triangle_surfaces(
            [list(reversed(face)) for face in reversed(reference)],
            [list(reversed(face)) for face in reversed(candidate)])
        self.assertEqual(a, b)

    def test_disable_mode_keeps_existing_narrow_hole_exploration(self):
        filled = square(-1, 1, -1, 1)
        cutout = square_with_hole()
        old = compare_multires_triangle_surfaces(
            filled, cutout, feature_aware=False)
        current = compare_multires_triangle_surfaces(
            filled, cutout, feature_aware=True)
        self.assertGreater(old["refined_symmetric_sampled_max"], .01)
        self.assertGreater(current["refined_symmetric_sampled_max"], .01)

    def test_512_face_safety_limit_and_sample_budget(self):
        rows = [
            [(i * 3, 0, 0), (i * 3 + 1, 0, 0), (i * 3, 1, 0)]
            for i in range(512)
        ]
        result = compare_multires_triangle_surfaces(rows, rows)
        self.assertEqual(result["reference_triangles"], 512)
        self.assertLess(
            result["reference_to_candidate"]["total_sample_count"], 512 * 48)
        self.assertFalse(result["complete_surface_coverage"])

    def test_unsupported_toggle_fails_closed(self):
        with self.assertRaises(SurfaceDistanceError):
            compare_multires_triangle_surfaces(
                square(-1, 1, -1, 1), square(-1, 1, -1, 1),
                feature_aware="on")

    def test_private_coordinates_are_not_in_report(self):
        rows = square(-12345.678, -12344.678, -1, 1)
        report = compare_multires_triangle_surfaces(rows, rows)
        self.assertNotIn("12345", str(report))
        self.assertTrue(all(v is False for v in report["safety"].values()))
        self.assertFalse(report["auto_approve"])

    def test_nonmanifold_edge_is_only_a_priority_hint(self):
        shared = ((0, 0, 0), (1, 0, 0))
        mesh = [
            [shared[0], shared[1], (0, 1, 0)],
            [shared[0], shared[1], (0, 0, 1)],
            [shared[0], shared[1], (0, -1, 0)],
        ]
        rows = _validated_triangles(mesh, "test")
        self.assertTrue(all(x["flags"]["nonmanifold_edge_hint"]
                            for x in geometry_feature_hints(rows)))


if __name__ == "__main__":
    unittest.main()
