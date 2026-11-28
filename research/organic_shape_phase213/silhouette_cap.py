"""R9E: bounded soft cap for transverse lower silhouette flare.
Compare directly to original R9C, not already contracted R9D.
Only excess lateral extent is compressed; unchanged upper vertices.
"""
import math
from tip_fairing import flare,LEVELS
from test_rim_wrap import generate
from cut_garment import inspect_cut
from side_width import widths
from intersection import audit as intersection_audit

PLAN=(1.05,.95)
def drop(report):
    return max(0.,*(a-b for a,b in zip(report["profile"],report["profile"][1:])))

def soft_cap(p,anchor,factor):
    if factor not in PLAN or not math.isfinite(anchor) or anchor<=0:
        raise ValueError("fixed positive cap")
    cap=anchor*factor
    knee=.70*cap
    out=[]
    for x,y,z in p:
        if z>=-.735 or abs(x)<=knee:
            out.append((x,y,z));continue
        t=max(0.,min(1.,(-.735-z)/.020))
        weight=t*t*(3-2*t)
        a=abs(x)
        limited=knee+(cap-knee)*(-math.expm1(-(a-knee)/(cap-knee)))
        new=a+weight*(limited-a)
        out.append((math.copysign(new,x),y,z))
    return out

def trial(case,source=None):
    original,p,q,l=generate(case,True,source)
    assert original["passed"]
    before=flare(p,q)
    candidates=[]
    for factor in PLAN if before["excess"]>.05 else (None,):
        out=p if factor is None else soft_cap(p,before["upper_min"],factor)
        after=flare(out,q)
        m=inspect_cut(out,q,l,out)
        collision=intersection_audit(out,q)
        side_error=max(abs(v-.32) for v in widths(out,l))
        unchanged=all(a==b for a,b in zip(p,out) if a[2]>=-.735)
        local_gate=(factor is None or (after["excess"]<=.035 and drop(after)<=.035 and
            drop(after)<=.5*drop(before) and after["upper_min"]>=.9*before["upper_min"]))
        eligible=(m["cut_pilot_pass"] and m["max_normal_jump"]<=30 and
            collision["passed"] and side_error<=.015 and unchanged and local_gate)
        candidates.append(dict(factor=factor,flare=after,max_sample_drop=drop(after),
            metrics=m,collision=collision,side_error=side_error,upper_unchanged=unchanged,
            local_gate=local_gate,eligible=eligible))
        if eligible:return dict(name=case[0],baseline=before,baseline_max_sample_drop=drop(before),
            candidates=candidates,selected=factor,passed=True),out,q,l
    return dict(name=case[0],baseline=before,baseline_max_sample_drop=drop(before),
        candidates=candidates,selected=None,passed=False),out,q,l
