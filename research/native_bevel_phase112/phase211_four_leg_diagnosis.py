"""Phase211-D2: locate first failure; bounded diagnostic, not gate tuning.
No changes to D1 geometry or acceptance criteria. Compare original, motor-off,
separated, reduced impulse, and heavier shaft for 61 frames only.
"""
import json,math,time,sys,itertools
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from phase211_four_leg_drive import setup,START,DUTY
from phase210_xy_cam import az,wrap
from phase210_inverse_cam import law,ROLLER
from phase211_backed_groove import FLOOR
from phase211_groove_profile import nearest
FRAMES=61
def contacts(obs,dg,allowed):
    records={}
    for o in obs:
        M=o.evaluated_get(dg).matrix_world
        vs=[M@v.co for v in o.data.vertices]
        lo=tuple(min(v[i] for v in vs) for i in range(3));hi=tuple(max(v[i] for v in vs) for i in range(3))
        records[o.name]=(o,vs,lo,hi)
    trees={};hits=[]
    for a,b in itertools.combinations(records,2):
        if frozenset((a,b)) in allowed:continue
        if any(records[a][3][i]<records[b][2][i] or records[b][3][i]<records[a][2][i] for i in range(3)):continue
        for k in (a,b):
            if k not in trees:
                o,v,_,_=records[k];o.data.calc_loop_triangles()
                trees[k]=BVHTree.FromPolygons(v,[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True,epsilon=0.)
        if trees[a].overlap(trees[b]):hits.append([a,b])
    return hits
def trial(name,separated,enabled,impulse=240.,mass=.8):
    sc,shaft,legs=setup(separated,enabled)
    shaft.rigid_body.mass=mass
    motor=next(o.rigid_body_constraint for o in sc.objects if o.rigid_body_constraint and o.rigid_body_constraint.type=='MOTOR')
    motor.motor_ang_max_impulse=impulse
    sc.frame_end=FRAMES;sc.rigidbody_world.point_cache.frame_end=FRAMES
    allowed={frozenset((c.object1.name,c.object2.name)) for o in sc.objects if (c:=o.rigid_body_constraint) and c.disable_collisions}
    for L in legs:
        for it in L['items']:allowed.add(frozenset((it['cam'].name,it['roller'].name)))
    obs=[o for o in sc.objects if o.rigid_body and o.type=='MESH']
    rows=[];first={};events=[];travel=0.;last=None
    limits={'sync':.015,'coupling':.015,'drift':.015,'error':.025,'axial':.05,'gap':.025,'outer_gap':.025,'tilt':.015}
    for f in range(1,FRAMES+1):
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        mat=lambda o:o.evaluated_get(dg).matrix_world.copy()
        S=mat(shaft);angle=az(S)
        if last is not None:travel+=wrap(angle-last)
        last=angle
        row=dict(frame=f,travel=travel,shaft_tilt=math.acos(max(-1.,min(1.,float(S.to_3x3().col[2].normalized().z)))),parts=[])
        new=False
        for j,L in enumerate(legs):
            phase=(START-travel+L['offset'])%math.tau;O=mat(L['out'])
            for i,it in enumerate(L['items']):
                A=mat(it['cam']);B=mat(it['roller']);D=mat(it['slide']);rel=A.inverted()@B;v=rel.translation
                p=np.array((v.x,v.y));out=float(O.translation[i]-it['base'])
                q=dict(part=it['cam'].name,sync=abs(wrap(az(A)-angle+L['offset'])),
                    coupling=abs(out-float(B.translation[i]-it['base'])),
                    drift=max((A.translation-Vector((0.,0.,it['z']))).length,math.hypot(B.translation[1-i],B.translation.z-it['rz']),abs(D.translation[1-i])),
                    error=abs(out-float(law(phase,it['kind'],DUTY))),
                    axial=abs(v.z),gap=abs(nearest(p,it['core'])-ROLLER),outer_gap=abs(nearest(p,it['outer'])-ROLLER),
                    tilt=math.acos(max(-1.,min(1.,float(A.to_3x3().col[2].normalized().z)))))
                row['parts'].append(q)
                for k,limit in limits.items():
                    if separated and k in ('axial','error','gap','outer_gap'):continue
                    if q[k]>limit and k not in first:
                        first[k]=dict(frame=f,part=q['part'],value=q[k]);new=True
        if f in (1,2,3,10,30,61) or new:
            events.append(dict(frame=f,unexpected_surface_pairs=contacts(obs,dg,allowed)))
        rows.append(row)
    summary=dict(name=name,separated=separated,enabled=enabled,impulse=impulse,shaft_mass=mass,
        travel=travel,first=first,events=events,peak={k:max(q[k] for r in rows for q in r['parts']) for k in limits})
    print('PHASE211D2_TRIAL',json.dumps(summary,allow_nan=False),flush=True)
    return dict(**summary,rows=rows)
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    trials=[trial(*args) for args in [('baseline',False,True),('motor_off',False,False),('separated',True,True),
        ('reduced_impulse',False,True,60.),('heavier_shaft',False,True,240.,8.)]]
    out=dict(complete=True,native_executed=True,approved=False,diagnosis_only=True,
        geometry_changed=False,criteria_changed=False,physical_walk_certified=False,
        frames=FRAMES,trials=trials,elapsed=time.perf_counter()-start)
    (dest/'phase211_four_leg_diagnosis.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE211D2_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='trials'},allow_nan=False),flush=True)
if __name__=='__main__':main()
