"""Turn GLB comparison differences into review-only diagnostic hints."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

MAX_REPORT_BYTES = 8 * 1024 * 1024
RULES = {
    "scene_dimensions": ("global_scale_or_units", 90, 0.90, ["scene scale","unit conversion","root transform","export scale"]),
    "scene_center": ("root_origin_or_parent_transform", 80, 0.85, ["root object location","origin placement","parent transform","cursor/reference center"]),
    "object_dimensions": ("part_size_parameter", 95, 0.92, ["radius/diameter/length parameters","clearance/wall thickness","object scale","modifier dimensions"]),
    "object_center": ("part_placement_or_joint_center", 94, 0.92, ["joint center","hinge axis location","3D cursor placement","parent/local transform"]),
    "scene_silhouette": ("assembly_shape_mismatch", 85, 0.78, ["overall assembly layout","missing cuts","wrong orientation","unexpected overlaps"]),
    "object_silhouette": ("part_profile_boolean_or_cutout", 98, 0.95, ["boolean cutters","opening/profile","split shape","rib/tab/dowel geometry","rotation/orientation"]),
    "missing_reference_object": ("missing_generation_branch_or_mode", 100, 0.98, ["feature toggle","split/integrated mode","object creation branch","collection linking"]),
    "extra_candidate_object": ("unexpected_generation_or_cleanup", 88, 0.90, ["temporary cutters","duplicate generation","cleanup step","preview-only helpers"]),
    "object_topology": ("topology_or_modifier_difference", 55, 0.55, ["segments/resolution","modifier application","triangulation","mesh generation algorithm"]),
    "object_name_fallback": ("role_or_naming_mapping", 35, 0.60, ["object role names","left/right naming","generated suffixes","mapping metadata"]),
    "object_count": ("part_count_mismatch", 92, 0.90, ["split mode","duplicate generation","merge/join step","hidden generated objects"]),
}
class DiagnosticError(ValueError): pass

def _load(path):
    p=Path(path)
    if not p.is_file(): raise DiagnosticError(f"Comparison report not found: {p}")
    if p.stat().st_size>MAX_REPORT_BYTES: raise DiagnosticError("Comparison report exceeds safe size limit")
    try: data=json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc: raise DiagnosticError("Invalid comparison report") from exc
    if not isinstance(data,dict) or data.get("kind")!="cbdk_glb_scene_comparison":
        raise DiagnosticError("Expected cbdk_glb_scene_comparison report")
    return data

def _target(metrics:dict[str,Any])->str:
    for key in ("reference_object","object"):
        v=metrics.get(key)
        if isinstance(v,str) and v: return v
    view=metrics.get("view")
    return f"scene:{view}" if isinstance(view,str) and view else "scene"

def diagnose_comparison(report:dict)->dict:
    if report.get("kind")!="cbdk_glb_scene_comparison": raise DiagnosticError("Expected comparison report")
    diffs=report.get("differences")
    if not isinstance(diffs,list): raise DiagnosticError("comparison.differences must be an array")
    grouped={}; unsupported=[]
    for i,row in enumerate(diffs):
        if not isinstance(row,dict): raise DiagnosticError(f"difference[{i}] must be an object")
        code=row.get("code"); sev=row.get("severity"); metrics=row.get("metrics",{})
        if not isinstance(code,str) or not isinstance(sev,str) or not isinstance(metrics,dict):
            raise DiagnosticError(f"difference[{i}] is malformed")
        rule=RULES.get(code)
        if not rule:
            unsupported.append(code); continue
        cat,base,conf,inspect=rule
        boost={"error":20,"warning":8,"info":0}.get(sev,0)
        key=(_target(metrics),cat)
        item=grouped.get(key)
        if item is None:
            item={"target":key[0],"category":cat,"priority":min(100,base+boost),"confidence":conf,
                  "inspect":list(inspect),"source_codes":[code],"evidence_items":[metrics],"severities":[sev]}
            grouped[key]=item
        else:
            item["priority"]=max(item["priority"],min(100,base+boost))
            item["confidence"]=max(item["confidence"],conf)
            if code not in item["source_codes"]: item["source_codes"].append(code)
            item["evidence_items"].append(metrics); item["severities"].append(sev)
    ranked=sorted(grouped.values(),key=lambda x:(-x["priority"],-x["confidence"],x["target"],x["category"]))
    errors=report.get("summary",{}).get("errors")
    if not isinstance(errors,int) or isinstance(errors,bool) or errors<0: raise DiagnosticError("comparison.summary.errors is invalid")
    return {"schema_version":1,"kind":"cbdk_glb_diagnosis","comparison_passed":bool(report.get("passed")),
            "needs_review":errors>0 or bool(ranked),"hypothesis_count":len(ranked),
            "unsupported_difference_codes":sorted(set(unsupported)),"hypotheses":ranked,
            "recommended_next_step":"inspect_highest_priority_hypothesis_then_regenerate_candidate" if errors>0 else "no_geometry_fix_required_from_current_evidence",
            "safety":{"edits_code":False,"auto_approves":False,"auto_merges":False,"private_geometry_required":False}}

def diagnose_comparison_file(path): return diagnose_comparison(_load(path))
def write_diagnosis(path,output):
    report=diagnose_comparison_file(path); target=Path(output); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return report
