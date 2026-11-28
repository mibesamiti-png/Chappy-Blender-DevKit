"""Team B R4: bounded synthetic contour workloads; review-only outcomes.

No third-party or private GLB inputs, raw geometry in reports, or part IDs
derived from user source names. The 256 edge limit is *per part*.
"""
from __future__ import annotations

from time import perf_counter
import tracemalloc
import unittest

from cbdk.glb_boundary_audit import boundary_audit
from cbdk.glb_part_match import (
    MAX_LAYOUT_BOUNDARY_EDGES,
    suggest_spatial_part_matches,
)
from cbdk.glb_surface_distance import SurfaceDistanceError

from test_glb_part_match import nearly_touching_triangles, square_frame


def open_edge_fixture(edge_count):
    """Exactly 255/256/257 boundary edges without duplicate/welded vertices."""
    if edge_count not in (255, 256, 257):
        raise ValueError("Only authored deterministic budget fixtures")
    # 84 disconnected triangles = 252 open edges; all world-separated.
    count = 85 if edge_count == 255 else 84
    triangles = [
        [(3. * i, 0., 0.), (3. * i + 1., 0., 0.),
         (3. * i, 1., 0.)]
        for i in range(count)
    ]
    if edge_count == 256:
        # Two triangles share an internal diagonal: 4 outer open edges.
        a, b, c, d = ((300., 0., 0.), (301., 0., 0.),
                      (300., 1., 0.), (301., 1., 0.))
        triangles += [[a, b, c], [b, d, c]]
    elif edge_count == 257:
        # Three-triangle fan: polygon boundary has five open edges.
        a, b, c, d, e = ((300., 0., 0.), (301., 0., 0.),
                         (302., 1., 0.), (301., 2., 0.), (300., 2., 0.))
        triangles += [[a, b, c], [a, c, d], [a, d, e]]
    return triangles


def many_rings():
    """64 anonymous 8-face square frames, well separated in a 4x4x4 grid."""
    groups = []
    for index in range(64):
        x = (index % 4) * 12.
        y = ((index // 4) % 4) * 12.
        z = (index // 16) * 12.
        groups.append([
            [(a + x, b + y, c + z) for a, b, c in face]
            for face in square_frame()
        ])
    return groups


def scaled(faces, factor, *, shift_x=0.):
    return [
        [(x * factor + shift_x, y * factor, z * factor)
         for x, y, z in face]
        for face in faces
    ]


class BudgetAndScaleReviewTests(unittest.TestCase):

    def test_exact_255_256_edges_still_suggest_but_257_fails_closed(self):
        self.assertEqual(MAX_LAYOUT_BOUNDARY_EDGES, 256)
        for edges, expected, reasons in (
            (255, "suggested", []),
            (256, "suggested", []),
            (257, "ambiguous", ["boundary_layout_budget_exceeded"]),
        ):
            with self.subTest(observed_boundary_edges=edges):
                faces = open_edge_fixture(edges)
                audit = boundary_audit(faces, [len(faces)])
                self.assertEqual(audit["parts"][0]["boundary_edges"], edges)
                self.assertEqual(audit["parts"][0]["nonmanifold_edge_incidence"], 0)
                start = perf_counter()
                result = suggest_spatial_part_matches(
                    faces, faces, [len(faces)], [len(faces)]
                )
                self.assertGreaterEqual(perf_counter() - start, 0.)
                row = result["reference_parts"][0]
                self.assertEqual(row["status"], expected)
                self.assertEqual(row["topology_review_reasons"], reasons)
                self.assertFalse(result["auto_apply"])
                self.assertFalse(result["cross_file_part_identity_proven"])
                self.assertEqual(result["unpaired_candidate_part_ids"],
                                 [] if expected == "suggested" else ["part_001"])

    def test_exact_512_triangles_64_parts_reordered_without_false_matches(self):
        groups = many_rings()
        reference = [face for group in groups for face in group]
        candidate = [
            [(x + .08, y + .04, z) for x, y, z in face]
            for group in reversed(groups) for face in group
        ]
        counts = [8] * 64
        self.assertEqual(len(reference), 512)
        self.assertEqual(len(candidate), 512)
        assert len(counts) == 64
        start = perf_counter()
        tracemalloc.start()
        try:
            result = suggest_spatial_part_matches(reference, candidate, counts, counts)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        elapsed = perf_counter() - start
        self.assertGreaterEqual(elapsed, 0.)
        self.assertLess(peak, 32 * 1024 * 1024)  # generous hard memory budget
        self.assertEqual(
            [r["candidate_part_ids"][0] for r in result["reference_parts"]],
            [f"part_{64 - i:03d}" for i in range(64)],
        )
        self.assertTrue(all(r["status"] == "suggested"
                            and not r["topology_review_reasons"]
                            for r in result["reference_parts"]))
        self.assertEqual(result["unpaired_candidate_part_ids"], [])
        self.assertFalse(result["auto_apply"])
        self.assertFalse(result["cross_file_part_identity_proven"])

    def test_513_triangles_and_65_parts_are_rejected_before_pairing(self):
        source = [
            [(3. * i, 0., 0.), (3. * i + 1., 0., 0.),
             (3. * i, 1., 0.)]
            for i in range(513)
        ]
        with self.assertRaises(SurfaceDistanceError):
            suggest_spatial_part_matches(source, source, [513], [513])
        with self.assertRaises(ValueError):
            suggest_spatial_part_matches(source[:65], source[:65],
                                         [1] * 65, [1] * 65)

    def test_R3_gap_and_point_contact_across_uniform_scene_scales(self):
        for factor in (.001, 1., 1000.):
            with self.subTest(uniform_scale=factor):
                apart = scaled(nearly_touching_triangles(), factor)
                touch = scaled(nearly_touching_triangles(touch=True), factor)
                for reference, candidate in ((apart, touch), (touch, apart)):
                    row = suggest_spatial_part_matches(
                        reference, candidate, [2], [2],
                    )["reference_parts"][0]
                    self.assertEqual(row["status"], "ambiguous")
                    self.assertEqual(row["topology_review_reasons"],
                                     ["boundary_component_count_mismatch"])
                same = suggest_spatial_part_matches(apart, apart, [2], [2])
                self.assertEqual(same["reference_parts"][0]["status"], "suggested")

    def test_R2_same_contour_retessellation_and_moved_hole_during_scale(self):
        for factor in (.01, 1., 100.):
            with self.subTest(uniform_scale=factor):
                ref = scaled(square_frame(), factor)
                same = scaled(square_frame(flip_diagonal=True), factor)
                moved = scaled(square_frame(opening_x=.24), factor)
                row_same = suggest_spatial_part_matches(ref, same, [8], [8])[
                    "reference_parts"][0]
                row_moved = suggest_spatial_part_matches(ref, moved, [8], [8])[
                    "reference_parts"][0]
                self.assertEqual(row_same["status"], "suggested")
                self.assertEqual(row_same["topology_review_reasons"], [])
                self.assertEqual(row_moved["status"], "ambiguous")
                self.assertEqual(row_moved["topology_review_reasons"],
                                 ["boundary_spatial_layout_mismatch"])


if __name__ == "__main__":
    unittest.main()
