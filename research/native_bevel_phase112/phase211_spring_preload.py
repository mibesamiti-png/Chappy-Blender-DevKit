"""Phase211-B4: bounded gravity-loaded passive spring anchor.
Same horizontal spring stiffness in all three trials; the additional mass
moves along a 45-degree guide to stretch the initially relaxed spring.
This is a fixture-level preload concept, not a latched or portable spring.
The force proxy k*extension is not a measured Bullet reaction force.
"""
import json,math,sys,time
from pathlib import Path
import numpy as np
import bpy
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase210_xy_cam import run_case
from phase210_inverse_cam import law
K=5.;DUTY=.77
def brief(c):
    return {k:v for k,v in c.items() if k!='rows'}
def preload_audit(c,p):
    rows=c['rows'][120:]
    q=dict(min_settled_anchor_travel=min(-r['preload_anchor_x'] for r in rows),
        max_guide_error=max(abs(r['preload_anchor_x']-r['preload_anchor_y']) for r in c['rows']),
        min_settled_force_proxy=min(r['spring_force_proxy'] for r in rows),
        max_force_proxy=max(r['spring_force_proxy'] for r in c['rows']),
        min_initial_force_proxy=min(r['spring_force_proxy'] for r in c['rows'][:120]))
    q['passed']=q['min_settled_anchor_travel']>=.9*p and q['max_guide_error']<=.02 and q['min_settled_force_proxy']>=2.
    return q
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    t=np.arange(36000)*math.tau/36000
    phase=float(t[np.argmin(law(t,'stride',DUTY))])
    trials=[];chosen=None
    for p in (0.,1.,2.):
        sub=dest/('phase211_preload_'+str(int(p)));sub.mkdir(exist_ok=True)
        c=run_case('engaged',False,True,sub,32,DUTY,phase,K,p)
        q=preload_audit(c,p) if p else None
        cases=[c]
        if p and c['passed'] and q['passed']:
            cases.extend(run_case(n,s,e,sub,32,DUTY,phase,K,p) for n,s,e in [('separated',True,True),('motor_off',False,False)])
        passed=bool(p and q['passed'] and len(cases)==3 and all(v['passed'] for v in cases))
        trials.append(dict(preload=p,audit=q,cases=cases,passed=passed))
        print('PHASE211B4_TRIAL',json.dumps(dict(preload=p,audit=q,cases=[brief(v) for v in cases],passed=passed),allow_nan=False),flush=True)
        if passed:
            chosen=p
            break
    baseline_failed=not trials[0]['cases'][0]['passed']
    out=dict(complete=True,native_executed=True,approved=False,
        preload_gate=baseline_failed and chosen is not None,baseline_failed=baseline_failed,
        selected_preload=chosen,stiffness=K,anchor_mass=3.,gravity=[0.,-9.81,0.],duty=DUTY,
        trials=trials,criteria_changed=False,cam_geometry_changed=False,
        initially_relaxed=True,gravity_dependent_anchor=True,force_proxy_not_measured=True,
        portable_return_certified=False,physical_walk_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase211_spring_preload.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE211B4_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='trials'},allow_nan=False),flush=True)
if __name__=='__main__':main()
