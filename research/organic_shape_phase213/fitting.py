"""R4 pilot: radial fitting to an independently defined organic torso field.
Static single-valued cross sections, no branch or general closest-point solver.
"""
from dataclasses import dataclass
import math
from boundary import Ellipsoid,Boundary
from patch import Patch
from junction import audit as mesh_audit

@dataclass(frozen=True)
class Target:
    hip: float
    depth: float
    back: float
    def __post_init__(self):
        if not (.22<=self.hip<=.45 and .12<=self.depth<=.32 and 0<=self.back<=.14):
            raise ValueError("fixed synthetic parameter range")
    def section(self,z):
        if not math.isfinite(z) or abs(z)>1.3:
            raise ValueError("outside torso chart")
        g=math.exp(-((z+.32)/.64)**2)
        return .72+self.hip*g,.53+self.depth*g,-self.back*g
    def field(self,x,y,z):
        a,b,c=self.section(z)
        return (x/a)**2+((y-c)/b)**2-1
    def ray(self,theta,z):
        dx,dy=math.cos(theta),math.sin(theta)
        lo,hi=0.,2.
        if not self.field(0,0,z)<0<self.field(hi*dx,hi*dy,z):
            raise ValueError("unbracketed ray")
        for _ in range(48):
            r=(lo+hi)/2
            if self.field(r*dx,r*dy,z)>0:hi=r
            else:lo=r
        return (lo+hi)/2
    def reference_radius(self,theta,z):
        # Closed-form quadratic intersection, independent of bisection.
        a,b,c=self.section(z)
        x,y=math.cos(theta),math.sin(theta)
        A=(x/a)**2+(y/b)**2;B=-2*y*c/b**2;C=(c/b)**2-1
        return (-B+math.sqrt(B*B-4*A*C))/(2*A)

def source():
    s=Ellipsoid((1.,.8,1.3))
    return Patch(Boundary(s,(-.72,)*8),Boundary(s,(.62,)*8)).mesh(96,24)

def fit(points,target,gap=.035):
    if not math.isfinite(gap) or not .015<=gap<=.06:
        raise ValueError("bounded radial gap required")
    out=[]
    for x,y,z in points:
        if not all(map(math.isfinite,(x,y,z))) or math.hypot(x,y)<1e-8:
            raise ValueError("invalid radial source")
        t=math.atan2(y,x);r=target.ray(t,z)+gap
        out.append((r*math.cos(t),r*math.sin(t),z))
    return out

def audit(source_points,points,faces,target,gap=.035):
    if len(source_points)!=len(points) or len(points)!=96*25:
        raise ValueError("fixed mesh budget")
    expected=[]
    vertex_errors=[];height_errors=[];direction_errors=[]
    for (x,y,z),(X,Y,Z) in zip(source_points,points):
        t=math.atan2(y,x);r=target.reference_radius(t,z)+gap
        expected.append((r*math.cos(t),r*math.sin(t),z))
        vertex_errors.append(math.dist(points[len(expected)-1],expected[-1]))
        height_errors.append(abs(Z-z))
        direction_errors.append(abs(math.atan2(math.sin(math.atan2(Y,X)-t),math.cos(math.atan2(Y,X)-t))))
    loops=(list(range(96)),list(range(96*24,96*25)))
    m=mesh_audit(points,faces,loops,expected)
    # Same topology audit, but annulus has Euler 0 and two boundaries.
    topology=m["euler"]==0 and m["components"]==1 and m["unused"]==0 and m["boundary_loops"]==2 and m["boundary_roles_ok"] and m["boundary_degrees_ok"] and not any(m[k] for k in ("vertex_link_errors","nonmanifold_edges","orientation_errors"))
    gaps=[];outward=[]
    def measure(p):
        x,y,z=p;t=math.atan2(y,x)
        gaps.append(math.hypot(x,y)-target.reference_radius(t,z))
    for p in points:measure(p)
    for f in faces:
        for tri in ((f[0],f[1],f[2]),(f[0],f[2],f[3])):
            a,b,c=(points[i] for i in tri)
            for weights in ((.5,.5,0),(.5,0,.5),(0,.5,.5),(1/3,1/3,1/3)):
                measure(tuple(sum(w*p[k] for w,p in zip(weights,(a,b,c))) for k in range(3)))
            from patch import cross,sub,dot
            n=cross(sub(b,a),sub(c,a))
            x,y,z=tuple((a[k]+b[k]+c[k])/3 for k in range(3))
            outward.append(dot(n,(x,y,0.)))
    result=dict(topology_pass=topology,vertices=len(points),quads=len(faces),boundary_loops=m["boundary_loops"],
        vertex_error=max(vertex_errors),height_error=max(height_errors),direction_error=max(direction_errors),
        min_sampled_radial_gap=min(gaps),max_sampled_radial_gap=max(gaps),gap_samples=len(gaps),
        inward_triangles=sum(v<=0 for v in outward),max_edge_ratio=m["max_edge_ratio"],max_normal_jump=m["max_normal_jump"],
        min_triangle_area=m["min_triangle_area"],min_quad_cos=m["min_quad_cos"])
    result["passed"]=topology and max(vertex_errors)<1e-10 and max(height_errors)<1e-12 and max(direction_errors)<1e-12 and min(gaps)>.005 and max(gaps)<.065 and result["inward_triangles"]==0 and m["max_edge_ratio"]<=8 and m["max_normal_jump"]<=20 and m["min_triangle_area"]>1e-7 and m["min_quad_cos"]>0
    return result
