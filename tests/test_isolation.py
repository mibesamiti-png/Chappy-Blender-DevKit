import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cbdk.isolation import extract_candidate, inspect_candidate
from cbdk.__main__ import main
from cbdk.scanner import scan


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def src(self, name, code):
        p = self.root / name
        p.write_text(code, encoding='utf-8')
        catalog = scan([p])
        return p, catalog, catalog['symbols'][0]['id']

    def test_pure_function_extraction_and_manifest(self):
        p, cat, candidate = self.src('pure.py', 'def smooth(t):\n    t = max(0.0, min(float(t), 1.0))\n    return t * t * (3 - 2 * t)\n')
        out = self.root / 'result' / 'smooth.py'
        before = hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertTrue(inspect_candidate(cat, candidate, p)['eligible_for_review_extraction'])
        report = extract_candidate(cat, candidate, p, out)
        self.assertTrue(out.is_file())
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), before)
        self.assertEqual(json.loads(out.with_suffix('.json').read_text())['candidate_id'], candidate)
        self.assertFalse(report['approved'])
        with self.assertRaises(FileExistsError):
            extract_candidate(cat, candidate, p, out)

    def test_cli_isolate_inspect_and_extract(self):
        p, cat, cid = self.src('cli.py', 'def scale(x):\n    return x * 3\n')
        catalog_file = self.root / 'catalog.json'
        catalog_file.write_text(json.dumps(cat), encoding='utf-8')
        out = self.root / 'output.py'
        self.assertEqual(main(['isolate', '--catalog', str(catalog_file), '--candidate', cid, '--source', str(p)]), 0)
        self.assertEqual(main(['isolate', '--catalog', str(catalog_file), '--candidate', cid, '--source', str(p), '--output', str(out)]), 0)
        self.assertTrue(out.exists())

    def test_math_dependency_allowlisted(self):
        p, cat, cid = self.src('math_fn.py', 'import math\ndef radial(x, y):\n    return math.hypot(x, y)\n')
        out = self.root / 'radial.py'
        result = extract_candidate(cat, cid, p, out)
        self.assertTrue(result['uses_math'])
        self.assertIn('import math', out.read_text())

    def test_reject_global_and_import_execution(self):
        p, cat, cid = self.src('bad.py', 'value = 11\ndef f(x):\n    return x + value\n')
        report = inspect_candidate(cat, cid, p)
        self.assertFalse(report['eligible_for_review_extraction'])
        self.assertIn('value', ' '.join(report['blockers']))
        with self.assertRaises(ValueError):
            extract_candidate(cat, cid, p, self.root / 'nope.py')

    def test_reject_side_effect_and_dynamic_call(self):
        for name, code in [('dynamic', 'def f(x):\n    return open(x).read()\n'),
                           ('mutation', 'def f(obj):\n    obj.value = 3\n    return obj\n'),
                           ('decorator', '@danger\ndef f(x):\n    return x\n')]:
            with self.subTest(name=name):
                p, cat, cid = self.src(name + '.py', code)
                self.assertFalse(inspect_candidate(cat, cid, p)['eligible_for_review_extraction'])

    def test_shadowed_math_rejected(self):
        p, cat, cid = self.src('shadow.py', 'def f(math):\n    return math.sin(2)\n')
        self.assertFalse(inspect_candidate(cat, cid, p)['eligible_for_review_extraction'])

    def test_tampered_source_blocked(self):
        p, cat, cid = self.src('changed.py', 'def f(x):\n    return x\n')
        p.write_text('def f(x):\n    return x * 999\n')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            extract_candidate(cat, cid, p, self.root / 'out.py')

    def test_methods_and_nonliteral_defaults_blocked(self):
        p, cat, cid = self.src('method.py', 'class Thing:\n    def method(self):\n        return 1\n')
        method_id = next(s['id'] for s in cat['symbols'] if s['kind'] == 'method')
        with self.assertRaisesRegex(ValueError, 'Only top-level'):
            inspect_candidate(cat, method_id, p)
        p, cat, cid = self.src('default.py', 'def f(x=__import__("os")):\n    return x\n')
        self.assertFalse(inspect_candidate(cat, cid, p)['eligible_for_review_extraction'])


if __name__ == '__main__':
    unittest.main()
