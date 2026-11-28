import json,unittest
from pathlib import Path
from tip_fairing import LEVELS,FACTORS,flare,contract,trial
from test_rim_wrap import CASES,generate
from fair_garment import trial as source_trial
from garment import edge_groups
from test_garment import preview

class TipTests(unittest.TestCase):
    def test_slices_measure_actual_surface(self):
        p=[(-.2,0.,-.82),(.2,0.,-.82),(.1,0.,-.69),(-.1,0.,-.69)]
        r=flare(p,[(0,1,2,3)])
        self.assertGreater(r["excess"],0.)
        self.assertEqual(len(r["profile"]),len(LEVELS))
    def test_locality_and_budget(self):
        p=[(.2,0.,-.80),(.2,0.,-.70),(.2,0.,.4),(0.,0.,-.80)]
        for factor in FACTORS:
            q=contract(p,factor)
            self.assertAlmostEqual(q[0][0],.2*factor)
            self.assertEqual(q[1:],p[1:])
            self.assertEqual([v[1:] for v in p],[v[1:] for v in q])
        with self.assertRaises(ValueError):contract(p,.1)

def evidence():
    dest=Path("results/tip_fairing");dest.mkdir(parents=True,exist_ok=True)
    p,q,l,r=source_trial();assert r["fixture_gate"]
    results=[]
    for case in CASES:
        result,a,b,c=trial(case,(p,q,l));results.append(result)
        name=case[0];groups=edge_groups(b,c)
        with (dest/(name+".obj")).open("w") as out:
            out.write("# Static lower flare correction pilot\n")
            for v in a:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            prev=None
            for f,role in zip(b,groups):
                if role!=prev:out.write("g "+role+"\n");prev=role
                out.write("f "+" ".join(str(i+1) for i in f)+"\n")
        preview(dest/(name+"_preview.svg"),a,b,groups)
    report=dict(complete=True,cases=results,fixture_gate=all(r["passed"] for r in results),
        global_intersection_verified=False,lower_body_fit_verified=False,blender_verified=False,visual_review_required=True)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213TIP_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
