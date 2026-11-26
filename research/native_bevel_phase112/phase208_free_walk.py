"""Phase 208-D: exploratory free-chassis walking on a horizontal floor.
Real tooth contacts, ideal bearings/pins and an explicit surrogate rigid
chassis. No externally fixed body, animation, ratio drive or imposed motion.
Ground proximity is a geometric proxy, not a measured contact-force sensor.
A failed walk is valid research data, never reported as a passing walk.
"""
import math,json,time,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase208_four_legs import setup_case,wrap,FRAMES
from phase208_single_leg import Z
from phase207_walking_machine import motion
CENTER_Y=1.75
LIMITS=dict(min_forward=1.,max_sideways=.75,max_tilt_deg=35.,min_drive=math.tau,max_phase_error=.20,max_foot_error=.08,max_joint=.025,near_ground=.035,max_nonfoot_near_frames=0,min_contact_frames=10,min_swing_clearance=.15)
def run_case(name,friction,enabled,dest):
    scene,gears,legs=setup_case(False,enabled,free=True,friction=friction)
    frame=bpy.data.objects['free chassis'];floor=bpy.data.objects['floor']
    moving=gears+[ob for leg in legs for ob in leg['obs']]
    obs=[frame]+moving
    assert all(ob.rigid_body.type=='ACTIVE' and not ob.rigid_body.kinematic and ob.animation_data is None for ob in obs)
    assert [ob.name for ob in scene.objects if ob.rigid_body and ob.rigid_body.type=='PASSIVE']==['floor']
    assert abs(floor.rigid_body.friction-friction)<1e-6 and all(abs(ob.rigid_body.friction-friction)<1e-6 for ob in obs)
    if name=='driven':bpy.ops.wm.save_as_mainfile(filepath=str(dest/'phase208_free_walk.blend'))
    masses=np.array([ob.rigid_body.mass for ob in obs])
    vertices=[np.array([tuple(v.co) for v in ob.data.vertices]) for ob in obs]
    r,d,l,m,u,v=Z;rows=[];last=None;travel=[0.]*len(moving)
    initial=None;start_com=None
    def xyz(M,x=0.,y=0.):return np.array(tuple(M@Vector((x,y,0.))))
    for i in range(1,FRAMES+1):
        scene.frame_set(i);dg=bpy.context.evaluated_depsgraph_get()
        W=[ob.evaluated_get(dg).matrix_world.copy() for ob in obs]
        # Remove chassis pose so angular and loop measurements do not mistake
        # free-body rolling or translation for input-shaft rotation.
        ref=Matrix.Translation((0,CENTER_Y,0))@W[0].inverted()
        M=[ref@q for q in W[1:]]
        ang=[math.atan2(q[1][0],q[0][0]) for q in M]
        if last is not None:
            for j in range(len(moving)):travel[j]+=wrap(ang[j]-last[j])
        last=ang
        up=W[0].to_3x3()@Vector((0,1,0))
        tilt=math.degrees(math.acos(max(-1.,min(1.,up.normalized().z))))
        origin=W[0]@Vector((0,-CENTER_Y,0))
        com=np.average(np.array([tuple(q.translation) for q in W]),axis=0,weights=masses)
        if initial is None:initial=origin.copy();start_com=com.copy()
        delta=origin-initial;cd=com-start_com
        heights=[float(np.min(vs@np.array(tuple(q[2])[:3])+q[2][3])) for vs,q in zip(vertices,W)]
        feet=[]
        for k,leg in enumerate(legs):
            j=3+3*k;x=leg['x'];s=leg['side']
            B,C,F=motion(Z,ang[j])
            p=xyz(M[j+2],u,v)
            expected=np.array([x+F[0],F[1],s*1.39])
            off=np.array([0,0,s*.32])
            joint=max(np.linalg.norm(xyz(M[j],r)+off-xyz(M[j+2])),
                np.linalg.norm(xyz(M[j+1],m)+off-xyz(M[j+2],l)),
                np.linalg.norm(xyz(M[j])-[x,0,s*1.07]),
                np.linalg.norm(xyz(M[j+1])-[x+d,0,s*1.07]))
            h=heights[1+j+2]
            feet.append(dict(name=leg['name'],crank=travel[j],error=float(np.linalg.norm(p-expected)),
                joint=float(joint),phase=abs(wrap(ang[j]-ang[leg['gear']]-leg['phase'])),
                min_z=h,near_floor=h<=LIMITS['near_ground']))
        foot_indices={1+3+3*k+2 for k in range(4)}
        nonfoot=min(h for j,h in enumerate(heights) if j not in foot_indices)
        rows.append(dict(frame=i,position=list(origin),displacement=list(delta),com_proxy_displacement=cd.tolist(),
            tilt_deg=tilt,gears=travel[:3],feet=feet,nonfoot_min_z=nonfoot))
    last=rows[-1];inp=last['gears'][1];outs=[last['gears'][0],last['gears'][2]]
    max_phase=max(abs(q['gears'][1]+q['gears'][j]) for q in rows for j in (0,2))
    max_error=max(p['error'] for q in rows for p in q['feet'])
    max_joint=max(p['joint'] for q in rows for p in q['feet'])
    max_crank_phase=max(p['phase'] for q in rows for p in q['feet'])
    tilt=max(q['tilt_deg'] for q in rows)
    nonfoot=sum(q['nonfoot_min_z']<=LIMITS['near_ground'] for q in rows)
    feet={}
    for leg in legs:
        n=leg['name'];f=[p for q in rows for p in q['feet'] if p['name']==n]
        feet[n]=dict(crank=f[-1]['crank'],near_floor_frames=sum(p['near_floor'] for p in f),
            min_z=min(p['min_z'] for p in f),max_z=max(p['min_z'] for p in f),
            max_error=max(p['error'] for p in f),max_joint=max(p['joint'] for p in f))
    forward=-last['displacement'][0];sideways=abs(last['displacement'][1])
    com_forward=-last['com_proxy_displacement'][0]
    com_xy=math.hypot(*last['com_proxy_displacement'][:2])
    pair_support={}
    for pair in (('LF','RB'),('RF','LB')):
        pair_support['+'.join(pair)]=sum(all(p['near_floor'] for p in q['feet'] if p['name'] in pair) for q in rows)
    checks=dict(forward=forward>=LIMITS['min_forward'] and com_forward>=.5,
        sideways=sideways<=LIMITS['max_sideways'],upright=tilt<=LIMITS['max_tilt_deg'],
        drive=abs(inp)>=LIMITS['min_drive'] and all(abs(v['crank'])>=LIMITS['min_drive'] for v in feet.values()),
        gear_sync=max_phase<=LIMITS['max_phase_error'],geometry=max_error<=LIMITS['max_foot_error'] and max_joint<=LIMITS['max_joint'] and max_crank_phase<=.025,
        no_nonfoot_ground=nonfoot<=LIMITS['max_nonfoot_near_frames'],
        foot_cycles=all(f['near_floor_frames']>=LIMITS['min_contact_frames'] and f['max_z']>=LIMITS['min_swing_clearance'] for f in feet.values()),
        diagonal_support=all(v>=LIMITS['min_contact_frames'] for v in pair_support.values()))
    result=dict(name=name,friction=friction,motor_enabled=enabled,forward=forward,sideways=sideways,
        com_proxy_forward=com_forward,com_proxy_xy=com_xy,max_tilt_deg=tilt,input=inp,outputs=outs,max_gear_phase_error=max_phase,
        max_foot_error=max_error,max_joint_error=max_joint,max_crank_phase=max_crank_phase,nonfoot_near_floor_frames=nonfoot,
        feet=feet,pair_support=pair_support,checks=checks,walk_candidate=all(checks.values()),rows=rows)
    # Strict JSON prevents a numerical blow-up being counted as valid evidence.
    print('PHASE208D_CASE',json.dumps({k:v for k,v in result.items() if k!='rows'},allow_nan=False),flush=True)
    return result
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    cases=[run_case(n,f,e,dest) for n,f,e in [('driven',.8,True),('frictionless',0.,True),('motor_off',.8,False)]]
    d,z,o=cases
    controls=dict(frictionless_no_net_com_translation=z['com_proxy_xy']<=.15,
        motor_off_not_walk=not o['walk_candidate'],
        frictionless_not_walk=not z['walk_candidate'])
    walk_gate=d['walk_candidate'] and all(controls.values())
    out=dict(complete=True,native_executed=True,approved=False,experiment_complete=True,walk_gate=walk_gate,
        physical_walk_certified=False,ideal_pins=True,surrogate_chassis=True,contact_metric='mesh vertex floor proximity, not contact force',
        motor_impulse_setting=20.,gravity=9.81,limits=LIMITS,controls=controls,cases=cases,elapsed=time.perf_counter()-start)
    (dest/'phase208_free_walk.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE208D_SUMMARY',json.dumps(dict(walk_gate=walk_gate,controls=controls,elapsed=out['elapsed'])),flush=True)
    # CI verifies evidence integrity, NOT that a negative result is a successful walk.
    assert len(cases)==3 and all(len(c['rows'])==FRAMES for c in cases)
if __name__=='__main__':main()
