"""R12F: locate normal discontinuities before changing another formula."""
import math
from collections import defaultdict,Counter
from boundary import norm
from patch import cross,sub,dot
from pattern_garment import N,UP,DOWN,BRIDGE,mesh
from junction import audit

def face_band(i):
    panel=N*(UP+DOWN)
    if i>=2*panel:return "crotch",(i-2*panel)//N
    role="front" if i<panel else "back"
    row=(i%panel)//N
    return role,row

def locate(p,q):
    inc=defaultdict(list)
    for i,f in enumerate(q):
        a,b,c,d=(p[j] for j in f)
        x=cross(sub(b,a),sub(c,a));y=cross(sub(c,a),sub(d,a))
        n=tuple(v+w for v,w in zip(x,y))
        for a,b in zip(f,f[1:]+f[:1]):inc[tuple(sorted((a,b)))].append((i,n))
    records=[]
    for edge,ns in inc.items():
        if len(ns)!=2:continue
        (i,a),(j,b)=ns
        den=norm(a)*norm(b)
        angle=math.degrees(math.acos(max(-1.,min(1.,dot(a,b)/den)))) if den else 180.
        x,y=p[edge[0]],p[edge[1]]
        records.append(dict(edge=list(edge),faces=[i,j],bands=[face_band(i),face_band(j)],
            midpoint=[(v+w)/2 for v,w in zip(x,y)],angle=angle))
    return sorted(records,key=lambda r:(-r["angle"],r["edge"]))

def classify(record):
    (a,i),(b,j)=record["bands"]
    if a!=b:return "panel_interface:"+"|".join(sorted((a,b)))
    if a=="crotch":return "crotch_interior"
    if min(i,j)<UP<=max(i,j):return "upper_lower_transition:"+a
    if max(i,j)<UP:return "upper:"+a
    if max(i,j)>=UP+DOWN-3:return "near_crotch:"+a
    return "lower:"+a

def diagnose(case,method):
    p,q,l,g,a,b=mesh(case,method)
    rows=locate(p,q)
    m=audit(p,q,l,p)
    if abs(rows[0]["angle"]-m["max_normal_jump"])>1e-9:raise ValueError("normal audit disagreement")
    regions=defaultdict(list)
    for r in rows:regions[classify(r)].append(r["angle"])
    return dict(method=method,max_normal_jump=rows[0]["angle"],
        high_angle_edges=sum(r["angle"]>55 for r in rows),
        regions={k:dict(count=len(v),maximum=max(v),above_55=sum(x>55 for x in v)) for k,v in sorted(regions.items())},
        worst=[dict(r,region=classify(r)) for r in rows[:12]])
