import math,unittest
from phase212_geneva import Geneva,IndexRequirement,audit,screen

class GenevaTests(unittest.TestCase):
    def test_four_slot_index_and_dwell(self):
        g=Geneva(4,10,.3,.05)
        self.assertAlmostEqual(g.advance,math.pi/2)
        self.assertAlmostEqual(g.dwell_fraction,.75)
        self.assertAlmostEqual(g.crank_radius,math.sqrt(50))
        self.assertEqual(g.sample(.1),(0.,0.,0.))
        self.assertAlmostEqual(g.sample(.5)[0],math.pi/4)
        self.assertAlmostEqual(g.sample(.9)[0],math.pi/2)
        self.assertAlmostEqual(g.sample(4)[0],math.tau)
        self.assertAlmostEqual(g.sample(-1)[0],-math.pi/2)
    def test_all_slot_counts_and_projection(self):
        for n in range(3,13):
            g=Geneva(n,20,.15,.05,phase_offset=.63)
            r=audit(g,IndexRequirement(math.tau/n,0))
            self.assertEqual(r["analytic"]["status"],"pass",r)
            self.assertFalse(r["physical_contact_certified"])
            self.assertFalse(r["locking_verified"])
    def test_derivatives_and_boundary_jump(self):
        g=Geneva(4,10,.3,.05)
        for u in (.4,.43,.5,.57,.6):
            h=1e-6;p,v,a=g.sample(u);lo=g.sample(u-h);hi=g.sample(u+h)
            self.assertAlmostEqual(v,(hi[0]-lo[0])/(2*h),places=6)
            self.assertAlmostEqual(a,(hi[1]-lo[1])/(2*h),places=5)
        self.assertEqual(g.sample(g.start)[1:],(0.,None))
        self.assertEqual(g.sample(g.end)[1:],(0.,None))
        self.assertAlmostEqual(g.sample(g.start+1e-9)[2],g.envelope()["acceleration_jump"],places=5)
        self.assertAlmostEqual(g.sample(g.end-1e-9)[2],-g.envelope()["acceleration_jump"],places=5)
        r=audit(g,IndexRequirement(math.pi/2,.7,require_c2=True))
        self.assertEqual(r["analytic"]["metrics"]["c2_compatible"]["status"],"fail")
    def test_candidate_selection(self):
        candidates=[("six",Geneva(6,10,.3,.05)),("compact",Geneva(4,1,.3,.05)),
            ("four",Geneva(4,10,.3,.05))]
        r=screen(IndexRequirement(math.pi/2,.75),candidates,3)
        self.assertEqual(r["decision"]["selected"],"four")
        self.assertEqual(r["decision"]["states"],{"six":"fail","compact":"fail","four":"pass"})
        self.assertEqual(r["reports"]["compact"]["analytic"]["metrics"]["hub"]["status"],"fail")
        self.assertEqual(screen(IndexRequirement(math.pi/2,.8),candidates,3)["decision"]["action"],"stop_and_redesign")
        with self.assertRaises(ValueError):screen(IndexRequirement(math.pi/2,.75),candidates,2)
    def test_phase_and_validation(self):
        a=Geneva(4,10,.3,.05);b=Geneva(4,10,.3,.05,.2)
        for u in (-2.1,-.6,.1,.31,.9,2.1):
            self.assertEqual(a.sample(u+.2),b.sample(u))
        for n in (2,13,True):
            with self.assertRaises(ValueError):Geneva(n,10,.3,.05)
        with self.assertRaises(ValueError):Geneva(4,10,0,.05)
        with self.assertRaises(ValueError):IndexRequirement(math.pi/2,1)
        with self.assertRaises(ValueError):a.sample(float("nan"))
if __name__=="__main__":unittest.main()
