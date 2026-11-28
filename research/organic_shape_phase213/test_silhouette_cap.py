import json,unittest
from pathlib import Path
from silhouette_cap import PLAN,soft_cap,drop,trial
from test_rim_wrap import CASES
from fair_garment import trial as source_trial
from garment import edge_groups
from test_garment import preview

class CapTests(unittest.TestCase):
    def test_selective_and_monotone(self):
        p=[(x,0.,-.78) for x in (-.3,-.12,-.03,0.,.03,.12,.3)]
        p.append((.3,0.,-.735))
        for f in PLAN:
            out=soft_cap(p,.16,f)
            self.assertEqual(out[2:5],p[2:5])
            self.assertEqual(out[-1],p[-1])
            self.assertEqual([x[0] for x in out[:-1]],sorted(x[0] for x in out[:-1]))
            self.assertLess(out[6][0],p[6][0])
            self.assertEqual([x[1:] for x in out],[x[1:] for x in p])
        with self.assertRaises(ValueError):soft_cap(p,0.,PLAN[0])
    def test_drop(self):
        self.assertAlmostEqual(drop({"profile":[.1,.3,.15,.2]}),.15)
        self.assertEqual(drop({"profile":[.1,.2,.3]}),0.)

def evidence():
    dest=Path("results/silhouette_cap");dest.mkdir(parents=True,exist_ok=True)
    p,q,l,r=source_trial();assert r["fixture_gate"]
    results=[]
    for case in CASES:
        result,a,b,c=trial(case,(p,q,l));results.append(result)
        name=case[0];groups=edge_groups(b,c)
        with (dest/(name+".obj")).open("w") as out:
            out.write("# Static selective silhouette cap pilot\n")
            for v in a:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            prev=None
            for f,role in zip(b,groups):
                if role!=prev:out.write("g "+role+"\n");prev=role
                out.write("f "+" ".join(str(i+1) for i in f)+"\n")
        preview(dest/(name+"_preview.svg"),a,b,groups)
    report=dict(complete=True,cases=results,fixture_gate=all(r["passed"] for r in results),
        global_intersection_verified=False,lower_body_fit_verified=False,blender_verified=False,visual_review_required=True)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213CAP_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
