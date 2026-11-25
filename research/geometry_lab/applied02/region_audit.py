"""Independent straight-region measurement on actual evaluated triangles."""
import argparse,json
from pathlib import Path
import numpy as np
def section(v,f,y):
    pts=[]
    for t in v[f]:
        for a,b in zip(t,np.roll(t,-1,axis=0)):
            if (a[1]-y)*(b[1]-y)<0:
                q=a+(b-a)*((y-a[1])/(b[1]-a[1]));pts.append(q[[0,2]])
    if not pts:raise ValueError("empty cross section")
    p=np.array(pts);return np.r_[p.min(0),p.max(0)]
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--dir",required=True);a=p.parse_args();d=Path(a.dir)
    raw=json.loads((d/"raw.json").read_text());e=json.loads((d/"evaluation.json").read_text());rows={}
    for l,s in (("R",1),("L",-1)):
        m=raw["open"]["Temple_"+l];b=raw["temple_base"][l];v=np.array(m["vertices"]);f=np.array(m["triangles"],int)
        sections=np.array([section(v,f,y+.005) for y in (.015,.045,.075)])
        delta=float(np.max(np.abs(sections-sections[0])))
        bv=np.array(b["vertices"]).reshape(7,4,3)
        straight=float(np.max(np.abs(bv[1,:, [0,2]]-bv[0,:, [0,2]])))
        ok=bool(delta<1e-6 and straight<1e-8 and len(b["vertices"])==28 and len(b["faces"])==26 and all(len(x)==4 for x in b["faces"]) and set(b["materials"])=={0,1} and b["modifier_types"]==["BEVEL"] and "Tip_"+l not in raw["open"])
        rows[l]=dict(section_bounds_m=sections.tolist(),max_cross_section_delta_m=delta,base_straight_delta_m=straight,base_vertices=len(b["vertices"]),base_quads=len(b["faces"]),passed=ok)
    gate=bool(e["gate"] and all(r["passed"] for r in rows.values()) and e["evaluated_triangles"]<7424)
    result=dict(approved=False,gate=gate,rows=rows,evaluated_triangles=e["evaluated_triangles"],prior_evaluated_triangles=7424,limitations=["sampled evaluated cross-section bounding boxes, not arbitrary surface straightness proof","single material-separated cosmetic exterior, no physical core or sleeve containment","no automatic region inference","no UV or mechanical clearance guarantee"])
    (d/"region_evaluation.json").write_text(json.dumps(result,indent=2));print("APPLIED02_REGION",json.dumps(result),flush=True)
    if not gate:raise SystemExit("region gate unmet")
