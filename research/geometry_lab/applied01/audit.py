"""Independent per-panel topology, actual UV/CGAL, dependency and contact checks."""
import argparse,json,itertools,math
from pathlib import Path
from collections import Counter
import numpy as np
from cbdk_geometry import Mesh
from cycles.r2.oracle import mesh_hits,triangle_hit
from cycles.r14.audit import uv_audit

def hits_between(a,b):
    x=np.asarray(a["vertices"])[a["triangles"]];y=np.asarray(b["vertices"])[b["triangles"]]
    lo=y.min(1);hi=y.max(1);n=0
    for t in x:
        ids=np.flatnonzero(np.all(hi>=t.min(0),axis=1)&np.all(lo<=t.max(0),axis=1))
        n+=sum(triangle_hit(t.tolist(),y[i].tolist()) for i in ids)
    return n
def topology(v,f,closed):
    e=Counter(tuple(sorted((a,b))) for t in f for a,b in zip(t,t[1:]+t[:1]))
    assert all(n in (1,2) for n in e.values())
    assert (sum(n==1 for n in e.values())==0)==closed
    assert len(v)-len(e)+len(f)==(2 if closed else 1)
    return len(e)
def gap(a,b):
    return float(np.max(np.linalg.norm(np.asarray(a)-np.asarray(b),axis=1)))
def edges(r):
    band=r["band"]["vertices"]; n=len(band)//4; top=np.array(band[-n:])
    out={}
    for label in ("R","L"):
        c=np.array(r["cup_"+label]["vertices"]).reshape(9,17,3)
        s=np.array(r["strap_"+label]["vertices"]).reshape(25,2,3)
        out["cup_band_"+label]=max(float(np.min(np.linalg.norm(top-p,axis=1))) for p in c[0])
        out["strap_cup_"+label]=gap(s[0],c[-1,12:14])
        out["strap_band_"+label]=max(float(np.min(np.linalg.norm(top-p,axis=1))) for p in s[-1])
        bridge=np.array(r["bridge"]["vertices"]).reshape(9,5,3)
        out["bridge_cup_"+label]=gap(bridge[:,-1 if label=="R" else 0],c[:,0])
    out["bridge_band"]=max(float(np.min(np.linalg.norm(top-p,axis=1))) for p in r["bridge"]["vertices"][:5])
    closure=np.array(r["closure"]["vertices"]).reshape(4,5,3);band=np.array(band).reshape(4,n,3)
    out["closure_band_R"]=gap(closure[:,0],band[:,-1])
    out["closure_band_L"]=gap(closure[:,-1],band[:,0])
    return out
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--dir",required=True);a=p.parse_args();d=Path(a.dir)
    raw=json.loads((d/"raw.json").read_text());spec=json.loads((d/"spec.json").read_text());summary={};allok=True
    allowed={frozenset(x.split("+")) for x in ("band+bridge","band+cup_R","band+cup_L","band+strap_R","band+strap_L","band+closure","bridge+cup_R","bridge+cup_L","cup_R+strap_R","cup_L+strap_L")}
    for arm,r in raw.items():
        parts={};expected={p["name"]:p for p in spec[arm]};assert set(r)==set(expected)
        for name,m in r.items():
            v=m["vertices"];f=m["triangles"];ev=m["evaluated_vertices"];ef=m["evaluated_triangles"]
            topology(v,f,False);topology(ev,ef,True)
            exact=np.array_equal(np.array(v,np.float32),np.array(expected[name]["vertices"],np.float32)) and m["quads"]==expected[name]["faces"]
            uv=uv_audit(v,f,m["corner_uv"]);base=mesh_hits(Mesh(np.asarray(v,float),np.asarray(f,int)));thick=mesh_hits(Mesh(np.asarray(ev,float),np.asarray(ef,int)))
            ok=bool(exact and not base and not thick and uv["overlap_pairs"]==0 and uv["degenerate_uv"]==0 and uv["mixed_winding_islands"]==0 and uv["islands"]==1)
            parts[name]=dict(vertices=len(v),quads=len(m["quads"]),evaluated_triangles=len(ef),base_hits=len(base),thick_hits=len(thick),uv_overlap=uv["overlap_pairs"],uv_p95=uv["anisotropy_p95"],exact=bool(exact),passed=ok);allok &= ok
        gaps=edges(r);contacts={};unexpected={}
        for x,y in itertools.combinations(r,2):
            count=hits_between(r[x],r[y])
            if count:
                contacts[x+"+"+y]=count
                if frozenset((x,y)) not in allowed:unexpected[x+"+"+y]=count
        allok &= max(gaps.values())<1e-6 and not unexpected
        summary[arm]=dict(parts=parts,gaps=gaps,base_cross_part_contacts=contacts,unexpected_pair_contacts=unexpected)
    changed=[k for k in raw["baseline"] if raw["baseline"][k]["vertices"]!=raw["changed"][k]["vertices"]]
    dependent=set(changed)=={"cup_R","strap_R"};allok &= dependent
    result=dict(approved=False,gate=bool(allok),arms=summary,changed_parts=changed,dependency_pass=dependent,limitations=["cross-part base contact allowlist is not proof of seam-only contact or thickness clearance","separate per-panel UVs not global atlas","parameter regeneration not interactive dependency graph","no fit or aesthetics verdict"])
    (d/"evaluation.json").write_text(json.dumps(result,indent=2));print("PILOT_SUMMARY",json.dumps(result),flush=True)
    if not allok:raise SystemExit("pilot gate unmet")
