"""R3: cached exact geometry; optional provable shared-simplex early exits.

The R2 implementation stays unchanged as a reference. No epsilon filtering.
"""
import math
from time import monotonic
import numpy as np
from .exact import rational_triangle, cross, sub, dot, _intersection, _on_shared


def _classify(a,b,ia,ib,na,nb,shortcuts):
    common=[a[k] for k,x in enumerate(ia) if x in ib]
    if len(common)==3:
        return True, 'duplicate'
    if shortcuts and len(common)==2:
        # Distinct planes intersect on the shared edge's supporting line;
        # nondegenerate triangles meet that line on precisely their shared edge.
        if any(cross(na,nb)):
            return False,'shared_edge_nonplanar'
        p,q=common
        oa=next(a[k] for k,x in enumerate(ia) if x not in ib)
        ob=next(b[k] for k,x in enumerate(ib) if x not in ia)
        side=dot(cross(sub(q,p),sub(oa,p)),cross(sub(q,p),sub(ob,p)))
        return side>0,'shared_edge_coplanar'
    if shortcuts and len(common)==1:
        # If both other vertices lie strictly on one side of the opposite
        # plane, its intersection with this triangle is the shared point only.
        for triangle,ids,other_ids,normal,origin in ((a,ia,ib,nb,b[0]),(b,ib,ia,na,a[0])):
            ds=[dot(normal,sub(p,origin)) for p,x in zip(triangle,ids) if x not in other_ids]
            if all(d>0 for d in ds) or all(d<0 for d in ds):
                return False,'shared_vertex_one_side'
    points=_intersection(a,b)
    hit=bool(points) and not (common and all(_on_shared(p,common) for p in points))
    return hit,'clip'


def detect_accelerated(mesh,pair_budget=200000,seconds=30,shortcuts=True):
    """Exact binary64 model. Same 2048-face cap as R2; all box pairs budgeted.

    Caches are per call and never reused after geometry changes. Timelimit is
    cooperative (checked between bounded preprocessing/rows/pairs).
    """
    if type(pair_budget) is not int or not 1<=pair_budget<=2000000:
        raise ValueError('pair_budget must be integer in 1..2000000')
    if isinstance(seconds,bool) or not math.isfinite(seconds) or not 0<seconds<=300:
        raise ValueError('seconds must be in (0,300]')
    if type(shortcuts) is not bool:raise ValueError('shortcuts must be bool')
    counts={};scanned=narrow=0
    def result(status,pairs,reason=None):
        return dict(status=status,pairs=pairs,reason=reason,scanned=scanned,
                    narrow_tests=narrow,paths=counts,certified=False,
                    arithmetic='exact_binary64_rational')
    if len(mesh.faces)>2048:return result('budget_exceeded',None,'face_limit')
    deadline=monotonic()+seconds
    triangles=mesh.vertices[mesh.faces]
    lo,hi=triangles.min(1),triangles.max(1)
    rational=[];normals=[]
    for t in triangles:
        if monotonic()>=deadline:return result('budget_exceeded',None,'time_limit')
        a=rational_triangle(t);rational.append(a)
        normals.append(cross(sub(a[1],a[0]),sub(a[2],a[0])))
    faces=[tuple(map(int,f)) for f in mesh.faces]
    hits=[]
    for i in range(len(triangles)-1):
        width=len(triangles)-i-1
        if scanned+width>pair_budget or monotonic()>=deadline:
            return result('budget_exceeded',None,'pair_or_time_limit')
        # O(n) temporary row, no n*n allocation. Direct comparisons only.
        mask=np.all(hi[i]>=lo[i+1:],axis=1)&np.all(hi[i+1:]>=lo[i],axis=1)
        scanned+=width
        for offset in np.flatnonzero(mask):
            if monotonic()>=deadline:return result('budget_exceeded',None,'time_limit')
            j=int(offset)+i+1;narrow+=1
            hit,path=_classify(rational[i],rational[j],faces[i],faces[j],normals[i],normals[j],shortcuts)
            counts[path]=counts.get(path,0)+1
            if hit:hits.append((i,j))
    return result('measured',hits)
