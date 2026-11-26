"""Phase211-B2: replace artificial horizontal gravity by a passive spring.
Single XY module, 77% duty, real cam contact and dynamic carriage.
Spring starts at its equilibrium (near minimum stride), not a calibrated
commercial spring. Fixed guides and ideal shaft couplings remain.
"""
import json,math,sys,time
from pathlib import Path
import numpy as np
import bpy
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase210_xy_cam import run_case
from phase210_inverse_cam import law
DUTY=.77
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    t=np.arange(36000)*math.tau/36000
    phase=float(t[np.argmin(law(t,'stride',DUTY))])
    trials=[];chosen=None;controls=None
    for k in (3.,10.,30.):
        p=dest/('phase211_spring_'+str(int(k)));p.mkdir(exist_ok=True)
        c=run_case('engaged',False,True,p,32,DUTY,phase,k)
        trials.append(dict(stiffness=k,case=c))
        print('PHASE211B2_TRIAL',json.dumps(dict(stiffness=k,case={a:b for a,b in c.items() if a!='rows'}),allow_nan=False),flush=True)
        if c['passed']:
            chosen=k
            controls=[run_case(n,s,e,p,32,DUTY,phase,k) for n,s,e in [('separated',True,True),('motor_off',False,False)]]
            break
    p=dest/'phase211_spring_disabled';p.mkdir(exist_ok=True)
    no_spring=run_case('engaged',False,True,p,32,DUTY,phase,0.)
    negative=not no_spring['checks']['axis_tracking'] or not no_spring['checks']['contact']
    gate=chosen is not None and all(c['passed'] for c in controls) and negative
    out=dict(complete=True,native_executed=True,approved=False,spring_gate=gate,
        duty=DUTY,start_phase=phase,gravity=[0.,-9.81,0.],selected_stiffness=chosen,
        trials=trials,controls=controls,spring_disabled=no_spring,negative_control_detected=negative,
        spring_preloaded=False,ideal_guides=True,whole_machine_certified=False,physical_walk_certified=False,
        elapsed=time.perf_counter()-start)
    (dest/'phase211_spring_return.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE211B2_SUMMARY',json.dumps({**{k:v for k,v in out.items() if k not in ('trials','controls','spring_disabled')},
        'controls':[{k:v for k,v in c.items() if k!='rows'} for c in (controls or [])],
        'spring_disabled':{k:v for k,v in no_spring.items() if k!='rows'}},allow_nan=False),flush=True)
if __name__=='__main__':main()
