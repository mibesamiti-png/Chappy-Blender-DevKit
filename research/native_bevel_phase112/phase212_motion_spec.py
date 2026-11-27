"""Phase212-B: normalized drive-cycle motion specifications.

A track is an unwrapped translation (mm or model units) or rotation (rad).
Velocity/acceleration are derivatives with respect to input cycles, not time.
All segment endpoints and cycle seams are C2 by construction. No implicit
conversion from a desired curve to a physically achievable mechanism.
"""
from dataclasses import dataclass
import math
from phase212_design_evaluation import finite

@dataclass(frozen=True)
class Knot:
    phase: float
    position: float
    velocity: float = 0.
    acceleration: float = 0.
    def __post_init__(self):
        if not all(finite(v) for v in (self.phase,self.position,self.velocity,self.acceleration)):
            raise ValueError("finite knot required")
        if not 0<=self.phase<=1:
            raise ValueError("phase outside cycle")

@dataclass(frozen=True)
class Track:
    name: str
    unit: str
    knots: tuple
    advance: float = 0.
    phase_offset: float = 0.
    def __post_init__(self):
        if not isinstance(self.name,str) or not self.name.strip() or self.unit not in ("mm","model_unit","rad"):
            raise ValueError("invalid track name or unit")
        if not finite(self.advance) or not finite(self.phase_offset) or not 0<=self.phase_offset<1:
            raise ValueError("invalid advance or phase offset")
        object.__setattr__(self,"knots",tuple(self.knots))
        k=self.knots
        if len(k)<2 or any(not isinstance(x,Knot) for x in k):
            raise ValueError("two or more knots required")
        if k[0].phase!=0 or k[-1].phase!=1 or any(b.phase<=a.phase for a,b in zip(k,k[1:])):
            raise ValueError("knots must cover one cycle in increasing order")
        if (not math.isclose(k[-1].position-k[0].position,self.advance,rel_tol=0,abs_tol=1e-10)
            or k[-1].velocity!=k[0].velocity or k[-1].acceleration!=k[0].acceleration):
            raise ValueError("discontinuous cycle seam")
    @staticmethod
    def coefficients(a,b):
        h=b.phase-a.phase
        c0=a.position;c1=h*a.velocity;c2=.5*h*h*a.acceleration
        p=b.position-c0-c1-c2
        v=h*b.velocity-c1-2*c2
        acc=h*h*b.acceleration-2*c2
        return (c0,c1,c2,10*p-4*v+.5*acc,-15*p+7*v-acc,6*p-3*v+.5*acc)
    def sample(self,cycle):
        if not finite(cycle):
            raise ValueError("finite cycle required")
        u=cycle+self.phase_offset
        n=math.floor(u);u-=n
        a,b=next((a,b) for a,b in zip(self.knots,self.knots[1:]) if a.phase<=u<b.phase)
        h=b.phase-a.phase;t=(u-a.phase)/h
        c=self.coefficients(a,b)
        return (sum(v*t**i for i,v in enumerate(c))+n*self.advance,
                sum(i*c[i]*t**(i-1) for i in range(1,6))/h,
                sum(i*(i-1)*c[i]*t**(i-2) for i in range(2,6))/(h*h))
    def dwell_intervals(self):
        # Structural dwell, not threshold-based approximate dwell.
        intervals=[]
        for a,b in zip(self.knots,self.knots[1:]):
            if a.position==b.position and a.velocity==b.velocity==a.acceleration==b.acceleration==0:
                if intervals and intervals[-1][1]==a.phase:
                    intervals[-1]=(intervals[-1][0],b.phase)
                else:intervals.append((a.phase,b.phase))
        return tuple(intervals)
    def to_dict(self):
        return dict(name=self.name,unit=self.unit,advance=self.advance,phase_offset=self.phase_offset,
                    knots=[dict(phase=k.phase,position=k.position,velocity=k.velocity,acceleration=k.acceleration) for k in self.knots])
    @classmethod
    def from_dict(cls,data):
        if set(data)!={"name","unit","advance","phase_offset","knots"}:
            raise ValueError("unknown or missing track fields")
        return cls(data["name"],data["unit"],tuple(Knot(**k) for k in data["knots"]),data["advance"],data["phase_offset"])

@dataclass(frozen=True)
class MotionSpec:
    tracks: tuple
    period_seconds: float
    def __post_init__(self):
        object.__setattr__(self,"tracks",tuple(self.tracks))
        if not self.tracks or any(not isinstance(t,Track) for t in self.tracks) or len({t.name for t in self.tracks})!=len(self.tracks):
            raise ValueError("unique tracks required")
        if not finite(self.period_seconds) or self.period_seconds<=0:
            raise ValueError("positive period required")
    def sample(self,seconds):
        if not finite(seconds):
            raise ValueError("finite time required")
        h=self.period_seconds
        return {t.name:(p,v/h,a/(h*h)) for t in self.tracks for p,v,a in [t.sample(seconds/h)]}
    def to_dict(self):
        return dict(schema="mechanical-motion-v1",period_seconds=self.period_seconds,tracks=[t.to_dict() for t in self.tracks])
    @classmethod
    def from_dict(cls,data):
        if set(data)!={"schema","period_seconds","tracks"} or data["schema"]!="mechanical-motion-v1":
            raise ValueError("unsupported motion schema")
        return cls(tuple(Track.from_dict(t) for t in data["tracks"]),data["period_seconds"])
