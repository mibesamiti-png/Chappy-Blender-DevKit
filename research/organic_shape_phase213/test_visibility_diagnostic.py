import unittest,math
from visibility_diagnostic import raster,rim_stats

class VisibilityTests(unittest.TestCase):
    def test_depth_order_not_face_order(self):
        # Coincident projected triangles at distinct depths; nearest is back-facing.
        p=[(-.4,0.,.1),(.4,0.,.1),(0.,0.,.5),(-.4,.3,.1),(.4,.3,.1),(0.,.3,.5)]
        t=[(0,2,1),(3,4,5)]
        a,_=raster(p,t,0.,width=80,height=120,scale=50)
        b,_=raster(p,t[::-1],0.,width=80,height=120,scale=50)
        self.assertEqual(a,b)
        self.assertGreater(a.count(2),0)
        self.assertEqual(a.count(1),0)
    def test_boundary_turn(self):
        p=[(0.,0.,.4),(1.,0.,.4),(1.,1.,.4),(0.,1.,.4)]
        r=rim_stats(p,[(0,1,2,3)])
        self.assertEqual(len(r),1)
        self.assertAlmostEqual(r[0]["max_3d_turn"],90.)
        self.assertEqual(r[0]["count"],4)
