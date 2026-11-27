"""R2 pilot: periodic annular quad patch between R1 boundaries.
A common chart correspondence avoids twisting independently sampled loops.
This is a constrained ellipsoid patch, not arbitrary boundary reconstruction.
"""
from collections import Counter,defaultdict
from dataclasses import dataclass
import math
from boundary import Boundary,norm,TAU

def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

@dataclass(frozen=True)
class Patch:
    lower: Boundary
    upper: Boundary
    def __post_init__(self):
        if self.lower.surface!=self.upper.surface or len(self.lower.controls)!=len(self.upper.controls):
            raise ValueError("common surface and knot count required")
        # Convex spline basis proves strict ordering over the entire chart.
        if min(b-a for a,b in zip(self.lower.controls,self.upper.controls))<.15:
            raise ValueError("ordered, separated control pairs required")
    def at(self,u,v):
        lat=(1-v)*self.lower.latitude(u)+v*self.upper.latitude(u)
        h=(1-v)*self.lower.offset+v*self.upper.offset
        p,n=self.lower.surface.point_normal(TAU*(u%1),lat)
        q=tuple(x+h*y for x,y in zip(p,n))
        return p,q,h
    def mesh(self,n=96,m=12):
        if type(n) is not int or type(m) is not int or not 32<=n<=256 or not 2<=m<=64:
            raise ValueError("bounded mesh budget required")
        # Equal-arc sampling of a shared midline fixes the correspondence.
        mid=Boundary(self.lower.surface,tuple((a+b)/2 for a,b in zip(self.lower.controls,self.upper.controls)),(self.lower.offset+self.upper.offset)/2)
        us=[r["u"] for r in mid.sample(n)]
        rows=[dict(u=u,v=j/m,base=p,point=q,offset=h) for j in range(m+1) for u in us for p,q,h in [self.at(u,j/m)]]
        faces=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(m) for i in range(n)]
        return rows,faces

def audit(patch,rows,faces):
    """Measure from actual vertices and faces, not a predicted topology."""
    if not rows or not faces or any(len(f)!=4 or len(set(f))!=4 or min(f)<0 or max(f)>=len(rows) for f in faces):
        raise ValueError("invalid quad mesh")
    pts=[r["point"] for r in rows]
    if any(len(p)!=3 or not all(math.isfinite(x) for x in p) for p in pts):
        raise ValueError("invalid points")
    edges=Counter();orient=Counter();neighbors=defaultdict(set);used=set()
    residual=offset_error=boundary_error=0.
    minimum_area=math.inf;max_aspect=0.;min_normal=1.;max_normal_jump=0.;edge_normals=defaultdict(list)
    axes=patch.lower.surface.axes
    for r in rows:
        p,q=r["base"],r["point"]
        raw=tuple(x/a**2 for x,a in zip(p,axes))
        residual=max(residual,abs(sum((x/a)**2 for x,a in zip(p,axes))-1))
        h=(1-r["v"])*patch.lower.offset+r["v"]*patch.upper.offset
        offset_error=max(offset_error,norm(sub(sub(q,p),tuple(h*x/norm(raw) for x in raw))))
        if r["v"] in (0.,1.):
            b=patch.lower if r["v"]==0. else patch.upper
            boundary_error=max(boundary_error,math.dist(q,b.at(r["u"])[2]))
    for f in faces:
        used.update(f)
        a,b,c,d=(pts[i] for i in f)
        x=cross(sub(b,a),sub(c,a));y=cross(sub(c,a),sub(d,a))
        minimum_area=min(minimum_area,norm(x)/2,norm(y)/2)
        mid=tuple(sum(rows[i]["base"][j] for i in f)/4 for j in range(3))
        grad=tuple(v/k**2 for v,k in zip(mid,axes))
        for v in (x,y):
            min_normal=min(min_normal,dot(v,grad)/(norm(v)*norm(grad)) if norm(v)>0 else -1.)
        lengths=[math.dist(pts[i],pts[j]) for i,j in zip(f,f[1:]+f[:1])]
        max_aspect=max(max_aspect,max(lengths)/min(lengths) if min(lengths)>0 else math.inf)
        fn=tuple(a+b for a,b in zip(x,y))
        for i,j in zip(f,f[1:]+f[:1]):
            e=tuple(sorted((i,j)));edges[e]+=1;orient[e]+=1 if i<j else -1
            neighbors[i].add(j);neighbors[j].add(i)
            edge_normals[e].append(fn)
    for ns in edge_normals.values():
        if len(ns)==2 and min(map(norm,ns))>0:
            x,y=ns;max_normal_jump=max(max_normal_jump,math.degrees(math.acos(max(-1.,min(1.,dot(x,y)/(norm(x)*norm(y)))))))
    border=defaultdict(set)
    for (i,j),k in edges.items():
        if k==1:border[i].add(j);border[j].add(i)
    def components(graph):
        remaining=set(graph);out=[]
        while remaining:
            stack=[remaining.pop()];seen=set(stack)
            while stack:
                for j in graph[stack.pop()] & remaining:
                    remaining.remove(j);seen.add(j);stack.append(j)
            out.append(seen)
        return out
    loops=components(border)
    boundary_roles=sorted(tuple(sorted({rows[i]["v"] for i in loop})) for loop in loops)
    result=dict(vertices=len(rows),quads=len(faces),euler=len(rows)-len(edges)+len(faces),
        components=len(components(neighbors)),unused=len(rows)-len(used),boundary_loops=len(loops),
        boundary_degrees_ok=all(len(v)==2 for v in border.values()),boundary_roles_ok=boundary_roles==[(0.,),(1.,)],
        nonmanifold_edges=sum(k>2 for k in edges.values()),orientation_errors=sum(k==2 and orient[e]!=0 for e,k in edges.items()),
        surface_residual=residual,offset_error=offset_error,boundary_error=boundary_error,min_triangle_area=minimum_area,
        max_edge_ratio=max_aspect,min_outward_cos=min_normal,max_normal_jump_degrees=max_normal_jump)
    result["passed"]=result["euler"]==0 and result["components"]==1 and result["unused"]==0 and result["boundary_loops"]==2 and result["boundary_degrees_ok"] and result["boundary_roles_ok"] and result["nonmanifold_edges"]==0 and result["orientation_errors"]==0 and max(residual,offset_error,boundary_error)<1e-10 and minimum_area>1e-8 and max_aspect<=8 and min_normal>.9 and max_normal_jump<=20
    return result
