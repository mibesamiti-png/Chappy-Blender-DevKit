import json,unittest
from pathlib import Path
from coverage_profile import CASES,trial,deform_profile
from fair_garment import trial as source_trial
from side_width import deform
from garment import edge_groups
from test_garment import preview

class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p,q,l,r=source_trial()
        assert r["fixture_gate"]
        cls.source=p,q,l
    def test_noop_and_validation(self):
        p,q,l=self.source
        p=deform(p,l,.32)
        self.assertEqual(deform_profile(p,l,0.,0.),p)
        for f,b in ((.11,0.),(0.,float("nan"))):
            with self.assertRaises(ValueError):deform_profile(p,l,f,b)
    def test_fixed_axes_and_independent_controls(self):
        for case in CASES:
            r,p,q,l=trial(case,False,self.source)
            self.assertEqual((q,l),self.source[1:])
            self.assertEqual(r["waist_drift"],0.)
            self.assertEqual(r["cardinal_drift"],0.)
            self.assertTrue(r["metrics"]["topology_pass"])
            self.assertFalse(r["passed"])
            for goal,actual in zip(r["coverage_requested"],r["coverage_changes"]):
                if goal:self.assertGreater(goal*actual,0.)
                else:self.assertAlmostEqual(actual,0.,places=10)

def evidence():
    dest=Path("results/coverage_profile");dest.mkdir(parents=True,exist_ok=True)
    p,q,l,r=source_trial();assert r["fixture_gate"]
    source=p,q,l
    cases=[]
    for case in CASES:
        result,p,q,l=trial(case,True,source);cases.append(result)
        name=case[0];groups=edge_groups(q,l)
        with (dest/(name+".obj")).open("w") as out:
            out.write("# Static front/rear coverage profile\n")
            for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            prev=None
            for f,role in zip(q,groups):
                if role!=prev:out.write("g "+role+"\n");prev=role
                out.write("f "+" ".join(str(i+1) for i in f)+"\n")
        preview(dest/(name+"_preview.svg"),p,q,groups)
    report=dict(complete=True,cases=cases,fixture_gate=all(r["passed"] for r in cases),
        global_intersection_verified=False,lower_body_fit_verified=False,blender_verified=False,visual_review_required=True)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213PROFILE_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
