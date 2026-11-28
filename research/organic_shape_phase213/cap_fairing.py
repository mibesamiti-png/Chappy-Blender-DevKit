"""R9F: local fairing of the R9E capped lower surface.
Keep the original cap acceptance thresholds and unchanged upper vertices.
"""
from collections import defaultdict
from silhouette_cap import soft_cap,drop
from tip_fairing import flare
from test_rim_wrap import generate
from cut_garment import inspect_cut
from side_width import widths
from intersection import audit as intersection_audit

PLAN=(4,8)

def fair_local(original,capped,faces,loops,steps):
    if steps not in PLAN:raise ValueError("fixed local fairing budget")
    adj=defaultdict(set)
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]):
            adj[a].add(b);adj[b].add(a)
    # Rim vertices follow their own boundary, never average across the opening.
    for l in loops:
        for j,i in enumerate(l):
            adj[i]={l[j-1],l[(j+1)%len(l)]}
    out=list(capped)
    for _ in range(steps):
        prev=out[:]
        for i,(x,y,z) in enumerate(original):
            if z>=-.735:continue
            t=min(1.,(-.735-z)/.035)
            w=.35*t*t*(3-2*t)
            ns=sorted(adj[i])
            if not ns:raise ValueError("isolated vertex")
            mean=tuple(sum(prev[j][k] for j in ns)/len(ns) for k in range(3))
            out[i]=tuple((1-w)*a+w*b for a,b in zip(prev[i],mean))
    return out

def trial(case,source=None):
    original,p,q,l=generate(case,True,source)
    assert original["passed"]
    before=flare(p,q)
    candidates=[]
    for steps in PLAN if before["excess"]>.05 else (None,):
        out=p if steps is None else fair_local(p,soft_cap(p,before["upper_min"],1.05),q,l,steps)
        after=flare(out,q)
        m=inspect_cut(out,q,l,out)
        collision=intersection_audit(out,q)
        side_error=max(abs(v-.32) for v in widths(out,l))
        unchanged=all(a==b for a,b in zip(p,out) if a[2]>=-.735)
        local_gate=(steps is None or (after["excess"]<=.035 and drop(after)<=.035 and
            drop(after)<=.5*drop(before) and after["upper_min"]>=.9*before["upper_min"]))
        eligible=(m["cut_pilot_pass"] and m["max_normal_jump"]<=30 and
            collision["passed"] and side_error<=.015 and unchanged and local_gate)
        candidates.append(dict(steps=steps,flare=after,max_sample_drop=drop(after),
            metrics=m,collision=collision,side_error=side_error,upper_unchanged=unchanged,
            local_gate=local_gate,eligible=eligible))
        if eligible:return dict(name=case[0],baseline=before,baseline_max_sample_drop=drop(before),
            candidates=candidates,selected=steps,passed=True),out,q,l
    return dict(name=case[0],baseline=before,baseline_max_sample_drop=drop(before),
        candidates=candidates,selected=None,passed=False),out,q,l
