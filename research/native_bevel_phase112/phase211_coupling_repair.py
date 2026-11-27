"""Phase211-E3: bounded cross-slide conditioning experiment.
Reuse E2 measurements. Only constraint pivot or cross-slide solver budget
changes. No geometry, mass, phase, motor, friction, or acceptance changes.
Short screening, not a full walk certification.
"""
import json,sys,time,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
import phase211_walk_load_diagnosis as diag
FRAMES=121
ORIGINAL_SETUP=diag.setup
VARIANTS=[('baseline','pad',100),('midpoint','midpoint',100),
    ('slider_pivot','slider',100),('cross_slide_iterations','pad',300)]
def trial(name,pivot,iterations):
    evidence=[]
    def configured(*args,**kwargs):
        sc,shaft,legs=ORIGINAL_SETUP(*args,**kwargs)
        bpy.context.view_layer.update()
        for o in sc.objects:
            c=o.rigid_body_constraint
            if not c or not o.name.endswith('cross-slide'):continue
            assert c.type=='GENERIC' and c.object1 and c.object2
            a=c.object1.matrix_world.translation.copy()
            b=c.object2.matrix_world.translation.copy()
            before=o.location.copy()
            assert (before-b).length<1e-4
            if pivot=='midpoint':o.location=(a+b)*.5
            elif pivot=='slider':o.location=a
            if iterations!=100:
                c.use_override_solver_iterations=True;c.solver_iterations=iterations
            evidence.append(dict(name=o.name,pad_lever_before=(before-b).length,
                slide_lever_before=(before-a).length,pad_lever_after=(o.location-b).length,
                slide_lever_after=(o.location-a).length,override=c.use_override_solver_iterations,
                effective_iterations=c.solver_iterations if c.use_override_solver_iterations else sc.rigidbody_world.solver_iterations))
        assert len(evidence)==8
        bpy.context.view_layer.update()
        return sc,shaft,legs
    diag.FRAMES=FRAMES;diag.setup=configured
    try:r=diag.run(name,True,.8,240.)
    finally:diag.setup=ORIGINAL_SETUP
    checks={k:r['peak'][k]<=v for k,v in diag.LIMITS.items()}
    checks.update(backplate=r['min_back_gap']>=.02,upright=r['max_tilt']<=15.,
        late_speed=r['late_mean_velocity']>=.8)
    r.update(pivot=pivot,iterations=iterations,pivot_evidence=evidence,
        screening_checks=checks,screening_passed=all(checks.values()))
    print('PHASE211E3_TRIAL',json.dumps({k:v for k,v in r.items() if k!='rows'},allow_nan=False),flush=True)
    return r
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    trials=[trial(*v) for v in VARIANTS]
    candidates=[r for r in trials[1:] if r['screening_passed']]
    selected=min(candidates,key=lambda r:(r['iterations'],r['peak']['foot_tracking'],r['name']))['name'] if candidates else None
    d=dict(complete=True,native_executed=True,approved=False,screening_only=True,
        geometry_changed=False,mass_changed=False,criteria_changed=False,
        physical_walk_certified=False,frames=FRAMES,limits=diag.LIMITS,
        trials=trials,selected=selected,elapsed=time.perf_counter()-start)
    (dest/'phase211_coupling_repair.json').write_text(json.dumps(d,indent=2,allow_nan=False))
    print('PHASE211E3_SUMMARY',json.dumps({k:v for k,v in d.items() if k!='trials'},allow_nan=False),flush=True)
if __name__=='__main__':main()
