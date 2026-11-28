import json,unittest
from pathlib import Path
from side_width import WIDTHS,trial,deform,widths
from fair_garment import trial as source_trial
from garment import edge_groups
from test_garment import preview

class SideWidthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p,q,l,r=source_trial()
        assert r["fixture_gate"]
        cls.source=p,q,l
    def test_fixed_boundaries_and_order(self):
        actual=[]
        for w in WIDTHS:
            r,p,q,l=trial(w,False,self.source)
            self.assertEqual((q,l),self.source[1:])
            self.assertEqual(r["waist_drift"],0)
            self.assertEqual(r["center_plane_drift"],0)
            self.assertTrue(r["metrics"]["topology_pass"])
            self.assertFalse(r["passed"])
            actual.append(sum(r["actual_widths"])/2)
        self.assertEqual(actual,sorted(actual,reverse=True))
    def test_invalid_width(self):
        p,q,l=self.source
        with self.assertRaises(ValueError):deform(p,l,0.)

def evidence():
    dest=Path("results/side_width");dest.mkdir(parents=True,exist_ok=True)
    p,q,l,r=source_trial();assert r["fixture_gate"]
    source=p,q,l
    cases=[]
    for w in WIDTHS:
        result,p,q,l=trial(w,True,source);cases.append(result)
        name="width_"+str(round(w*100))
        groups=edge_groups(q,l)
        with (dest/(name+".obj")).open("w") as out:
            out.write("# Static side-width variation\n")
            for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            prev=None
            for f,role in zip(q,groups):
                if role!=prev:out.write("g "+role+"\n");prev=role
                out.write("f "+" ".join(str(i+1) for i in f)+"\n")
        preview(dest/(name+"_preview.svg"),p,q,groups)
    report=dict(complete=True,cases=cases,fixture_gate=all(r["passed"] for r in cases),
        global_intersection_verified=False,lower_body_fit_verified=False,blender_verified=False,visual_review_required=True)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213SIDE_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
