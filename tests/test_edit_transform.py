"""Safety regression tests for CBDK v0.14 selected-vertex transformation."""
import math
import sys
import types
import unittest
from unittest.mock import patch

from parts.blender.context import BlenderContextError
from parts.blender.edit_transform import (
    MAX_ABS_COORD, VertexTranslationResult, translate_selected_vertices,
)


class FakeVertex:
    def __init__(self, coord, selected=True, *, fail_once=False):
        self._co = tuple(coord)
        self.select = selected
        self.fail_once = fail_once

    @property
    def co(self):
        return self._co

    @co.setter
    def co(self, new):
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("injected write failure")
        self._co = tuple(new)


class FakeBMesh:
    def __init__(self, verts):
        self.verts = verts


def setup(verts=None, *, updater=None):
    verts = verts if verts is not None else [
        FakeVertex((1, 2, 3)), FakeVertex((0, 1, 0), selected=False)
    ]
    mesh = types.SimpleNamespace(users=1, shape_keys=None, library=None)
    obj = types.SimpleNamespace(type="MESH", data=mesh, library=None)
    context = types.SimpleNamespace(active_object=obj, mode="EDIT_MESH",
                                    objects_in_mode_unique_data=[obj])
    bm = FakeBMesh(verts)
    updates = []
    def update(_mesh, **kwargs):
        updates.append(kwargs)
        if updater is not None:
            updater()
    module = types.SimpleNamespace(from_edit_mesh=lambda _: bm, update_edit_mesh=update)
    return context, bm, module, updates


class EditTransformTests(unittest.TestCase):
    def perform(self, context, module, offset):
        with patch.dict(sys.modules, {"bmesh": module}):
            return translate_selected_vertices(context, offset)

    def test_selected_only_moves_local_coordinates(self):
        context, bm, module, updates = setup()
        result = self.perform(context, module, (0, -0.25, 0.1))
        self.assertIsInstance(result, VertexTranslationResult)
        self.assertEqual(result.moved_vertices, 1)
        self.assertEqual(bm.verts[0].co, (1, 1.75, 3.1))
        self.assertEqual(bm.verts[1].co, (0, 1, 0))
        self.assertEqual(len(updates), 1)
        self.assertEqual(context.mode, "EDIT_MESH")

    def test_valid_negative_translation(self):
        context, bm, module, _ = setup()
        self.perform(context, module, (-1.0, 0.0, -0.5))
        self.assertEqual(bm.verts[0].co, (0, 2, 2.5))

    def test_two_selected_vertices_move(self):
        verts = [FakeVertex((0,0,0)), FakeVertex((1,2,3))]
        context, bm, module, _ = setup(verts)
        result = self.perform(context, module, (1, 0, 0))
        self.assertEqual(result.moved_vertices, 2)
        self.assertEqual([v.co for v in bm.verts], [(1,0,0), (2,2,3)])

    def test_invalid_offsets_rejected_before_mutation(self):
        for offset in ((), (1,), (0, 0, 0), (math.nan, 0, 0),
                       (math.inf, 0, 0), (11, 0, 0), ('invalid', 0, 0),
                       {0: 1}, None):
            with self.subTest(offset=offset):
                context, bm, module, updates = setup()
                with self.assertRaises(BlenderContextError):
                    self.perform(context, module, offset)
                self.assertEqual(bm.verts[0].co, (1, 2, 3))
                self.assertEqual(updates, [])

    def test_object_mode_rejected(self):
        context, bm, module, updates = setup()
        context.mode = 'OBJECT'
        with self.assertRaises(BlenderContextError):
            self.perform(context, module, (0, 0, 0.1))
        self.assertFalse(updates)

    def test_multi_edit_mode_rejected(self):
        context, bm, module, updates = setup()
        context.objects_in_mode_unique_data.append(types.SimpleNamespace(type='MESH'))
        with self.assertRaisesRegex(BlenderContextError, "Exactly one"):
            self.perform(context, module, (0, 0, 0.1))
        self.assertFalse(updates)

    def test_missing_mode_collection_rejected(self):
        context, bm, module, _ = setup()
        context.objects_in_mode_unique_data = None
        with self.assertRaises(BlenderContextError):
            self.perform(context, module, (0, 0, 0.1))

    def test_shared_mesh_rejected(self):
        context, bm, module, _ = setup()
        context.active_object.data.users = 2
        with self.assertRaisesRegex(BlenderContextError, "Shared"):
            self.perform(context, module, (0, 0, 0.1))

    def test_shape_keys_rejected(self):
        context, bm, module, _ = setup()
        context.active_object.data.shape_keys = object()
        with self.assertRaisesRegex(BlenderContextError, "shape keys"):
            self.perform(context, module, (0, 0, 0.1))

    def test_linked_data_rejected(self):
        for linked_location in ('library', 'mesh_library'):
            with self.subTest(linked_location=linked_location):
                context, bm, module, _ = setup()
                if linked_location == 'library':
                    context.active_object.library = object()
                else:
                    context.active_object.data.library = object()
                with self.assertRaises(BlenderContextError):
                    self.perform(context, module, (0, 0, 0.1))

    def test_no_selected_vertices_rejected(self):
        context, bm, module, _ = setup([FakeVertex((0,0,0), selected=False)])
        with self.assertRaisesRegex(BlenderContextError, "Select"):
            self.perform(context, module, (0, 0, 0.1))

    def test_invalid_existing_coordinate_is_rejected_before_writes(self):
        verts = [FakeVertex((1,2,3)), FakeVertex((math.inf, 0, 0))]
        context, bm, module, _ = setup(verts)
        with self.assertRaisesRegex(BlenderContextError, "invalid coordinates"):
            self.perform(context, module, (0,0,0.1))
        self.assertEqual(bm.verts[0].co, (1,2,3))

    def test_out_of_range_result_is_rejected_without_writes(self):
        verts = [FakeVertex((0,0,0)), FakeVertex((MAX_ABS_COORD, 0, 0))]
        context, bm, module, _ = setup(verts)
        with self.assertRaisesRegex(BlenderContextError, "invalid coordinates"):
            self.perform(context, module, (1,0,0))
        self.assertEqual(bm.verts[0].co, (0,0,0))

    def test_write_exception_rolls_back_prior_vertices(self):
        verts = [FakeVertex((1,2,3)), FakeVertex((4,5,6), fail_once=True)]
        context, bm, module, updates = setup(verts)
        with self.assertRaisesRegex(BlenderContextError, "restored"):
            self.perform(context, module, (0,0,0.1))
        self.assertEqual([v.co for v in bm.verts], [(1,2,3), (4,5,6)])
        self.assertEqual(len(updates), 1)

    def test_update_failure_attempts_rollback_and_second_update(self):
        state = {'count': 0}
        def updater():
            state['count'] += 1
            if state['count'] == 1:
                raise RuntimeError("injected update failure")
        context, bm, module, updates = setup(updater=updater)
        with self.assertRaisesRegex(BlenderContextError, "restored"):
            self.perform(context, module, (0,0,0.1))
        self.assertEqual(bm.verts[0].co, (1,2,3))
        self.assertEqual(state['count'], 2)

    def test_rollback_incomplete_reported_explicitly(self):
        verts = [FakeVertex((0,0,0))]
        def updater():
            raise RuntimeError("always fails")
        context, bm, module, _ = setup(verts, updater=updater)
        with self.assertRaisesRegex(BlenderContextError, "incomplete"):
            self.perform(context, module, (0,0,0.1))
        self.assertEqual(bm.verts[0].co, (0,0,0))


if __name__ == '__main__':
    unittest.main()
