"""R1: periodic, locally editable boundaries on synthetic organic surfaces.

The chart is longitude + latitude on an ellipsoid. It is deliberately not
a general mesh parameterizer or a garment generator. No cloth physics.
"""
from dataclasses import dataclass
from bisect import bisect_left
import math

TAU=math.tau

def norm(v):
    return math.sqrt(sum(x*x for x in v))

def distance(a,b):
    return math.dist(a,b)

@dataclass(frozen=True)
class Ellipsoid:
    axes: tuple
    def __post_init__(self):
        if len(self.axes)!=3 or any(not math.isfinite(a) or a<=0 for a in self.axes):
            raise ValueError("three positive finite axes required")
    def point_normal(self,theta,lat):
        a,b,c=self.axes
        p=(a*math.cos(lat)*math.cos(theta),b*math.cos(lat)*math.sin(theta),c*math.sin(lat))
        raw=tuple(x/(r*r) for x,r in zip(p,self.axes))
        length=norm(raw)
        return p,tuple(x/length for x in raw)

@dataclass(frozen=True)
class Boundary:
    surface: Ellipsoid
    controls: tuple
    offset: float=0.
    def __post_init__(self):
        if not 4<=len(self.controls)<=32 or any(not math.isfinite(v) or abs(v)>1.2 for v in self.controls):
            raise ValueError("4-32 finite latitude controls within +/-1.2 rad")
        if not math.isfinite(self.offset) or not 0<=self.offset<=.1*min(self.surface.axes):
            raise ValueError("bounded outward offset required")
    def latitude(self,u):
        n=len(self.controls)
        t=(u%1)*n;i=math.floor(t);f=t-i
        a,b,c,d=(self.controls[(i+j)%n] for j in (-1,0,1,2))
        return ((1-f)**3*a+(3*f**3-6*f*f+4)*b+(-3*f**3+3*f*f+3*f+1)*c+f**3*d)/6
    def at(self,u):
        p,n=self.surface.point_normal(TAU*(u%1),self.latitude(u))
        q=tuple(x+self.offset*y for x,y in zip(p,n))
        return p,n,q
    def sample(self,count=96,dense=4096):
        if type(count) is not int or not 32<=count<=256 or type(dense) is not int or not 16*count<=dense<=16384:
            raise ValueError("bounded sampling budget required")
        prev=self.at(0)[2];arc=[0.]
        for i in range(1,dense+1):
            q=self.at(i/dense)[2]
            arc.append(arc[-1]+distance(prev,q));prev=q
        result=[]
        for i in range(count):
            target=arc[-1]*i/count
            j=max(1,bisect_left(arc,target))
            u=(j-1+(target-arc[j-1])/(arc[j]-arc[j-1]))/dense
            p,n,q=self.at(u)
            result.append(dict(u=u,base=p,normal=n,point=q))
        return result

def audit(boundary,rows):
    """Independent checks: implicit surface, displacement, chord length, turning."""
    count=len(rows);axes=boundary.surface.axes
    if count<32 or any(not all(math.isfinite(x) for x in r["point"]) for r in rows):
        raise ValueError("incomplete or invalid loop")
    chords=[];turns=[];surface=[];offset=[];direction=[];angles=[]
    for i,r in enumerate(rows):
        p,q=r["base"],r["point"]
        surface.append(abs(sum((x/a)**2 for x,a in zip(p,axes))-1))
        v=tuple(y-x for x,y in zip(p,q));offset.append(abs(norm(v)-boundary.offset))
        # Independent gradient, not the generator's recorded normal.
        raw=tuple(x/(a*a) for x,a in zip(p,axes))
        direction.append(norm(tuple(x-boundary.offset*y/norm(raw) for x,y in zip(v,raw))))
        angles.append(math.atan2(q[1]/axes[1],q[0]/axes[0]))
        prev=rows[(i-1)%count]["point"];nxt=rows[(i+1)%count]["point"]
        a=tuple(x-y for x,y in zip(q,prev));b=tuple(x-y for x,y in zip(nxt,q))
        la,lb=norm(a),norm(b)
        if min(la,lb)<=1e-12:raise ValueError("duplicate points")
        chords.append(lb)
        turns.append(math.degrees(math.acos(max(-1.,min(1.,sum(x*y for x,y in zip(a,b))/(la*lb))))))
    increments=[(angles[(i+1)%count]-angles[i])%TAU for i in range(count)]
    result=dict(surface_residual=max(surface),offset_error=max(offset),normal_offset_error=max(direction),
        chord_ratio=max(chords)/min(chords),max_turn_degrees=max(turns),
        one_winding=all(0<x<math.pi for x in increments) and abs(sum(increments)-TAU)<1e-9,
        vertices=count,closure_chord=chords[-1])
    result["passed"]=result["surface_residual"]<1e-10 and result["offset_error"]<1e-10 and result["normal_offset_error"]<1e-10 and result["chord_ratio"]<=1.1 and result["max_turn_degrees"]<=20 and result["one_winding"]
    return result
