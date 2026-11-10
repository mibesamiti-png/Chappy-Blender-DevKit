import unittest
import importlib.util
from cbdk_geometry import Mesh
from cbdk_geometry.exact import detect_exact
from cbdk_geometry.accelerated import detect_accelerated
from cbdk_geometry.fixtures import soup
from cycles.r2.fixtures import analytic_cases
from cycles.r3.fixtures import torus,sheet


class AcceleratedTests(unittest.TestCase):
    def test_analytic_90_and_ablation(self):
        for c in analytic_cases():
            for enabled in (False,True):
                r=detect_accelerated(c['mesh'],shortcuts=enabled)
                self.assertEqual(r['status'],'measured')
                self.assertEqual(bool(r['pairs']),c['expected'],c['name'])

    def test_new_shapes_reference_parity(self):
        for mesh in (torus(8,6),sheet(False,6),sheet(True,6),soup(30)):
            ref=detect_exact(mesh)
            self.assertEqual(ref['status'],'measured')
            for enabled in (False,True):
                self.assertEqual(detect_accelerated(mesh,shortcuts=enabled)['pairs'],ref['pairs'])

    def test_budget_and_invalid(self):
        m=torus(8,6)
        for kw in ({'pair_budget':2},{'seconds':1e-100}):
            r=detect_accelerated(m,**kw)
            self.assertEqual(r['status'],'budget_exceeded');self.assertIsNone(r['pairs'])
        for kw in ({'shortcuts':1},{'pair_budget':True},{'seconds':float('nan')}):
            with self.assertRaises(ValueError):detect_accelerated(m,**kw)

    def test_no_stale_cache_after_new_input(self):
        m=sheet(False,6);original=detect_accelerated(m)
        detect_accelerated(sheet(True,6))
        self.assertEqual(detect_accelerated(m),original)

    @unittest.skipUnless(importlib.util.find_spec('CGAL'),'optional oracle missing')
    def test_independent_shapes(self):
        from cycles.r2.oracle import mesh_hits
        for mesh in (torus(8,6),sheet(False,6),sheet(True,6)):
            self.assertEqual(detect_accelerated(mesh)['pairs'],mesh_hits(mesh))
