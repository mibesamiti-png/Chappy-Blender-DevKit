import json,unittest
from pathlib import Path
from junction import mesh,smooth,audit

FIXTURES=(("reference",1.35,.75,.68),("wide",1.55,.75,.80),("deep",1.35,.90,.68))
PLAN=(0,8,16,32)

def trial(f):
    name,*dims=f
    pts,faces,loops=mesh(*dims)
    base=audit(pts,faces,loops,pts)
    candidates=[]
    for steps in PLAN:
        p=smooth(pts,faces,loops,steps)
        m=audit(p,faces,loops,pts)
        eligible=steps>0 and m["passed"] and m["max_normal_jump"]<=.9*base["max_normal_jump"]
        candidates.append(dict(steps=steps,metrics=m,eligible=eligible))
        if eligible:
            return dict(name=name,dimensions=dims,candidates=candidates,selected=steps,passed=True),p,faces
    return dict(name=name,dimensions=dims,candidates=candidates,selected=None,passed=False),pts,faces

class JunctionTests(unittest.TestCase):
    def test_topology(self):
        for f in FIXTURES:
            p,q,l=mesh(*f[1:])
            m=audit(p,q,l,p)
            self.assertTrue(m["topology_pass"],m)
            self.assertEqual(m["boundary_loops"],3)
            self.assertEqual(m["euler"],-1)
    def test_fixed_boundaries(self):
        p,q,l=mesh()
        for steps in PLAN:
            s=smooth(p,q,l,steps)
            self.assertTrue(all(s[i]==p[i] for loop in l for i in loop))
            self.assertTrue(audit(s,q,l,p)["topology_pass"])
        self.assertNotEqual(s,p)
    def test_negative_controls(self):
        p,q,l=mesh()
        self.assertFalse(audit(p,q[1:],l,p)["topology_pass"])
        self.assertFalse(audit(p,q+[q[0]],l,p)["topology_pass"])
        rev=q[:];rev[3]=rev[3][::-1]
        self.assertFalse(audit(p,rev,l,p)["topology_pass"])
        moved=p[:];i=l[0][0];x,y,z=moved[i];moved[i]=(x+.1,y,z)
        self.assertFalse(audit(moved,q,l,p)["passed"])
    def test_bounded_selection(self):
        for f in FIXTURES:
            r,_,_=trial(f)
            self.assertEqual([c["steps"] for c in r["candidates"]],list(PLAN[:len(r["candidates"])]))
            eligible=[c["steps"] for c in r["candidates"] if c["eligible"]]
            self.assertEqual(r["selected"],eligible[0] if eligible else None)
            self.assertEqual(r["passed"],bool(eligible))
    def test_reject_parameters(self):
        with self.assertRaises(ValueError):mesh(width=.1)
        p,q,l=mesh()
        with self.assertRaises(ValueError):smooth(p,q,l,99)

def evidence():
    dest=Path("results/r3");dest.mkdir(parents=True,exist_ok=True)
    cases=[]
    for f in FIXTURES:
        r,p,q=trial(f);cases.append(r)
        with (dest/(f[0]+".obj")).open("w") as out:
            out.write("# R3 synthetic junction candidate\n")
            for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            for face in q:out.write("f "+" ".join(str(i+1) for i in face)+"\n")
    report=dict(complete=True,scope="fixed synthetic one-to-two junction",cases=cases,
        fixture_gate=all(c["passed"] for c in cases),global_intersection_verified=False,blender_verified=False,garment_certified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213R3_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
