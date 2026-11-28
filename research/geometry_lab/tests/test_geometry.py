import unittest
import numpy as np
from cbdk_geometry import Mesh, detect, guarded_step, quality
from cbdk_geometry.fixtures import pair, soup, sphere


class GeometryTests(unittest.TestCase):
    def test_analytic_labels_and_scale(self):
        for scale in (1e-6, 1, 1e6):
            for kind, expected in [('cross', True), ('separate', False),
                    ('coplanar', True), ('coplanar_separate', False),
                    ('touch', True), ('near_miss', False)]:
                for method in ('brute', 'sweep'):
                    with self.subTest(scale=scale, kind=kind, method=method):
                        self.assertEqual(bool(detect(pair(kind, scale), method)['pairs']), expected)

    def test_adjacency_and_fold(self):
        for third, expected in [([1, 1, 0], False), ([.2, .2, 0], True)]:
            mesh = Mesh([[0, 0, 0], [1, 0, 0], [0, 1, 0], third],
                        [[0, 1, 2], [1, 3, 2]])
            self.assertEqual(bool(detect(mesh)['pairs']), expected)

    def test_shared_vertex_crossing(self):
        mesh = Mesh([[0, 0, 0], [2, 0, 0], [0, 2, 0], [1, 1, -1], [1, 1, 1]],
                    [[0, 1, 2], [0, 3, 4]])
        self.assertTrue(detect(mesh)['pairs'])

    def test_duplicate_face(self):
        self.assertTrue(detect(Mesh([[0,0,0],[1,0,0],[0,1,0]], [[0,1,2],[2,1,0]]))['pairs'])

    def test_sweep_parity(self):
        for seed in range(5):
            mesh = soup(40, seed)
            self.assertEqual(detect(mesh, 'brute')['pairs'], detect(mesh)['pairs'])

    def test_budget_not_clean(self):
        result = detect(soup(10), 'brute', pair_budget=1)
        self.assertEqual(result['status'], 'budget_exceeded')
        self.assertIsNone(result['pairs'])

    def test_reject_invalid(self):
        for vertices, faces in [([[0,0,0],[1,0,0],[2,0,0]], [[0,1,2]]),
                ([[0,0,0],[1,0,0],[0,float('nan'),0]], [[0,1,2]]),
                ([[0,0,0],[1,0,0],[0,1,0]], [[0.,1.,2.]]),
                ([[0,0,0],[1,0,0],[0,1,0]], [[0,1,5]])]:
            with self.assertRaises(ValueError):
                Mesh(vertices, faces)

    def test_tunneling_prevented(self):
        mesh = pair('separate')
        d = np.zeros_like(mesh.vertices)
        d[3:, 2] = -2
        # Both endpoints clean: endpoint-only line search would tunnel.
        self.assertFalse(detect(Mesh(mesh.vertices+d, mesh.faces))['pairs'])
        result = guarded_step(mesh, d)
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(result['alpha'], .25)
        self.assertFalse(detect(result['mesh'])['pairs'])
        self.assertTrue(np.array_equal(mesh.vertices[3:, 2], [1,1,1]))

    def test_motion_rejections(self):
        mesh = pair('cross')
        self.assertEqual(guarded_step(mesh, np.zeros_like(mesh.vertices))['status'], 'initial_collision')
        mesh = sphere(segments=8, rings=4)
        with self.assertRaises(ValueError):
            guarded_step(mesh, np.zeros_like(mesh.vertices))

    def test_closed_sphere_quality(self):
        q = quality(sphere())
        self.assertEqual((q['boundary_edges'], q['nonmanifold_edges'], q['components']), (0,0,1))
        self.assertLess(abs(q['volume']-4*np.pi/3)/(4*np.pi/3), .04)

if __name__ == '__main__':
    unittest.main()
