"""R16 explicit seam cut and harmonic disk solve for rectangular source UV."""
from collections import defaultdict
import heapq
import numpy as np

class Reject(ValueError): pass

def source_loop(points,v):
    """Independent per-edge UV pins in original loop coordinate space."""
    p=np.asarray(points,dtype=np.float32).astype(float)
    area=np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1))
    if abs(area)<1e-9: raise Reject("degenerate input loop")
    if area<0: p=p[::-1]
    anchor=int(np.argmax(p[:,0])); p=np.roll(p,-anchor,axis=0)
    length=np.linalg.norm(np.roll(p,-1,axis=0)-p,axis=1)
    if np.any(length<=1e-9): raise Reject("duplicate source points")
    u=np.r_[0.,np.cumsum(length)/sum(length)]; u[-1]=1.
    return [(tuple(p[i]),tuple(p[(i+1)%len(p)]),(float(u[i]),v),(float(u[i+1]),v)) for i in range(len(p))]

def solve(vertices,faces,lower,upper):
    v=np.asarray(vertices,float); f=np.asarray(faces,int); n=len(f)
    if n<3 or n>600 or f.shape!=(n,3) or not np.isfinite(v).all() or np.any(f<0) or np.any(f>=len(v)): raise Reject("mesh dimensions")
    lookup={tuple(p):i for i,p in enumerate(v.astype(np.float32).astype(float))}
    if len(lookup)!=len(v): raise Reject("ambiguous vertex coordinates")
    incidence=defaultdict(list)
    for i,t in enumerate(f):
        for j in range(3):
            a,b=int(t[j]),int(t[(j+1)%3]); incidence[tuple(sorted((a,b)))].append((i,j,(j+1)%3))
    if any(len(x)>2 for x in incidence.values()): raise Reject("nonmanifold")
    boundary={e for e,x in incidence.items() if len(x)==1}
    source={}; anchors=[]
    for rows,h in ((lower,0.),(upper,1.)):
        if len(rows)<3: raise Reject("short boundary")
        last=0.; anchors.append(lookup.get(rows[0][0],-1))
        for k,(a,b,ua,ub) in enumerate(rows):
            ua=np.asarray(ua,float); ub=np.asarray(ub,float)
            if not np.isfinite([ua,ub]).all() or ua.shape!=(2,) or ub.shape!=(2,): raise Reject("nonfinite pin")
            if abs(ua[1]-h)>1e-9 or abs(ub[1]-h)>1e-9 or abs(ua[0]-last)>1e-9 or ub[0]<=ua[0] or ub[0]>1+1e-9 or ub[0]-ua[0]>.5: raise Reject("nonmonotonic or incompatible source pin")
            if b!=rows[(k+1)%len(rows)][0] or a not in lookup or b not in lookup: raise Reject("source loop correspondence")
            x,y=lookup[a],lookup[b]; e=tuple(sorted((x,y)))
            if e in source: raise Reject("duplicate source edge")
            source[e]={x:ua,y:ub}; last=ub[0]
        if abs(last-1)>1e-9: raise Reject("source does not span unit interval")
    if set(source)!=boundary: raise Reject("source boundary edge set mismatch")
    lo,hi=anchors
    bv={i for e in boundary for i in e}; graph=defaultdict(list)
    for a,b in incidence:
        if (a in bv and a not in anchors) or (b in bv and b not in anchors): continue
        if (a,b) in boundary: continue
        d=float(np.linalg.norm(v[a]-v[b]))
        graph[a].append((b,d)); graph[b].append((a,d))
    queue=[(0.,(lo,))]; seen=set(); path=None
    while queue:
        d,p=heapq.heappop(queue); u=p[-1]
        if u in seen: continue
        seen.add(u)
        if u==hi: path=list(p); break
        for w,c in sorted(graph[u]):
            if w not in seen: heapq.heappush(queue,(d+c,p+(w,)))
    if path is None: raise Reject("no interior seam path")
    seam={tuple(sorted(e)) for e in zip(path,path[1:])}
    parent=list(range(3*n))
    def root(i):
        while parent[i]!=i: parent[i]=parent[parent[i]]; i=parent[i]
        return i
    def corner(fi,vi): return 3*fi+int(np.flatnonzero(f[fi]==vi)[0])
    for e,refs in incidence.items():
        if len(refs)==2 and e not in seam:
            a,b=refs[0][0],refs[1][0]
            for vi in e: parent[root(corner(a,vi))]=root(corner(b,vi))
    roots=sorted({root(i) for i in range(3*n)}); index={r:i for i,r in enumerate(roots)}
    cf=np.array([index[root(i)] for i in range(3*n)]).reshape(n,3)
    g=[set() for _ in roots]; cutedges=defaultdict(int)
    for t in cf:
        for a,b in zip(t,np.roll(t,-1)):
            a,b=int(a),int(b)
            if a==b: raise Reject("collapsed cut topology")
            g[a].add(b); g[b].add(a); cutedges[tuple(sorted((a,b)))]+=1
    if len(roots)-len(cutedges)+n!=1 or any(c>2 for c in cutedges.values()): raise Reject("cut not a disk")
    bd=defaultdict(set)
    for (a,b),c in cutedges.items():
        if c==1: bd[a].add(b); bd[b].add(a)
    if not bd or any(len(x)!=2 for x in bd.values()): raise Reject("cut boundary not cycle")
    reached=set(); stack=[next(iter(bd))]
    while stack:
        u=stack.pop()
        if u in reached: continue
        reached.add(u); stack.extend(bd[u]-reached)
    if reached!=set(bd): raise Reject("multiple boundary cycles")
    pinned={}
    def pin(node,value):
        value=np.asarray(value,float)
        if node in pinned and np.max(np.abs(pinned[node]-value))>1e-9: raise Reject("conflicting corner pin")
        pinned[node]=value
    for e,values in source.items():
        i=incidence[e][0][0]
        for vi,uv in values.items(): pin(cf[i,corner(i,vi)%3],uv)
    # Trace each copy of the prescribed seam in the cut mesh.
    layers=[]
    for vi in path:
        nodes={int(cf[i,j]) for i,j in zip(*np.where(f==vi))}
        if len(nodes)!=2: raise Reject("seam vertex did not split into two")
        layers.append(nodes)
    arc=np.r_[0.,np.cumsum([np.linalg.norm(v[a]-v[b]) for a,b in zip(path,path[1:])])]
    if arc[-1]<=0: raise Reject("zero seam length")
    for start in sorted(layers[0]):
        u=float(pinned[start][0]); current=start
        if u not in (0.,1.): raise Reject("invalid seam endpoint")
        for k in range(1,len(path)):
            candidates=layers[k]&bd[current]
            if len(candidates)!=1: raise Reject("ambiguous seam side")
            current=next(iter(candidates)); pin(current,(u,float(arc[k]/arc[-1])))
    if set(pinned)!=set(bd): raise Reject("incomplete cut boundary pins")
    free=sorted(set(range(len(roots)))-set(pinned)); uv=np.zeros((len(roots),2))
    for i,p in pinned.items(): uv[i]=p
    if free:
        fi={v:i for i,v in enumerate(free)}; A=np.zeros((len(free),len(free))); B=np.zeros((len(free),2))
        for k,i in enumerate(free):
            A[k,k]=len(g[i])
            for j in g[i]:
                if j in fi: A[k,fi[j]]-=1
                else: B[k]+=uv[j]
        try: uv[free]=np.linalg.solve(A,B)
        except np.linalg.LinAlgError as exc: raise Reject("singular harmonic solve") from exc
        if np.max(np.abs(A@uv[free]-B))>1e-8: raise Reject("harmonic residual")
    if not np.isfinite(uv).all(): raise Reject("nonfinite result")
    out=uv[cf]; gap=max(float(np.max(np.abs(out[incidence[e][0][0],corner(incidence[e][0][0],vi)%3]-p))) for e,values in source.items() for vi,p in values.items())
    return out,dict(path=path,seam_edges=len(seam),boundary_error=gap,cut_vertices=len(roots),free_vertices=len(free))
