"""Check actual single-envelope cut topology and export comparison evidence."""
import json,unittest
from pathlib import Path
from cut_garment import base,trial,round_hem,inspect_cut
from garment import edge_groups
from test_garment import preview
from junction import audit

class CutTests(unittest.TestCase):
    def test_three_distinct_cuts(self):
        p,q,l=base()
        m=audit(p,q,l,p)
        self.assertTrue(m["topology_pass"],m)
        self.assertEqual(len(l),3)
        self.assertTrue(all(p[i][0]<0 for i in l[1]))
        self.assertTrue(all(p[i][0]>0 for i in l[2]))
        self.assertEqual(len({i for loop in l for i in loop}),sum(map(len,l)))
    def test_round_only_leg_edges(self):
        p,q,l=base();s=round_hem(p,l)
        leg=set(l[1]+l[2])
        self.assertTrue(all(a==b for i,(a,b) in enumerate(zip(p,s)) if i not in leg))
        self.assertTrue(any(p[i]!=s[i] for i in leg))
    def test_bounded_trial(self):
        p,q,l,r=trial()
        self.assertEqual([c["smoothing"] for c in r["candidates"]],list((0,8,16)[:len(r["candidates"])]))
        self.assertEqual(r["fixture_gate"],any(c["metrics"]["cut_pilot_pass"] for c in r["candidates"]))
        self.assertTrue(audit(p,q,l,p)["topology_pass"])
    def test_negative_control(self):
        p,q,l=base()
        self.assertFalse(inspect_cut(p,q[1:],l,p)["cut_pilot_pass"])

def evidence():
    dest=Path("results/r7c");dest.mkdir(parents=True,exist_ok=True)
    p,q,l,r=trial();groups=edge_groups(q,l)
    with (dest/"cut_envelope.obj").open("w") as out:
        out.write("# R7C single-envelope garment surface; optional Solidify\n")
        for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
        prev=None
        for f,role in zip(q,groups):
            if role!=prev:out.write("g "+role+"\n");prev=role
            out.write("f "+" ".join(str(i+1) for i in f)+"\n")
    preview(dest/"cut_envelope_preview.svg",p,q,groups)
    r.update(scope="synthetic single envelope with three cuts",visual_review_required=True,
        global_intersection_verified=False,lower_body_fit_verified=False,blender_verified=False)
    (dest/"report.json").write_text(json.dumps(r,indent=2,allow_nan=False))
    print("PHASE213R7C_SUMMARY",json.dumps(r,allow_nan=False))
if __name__=="__main__":evidence()
