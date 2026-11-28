"""R7D: fair cut boundaries and propagate their displacement to nearby faces.
Preserve waist and original hem bounding boxes. No leg lofts or physics.
"""
import math
from collections import defaultdict
from cut_garment import base,trial as old_trial,inspect_cut
from refinement import refine
from boundary import norm
from patch import sub,dot

PLAN=(12,24)

def fair(points,faces,loops,steps):
    if steps not in PLAN:raise ValueError("fixed fairing budget")
    targets=list(points)
    for _ in range(steps):
        old=targets[:]
        for l in loops[1:]:
            for j,i in enumerate(l):
                a,b=old[l[j-1]],old[l[(j+1)%len(l)]]
                targets[i]=tuple(.5*x+.25*(y+z) for x,y,z in zip(old[i],a,b))
    # Restore cut extents, avoiding trivial improvement by shrinking holes.
    for l in loops[1:]:
        bounds=[]
        for k in range(3):
            lo,hi=min(points[i][k] for i in l),max(points[i][k] for i in l)
            a,b=min(targets[i][k] for i in l),max(targets[i][k] for i in l)
            if b-a<1e-10:raise ValueError("collapsed hem")
            bounds.append((lo,hi,a,b))
        for i in l:
            targets[i]=tuple(lo+(x-a)*(hi-lo)/(b-a) for x,(lo,hi,a,b) in zip(targets[i],bounds))
    adjacency=defaultdict(set)
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]):adjacency[a].add(b);adjacency[b].add(a)
    fixed={i for l in loops for i in l}
    disp=[sub(t,p) if i in fixed else (0.,0.,0.) for i,(t,p) in enumerate(zip(targets,points))]
    for _ in range(24):
        old=disp
        disp=[d if i in fixed else tuple(.85*sum(old[j][k] for j in sorted(adjacency[i]))/len(adjacency[i]) for k in range(3)) for i,d in enumerate(old)]
    return [targets[i] if i in fixed else tuple(x+y for x,y in zip(p,disp[i])) for i,p in enumerate(points)]

def hem_metrics(p,loops):
    # Measure turning on projected side-view rim, ignoring collinear refinement points.
    result=[]
    for l in loops[1:]:
        points=[p[i][1:] for i in l]
        angles=[]
        for j,b in enumerate(points):
            a,c=points[j-1],points[(j+1)%len(points)]
            u,v=sub(b,a),sub(c,b)
            den=norm(u)*norm(v)
            if den<1e-12:raise ValueError("collapsed projected edge")
            angles.append(math.degrees(math.acos(max(-1.,min(1.,dot(u,v)/den)))))
        area=abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])))/2
        result.append(dict(max_turn=max(angles),turn_energy=sum(a*a for a in angles),projected_area=area))
    return result

def trial():
    oldp,oldq,oldl,old=old_trial()
    assert old["fixture_gate"]
    reference=hem_metrics(oldp,oldl)
    p,q,l=base()
    candidates=[]
    for steps in PLAN:
        s=fair(p,q,l,steps)
        a,b,c,ref=refine(s,q,l,"smooth")
        m=inspect_cut(a,b,c,ref)
        hems=hem_metrics(a,c)
        eligible=m["cut_pilot_pass"] and all(h["max_turn"]<=.9*r["max_turn"] and h["turn_energy"]<=r["turn_energy"] and .8<=h["projected_area"]/r["projected_area"]<=1.2 for h,r in zip(hems,reference))
        candidates.append(dict(steps=steps,metrics=m,hems=hems,eligible=eligible))
        if eligible:
            return a,b,c,dict(complete=True,reference=reference,candidates=candidates,selected=steps,fixture_gate=True)
    return a,b,c,dict(complete=True,reference=reference,candidates=candidates,selected=None,fixture_gate=False)
