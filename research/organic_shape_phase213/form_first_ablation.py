"""R13C: one frozen ablation of R13B initialization, same fairing and target."""
import json
from pathlib import Path
from form_first_pilot import (extract, fair, measure, render, mask, compare_masks,
    export, LEVEL, RES, VIEWS, W, H)
from visibility_diagnostic import png

def main():
    root=Path("results/form_first")
    src=json.loads((root/"report.json").read_text())
    if not src["complete"] or not src["control_pass"]:
        raise ValueError("R13B evidence gate failed")
    rows={c["name"]:c for c in src["cases"]}
    if set(rows)!={"direct","offset","fair_project"}:
        raise ValueError("unexpected source comparison")
    dest=root/"ablation";dest.mkdir(parents=True,exist_ok=True)
    p,q=extract(LEVEL,RES)
    v=fair(p,q)
    reference,tq=extract(LEVEL,tuple(2*x for x in RES))
    export(dest/"direct_fair.obj",v,q)
    r=measure(v,q);views={}
    for label,angle in VIEWS:
        side,light=render(v,q,angle)
        target,_=render(reference,tq,angle)
        png(dest/("direct_fair_"+label+".png"),side,light,False,width=W,height=H)
        views[label]=compare_masks(mask(side),mask(target))
    r.update(name="direct_fair",views=views,
             passes_numeric_gate=r["geometry_pass"] and all(x["iou"]>=.9 for x in views.values()),
             connectivity_preserved=True)
    f=rows["fair_project"]
    def worst_iou(c):return min(x["iou"] for x in c["views"].values())
    comparison=dict(iou_delta=worst_iou(r)-worst_iou(f),
        residual_ratio=r["sampled_field_residual_p95"]/f["sampled_field_residual_p95"],
        quality_ratio=r["quality_p05"]/f["quality_p05"],
        normal_p95_ratio=r["normal_jump_p95"]/f["normal_jump_p95"],
        max_normal_jump_direct_fair=r["normal_jump_max"],
        max_normal_jump_reference_fair=f["normal_jump_max"])
    comparable=(r["passes_numeric_gate"] and f["passes_numeric_gate"]
        and comparison["iou_delta"]>=-.001 and comparison["residual_ratio"]<=1.2
        and comparison["quality_ratio"]>=.9 and comparison["normal_p95_ratio"]<=1.1)
    report=dict(complete=True,candidate=r,comparison=comparison,comparable=comparable,
        same_target=True,same_fairing=True,synthetic_one_fixture=True,
        visual_review_required=True,blender_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213FORMFIRSTABLATION_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":main()
