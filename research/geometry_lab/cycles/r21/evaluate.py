"""R21 final actual Blender Mesh assessment, independent of proposed array indexing."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from cbdk_geometry import Mesh
from cycles.r7.evaluate import assess
from cycles.r14.audit import incidence,controls
from cycles.r18.evaluate import eval_row
from cycles.r20.refine import normals,angles
from cycles.r17.refine import seam_set
from cycles.r21.fixtures import cases

def canon(v,f,uv,ids,mats,mask):
    result=[]
    for i in np.flatnonzero(mask):
        trip=[(tuple(v[k]),tuple(uv[i,j])) for j,k in enumerate(f[i])]
        result.append((int(ids[i]),int(mats[i]),min(tuple(trip[j:]+trip[:j]) for j in range(3))))
    return sorted(result)

def arrays(row):
    return (np.asarray(row["vertices"],np.float32).astype(float),np.asarray(row["triangles"],int),np.asarray(row["corner_uv"],np.float32).astype(float),np.asarray(row["face_ids"],int),np.asarray(row["materials"],int))

def bridge_metrics(v,f,ids):
    chosen=f[ids<0]; used=sorted(set(chosen.ravel())); idx={k:i for i,k in enumerate(used)}
    return v[used],np.array([[idx[k] for k in t] for t in chosen])

def internal(v,f,ids):
    p=[rs for rs in incidence(f).values() if len(rs)==2 and ids[rs[0]]<0 and ids[rs[1]]<0]
    return angles(normals(v,f),p)

def evaluate(row,prep,base,case):
    if prep["status"]!="prepared": raise ValueError(prep.get("error","missing selected"))
    q=eval_row(row,prep,case); old=prep["baseline_audit"]; x=prep["selected"]
    v,f,u,i,m=arrays(row); bv,bf,bu,bi,bm=arrays(base); xv,xf,xu,xi,xm=arrays(x)
    source_exact=canon(v,f,u,i,m,i>0)==canon(bv,bf,bu,bi,bm,bi>0)
    all_exact=canon(v,f,u,i,m,np.ones(len(i),bool))==canon(xv,xf,xu,xi,xm,np.ones(len(xi),bool))
    def edge_coords(v,edges): return {tuple(sorted((tuple(v[a]),tuple(v[b])))) for a,b in edges}
    flags_exact=edge_coords(v,row["seam_flags"])==edge_coords(xv,x["seam_flags"])
    # Original source/seam UV pins checked via original indexed R20 arrays, then actual exact roundtrip.
    if not np.array_equal(xf,bf) or not np.array_equal(xi,bi) or not np.array_equal(xm,bm): raise ValueError("selected connectivity or metadata changed")
    pinned=set(bf[bi>0].ravel())
    seam=seam_set(bf,bu); pins=pinned|{k for e in seam for k in e}
    mask=np.isin(bf,list(pins))
    pins_exact=bool(np.array_equal(xv[sorted(pinned)],bv[sorted(pinned)]) and np.array_equal(xu[mask],bu[mask]) and seam_set(xf,xu)==seam)
    sv,sf=bridge_metrics(v,f,i); osv,osf=bridge_metrics(bv,bf,bi)
    g=assess(Mesh(sv,sf),case); og=assess(Mesh(osv,osf),case)
    a=q["normals"]; b=old["normals"]; ia=internal(v,f,i); ib=internal(bv,bf,bi)
    gain=1-a["p95_deg"]/b["p95_deg"]
    normal_ok=all(a[k]<=b[k]+1e-8 for k in ("mean_deg","p95_deg","max_deg")) and ia["p95_deg"]<=1.05*ib["p95_deg"]+1e-8 and ia["max_deg"]<=ib["max_deg"]+5
    uv_ok=all(q[t][k]<=old[t][k]+1e-6 for t in ("full_uv","strip_uv") for k in ("anisotropy_p95","anisotropy_max"))
    quality_ok=g["status"]==og["status"]=="passed" and g["quality"]["min_triangle_quality"]>=max(.1,.9*og["quality"]["min_triangle_quality"])
    passed=bool(q["passed"] and source_exact and all_exact and flags_exact and pins_exact and normal_ok and uv_ok and quality_ok)
    return dict(case=row["case"],passed=passed,source_exact=source_exact,all_triangles_exact=all_exact,seam_flags_exact=flags_exact,pins_exact=pins_exact,normal_ok=normal_ok,uv_ok=uv_ok,quality_ok=quality_ok,p95_gain=gain,before=b,after=a,method=x["method"],rescued=x["rescued"],uv_attempts=x["uv_attempts"],joined_cgal_pairs=q["joined_cgal_pairs"],full_overlap=q["full_uv"]["overlap_pairs"],roundtrip_error=q["bridge_uv_roundtrip_error"],baseline_audit=old,final_audit=q)

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--raw",required=True); p.add_argument("--baseline",required=True); p.add_argument("--output",required=True); a=p.parse_args()
    path=Path(a.input); selected=json.loads(path.read_text()); raw=json.loads(Path(a.raw).read_text()); base=json.loads(Path(a.baseline).read_text())
    if raw["input_sha256"]!=hashlib.sha256(path.read_bytes()).hexdigest() or raw["blender"]!="4.4.3": raise ValueError("selected provenance")
    controls(); by={r["case"]:r for r in selected["rows"]}; orig={r["case"]:r for r in base["rows"]}; cb={c["name"]:c for c in cases()}; rows=[]
    for r in raw["rows"]:
        try: q=evaluate(r,by[r["case"]],orig[r["case"]],cb[r["case"]])
        except Exception as e: q=dict(case=r["case"],passed=False,error=type(e).__name__+": "+str(e))
        rows.append(q); print("R21_ROW",json.dumps({k:v for k,v in q.items() if k not in ("baseline_audit","final_audit")}),flush=True)
    n=sum(r.get("p95_gain",0)>=.05 and r["passed"] for r in rows)
    gate=len(rows)==8 and len({r["case"] for r in rows})==8 and set(r["case"] for r in rows)==set(cb) and all(r["passed"] for r in rows) and n>=4
    with Path(a.output).open("x") as f: json.dump(dict(cycle="R21",approved=False,synthetic_only=True,gate=gate,improved=n,rows=rows),f,indent=2,allow_nan=False)
    print("R21_SUMMARY",json.dumps(dict(gate=gate,passed=sum(r["passed"] for r in rows),total=len(rows),improved=n)),flush=True)
    if not gate: raise SystemExit("R21 gate failed; preserve evidence")
