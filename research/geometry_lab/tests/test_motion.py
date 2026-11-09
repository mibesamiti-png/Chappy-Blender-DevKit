import unittest
import numpy as np
from cbdk_geometry import Mesh, detect, guarded_step
from cbdk_geometry.fixtures import pair


class MotionTests(unittest.TestCase):
    def test_full_safe_step(self):
        mesh = pair('separate')
        d = np.zeros_like(mesh.vertices)
        d[3:,2] = 1
        r = guarded_step(mesh,d)
        self.assertEqual((r['status'],r['alpha']), ('accepted',1))

    def test_exhaustion_keeps_original(self):
        mesh = pair('separate')
        d = np.zeros_like(mesh.vertices)
        d[3:,2] = -2
        r = guarded_step(mesh,d,max_halvings=0)
        self.assertEqual(r['status'],'blocked')
        self.assertIs(r['mesh'], mesh)

    def test_false_rejection_is_explicit(self):
        # Disjoint coplanar triangles but overlapping bounding boxes.
        mesh = Mesh([[0,0,0],[2,0,0],[0,2,0],[2,2,0],[2,.5,0],[.5,2,0]], [[0,1,2],[3,4,5]])
        self.assertEqual(detect(mesh)['pairs'], [])
        r = guarded_step(mesh,np.zeros_like(mesh.vertices))
        self.assertEqual(r['status'],'blocked')

    def test_nonfinite_motion_rejected(self):
        mesh=pair('separate')
        with self.assertRaises(ValueError):
            guarded_step(mesh,np.full_like(mesh.vertices,np.nan))
