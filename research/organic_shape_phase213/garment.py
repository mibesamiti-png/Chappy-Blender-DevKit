"""R7 static garment pilot: one waist, two curved leg openings.
Standalone synthetic garment; not a real-body fit or a cloth simulation.
"""
import math
from boundary import Boundary,Ellipsoid
from fitting import Target,fit
from junction import audit,smooth
from refinement import refine
from collections import Counter

N=48
GAP=.045
TARGET=Target(.32,.22,.08)
WAIST=Boundary(Ellipsoid((1.,1.,1.)),(.04,.02,-.02,-.04,-.04,-.02,.02,.04))

def base():
    p=[];faces=[]
    def add(q):
        p.append(tuple(q));return len(p)-1
    def upper(theta,z):
        return fit([(math.cos(theta),math.sin(theta),z)],TARGET,GAP)[0]
    angles=[math.pi/2+math.tau*i/N for i in range(N)]
    waist_z=[.48+WAIST.latitude(i/N) for i in range(N)]
    # R4 radial projection along the entire upper band, not just endpoints.
    rings=[]
    for j in range(9):
        t=j/8
        rings.append([add(upper(a,(1-t)*z+t*(-.08))) for a,z in zip(angles,waist_z)])
    def connect(a,b):
        faces.extend((a[i],b[i],b[(i+1)%N],a[(i+1)%N]) for i in range(N))
    for a,b in zip(rings,rings[1:]):connect(a,b)
    top,mid=rings[0],rings[-1]
    front=p[mid[0]][1];back=p[mid[N//2]][1]
    bridge=[add((0.,back+(front-back)*j/(N//2),-.08-.67*math.sin(math.pi*j/(N//2)))) for j in range(1,N//2)]
    left=mid[:N//2+1]+bridge
    right=mid[N//2:]+[mid[0]]+bridge[::-1]
    def leg(sign,start):
        out=[]
        for i in range(N):
            a=start+math.tau*i/N;c=math.cos(a);s=math.sin(a)
            # High outer edge, lower inner edge, slightly lower rear hem.
            z=-.67+.27*sign*c+.045*s
            out.append(add((sign*.52+.435*c,-.04+.465*s,z)))
        return out
    low_l=leg(-1,math.pi/2);low_r=leg(1,3*math.pi/2)
    def branch(a,b):
        prev=a
        for j in range(1,13):
            t=j/12
            nxt=b if j==12 else []
            if j!=12:
                for i,(k,l) in enumerate(zip(a,b)):
                    A,B=p[k],p[l]
                    w=math.sin(math.pi*(i-N//2)/(N//2)) if i>N//2 else 0.
                    q=(1-w)*t+w*t*t*(3-2*t)
                    nxt.append(add((A[0]+t*(B[0]-A[0]),A[1]+q*(B[1]-A[1]),A[2]+q*(B[2]-A[2]))))
            connect(prev,nxt);prev=nxt
    branch(left,low_l);branch(right,low_r)
    return p,faces,(top,low_l,low_r)

def edge_groups(faces,loops):
    roles={tuple(sorted((a,b))):role for role,l in zip(("waist","left_leg","right_leg"),loops) for a,b in zip(l,l[1:]+l[:1])}
    return [next((roles[e] for e in (tuple(sorted((a,b))) for a,b in zip(f,f[1:]+f[:1])) if e in roles),"fabric") for f in faces]

def inspect(p,q,l,ref):
    m=audit(p,q,l,ref)
    waist,left,right=l
    gaps=[]
    def sample(x):
        a,b,z=x
        if z>=.04:
            gaps.append(math.hypot(a,b)-TARGET.reference_radius(math.atan2(b,a),z))
    for x in p:sample(x)
    for f in q:
        for t in ((f[0],f[1],f[2]),(f[0],f[2],f[3])):
            a,b,c=(p[i] for i in t)
            for w in ((.5,.5,0),(.5,0,.5),(0,.5,.5),(1/3,1/3,1/3)):
                sample(tuple(sum(k*x[j] for k,x in zip(w,(a,b,c))) for j in range(3)))
    groups=edge_groups(q,l)
    counts=Counter(groups)
    m.update(upper_gap_min=min(gaps),upper_gap_max=max(gaps),upper_gap_samples=len(gaps),
        waist_z_range=[min(p[i][2] for i in waist),max(p[i][2] for i in waist)],
        leg_z_range=[min(p[i][2] for i in left+right),max(p[i][2] for i in left+right)],
        left_max_x=max(p[i][0] for i in left),right_min_x=min(p[i][0] for i in right),
        edge_groups=dict(counts))
    m["garment_pilot_pass"]=m["passed"] and m["upper_gap_min"]>.005 and m["upper_gap_max"]<.085 and m["left_max_x"]<0<m["right_min_x"] and all(counts[role]==len(loop) for role,loop in zip(("waist","left_leg","right_leg"),l))
    return m

def trial():
    p,q,l=base()
    history=[]
    # Bounded candidate plan: only one refinement pass, no thickness required.
    for steps in (0,8,16):
        s=smooth(p,q,l,steps)
        a,b,c,ref=refine(s,q,l,"smooth")
        m=inspect(a,b,c,ref)
        history.append(dict(smoothing=steps,metrics=m))
        if m["garment_pilot_pass"]:
            return a,b,c,dict(complete=True,selected=steps,candidates=history,fixture_gate=True)
    return a,b,c,dict(complete=True,selected=None,candidates=history,fixture_gate=False)
