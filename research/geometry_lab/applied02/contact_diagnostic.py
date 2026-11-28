"""Discrete cross-part triangle contact diagnostic on actual evaluated open meshes.

Rigid analytic transforms validated at 85 degrees by native Blender snapshots.
No edits to mesh or generator. A hit is surface contact, not penetration depth.
"""
import argparse, itertools, json, math
from pathlib import Path
import numpy as np
from cycles.r2.oracle import triangle_hit

def transformed(m,r,l):
    v=np.asarray(m["vertices"],float)
    side=m["parent"]
    if side in ("Hinge_R","Hinge_L"):
        s=1 if side=="Hinge_R" else -1
        a=math.radians(s*(r if s==1 else l));c=math.cos(a);q=math.sin(a)
        pivot=np.array([s*.069,.005,.003])
        v=(v-pivot)@np.array([[c,q,0],[-q,c,0],[0,0,1]])+pivot
    return v

def hit_pairs(x,y):
    if np.any(x.max(axis=(0,1))<y.min(axis=(0,1))) or np.any(y.max(axis=(0,1))<x.min(axis=(0,1))):return 0
    lo=y.min(axis=1);hi=y.max(axis=1);count=0
    for t in x:
        ids=np.flatnonzero(np.all(hi>=t.min(axis=0),axis=1)&np.all(lo<=t.max(axis=0),axis=1))
        count+=sum(triangle_hit(t.tolist(),y[i].tolist()) for i in ids)
    return int(count)

def intended_pair(x,y,b):
    if b[x]["parent"] is not None and b[x]["parent"]==b[y]["parent"]:
        return True # rigid same-side assembly, internal contacts not measured here
    for side in ("R","L"):
        if frozenset((x,y)) in (frozenset(("Pin_"+side,"Sleeve_"+side)),frozenset(("Endpiece_"+side,"Sleeve_"+side)),frozenset(("Pin_"+side,"Temple_"+side)),frozenset(("Endpiece_"+side,"Temple_"+side))):
            return True # declared adjacent hinge interfaces; not certified mechanically
    return False

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--dir",required=True);a=p.parse_args();d=Path(a.dir)
    raw=json.loads((d/"raw.json").read_text());base=raw["open"]
    e=json.loads((d/"evaluation.json").read_text())
    if not e["gate"]:raise SystemExit("base gate not passed")
    pairs=[(x,y) for x,y in itertools.combinations(sorted(base),2) if (base[x]["parent"] or base[y]["parent"]) and not intended_pair(x,y,base)]
    angles=range(0,86,5)
    states=sorted(set((r,l) for t in angles for r,l in ((t,0),(0,t),(85,t),(t,85),(t,t))))
    rows=[]
    for r,l in states:
        tri={k:transformed(m,r,l)[np.array(m["triangles"],int)] for k,m in base.items()}
        contacts={}
        for x,y in pairs:
            n=hit_pairs(tri[x],tri[y])
            if n:contacts[x+"+"+y]=n
        rows.append(dict(right_deg=r,left_deg=l,nonexempt_surface_contacts=contacts))
    result=dict(approved=False,diagnostic_only=True,state_count=len(rows),pair_count_per_state=len(pairs),states_with_contact=sum(bool(x["nonexempt_surface_contacts"]) for x in rows),rows=rows,limitations=["5 degree discrete samples only; not continuous collision detection","surface contact count is not penetration or containment","same-side rigid parts and declared adjacent hinge pairs excluded, no certified hinge clearance","analytic rigid transforms from actual evaluated open geometry, not native Blender evaluation at each sampled pose","no static-static pair audit"])
    (d/"contact_diagnostic.json").write_text(json.dumps(result,indent=2))
    print("APPLIED02_CONTACT",json.dumps({**result,"rows":[x for x in rows if x["nonexempt_surface_contacts"]]}),flush=True)
