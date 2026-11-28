"""R11A: synthetic pelvis-to-thigh envelope, independent implicit-field pilot.

Extract a single open triangle surface with three boundary loops. No garment
fitting, anatomical landmarks, genital detail or real-body certification.
"""
import math
from collections import Counter,defaultdict
from itertools import product
from patch import sub,cross,dot
from boundary import norm

CASES=(("neutral",1.00,.70,.08,.56,.43,.48),
       ("wide_hip",1.13,.73,.10,.62,.46,.49),
       ("deep_hip",1.02,.82,.15,.56,.43,.54))
BOUNDS=((-1.5,1.5),(-1.25,1.25),(-1.25,.80))
RES=(30,26,30)
TETS=((0,1,3,7),(0,3,2,7),(0,2,6,7),(0,6,4,7),(0,4,5,7),(0,5,1,7))
CORNERS=((0,0,0),(1,0,0),(0,1,0),(1,1,0),(0,0,1),(1,0,1),(0,1,1),(1,1,1))

def smooth_min(a,b,k=.10):
    h=max(k-abs(a-b),0.)/k
    return min(a,b)-.25*k*h*h

def field(p,case):
    _,hip,depth,back,sep,rx,ry=case
    x,y,z=p
    g=math.exp(-((z+.12)/.62)**2)
    a=.72+(hip-.72)*g
    b=.55+(depth-.55)*g
    pelvis=.60*(math.sqrt((x/a)**2+((y+back*g)/b)**2+(max(0.,-.10-z)/.60)**2)-1)
    def leg(sign):
        t=max(0.,min(1.,(z+1.25)/.9))
        r=rx*(.92+.08*t);d=ry*(.94+.06*t)
        return .45*(math.sqrt(((x-sign*sep)/r)**2+((y+.035)/d)**2+(max(0.,z+.48)/.68)**2)-1)
    return smooth_min(pelvis,smooth_min(leg(-1),leg(1)))

def edge_root(a,b,fa,fb,case):
    """Bracket a root on the same lattice edge, without moving off the edge."""
    if fa==0:return a
    if fb==0:return b
    if (fa<0)==(fb<0):raise ValueError("root not bracketed")
    lo,hi=0.,1.
    for _ in range(24):
        t=(lo+hi)/2
        v=tuple(x+t*(y-x) for x,y in zip(a,b))
        fv=field(v,case)
        if fv==0:return v
        if (fv<0)==(fa<0):lo=t
        else:hi=t
    return tuple(x+(lo+hi)/2*(y-x) for x,y in zip(a,b))

def extract(case,method="linear"):
    if method not in ("linear","bracketed"):raise ValueError("fixed extraction methods")
    if case not in CASES:raise ValueError("fixed fixtures only")
    nx,ny,nz=RES
    grid={k:tuple(lo+(hi-lo)*i/n for i,n,(lo,hi) in zip(k,RES,BOUNDS))
          for k in product(range(nx+1),range(ny+1),range(nz+1))}
    values={k:field(v,case) for k,v in grid.items()}
    p=[];q=[];cache={}
    def edge(a,b):
        key=tuple(sorted((a,b)))
        if key not in cache:
            a,b=key;fa,fb=values[a],values[b]
            t=fa/(fa-fb)
            cache[key]=len(p)
            p.append(edge_root(grid[a],grid[b],fa,fb,case) if method=="bracketed" else tuple(x+t*(y-x) for x,y in zip(grid[a],grid[b])))
        return cache[key]
    def emit(t,normal):
        a,b,c=(p[i] for i in t)
        if dot(cross(sub(b,a),sub(c,a)),normal)<0:t=(t[0],t[2],t[1])
        q.append(t)
    for i,j,k in product(range(nx),range(ny),range(nz)):
        cube=[(i+x,j+y,k+z) for x,y,z in CORNERS]
        for tet in TETS:
            inside=[cube[t] for t in tet if values[cube[t]]<0]
            outside=[cube[t] for t in tet if values[cube[t]]>=0]
            if not inside or not outside:continue
            normal=tuple(sum(grid[a][n] for a in outside)/len(outside)-sum(grid[a][n] for a in inside)/len(inside) for n in range(3))
            if len(inside)==1:emit(tuple(edge(inside[0],b) for b in outside),normal)
            elif len(outside)==1:emit(tuple(edge(a,outside[0]) for a in inside),normal)
            else:
                a,b=inside;c,d=outside
                ring=(edge(a,c),edge(a,d),edge(b,d),edge(b,c))
                emit((ring[0],ring[1],ring[2]),normal);emit((ring[0],ring[2],ring[3]),normal)
    return p,q

def components(adj):
    remaining=set(adj);out=[]
    while remaining:
        seen={remaining.pop()};stack=list(seen)
        while stack:
            for j in adj[stack.pop()]&remaining:
                remaining.remove(j);seen.add(j);stack.append(j)
        out.append(seen)
    return out

def audit(p,q,case):
    edges=Counter();direction=Counter();adj=defaultdict(set);normals=defaultdict(list)
    link=defaultdict(lambda:defaultdict(set))
    areas=[]
    for t in q:
        a,b,c=(p[i] for i in t)
        n=cross(sub(b,a),sub(c,a));areas.append(norm(n)/2)
        for j,i in enumerate(t):
            k=t[(j+1)%3];prev=t[(j-1)%3]
            e=tuple(sorted((i,k)));edges[e]+=1;direction[e]+=1 if i<k else -1
            adj[i].add(k);adj[k].add(i);normals[e].append(n)
            link[i][k].add(prev);link[i][prev].add(k)
    border=defaultdict(set)
    for (i,j),n in edges.items():
        if n==1:border[i].add(j);border[j].add(i)
    loops=components(border)
    roles=[]
    for l in loops:
        if all(abs(p[i][2]-.80)<1e-9 for i in l):roles.append("waist")
        elif all(abs(p[i][2]+1.25)<1e-9 for i in l):
            roles.append("left" if max(p[i][0] for i in l)<0 else "right" if min(p[i][0] for i in l)>0 else "invalid")
        else:roles.append("invalid")
    jumps=[]
    for ns in normals.values():
        if len(ns)==2 and norm(ns[0])*norm(ns[1])>0:
            jumps.append(math.degrees(math.acos(max(-1.,min(1.,dot(*ns)/(norm(ns[0])*norm(ns[1])))))))
    links_bad=0
    for i,g in link.items():
        degrees=[len(s) for s in g.values()]
        ok=(degrees.count(1)==2 and all(d in (1,2) for d in degrees)) if i in border else all(d==2 for d in degrees)
        links_bad+=int(not ok or len(components(g))!=1)
    residual=max(abs(field(v,case)) for v in p)
    result=dict(vertices=len(p),triangles=len(q),euler=len(p)-len(edges)+len(q),
        components=len(components(adj)),unused=len(p)-len(adj),boundary_roles=sorted(roles),
        boundary_degrees_ok=all(len(v)==2 for v in border.values()),
        nonmanifold=sum(n>2 for n in edges.values()),orientation_errors=sum(n==2 and direction[e]!=0 for e,n in edges.items()),
        vertex_link_errors=links_bad,min_area=min(areas),max_normal_jump=max(jumps),max_field_residual=residual)
    result["passed"]=(result["euler"]==-1 and result["components"]==1 and result["unused"]==0
        and result["boundary_roles"]==["left","right","waist"] and result["boundary_degrees_ok"]
        and result["nonmanifold"]==result["orientation_errors"]==links_bad==0
        and result["min_area"]>1e-12 and result["max_normal_jump"]<=55 and residual<=.015)
    return result
