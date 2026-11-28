"""R12G: shared ellipse angular parameter, fixed five cases."""
import json,math,unittest
from pathlib import Path
from pattern_garment import CASES,mesh
from test_pattern_rim import compare,side_angles
from test_pattern_garment import export_obj
from visibility_diagnostic import raster,png

class EllipseRimTests(unittest.TestCase):
    def test_fixed_geometry_contract(self):
        for case in CASES:
            p,q,l,g,a,b=mesh(case)
            v,f,r,h,c,d=mesh(case,"ellipse_rim")
            self.assertEqual((q,l,g,a,b),(f,r,h,c,d))
            self.assertTrue(all(p[i]==v[i] for i in set(l[0])|set(a)|set(b)))
    def test_rim_and_quad_quality(self):
        from junction import audit
        for case in CASES:
            p,q,l,*_=mesh(case,"ellipse_rim")
            self.assertLessEqual(max(side_angles(p,l,case)),35.)
            m=audit(p,q,l,p)
            self.assertGreater(m["min_quad_cos"],0.)
            self.assertLessEqual(m["max_edge_ratio"],20.)
            self.assertLessEqual(m["max_normal_jump"],55.)

def evidence():
    dest=Path("results/pattern_ellipse");dest.mkdir(parents=True,exist_ok=True)
    source=json.loads(Path("results/pattern_reimport/report.json").read_text())
    if not source["fixture_gate"]:raise ValueError("R12C source gate failed")
    cases=[]
    for case in CASES:
        r,(p,q,g)=compare(case,"ellipse_rim");cases.append(r)
        name=case[0]
        export_obj(dest/(name+"_candidate.obj"),p,q,g)
        tris=[t for f in q for t in ((f[0],f[1],f[2]),(f[0],f[2],f[3]))]
        for label,angle in (("front",0.),("side",math.pi/2),("back",math.pi)):
            side,lights=raster(p,tris,angle)
            png(dest/(name+"_"+label+".png"),side,lights,False)
    report=dict(complete=True,cases=cases,fixture_gate=all(c["passed"] for c in cases),
        original_preserved=True,visual_review_required=True,blender_verified=False,anatomical_fit_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213ELLIPSE_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
