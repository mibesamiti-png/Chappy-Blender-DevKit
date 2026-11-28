"""R8: predeclared unseen synthetic shape/configuration combinations.
No per-case tuning, no retry with changed gates.
"""
import json,unittest
from pathlib import Path
from fitting import Target
from cut_garment import base,round_hem,inspect_cut
from fair_garment import fair,hem_metrics
from refinement import refine
from intersection import audit as intersection_audit
from garment import edge_groups
from test_garment import preview

# name, hip/depth/rear shift, waist height, lower depth, cut extent, rear/front range
CASES=(
    ("wide_high",(.45,.18,.06),.50,.84,6,4,14),
    ("deep_low",(.28,.32,.14),.30,.91,6,4,14),
    ("high_cut",(.35,.24,.09),.42,.80,7,3,14),
    ("full_coverage",(.26,.16,.04),.46,.76,4,5,12),
    ("combined_holdout",(.39,.29,.12),.34,.88,5,3,13),
)
def trial(case,check_intersection=True):
    name,params,waist,depth,cut,ylo,yhi=case
    target=Target(*params)
    p,q,l=base(target,waist,depth,cut,ylo,yhi)
    r,s,t,_=refine(round_hem(p,l),q,l,"smooth")
    reference=hem_metrics(r,t)
    # Apply the successful R7D recipe exactly once, without a fallback search.
    out,faces,loops,ref=refine(fair(p,q,l,12),q,l,"smooth")
    m=inspect_cut(out,faces,loops,ref,target)
    hems=hem_metrics(out,loops)
    hem_gate=all(h["max_turn"]<=.9*b["max_turn"] and h["turn_energy"]<=b["turn_energy"] and .8<=h["projected_area"]/b["projected_area"]<=1.2 for h,b in zip(hems,reference))
    collisions=intersection_audit(out,faces) if check_intersection else None
    gate=m["cut_pilot_pass"] and hem_gate and collisions is not None and collisions["passed"]
    return dict(name=name,configuration=list(case[1:]),metrics=m,reference_hems=reference,hems=hems,hem_gate=hem_gate,nonincident_intersection=collisions,passed=gate),out,faces,loops

class VariationTests(unittest.TestCase):
    def test_explicit_default_is_unchanged(self):
        from garment import TARGET
        self.assertEqual(base(),base(TARGET,.40,.82,6,4,14))
    def test_configurations(self):
        self.assertEqual(len(set(c[1:] for c in CASES)),5)
        for case in CASES:
            r,p,q,l=trial(case,False)
            self.assertTrue(r["metrics"]["topology_pass"],r)
            self.assertEqual(len(l),3)
            self.assertIsNone(r["nonincident_intersection"])
            self.assertFalse(r["passed"])
    def test_reject_invalid(self):
        for kwargs in (dict(cut=8),dict(waist=.7),dict(depth=.2),dict(ylo=0),dict(yhi=16)):
            with self.assertRaises(ValueError):base(**kwargs)

def evidence():
    dest=Path("results/r8");dest.mkdir(parents=True,exist_ok=True)
    results=[]
    for case in CASES:
        result,p,q,l=trial(case);results.append(result)
        groups=edge_groups(q,l)
        with (dest/(case[0]+".obj")).open("w") as out:
            out.write("# R8 fixed synthetic variation; open quad surface\n")
            for v in p:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            prev=None
            for f,role in zip(q,groups):
                if role!=prev:out.write("g "+role+"\n");prev=role
                out.write("f "+" ".join(str(i+1) for i in f)+"\n")
        preview(dest/(case[0]+"_preview.svg"),p,q,groups)
    report=dict(complete=True,cases=results,fixture_gate=all(r["passed"] for r in results),
        global_intersection_verified=False,lower_body_fit_verified=False,blender_verified=False,visual_review_required=True)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213R8_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
