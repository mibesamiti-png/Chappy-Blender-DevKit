"""R5 NEXT-008: deterministic, resource-bounded GLB candidate regression.

Only CBDK-authored synthetic triangle soups enter these tests; test output
contains statuses and aggregate resource numbers, not geometry coordinates.
"""
from __future__ import annotations

from statistics import median
import struct
from time import perf_counter
import tracemalloc
import unittest

from cbdk.glb_boundary_audit import boundary_audit
from cbdk.glb_part_match import suggest_spatial_part_matches

from test_glb_match_budget_r4 import many_rings, open_edge_fixture
from test_glb_part_match import nearly_touching_triangles, square_frame


def reorder_faces(faces):
    """Reverse face order while alternating winding and cyclic vertex order."""
    result = []
    for index, face in enumerate(reversed(faces)):
        result.append(list(reversed(face)) if index % 2
                      else list(face[1:]) + [face[0]])
    return result


def float32_faces(faces):
    """Simulate GLB float32 vertex packing without relying on private files."""
    def f32(number):
        return struct.unpack("<f", struct.pack("<f", float(number)))[0]
    return [[tuple(f32(number) for number in point) for point in face]
            for face in faces]


def shifted_faces(faces, amount):
    return [[(x + amount, y - amount / 2., z) for x, y, z in face]
            for face in faces]


