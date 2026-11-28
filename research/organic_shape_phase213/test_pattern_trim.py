"""R12E: compare a whole-row angular trim against unchanged R12A baseline."""
import json,math,unittest
from pathlib import Path
from pattern_garment import CASES,mesh
from test_pattern_rim import compare,side_angles
from test_pattern_garment import export_obj
from visibility_diagnostic import raster,png

class TrimmedRimTests(unittest.TestCase):
    def test_fixed_endpoints_and_connectivity(self):
        for case in CASES:
            p,q,l,g,a,b=mesh(case)
            v,f,r,h,c,d=mesh(case,"trimmed_rim")
            self.assertEqual((q,l,g,a,b),(f,r,h,c,d))
            self.assertTrue(all(p[i]==v[i] for i in set(l[0])|set(a)|set(b)))
    def test_horizontal_sections(self):
        from pattern_garment import N,UP,DOWN
        case=CASES[0]
        p,q,l,g,a,b=mesh(case,"trimmed_rim")
        # Each front panel row after the shared upper rows has N+1 vertices.
        for j in range(1,DOWN):
            start=(UP+1)*(N+1)+(j-1)*(N+1)
            self.assertLess(max(v[2] for v in p[start:start+N+1])-min(v[2] for v in p[start:start+N+1]),1e-12)
    def test_side_turn_improves(self):
        for case in CASES:
            p,q,l,*_=mesh(case)
            v,f,r,*_=mesh(case,"trimmed_rim")
            self.assertLess(max(side_angles(v,r,case)),max(side_angles(p,l,case)))

def evidence():
    dest=Path("results/pattern_trim");dest.mkdir(parents=True,exist_ok=True)
    source=json.loads(Path("results/pattern_reimport/report.json").read_text())
    if not source["fixture_gate"]:raise ValueError("R12C source gate failed")
    cases=[]
    for case in CASES:
        r,(p,q,g)=compare(case,"trimmed_rim");cases.append(r)
        name=case[0]
        export_obj(dest/(name+"_candidate.obj"),p,q,g)
        tris=[t for f in q for t in ((f[0],f[1],f[2]),(f[0],f[2],f[3]))]
        for label,angle in (("front",0.),("side",math.pi/2),("back",math.pi)):
            side,lights=raster(p,tris,angle)
            png(dest/(name+"_"+label+".png"),side,lights,False)
    report=dict(complete=True,cases=cases,fixture_gate=all(c["passed"] for c in cases),
        original_preserved=True,visual_review_required=True,blender_verified=False,anatomical_fit_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213PATTERNTRIM_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
