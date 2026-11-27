"""Phase211-B3: final bounded stiffness extension, no changes to criteria.
Reuses B2 evidence generated on the same checkout, including no-spring control.
If both candidates fail, retain failure and revisit return mechanism.
"""
import json,math,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from phase210_xy_cam import run_case
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results'
    base=json.loads((dest/'phase211_spring_return.json').read_text())
    assert base['complete'] and base['duty']==.77 and base['gravity']==[0.,-9.81,0.]
    phase=base['start_phase'];trials=[];chosen=None
    # Preserve a successful B2 if future simulation behavior changes.
    if not base['spring_gate']:
        for k in (60.,100.):
            p=dest/('phase211_spring_'+str(int(k)));p.mkdir(exist_ok=True)
            c=run_case('engaged',False,True,p,32,.77,phase,k)
            r=dict(stiffness=k,cases=[c])
            if c['passed']:
                r['cases'].extend(run_case(n,s,e,p,32,.77,phase,k) for n,s,e in [('separated',True,True),('motor_off',False,False)])
            r['passed']=len(r['cases'])==3 and all(v['passed'] for v in r['cases'])
            peak=max(c['rows'],key=lambda row:abs(row['stride_gap']))
            r['peak_contact']=dict(frame=peak['frame'],phase=peak['phase'],gap=peak['stride_gap'],expected=peak['stride_expected'],follower=peak['stride_follower'])
            trials.append(r)
            print('PHASE211B3_TRIAL',json.dumps({**r,'cases':[{a:b for a,b in v.items() if a!='rows'} for v in r['cases']]},allow_nan=False),flush=True)
            if r['passed']:
                chosen=k
                break
    if base['spring_gate']:chosen=base['selected_stiffness']
    out=dict(complete=True,native_executed=True,approved=False,
        prior_gate=base['spring_gate'],negative_control_detected=base['negative_control_detected'],
        spring_gate=chosen is not None and base['negative_control_detected'],selected_stiffness=chosen,
        trials=trials,duty=.77,gravity=base['gravity'],criteria_changed=False,geometry_changed=False,
        physical_walk_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase211_spring_refine.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE211B3_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='trials'},allow_nan=False),flush=True)
if __name__=='__main__':main()
