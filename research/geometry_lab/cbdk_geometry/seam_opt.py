"""R13 research: Pareto-safe internal UV seam graph optimization.

Two charts: exact binary s-t cuts for count, length and hybrid Potts costs.
3+ charts: deterministic ICM of the same costs, no global optimality claim.
Original source-boundary face chart pins stay fixed; XYZ/face indices unchanged.
"""
from collections import defaultdict,deque
from time import monotonic
import numpy as np


def _binary_min_cut(n,links,fixed,weights,deadline):
    source,sink=n,n+1
    graph=[[] for _ in range(n+2)]
    def edge(u,v,c):
        graph[u].append([v,float(c),len(graph[v])])
        graph[v].append([u,0.,len(graph[u])-1])
    total=0.
    for (u,v,_),weight in zip(links,weights):
        if weight<=0 or not np.isfinite(weight):
            raise ValueError("nonpositive cut capacity")
        edge(u,v,weight)
        edge(v,u,weight)
        total+=weight
    hard=total+1.
    for i,label in sorted(fixed.items()):
        if label==0:edge(source,i,hard)
        else:edge(i,sink,hard)
    eps=1e-11
    while True:
        if monotonic()>deadline:raise TimeoutError("R13 mincut time budget")
        level=[-1]*(n+2)
        level[source]=0
        queue=deque([source])
        while queue:
            u=queue.popleft()
            for v,cap,rev in graph[u]:
                if cap>eps and level[v]<0:
                    level[v]=level[u]+1
                    queue.append(v)
        if level[sink]<0:break
        indices=[0]*(n+2)
        def dfs(u,flow):
            if u==sink:return flow
            while indices[u]<len(graph[u]):
                e=graph[u][indices[u]]
                v,cap,rev=e
                if cap>eps and level[v]==level[u]+1:
                    pushed=dfs(v,min(flow,cap))
                    if pushed>eps:
                        e[1]-=pushed
                        graph[v][rev][1]+=pushed
                        return pushed
                indices[u]+=1
            return 0.
        while dfs(source,hard)>eps:
            pass
    reached={source}
    queue=deque([source])
    while queue:
        u=queue.popleft()
        for v,cap,rev in graph[u]:
            if cap>eps and v not in reached:
                reached.add(v)
                queue.append(v)
    labels=np.array([0 if i in reached else 1 for i in range(n)],dtype=int)
    if any(labels[i]!=label for i,label in fixed.items()):
        raise RuntimeError("mincut violated hard source constraints")
    return labels


def _icm(n,links,initial,fixed,weights,deadline):
    labels=initial.copy()
    adjacent=[[] for _ in range(n)]
    for (u,v,_),weight in zip(links,weights):
        adjacent[u].append((v,weight))
        adjacent[v].append((u,weight))
    for _ in range(40):
        changed=False
        for face in range(n):
            if face in fixed:continue
            choices=sorted({int(labels[face])}|
                           {int(labels[neighbor]) for neighbor,_ in adjacent[face]})
            def cost(k):
                return sum(w for neighbor,w in adjacent[face] if labels[neighbor]!=k)
            old=cost(labels[face])
            winner=min(choices,key=lambda k:(cost(k),k!=labels[face],k))
            if cost(winner)<old-1e-9:
                labels[face]=winner
                changed=True
        if monotonic()>deadline:raise TimeoutError("R13 ICM time budget")
        if not changed:break
    return labels


