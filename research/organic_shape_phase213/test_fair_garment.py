import json,unittest
from pathlib import Path
from fair_garment import fair,trial,PLAN
from cut_garment import base
from garment import edge_groups
from test_garment import preview

class FairTests(unittest.TestCase):
    def test_fixed_waist_and_extents(self):
        p,q,l=base()
        for steps in PLAN:
            s=fair(p,q,l,steps)
            self.assertTrue(all(p[i]==s[i] for i in l[0]))
            for loop in l[1:]:
                for k in range(3):
                    self.assertAlmostEqual(min(p[i][k] for i in loop),min(s[i][k] for i in loop))
                    self.assertAlmostEqual(max(p[i][k] for i in loop),max(s[i][k] for i in loop))
            self.assertNotEqual(p,s)
        with self.assertRaises(ValueError):fair(p,q,l,99)
    def test_bounded_trial(self):
        p,q,l,r=trial()
        self.assertEqual([c["steps"] for c in r["candidates"]],list(PLAN[:len(r["candidates"])]))
        self.assertEqual(r["fixture_gate"],any(c["eligible"] for c in r["candidates"]))
        self.assertEqual((len(p),len(q)),(4311,4160))
        self.assertTrue(r["candidates"][-1]["metrics"]["topology_pass"])

def evidence():
    dest=Path("results/r7d");dest.mkdir(parents=True,exist_ok=True)
    p,q,l,r=trial();groups=edge_groups(q,l)
    with (dest/"fair_envelope.obj").open("w") as out:
        out.write("# R7D fair hem, static surface\n")
        for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
        prev=None
        for f,role in zip(q,groups):
            if role!=prev:out.write("g "+role+"\n");prev=role
            out.write("f "+" ".join(str(i+1) for i in f)+"\n")
    preview(dest/"fair_envelope_preview.svg",p,q,groups)
    r.update(visual_review_required=True,global_intersection_verified=False,lower_body_fit_verified=False,blender_verified=False)
    (dest/"report.json").write_text(json.dumps(r,indent=2,allow_nan=False))
    print("PHASE213R7D_SUMMARY",json.dumps(r,allow_nan=False))
if __name__=="__main__":evidence()
