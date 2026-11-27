"""Phase 210-C4: isolate the separated control's transient constraint error.
Frozen geometry, preload, mass, drive and gates. Change only substeps.
No relaxation of the original control, no claim of physical stop forces.
"""
import json,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from phase210_xy_cam import run_case
def diagnose(c):
    rows=c['rows'];out={}
    for k in ('stride','lift'):
        peak=max(rows,key=lambda r:abs(r[k+'_coupler_error']))
        first=next((r['frame'] for r in rows if r[k+'_slide_displacement']<=-.145),None)
        out[k]=dict(peak_frame=peak['frame'],peak_error=peak[k+'_coupler_error'],
            displacement=peak[k+'_slide_displacement'],lower_stop=-.15,first_near_stop_frame=first,
            roller_slide_error=peak[k+'_roller_slide_error'],slide_output_error=peak[k+'_slide_output_error'],
            after_120=max(abs(r[k+'_coupler_error']) for r in rows[120:]))
    return out
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    trials=[];chosen=None
    for substeps in (16,32,64):
        sub=dest/('phase210_xy_resolution_'+str(substeps));sub.mkdir(exist_ok=True)
        cases=[run_case('separated',True,True,sub,substeps)]
        diagnostic=diagnose(cases[0])
        if cases[0]['passed']:
            cases.extend(run_case(n,False,e,sub,substeps) for n,e in [('engaged',True),('motor_off',False)])
        passed=len(cases)==3 and all(c['passed'] for c in cases)
        trials.append(dict(substeps=substeps,cases=cases,diagnostic=diagnostic,passed=passed))
        print('PHASE210C4_TRIAL',json.dumps(dict(substeps=substeps,diagnostic=diagnostic,passed=passed,
            cases=[{k:v for k,v in c.items() if k!='rows'} for c in cases]),allow_nan=False),flush=True)
        if passed:
            chosen=substeps
            break
    base=trials[0]['cases'][0]
    reproduced=not base['checks']['coupling'] and all(v for k,v in base['checks'].items() if k!='coupling')
    out=dict(complete=True,native_executed=True,approved=False,baseline_reproduced=reproduced,
        physical_gate=reproduced and chosen is not None,selected_substeps=chosen,trials=trials,
        candidates=[16,32,64],criteria_changed=False,geometry_changed=False,walking_certified=False,
        elapsed=time.perf_counter()-start)
    (dest/'phase210_xy_diagnosis.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE210C4_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='trials'},allow_nan=False),flush=True)
if __name__=='__main__':main()
