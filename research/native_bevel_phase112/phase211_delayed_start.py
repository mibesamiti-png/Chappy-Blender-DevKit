"""Phase211-B5: distinguish startup transients from steady cam tracking.
Same B4 geometry, masses, spring and drive; motor holds zero speed for
120 frames, then commands 1 rad/s. No body transform keyframes.
The full startup interval is retained and checked, not discarded.
"""
import json,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from phase210_xy_cam import run_case
from phase211_spring_preload import preload_audit
DELAY=120
def brief(c):
    return {k:v for k,v in c.items() if k!='rows'}
def peaks(c,split):
    rows=c['rows']
    p=max(rows,key=lambda r:abs(r['stride_error']))
    return dict(frame=p['frame'],phase=p['phase'],error=p['stride_error'],
        gap=p['stride_gap'],anchor_x=p['preload_anchor_x'],force_proxy=p['spring_force_proxy'],
        after_split=max(abs(r['stride_error']) for r in rows[split:]))
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results'
    b=json.loads((dest/'phase211_spring_preload.json').read_text())
    assert b['complete'] and b['stiffness']==5.
    base=[q for q in b['trials'] if q['preload']>0]
    evidence=[dict(preload=q['preload'],peak=peaks(q['cases'][0],DELAY)) for q in base]
    sub=dest/'phase211_delayed';sub.mkdir(exist_ok=True)
    from phase210_inverse_cam import law
    import numpy as np,math
    t=np.arange(36000)*math.tau/36000
    phase=float(t[np.argmin(law(t,'stride',.77))])
    c=run_case('engaged',False,True,sub,32,.77,phase,5.,1.,DELAY)
    q=preload_audit(c,1.)
    cases=[c]
    if c['passed'] and q['passed']:
        cases.extend(run_case(n,s,e,sub,32,.77,phase,5.,1.,DELAY) for n,s,e in [('separated',True,True),('motor_off',False,False)])
    gate=len(cases)==3 and all(v['passed'] for v in cases) and q['passed']
    out=dict(complete=True,native_executed=True,approved=False,delayed_gate=gate,
        baseline_peaks=evidence,delayed_peak=peaks(c,DELAY),audit=q,cases=cases,
        delay_frames=DELAY,drive_frames=601,preload=1.,stiffness=5.,
        motor_hold=True,criteria_relaxed=False,body_transform_keyframes=False,
        portable_return_certified=False,physical_walk_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase211_delayed_start.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE211B5_SUMMARY',json.dumps({**out,'cases':[brief(v) for v in cases]},allow_nan=False),flush=True)
if __name__=='__main__':main()
