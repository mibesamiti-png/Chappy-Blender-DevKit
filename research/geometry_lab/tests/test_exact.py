import unittest
import numpy as np
from cbdk_geometry import detect
from cbdk_geometry.exact import classify_pair, detect_exact
from cbdk_geometry.fixtures import pair, soup
from cycles.r2.fixtures import analytic_cases


class ExactTests(unittest.TestCase):
    def test_analytic_and_permutations(self):
        for case in analytic_cases():
            m=case['mesh']
            with self.subTest(name=case['name'],scale=case['scale'],reverse=case['reverse']):
                for ids in (m.faces,m.faces[::-1]):
                    a,b=m.vertices[ids]
                    result=classify_pair(a,b,*ids)
                    self.assertEqual(result in ('intersection','duplicate'),case['expected'])
                    self.assertEqual(result,classify_pair(a,b,*ids,prefilter=False))

    def test_old_detector_counterexamples_are_preserved(self):
        cases=[c for c in analytic_cases() if c['scale']==1 and not c['reverse']]
        misses=[c for c in cases if bool(detect(c['mesh'])['pairs'])!=c['expected']]
        self.assertTrue(any(c['name'].startswith('shared_vertex_sliver') for c in misses))
        self.assertTrue(any(c['name'].startswith('positive_gap') for c in misses))

    def test_budget_fails_closed_even_with_sparse_boxes(self):
        result=detect_exact(soup(10),pair_budget=2)
        self.assertEqual(result['status'],'budget_exceeded')
        self.assertIsNone(result['pairs'])
        self.assertEqual(result['scanned'],2)

    def test_mesh_api_and_input_preservation(self):
        m=pair('cross');before=m.vertices.copy()
        self.assertEqual(detect_exact(m)['pairs'],[(0,1)])
        np.testing.assert_array_equal(m.vertices,before)

    def test_invalid_input_and_connectivity(self):
        a=pair('cross').vertices[:3]
        for b in ([[0,0,0]]*3, [[0,0,0],[1,0,0],[0,np.inf,0]]):
            with self.assertRaises(ValueError):classify_pair(a,b)
        with self.assertRaises(ValueError):classify_pair(a,a+[0,0,1],[0,1,2],[0,3,4])
        for kwargs in ({'pair_budget':True},{'pair_budget':0},{'seconds':float('nan')},{'seconds':0}):
            with self.assertRaises(ValueError):detect_exact(pair(),**kwargs)
