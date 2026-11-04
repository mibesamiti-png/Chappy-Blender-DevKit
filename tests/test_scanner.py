import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cbdk.dedup import duplicates
from cbdk.report import write_json, write_report
from cbdk.scanner import scan
from cbdk.search import search


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def put(self, name, code):
        path = self.root / name
        path.write_text(code, encoding='utf-8')
        return path

    def test_cross_volume_path_does_not_abort_scan(self):
        path = self.put('cross_drive.py', 'def helper(x):\n    return x + 1\n')
        with patch('cbdk.scanner.os.path.relpath', side_effect=ValueError("path is on another drive")):
            result = scan([path])
        self.assertEqual(result['files'][0]['path'], str(path.resolve()))
        self.assertEqual(result['symbols'][0]['source'], str(path.resolve()))
        self.assertEqual(len(result['symbols']), 1)

    def test_ast_exact_duplicate_despite_docstring(self):
        self.put('a.py', 'def get_middle(x):\n    """A."""\n    return x + 1\n')
        self.put('b.py', 'def compute_middle(x):\n    """B."""\n    return x+1\n')
        catalog = scan([self.root])
        result = duplicates(catalog)
        self.assertEqual(len(result['exact_groups']), 1)
        self.assertEqual(len(catalog['symbols']), 2)

    def test_shape_same_not_identical(self):
        self.put('c.py', 'def one(foo):\n    return foo + 1\n')
        self.put('d.py', 'def two(bar):\n    return bar + 2\n')
        result = duplicates(scan([self.root]))
        self.assertEqual(len(result['exact_groups']), 0)
        self.assertEqual(len(result['shape_groups']), 1)

    def test_invalid_python_does_not_execute(self):
        self.put('broken.py', 'def broken(:\n')
        self.put('unsafe.py', 'raise RuntimeError("THIS MUST NOT EXECUTE")\ndef safe():\n    return 1\n')
        catalog = scan([self.root])
        self.assertEqual(len(catalog['symbols']), 1)
        self.assertEqual({x['status'] for x in catalog['files']}, {'parsed','parse_error'})

    def test_imports_and_class_methods(self):
        self.put('op.py', 'import bpy\nbl_info={"name":"Op","blender":(4,2,0)}\nclass Test:\n    def poll(self, context):\n        return context.active_object is not None\n')
        catalog = scan([self.root])
        self.assertEqual(len(catalog['symbols']), 2)
        self.assertEqual(catalog['files'][0]['bl_info']['blender'], [4, 2, 0])
        self.assertEqual(catalog['symbols'][1]['qualname'], 'Test.poll')

    def test_report_and_search(self):
        self.put('select.py', 'def get_selected_vertices(vertices):\n    return [v for v in vertices if v.select]\n')
        cat = scan([self.root])
        found = search(cat, '選択 頂点')
        self.assertTrue(found)
        out = self.root / 'out'
        write_json(out / 'catalog.json', cat)
        summary = write_report(out / 'report.md', cat, duplicates(cat))
        self.assertEqual(summary['files'], 1)
        self.assertTrue((out / 'report.md').exists())
        self.assertEqual(len(json.loads((out / 'catalog.json').read_text())['symbols']), 1)


if __name__ == '__main__':
    unittest.main()
