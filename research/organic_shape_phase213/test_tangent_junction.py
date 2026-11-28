"""R3B fixed tangent-aware repair, compare to the original linear loft."""
import json,unittest
from pathlib import Path
from junction import mesh,smooth,audit
from test_junction import FIXTURES

def trial(f):
    name,*dims=f
    reference,faces,loops=mesh(*dims)
    baseline=audit(reference,faces,loops,reference)
    p,q,l=mesh(*dims,method="tangent")
    assert q==faces and l==loops
    candidates=[]
    for steps in (0,8,16,32):
        out=smooth(p,q,l,steps);m=audit(out,q,l,reference)
        ok=m["passed"] and m["max_normal_jump"]<=.9*baseline["max_normal_jump"]
        candidates.append(dict(steps=steps,metrics=m,eligible=ok))
        if ok:
            return dict(name=name,baseline=baseline,candidates=candidates,selected=steps,passed=True),out,q
    return dict(name=name,baseline=baseline,candidates=candidates,selected=None,passed=False),p,q

class TangentTests(unittest.TestCase):
    def test_preserve_topology_and_boundary(self):
        for f in FIXTURES:
            p,q,l=mesh(*f[1:]);s,t,u=mesh(*f[1:],method="tangent")
            self.assertEqual((q,l),(t,u))
            self.assertTrue(all(p[i]==s[i] for loop in l for i in loop))
            self.assertTrue(audit(s,t,u,p)["topology_pass"])
            self.assertNotEqual(p,s)
    def test_bounded_gate(self):
        for f in FIXTURES:
            r,_,_=trial(f)
            self.assertEqual([c["steps"] for c in r["candidates"]],list((0,8,16,32)[:len(r["candidates"])]))
            self.assertEqual(r["passed"],any(c["eligible"] for c in r["candidates"]))
            if r["passed"]:self.assertTrue(r["candidates"][-1]["eligible"])
    def test_invalid_method(self):
        with self.assertRaises(ValueError):mesh(method="unknown")

def evidence():
    dest=Path("results/r3b");dest.mkdir(parents=True,exist_ok=True)
    cases=[]
    for f in FIXTURES:
        r,p,q=trial(f);cases.append(r)
        with (dest/(f[0]+".obj")).open("w") as out:
            out.write("# R3B tangent-aware junction\n")
            for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            for face in q:out.write("f "+" ".join(str(i+1) for i in face)+"\n")
    report=dict(complete=True,cases=cases,fixture_gate=all(c["passed"] for c in cases),global_intersection_verified=False,blender_verified=False,garment_certified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213R3B_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
