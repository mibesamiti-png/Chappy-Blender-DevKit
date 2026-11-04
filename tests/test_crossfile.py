"""v0.5 cross-file extraction tests: no source module is ever imported."""
import hashlib
import json
import tempfile
import runpy
import unittest
from pathlib import Path

from cbdk.__main__ import main
from cbdk.crossfile import extract_crossfile, inspect_crossfile
from cbdk.scanner import scan


class CrossfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'workspace'
        self.root.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text(content, encoding='utf-8')
        return path

    def candidate(self, cat, filename, func):
        return next(s['id'] for s in cat['symbols']
                    if s['source_name'] == filename and s['qualname'] == func and s['kind'] == 'function')

    def analyze(self, filename='main.py', func='run'):
        cat = scan([self.root])
        return cat, self.candidate(cat, filename, func), self.root / filename

    def test_crossfile_two_level_dependency_and_manifest(self):
        self.write('main.py', 'from .helpers import helper\ndef run(v):\n    return helper(v) + 1\n')
        self.write('helpers.py', 'from .constants import f\ndef helper(v):\n    return f(v) * 2\n')
        self.write('constants.py', 'def f(v):\n    return max(0, v)\n')
        cat, cid, src = self.analyze()
        before = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in self.root.glob('*.py')}
        report = inspect_crossfile(cat, cid, src, sources_root=self.root)
        self.assertTrue(report['eligible_for_review_extraction'], report['blockers'])
        self.assertEqual([x['name'] for x in report['functions']], ['f', 'helper', 'run'])
        self.assertEqual(len(report['files']), 3)
        out = self.root / 'output' / 'result.py'
        extracted = extract_crossfile(cat, cid, src, out, sources_root=self.root)
        self.assertFalse(extracted['approved'])
        self.assertNotIn('from .', out.read_text())
        # Execute only this synthetic test fixture, never collected user sources.
        self.assertEqual(runpy.run_path(str(out))['run'](3), 7)
        self.assertEqual(before, {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in self.root.glob('*.py')})
        self.assertEqual(len(json.loads(out.with_suffix('.json').read_text())['files']), 3)
        with self.assertRaises(FileExistsError):
            extract_crossfile(cat, cid, src, out, sources_root=self.root)

    def test_same_file_math_constant_and_imported_helper(self):
        self.write('main.py', 'from .helper import square\nimport math\nEPS = 0.5\ndef run(x):\n    return math.sin(square(x)) + EPS\n')
        self.write('helper.py', 'def square(v):\n    return v * v\n')
        cat, cid, src = self.analyze()
        report = inspect_crossfile(cat, cid, src, sources_root=self.root)
        self.assertTrue(report['eligible_for_review_extraction'], report['blockers'])
        self.assertTrue(report['uses_math'])
        self.assertEqual([v['name'] for v in report['constants']], ['EPS'])
        out = self.root / 'output.py'
        extract_crossfile(cat, cid, src, out, sources_root=self.root)
        self.assertIn('import math', out.read_text())
        self.assertIn('EPS = 0.5', out.read_text())

    def test_missing_or_changed_import_refuses(self):
        self.write('main.py', 'from .helper import h\ndef run(x):\n    return h(x)\n')
        helper = self.write('helper.py', 'def h(x):\n    return x+1\n')
        cat, cid, src = self.analyze()
        helper.write_text('def h(x):\n    return x+3\n')
        report = inspect_crossfile(cat, cid, src, sources_root=self.root)
        self.assertFalse(report['eligible_for_review_extraction'])
        self.assertIn('changed', ' '.join(report['blockers']))

    def test_cycle_refused(self):
        self.write('main.py', 'from .helper import h\ndef run(x):\n    return h(x)\n')
        self.write('helper.py', 'from .main import run\ndef h(x):\n    return run(x)\n')
        cat, cid, src = self.analyze()
        r = inspect_crossfile(cat, cid, src, sources_root=self.root)
        self.assertFalse(r['eligible_for_review_extraction'])
        self.assertIn('cycle', ' '.join(r['blockers']).lower())

    def test_collision_of_names_in_different_files(self):
        self.write('main.py', 'from .helper import h\ndef run(v):\n    return h(v) + same(v)\ndef same(v):\n    return v+1\n')
        self.write('helper.py', 'def h(v):\n    return same(v)\ndef same(v):\n    return v*2\n')
        cat, cid, src = self.analyze()
        r = inspect_crossfile(cat, cid, src, sources_root=self.root)
        self.assertFalse(r['eligible_for_review_extraction'])
        self.assertIn('collision', ' '.join(r['blockers']))

    def test_alias_and_external_import_rejected(self):
        self.write('main.py', 'from .helper import h as aliased\ndef run(x):\n    return aliased(x)\n')
        self.write('helper.py', 'def h(x):\n    return x\n')
        cat, cid, src = self.analyze()
        r = inspect_crossfile(cat, cid, src, sources_root=self.root)
        self.assertFalse(r['eligible_for_review_extraction'])
        self.assertIn('unresolved', ' '.join(r['blockers']))
        self.write('main.py', 'from remote_api import h\ndef run(x):\n    return h(x)\n')
        cat, cid, src = self.analyze()
        r = inspect_crossfile(cat, cid, src, sources_root=self.root)
        self.assertFalse(r['eligible_for_review_extraction'])

    def test_blender_api_not_extracted(self):
        self.write('main.py', 'import bpy\ndef run():\n    return bpy.context.object\n')
        cat, cid, src = self.analyze()
        r = inspect_crossfile(cat, cid, src, sources_root=self.root)
        self.assertFalse(r['eligible_for_review_extraction'])
        self.assertIn('bpy', ' '.join(r['blockers']))

    def test_output_cannot_overwrite_any_source(self):
        src = self.write('main.py', 'def run(x):\n    return x + 1\n')
        cat, cid, _ = self.analyze()
        with self.assertRaisesRegex(ValueError, 'Output'):
            extract_crossfile(cat, cid, src, src, sources_root=self.root)

    def test_root_source_not_in_root(self):
        src = self.write('main.py', 'def run(x):\n    return x\n')
        cat, cid, _ = self.analyze()
        with self.assertRaisesRegex(ValueError, 'root'):
            inspect_crossfile(cat, cid, src, sources_root=self.root / 'bad')

    def test_max_files_restriction(self):
        self.write('main.py', 'from .helper import h\ndef run(x):\n    return h(x)\n')
        self.write('helper.py', 'def h(x):\n    return x+1\n')
        cat, cid, src = self.analyze()
        r = inspect_crossfile(cat, cid, src, sources_root=self.root, max_files=1)
        self.assertFalse(r['eligible_for_review_extraction'])
        self.assertIn('limit', ' '.join(r['blockers']))

    def test_cli_review_and_output(self):
        self.write('main.py', 'from .helper import f\ndef run(x):\n    return f(x)\n')
        self.write('helper.py', 'def f(x):\n    return x+9\n')
        cat, cid, src = self.analyze()
        catalog_file = self.root / 'catalog.json'
        catalog_file.write_text(json.dumps(cat), encoding='utf-8')
        args = ['crossfile', '--catalog', str(catalog_file), '--candidate', cid,
                '--source', str(src), '--sources-root', str(self.root)]
        self.assertEqual(main(args), 0)
        output = self.root / 'out.py'
        self.assertEqual(main(args + ['--output', str(output)]), 0)
        self.assertTrue(output.exists())


if __name__ == '__main__':
    unittest.main()
