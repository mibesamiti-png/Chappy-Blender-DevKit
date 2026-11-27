import json,unittest
from pathlib import Path
from test_refinement import source
from test_junction import FIXTURES
from refinement import refine
from junction import audit as surface_audit
from shell import shell,audit,THICKNESS

def fixture(f):
    p,q,l=source(f)
    s,t,u,ref=refine(p,q,l,"smooth")
    m=surface_audit(s,t,u,ref)
    assert m["passed"] and m["max_normal_jump"]<=surface_audit(p,q,l,p)["max_normal_jump"]+1e-8
    return s,t,u

def trial(f):
    p,q,l=fixture(f)
    s,t,g=shell(p,q,l)
    m=audit(p,q,l,s,t,g)
    return dict(name=f[0],metrics=m),s,t,g

class ShellTests(unittest.TestCase):
    def test_fixed_fixtures(self):
        for f in FIXTURES:
            r,p,q,g=trial(f)
            self.assertEqual(len(p),12574)
            self.assertEqual(len(q),12576)
            self.assertTrue(r["metrics"]["passed"],r)
    def test_preserve_outer_and_edge_roles(self):
        p,q,l=fixture(FIXTURES[0]);s,t,g=shell(p,q,l)
        self.assertEqual(s[:len(p)],p)
        for role,loop in zip(("waist","left","right"),l):
            self.assertEqual(g.count("rim_"+role),len(loop))
            self.assertEqual(g.count("edge_strip_"+role),len(loop))
    def test_negative_controls(self):
        p,q,l=fixture(FIXTURES[0]);s,t,g=shell(p,q,l)
        self.assertFalse(audit(p,q,l,s,t[:-1],g[:-1])["passed"])
        bad=t[:];bad[20]=bad[20][::-1]
        self.assertFalse(audit(p,q,l,s,bad,g)["passed"])
        moved=s[:];moved[len(p)]=p[0]
        self.assertFalse(audit(p,q,l,moved,t,g)["passed"])
    def test_invalid_input(self):
        p,q,l=fixture(FIXTURES[0])
        with self.assertRaises(ValueError):shell(p,q,l,.1)
        with self.assertRaises(ValueError):shell(p,q,l[:2])
        with self.assertRaises(ValueError):shell(p,q[1:],l)

def evidence():
    dest=Path("results/r6");dest.mkdir(parents=True,exist_ok=True)
    cases=[]
    for f in FIXTURES:
        r,p,q,g=trial(f);cases.append(r)
        with (dest/(f[0]+".obj")).open("w") as out:
            out.write("# R6 static shell and named edge strips\n")
            for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            previous=None
            for face,group in zip(q,g):
                if group!=previous:out.write("g "+group+"\n");previous=group
                out.write("f "+" ".join(str(i+1) for i in face)+"\n")
    report=dict(complete=True,thickness=THICKNESS,cases=cases,fixture_gate=all(c["metrics"]["passed"] for c in cases),raised_band=False,global_intersection_verified=False,blender_verified=False,garment_certified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213R6_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
