import json, math, unittest
from pathlib import Path
from boundary import Boundary,Ellipsoid,audit

FIXTURES=(
    ("sphere", (1.,1.,1.),(0.,)*8,0.),
    ("oval", (1.,.78,1.3),(.15,.25,.12,-.1,-.2,-.05,.18,.23),.03),
    ("asymmetric_band",(1.15,.68,1.4),(.15,.45,.2,-.3,-.5,-.22,.1,.28),.04),
)

class BoundaryTests(unittest.TestCase):
    def test_fixture_metrics(self):
        for name,axes,controls,offset in FIXTURES:
            with self.subTest(name=name):
                b=Boundary(Ellipsoid(axes),controls,offset)
                rows=b.sample()
                q=audit(b,rows)
                self.assertTrue(q["passed"],q)
                self.assertEqual(len(rows),96)
                self.assertTrue(all(a["u"]<c["u"] for a,c in zip(rows,rows[1:])))
    def test_seam_and_knots_c2(self):
        b=Boundary(Ellipsoid((1.,.8,1.2)),FIXTURES[-1][2],.03)
        h=1e-5
        for i in range(len(b.controls)):
            t=i/len(b.controls)
            a,c,d,e,f=[b.latitude(t+j*h) for j in (-2,-1,0,1,2)]
            left=(3*d-4*c+a)/(2*h)
            right=(-3*d+4*e-f)/(2*h)
            self.assertLess(abs(left-right),1e-5)
            self.assertLess(abs((d-2*c+a)-(f-2*e+d))/h**2,.1)
        self.assertLess(math.dist(b.at(0)[2],b.at(1)[2]),1e-12)
    def test_local_control_edit(self):
        b=Boundary(Ellipsoid((1.,.8,1.2)),(0.,)*8)
        c=Boundary(b.surface,(.3,)+(0.,)*7)
        unchanged=changed=0
        for i in range(128):
            u=i/128
            diff=math.dist(b.at(u)[2],c.at(u)[2])
            if .25<=u<=.75:
                self.assertLess(diff,1e-12);unchanged+=1
            elif diff>1e-6:changed+=1
        self.assertGreaterEqual(unchanged,65)
        self.assertGreater(changed,0)
    def test_resolution(self):
        b=Boundary(Ellipsoid(FIXTURES[-1][1]),FIXTURES[-1][2],.04)
        for n in (64,128,256):
            self.assertTrue(audit(b,b.sample(n))["passed"])
    def test_reject_bad_inputs(self):
        with self.assertRaises(ValueError):Ellipsoid((1.,0.,1.))
        s=Ellipsoid((1.,1.,1.))
        for controls,offset in [((0.,)*3,0),((0.,)*7+(float("nan"),),0),((1.3,)*8,0),((0.,)*8,-.1),((0.,)*8,.2)]:
            with self.assertRaises(ValueError):Boundary(s,controls,offset)
        with self.assertRaises(ValueError):Boundary(s,(0.,)*8).sample(8)
    def test_independent_negative_controls(self):
        b=Boundary(Ellipsoid((1.,1.,1.)),(0.,)*8,.03)
        rows=b.sample()
        r=rows[4];r["point"]=(r["point"][0]+.2,*r["point"][1:])
        self.assertFalse(audit(b,rows)["passed"])
        rows=b.sample();rows.reverse()
        self.assertFalse(audit(b,rows)["passed"])
        rows=b.sample();rows[3]["point"]=rows[2]["point"]
        with self.assertRaises(ValueError):audit(b,rows)

def evidence():
    dest=Path("results");dest.mkdir(exist_ok=True)
    cases=[]
    for name,axes,controls,offset in FIXTURES:
        b=Boundary(Ellipsoid(axes),controls,offset);rows=b.sample()
        metric=audit(b,rows)
        assert metric["passed"]
        cases.append(dict(name=name,axes=axes,controls=controls,offset=offset,metrics=metric,rows=rows))
        # OBJ is a closed polyline, not a filled garment or native Blender proof.
        with (dest/(name+".obj")).open("w") as f:
            f.write("# R1 sampled closed boundary\n")
            for r in rows:f.write("v "+" ".join(format(x,".12g") for x in r["point"])+"\n")
            f.write("l "+" ".join(map(str,range(1,len(rows)+1)))+" 1\n")
    out=dict(complete=True,scope="synthetic ellipsoid chart only",cases=cases,blender_verified=False,garment_certified=False)
    (dest/"report.json").write_text(json.dumps(out,indent=2,allow_nan=False))
    print("PHASE213R1_SUMMARY",json.dumps([{k:v for k,v in c.items() if k!="rows"} for c in cases],allow_nan=False))

if __name__=="__main__":
    evidence()
