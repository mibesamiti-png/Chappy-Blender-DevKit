"""Compare actual Blender triangle UVs with frozen uniform chart at identical XYZ."""
import argparse,json
from pathlib import Path
import numpy as np
from applied01.generate import generate
from cycles.r14.audit import uv_audit
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--dir",required=True);a=p.parse_args();d=Path(a.dir)
    raw=json.loads((d/"raw.json").read_text());e=json.loads((d/"evaluation.json").read_text())
    rows=[]
    for arm,parts in (("baseline",generate()),("changed",generate(.075))):
        for p in parts:
            name=p["name"];m=raw[arm][name];v=np.asarray(m["vertices"]);f=np.asarray(m["triangles"])
            same=np.array_equal(v.astype(np.float32),np.array(p["vertices"],np.float32)) and m["quads"]==p["faces"]
            old=uv_audit(v,f,np.asarray(p["uv"],np.float32)[f]);new=uv_audit(v,f,m["corner_uv"])
            before=old["anisotropy_p95"];after=new["anisotropy_p95"]
            passed=bool(same and new["overlap_pairs"]==0 and new["mixed_winding_islands"]==0 and new["degenerate_uv"]==0 and new["islands"]==1 and after<=before+1e-6 and (not name.startswith("strap") or after<=.1*before) and (name!="band" or after<=.1*before))
            rows.append(dict(arm=arm,part=name,before=before,after=after,relative_gain=1-after/before,geometry_exact=bool(same),passed=passed))
    gate=bool(e["gate"] and len(rows)==14 and all(r["passed"] for r in rows))
    result=dict(approved=False,gate=gate,rows=rows,limitations=["per-panel metric chart, no packed atlas or uniform global texel density","same known synthetic garment, not holdout","strap residual anisotropy remains","no thickness cross-part clearance or fit claims"])
    (d/"uv_comparison.json").write_text(json.dumps(result,indent=2));print("PILOT_UV_SUMMARY",json.dumps(result),flush=True)
    if not gate:raise SystemExit("UV correction gate unmet")
