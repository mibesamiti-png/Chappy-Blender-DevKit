import math,unittest
from phase212_motion_spec import Knot,Track
from phase212_radial_cam import CamConfig,generate,audit,screen

def stride(offset=0.):
    duty=.77;v=2.4/duty
    return Track("stride","model_unit",(Knot(0,0,v),Knot(duty,2.4,v),Knot(1,0,v)),phase_offset=offset)

def cfg(base=7.,core=.5):
    return CamConfig(base,.25,core,samples=360)

class CamTests(unittest.TestCase):
    def test_constant_radius_and_core(self):
        t=Track("dwell","mm",(Knot(0,0),Knot(1,0)))
        c=cfg(3.)
        poly=generate(t,c)
        self.assertTrue(all(abs(math.hypot(*p)-2.75)<1e-12 for p in poly))
        r=audit(t,c,poly)
        self.assertEqual(r["sampled_geometry"]["status"],"pass")
        self.assertFalse(r["physical_contact_certified"])
        self.assertFalse(r["continuous_proof"])
        self.assertEqual(audit(t,cfg(3.,2.8),poly)["sampled_geometry"]["metrics"]["core_radius"]["status"],"fail")
    def test_historical_stride_and_shift(self):
        c=cfg()
        for offset in (0.,.25):
            t=stride(offset);p=generate(t,c);r=audit(t,c,p)
            self.assertEqual(r["sampled_geometry"]["status"],"pass",r)
            self.assertGreater(r["audit_samples"],len(p))
        self.assertNotEqual(generate(stride(),c),generate(stride(.25),c))
    def test_independent_negative_controls(self):
        t=stride();c=cfg()
        naive=[]
        for i in range(c.samples):
            u=i/c.samples;r=c.pitch_base+t.sample(u)[0]-c.roller_radius
            naive.append((r*math.cos(math.tau*u),r*math.sin(math.tau*u)))
        r=audit(t,c,naive)["sampled_geometry"]
        self.assertEqual(r["metrics"]["roller_gap"]["status"],"fail")
        small=cfg(2.)
        self.assertEqual(audit(t,small,generate(t,small))["sampled_geometry"]["metrics"]["pressure"]["status"],"fail")
        poly=list(generate(t,c));poly[100]=(poly[100][0]*1.1,poly[100][1]*1.1)
        self.assertEqual(audit(t,c,poly)["sampled_geometry"]["status"],"fail")
    def test_fixed_budget(self):
        t=stride()
        r=screen(t,[("compact",cfg(2.)),("reference",cfg())],2)
        self.assertEqual(r["decision"]["selected"],"reference")
        self.assertEqual(r["decision"]["states"],{"compact":"fail","reference":"pass"})
        self.assertFalse(r["physical_contact_certified"])
        self.assertEqual(screen(t,[("compact",cfg(2.))],1)["decision"]["action"],"stop_and_redesign")
        with self.assertRaises(ValueError):screen(t,[("compact",cfg(2.)),("reference",cfg())],1)
    def test_reject_unsupported(self):
        for t in (Track("rotation","rad",(Knot(0,0),Knot(1,0))),
                  Track("advance","mm",(Knot(0,0),Knot(1,1)),1)):
            with self.assertRaises(ValueError):generate(t,cfg())
        with self.assertRaises(ValueError):CamConfig(2,0,.5)
        with self.assertRaises(ValueError):audit(stride(),cfg(),[(0,0)]*360)

if __name__=="__main__":unittest.main(verbosity=2)
