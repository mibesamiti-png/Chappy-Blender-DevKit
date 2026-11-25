"""R18 independent joined UV/CGAL audit of actual Blender Mesh loop triangles."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from cbdk_geometry import Mesh
from cycles.r2.oracle import mesh_hits
from cycles.r14.audit import uv_audit,incidence,controls,boundary_normals
from cycles.r16.cut_uv import source_loop
from cycles.r17.fixtures import cases

def eval_row(row,prior,case):
    if row["status"]!="generated": raise ValueError(row.get("reason","generation error"))
    v=np.asarray(row["vertices"],float); f=np.asarray(row["triangles"],int); uv=np.asarray(row["corner_uv"],float)
    ids=np.asarray(row["face_ids"],int); mats=np.asarray(row["materials"],int)
    refv=np.asarray(prior["vertices"],np.float32); reff=np.asarray(prior["faces"],int)
    refuv=np.asarray(prior[row["arm"]+"_uv"],np.float32)
    lookup={tuple(p):i for i,p in enumerate(v.astype(np.float32))}
    if len(lookup)!=len(v): raise ValueError("duplicate joined coordinates")
    mapping=np.array([lookup[tuple(p)] for p in refv]); target=mapping[reff]
    seen=set(); errors=[]
    for i in np.flatnonzero(ids<0):
        k=-ids[i]-1
        if k in seen or k>=len(target): raise ValueError("duplicate/invalid bridge face tag")
        seen.add(k)
        if set(f[i])!=set(target[k]): raise ValueError("bridge geometry changed")
        for j,key in enumerate(f[i]): errors.append(float(np.max(np.abs(uv[i,j]-refuv[k,np.flatnonzero(target[k]==key)[0]]))))
    if len(seen)!=len(reff): raise ValueError("missing bridge triangle")
    lo=source_loop(case["a"],0.); hi=source_loop(case["b"],1.)
    boundary_pins={tuple(sorted((lookup[tuple(np.float32(x))],lookup[tuple(np.float32(y))]))):{lookup[tuple(np.float32(x))]:ux,lookup[tuple(np.float32(y))]:uy} for x,y,ux,uy in lo+hi}
    edges=incidence(f); gap=[]; pin_error=[]
    flags={tuple(sorted(e)) for e in row["seam_flags"]}; actual=set(); cross=0; source_seams=0; bridge_seams=0
    for e,refs in edges.items():
        if len(refs)!=2: continue
        i,j=refs; p=dict(zip(f[i],uv[i])); q=dict(zip(f[j],uv[j]))
        d=max(float(np.max(np.abs(p[k]-q[k]))) for k in e)
        if d>1e-5:
            actual.add(e)
            if ids[i]<0 and ids[j]<0: bridge_seams+=1
            elif ids[i]>0 and ids[j]>0: source_seams+=1
        if (ids[i]<0)!=(ids[j]<0):
            cross+=1; gap.append(d)
            for k,pin in boundary_pins[e].items(): pin_error.extend([float(np.max(np.abs(p[k]-pin))),float(np.max(np.abs(q[k]-pin)))])
    if cross!=len(boundary_pins): raise ValueError("source/bridge edge count mismatch")
    full=uv_audit(v,f,uv); full.pop("signed_areas")
    # Use original strip index space for the bridge-only audit; actual rounded UVs.
    new=np.zeros_like(refuv)
    for i in np.flatnonzero(ids<0):
        k=-ids[i]-1
        for j,key in enumerate(f[i]): new[k,np.flatnonzero(target[k]==key)[0]]=uv[i,j]
    strip=uv_audit(refv,reff,new); strip.pop("signed_areas")
    hits=len(mesh_hits(Mesh(v,f)))
    normals=boundary_normals(refv,reff,v,f)
    material_ok=bool(np.all(mats[ids<0]==2) and np.all(mats[ids>0]<2))
    ok=bool(row["source_preserved"] and row["scene_restored"] and max(errors)==0 and max(gap)<=1e-6 and max(pin_error)<=1e-6 and material_ok and actual==flags and bridge_seams==prior["seams"] and source_seams==2 and hits==0 and full["overlap_pairs"]==0 and full["mixed_winding_islands"]==0 and full["degenerate_uv"]==0 and full["islands"]==1 and strip["overlap_pairs"]==0 and strip["mixed_winding_islands"]==0 and strip["degenerate_uv"]==0 and strip["islands"]==1)
    return dict(case=row["case"],arm=row["arm"],passed=ok,source_preserved=row["source_preserved"],scene_restored=row["scene_restored"],source_pin_error=max(pin_error),bridge_uv_roundtrip_error=max(errors),boundary_gap=max(gap),seam_flags_match=actual==flags,bridge_seams=bridge_seams,source_seams=source_seams,source_edges=cross,materials_ok=material_ok,joined_cgal_pairs=hits,full_uv=full,strip_uv=strip,normals=normals)

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--raw",required=True); p.add_argument("--output",required=True); a=p.parse_args()
    inp=Path(a.input); prior=json.loads(inp.read_text()); raw=json.loads(Path(a.raw).read_text())
    if raw["input_sha256"]!=hashlib.sha256(inp.read_bytes()).hexdigest() or raw["blender"]!="4.4.3" or raw["approved"]: raise ValueError("provenance")
    controls(); by={r["case"]:r for r in prior["rows"]}; cb={c["name"]:c for c in cases()}
    rows=[]; seen=set()
    for r in raw["rows"]:
        k=(r["case"],r["arm"])
        if k in seen or k[1] not in ("baseline","candidate"): raise ValueError("duplicate/unknown")
        seen.add(k)
        try: o=eval_row(r,by[k[0]],cb[k[0]])
        except Exception as exc: o=dict(case=k[0],arm=k[1],passed=False,error=type(exc).__name__+": "+str(exc))
        rows.append(o); print("R18_ROW",json.dumps(o),flush=True)
    gate=len(rows)==24 and all(r["passed"] for r in rows)
    out=dict(cycle="R18",approved=False,retrospective=True,gate=gate,rows=rows)
    with Path(a.output).open("x") as f: json.dump(out,f,indent=2,allow_nan=False)
    print("R18_SUMMARY",json.dumps(dict(gate=gate,passed=sum(r["passed"] for r in rows),total=len(rows))),flush=True)
    if not gate: raise SystemExit("R18 integration gate failed")
