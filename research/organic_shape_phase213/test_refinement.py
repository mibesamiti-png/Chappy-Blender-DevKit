import json,unittest
from pathlib import Path
from junction import mesh,audit
from test_tangent_junction import trial as source_trial
from test_junction import FIXTURES
from refinement import refine

def source(f):
    r,p,q=source_trial(f)
    assert r["passed"]
    _,_,loops=mesh(*f[1:])
    return p,q,loops

def trial(f):
    p,q,l=source(f)
    baseline=audit(p,q,l,p)
    candidates=[]
    for method in ("smooth","linear"):
        s,t,u,ref=refine(p,q,l,method)
        m=audit(s,t,u,ref)
        ok=m["passed"] and m["max_normal_jump"]<=baseline["max_normal_jump"]+1e-8
        candidates.append(dict(method=method,metrics=m,eligible=ok))
        if ok:
            return dict(name=f[0],baseline=baseline,candidates=candidates,selected=method,passed=True),s,t
    return dict(name=f[0],baseline=baseline,candidates=candidates,selected=None,passed=False),p,q

class RefinementTests(unittest.TestCase):
    def test_topology_and_boundary(self):
        for f in FIXTURES:
            p,q,l=source(f)
            for method in ("linear","smooth"):
                s,t,u,ref=refine(p,q,l,method)
                self.assertEqual(len(t),4*len(q))
                self.assertEqual([len(x) for x in u],[2*len(x) for x in l])
                self.assertTrue(all(s[i]==p[i] for loop in l for i in loop))
                self.assertTrue(all(s[i]==ref[i] for loop in u for i in loop))
                self.assertTrue(audit(s,t,u,ref)["topology_pass"])
    def test_independent_boundary_midpoints(self):
        p,q,l=source(FIXTURES[0])
        s,t,u,ref=refine(p,q,l)
        for old,new in zip(l,u):
            for j,a in enumerate(old):
                b=old[(j+1)%len(old)]
                self.assertEqual(new[2*j],a)
                self.assertEqual(s[new[2*j+1]],tuple((x+y)/2 for x,y in zip(p[a],p[b])))
    def test_invalid_mesh(self):
        p,q,l=source(FIXTURES[0])
        for bad in (q[1:],q+[q[0]],q[:1]+[q[1][::-1]]+q[2:]):
            with self.assertRaises(ValueError):refine(p,bad,l)
        with self.assertRaises(ValueError):refine(p,q,l[:2])
        with self.assertRaises(ValueError):refine(p,q,l,"unknown")
    def test_bounded_selection(self):
        for f in FIXTURES:
            r,p,q=trial(f)
            self.assertEqual([c["method"] for c in r["candidates"]],list(("smooth","linear")[:len(r["candidates"])]))
            self.assertEqual(r["passed"],any(c["eligible"] for c in r["candidates"]))
            if r["passed"]:self.assertTrue(r["candidates"][-1]["eligible"])

def evidence():
    dest=Path("results/r5");dest.mkdir(parents=True,exist_ok=True)
    cases=[]
    for f in FIXTURES:
        r,p,q=trial(f);cases.append(r)
        with (dest/(f[0]+".obj")).open("w") as out:
            out.write("# R5 boundary-preserving refinement candidate\n")
            for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            for face in q:out.write("f "+" ".join(str(i+1) for i in face)+"\n")
    report=dict(complete=True,cases=cases,fixture_gate=all(c["passed"] for c in cases),global_intersection_verified=False,blender_verified=False,garment_certified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213R5_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
