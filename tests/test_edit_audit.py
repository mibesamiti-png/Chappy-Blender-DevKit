"""Unit tests for immutable BMesh snapshots, diff auditing and safe rollback."""
import math
import unittest
from dataclasses import FrozenInstanceError

from parts.blender.context import BlenderContextError
from parts.blender.edit_audit import (
    MAX_AUDIT_ELEMENTS, MeshEditSnapshot, audit_vertex_translation,
    capture_edit_snapshot, restore_edit_snapshot,
)


class Vert:
    def __init__(self, co, select=False):
        self.co = tuple(co)
        self.select = select

    def select_set(self, value):
        self.select = bool(value)


class Edge:
    def __init__(self, left, right):
        self.verts = (left, right)


class Face:
    def __init__(self, *verts):
        self.verts = verts


def sample_mesh():
    a, b, c = Vert((0, 0, 0), True), Vert((1, 0, 0)), Vert((0, 1, 0))
    mesh = type("FakeBMesh", (), {})()
    mesh.verts = [a, b, c]
    mesh.edges = [Edge(a, b), Edge(b, c), Edge(c, a)]
    mesh.faces = [Face(a, b, c)]
    return mesh


class EditAuditTests(unittest.TestCase):
    def test_capture_contains_detached_immutable_data(self):
        bm = sample_mesh()
        snap = capture_edit_snapshot(bm)
        self.assertEqual(snap.coordinates, ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)))
        self.assertEqual(snap.selected, (True, False, False))
        self.assertEqual(snap.edges, ((0, 1), (0, 2), (1, 2)))
        self.assertEqual(snap.faces, ((0, 1, 2),))
        bm.verts[0].co = (3, 3, 3)
        self.assertEqual(snap.coordinates[0], (0.0, 0.0, 0.0))
        with self.assertRaises(FrozenInstanceError):
            snap.selected = ()

    def test_requested_single_vertex_translation_passes(self):
        bm = sample_mesh()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0, 0, 0.125)
        diff = audit_vertex_translation(before, capture_edit_snapshot(bm), (0.0, 0.0, 0.125))
        self.assertTrue(diff.valid)
        self.assertEqual(diff.moved_vertices, (0,))
        self.assertEqual(diff.unexpected_vertices, ())
        self.assertFalse(diff.selection_changed)
        self.assertFalse(diff.topology_changed)

    def test_unselected_vertex_change_fails(self):
        bm = sample_mesh()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0, 0, 0.1)
        bm.verts[2].co = (4, 5, 6)
        diff = audit_vertex_translation(before, capture_edit_snapshot(bm), (0, 0, 0.1))
        self.assertFalse(diff.valid)
        self.assertEqual(diff.unexpected_vertices, (2,))

    def test_wrong_delta_fails_even_when_selected(self):
        bm = sample_mesh()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0, 0, 0.25)
        diff = audit_vertex_translation(before, capture_edit_snapshot(bm), (0, 0, 0.1))
        self.assertFalse(diff.valid)
        self.assertFalse(diff.expected_delta_matched)

    def test_selection_change_detected(self):
        bm = sample_mesh()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0, 0, 0.1)
        bm.verts[1].select_set(True)
        diff = audit_vertex_translation(before, capture_edit_snapshot(bm), (0, 0, 0.1))
        self.assertFalse(diff.valid)
        self.assertTrue(diff.selection_changed)

    def test_connectivity_change_detected_with_equal_counts(self):
        bm = sample_mesh()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (0, 0, 0.1)
        bm.edges[0] = Edge(bm.verts[1], bm.verts[2])
        diff = audit_vertex_translation(before, capture_edit_snapshot(bm), (0, 0, 0.1))
        self.assertTrue(diff.topology_changed)
        self.assertFalse(diff.valid)

    def test_restoration_includes_coordinates_and_selection(self):
        bm = sample_mesh()
        before = capture_edit_snapshot(bm)
        bm.verts[0].co = (1, 2, 3)
        bm.verts[1].select_set(True)
        restore_edit_snapshot(bm, before)
        self.assertEqual(capture_edit_snapshot(bm), before)

    def test_restore_after_nonfinite_coordinate_corruption(self):
        bm = sample_mesh()
        saved = capture_edit_snapshot(bm)
        bm.verts[0].co = (math.nan, math.inf, 1.0)
        bm.verts[2].select_set(True)
        restore_edit_snapshot(bm, saved)
        self.assertEqual(capture_edit_snapshot(bm), saved)

    def test_restore_without_reading_broken_coordinate(self):
        bm = sample_mesh()
        saved = capture_edit_snapshot(bm)
        bm.verts[0].co = object()
        restore_edit_snapshot(bm, saved)
        self.assertEqual(capture_edit_snapshot(bm), saved)

    def test_restore_rejects_silent_setter_failure(self):
        class NoopVert(Vert):
            def __setattr__(self, name, value):
                if name == "co" and getattr(self, "lock", False):
                    return
                object.__setattr__(self, name, value)

        bm = sample_mesh()
        vertex = bm.verts[0]
        vertex.__class__ = NoopVert
        saved = capture_edit_snapshot(bm)
        vertex.co = (7, 7, 7)
        vertex.lock = True
        with self.assertRaisesRegex(BlenderContextError, "restoration mismatch"):
            restore_edit_snapshot(bm, saved)

    def test_refuse_restore_if_topology_different(self):
        bm = sample_mesh()
        before = capture_edit_snapshot(bm)
        bm.edges[0] = Edge(bm.verts[1], bm.verts[2])
        with self.assertRaisesRegex(BlenderContextError, "Topology changed"):
            restore_edit_snapshot(bm, before)

    def test_nonfinite_vertex_rejected(self):
        bm = sample_mesh()
        bm.verts[2].co = (math.nan, 0, 0)
        with self.assertRaisesRegex(BlenderContextError, "non-finite"):
            capture_edit_snapshot(bm)

    def test_large_mesh_rejected_before_copy(self):
        bm = sample_mesh()
        bm.verts = [bm.verts[0]] * (MAX_AUDIT_ELEMENTS + 1)
        with self.assertRaisesRegex(BlenderContextError, "size limit"):
            capture_edit_snapshot(bm)

    def test_bad_delta_rejected(self):
        bm = sample_mesh()
        snap = capture_edit_snapshot(bm)
        for bad in ((math.nan, 0, 0), (math.inf, 0, 0), (1, 2), [0, 0, 1]):
            with self.subTest(delta=bad):
                with self.assertRaises(BlenderContextError):
                    audit_vertex_translation(snap, snap, bad)

    def test_unchanged_mesh_is_valid_for_zero_expected_delta(self):
        bm = sample_mesh()
        snap = capture_edit_snapshot(bm)
        result = audit_vertex_translation(snap, snap, (0.0, 0.0, 0.0))
        self.assertTrue(result.valid)
        self.assertEqual(result.moved_vertices, ())


if __name__ == "__main__":
    unittest.main()