def optimize_uv_charts(vertices,faces,boundary_offsets,baseline,seconds=10.0):
    """Return new per-face UV translations and count/length diagnostics.

    Finite 3D vertex array, triangulated strip, and complete boundary offsets
    are required. Chart offset equality tolerance: 5 decimals (UV source noise).
    """
    if isinstance(seconds,bool) or not np.isfinite(seconds) or not 0<seconds<=60:
        raise ValueError("R13 requires finite positive time budget")
    started=monotonic()
    deadline=started+seconds
    v=np.asarray(vertices,dtype=float)
    f=np.asarray(faces,dtype=int)
    baseline=np.asarray(baseline,dtype=float)
    if (v.ndim!=2 or v.shape[1]!=3 or f.ndim!=2 or f.shape[1]!=3
            or baseline.shape!=(len(f),2) or not 2<=len(f)<=600):
        raise ValueError("R13 geometry dimensions or face budget")
    if (not np.isfinite(v).all() or not np.isfinite(baseline).all()
            or not np.all((f>=0)&(f<len(v)))):
        raise ValueError("R13 nonfinite or invalid geometry")
    incidence=defaultdict(list)
    for i,tri in enumerate(f):
        for a,b in zip(tri,np.roll(tri,-1)):
            incidence[tuple(sorted((int(a),int(b))))].append(i)
    boundary={edge:refs[0] for edge,refs in incidence.items() if len(refs)==1}
    if set(boundary_offsets)!=set(boundary):
        raise ValueError("missing/unexpected R13 boundary constraints")
    chart_keys=sorted({tuple(np.round(point,5)) for point in baseline})
    name={key:i for i,key in enumerate(chart_keys)}
    labels=np.asarray([name[tuple(np.round(point,5))] for point in baseline],dtype=int)
    fixed={}
    for edge,fi in sorted(boundary.items()):
        expected=np.asarray(boundary_offsets[edge],dtype=float)
        if (expected.shape!=(2,) or not np.isfinite(expected).all()
                or np.max(np.abs(expected-baseline[fi]))>1e-5):
            raise ValueError("source boundary offset differs from R12")
        if fi in fixed and fixed[fi]!=labels[fi]:
            raise ValueError("one face has conflicting chart labels")
        fixed[fi]=int(labels[fi])
    links=[]
    for edge,adj in sorted(incidence.items()):
        if len(adj)==2:
            u,w=adj
            length=float(np.linalg.norm(v[edge[0]]-v[edge[1]]))
            if not np.isfinite(length) or length<=1e-10:
                raise ValueError("degenerate seam-edge length")
            links.append((u,w,length))
        elif len(adj)>2:
            raise ValueError("nonmanifold research strip")
    if not links:raise ValueError("strip has no interior edges")
    median_length=float(np.median([link[2] for link in links]))
    def score(lab):
        cut=[edge for edge in links if lab[edge[0]]!=lab[edge[1]]]
        return len(cut),float(sum(edge[2] for edge in cut))
    original=score(labels)
    candidates=[("original",labels.copy(),original)]
    if len(chart_keys)>1:
        for method in ("count","length","hybrid"):
            weights=[1. if method=="count" else length if method=="length"
                     else (.5+.5*length/median_length) for _,_,length in links]
            if len(chart_keys)==2:
                attempt=_binary_min_cut(len(f),links,fixed,weights,deadline)
            else:
                attempt=_icm(len(f),links,labels,fixed,weights,deadline)
            candidates.append((method,attempt,score(attempt)))
    possible=[choice for choice in candidates
              if choice[2][0]<=original[0] and choice[2][1]<=original[1]+1e-8]
    chosen=min(possible,
               key=lambda choice:(choice[2][1],choice[2][0],
                                  choice[0]!="original",choice[0]))
    representative={label:np.median(baseline[labels==label],axis=0)
                    for label in range(len(chart_keys))}
    result=np.asarray([representative[label] for label in chosen[1]])
    for face in fixed:
        result[face]=baseline[face]
    final=score(chosen[1])
    return result,dict(method=chosen[0],chart_count=len(chart_keys),
                       old_seams=original[0],old_length=original[1],
                       new_seams=final[0],new_length=final[1],
                       count_reduction=(original[0]-final[0])/(original[0] or 1),
                       length_reduction=(original[1]-final[1])/(original[1] or 1),
                       elapsed_seconds=monotonic()-started,
                       pinned_face_count=len(fixed))
