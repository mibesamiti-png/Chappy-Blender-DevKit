"""Phase211-E2: bounded load diagnosis, not a walking acceptance test.
Reuse E1 assembly. Compare floor absent, friction absent, and impulse cap.
All part displacement comparisons use the moving chassis reference frame.
"""
import json,math,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
import numpy as np
from mathutils import Vector
from phase211_four_leg_drive import setup,START,DUTY,IMPULSE
from phase211_free_walk import FLOOR_Y
from phase210_inverse_cam import law,ROLLER
from phase210_xy_cam import az,wrap
from phase211_groove_profile import nearest
from phase211_backed_groove import FLOOR
FRAMES=301
LIMITS=dict(cam_tracking=.025,roller_bearing=.015,cross_slide=.015,guide=.015,
    axial=.05,contact=.025,outer_contact=.025,foot_tracking=.04,shaft_drift=.015)
def run(name,has_floor,friction,impulse):
    sc,shaft,legs=setup(False,True,True,True,True,friction)
    chassis=bpy.data.objects['chassis reference']
    if not has_floor:bpy.data.objects.remove(bpy.data.objects['physical floor'],do_unlink=True)
    motor=next(o.rigid_body_constraint for o in sc.objects if o.rigid_body_constraint and o.rigid_body_constraint.type=='MOTOR')
    motor.motor_ang_max_impulse=impulse
    sc.frame_end=FRAMES;sc.rigidbody_world.point_cache.frame_end=FRAMES
    bpy.context.view_layer.update()
    rows=[];first={};last=None;travel=0.;initial={}
    for f in range(1,FRAMES+1):
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        mat=lambda o:o.evaluated_get(dg).matrix_world.copy()
        C=mat(chassis);inv=C.inverted();S=inv@mat(shaft);angle=az(S)
        delta=0. if last is None else wrap(angle-last);last=angle;travel+=delta
        row=dict(frame=f,travel=travel,velocity=-60.*delta,body_x=float(C.translation.x),body_y=float(C.translation.y),
            body_z=float(C.translation.z),tilt=math.degrees(math.acos(max(-1.,min(1.,float(C.to_3x3().col[1].normalized().y))))),
            shaft_drift=(S.translation-Vector((0.,6.,0.))).length,axes=[],feet=[])
        for j,L in enumerate(legs):
            phase=(START-travel+L['offset'])%math.tau
            W=mat(L['out']);P=inv@W;foot=P.translation
            if f==1:initial[j]=foot.copy()
            foot_delta=foot-initial[j];expected_delta=[]
            gap=min((W@v.co).y for v in L['out'].data.vertices)-FLOOR_Y if has_floor else None
            for i,it in enumerate(L['items']):
                k=f"L{j}_{it['kind']}";A=S@it['cam_local'];B=inv@mat(it['roller']);D=inv@mat(it['slide'])
                if f==1:initial[k]=(B.translation.copy(),D.translation.copy())
                b0,d0=initial[k];bd=B.translation-b0;dd=D.translation-d0
                desired=float(law(phase,it['kind'],DUTY));initial_law=it['initial']-it['base']
                expected_delta.append(desired-initial_law)
                rel=A.inverted()@B;v=rel.translation;p=np.array((v.x,v.y))
                reach=.12*abs(rel[2][2])+ROLLER*math.hypot(rel[2][0],rel[2][1])
                q=dict(axis=k,cam_tracking=abs(float(B.translation[i]+(6. if i==1 else 0.)-it['base'])-desired),
                    roller_bearing=(bd-dd).length,cross_slide=abs(float(foot_delta[i]-dd[i])),
                    guide=math.sqrt(sum(float(dd[h])**2 for h in range(3) if h!=i)),
                    axial=abs(v.z),contact=abs(nearest(p,it['core'])-ROLLER),
                    outer_contact=abs(nearest(p,it['outer'])-ROLLER),
                    back_gap=FLOOR+it['side']*v.z-reach)
                row['axes'].append(q)
            err=(foot_delta-Vector((*expected_delta,0.))).length
            row['feet'].append(dict(leg=j,foot_tracking=err,floor_gap=gap))
        for q in row['axes']+row['feet']+[row]:
            for k,limit in LIMITS.items():
                if k in q and q[k]>limit and k not in first:
                    first[k]=dict(frame=f,part=q.get('axis',q.get('leg','shaft')),value=q[k],travel=travel)
        rows.append(row)
    peak={k:max(q[k] for r in rows for q in r['axes']+r['feet']+[r] if k in q) for k in LIMITS}
    min_back=min(q['back_gap'] for r in rows for q in r['axes'])
    end=rows[-1]
    summary=dict(name=name,has_floor=has_floor,friction=friction,impulse=impulse,travel=travel,
        forward_dx=end['body_x']-rows[0]['body_x'],lateral_dz=end['body_z']-rows[0]['body_z'],
        max_tilt=max(r['tilt'] for r in rows),late_mean_velocity=sum(r['velocity'] for r in rows[-60:])/60.,
        first=first,peak=peak,min_back_gap=min_back)
    print('PHASE211E2_TRIAL',json.dumps(summary,allow_nan=False),flush=True)
    return dict(**summary,rows=rows)
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    trials=[run(*args) for args in [('baseline',True,.8,IMPULSE),('no_floor',False,.8,IMPULSE),
        ('frictionless',True,0.,IMPULSE),('higher_impulse',True,.8,4.*IMPULSE)]]
    out=dict(complete=True,native_executed=True,approved=False,diagnosis_only=True,
        geometry_changed=False,acceptance_changed=False,physical_walk_certified=False,
        frames=FRAMES,limits=LIMITS,trials=trials,elapsed=time.perf_counter()-start)
    (dest/'phase211_walk_load_diagnosis.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE211E2_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='trials'},allow_nan=False),flush=True)
if __name__=='__main__':main()
