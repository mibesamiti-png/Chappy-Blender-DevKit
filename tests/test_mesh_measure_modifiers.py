"""Unit tests for safe, immutable CBDK geometry and modifier helpers."""
import math
import sys
import types
import unittest
from unittest.mock import patch

from parts.blender.context import BlenderContextError
from parts.blender.measure import mesh_world_bounds
from parts.blender.modifiers import modifier_snapshot


class Matrix:
    def __init__(self, scale=(1, 1, 1), translate=(0, 0, 0)):
        self.scale = scale
        self.translate = translate

    def __matmul__(self, vec):
        return tuple(self.translate[i] + self.scale[i] * vec[i] for i in range(3))


class FakeModifier:
    def __init__(self, name, kind, viewport=True, render=True):
        self.name = name
        self.type = kind
        self.show_viewport = viewport
        self.show_render = render


def make_context():
    obj = types.SimpleNamespace(
        type="MESH", data=types.SimpleNamespace(vertices=[1, 2, 3]),
        matrix_world=Matrix(scale=(2, 3, 4), translate=(5, -3, 2)),
        bound_box=[
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0),
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0),
        ],
        modifiers=[FakeModifier("Subdiv", "SUBSURF", False, True)],
    )
    return types.SimpleNamespace(active_object=obj, mode="OBJECT")


class MeshAndModifierTests(unittest.TestCase):
    def test_world_bounds_with_nonuniform_scale_and_translation(self):
        context = make_context()
        with patch.dict(sys.modules, {"mathutils": types.SimpleNamespace(Vector=tuple)}):
            result = mesh_world_bounds(context)
        self.assertEqual(result.minimum, (5, -3, 2))
        self.assertEqual(result.maximum, (7, 0, 2))
        self.assertEqual(result.dimensions, (2, 3, 0))
        self.assertEqual(result.vertex_count, 3)

    def test_bounds_are_immutable(self):
        context = make_context()
        with patch.dict(sys.modules, {"mathutils": types.SimpleNamespace(Vector=tuple)}):
            result = mesh_world_bounds(context)
        with self.assertRaises((AttributeError, TypeError)):
            result.minimum = (0, 0, 0)

    def test_edit_mode_rejects_both_helpers(self):
        context = make_context()
        context.mode = "EDIT_MESH"
        for helper in (mesh_world_bounds, modifier_snapshot):
            with self.subTest(helper=helper.__name__):
                with self.assertRaises(BlenderContextError):
                    helper(context)

    def test_missing_active_mesh_rejected(self):
        context = make_context()
        context.active_object = None
        for helper in (mesh_world_bounds, modifier_snapshot):
            with self.assertRaises(BlenderContextError):
                helper(context)

    def test_bounds_empty_mesh_rejected(self):
        context = make_context()
        context.active_object.data.vertices = []
        with self.assertRaisesRegex(BlenderContextError, "vertices"):
            mesh_world_bounds(context)

    def test_invalid_bound_box_rejected(self):
        context = make_context()
        context.active_object.bound_box = [(0, 0, 0)]
        with self.assertRaisesRegex(BlenderContextError, "bounding box"):
            mesh_world_bounds(context)

    def test_non_finite_coordinates_rejected(self):
        context = make_context()
        context.active_object.matrix_world = Matrix(scale=(math.inf, 2, 3))
        with patch.dict(sys.modules, {"mathutils": types.SimpleNamespace(Vector=tuple)}):
            with self.assertRaisesRegex(BlenderContextError, "non-finite"):
                mesh_world_bounds(context)

    def test_snapshot_is_detached_and_immutable(self):
        context = make_context()
        before = context.active_object.modifiers[0]
        result = modifier_snapshot(context)
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0].name, result[0].type, result[0].viewport, result[0].render),
                         ("Subdiv", "SUBSURF", False, True))
        before.name = "Later"
        before.show_viewport = True
        self.assertEqual(result[0].name, "Subdiv")
        self.assertFalse(result[0].viewport)
        with self.assertRaises((AttributeError, TypeError)):
            result[0].name = "Different"

    def test_empty_modifier_list_supported(self):
        context = make_context()
        context.active_object.modifiers = []
        self.assertEqual(modifier_snapshot(context), ())

    def test_modifier_order_preserved(self):
        context = make_context()
        context.active_object.modifiers = [
            FakeModifier("A", "MIRROR"), FakeModifier("B", "SUBSURF", False, False),
        ]
        result = modifier_snapshot(context)
        self.assertEqual([x.name for x in result], ["A", "B"])
        self.assertEqual([x.type for x in result], ["MIRROR", "SUBSURF"])


if __name__ == "__main__":
    unittest.main()
