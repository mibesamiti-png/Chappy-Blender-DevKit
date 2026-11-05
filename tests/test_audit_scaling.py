"""v0.16 safeguards and resource measurements for streamed BMesh edit audits.

Performance observations are printed by the dedicated benchmark script rather
than enforcing machine-dependent "fast enough" claims in unit tests.
"""
import math
import unittest

from parts.blender.context import BlenderContextError
from parts.blender.edit_audit import (
    MAX_AUDIT_ELEMENTS, audit_live_vertex_translation,
    audit_vertex_translation, capture_edit_snapshot, preflight_audit_size,
)


class V:
    def __init__(self, coord=(0., 0., 0.), selected=False):
        self.co = tuple(coord)
        self.select = selected


class E:
    def __init__(self, a, b):
        self.verts = (a, b)


class F:
    def __init__(self, vertices):
        self.verts = tuple(vertices)


class BM:
    def __init__(self, vertices, edges=(), faces=()):
        self.verts = list(vertices)
        self.edges = list(edges)
        self.faces = list(faces)


def tri():
    verts = [V((0, 0, 0), True), V((1, 0, 0)), V((0, 1, 0))]
    return BM(verts, [E(verts[0], verts[1]), E(verts[1], verts[2]),
                      E(verts[2], verts[0])], [F(verts)])


class SizeOnly:
    """A large BMesh collection that raises if Python tries to enumerate it."""
    def __init__(self, length):
        self.length = length

    def __len__(self):
        return self.length

    def __iter__(self):
        raise AssertionError("Must reject before allocating or enumerating")


