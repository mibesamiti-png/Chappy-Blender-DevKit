"""R10D: bounded local rim fairing based on actual 3D turning angles.
Only affected rim neighborhoods move; the accepted R9F remains unchanged.
"""
import math
from collections import Counter,defaultdict
from patch import sub,dot
from visibility_diagnostic import unit
from cut_garment import inspect_cut
from side_width import widths
from tip_fairing import flare
from silhouette_cap import drop
from test_rim_wrap import extent
from intersection import audit as intersection_audit

PLAN=(4,8)

def loops_from_mesh(p,q):
    edges=Counter(tuple(sorted((a,b))) for f in q for a,b in zip(f,f[1:]+f[:1]))
    adj=defaultdict(set)
    for (a,b),n in edges.items():
        if n==1:adj[a].add(b);adj[b].add(a)
    if any(len(v)!=2 for v in adj.values()):raise ValueError("invalid rim")
    result=[]
    while adj:
        start=min(adj);loop=[start];prev=-1;cur=start
        while True:
            nxt=min(adj[cur]-{prev});prev,cur=cur,nxt
            if cur==start:break
            loop.append(cur)
        for i in loop:del adj[i]
        result.append(loop)
    def role(l):
        if min(p[i][2] for i in l)>.3:return 0
        if max(p[i][0] for i in l)<0:return 1
        if min(p[i][0] for i in l)>0:return 2
        raise ValueError("unknown rim role")
    if sorted(map(role,result))!=[0,1,2]:raise ValueError("missing rim")
    return tuple(sorted(result,key=role))

def turns(p,l):
    return [math.degrees(math.acos(max(-1.,min(1.,dot(
        unit(sub(p[i],p[l[j-1]])),unit(sub(p[l[(j+1)%len(l)]],p[i])))))))
        for j,i in enumerate(l)]

def fair(p,q,l,steps):
    if steps not in PLAN:raise ValueError("fixed budget")
    targets=list(p)
    weights={}
    for loop in l[1:]:
        angles=turns(p,loop)
        peaks=[j for j,a in enumerate(angles) if a>30.]
        for j,i in enumerate(loop):
            if peaks:
                d=min(min((j-k)%len(loop),(k-j)%len(loop)) for k in peaks)
                if d<5:
                    t=1-d/5
                    weights[i]=.35*t*t*(3-2*t)
    if not weights:return list(p)
    for _ in range(steps):
        prev=targets[:]
        for loop in l[1:]:
            for j,i in enumerate(loop):
                w=weights.get(i,0.)
                if w:
                    a,b=prev[loop[j-1]],prev[loop[(j+1)%len(loop)]]
                    targets[i]=tuple((1-w)*x+w*(y+z)/2 for x,y,z in zip(prev[i],a,b))
    adj=defaultdict(set)
    for f in q:
        for a,b in zip(f,f[1:]+f[:1]):
            adj[a].add(b);adj[b].add(a)
    fixed={i for loop in l for i in loop}
    disp=[sub(a,b) if i in fixed else (0.,0.,0.) for i,(a,b) in enumerate(zip(targets,p))]
    # Boundary displacement is propagated locally; all other boundaries fixed.
    for _ in range(8):
        prev=disp
        disp=[d if i in fixed else tuple(.75*sum(prev[j][k] for j in sorted(adj[i]))/len(adj[i]) for k in range(3)) for i,d in enumerate(prev)]
    return [targets[i] if i in fixed else tuple(x+y for x,y in zip(a,d)) for i,(a,d) in enumerate(zip(p,disp))]

def trial(p,q,l):
    before=[max(turns(p,loop)) for loop in l[1:]]
    baseline_flare=flare(p,q)
    baseline_extent=extent(p,l)
    base_widths=widths(p,l)
    history=[]
    for steps in PLAN if max(before)>30 else (None,):
        out=p if steps is None else fair(p,q,l,steps)
        after=[max(turns(out,loop)) for loop in l[1:]]
        m=inspect_cut(out,q,l,out)
        actual_flare=flare(out,q)
        actual_extent=extent(out,l)
        collision=intersection_audit(out,q)
        width_error=max(abs(a-b) for a,b in zip(base_widths,widths(out,l)))
        extent_error=max(abs(a-b) for x,y in zip(baseline_extent,actual_extent) for a,b in zip(x,y))
        waist_drift=max(math.dist(p[i],out[i]) for i in l[0])
        displacement=max(math.dist(a,b) for a,b in zip(p,out))
        angle_gate=all(b<=30 and (b<=.85*a if a>30 else b<=a+1) for a,b in zip(before,after))
        eligible=(angle_gate and m["cut_pilot_pass"] and m["max_normal_jump"]<=30 and collision["passed"]
            and width_error<=.005 and extent_error<=.05 and waist_drift==0 and displacement<=.025
            and actual_flare["excess"]<=baseline_flare["excess"]+.01
            and drop(actual_flare)<=drop(baseline_flare)+.01)
        history.append(dict(steps=steps,turns=after,angle_gate=angle_gate,metrics=m,collision=collision,
            width_error=width_error,extent_error=extent_error,waist_drift=waist_drift,
            max_displacement=displacement,flare=actual_flare["excess"],drop=drop(actual_flare),eligible=eligible))
        if eligible:return dict(baseline_turns=before,candidates=history,selected=steps,passed=True),out
    return dict(baseline_turns=before,candidates=history,selected=None,passed=False),p
