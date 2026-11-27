"""Phase212-I: analytic external Geneva indexer, separate from C2 cam tracks.
Ideal centerline kinematics only. The pin/slot dimensions are preliminary
envelopes, not wheel/locking disk geometry or contact validation.
Driver advances one revolution per normalized cycle. Positive output angle
uses the convention pin=(C-r*cos(theta),r*sin(theta)).
"""
import math
from dataclasses import dataclass
from phase212_design_evaluation import finite,Limit,evaluate,select_candidate

@dataclass(frozen=True)
class Geneva:
    slots: int
    center_distance: float
    pin_radius: float
    clearance: float
    phase_offset: float=0.
    def __post_init__(self):
        if type(self.slots) is not int or not 3<=self.slots<=12:
            raise ValueError("bounded external Geneva slot count 3..12")
        if not all(finite(v) and v>0 for v in (self.center_distance,self.pin_radius,self.clearance)):
            raise ValueError("positive dimensions required")
        if not finite(self.phase_offset) or not 0<=self.phase_offset<1:
            raise ValueError("invalid phase offset")
    @property
    def beta(self):return math.pi/self.slots
    @property
    def crank_radius(self):return self.center_distance*math.sin(self.beta)
    @property
    def advance(self):return 2*self.beta
    @property
    def active_fraction(self):return .5-1/self.slots
    @property
    def dwell_fraction(self):return 1-self.active_fraction
    @property
    def start(self):return (1-self.active_fraction)/2
    @property
    def end(self):return (1+self.active_fraction)/2
    def pin(self,cycle):
        theta=math.tau*((cycle+self.phase_offset)%1-.5)
        r=self.crank_radius;C=self.center_distance
        return C-r*math.cos(theta),r*math.sin(theta)
    def sample(self,cycle):
        """Unwrapped angle, first and second cycle derivatives.
        At exact engagement boundaries acceleration is undefined (None).
        """
        if not finite(cycle):raise ValueError("finite cycle required")
        x=cycle+self.phase_offset;n=math.floor(x);u=x-n
        p=n*self.advance
        if abs(u-self.start)<=1e-14:return p,0.,None
        if abs(u-self.end)<=1e-14:return p+self.advance,0.,None
        if u<self.start:return p,0.,0.
        if u>self.end:return p+self.advance,0.,0.
        theta=math.tau*(u-.5);C=self.center_distance;r=self.crank_radius
        x,y=self.pin(cycle);d=x*x+y*y
        N=r*(C*math.cos(theta)-r)
        Np=-r*C*math.sin(theta);dp=2*C*r*math.sin(theta)
        return p+self.beta+math.atan2(y,x),math.tau*N/d,math.tau**2*(Np*d-N*dp)/d**2
    def envelope(self):
        """Necessary conservative radial slot clearance bounds, not a solid."""
        C=self.center_distance;r=self.crank_radius;w=self.pin_radius+self.clearance
        inner=C-r
        return dict(crank_radius=r,centerline_inner=inner,centerline_entry=C*math.cos(self.beta),
            slot_half_width=w,slot_inner_end=inner-w,adjacent_slot_web_bound=2*inner*math.sin(self.beta)-2*w,
            acceleration_jump=math.tau**2*math.tan(self.beta))

@dataclass(frozen=True)
class IndexRequirement:
    advance: float
    dwell_min: float
    angle_tolerance: float=1e-8
    min_hub: float=.1
    min_web: float=.1
    require_c2: bool=False
    def __post_init__(self):
        if not finite(self.advance) or self.advance<=0 or not finite(self.dwell_min) or not 0<=self.dwell_min<1:
            raise ValueError("positive indexing advance and valid dwell required")
        if not all(finite(v) and v>0 for v in (self.angle_tolerance,self.min_hub,self.min_web)) or type(self.require_c2) is not bool:
            raise ValueError("invalid indexing limits")

def audit(g,req,samples=721):
    if type(samples) is not int or not 121<=samples<=3601:raise ValueError("bounded audit samples")
    env=g.envelope()
    obs={"step_error":[(1,"indexer",abs(g.advance-req.advance))],
         "dwell":[(1,"indexer",g.dwell_fraction)],
         "hub":[(1,"indexer",env["slot_inner_end"])],
         "web_bound":[(1,"indexer",env["adjacent_slot_web_bound"])],
         "c2_compatible":[(1,"indexer",int(not req.require_c2))],
         "slot_alignment":[],"radial_range":[],"monotonic":[]}
    # Independent Cartesian projection of pin onto the moving slot axis.
    # Slot is initially at -beta, then follows the wheel angle.
    for i in range(samples):
        u=g.start+(g.end-g.start)*i/(samples-1)-g.phase_offset
        p,_,_=g.sample(u);x,y=g.pin(u)
        a=p-g.beta
        obs["slot_alignment"].append((i+1,"pin",abs(-x*math.sin(a)+y*math.cos(a))))
        rho=x*math.cos(a)+y*math.sin(a)
        obs["radial_range"].append((i+1,"pin",rho))
        if i:obs["monotonic"].append((i+1,"wheel",p-prev))
        prev=p
    eps=1e-10*max(1.,g.center_distance)
    limits=(Limit("step_error",upper=req.angle_tolerance),Limit("dwell",lower=req.dwell_min),
        Limit("hub",lower=req.min_hub),Limit("web_bound",lower=req.min_web),
        Limit("c2_compatible",lower=1),Limit("slot_alignment",upper=eps),
        Limit("radial_range",lower=env["centerline_inner"]-eps,upper=env["centerline_entry"]+eps),
        Limit("monotonic",lower=-1e-12))
    return dict(analytic=evaluate(limits,obs),envelope=env,slots=g.slots,
        advance=g.advance,dwell_fraction=g.dwell_fraction,continuity="C1_not_C2",
        wheel_solid_verified=False,locking_verified=False,physical_contact_certified=False)

def screen(req,candidates,budget):
    candidates=tuple(candidates);ids=tuple(k for k,_ in candidates)
    select_candidate(ids,{},budget)
    reports={k:audit(g,req) for k,g in candidates}
    decision=select_candidate(ids,{k:v["analytic"]["status"] for k,v in reports.items()},budget)
    return dict(decision=decision,reports=reports,physical_contact_certified=False)
