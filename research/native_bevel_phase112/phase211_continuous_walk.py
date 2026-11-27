"""Phase211-E5: fixed E4 candidate, three-cycle gait acceptance.
Use E1 geometry and measurements without relaxed thresholds.
Actual cam/pad contacts, ideal offset couplers, no manufacturing certification.
Each case has the same horizon. No parameter search.
"""
import json,math,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
import phase211_free_walk as walk
FRAMES=1201
MASS=.5
IMPULSE=960.
CASES={'free_engaged':(True,.8),'frictionless':(True,0.),'motor_off':(False,.8)}
def main():
    assert bpy.app.version_string=='4.4.3'
    name=sys.argv[sys.argv.index('--')+1]
    enabled,friction=CASES[name]
    start=time.perf_counter()
    dest=ROOT/'results'/'phase211_continuous'/name
    dest.mkdir(parents=True,exist_ok=True)
    original=walk.setup
    evidence=[]
    def configured(*args,**kwargs):
        sc,shaft,legs=original(*args,**kwargs)
        bpy.context.view_layer.update()
        for L in legs:
            for o in [L['out']]+[it['slide'] for it in L['items']]:
                assert abs(o.rigid_body.mass-.1)<1e-6
                o.rigid_body.mass=MASS
                evidence.append(dict(name=o.name,mass=float(o.rigid_body.mass)))
        pivots=[]
        for o in sc.objects:
            c=o.rigid_body_constraint
            if not c:continue
            if o.name.endswith('cross-slide'):
                o.location=c.object1.matrix_world.translation.copy();pivots.append(o)
            elif c.type=='MOTOR':
                assert c.use_motor_ang==enabled
                c.motor_ang_max_impulse=IMPULSE
        assert len(pivots)==8 and len(evidence)==12
        sc.frame_end=FRAMES;sc.rigidbody_world.point_cache.frame_end=FRAMES
        bpy.context.view_layer.update()
        assert all((o.location-o.rigid_body_constraint.object1.matrix_world.translation).length<1e-4 for o in pivots)
        assert sc.rigidbody_world.solver_iterations==100 and sc.rigidbody_world.substeps_per_frame==32
        return sc,shaft,legs
    walk.FRAMES=FRAMES;walk.setup=configured
    try:r=walk.run(name,True,enabled,friction,dest)
    finally:walk.setup=original
    cycles=[];rows=r['rows'];prev=rows[0]
    for n in range(1,4):
        nxt=next((v for v in rows if -v['travel']>=n*math.tau),None)
        if nxt is None:break
        cycles.append(dict(cycle=n,start_frame=prev['frame'],end_frame=nxt['frame'],
            dx=nxt['x']-prev['x'],dz=nxt['z']-prev['z']))
        prev=nxt
    checks=dict(r['checks'])
    if enabled:checks['three_cycles']=len(cycles)==3
    if name=='free_engaged':
        checks['forward_every_cycle']=len(cycles)==3 and all(c['dx']<=-.5 for c in cycles)
        checks['lateral_every_cycle']=len(cycles)==3 and all(abs(c['dz'])<=.5 for c in cycles)
    d=dict(complete=True,native_executed=True,approved=False,case=name,frames=FRAMES,
        candidate='moving_mass_and_drive',moving_mass=MASS,impulse=IMPULSE,pivot='slider',
        mass_evidence=evidence,ideal_offset_couplers=True,ideal_rigid_camshaft=True,
        support_is_geometric_proxy=True,com_is_origin_weighted_proxy=True,
        physical_manufacturing_certified=False,cycles=cycles,checks=checks,case_gate=all(checks.values()),
        result=r,elapsed=time.perf_counter()-start)
    (dest/'report.json').write_text(json.dumps(d,indent=2,allow_nan=False))
    print('PHASE211E5_CASE',json.dumps({**{k:v for k,v in d.items() if k not in ('result','mass_evidence')},
        'measurements':{k:v for k,v in r.items() if k!='rows'}},allow_nan=False),flush=True)
if __name__=='__main__':main()
