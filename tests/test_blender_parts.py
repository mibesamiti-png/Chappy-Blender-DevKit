import sys
import types
import unittest
from unittest.mock import patch

from parts.blender import (BlenderContextError, count_edit_selection,
                           require_active_mesh, selected_mesh_objects)
from cbdk.blender_test import run_smoke


class Obj:
    type = 'MESH'
    data = object()


class BlenderHelperTests(unittest.TestCase):
    def test_active_mesh_and_mode(self):
        obj = Obj()
        context = types.SimpleNamespace(active_object=obj, mode='OBJECT')
        self.assertIs(require_active_mesh(context, mode='OBJECT'), obj)
        with self.assertRaises(BlenderContextError):
            require_active_mesh(context, mode='EDIT_MESH')
        with self.assertRaises(BlenderContextError):
            require_active_mesh(None)
        with self.assertRaises(BlenderContextError):
            require_active_mesh(types.SimpleNamespace(active_object=None))

    def test_selection_snapshot(self):
        mesh = Obj()
        light = types.SimpleNamespace(type='LIGHT', data=object())
        context = types.SimpleNamespace(selected_objects=[light, mesh])
        self.assertEqual(selected_mesh_objects(context), (mesh,))
        with self.assertRaises(BlenderContextError):
            selected_mesh_objects(types.SimpleNamespace())

    def test_count_readonly_in_edit_mode(self):
        obj = Obj()
        bm = types.SimpleNamespace(
            verts=[types.SimpleNamespace(select=True), types.SimpleNamespace(select=False)],
            edges=[types.SimpleNamespace(select=True)],
            faces=[types.SimpleNamespace(select=False)],
        )
        fake_bmesh = types.SimpleNamespace(from_edit_mesh=lambda mesh: bm)
        context = types.SimpleNamespace(active_object=obj, mode='EDIT_MESH',
                                        objects_in_mode_unique_data=[obj])
        with patch.dict(sys.modules, {'bmesh': fake_bmesh}):
            result = count_edit_selection(context)
        self.assertEqual((result.vertices, result.edges, result.faces), (1, 1, 0))
        with self.assertRaises((AttributeError, TypeError)):
            result.vertices = 2

    def test_multi_edit_and_missing_context_blocked(self):
        obj = Obj()
        context = types.SimpleNamespace(active_object=obj, mode='EDIT_MESH',
                                        objects_in_mode_unique_data=[obj, Obj()])
        with self.assertRaises(BlenderContextError):
            count_edit_selection(context)
        context.objects_in_mode_unique_data = None
        with self.assertRaises(BlenderContextError):
            count_edit_selection(context)

    @patch('cbdk.blender_test.subprocess.run')
    def test_only_allow_trusted_smoke_suite(self, runner):
        runner.return_value = types.SimpleNamespace(returncode=0,
            stdout='CBDK_BLENDER_SMOKE_PASS {"suite":"parts"}', stderr='')
        result = run_smoke('blender', suite='parts')
        self.assertTrue(result['verified'])
        self.assertTrue(runner.call_args.args[0][-1].endswith('blender_parts_smoke.py'))
        with self.assertRaises(ValueError):
            run_smoke('blender', suite='../../danger.py')


if __name__ == '__main__':
    unittest.main()
