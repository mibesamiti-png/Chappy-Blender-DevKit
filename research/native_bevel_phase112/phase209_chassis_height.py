"""Phase 209-A: bounded chassis-height intervention on Phase208-D.
Same mass, box dimensions, gearing, legs, phase, gravity, motor and friction.
Only the ideal chassis body's local Y center changes. Its inertia about its
own origin is unchanged, but assembly mass distribution changes.
Do not infer manufactured-frame feasibility or true physical COM certification.
"""
import json,math,time,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase208_free_walk import run_case,LIMITS,FRAMES
HEIGHTS=(('baseline',1.75),('lower',-1.55),('lowest',-2.0))
def summarize(c):
    rows=c['rows']
    first=next((q['frame'] for q in rows if q['tilt_deg']>LIMITS['max_tilt_deg']),None)
    floor=next((q['frame'] for q in rows if q['nonfoot_min_z']<=LIMITS['near_ground']),None)
    return dict(name=c['name'],height=c['chassis_center_y'],initial_com_proxy_z=c['initial_com_proxy_z'],
        max_tilt=c['max_tilt_deg'],first_tilt_failure_frame=first,first_nonfoot_near_frame=floor,
        nonfoot_frames=c['nonfoot_near_floor_frames'],forward=c['forward'],sideways=c['sideways'],
        input=c['input'],max_gear_phase_error=c['max_gear_phase_error'],max_foot_error=c['max_foot_error'],
        max_joint_error=c['max_joint_error'],checks=c['checks'],walk_candidate=c['walk_candidate'])
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    # 24-tooth gear tip radius 1.3; chassis half-height .16. Never
    # exploit the disabled anchor/gear collision by placing it in a gear.
    assert all(abs(y)-.16>1.3 for _,y in HEIGHTS)
    cases=[]
    for name,y in HEIGHTS:
        c=run_case(name,.8,True,dest,center_y=y,save_name='phase209_'+name+'.blend')
        cases.append(c)
        print('PHASE209A_CASE',json.dumps(summarize(c),allow_nan=False),flush=True)
    base=cases[0]
    # Keep the original walking gate unchanged. An exploratory ranking
    # is not a declaration of success, and never modifies a failed gate.
    def rank(c):
        return (not c['walk_candidate'],c['nonfoot_near_floor_frames'],c['max_tilt_deg'],c['sideways'])
    best=min(cases,key=rank)
    changes=[dict(name=c['name'],com_proxy_height_delta=c['initial_com_proxy_z']-base['initial_com_proxy_z'],
        tilt_delta=c['max_tilt_deg']-base['max_tilt_deg'],nonfoot_frames_delta=c['nonfoot_near_floor_frames']-base['nonfoot_near_floor_frames'],
        forward_delta=c['forward']-base['forward'],sideways_delta=c['sideways']-base['sideways']) for c in cases[1:]]
    baseline_reproduced=not base['walk_candidate'] and base['max_tilt_deg']>90 and base['checks']['geometry'] and base['checks']['gear_sync']
    controls={}
    extra=[]
    if best['walk_candidate']:
        for name,f,e in [('frictionless',0.,True),('motor_off',.8,False)]:
            c=run_case(name,f,e,dest,center_y=best['chassis_center_y'])
            extra.append(c)
            print('PHASE209A_CONTROL',json.dumps(summarize(c),allow_nan=False),flush=True)
        z,o=extra
        controls=dict(frictionless_no_net_com_translation=z['com_proxy_xy']<=.15,
            frictionless_not_walk=not z['walk_candidate'],motor_off_not_walk=not o['walk_candidate'])
    walk_gate=baseline_reproduced and best['walk_candidate'] and bool(controls) and all(controls.values())
    out=dict(complete=True,native_executed=True,approved=False,physical_walk_certified=False,
        baseline_reproduced=baseline_reproduced,walk_gate=walk_gate,ranked_candidate=best['name'],
        controls=controls,cases=cases,additional_cases=extra,changes=changes,
        intervention='chassis center only; mass 3.0, dimensions 6.4 x .32 x 1.0 unchanged',
        limits=LIMITS,elapsed=time.perf_counter()-start)
    (dest/'phase209_chassis_height.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE209A_SUMMARY',json.dumps(dict(baseline_reproduced=baseline_reproduced,walk_gate=walk_gate,
        ranked_candidate=best['name'],changes=changes,controls=controls,elapsed=out['elapsed']),allow_nan=False),flush=True)
    assert len(cases)==3 and all(len(c['rows'])==FRAMES for c in cases+extra)
    assert all(c['initial_com_proxy_z']<base['initial_com_proxy_z'] for c in cases[1:])
if __name__=='__main__':main()
