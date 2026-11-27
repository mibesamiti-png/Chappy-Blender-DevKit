"""Phase210-C2: bounded drive capacity diagnosis, same profile and gates.
Change only Bullet motor maximum angular impulse. Not a calibrated
physical motor torque rating. Preserve all failures and baseline.
"""
import json,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from phase210_stride_contact import run_case
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    trials=[];selected=None
    for impulse in (10.,40.,100.):
        sub=dest/('phase210_stride_impulse_'+str(int(impulse)));sub.mkdir(exist_ok=True)
        cases=[run_case(n,z,True,sub,impulse) for n,z in [('engaged',0.),('separated',1.)]]
        passed=all(c['passed'] for c in cases)
        if passed:
            cases.append(run_case('motor_off',0.,False,sub,impulse))
            passed=all(c['passed'] for c in cases)
        trials.append(dict(impulse=impulse,cases=cases,passed=passed))
        print('PHASE210C2_TRIAL',json.dumps(dict(impulse=impulse,passed=passed,
            cases=[{k:v for k,v in c.items() if k!='rows'} for c in cases]),allow_nan=False),flush=True)
        if passed:
            selected=impulse
            break
    baseline=trials[0]
    reproduced=all(not c['checks']['full_cycle'] for c in baseline['cases'][:2])
    out=dict(complete=True,native_executed=True,approved=False,baseline_reproduced=reproduced,
        physical_gate=reproduced and selected is not None,selected_impulse=selected,trials=trials,
        impulse_candidates=[10.,40.,100.],profile_changed=False,criteria_changed=False,
        combined_motion_certified=False,walking_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase210_stride_impulse.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE210C2_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='trials'},allow_nan=False),flush=True)
if __name__=='__main__':main()
