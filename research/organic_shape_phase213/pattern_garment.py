"""R12A: outline-first static garment pilot, optional panel segmentation.
Analytic synthetic dimensions, not digitized commercial patterns or cloth physics.
"""
import math
from collections import Counter,defaultdict
from junction import audit
from intersection import audit as intersection_audit

# name, hip halfwidth, front depth, rear depth, side height, crotch full width, length
CASES=(("standard",1.0,.69,.79,.32,.34,.38),
       ("narrow_side",1.0,.69,.79,.18,.30,.38),
       ("wide_crotch",1.0,.69,.79,.32,.46,.38),
       ("long_crotch",1.0,.69,.79,.32,.34,.50),
       ("rear_coverage",1.0,.69,.88,.32,.34,.38))
N=32;UP=8;DOWN=24;BRIDGE=12
WAIST=.40;BOTTOM=-.70

def smooth(t):return t*t*(3-2*t)

def mesh(case,method="original"):
    if method not in ("original","round_rim"):raise ValueError("fixed outline methods")
    if case not in CASES:raise ValueError("fixed pattern fixtures")
    _,hip,front,rear,side,width,length=case
    p=[];q=[];groups=[];shared={}
    def add(v):
        p.append(tuple(v));return len(p)-1
    def row(sign,j):
        upper=j<=UP
        t=j/UP if upper else (j-UP)/DOWN
        d=front if sign==1 else rear
        side_z=WAIST-side
        if upper:
            w=.85+(hip-.85)*smooth(t)
            cy=d*(.84+.16*smooth(t));ey=0.
            z=WAIST-side*t
            blend=0.
        else:
            a=math.pi*t/2
            w=width/2+(hip-width/2)*math.cos(a)**2
            cy=length/2+(d-length/2)*math.cos(a)
            ey=cy*(math.sin(a) if method=="round_rim" else math.sin(a)**2)
            z=side_z-(side_z-BOTTOM)*math.sin(a)
            blend=smooth(t)
        out=[]
        for i in range(N+1):
            u=2*i/N-1
            x=w*((1-blend)*math.sin(math.pi*u/2)+blend*u)
            y=sign*(ey+(cy-ey)*math.cos(math.pi*u/2))
            zz=z
            if not upper and method=="round_rim":
                # Only the outer rim needs a horizontal tangent at the side join.
                # Keep the middle of the panel on its original height profile.
                weight=abs(u)**6
                zz=(1-weight)*z+weight*(side_z-(side_z-BOTTOM)*smooth(t))
            if i in (0,N) and upper:
                key=(j,i)
                if key not in shared:shared[key]=add((x,0.,z))
                idx=shared[key]
            elif j==UP+DOWN:
                idx=add((width/2*u,sign*length/2,BOTTOM))
            else:idx=add((x,y,zz))
            out.append(idx)
        return out
    def connect(a,b,role,reverse=False):
        for i in range(N):
            f=(a[i],a[i+1],b[i+1],b[i])
            q.append(f[::-1] if reverse else f);groups.append(role)
    panels={}
    for sign,role in ((1,"front"),(-1,"back")):
        rows=[row(sign,j) for j in range(UP+DOWN+1)]
        for a,b in zip(rows,rows[1:]):connect(a,b,role,sign==-1)
        panels[role]=rows
    first,last=panels["front"][-1],panels["back"][-1]
    prev=first
    for j in range(1,BRIDGE+1):
        t=j/BRIDGE
        nxt=last if j==BRIDGE else [add((width/2*(2*i/N-1),length*(.5-t),
            BOTTOM-.035*(1-(1-2*t)**2)**2)) for i in range(N+1)]
        connect(prev,nxt,"crotch");prev=nxt
    # Recover ordered boundary loops from directed single-incidence edges.
    counts=Counter(tuple(sorted((a,b))) for f in q for a,b in zip(f,f[1:]+f[:1]))
    nxt={a:b for f in q for a,b in zip(f,f[1:]+f[:1]) if counts[tuple(sorted((a,b)))]==1}
    loops=[]
    while nxt:
        start=min(nxt);i=start;l=[]
        while True:
            l.append(i);i=nxt.pop(i)
            if i==start:break
        loops.append(l)
    def role(l):
        if all(abs(p[i][2]-WAIST)<1e-10 for i in l):return 0
        if max(p[i][0] for i in l)<0:return 1
        if min(p[i][0] for i in l)>0:return 2
        raise ValueError("unknown boundary")
    if sorted(map(role,loops))!=[0,1,2]:raise ValueError("missing boundary")
    return p,q,tuple(sorted(loops,key=role)),groups,first,last

def partition(groups,mode):
    if mode=="integrated":return ["fabric"]*len(groups)
    if mode=="separate":return list(groups)
    raise ValueError("unsupported panel mode")

def inspect(case,p,q,l,groups,first,last):
    m=audit(p,q,l,p)
    widths=[math.dist(p[r[0]],p[r[-1]]) for r in (first,last)]
    length=math.dist(p[first[N//2]],p[last[N//2]])
    inc=defaultdict(list)
    for f,g in zip(q,groups):
        for a,b in zip(f,f[1:]+f[:1]):inc[tuple(sorted((a,b)))].append(g)
    seams=Counter(tuple(sorted(v)) for v in inc.values() if len(v)==2 and v[0]!=v[1])
    expected={("crotch","front"):N,("back","crotch"):N,("back","front"):UP*2}
    seam_gate=dict(seams)==expected
    collision=intersection_audit(p,q)
    width_error=max(abs(v-case[5]) for v in widths)
    length_error=abs(length-case[6])
    return dict(metrics=m,crotch_widths=widths,crotch_chord_length=length,
        width_error=width_error,length_error=length_error,
        seam_edges={"|".join(k):v for k,v in seams.items()},seam_gate=seam_gate,
        nonincident_intersection=collision,
        passed=m["topology_pass"] and m["min_triangle_area"]>1e-7 and m["min_quad_cos"]>0
        and m["max_edge_ratio"]<=20 and m["max_normal_jump"]<=55
        and width_error<1e-10 and length_error<1e-10 and seam_gate and collision["passed"])
