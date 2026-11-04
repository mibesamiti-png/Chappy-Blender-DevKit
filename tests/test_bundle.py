"""Synthetic-only tests for v0.4 bundle extraction. No user addon is run."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cbdk.__main__ import main
from cbdk.bundle import inspect_bundle, extract_bundle
from cbdk.scanner import scan


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, text):
        path = self.dir / 'example.py'
        path.write_text(text, encoding='utf-8')
        catalog = scan([path])
        ids = {s['qualname']: s['id'] for s in catalog['symbols']}
        return path, catalog, ids

    def test_dependency_order_constants_and_math(self):
        p,c,ids=self.source('''import math
EPS = 0.001
def root(x,y):
    return radial(x,y) + bias(x)
def radial(x,y):
    return math.hypot(x,y)
def bias(x):
    return clamp(x) + EPS
def clamp(x):
    return max(0.0,min(x,1.0))
''')
        result=inspect_bundle(c,ids['root'],p)
        self.assertTrue(result['eligible_for_review_extraction'],result['blockers'])
        self.assertEqual([x['name'] for x in result['functions']], ['clamp','bias','radial','root'])
        self.assertEqual(result['constants'],[{'name':'EPS','value':.001}])
        self.assertTrue(result['uses_math'])
        before=hashlib.sha256(p.read_bytes()).hexdigest()
        out=self.dir/'out'/'bundle.py'
        extract_bundle(c,ids['root'],p,out)
        self.assertEqual(before,hashlib.sha256(p.read_bytes()).hexdigest())
        self.assertTrue(out.with_suffix('.json').exists())
        # Execute only our synthetic, known-safe test fixture.
        ns={}
        exec(compile(out.read_text(),'<synthetic-test-fixture>','exec'),ns)
        self.assertAlmostEqual(ns['root'](3,4),6.001)

    def test_cyclic_dependency_rejected(self):
        p,c,ids=self.source('''def a(x):
    return b(x)
def b(x):
    return a(x)
''')
        result=inspect_bundle(c,ids['a'],p)
        self.assertFalse(result['eligible_for_review_extraction'])
        self.assertIn('Cyclic dependency',' '.join(result['blockers']))

    def test_unknown_bpy_and_dynamic_calls_are_rejected(self):
        sources=[
            'def root():\n    return bpy.context.object\n',
            'def root(cb):\n    return cb()\n',
            'def root(obj):\n    return obj.name\n']
        for src in sources:
            with self.subTest(src=src):
                p,c,ids=self.source(src)
                self.assertFalse(inspect_bundle(c,ids['root'],p)['eligible_for_review_extraction'])

    def test_builtin_shadow_and_math_override_rejected(self):
        sources=[
            'max=lambda x:0\ndef root(x):\n    return max(x,1)\n',
            'import math\nmath=2\ndef root(x):\n    return math.sin(x)\n',
            'def root(x):\n    return calc(x)\ndef calc(x):\n    return max(x,1)\nmax=3\n']
        for src in sources:
            with self.subTest(src=src):
                p,c,ids=self.source(src)
                self.assertFalse(inspect_bundle(c,ids['root'],p)['eligible_for_review_extraction'])

    def test_duplicate_top_level_function_rejected(self):
        p,c,ids=self.source('def root(x):\n    return x\ndef root(x):\n    return x+1\n')
        with self.assertRaisesRegex(ValueError,'ambiguous|Duplicate'):
            inspect_bundle(c,ids['root'],p)

    def test_dynamic_default_or_decorator_blocks_entire_bundle(self):
        sources=[
            'def root(x):\n    return helper(x)\ndef helper(x=lookup()):\n    return x\n',
            'def root(x):\n    return helper(x)\n@decorate\ndef helper(x):\n    return x\n']
        for src in sources:
            with self.subTest(src=src):
                p,c,ids=self.source(src)
                self.assertFalse(inspect_bundle(c,ids['root'],p)['eligible_for_review_extraction'])

    def test_source_tamper_and_collision_refused(self):
        p,c,ids=self.source('def root(x):\n    return helper(x)\ndef helper(x):\n    return x+1\n')
        out=self.dir/'out.py'
        self.assertTrue(inspect_bundle(c,ids['root'],p)['eligible_for_review_extraction'])
        extract_bundle(c,ids['root'],p,out)
        with self.assertRaises(FileExistsError):
            extract_bundle(c,ids['root'],p,out)
        p.write_text(p.read_text()+'\n# source changed\n')
        with self.assertRaisesRegex(ValueError,'mismatch'):
            inspect_bundle(c,ids['root'],p)

    def test_reject_nonliteral_global(self):
        p,c,ids=self.source('EPS=1+2\ndef root(x):\n    return x*EPS\n')
        self.assertFalse(inspect_bundle(c,ids['root'],p)['eligible_for_review_extraction'])

    def test_annotated_constant_cannot_copy_runtime_annotation(self):
        p,c,ids=self.source('EPS: evil() = 1\ndef root(x):\n    return x+EPS\n')
        self.assertFalse(inspect_bundle(c,ids['root'],p)['eligible_for_review_extraction'])

    def test_limits_and_main_path(self):
        p,c,ids=self.source('def root(x):\n    return helper(x)\ndef helper(x):\n    return x+1\n')
        self.assertFalse(inspect_bundle(c,ids['root'],p,max_functions=1)['eligible_for_review_extraction'])
        with self.assertRaises(ValueError):
            inspect_bundle(c,ids['root'],p,max_functions=0)
        cat=self.dir/'catalog.json'
        cat.write_text(json.dumps(c))
        out=self.dir/'bundle.py'
        args=['bundle','--catalog',str(cat),'--candidate',ids['root'],'--source',str(p)]
        self.assertEqual(main(args),0)
        self.assertEqual(main(args+['--output',str(out)]),0)
        self.assertTrue(out.is_file())

    def test_bundle_is_not_marked_approved(self):
        p,c,ids=self.source('def a(x):\n    return b(x)\ndef b(x):\n    return x+2\n')
        result=inspect_bundle(c,ids['a'],p)
        self.assertEqual(result['verification'],'static_only')
        self.assertFalse(result['approved'])
        self.assertEqual(len(result['dependencies']),1)


if __name__ == '__main__':
    unittest.main()
