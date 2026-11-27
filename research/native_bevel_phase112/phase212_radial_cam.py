"""Phase212-C: external radial translating roller cam geometry adapter.

One turn of input corresponds to one track cycle (negative cam rotation).
Coordinates use track units. This is sampled planar geometry validation only;
no preload, return mechanism, torque, collision or manufacturing claim.
"""
from dataclasses import dataclass
import math
from phase212_motion_spec import Track
from phase212_design_evaluation import Limit,evaluate,finite,select_candidate

@dataclass(frozen=True)
class CamConfig:
    pitch_base: float
    roller_radius: float
    min_core_radius: float
    pressure_max: float = 30.
    offset_min: float = .05
    gap_tolerance: float = .002
    samples: int = 720
    def __post_init__(self):
        values=(self.pitch_base,self.roller_radius,self.min_core_radius,self.pressure_max,self.offset_min,self.gap_tolerance)
        if not all(finite(v) and v>0 for v in values) or self.pressure_max>=90 or self.offset_min>=1:
            raise ValueError("invalid positive cam dimensions or limits")
        if type(self.samples) is not int or not 120<=self.samples<=1440:
            raise ValueError("bounded sample count required")

def _check_track(track):
    if not isinstance(track,Track) or track.unit not in ("mm","model_unit") or track.advance!=0:
        raise ValueError("closed translating track required")

def pitch(track,cfg,u):
    p,v,a=track.sample(u)
    r=cfg.pitch_base+p
    v/=math.tau;a/=math.tau**2
    if not math.isfinite(r) or r<=0:
        raise ValueError("pitch radius must be positive")
    t=u*math.tau;c=math.cos(t);s=math.sin(t)
    speed=math.hypot(r,v)
    normal=((r*c+v*s)/speed,(r*s-v*c)/speed)
    curvature=(r*r+2*v*v-r*a)/speed**3
    return ((r*c,r*s),normal,math.degrees(math.atan2(abs(v),r)),1-cfg.roller_radius*curvature)

def generate(track,cfg):
    _check_track(track)
    out=[]
    for i in range(cfg.samples):
        p,n,_,_=pitch(track,cfg,i/cfg.samples)
        out.append((p[0]-cfg.roller_radius*n[0],p[1]-cfg.roller_radius*n[1]))
    return tuple(out)

def _edges(profile):
    result=[]
    for (x,y),(X,Y) in zip(profile,profile[1:]+profile[:1]):
        dx=X-x;dy=Y-y;l2=dx*dx+dy*dy
        if not finite(l2) or l2<=1e-24:
            raise ValueError("degenerate edge")
        result.append((x,y,X,Y,dx,dy,l2))
    return result

def _nearest_and_inside(point,edges):
    x,y=point;best=float("inf");inside=False
    for ax,ay,bx,by,dx,dy,l2 in edges:
        u=max(0.,min(1.,((x-ax)*dx+(y-ay)*dy)/l2))
        q=(x-ax-u*dx)**2+(y-ay-u*dy)**2
        best=min(best,q)
        if (ay>y)!=(by>y) and x<ax+(y-ay)*dx/dy:
            inside=not inside
    return math.sqrt(best),inside

def audit(track,cfg,profile):
    """Audit submitted polygon against off-grid roller centers and all edges."""
    _check_track(track)
    poly=tuple(tuple(v) for v in profile)
    if len(poly)!=cfg.samples or any(len(p)!=2 or not all(finite(v) for v in p) for p in poly):
        raise ValueError("invalid submitted profile")
    edges=_edges(poly)
    turns=[math.atan2(x*Y-y*X,x*X+y*Y) for x,y,X,Y,*_ in edges]
    core,origin_inside=_nearest_and_inside((0.,0.),edges)
    n=2*cfg.samples
    phases=sorted(set([(i+.37)/n for i in range(n)]+[(k.phase-track.phase_offset)%1 for k in track.knots]))
    observations={k:[] for k in ("pressure","offset","roller_gap","roller_inside")}
    for i,u in enumerate(phases,1):
        p,_,pressure,offset=pitch(track,cfg,u)
        d,inside=_nearest_and_inside(p,edges)
        for k,v in (("pressure",pressure),("offset",offset),("roller_gap",d-cfg.roller_radius),("roller_inside",int(inside))):
            observations[k].append((i,track.name,v))
    observations.update(polar_step=[(i,track.name,t) for i,t in enumerate(turns,1)],
        winding=[(1,track.name,sum(turns)/math.tau)],core_radius=[(1,track.name,core)],
        origin_inside=[(1,track.name,int(origin_inside))])
    limits=(Limit("pressure",upper=cfg.pressure_max),Limit("offset",lower=cfg.offset_min),
        Limit("roller_gap",lower=-cfg.gap_tolerance,upper=cfg.gap_tolerance),
        Limit("roller_inside",upper=0),Limit("polar_step",lower=1e-10,upper=math.pi-1e-10),
        Limit("winding",lower=1-1e-8,upper=1+1e-8),Limit("core_radius",lower=cfg.min_core_radius),
        Limit("origin_inside",lower=1))
    report=evaluate(limits,observations)
    return dict(sampled_geometry=report,profile_samples=len(poly),audit_samples=len(phases),
        phase_unit="input_cycle",unit=track.unit,physical_contact_certified=False,
        manufacturing_certified=False,continuous_proof=False)

def screen(track,candidates,budget):
    """Candidate order is a predeclared preference; no iterative search."""
    candidates=tuple(candidates)
    ids=tuple(k for k,_ in candidates)
    select_candidate(ids,{},budget) # validate budget/identity before geometry
    results={};profiles={}
    for name,cfg in candidates:
        try:
            poly=generate(track,cfg)
            report=audit(track,cfg,poly)
        except (ValueError,OverflowError,ZeroDivisionError) as exc:
            results[name]=dict(status="unverified",reason=str(exc))
            continue
        results[name]=dict(status=report["sampled_geometry"]["status"],report=report)
        profiles[name]=poly
    decision=select_candidate(ids,{k:v["status"] for k,v in results.items()},budget)
    return dict(decision=decision,results=results,profiles=profiles,
        physical_contact_certified=False)
