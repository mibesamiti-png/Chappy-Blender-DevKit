import json,math,unittest
from pathlib import Path
from fitting import Target,source,fit,audit

FIXTURES=(("reference",.32,.22,.08),("wide_hip",.45,.18,.06),("deep_back",.28,.32,.14))
def trial(f):
    name,*dims=f
    target=Target(*dims)
    rows,faces=source();p=[r["point"] for r in rows]
    q=fit(p,target)
    return dict(name=name,dimensions=dims,metrics=audit(p,q,faces,target)),q,faces

class FitTests(unittest.TestCase):
    def test_frozen_cases(self):
        for f in FIXTURES:
            r,_,_=trial(f)
            self.assertTrue(r["metrics"]["passed"],r)
    def test_independent_ray(self):
        for _,*dims in FIXTURES:
            t=Target(*dims)
            for z in (-1.,-.32,0.,.8):
                for i in range(32):
                    a=math.tau*i/32
                    self.assertLess(abs(t.ray(a,z)-t.reference_radius(a,z)),1e-12)
    def test_negative_controls(self):
        rows,faces=source();p=[r["point"] for r in rows];t=Target(*FIXTURES[0][1:])
        q=fit(p,t)
        self.assertFalse(audit(p,q,faces[1:],t)["passed"])
        bad=q[:];x,y,z=bad[100];bad[100]=(x*.8,y*.8,z)
        m=audit(p,bad,faces,t)
        self.assertFalse(m["passed"])
        self.assertLess(m["min_sampled_radial_gap"],0)
        self.assertFalse(audit(p,q,faces,t,.045)["passed"])
    def test_reject_out_of_scope(self):
        with self.assertRaises(ValueError):Target(.8,.2,.1)
        t=Target(.3,.2,.1)
        with self.assertRaises(ValueError):fit([(0.,0.,0.)],t)
        with self.assertRaises(ValueError):fit([(1.,0.,2.)],t)
        with self.assertRaises(ValueError):fit([(1.,0.,0.)],t,0.)

def evidence():
    dest=Path("results/r4");dest.mkdir(parents=True,exist_ok=True)
    cases=[]
    for f in FIXTURES:
        r,p,q=trial(f);cases.append(r)
        with (dest/(f[0]+".obj")).open("w") as out:
            out.write("# R4 synthetic radial-fit patch\n")
            for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            for face in q:out.write("f "+" ".join(str(i+1) for i in face)+"\n")
    report=dict(complete=True,scope="synthetic torso annulus only",cases=cases,fixture_gate=all(c["metrics"]["passed"] for c in cases),continuous_clearance_verified=False,blender_verified=False,garment_certified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213R4_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
