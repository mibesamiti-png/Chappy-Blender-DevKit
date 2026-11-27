"""Phase211-E4: finite mass/drive comparison at best E3 pivot.
Four fixed cases, no search loop. Stop after this screen if none pass;
reconsider the transmission architecture instead of repeated tuning.
Masses are model parameters, not validated material-derived masses.
"""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
import phase211_walk_load_diagnosis as diag
ORIGINAL_SETUP=diag.setup
FRAMES=121
VARIANTS=[('slider_reference',.1,240.),('drive_only',.1,960.),
    ('moving_mass_only',.5,240.),('moving_mass_and_drive',.5,960.)]
def trial(name,mass,impulse):
    evidence=[]
    def configured(*args,**kwargs):
        sc,shaft,legs=ORIGINAL_SETUP(*args,**kwargs)
        bpy.context.view_layer.update()
        for L in legs:
            for o in [L['out']]+[it['slide'] for it in L['items']]:
                assert abs(o.rigid_body.mass-.1)<1e-6
                o.rigid_body.mass=mass
                evidence.append(dict(name=o.name,mass=float(o.rigid_body.mass)))
        pivots=[]
        for o in sc.objects:
            c=o.rigid_body_constraint
            if c and o.name.endswith('cross-slide'):
                o.location=c.object1.matrix_world.translation
                pivots.append(o)
        assert len(pivots)==8 and len(evidence)==12
        bpy.context.view_layer.update()
        assert all((o.location-o.rigid_body_constraint.object1.matrix_world.translation).length<1e-4 for o in pivots)
        return sc,shaft,legs
    diag.FRAMES=FRAMES;diag.setup=configured
    try:r=diag.run(name,True,.8,impulse)
    finally:diag.setup=ORIGINAL_SETUP
    checks={k:r['peak'][k]<=v for k,v in diag.LIMITS.items()}
    checks.update(backplate=r['min_back_gap']>=.02,upright=r['max_tilt']<=15.,
        late_speed=r['late_mean_velocity']>=.8)
    r.update(moving_mass=mass,mass_evidence=evidence,pivot='slider',screening_checks=checks,
        screening_passed=all(checks.values()))
    print('PHASE211E4_TRIAL',json.dumps({k:v for k,v in r.items() if k!='rows'},allow_nan=False),flush=True)
    return r
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    trials=[trial(*v) for v in VARIANTS]
    candidates=[r for r in trials if r['screening_passed']]
    selected=min(candidates,key=lambda r:(r['impulse'],r['moving_mass'],r['peak']['foot_tracking']))['name'] if candidates else None
    d=dict(complete=True,native_executed=True,approved=False,screening_only=True,
        geometry_changed=False,criteria_changed=False,physical_walk_certified=False,
        mass_is_model_parameter=True,stop_if_no_candidate=True,frames=FRAMES,limits=diag.LIMITS,
        trials=trials,selected=selected,elapsed=time.perf_counter()-start)
    (dest/'phase211_coupling_load_screen.json').write_text(json.dumps(d,indent=2,allow_nan=False))
    print('PHASE211E4_SUMMARY',json.dumps({k:v for k,v in d.items() if k!='trials'},allow_nan=False),flush=True)
if __name__=='__main__':main()
