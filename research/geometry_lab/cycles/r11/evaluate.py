"""R11 independent Python3.12 CGAL oracle + Blender attribute round-trip audit.

Blender runner does not execute CGAL. Both bridge strip and combined sleeve
geometry are independently evaluated; full CGAL defects are not hidden.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
from cbdk_geometry import Mesh
from cycles.r2.oracle import mesh_hits
from cycles.r7.evaluate import assess
from cycles.r11.fixtures import cases

ROOT=Path(__file__).resolve().parents[2]
ARMS=("r11_attribute_adapter","r11_zero_uv_control")


def evaluate(raw,dev_smoke=False):
    if raw.get("cycle")!="R11" or not raw.get("synthetic_only"):
        raise ValueError("R11 synthetic provenance required")
    fixtures={(c["name"],c["uv_mode"]):c for c in cases()
              if not dev_smoke or c["split"]=="development"}
    expected={(name,uv_mode,arm) for name,uv_mode in fixtures for arm in ARMS}
    seen=set()
    results=[]
    for r in raw["cases"]:
        k=(r["case"],r["uv_mode"],r["arm"])
        if k not in expected or k in seen:raise ValueError("R11 unexpected/repeated arm")
        seen.add(k)
        entry={x:y for x,y in r.items()
               if x not in ("strip_vertices","strip_faces",
                            "complete_vertices","complete_triangles")}
        if r["status"]!="generated":
            entry["audit_status"]="generation_error"
        else:
            try:
                strip=Mesh(r["strip_vertices"],r["strip_faces"])
                combined=Mesh(r["complete_vertices"],r["complete_triangles"])
                strip_hits=mesh_hits(strip)
                complete_hits=mesh_hits(combined)
                geo=assess(strip,fixtures[(r["case"],r["uv_mode"])])
                entry.update(
                    strip_cgal_pairs=len(strip_hits),
                    joined_cgal_pairs=len(complete_hits),
                    strip_quality_passed=(geo["status"]=="passed"),
                    strip_min_triangle_quality=geo["quality"]["min_triangle_quality"],
                    full_triangles=len(combined.faces),
                    original_border_preserved_independent=geo["original_boundary_edges_preserved"],
                    strip_topology_valid=geo["topology_valid"],
                )
                core_ok=(r["original_source_signature_unchanged"]
                         and r["source_boundary_unchanged"]
                         and r["bridge_triangle_count"]==r["expected_bridge_triangle_count"]
                         and r["shared_source_to_bridge_edges"]==r["original_boundary_vertices"]
                         and r["outer_boundary_edges"]==r["original_boundary_vertices"]
                         and r["nonmanifold_edges"]==0
                         and r["scene_restored"]
                         and len(strip_hits)==0)
                has_attributes=(r["bridge_material_2"]
                                and r["bridge_uv_finite_and_nonzero_bounded"])
                continuous=(r["uv_mode"]=="continuous")
                detected_seam=(r["max_boundary_uv_gap"]>.05)
                continuous_ok=r["max_boundary_uv_gap"]<=1e-6
                if r["arm"]=="r11_attribute_adapter":
                    ok=(core_ok and has_attributes and
                        (continuous_ok if continuous else detected_seam))
                    entry["audit_status"]="passed" if ok else "failed"
                else:
                    negative_detected=(not has_attributes and not r["bridge_material_2"])
                    entry["audit_status"]="negative_detected" if core_ok and negative_detected else "negative_control_failed"
                entry["core_integrity"]=bool(core_ok)
                entry["new_bridge_attributes_assigned"]=bool(has_attributes)
                entry["boundary_uv_continuity"]=bool(continuous_ok)
                entry["uv_island_incompatibility_detected"]=bool(detected_seam)
                entry["complete_mesh_cgal_clear"]=bool(len(complete_hits)==0)
            except Exception as exc:
                entry.update(audit_status="oracle_unavailable",
                             reason=type(exc).__name__+": "+str(exc))
        results.append(entry)
        print("R11_RESULT",json.dumps({x:entry.get(x) for x in
            ("case","uv_mode","arm","audit_status",
             "strip_cgal_pairs","joined_cgal_pairs","max_boundary_uv_gap")}),flush=True)
    if seen!=expected:raise ValueError("R11 missing arm/fixture")

    summary={}
    for split in ("development","holdout"):
        summary[split]={}
        for arm in ARMS:
            items=[r for r in results if r["split"]==split and r["arm"]==arm]
            summary[split][arm]=dict(
                total=len(items),
                passed=sum(x["audit_status"]=="passed" for x in items),
                negative_detected=sum(x["audit_status"]=="negative_detected" for x in items),
                failed=sum(x["audit_status"] not in ("passed","negative_detected") for x in items),
                combined_cgal_crossings=sum(x.get("joined_cgal_pairs",0) for x in items))
    candidates=[r for r in results if r["arm"]=="r11_attribute_adapter"]
    negatives=[r for r in results if r["arm"]=="r11_zero_uv_control"]
    all_checked=all(r["audit_status"]!="oracle_unavailable" for r in results)
    audited=all(r["audit_status"]=="passed" for r in candidates)
    controls=all(r["audit_status"]=="negative_detected" for r in negatives)
    combined_clean=all(r.get("joined_cgal_pairs")==0 for r in candidates)
    strip_clean=all(r.get("strip_cgal_pairs")==0 for r in candidates)
    base_successes=sum(r.get("strip_quality_passed") is True for r in candidates)
    result=dict(cycle="R11",dev_smoke=dev_smoke,blender=raw["blender"],
                cgal=version("cgal"),synthetic_only=True,
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                 for p in ("cycles/r11/fixtures.py","cycles/r11/blender_run.py",
                           "cycles/r11/evaluate.py")},
                blender_generator_source_sha256=raw["source_sha256"],
                cases=results,summary=summary,
                attribute_audit_gate_met=bool(all_checked and audited and controls and strip_clean),
                whole_mesh_cgal_gate_met=bool(combined_clean),
                strip_quality_successes=base_successes,
                full_combined_mesh_intersection_total=sum(r.get("joined_cgal_pairs",0) for r in candidates),
                approved=False,
                decision=("blocked_oracle" if not all_checked else
                          "attribute_audit_passed_with_full_mesh_cgal_clear"
                          if audited and controls and strip_clean and combined_clean else
                          "audit_or_assembled_geometry_failed"),
                caveat="Synthetic collars + convenient UV projection only. Split UV islands deliberately mismatch; normal/UV material workflow unapproved.")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--development-only",action="store_true")
    args=p.parse_args()
    inp=Path(args.input)
    result=evaluate(json.loads(inp.read_text()),dev_smoke=args.development_only)
    result["raw_sha256"]=hashlib.sha256(inp.read_bytes()).hexdigest()
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x") as f:json.dump(result,f,indent=2)
    print("R11_SUMMARY",json.dumps({k:result[k] for k in
        ("summary","attribute_audit_gate_met","whole_mesh_cgal_gate_met",
         "strip_quality_successes","full_combined_mesh_intersection_total",
         "decision")}),flush=True)
    if result["decision"]=="blocked_oracle":
        raise SystemExit("R11 incomplete independent CGAL evaluation")
