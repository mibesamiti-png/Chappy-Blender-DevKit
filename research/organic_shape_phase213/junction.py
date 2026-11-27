"""R3 bounded one-to-two surface junction, no body fitting or cloth physics."""
from collections import Counter,defaultdict
import math
from patch import sub,dot,cross
from boundary import norm

def mesh(width=1.35,depth=.75,separation=.68,method='linear'):
    if method not in ('linear','tangent'):
        raise ValueError('fixed junction methods only')
    if not (1.2<=width<=1.6 and .65<=depth<=.95 and .60<=separation<=.85):
        raise ValueError("bounded synthetic fixture")
    n=48;half=n//2
    pts=[];faces=[]
    def add(p):
        pts.append(tuple(p));return len(pts)-1
    def ring(cx,rx,ry,z,start):
        return [add((cx+rx*math.cos(start+math.tau*i/n),ry*math.sin(start+math.tau*i/n),z)) for i in range(n)]
    def loft(a,b,steps,branch=False):
        prev=a
        for j in range(1,steps+1):
            t=j/steps
            def point(index,i,k):
                A,B=pts[i],pts[k]
                weight=math.sin(math.pi*(index-half)/half) if method=='tangent' and branch and index>half else 0.
                q=(1-weight)*t+weight*t*t*(3-2*t)
                return (A[0]+t*(B[0]-A[0]),A[1]+q*(B[1]-A[1]),A[2]+q*(B[2]-A[2]))
            nxt=b if j==steps else [add(point(index,i,k)) for index,(i,k) in enumerate(zip(a,b))]
            faces.extend((prev[i],nxt[i],nxt[(i+1)%n],prev[(i+1)%n]) for i in range(n))
            prev=nxt
    top=ring(0,width,depth,1.4,math.pi/2)
    mid=ring(0,width,depth,.55,math.pi/2)
    loft(top,mid,8)
    # Both branches share this exact seam, in opposite traversal directions.
    bridge=[add((0.,-depth+2*depth*j/half,.55-.65*math.sin(math.pi*j/half))) for j in range(1,half)]
    left=mid[:half+1]+bridge
    right=mid[half:]+[mid[0]]+bridge[::-1]
    low_l=ring(-separation,.46,.54,-1.2,math.pi/2)
    low_r=ring(separation,.46,.54,-1.2,3*math.pi/2)
    loft(left,low_l,12,True);loft(right,low_r,12,True)
    return pts,faces,(top,low_l,low_r)

def smooth(pts,faces,loops,steps=16):
    if steps not in (0,8,16,32):raise ValueError("bounded smoothing plan")
    fixed=set(i for l in loops for i in l);adj=defaultdict(set)
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]):adj[a].add(b);adj[b].add(a)
    out=list(pts)
    for _ in range(steps):
        # Taubin-style paired passes; fixed boundary coordinates are exact.
        for w in (.45,-.47):
            src=out
            out=[p if i in fixed else tuple(x+w*(sum(src[j][k] for j in sorted(adj[i]))/len(adj[i])-x) for k,x in enumerate(p)) for i,p in enumerate(src)]
    return out

def audit(pts,faces,loops,reference):
    if any(len(p)!=3 or not all(map(math.isfinite,p)) for p in pts):
        raise ValueError("invalid coordinates")
    edges=Counter();directions=Counter();adj=defaultdict(set);edge_normals=defaultdict(list)
    links=defaultdict(lambda:defaultdict(set))
    area=math.inf;ratio=0.;min_quad_cos=1.;used=set()
    for f in faces:
        if len(f)!=4 or len(set(f))!=4 or min(f)<0 or max(f)>=len(pts):raise ValueError("invalid face")
        used.update(f);a,b,c,d=(pts[i] for i in f)
        x=cross(sub(b,a),sub(c,a));y=cross(sub(c,a),sub(d,a))
        lx,ly=norm(x),norm(y);area=min(area,lx/2,ly/2)
        min_quad_cos=min(min_quad_cos,dot(x,y)/(lx*ly) if lx*ly else -1.)
        fn=tuple(a+b for a,b in zip(x,y))
        lens=[math.dist(pts[i],pts[j]) for i,j in zip(f,f[1:]+f[:1])]
        ratio=max(ratio,max(lens)/min(lens) if min(lens)>0 else math.inf)
        for k,i in enumerate(f):
            j=f[(k+1)%4];prev=f[(k-1)%4]
            e=tuple(sorted((i,j)));edges[e]+=1;directions[e]+=1 if i<j else -1
            adj[i].add(j);adj[j].add(i);edge_normals[e].append(fn)
            links[i][prev].add(j);links[i][j].add(prev)
    def components(graph):
        unseen=set(graph);out=[]
        while unseen:
            stack=[unseen.pop()];seen=set(stack)
            while stack:
                for j in graph[stack.pop()]&unseen:
                    unseen.remove(j);seen.add(j);stack.append(j)
            out.append(seen)
        return out
    border=defaultdict(set)
    for (i,j),v in edges.items():
        if v==1:border[i].add(j);border[j].add(i)
    found=components(border)
    expected={frozenset(l) for l in loops}
    link_errors=0
    for i,g in links.items():
        ds=sorted(len(v) for v in g.values())
        valid=(ds.count(1)==2 and all(d in (1,2) for d in ds)) if i in border else all(d==2 for d in ds)
        link_errors+=int(not valid or len(components(g))!=1)
    angles=[]
    for ns in edge_normals.values():
        if len(ns)==2:
            a,b=ns;den=norm(a)*norm(b)
            angles.append(math.degrees(math.acos(max(-1.,min(1.,dot(a,b)/den)))) if den else 180.)
    angles.sort()
    drift=max(math.dist(pts[i],reference[i]) for l in loops for i in l)
    out=dict(vertices=len(pts),quads=len(faces),euler=len(pts)-len(edges)+len(faces),
        components=len(components(adj)),unused=len(pts)-len(used),boundary_loops=len(found),
        boundary_roles_ok={frozenset(l) for l in found}==expected,
        boundary_degrees_ok=all(len(g)==2 for g in border.values()),vertex_link_errors=link_errors,
        nonmanifold_edges=sum(k>2 for k in edges.values()),orientation_errors=sum(k==2 and directions[e]!=0 for e,k in edges.items()),
        min_triangle_area=area,max_edge_ratio=ratio,min_quad_cos=min_quad_cos,
        max_normal_jump=max(angles),p95_normal_jump=angles[math.floor(.95*(len(angles)-1))],boundary_drift=drift)
    out["topology_pass"]=out["euler"]==-1 and out["components"]==1 and out["unused"]==0 and out["boundary_loops"]==3 and out["boundary_roles_ok"] and out["boundary_degrees_ok"] and not any(out[k] for k in ("vertex_link_errors","nonmanifold_edges","orientation_errors"))
    out["quality_pass"]=area>1e-7 and ratio<=20 and min_quad_cos>0 and drift<1e-12 and out["max_normal_jump"]<=100
    out["passed"]=out["topology_pass"] and out["quality_pass"]
    return out
