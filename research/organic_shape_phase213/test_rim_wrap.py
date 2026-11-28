"""R9C: let leg openings reach the front/rear envelope charts.
Fixed chart masks, no separate lofts, keep standard side height.
"""
import math,json,unittest
from pathlib import Path
from cut_garment import base,inspect_cut
from fair_garment import fair,trial as source_trial,hem_metrics
from refinement import refine
from side_width import deform,widths
from intersection import audit as intersection_audit
from garment import edge_groups
from test_garment import preview

CASES=(("standard",4,14),("front_wrap",4,16),("rear_wrap",0,14),("both_wrap",0,16))

def extent(points,loops):
    result=[]
    for l in loops[1:]:
        a=[math.atan2(points[i][1],abs(points[i][0])) for i in l]
        result.append((max(a),-min(a)))
    return result

def generate(case,check_intersection=True,source=None):
    name,ylo,yhi=case
    if source is None:
        p,q,l,r=source_trial();assert r["fixture_gate"]
    else:p,q,l=source
    baseline=deform(p,l,.32)
    ref_extent=extent(baseline,l)
    if name=="standard":
        out,faces,loops=baseline,q,l
    else:
        p,q,l=base(ylo=ylo,yhi=yhi)
        a,faces,loops,_=refine(fair(p,q,l,12),q,l,"smooth")
        out=deform(a,loops,.32)
    m=inspect_cut(out,faces,loops,out)
    actual=extent(out,loops)
    changes=[[a-b for a,b in zip(x,y)] for x,y in zip(actual,ref_extent)]
    wrap_gate=all((f>=.10 if yhi==16 else abs(f)<=.12) and (b>=.10 if ylo==0 else abs(b)<=.12) for f,b in changes)
    actual_widths=widths(out,loops)
    hems=hem_metrics(out,loops)
    collision=intersection_audit(out,faces) if check_intersection else None
    passed=m["cut_pilot_pass"] and wrap_gate and max(abs(v-.32) for v in actual_widths)<=.015 and m["max_normal_jump"]<=30 and max(h["max_turn"] for h in hems)<=50 and collision is not None and collision["passed"]
    return dict(name=name,configuration=[ylo,yhi],baseline_extent=ref_extent,actual_extent=actual,extent_changes=changes,wrap_gate=wrap_gate,actual_widths=actual_widths,hems=hems,metrics=m,nonincident_intersection=collision,passed=passed),out,faces,loops

class RimWrapTests(unittest.TestCase):
    def test_chart_topology(self):
        from junction import audit
        for _,ylo,yhi in CASES:
            p,q,l=base(ylo=ylo,yhi=yhi)
            m=audit(p,q,l,p)
            self.assertTrue(m["topology_pass"],m)
            self.assertEqual(len(l),3)
    def test_fixed_plan(self):
        self.assertEqual(len(set(c[1:] for c in CASES)),4)
        p,q,l,r=source_trial();assert r["fixture_gate"]
        report,*_=generate(CASES[0],False,(p,q,l))
        self.assertFalse(report["passed"])
        self.assertEqual(report["extent_changes"],[[0.,0.],[0.,0.]])

def evidence():
    dest=Path("results/rim_wrap");dest.mkdir(parents=True,exist_ok=True)
    p,q,l,r=source_trial();assert r["fixture_gate"]
    results=[]
    for case in CASES:
        result,a,b,c=generate(case,True,(p,q,l));results.append(result)
        name=case[0];groups=edge_groups(b,c)
        with (dest/(name+".obj")).open("w") as out:
            out.write("# Static chart wrap pilot\n")
            for v in a:out.write("v "+" ".join(format(x,".12g") for x in v)+"\n")
            prev=None
            for f,role in zip(b,groups):
                if role!=prev:out.write("g "+role+"\n");prev=role
                out.write("f "+" ".join(str(i+1) for i in f)+"\n")
        preview(dest/(name+"_preview.svg"),a,b,groups)
    report=dict(complete=True,cases=results,fixture_gate=all(r["passed"] for r in results),
        global_intersection_verified=False,lower_body_fit_verified=False,blender_verified=False,visual_review_required=True)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213WRAP_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":evidence()
