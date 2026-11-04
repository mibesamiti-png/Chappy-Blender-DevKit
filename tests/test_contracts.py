import json
import tempfile
import unittest
from pathlib import Path

from cbdk.__main__ import main
from cbdk.contracts import make_blender_contracts


class BlenderContractTests(unittest.TestCase):
    def test_context_and_operator_contracts(self):
        audit = {'schema_version': 1, 'symbols': [
            {'candidate_id': 'CND-1', 'file': 'one.py', 'function': 'get_edit_bmesh',
             'kind': 'function', 'line': 3, 'api_paths': ['bmesh.from_edit_mesh'],
             'api_calls': ['bmesh.from_edit_mesh'], 'context_references': [], 'operator_calls': []},
            {'candidate_id': 'CND-2', 'file': 'two.py', 'function': 'transform',
             'kind': 'function', 'line': 4, 'api_paths': ['bpy.ops.object.mode_set'],
             'api_calls': ['bpy.ops.object.mode_set'], 'context_references': ['bpy.context.active_object'],
             'operator_calls': ['bpy.ops.object.mode_set']},
        ]}
        result = make_blender_contracts(audit)
        self.assertEqual(result['contracts_count'], 2)
        self.assertEqual(result['edit_mesh_candidates'], 1)
        self.assertEqual(result['operator_candidates'], 1)
        self.assertEqual(result['contracts'][0]['mode_hints_not_guarantees'], ['EDIT_MESH'])
        self.assertFalse(result['contracts'][0]['approved'])
        self.assertIn('operator_poll', result['contracts'][1]['suggested_tests'])
        self.assertEqual(result['contracts'][1]['mode_hints_not_guarantees'], [])

    def test_invalid_schema(self):
        with self.assertRaises(ValueError):
            make_blender_contracts({'schema_version': 20, 'symbols': []})

    def test_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            audit = Path(folder) / 'audit.json'
            output = Path(folder) / 'contracts.json'
            audit.write_text(json.dumps({'schema_version': 1, 'symbols': []}), encoding='utf-8')
            self.assertEqual(main(['contracts', '--audit', str(audit), '--output', str(output)]), 0)
            self.assertTrue(output.exists())
            self.assertEqual(json.loads(output.read_text())['contracts_count'], 0)


if __name__ == '__main__':
    unittest.main()