class RollingR5DeterminismTests(unittest.TestCase):

    def _check_review_only(self, report):
        self.assertEqual(report["status"], "review_only")
        self.assertFalse(report["auto_apply"])
        self.assertFalse(report["cross_file_part_identity_proven"])

    def test_budget_counts_remain_deterministic_when_faces_and_winding_reordered(self):
        for count, expected, reasons in (
            (255, "suggested", []),
            (256, "suggested", []),
            (257, "ambiguous", ["boundary_layout_budget_exceeded"]),
        ):
            with self.subTest(boundary_edges=count):
                original = open_edge_fixture(count)
                reordered = reorder_faces(original)
                self.assertEqual(
                    boundary_audit(reordered, [len(reordered)])["parts"][0]["boundary_edges"],
                    count,
                )
                first = suggest_spatial_part_matches(
                    original, reordered, [len(original)], [len(reordered)])
                self._check_review_only(first)
                row = first["reference_parts"][0]
                self.assertEqual(row["status"], expected)
                self.assertEqual(row["topology_review_reasons"], reasons)
                self.assertEqual(row["topology_review_required"], bool(reasons))
                self.assertEqual(first["unpaired_candidate_part_ids"],
                                 [] if expected == "suggested" else ["part_001"])
                for _ in range(2):
                    self.assertEqual(first, suggest_spatial_part_matches(
                        original, reordered, [len(original)], [len(reordered)]))

    def test_256_edge_float32_translation_and_micro_coordinate_change(self):
        reference = open_edge_fixture(256)
        rounded = float32_faces(reorder_faces(reference))
        translated = shifted_faces(rounded, .0001)
        for case in (rounded, translated):
            with self.subTest(case="shifted" if case is translated else "float32"):
                report = suggest_spatial_part_matches(
                    reference, case, [86], [86])
                self._check_review_only(report)
                row = report["reference_parts"][0]
                self.assertEqual(row["status"], "suggested")
                self.assertEqual(row["topology_review_reasons"], [])
                self.assertEqual(report, suggest_spatial_part_matches(
                    reference, case, [86], [86]))

    def test_micro_hole_jitter_is_stable_but_large_movement_demotes(self):
        reference = float32_faces(square_frame())
        micro = float32_faces(reorder_faces(square_frame(opening_x=.00004)))
        moved = float32_faces(reorder_faces(square_frame(opening_x=.24)))
        expected = (
            (micro, "suggested", []),
            (moved, "ambiguous", ["boundary_spatial_layout_mismatch"]),
        )
        for candidate, status, reasons in expected:
            with self.subTest(status=status):
                rows = [
                    suggest_spatial_part_matches(reference, candidate, [8], [8])
                    for _ in range(3)
                ]
                self.assertTrue(all(row == rows[0] for row in rows))
                self.assertEqual(rows[0]["reference_parts"][0]["status"], status)
                self.assertEqual(rows[0]["reference_parts"][0]
                                 ["topology_review_reasons"], reasons)
                self._check_review_only(rows[0])

    def test_sub_tolerance_disconnection_never_promoted_by_permutation(self):
        apart = float32_faces(nearly_touching_triangles())
        contact = float32_faces(nearly_touching_triangles(touch=True))
        for source, target in ((apart, contact), (contact, apart)):
            for candidate in (target, reorder_faces(target)):
                with self.subTest(reverse=source is contact,
                                  reorder=candidate is not target):
                    report = suggest_spatial_part_matches(
                        source, candidate, [2], [2])
                    row = report["reference_parts"][0]
                    self.assertEqual(row["status"], "ambiguous")
                    self.assertEqual(row["topology_review_reasons"],
                                     ["boundary_component_count_mismatch"])
                    self._check_review_only(report)

    def test_coincident_64_parts_fail_closed_even_when_face_order_changes(self):
        reference = [face for _ in range(64) for face in square_frame()]
        candidate = reorder_faces(reference)
        counts = [8] * 64
        snapshots = [
            suggest_spatial_part_matches(reference, candidate, counts, counts)
            for _ in range(2)
        ]
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertTrue(all(row["status"] == "ambiguous"
                            and len(row["candidate_part_ids"]) <= 2
                            for row in snapshots[0]["reference_parts"]))
        self.assertEqual(snapshots[0]["unpaired_candidate_part_ids"],
                         [f"part_{i:03d}" for i in range(1, 65)])
        self._check_review_only(snapshots[0])

    def test_reordered_64_part_512_face_scene_resource_is_bounded_and_stable(self):
        groups = many_rings()
        reference = [face for group in groups for face in group]
        candidate = [face for group in reversed(groups)
                     for face in reorder_faces(group)]
        counts = [8] * 64
        start = perf_counter()
        tracemalloc.start()
        try:
            first = suggest_spatial_part_matches(
                reference, candidate, counts, counts)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        elapsed_ms = (perf_counter() - start) * 1000.
        self.assertLess(peak, 32 * 1024 * 1024)
        self.assertEqual(
            [row["candidate_part_ids"] for row in first["reference_parts"]],
            [[f"part_{64-i:03d}"] for i in range(64)],
        )
        self.assertTrue(all(row["status"] == "suggested"
                            and not row["topology_review_reasons"]
                            for row in first["reference_parts"]))
        self._check_review_only(first)
        self.assertEqual(first, suggest_spatial_part_matches(
            reference, candidate, counts, counts))
        # Only aggregate synthetic-fixture numbers; no model coordinates.
        print(f"CBDK_R5_64PARTS_REVIEW ms={elapsed_ms:.3f} peak_kib={peak//1024}")

    def test_256_edge_repeated_median_and_257_fail_closed_budget(self):
        exact = open_edge_fixture(256)
        over = open_edge_fixture(257)
        times = []
        # Warm up the path, then time a small number of repeatable samples.
        suggest_spatial_part_matches(exact, exact, [86], [86])
        for _ in range(5):
            t0 = perf_counter()
            result = suggest_spatial_part_matches(exact, exact, [86], [86])
            times.append((perf_counter() - t0) * 1000.)
            self.assertEqual(result["reference_parts"][0]["status"], "suggested")
            self._check_review_only(result)
        budget = suggest_spatial_part_matches(over, reorder_faces(over),
                                              [87], [87])
        self.assertEqual(budget["reference_parts"][0]["status"], "ambiguous")
        self.assertEqual(budget["reference_parts"][0]["topology_review_reasons"],
                         ["boundary_layout_budget_exceeded"])
        self._check_review_only(budget)
        print(f"CBDK_R5_256EDGES median_ms={median(times):.3f} samples=5")


if __name__ == "__main__":
    unittest.main()
