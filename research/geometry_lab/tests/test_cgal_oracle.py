"""Optional locally; mandatory in the isolated R2 CI job."""
import importlib.util
import unittest
import numpy as np
from cbdk_geometry.exact import classify_pair,detect_exact
from cbdk_geometry.fixtures import sphere


@unittest.skipUnless(importlib.util.find_spec('CGAL'), 'optional CGAL oracle not installed')
class OracleTests(unittest.TestCase):
    def test_independent_seeded_kernel_predicates(self):
        from cycles.r2.oracle import triangle_hit
        rng=np.random.default_rng(701)
        for _ in range(64):
            a,b=rng.normal(size=(2,3,3))
            self.assertEqual(classify_pair(a,b)!='disjoint',triangle_hit(a,b))

    def test_manifold_mesh_shared_simplex_semantics(self):
        from cycles.r2.oracle import mesh_hits
        mesh=sphere(segments=12,rings=6)
        result=detect_exact(mesh)
        self.assertEqual(result['status'],'measured')
        self.assertEqual(result['pairs'],mesh_hits(mesh))
        self.assertEqual(result['pairs'],[])
