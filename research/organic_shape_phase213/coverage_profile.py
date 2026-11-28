"""R9B: independently vary front/rear leg-opening height near the diagonal rays.

Preserve the waist, side and sagittal planes; use R9A as the base.
Coverage is a vertical height difference, not fabric area or center-front depth.
"""
import math
from garment import TARGET,GAP,WAIST
from side_width import DEPTH,crossings,widths,deform as side_deform
from fair_garment import trial as source_trial
from cut_garment import inspect_cut
from intersection import audit as intersection_audit

# Fixed trial: (name, side width, front coverage change, rear coverage change)
CASES=(("standard",.32,0.,0.),("front_shallow",.32,-.08,0.),
       ("rear_deep",.32,0.,.08),("combined",.48,-.08,.08))
RAYS=((1,3*math.pi/4,"front"),(2,math.pi/4,"front"),
      (1,-3*math.pi/4,"rear"),(2,-math.pi/4,"rear"))

def coverages(points,loops):
    return [max(crossings(points,loops[0],theta))-max(crossings(points,loops[i],theta))
            for i,theta,_ in RAYS]

def deform_profile(points,loops,front,rear):
    if not all(math.isfinite(v) and abs(v)<=.10 for v in (front,rear)):
        raise ValueError("bounded profile changes")
    if front==rear==0:return list(points)
    parameters={}
    for i,theta,region in RAYS:
        top=max(crossings(points,loops[0],theta))
        hem=max(crossings(points,loops[i],theta))
        delta=front if region=="front" else rear
        a=(hem+DEPTH)/(top+DEPTH)
        b=(hem-delta+DEPTH)/(top+DEPTH)
        if not 0<a<1 or not 0<b<1:raise ValueError("unreachable coverage")
        parameters[i,region]=math.log(a*(1-b)/(b*(1-a))) if delta else 0.
    fixed=set(loops[0])
    out=[]
    for i,(x,y,z) in enumerate(points):
        r=math.hypot(x,y)
        if i in fixed or r<1e-10 or abs(x)<1e-12 or abs(y)<1e-12:
            out.append((x,y,z));continue
        theta=math.atan2(y,x)
        top=.40+WAIST.latitude((theta-math.pi/2)/math.tau)
        t=(z+DEPTH)/(top+DEPTH)
        param=parameters[(1 if x<0 else 2),("front" if y>0 else "rear")]
        if param==0 or not 0<t<1:
            out.append((x,y,z));continue
        # C1 blend with zero value and slope at the four cardinal axes.
        k=math.exp(math.sin(2*theta)**2*param)
        new_z=(top+DEPTH)*t/(t+k*(1-t))-DEPTH
        def nominal(h):
            scale=math.sqrt(max(0.,1-(min(h,0.)/DEPTH)**2))
            return (TARGET.reference_radius(theta,h)+GAP)*scale
        old_r=nominal(z)
        if old_r<1e-10:raise ValueError("singular radius")
        scale=nominal(new_z)/old_r
        out.append((x*scale,y*scale,new_z))
    return out

def trial(case,check_intersection=True,source=None):
    name,side,front,rear=case
    if source is None:
        p,q,l,r=source_trial()
        assert r["fixture_gate"]
    else:p,q,l=source
    base=side_deform(p,l,side)
    out=deform_profile(base,l,front,rear)
    original=coverages(base,l);actual=coverages(out,l)
    requested=[front,front,rear,rear]
    changes=[b-a for a,b in zip(original,actual)]
    side_before=widths(base,l);side_after=widths(out,l)
    error=max(abs(a-b) for a,b in zip(changes,requested))
    side_drift=max(abs(a-b) for a,b in zip(side_before,side_after))
    waist_drift=max(math.dist(base[i],out[i]) for i in l[0])
    cardinal_drift=max(math.dist(a,b) for a,b in zip(base,out) if min(abs(a[0]),abs(a[1]))<1e-12)
    m=inspect_cut(out,q,l,out)
    collision=intersection_audit(out,q) if check_intersection else None
    passed=(m["cut_pilot_pass"] and error<=.015 and side_drift<=.005
        and max(abs(v-side) for v in side_after)<=.015 and waist_drift==0
        and cardinal_drift==0 and m["max_normal_jump"]<=30
        and collision is not None and collision["passed"])
    return dict(name=name,side_requested=side,coverage_requested=requested,
        base_coverages=original,actual_coverages=actual,coverage_changes=changes,
        coverage_max_error=error,side_before=side_before,side_after=side_after,
        side_drift=side_drift,waist_drift=waist_drift,cardinal_drift=cardinal_drift,
        metrics=m,nonincident_intersection=collision,passed=passed),out,q,l
