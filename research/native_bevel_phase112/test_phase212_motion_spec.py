import json,math,unittest
from phase212_motion_spec import Knot,Track,MotionSpec

class MotionTests(unittest.TestCase):
    def test_translation_and_dwell(self):
        t=Track("push","mm",(Knot(0,0),Knot(.25,0),Knot(.5,10),Knot(.75,10),Knot(1,0)))
        self.assertEqual(t.dwell_intervals(),((0,.25),(.5,.75)))
        self.assertEqual(t.sample(.125),(0,0,0))
        self.assertEqual(t.sample(.625),(10,0,0))
        self.assertAlmostEqual(t.sample(.375)[0],5)
        self.assertAlmostEqual(t.sample(.875)[0],5)
        for k in t.knots:
            for got,want in zip(t.sample(k.phase),(k.position,k.velocity,k.acceleration)):
                self.assertAlmostEqual(got,want,places=8)
    def test_unwrapped_rotation_and_offset(self):
        t=Track("index","rad",(Knot(0,0),Knot(.5,math.pi/2),Knot(1,math.pi/2)),math.pi/2,.25)
        self.assertAlmostEqual(t.sample(0)[0],math.pi/4)
        self.assertAlmostEqual(t.sample(1)[0],3*math.pi/4)
        self.assertAlmostEqual(t.sample(-1)[0],-math.pi/4)
        self.assertEqual(t.dwell_intervals(),((.5,1),))
        for cycle in (-2.4,-.1,.1,.7,2.7):
            a=t.sample(cycle);b=t.sample(cycle+4)
            self.assertAlmostEqual(b[0]-a[0],2*math.pi)
            self.assertAlmostEqual(a[1],b[1])
            self.assertAlmostEqual(a[2],b[2])
    def test_historical_stride_exact(self):
        # Phase210 inverse-cam stride law, re-expressed without hardcoded
        # mechanism types; lift's degree-six law is not represented here.
        duty=.77;A=2.4;v=A/duty;k=v*(1-duty)
        t=Track("stride","model_unit",(Knot(0,0,v),Knot(duty,A,v),Knot(1,0,v)))
        for i in range(1001):
            u=i/1000%1
            q=max(0,min(1,(u-duty)/(1-duty)))
            expected=A*u/duty if u<=duty else A+k*q-(A+k)*(10*q**3-15*q**4+6*q**5)
            self.assertAlmostEqual(t.sample(u)[0],expected,places=10)
    def test_derivatives_and_time_scaling(self):
        t=Track("stroke","mm",(Knot(0,0),Knot(.5,8,0,-4),Knot(1,0)))
        spec=MotionSpec((t,),2.5)
        h=1e-5
        for s in (.2,.8,1.25,1.8,2.7):
            p,v,a=spec.sample(s)["stroke"]
            lo=spec.sample(s-h)["stroke"];hi=spec.sample(s+h)["stroke"]
            self.assertAlmostEqual(v,(hi[0]-lo[0])/(2*h),places=6)
            self.assertAlmostEqual(a,(hi[1]-lo[1])/(2*h),places=5)
        self.assertEqual(MotionSpec.from_dict(json.loads(json.dumps(spec.to_dict()))),spec)
    def test_invalid_specs(self):
        for knots in ((Knot(0,0),Knot(1,1)),(Knot(0,0),Knot(1,0,1)),
                      (Knot(.1,0),Knot(1,0)),(Knot(0,0),Knot(.5,0),Knot(.5,0),Knot(1,0))):
            with self.assertRaises(ValueError):Track("x","mm",knots)
        t=Track("x","mm",(Knot(0,0),Knot(1,0)))
        for period in (0,-1,float("nan"),True):
            with self.assertRaises(ValueError):MotionSpec((t,),period)
        with self.assertRaises(ValueError):MotionSpec((t,t),1)
        with self.assertRaises(ValueError):Track("x","degrees",t.knots)
        with self.assertRaises(ValueError):Knot(0,float("inf"))
        with self.assertRaises(ValueError):t.sample(float("nan"))

if __name__=="__main__":unittest.main(verbosity=2)
