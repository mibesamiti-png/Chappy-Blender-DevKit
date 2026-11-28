"""R5: one conforming quad refinement pass with fixed boundary polylines.

Original boundary vertices and piecewise-linear edges stay exact.
Interior Catmull-Clark is a candidate, not an unconditional repair.
"""
from collections import defaultdict
import math

def mean(points):
    return tuple(sum(p[k] for p in points)/len(points) for k in range(3))

def refine(points,faces,loops,method="smooth"):
    if method not in ("smooth","linear") or not 4<=len(points)<=10000 or not 1<=len(faces)<=10000:
        raise ValueError("unsupported method or refinement budget")
    if any(len(p)!=3 or not all(map(math.isfinite,p)) for p in points):
        raise ValueError("invalid points")
    edges=defaultdict(list);incident=defaultdict(list);adj=defaultdict(set);direct=defaultdict(int)
    for j,f in enumerate(faces):
        if len(f)!=4 or len(set(f))!=4 or min(f)<0 or max(f)>=len(points):
            raise ValueError("invalid quad")
        for a,b in zip(f,f[1:]+f[:1]):
            e=tuple(sorted((a,b)));edges[e].append(j);direct[e]+=1 if a<b else -1
            incident[a].append(j);adj[a].add(b);adj[b].add(a)
    if len(incident)!=len(points) or any(len(v)>2 or (len(v)==2 and direct[e]!=0) for e,v in edges.items()):
        raise ValueError("invalid edge incidence")
    border={e for e,v in edges.items() if len(v)==1}
    flat=[i for l in loops for i in l]
    if len(set(flat))!=len(flat) or any(len(l)<3 for l in loops):
        raise ValueError("invalid boundary loops")
    declared={tuple(sorted((a,b))) for l in loops for a,b in zip(l,l[1:]+l[:1])}
    if border!=declared:
        raise ValueError("boundary mismatch")
    fixed=set(flat);centers=[mean([points[i] for i in f]) for f in faces]
    mids={e:mean([points[i] for i in e]) for e in edges}
    out=list(points)
    if method=="smooth":
        for i,p in enumerate(points):
            if i in fixed:continue
            n=len(adj[i])
            if n<3 or len(incident[i])!=n:raise ValueError("unsupported interior vertex")
            F=mean([centers[j] for j in incident[i]])
            R=mean([mids[tuple(sorted((i,j)))] for j in sorted(adj[i])])
            out[i]=tuple((F[k]+2*R[k]+(n-3)*p[k])/n for k in range(3))
    edge_ids={}
    for e in sorted(edges):
        edge_ids[e]=len(out)
        out.append(mean([points[i] for i in e]+[centers[j] for j in edges[e]]) if method=="smooth" and e not in border else mids[e])
    face_start=len(out);out.extend(centers)
    quads=[]
    for j,f in enumerate(faces):
        for k,a in enumerate(f):
            b=f[(k+1)%4];c=f[(k-1)%4]
            quads.append((a,edge_ids[tuple(sorted((a,b)))],face_start+j,edge_ids[tuple(sorted((c,a)))]))
    new_loops=[];reference=list(out)
    for l in loops:
        new=[]
        for a,b in zip(l,l[1:]+l[:1]):
            e=tuple(sorted((a,b)));mid=edge_ids[e]
            new.extend((a,mid))
            reference[a]=points[a];reference[mid]=mids[e]
        new_loops.append(new)
    return out,quads,tuple(new_loops),reference
