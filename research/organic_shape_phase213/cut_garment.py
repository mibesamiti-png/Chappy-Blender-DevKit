"""R7C: cut two leg openings into a single rounded body envelope.

Structured cube-sphere chart, one top cut and two side-to-bottom cuts.
No independent leg cylinders or seam lofts. Synthetic envelope only.
"""
import math
from collections import defaultdict,Counter
from garment import TARGET,GAP,WAIST,edge_groups,inspect
from junction import audit,smooth
from refinement import refine
from test_rounded_garment import shape_metrics

N=16

def chart_point(key,target=TARGET,waist=.40,depth=.82):
    x,y,z=(2*k/N-1 for k in key)
    length=math.sqrt(x*x+y*y+z*z)
    a,b,c=x/length,y/length,z/length
    if math.hypot(a,b)<1e-12:
        return (0.,0.,-depth)
    theta=math.atan2(b,a)
    if c>=0:
        top=1/math.sqrt(1+1/max(math.cos(theta)**2,math.sin(theta)**2))
        u=c/top
        height=u*(waist+WAIST.latitude((theta-math.pi/2)/math.tau))
        scale=1.
    else:
        height=depth*c
        scale=math.sqrt(max(0.,1-c*c))
    r=(target.ray(theta,height)+GAP)*scale
    return (r*math.cos(theta),r*math.sin(theta),height)

def base(target=TARGET,waist=.40,depth=.82,cut=6,ylo=4,yhi=14):
    if not (.28<=waist<=.55 and .72<=depth<=.94 and type(cut) is int and 4<=cut<=7 and type(ylo) is int and type(yhi) is int and (ylo==0 or 2<=ylo<=5) and (yhi==N or 11<=yhi<=14)):
        raise ValueError("bounded chart configuration")
    points=[];faces=[];keys=[];ids={}
    def add(k):
        if k not in ids:
            ids[k]=len(points);keys.append(k);points.append(chart_point(k,target,waist,depth))
        return ids[k]
    # parameter directions chosen so cross(du,dv) is outward
    charts=(
        ("bottom",lambda u,v:(v,u,0)),
        ("left",lambda u,v:(0,v,u)),
        ("right",lambda u,v:(N,u,v)),
        ("rear",lambda u,v:(u,0,v)),
        ("front",lambda u,v:(v,N,u)),
    )
    for name,fn in charts:
        for u in range(N):
            for v in range(N):
                k=fn(u,v)
                # Openings traverse the side/bottom edge rather than a tube end.
                if name=="bottom" and (k[0]<cut or k[0]>=N-cut) and ylo<=k[1]<yhi:continue
                if name in ("left","right") and k[2]<cut and ylo<=k[1]<yhi:continue
                # Optional wrap across the front/rear chart edge. The
                # matching bottom and side cuts share exactly the same lattice.
                if ((name=="front" and yhi==N) or (name=="rear" and ylo==0)) and (k[0]<cut or k[0]>=N-cut) and k[2]<cut:continue
                faces.append(tuple(add(fn(a,b)) for a,b in ((u,v),(u+1,v),(u+1,v+1),(u,v+1))))
    edge=defaultdict(list)
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]):edge[tuple(sorted((a,b)))].append((a,b))
    outgoing={}
    for v in edge.values():
        if len(v)==1:
            a,b=v[0]
            if a in outgoing:raise ValueError("nonmanifold border")
            outgoing[a]=b
    loops=[]
    while outgoing:
        first=min(outgoing);current=first;loop=[]
        while current in outgoing:
            loop.append(current);current=outgoing.pop(current)
        if current!=first:raise ValueError("open boundary chain")
        loops.append(loop)
    def role(l):
        if all(keys[i][2]==N for i in l):return 0
        if all(keys[i][0]<=cut for i in l):return 1
        if all(keys[i][0]>=N-cut for i in l):return 2
        raise ValueError("ambiguous loop role")
    loops=tuple(sorted(loops,key=role))
    if [role(l) for l in loops]!=[0,1,2]:raise ValueError("missing cut")
    return points,faces,loops

def round_hem(points,loops):
    out=list(points)
    # Only the two cut boundaries are rounded; no new leg surface is extruded.
    for _ in range(4):
        src=out[:]
        for l in loops[1:]:
            for j,i in enumerate(l):
                a,b=src[l[j-1]],src[l[(j+1)%len(l)]]
                out[i]=tuple(.5*x+.25*(y+z) for x,y,z in zip(src[i],a,b))
    return out

def inspect_cut(p,q,l,ref,target=TARGET):
    m=inspect(p,q,l,ref,target=target)
    # A corner quad can touch two rim edges. Count edges separately from faces.
    edges=Counter(tuple(sorted((a,b))) for f in q for a,b in zip(f,f[1:]+f[:1]))
    declared={tuple(sorted((a,b))) for loop in l for a,b in zip(loop,loop[1:]+loop[:1])}
    m["cut_boundary_exact"]=declared=={e for e,n in edges.items() if n==1}
    m["cut_loop_sizes"]=[len(loop) for loop in l]
    m["shape"]=shape_metrics(p,q,l)
    m["cut_pilot_pass"]=m["passed"] and m["cut_boundary_exact"] and m["upper_gap_min"]>.005 and m["upper_gap_max"]<.085 and m["left_max_x"]<0<m["right_min_x"] and m["shape"]["notch_depth"]<=.035
    return m

def trial():
    p,q,l=base()
    base_metrics=audit(p,q,l,p)
    history=[]
    rounded=round_hem(p,l)
    for steps in (0,8,16):
        s=smooth(rounded,q,l,steps)
        a,b,c,ref=refine(s,q,l,"smooth")
        m=inspect_cut(a,b,c,ref)
        history.append(dict(smoothing=steps,metrics=m))
        if m["cut_pilot_pass"]:
            return a,b,c,dict(complete=True,base=base_metrics,candidates=history,selected=steps,fixture_gate=True)
    return a,b,c,dict(complete=True,base=base_metrics,candidates=history,selected=None,fixture_gate=False)
