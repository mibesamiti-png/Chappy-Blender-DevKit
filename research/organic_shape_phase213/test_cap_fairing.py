import json,unittest
from pathlib import Path
from cap_fairing import PLAN,fair_local,trial
from test_rim_wrap import CASES
from fair_garment import trial as source_trial
from garment import edge_groups
from test_garment import preview

class CapFairTests(unittest.TestCase):
    def test_fixed_upper_and_local_change(self):
        p=[(-.1,0.,-.78),(.1,0.,-.78),(.1,0.,-.72),(-.1,0.,-.72)]
        q=[(0,1,2,3)]
        l=([0,1,2,3],)
        for n in PLAN:
            out=fair_local(p,p,q,l,n)
            self.assertEqual(out[2:],p[2:])
            self.assertNotEqual(out[:2],p[:2])
            self.assertEqual(len(out),len(p))
        with self.assertRaises(ValueError):fair_local(p,p,q,l,99)
    def test_waist_and_normal_case_identity(self):
        p,q,l,r=source_trial();self.assertTrue(r["fixture_gate"])
        from side_width import deform
        from cap_fairing import fair_local
        a=deform(p,l,.32)
        for n in PLAN:
            b=fair_local(a,a,q,l,n)
            self.assertTrue(all(b[i]==a[i] for i in l[0]))

def evidence():
    dest=Path("results/cap_fairing");dest.mkdir(parents=True,exist_ok=True)
    p,q,l,r=source_trial();assert r["fixture_gate"]
    results=[]
    for case in CASES:
        result,a,b,c=trial(case,(p,q,l));results.append(result)
        name=case[0];groups=edge_groups(b,c)
        with (dest/(name+".obj")).open("w") as out:
            out.write("# Static local cap fairing pilot\n")
            for v in a:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            prev=None
            for f,role in zip(b,groups):
                if role!=prev:out.write("g "+role+"\n");prev=role
                out.write("f "+" ".join(str(i+1) for i in f)+"\n")
        preview(dest/(name+"_preview.svg"),a,b,groups)
    report=dict(complete=True,cases=results,fixture_gate=all(r["passed"] for r in results),
        global_intersection_verified=False,lower_body_fit_verified=False,blender_verified=False,visual_review_required=True)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213CAPFAIR_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
