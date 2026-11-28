"""R9A: independently control side fabric height without changing waist or cuts.
A bounded azimuth-weighted monotone height warp on the accepted R7D surface.
Widths are vertical distances in fixture units, not surface arc lengths.
"""
import math
from garment import TARGET,GAP,WAIST
from fair_garment import trial as source_trial
from cut_garment import inspect_cut
from intersection import audit as intersection_audit

WIDTHS=(.48,.32,.18)
DEPTH=.82

def crossings(points,loop,theta):
    c,s=math.cos(theta),math.sin(theta)
    values=[]
    for i,j in zip(loop,loop[1:]+loop[:1]):
        a,b=points[i],points[j]
        u=-s*a[0]+c*a[1];v=-s*b[0]+c*b[1]
        if abs(u)<1e-12 and c*a[0]+s*a[1]>0:values.append(a[2])
        if u*v<0:
            t=u/(u-v)
            if c*(a[0]+t*(b[0]-a[0]))+s*(a[1]+t*(b[1]-a[1]))>0:
                values.append(a[2]+t*(b[2]-a[2]))
    if not values:raise ValueError("missing ray crossing")
    return values

def widths(points,loops):
    return [max(crossings(points,loops[0],theta))-max(crossings(points,loops[i],theta)) for i,theta in ((1,math.pi),(2,0.))]

def deform(points,loops,width):
    if width not in WIDTHS:raise ValueError("fixed side width fixtures")
    parameters=[]
    for i,theta in ((1,math.pi),(2,0.)):
        top=max(crossings(points,loops[0],theta))
        hem=max(crossings(points,loops[i],theta))
        a=(hem+DEPTH)/(top+DEPTH)
        b=(top-width+DEPTH)/(top+DEPTH)
        if not 0<a<1 or not 0<b<1:raise ValueError("unreachable width")
        parameters.append((a*(1-b))/(b*(1-a)))
    fixed=set(loops[0])
    out=[]
    for i,(x,y,z) in enumerate(points):
        r=math.hypot(x,y)
        if i in fixed or r<1e-10 or abs(x)<1e-12:
            out.append((x,y,z));continue
        theta=math.atan2(y,x)
        top=.40+WAIST.latitude((theta-math.pi/2)/math.tau)
        t=(z+DEPTH)/(top+DEPTH)
        if not 0<t<1:
            out.append((x,y,z));continue
        weight=(abs(x)/r)**6
        k=math.exp(weight*math.log(parameters[0 if x<0 else 1]))
        new_z=(top+DEPTH)*t/(t+k*(1-t))-DEPTH
        def nominal(h):
            scale=math.sqrt(max(0.,1-(min(h,0.)/DEPTH)**2))
            return (TARGET.reference_radius(theta,h)+GAP)*scale
        old_r=nominal(z)
        if old_r<1e-10:raise ValueError("singular radius")
        new_r=nominal(new_z)*r/old_r
        out.append((x*new_r/r,y*new_r/r,new_z))
    return out

def trial(width,check_intersection=True,source=None):
    if source is None:
        p,q,l,r=source_trial()
        assert r["fixture_gate"]
    else:p,q,l=source
    out=deform(p,l,width)
    m=inspect_cut(out,q,l,out)
    actual=widths(out,l)
    drift=max(math.dist(p[i],out[i]) for i in l[0])
    center_drift=max(math.dist(a,b) for a,b in zip(p,out) if abs(a[0])<1e-12)
    collision=intersection_audit(out,q) if check_intersection else None
    passed=m["cut_pilot_pass"] and max(abs(w-width) for w in actual)<=.015 and drift==0 and center_drift==0 and m["max_normal_jump"]<=30 and collision is not None and collision["passed"]
    return dict(requested_width=width,actual_widths=actual,original_widths=widths(p,l),waist_drift=drift,center_plane_drift=center_drift,metrics=m,nonincident_intersection=collision,passed=passed),out,q,l
