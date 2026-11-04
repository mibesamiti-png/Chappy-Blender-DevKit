import json
import tempfile
import unittest
from pathlib import Path

from cbdk.__main__ import main
from cbdk.blender_audit import audit_blender_dependencies
from cbdk.scanner import scan


class BlenderAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def src(self, name, code):
        path = self.root / name
        path.write_text(code, encoding='utf-8')
        return path

    def test_bpy_ops_alias_context_marked(self):
        p = self.src('ops.py', 'import bpy as blender\ndef operate():\n    blender.ops.object.mode_set(mode="EDIT")\n    return blender.context.object\n')
        report = audit_blender_dependencies(scan([p]))
        self.assertEqual(report['blender_related_symbols'], 1)
        item = report['symbols'][0]
        self.assertIn('bpy.ops.object.mode_set', item['operator_calls'])
        self.assertIn('bpy.context.object', item['api_paths'])
        self.assertTrue(item['context_sensitive'])
        self.assertTrue(item['requires_blender_runtime_validation'])

    def test_bmesh_mathutils_data_api(self):
        p = self.src('mesh.py', 'import bmesh\nfrom mathutils import Vector\ndef action(mesh):\n    bm = bmesh.from_edit_mesh(mesh)\n    return Vector((0, 0, 0))\n')
        report = audit_blender_dependencies(scan([p]))
        self.assertEqual(report['blender_related_symbols'], 1)
        item = report['symbols'][0]
        self.assertIn('bmesh.from_edit_mesh', item['bmesh_calls'])
        self.assertIn('mathutils.Vector', item['api_calls'])
        self.assertTrue(item['context_sensitive'])

    def test_import_from_bpy_ops(self):
        p = self.src('imp.py', 'from bpy import ops\ndef delete():\n    return ops.object.delete()\n')
        report = audit_blender_dependencies(scan([p]))
        self.assertIn('bpy.ops.object.delete', report['symbols'][0]['operator_calls'])

    def test_pure_function_not_counted(self):
        p = self.src('pure.py', 'def add(x):\n    return x + 1\n')
        report = audit_blender_dependencies(scan([p]))
        self.assertEqual(report['blender_related_symbols'], 0)

    def test_class_methods_not_double_counted(self):
        p = self.src('class.py', 'import bpy\nclass Helper:\n    def run(self):\n        return bpy.ops.object.delete()\n')
        report = audit_blender_dependencies(scan([p]))
        self.assertEqual(report['blender_related_symbols'], 1)
        self.assertEqual(report['symbols'][0]['function'], 'Helper.run')

    def test_source_tampering_detected(self):
        p = self.src('tamper.py', 'import bpy\ndef a():\n    return bpy.data.objects\n')
        cat = scan([p])
        p.write_text('def a():\n    return 1\n')
        with self.assertRaisesRegex(ValueError, 'changed'):
            audit_blender_dependencies(cat)

    def test_cli_writes_json(self):
        p = self.src('cli.py', 'import bpy\ndef draw():\n    return bpy.data.materials\n')
        cat = scan([p])
        catalog = self.root / 'catalog.json'
        output = self.root / 'report.json'
        catalog.write_text(json.dumps(cat), encoding='utf-8')
        self.assertEqual(main(['audit-blender', '--catalog', str(catalog), '--output', str(output)]), 0)
        self.assertEqual(json.loads(output.read_text())['blender_related_symbols'], 1)


if __name__ == '__main__':
    unittest.main()
