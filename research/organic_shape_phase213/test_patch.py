import unittest,json,math
from pathlib import Path
from boundary import Ellipsoid,Boundary
from patch import Patch,audit

FIXTURES=(
    ("sphere_band",(1.,1.,1.),(-.4,)*8,(.4,)*8,0.,0.),
    ("oval_band",(1.,.78,1.3),(-.5,-.42,-.55,-.7,-.6,-.35,-.25,-.4),(.15,.25,.12,-.1,-.2,-.05,.18,.23),.01,.03),
    ("asymmetric_band",(1.15,.68,1.4),(-.6,-.35,-.45,-.8,-.9,-.75,-.5,-.4),(.15,.45,.2,-.3,-.5,-.22,.1,.28),.02,.04),
)
def make(f):
    name,axes,a,b,h,k=f
    s=Ellipsoid(axes)
    return Patch(Boundary(s,a,h),Boundary(s,b,k))

class PatchTests(unittest.TestCase):
    def test_frozen_patches(self):
        for f in FIXTURES:
            with self.subTest(name=f[0]):
                p=make(f);r,q=p.mesh();m=audit(p,r,q)
                self.assertTrue(m["passed"],m)
                self.assertEqual((len(r),len(q)),(1248,1152))
    def test_exact_boundaries_and_periodicity(self):
        p=make(FIXTURES[-1])
        for j in range(33):
            u=j/32
            self.assertLess(math.dist(p.at(u,0)[1],p.lower.at(u)[2]),1e-12)
            self.assertLess(math.dist(p.at(u,1)[1],p.upper.at(u)[2]),1e-12)
            self.assertLess(math.dist(p.at(0,u)[1],p.at(1,u)[1]),1e-12)
    def test_locality(self):
        p=make(FIXTURES[-1]);b=p.upper
        c=Patch(p.lower,Boundary(b.surface,(b.controls[0]+.15,)+b.controls[1:],b.offset))
        self.assertGreater(math.dist(p.at(0,.5)[1],c.at(0,.5)[1]),.01)
        for i in range(16,49):
            for v in (0.,.5,1.):
                self.assertLess(math.dist(p.at(i/64,v)[1],c.at(i/64,v)[1]),1e-12)
        self.assertLess(math.dist(p.at(0,0)[1],c.at(0,0)[1]),1e-12)
    def test_invalid_boundaries_and_budget(self):
        p=make(FIXTURES[0])
        with self.assertRaises(ValueError):Patch(p.upper,p.lower)
        with self.assertRaises(ValueError):Patch(p.lower,Boundary(Ellipsoid((1.,1.,2.)),(.4,)*8))
        with self.assertRaises(ValueError):p.mesh(8,2)
    def test_negative_controls(self):
        p=make(FIXTURES[0]);r,q=p.mesh()
        self.assertFalse(audit(p,r,q[1:])["passed"])
        flipped=q[:];flipped[4]=flipped[4][::-1]
        self.assertFalse(audit(p,r,flipped)["passed"])
        self.assertFalse(audit(p,r,q+[q[0]])["passed"])
        r[100]["point"]=(0.,0.,0.)
        self.assertFalse(audit(p,r,q)["passed"])

def evidence():
    dest=Path("results/r2");dest.mkdir(parents=True,exist_ok=True)
    cases=[]
    for f in FIXTURES:
        p=make(f);r,q=p.mesh();m=audit(p,r,q)
        assert m["passed"],m
        name=f[0];cases.append(dict(name=name,metrics=m,rows=r,faces=q))
        with (dest/(name+".obj")).open("w") as out:
            out.write("# R2 synthetic annular patch\n")
            for v in r:out.write("v "+" ".join(format(x,".12g") for x in v["point"])+"\n")
            for face in q:out.write("f "+" ".join(str(i+1) for i in face)+"\n")
    report=dict(complete=True,scope="two ordered loops on a common ellipsoid",cases=cases,blender_verified=False,garment_certified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213R2_SUMMARY",json.dumps([dict(name=c["name"],metrics=c["metrics"]) for c in cases],allow_nan=False))
if __name__=="__main__":evidence()
