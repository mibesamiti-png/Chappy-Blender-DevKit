import json,unittest
from pathlib import Path
from pattern_garment import CASES,mesh,N,UP,DOWN
from pattern_normal_diagnostic import locate,diagnose,face_band
from junction import audit

class NormalDiagnosticTests(unittest.TestCase):
    def test_location_matches_independent_audit(self):
        p,q,l,*_=mesh(CASES[0],"trimmed_rim")
        self.assertAlmostEqual(locate(p,q)[0]["angle"],audit(p,q,l,p)["max_normal_jump"])
    def test_known_right_angle(self):
        p=[(0,0,0),(1,0,0),(1,1,0),(0,1,0),(1,0,1),(0,0,1)]
        r=locate(p,[(0,1,2,3),(1,0,5,4)])
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]["edge"],[0,1])
        self.assertAlmostEqual(r[0]["angle"],90.)
        self.assertEqual(r[0]["midpoint"],[.5,0.,0.])
    def test_panel_indexing(self):
        n=N*(UP+DOWN)
        self.assertEqual(face_band(n-1),("front",UP+DOWN-1))
        self.assertEqual(face_band(n),("back",0))
        self.assertEqual(face_band(2*n),("crotch",0))

def evidence():
    dest=Path("results/pattern_normal_diagnostic");dest.mkdir(parents=True,exist_ok=True)
    results=[]
    for case in CASES:
        results.append(dict(name=case[0],methods=[diagnose(case,m) for m in ("original","round_rim","trimmed_rim")]))
    report=dict(complete=True,cases=results,geometry_changed=False,diagnostic_only=True)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    summary=[dict(name=c["name"],methods=[dict(method=m["method"],max_normal_jump=m["max_normal_jump"],high_angle_edges=m["high_angle_edges"],worst=m["worst"][0],regions=m["regions"]) for m in c["methods"]]) for c in results]
    print("PHASE213NORMALLOC_SUMMARY",json.dumps(summary,allow_nan=False))
if __name__=="__main__":evidence()
