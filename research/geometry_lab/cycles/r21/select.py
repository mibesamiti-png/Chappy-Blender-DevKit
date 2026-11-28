"""Audit baseline real Mesh then run unchanged R20 and extract final strip."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from cycles.r18.evaluate import eval_row
from cycles.r20.refine import refine
from cycles.r21.fixtures import cases

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--raw",required=True); p.add_argument("--output",required=True); a=p.parse_args()
    path=Path(a.input); prior=json.loads(path.read_text()); raw=json.loads(Path(a.raw).read_text())
    if raw["input_sha256"]!=hashlib.sha256(path.read_bytes()).hexdigest() or raw["blender"]!="4.4.3": raise ValueError("baseline provenance")
    by={r["case"]:r for r in prior["rows"]}; fixtures={c["name"]:c for c in cases()}; rows=[]
    for r in raw["rows"]:
        name=r["case"]
        try:
            q=eval_row(r,by[name],fixtures[name])
            if not q["passed"]: raise ValueError("baseline R18 gate")
            x=refine(r,fixtures[name])
            if not x["passed"]: raise ValueError("R20 selected output failed")
            f=np.asarray(x["triangles"],int); v=np.asarray(x["vertices"],float); uv=np.asarray(x["corner_uv"],float)
            ids=np.asarray(x["face_ids"],int); bridge=np.flatnonzero(ids<0)
            bridge=bridge[np.argsort(-ids[bridge])]
            used=sorted(set(f[bridge].ravel())); mapping={k:i for i,k in enumerate(used)}
            sf=[[mapping[int(k)] for k in t] for t in f[bridge]]
            result=dict(case=name,status="prepared",vertices=v[used].tolist(),faces=sf,candidate_uv=uv[bridge].tolist(),seams=by[name]["seams"],selected=x,baseline_audit=q)
        except Exception as e: result=dict(case=name,status="error",error=type(e).__name__+": "+str(e))
        rows.append(result); print("R21_SELECT",name,result["status"],result.get("error",""),result.get("selected",{}).get("method",""),flush=True)
    with Path(a.output).open("x") as f: json.dump(dict(cycle="R21",stage="selected",approved=False,rows=rows),f,allow_nan=False)
