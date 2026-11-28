import json,math,unittest
from pathlib import Path
from pattern_coverage import PLAN,generate,evaluate
from pattern_garment import DOWN
from test_pattern_garment import export_obj
from visibility_diagnostic import raster,png

class PanelCoverageTests(unittest.TestCase):
    def test_independent_width(self):
        for spec in PLAN:
            _,p,v,q,l,g,a,b,rows=generate(spec)
            for role,value in (("front",spec[2]),("back",spec[3])):
                row=rows[role][DOWN//2]
                self.assertAlmostEqual(max(abs(v[i][0]) for i in row)/max(abs(p[i][0]) for i in row)-1,value)
                if not value:self.assertTrue(all(p[i]==v[i] for r in rows[role] for i in r))
            self.assertTrue(all(p[i]==v[i] for i in set(l[0])|set(a)|set(b)))
    def test_identity_and_invalid(self):
        _,p,v,*_=generate(PLAN[0])
        self.assertEqual(p,v)
        with self.assertRaises(ValueError):generate(("invalid",0,0.,0.))

def evidence():
    src=json.loads(Path("results/pattern_ellipse/report.json").read_text())
    if not src["fixture_gate"]:raise ValueError("R12G input gate failed")
    dest=Path("results/pattern_coverage");dest.mkdir(parents=True,exist_ok=True)
    cases=[]
    for spec in PLAN:
        r,(p,q,g)=evaluate(spec);cases.append(r)
        name=spec[0]
        export_obj(dest/(name+"_candidate.obj"),p,q,g)
        tris=[t for f in q for t in ((f[0],f[1],f[2]),(f[0],f[2],f[3]))]
        for label,angle in (("front",0.),("side",math.pi/2),("back",math.pi)):
            side,lights=raster(p,tris,angle)
            png(dest/(name+"_"+label+".png"),side,lights,False)
    report=dict(complete=True,cases=cases,fixture_gate=all(c["passed"] for c in cases),
        original_preserved=True,visual_review_required=True,blender_verified=False,
        anatomical_fit_verified=False,metric="projected halfwidth of fixed middle lower-panel row")
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213PANELCOVERAGE_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
