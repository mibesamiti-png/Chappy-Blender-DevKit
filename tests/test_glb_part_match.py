"""GLB-020: matching suggestions are cautious, anonymous and non-authoritative."""
from __future__ import annotations

import unittest

from cbdk.glb_part_match import suggest_spatial_part_matches


def triangle(x=0.0, z=0.0):
    return [(x, 0., z), (x + 1., 0., z), (x, 1., z)]


def square_frame(*, opening_x=0., opening_half_width=.3,
                 flip_diagonal=False, flip_winding=False, offset_x=0.):
    """Eight-triangle CBDK-only square annulus, one real inner boundary."""
    outer = [(-1., -1., 0.), (1., -1., 0.),
             (1., 1., 0.), (-1., 1., 0.)]
    inner = [
        (opening_x - opening_half_width, -.3, 0.),
        (opening_x + opening_half_width, -.3, 0.),
        (opening_x + opening_half_width, .3, 0.),
        (opening_x - opening_half_width, .3, 0.),
    ]
    vertices = [((x + offset_x), y, z) for x, y, z in outer + inner]
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        if flip_diagonal:
            indices = ((i, j, i + 4), (j, j + 4, i + 4))
        else:
            indices = ((i, j, j + 4), (i, j + 4, i + 4))
        for face in indices:
            tri = [vertices[k] for k in face]
            faces.append(list(reversed(tri)) if flip_winding else tri)
    return faces