class StreamingAuditTests(unittest.TestCase):
    def test_size_guard_checks_before_copying_elements(self):
        bm = BM([])
        bm.verts = SizeOnly(MAX_AUDIT_ELEMENTS + 1)
        with self.assertRaisesRegex(BlenderContextError, "size limit"):
            capture_edit_snapshot(bm)

    def test_streaming_audit_checks_limit_before_enumeration(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        bm.verts = SizeOnly(MAX_AUDIT_ELEMENTS + 1)
        with self.assertRaisesRegex(BlenderContextError, "size limit"):
            audit_live_vertex_translation(before, bm, (0., 0., 0.1))

    def test_boundary_accepted_and_above_rejected(self):
        bm = BM([V()] * MAX_AUDIT_ELEMENTS)
        self.assertEqual(preflight_audit_size(bm), (MAX_AUDIT_ELEMENTS, 0, 0))
        bm.verts.append(V())
        with self.assertRaises(BlenderContextError):
            preflight_audit_size(bm)

    def test_streamed_matches_snapshot_for_valid_edit(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0., 0., 0.125)
        actual = audit_live_vertex_translation(before, bm, (0., 0., 0.125))
        expected = audit_vertex_translation(before, capture_edit_snapshot(bm),
                                            (0., 0., 0.125))
        self.assertEqual(actual, expected)
        self.assertTrue(actual.valid)

    def test_streamed_finds_unselected_coordinate_tamper(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0., 0., 0.125)
        bm.verts[1].co = (1., 0., 0.05)
        report = audit_live_vertex_translation(before, bm, (0., 0., 0.125))
        self.assertFalse(report.valid)
        self.assertEqual(report.unexpected_vertices, (1,))

    def test_streamed_finds_selection_change(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0., 0., 0.1)
        bm.verts[2].select = True
        report = audit_live_vertex_translation(before, bm, (0., 0., 0.1))
        self.assertFalse(report.valid)
        self.assertTrue(report.selection_changed)

    def test_streamed_finds_topology_rewire_with_equal_counts(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0., 0., 0.1)
        bm.edges[0] = E(bm.verts[1], bm.verts[2])
        report = audit_live_vertex_translation(before, bm, (0., 0., 0.1))
        self.assertFalse(report.valid)
        self.assertTrue(report.topology_changed)

    def test_streamed_finds_nonfinite_coordinate(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0., 0., math.inf)
        report = audit_live_vertex_translation(before, bm, (0., 0., 0.1))
        self.assertFalse(report.valid)
        self.assertEqual(report.unexpected_vertices, (0,))

    def test_old_and_streaming_both_reject_subprecision_noop(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        delta = (0.0, 0.0, 0.000001)
        old = audit_vertex_translation(before, capture_edit_snapshot(bm), delta)
        live = audit_live_vertex_translation(before, bm, delta)
        self.assertEqual(old, live)
        self.assertFalse(old.valid)
        self.assertFalse(old.expected_delta_matched)

    def test_old_and_streaming_both_reject_nonzero_unselected_noop(self):
        bm = tri()
        bm.verts[0].select = False
        before = capture_edit_snapshot(bm)
        delta = (0.0, 0.0, 0.125)
        old = audit_vertex_translation(before, capture_edit_snapshot(bm), delta)
        live = audit_live_vertex_translation(before, bm, delta)
        self.assertEqual(old, live)
        self.assertFalse(live.valid)

    def test_old_and_streaming_validate_non_numeric_delta_consistently(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        for bad in (("bad", 0.0, 0.0), (True, 0.0, 0.1), (None, 0.0, 0.1)):
            with self.subTest(bad=bad):
                with self.assertRaises(BlenderContextError):
                    audit_vertex_translation(before, before, bad)
                with self.assertRaises(BlenderContextError):
                    audit_live_vertex_translation(before, bm, bad)

    def test_both_reject_one_missing_axis_in_mixed_translation(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0.125, 0., 0.)  # X succeeded, tiny Y was lost
        delta = (0.125, 0.000001, 0.)
        old = audit_vertex_translation(before, capture_edit_snapshot(bm), delta)
        live = audit_live_vertex_translation(before, bm, delta)
        self.assertEqual(old, live)
        self.assertFalse(live.valid)
        self.assertEqual(live.unexpected_vertices, (0,))

    def test_both_reject_subthreshold_unselected_coordinate_tamper(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0., 0., 0.125)
        bm.verts[1].co = (1.000001, 0., 0.)
        delta = (0., 0., 0.125)
        old = audit_vertex_translation(before, capture_edit_snapshot(bm), delta)
        live = audit_live_vertex_translation(before, bm, delta)
        self.assertEqual(old, live)
        self.assertFalse(live.valid)
        self.assertEqual(live.unexpected_vertices, (1,))

    def test_both_reject_tiny_underdelivery_even_if_axis_changed(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0., 0., 0.0000001)
        delta = (0., 0., 0.000001)
        old = audit_vertex_translation(before, capture_edit_snapshot(bm), delta)
        live = audit_live_vertex_translation(before, bm, delta)
        self.assertEqual(old, live)
        self.assertFalse(live.valid)
        self.assertEqual(live.unexpected_vertices, (0,))

    def test_both_accept_correct_tiny_delta(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0., 0., 0.000001)
        delta = (0., 0., 0.000001)
        old = audit_vertex_translation(before, capture_edit_snapshot(bm), delta)
        live = audit_live_vertex_translation(before, bm, delta)
        self.assertEqual(old, live)
        self.assertTrue(live.valid)
        self.assertEqual(live.moved_vertices, (0,))

    def test_selected_axis_without_offset_must_stay_identical(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0.000001, 0., 0.125)
        delta = (0., 0., 0.125)
        old = audit_vertex_translation(before, capture_edit_snapshot(bm), delta)
        live = audit_live_vertex_translation(before, bm, delta)
        self.assertEqual(old, live)
        self.assertFalse(live.valid)
        self.assertEqual(live.unexpected_vertices, (0,))

    def test_streamed_detects_silent_noop(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        report = audit_live_vertex_translation(before, bm, (0., 0., 0.1))
        self.assertFalse(report.valid)
        self.assertFalse(report.expected_delta_matched)

    def test_huge_world_coordinates_do_not_hide_small_error(self):
        # Old relative tolerance scaled by world position and silently
        # accepted a missing movement at x=1_000_000.
        bm = BM([V((1_000_000., 0., 0.), True)])
        before = capture_edit_snapshot(bm)
        report = audit_live_vertex_translation(before, bm, (0.125, 0., 0.))
        self.assertFalse(report.valid)

    def test_unmodified_zero_delta_accepted_for_direct_audit_only(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        report = audit_live_vertex_translation(before, bm, (0., 0., 0.))
        self.assertTrue(report.valid)
        self.assertEqual(report.moved_vertices, ())

    def test_invalid_delta_rejected(self):
        bm = tri()
        before = capture_edit_snapshot(bm)
        for invalid in ((math.nan, 0., 0.), [0., 0., 0.1], (0., 1.), (math.inf, 0., 0.)):
            with self.subTest(invalid=invalid):
                with self.assertRaises(BlenderContextError):
                    audit_live_vertex_translation(before, bm, invalid)


if __name__ == "__main__":
    unittest.main()
