"""R9D: detect and reduce lower frontal-projection flares.
Fixed horizontal slices of actual triangulated geometry, then bounded
smooth local X contraction. No modification when a flare is absent.
"""
from test_rim_wrap import CASES,generate
from cut_garment import inspect_cut
from side_width import widths
from intersection import audit as intersection_audit

LEVELS=tuple(-.810+i*.005 for i in range(23))
FACTORS=(.60,.50)

def slices(p,q):
    edges={tuple(sorted((a,b))) for f in q for t in ((f[0],f[1],f[2]),(f[0],f[2],f[3])) for a,b in zip(t,t[1:]+t[:1])}
    result=[]
    for h in LEVELS:
        values=[]
        for i,j in edges:
            a,b=p[i],p[j]
            if a[2]==h:values.append(abs(a[0]))
            if b[2]==h:values.append(abs(b[0]))
            if (a[2]-h)*(b[2]-h)<0:
                t=(h-a[2])/(b[2]-a[2])
                values.append(abs(a[0]+t*(b[0]-a[0])))
        if not values:raise ValueError("missing slice")
        result.append(max(values))
    return result

def flare(p,q):
    profile=slices(p,q)
    lower=max(w for z,w in zip(LEVELS,profile) if z<-.750)
    upper=min(w for z,w in zip(LEVELS,profile) if z>=-.745)
    return dict(lower_max=lower,upper_min=upper,excess=max(0.,lower-upper),profile=profile)

def contract(p,factor):
    if factor not in FACTORS:raise ValueError("fixed factor")
    out=[]
    for x,y,z in p:
        t=max(0.,min(1.,(z+.755)/.055))
        scale=factor+(1-factor)*t*t*(3-2*t)
        out.append((x*scale,y,z))
    return out

def trial(case,source=None):
    original,p,q,l=generate(case,True,source)
    assert original["passed"]
    before=flare(p,q)
    candidates=[]
    # Detect a lower flare; unaffected shapes are left exactly unchanged.
    factors=FACTORS if before["excess"]>.05 else (None,)
    for f in factors:
        out=p if f is None else contract(p,f)
        after=flare(out,q)
        m=inspect_cut(out,q,l,out)
        collision=intersection_audit(out,q)
        side_error=max(abs(v-.32) for v in widths(out,l))
        unchanged=all(a==b for a,b in zip(p,out) if a[2]>=-.70)
        eligible=(m["cut_pilot_pass"] and m["max_normal_jump"]<=30 and collision["passed"]
                  and side_error<=.015 and unchanged and after["excess"]<=.05
                  and (f is None or after["excess"]<=.5*before["excess"]))
        candidates.append(dict(factor=f,flare=after,metrics=m,collision=collision,side_error=side_error,
                               upper_unchanged=unchanged,eligible=eligible))
        if eligible:return dict(name=case[0],baseline=before,candidates=candidates,selected=f,passed=True),out,q,l
    return dict(name=case[0],baseline=before,candidates=candidates,selected=None,passed=False),out,q,l