class PartCandidatesTests(unittest.TestCase):
    def test_reordered_meshes_are_suggested_by_position_not_index(self):
        ref = [triangle(0), triangle(3)]
        cand = [triangle(3), triangle(0)]
        result = suggest_spatial_part_matches(ref, cand, [1, 1], [1, 1])
        self.assertEqual(
            [r["candidate_part_ids"] for r in result["reference_parts"]],
            [["part_002"], ["part_001"]],
        )
        self.assertTrue(all(r["status"] == "suggested" for r in result["reference_parts"]))
        self.assertFalse(result["cross_file_part_identity_proven"])
        self.assertFalse(result["auto_apply"])
        self.assertEqual(result["unpaired_candidate_part_ids"], [])
        self.assertNotIn("center", str(result))
        self.assertNotIn("source_name", str(result))

    def test_ambiguous_coincident_parts_never_autopair(self):
        same = [triangle(0), triangle(0)]
        result = suggest_spatial_part_matches(same, same, [1, 1], [1, 1])
        self.assertEqual(
            [r["status"] for r in result["reference_parts"]],
            ["ambiguous", "ambiguous"],
        )
        self.assertEqual(result["unpaired_candidate_part_ids"],
                         ["part_001", "part_002"])

    def test_missing_part_is_unmatched_not_misidentified(self):
        result = suggest_spatial_part_matches(
            [triangle(0), triangle(6)], [triangle(0)], [1, 1], [1],
        )
        self.assertEqual(
            [r["status"] for r in result["reference_parts"]],
            ["suggested", "unmatched"],
        )
        self.assertEqual(result["reference_parts"][1]["candidate_part_ids"], [])

    def test_small_displacement_still_proposes_review(self):
        result = suggest_spatial_part_matches(
            [triangle(0), triangle(6)],
            [triangle(6.1), triangle(.1)], [1, 1], [1, 1],
        )
        self.assertEqual(
            [r["candidate_part_ids"] for r in result["reference_parts"]],
            [["part_002"], ["part_001"]],
        )

    def test_closed_vs_open_part_cannot_be_a_confident_match(self):
        a, b, c, d = ((0., 0., 0.), (1., 0., 0.),
                       (0., 1., 0.), (0., 0., 1.))
        closed = [[a, b, c], [a, d, b], [a, c, d], [b, d, c]]
        open_part = closed[1:]
        result = suggest_spatial_part_matches(
            closed, open_part, [4], [3],
        )
        row = result["reference_parts"][0]
        self.assertEqual(row["status"], "ambiguous")
        self.assertTrue(row["topology_review_required"])
        self.assertEqual(row["candidate_part_ids"], ["part_001"])
        self.assertEqual(result["unpaired_candidate_part_ids"], ["part_001"])
        self.assertFalse(result["cross_file_part_identity_proven"])

    def test_equal_open_edge_states_do_not_block_spatial_candidate(self):
        result = suggest_spatial_part_matches(
            [triangle(0.)], [triangle(.03)], [1], [1],
        )
        row = result["reference_parts"][0]
        self.assertEqual(row["status"], "suggested")
        self.assertFalse(row["topology_review_required"])

    def test_equal_bounds_but_different_open_edge_counts_demote_match(self):
        # Two triangles share an edge in the reference, but are disconnected
        # in the candidate. Bounds, centers, face counts and open-edge flags
        # are identical; only the number of boundary edges differs.
        a, b, c, d, e = (
            (0., 0., 0.), (1., 0., 0.), (0., 1., 0.),
            (1., 1., 0.), (.4, .7, 0.),
        )
        reference = [[a, b, c], [b, d, c]]
        candidate = [[a, b, c], [a, d, e]]
        result = suggest_spatial_part_matches(reference, candidate, [2], [2])
        row = result["reference_parts"][0]
        self.assertEqual(row["normalized_score"], 0.0)
        self.assertEqual(row["status"], "ambiguous")
        self.assertEqual(row["candidate_part_ids"], ["part_001"])
        self.assertTrue(row["topology_review_required"])
        self.assertEqual(row["topology_review_reasons"],
                         ["boundary_edge_count_mismatch"])
        self.assertEqual(result["unpaired_candidate_part_ids"], ["part_001"])
        self.assertFalse(result["cross_file_part_identity_proven"])

    def test_nonmanifold_count_change_demotes_even_when_both_observed(self):
        # Both inputs have a nonmanifold edge, but 2 vs 1 such edges.
        # Every triangle is valid and both inputs share the same AABB.
        a, b, c, d = (
            (0., 0., 0.), (1., 0., 0.), (0., 1., 0.), (1., 1., 0.),
        )
        interior = [
            (.10 + .10 * index, .20 + .05 * index, 0.)
            for index in range(6)
        ]
        reference = ([[a, b, interior[i]] for i in range(3)]
                     + [[c, d, interior[i]] for i in range(3, 6)])
        candidate = ([[a, b, interior[i]] for i in range(4)]
                     + [[c, d, interior[i]] for i in range(4, 6)])
        result = suggest_spatial_part_matches(reference, candidate, [6], [6])
        row = result["reference_parts"][0]
        self.assertEqual(row["normalized_score"], 0.0)
        self.assertEqual(row["status"], "ambiguous")
        self.assertTrue(row["topology_review_required"])
        self.assertIn("nonmanifold_edge_count_mismatch",
                      row["topology_review_reasons"])
        self.assertEqual(result["unpaired_candidate_part_ids"], ["part_001"])

    def test_equal_topology_keeps_empty_reasons_for_suggested_match(self):
        result = suggest_spatial_part_matches(
            [triangle(0.)], [triangle(.02)], [1], [1],
        )
        row = result["reference_parts"][0]
        self.assertEqual(row["status"], "suggested")
        self.assertEqual(row["topology_review_reasons"], [])
        self.assertFalse(row["topology_review_required"])

    def test_same_boundary_count_but_moved_opening_is_ambiguous(self):
        reference = square_frame()
        shifted_hole = square_frame(opening_x=.24)
        from cbdk.glb_boundary_audit import boundary_audit
        self.assertEqual(boundary_audit(reference, [8])["parts"][0]["boundary_edges"], 8)
        self.assertEqual(boundary_audit(shifted_hole, [8])["parts"][0]["boundary_edges"], 8)
        row = suggest_spatial_part_matches(
            reference, shifted_hole, [8], [8],
        )["reference_parts"][0]
        self.assertEqual(row["normalized_score"], 0.0)
        self.assertEqual(row["status"], "ambiguous")
        self.assertEqual(row["topology_review_reasons"],
                         ["boundary_spatial_layout_mismatch"])
        self.assertEqual(row["candidate_part_ids"], ["part_001"])

    def test_same_boundary_count_but_resized_opening_is_ambiguous(self):
        reference = square_frame()
        changed = square_frame(opening_half_width=.5)
        result = suggest_spatial_part_matches(reference, changed, [8], [8])
        self.assertEqual(result["reference_parts"][0]["status"], "ambiguous")
        self.assertEqual(result["reference_parts"][0]["topology_review_reasons"],
                         ["boundary_spatial_layout_mismatch"])
        self.assertEqual(result["unpaired_candidate_part_ids"], ["part_001"])
        self.assertFalse(result["cross_file_part_identity_proven"])

    def test_opposite_diagonals_and_reversed_winding_are_not_mismatch(self):
        reference = square_frame()
        same_contour = square_frame(flip_diagonal=True, flip_winding=True)
        row = suggest_spatial_part_matches(
            reference, same_contour, [8], [8],
        )["reference_parts"][0]
        self.assertEqual(row["status"], "suggested")
        self.assertEqual(row["topology_review_reasons"], [])

    def test_symmetric_reflection_same_contour_is_not_mismatch(self):
        reference = square_frame()
        mirrored = [[(-x, y, z) for x, y, z in face]
                    for face in square_frame(flip_diagonal=True)]
        row = suggest_spatial_part_matches(
            reference, mirrored, [8], [8],
        )["reference_parts"][0]
        self.assertEqual(row["status"], "suggested")
        self.assertEqual(row["topology_review_reasons"], [])

    def test_part_translation_and_reordered_parts_still_suggest(self):
        a, b = square_frame(offset_x=-4.), square_frame(offset_x=4.)
        shuffled = square_frame(offset_x=4.04, flip_diagonal=True)
        other = square_frame(offset_x=-3.96, flip_winding=True)
        result = suggest_spatial_part_matches(
            a + b, shuffled + other, [8, 8], [8, 8],
        )
        self.assertEqual([row["status"] for row in result["reference_parts"]],
                         ["suggested", "suggested"])
        self.assertEqual([row["candidate_part_ids"] for row in result["reference_parts"]],
                         [["part_002"], ["part_001"]])
        self.assertTrue(all(not row["topology_review_reasons"]
                            for row in result["reference_parts"]))

    def test_boundary_budget_demotes_without_expensive_pairwise_scan(self):
        # 90 disconnected triangles have 270 distinct open edges.
        faces = [triangle(float(i * 2)) for i in range(90)]
        result = suggest_spatial_part_matches(faces, faces, [90], [90])
        row = result["reference_parts"][0]
        self.assertEqual(row["status"], "ambiguous")
        self.assertEqual(row["topology_review_reasons"],
                         ["boundary_layout_budget_exceeded"])
        self.assertEqual(result["unpaired_candidate_part_ids"], ["part_001"])

    def test_rejects_invalid_parts_and_nonfinite_coordinates(self):
        faces = [triangle()]
        for a, b in (
            ([0], [1]), ([2], [1]), ([True], [1]), ([1] * 65, [1]),
        ):
            with self.subTest(a=a):
                with self.assertRaises(ValueError):
                    suggest_spatial_part_matches(faces, faces, a, b)
        nan = [triangle(0., float("nan"))]
        with self.assertRaises(ValueError):
            suggest_spatial_part_matches(nan, faces, [1], [1])

    def test_never_exceeds_bounded_candidates(self):
        original = [triangle(x * 2.0) for x in range(40)]
        result = suggest_spatial_part_matches(
            original, list(reversed(original)), [1] * 40, [1] * 40,
        )
        self.assertLessEqual(len(result["reference_parts"]), 64)
        self.assertTrue(all(len(r["candidate_part_ids"]) <= 2
                            for r in result["reference_parts"]))


if __name__ == "__main__":
    unittest.main()
