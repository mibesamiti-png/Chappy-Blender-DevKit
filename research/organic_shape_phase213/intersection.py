"""Bounded floating-point triangle SAT audit for nonincident triangles.

Fixed triangulation of quads; common-index pairs excluded and counted.
Coplanar contacts are included. This is not an exact predicate or a proof
against overlap between incident triangles.
"""
from collections import defaultdict
from itertools import product
import math
from patch import sub,cross,dot
from boundary import norm

EPS=1e-9
CELL=.12

def triangle_hit(a,b):
    ea=[sub(a[(i+1)%3],a[i]) for i in range(3)]
    eb=[sub(b[(i+1)%3],b[i]) for i in range(3)]
    na=cross(ea[0],ea[1]);nb=cross(eb[0],eb[1])
    if min(norm(na),norm(nb))<1e-12:raise ValueError("degenerate triangle")
    axes=[na,nb]+[cross(x,y) for x in ea for y in eb]
    # In-plane axes also handle coplanar triangles.
    axes += [cross(na,e) for e in ea]+[cross(nb,e) for e in eb]
    for axis in axes:
        length=norm(axis)
        if length<1e-14:continue
        v=[dot(axis,p) for p in a];w=[dot(axis,p) for p in b]
        if max(v)<min(w)-EPS*length or max(w)<min(v)-EPS*length:return False
    return True

def audit(points,faces):
    if not 1<=len(faces)<=20000 or not points:raise ValueError("bounded mesh required")
    if any(len(p)!=3 or not all(math.isfinite(x) and abs(x)<=4 for x in p) for p in points):
        raise ValueError("invalid or out-of-scope coordinates")
    tris=[];parent=[];bounds=[];grid=defaultdict(list)
    for j,f in enumerate(faces):
        if len(f) not in (3,4) or len(set(f))!=len(f) or min(f)<0 or max(f)>=len(points):
            raise ValueError("invalid face")
        for t in ((tuple(f),) if len(f)==3 else ((f[0],f[1],f[2]),(f[0],f[2],f[3]))):
            a,b,c=[points[i] for i in t]
            if norm(cross(sub(b,a),sub(c,a)))<1e-12:raise ValueError("degenerate triangle")
            box=tuple((min(a[k],b[k],c[k]),max(a[k],b[k],c[k])) for k in range(3))
            index=len(tris);tris.append(t);parent.append(j);bounds.append(box)
            ranges=[range(math.floor((lo-EPS)/CELL),math.floor((hi+EPS)/CELL)+1) for lo,hi in box]
            if math.prod(map(len,ranges))>10000:raise ValueError("triangle broadphase budget")
            for cell in product(*ranges):grid[cell].append(index)
    pairs=set()
    for bucket in grid.values():
        for k,i in enumerate(bucket):
            for j in bucket[k+1:]:
                pairs.add((i,j))
                if len(pairs)>2000000:raise ValueError("candidate budget exceeded")
    skipped=0;aabb_pairs=0;tested=0;hits=[]
    for i,j in sorted(pairs):
        if any(a[1]<b[0]-EPS or b[1]<a[0]-EPS for a,b in zip(bounds[i],bounds[j])):continue
        aabb_pairs+=1
        if set(tris[i])&set(tris[j]):
            skipped+=1;continue
        tested+=1
        if triangle_hit([points[k] for k in tris[i]],[points[k] for k in tris[j]]):
            hits.append((i,j,parent[i],parent[j]))
    return dict(triangles=len(tris),grid_cells=len(grid),candidate_pairs=len(pairs),
        aabb_pairs=aabb_pairs,incident_pairs_excluded=skipped,nonincident_pairs_tested=tested,
        intersections=len(hits),first_hits=hits[:20],passed=not hits,
        exact_predicate=False,incident_overlap_verified=False)
