"""R6: fixed static shell thickness, closed edge rims, named edge strips.
No cloth mechanics, no raised elastic geometry, no global intersection proof.
"""
from collections import Counter,defaultdict
import math
from patch import cross,sub,dot
from boundary import norm

THICKNESS=.012

def triangles(f):
    return ((f[0],f[1],f[2]),(f[0],f[2],f[3]))

def normal(p,t):
    a,b,c=(p[i] for i in t)
    return cross(sub(b,a),sub(c,a))

def shell(points,faces,loops,thickness=THICKNESS):
    if thickness!=THICKNESS or not 4<=len(points)<=10000:
        raise ValueError("fixed thickness and bounded mesh")
    if any(len(p)!=3 or not all(map(math.isfinite,p)) for p in points):
        raise ValueError("invalid vertices")
    n=len(points);edges=defaultdict(list);normals=[[0.,0.,0.] for _ in points]
    for j,f in enumerate(faces):
        if len(f)!=4 or len(set(f))!=4 or min(f)<0 or max(f)>=n:raise ValueError("invalid quad")
        for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted((a,b)))].append((a,b,j))
        for t in triangles(f):
            v=normal(points,t)
            for i in t:
                for k in range(3):normals[i][k]+=v[k]
    if any(len(v)>2 or (len(v)==2 and v[0][:2]!=v[1][:2][::-1]) for v in edges.values()):
        raise ValueError("bad source edge incidence")
    roles={}
    if len(loops)!=3 or len(set(i for l in loops for i in l))!=sum(map(len,loops)):
        raise ValueError("three disjoint loops required")
    for role,l in zip(("waist","left","right"),loops):
        for a,b in zip(l,l[1:]+l[:1]):roles[tuple(sorted((a,b)))]=role
    if set(roles)!={e for e,v in edges.items() if len(v)==1}:raise ValueError("source boundary mismatch")
    if any(norm(v)<1e-12 for v in normals):raise ValueError("undefined vertex normal")
    inner=[tuple(x-thickness*y/norm(v) for x,y in zip(p,v)) for p,v in zip(points,normals)]
    out=list(points)+inner
    quads=list(faces)+[tuple(i+n for i in f[::-1]) for f in faces]
    groups=["outer"]*len(faces)+["inner"]*len(faces)
    for e,role in sorted(roles.items()):
        a,b,j=edges[e][0]
        groups[j]="edge_strip_"+role
        quads.append((b,a,a+n,b+n));groups.append("rim_"+role)
    return out,quads,groups

def audit(source,source_faces,loops,points,faces,groups):
    n=len(source);m=len(source_faces)
    if len(points)!=2*n or len(groups)!=len(faces):raise ValueError("bad shell dimensions")
    edges=Counter();direction=Counter();adj=defaultdict(set)
    links=defaultdict(lambda:defaultdict(set));used=set()
    min_area=math.inf;volume=0.
    for f in faces:
        if len(f)!=4 or len(set(f))!=4 or min(f)<0 or max(f)>=len(points):raise ValueError("bad shell quad")
        used.update(f)
        for k,a in enumerate(f):
            b=f[(k+1)%4];c=f[(k-1)%4];e=tuple(sorted((a,b)))
            edges[e]+=1;direction[e]+=1 if a<b else -1
            adj[a].add(b);adj[b].add(a);links[a][b].add(c);links[a][c].add(b)
        for t in triangles(f):
            a,b,c=(points[i] for i in t)
            min_area=min(min_area,norm(normal(points,t))/2)
            volume+=dot(a,cross(b,c))/6
    def components(g):
        todo=set(g);count=0
        while todo:
            count+=1;stack=[todo.pop()]
            while stack:
                for v in g[stack.pop()]&todo:todo.remove(v);stack.append(v)
        return count
    vertex_link_errors=sum(any(len(v)!=2 for v in g.values()) or components(g)!=1 for g in links.values())
    min_alignment=1.;local_inversions=0
    for f in source_faces:
        for t in triangles(f):
            a=normal(source,t);b=normal(points,tuple(i+n for i in t))
            den=norm(a)*norm(b);c=dot(a,b)/den if den else -1.
            min_alignment=min(min_alignment,c);local_inversions+=int(c<=0)
    thicknesses=[math.dist(points[i],points[i+n]) for i in range(n)]
    # Test layer direction against incident source triangle normals, not stored normals.
    bad_direction=0
    for f in source_faces:
        for t in triangles(f):
            v=normal(source,t)
            bad_direction+=sum(dot(sub(points[i],points[i+n]),v)<=0 for i in t)
    outer_drift=max(math.dist(source[i],points[i]) for i in range(n))
    role_counts=Counter(groups)
    rim_ok=all(role_counts["rim_"+role]==len(l) and role_counts["edge_strip_"+role]>0 for role,l in zip(("waist","left","right"),loops))
    layer_faces_ok=faces[:m]==list(source_faces) and faces[m:2*m]==[tuple(i+n for i in f[::-1]) for f in source_faces]
    out=dict(vertices=len(points),quads=len(faces),euler=len(points)-len(edges)+len(faces),
        components=components(adj),unused=len(points)-len(used),open_edges=sum(k==1 for k in edges.values()),
        nonmanifold_edges=sum(k>2 for k in edges.values()),orientation_errors=sum(k==2 and direction[e]!=0 for e,k in edges.items()),
        vertex_link_errors=vertex_link_errors,min_triangle_area=min_area,signed_volume=volume,
        min_thickness=min(thicknesses),max_thickness=max(thicknesses),outer_drift=outer_drift,
        min_inner_alignment=min_alignment,local_inversions=local_inversions,bad_layer_direction=bad_direction,
        rim_counts=dict(role_counts),rim_ok=rim_ok,layer_faces_ok=layer_faces_ok)
    out["passed"]=out["euler"]==-2 and out["components"]==1 and not any(out[k] for k in ("unused","open_edges","nonmanifold_edges","orientation_errors","vertex_link_errors","local_inversions","bad_layer_direction")) and min_area>1e-8 and volume>0 and max(abs(t-THICKNESS) for t in thicknesses)<1e-10 and outer_drift<1e-12 and rim_ok and layer_faces_ok
    return out
