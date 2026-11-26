"""Phase 210-B: motor-only lift cam, gravity-return free roller.
Fixed ideal guide and bearing; no prescribed follower position, springs,
keyframes, linkage to the motor or second motor. Negative controls retain
the same gravity and guide, changing axial contact or motor enable only.
Not a complete leg, real-world fabrication or load certification.
"""
import json,math,time,sys
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase208_motor_contact import body,constraint
from phase206_hybrid_machine import ring,BORE,key_check
from phase210_inverse_cam import profile,law,ROLLER
FPS=60;FRAMES=481;BASE=2.5
def setup(offset,enabled,kind='lift',base=BASE,start_phase=0.,upper=1.,impulse=10.):
    initial=base+float(law(start_phase,kind))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene
    sc.gravity=(-9.81,0.,0.);sc.render.fps=FPS;sc.frame_start=1;sc.frame_end=FRAMES
    bpy.ops.mesh.primitive_cube_add(size=.5,location=(0,0,-5))
    anchor=body(bpy.context.object,True);anchor.name='ideal stationary guide and bearing reference'
    anchor.hide_render=True
    c=profile(kind,base)
    mesh,a=ring('inverse '+kind+' cam',[tuple(v) for v in c],[tuple(v*BORE/max(abs(v))) for v in c])
    assert a['passed'] and key_check(mesh)
    cam=bpy.data.objects.new('motor driven '+kind+' cam',mesh);sc.collection.objects.link(cam)
    cam.rotation_euler.z=-start_phase
    body(cam);cam.rigid_body.mass=3.;cam.color=(.8,.55,.15,1)
    constraint('ideal cam bearing','HINGE',anchor,cam,(0.,0.,0.))
    motor=constraint('only motor','MOTOR',anchor,cam,(0.,0.,0.),(0.,-math.pi/2,0.))
    motor.use_motor_lin=False;motor.use_motor_ang=enabled
    motor.motor_ang_target_velocity=1.;motor.motor_ang_max_impulse=impulse
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=ROLLER,depth=.24,location=(initial,0.,offset))
    roller=body(bpy.context.object);roller.name='unpowered rolling follower'
    roller.rigid_body.collision_shape='CONVEX_HULL';roller.rigid_body.mass=.25
    roller.rigid_body.friction=.2;roller.color=(.2,.55,.85,1)
    # X translation and Z spin free within generous stops, all other DOFs locked.
    guide=constraint('ideal linear guide with free roller spin','GENERIC',anchor,roller,(initial,0.,offset))
    guide.use_limit_lin_x=True;guide.limit_lin_x_lower=-.10;guide.limit_lin_x_upper=upper
    for axis in ('y','z'):
        setattr(guide,'use_limit_lin_'+axis,True)
        setattr(guide,'limit_lin_'+axis+'_lower',0.)
        setattr(guide,'limit_lin_'+axis+'_upper',0.)
    for axis in ('x','y'):
        setattr(guide,'use_limit_ang_'+axis,True)
        setattr(guide,'limit_ang_'+axis+'_lower',0.)
        setattr(guide,'limit_ang_'+axis+'_upper',0.)
    guide.use_limit_ang_z=False
    world=sc.rigidbody_world;world.substeps_per_frame=16;world.solver_iterations=100
    world.point_cache.frame_start=1;world.point_cache.frame_end=FRAMES
    bpy.context.view_layer.update();sc.frame_set(1)
    cs=[o.rigid_body_constraint for o in sc.objects if o.rigid_body_constraint]
    assert len(cs)==3 and sum(x.type=='MOTOR' and x.use_motor_ang for x in cs)==int(enabled)
    assert all(o.animation_data is None and not o.rigid_body.kinematic for o in (cam,roller))
    return sc,cam,roller,c
def run_case(name,offset,enabled,dest):
    sc,cam,roller,c=setup(offset,enabled)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/('phase210_cam_'+name+'.blend')))
    edge=np.roll(c,-1,axis=0)-c;den=np.sum(edge*edge,axis=1)
    rows=[];last=None;travel=0.;spin=0.;last_spin=None
    for f in range(1,FRAMES+1):
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        A=cam.evaluated_get(dg).matrix_world.copy();B=roller.evaluated_get(dg).matrix_world.copy()
        angle=math.atan2(A[1][0],A[0][0]);ra=math.atan2(B[1][0],B[0][0])
        if last is not None:travel+=math.atan2(math.sin(angle-last),math.cos(angle-last))
        if last_spin is not None:spin+=math.atan2(math.sin(ra-last_spin),math.cos(ra-last_spin))
        last=angle;last_spin=ra
        local=A.inverted()@B.translation;p=np.array((local.x,local.y))
        delta=p-c;t=np.clip(np.sum(delta*edge,axis=1)/den,0.,1.)
        gap=float(np.linalg.norm(delta-t[:,None]*edge,axis=1).min()-ROLLER)
        expected=float(law(-travel,'lift'));actual=float(B.translation.x-BASE)
        rows.append(dict(frame=f,angle=travel,roller_spin=spin,expected=expected,actual=actual,
            error=actual-expected,radial_gap=gap,axial_separation=abs(local.z),
            guide_drift=math.hypot(B.translation.y,B.translation.z-offset),cam_drift=A.translation.length))
    actual=[r['actual'] for r in rows];amp=max(actual)-min(actual)
    maxerr=max(abs(r['error']) for r in rows);drift=max(max(r['guide_drift'],r['cam_drift']) for r in rows)
    dwell=max(abs(r['actual']) for r in rows if r['expected']<=1e-8)
    gapmax=max(abs(r['radial_gap']) for r in rows)
    checks=dict(guide_and_bearing=drift<=.015)
    if name=='engaged':
        checks.update(full_cycle=travel<=-math.tau,stroke=.55<=amp<=.65,tracking=maxerr<=.025,
            dwell=dwell<=.025,contact_gap=gapmax<=.025,axial_overlap=max(r['axial_separation'] for r in rows)<.05)
    elif name=='separated':
        checks.update(full_cycle=travel<=-math.tau,no_positive_lift=max(actual)<=.025,
            no_periodic_lift=max(actual[60:])-min(actual[60:])<=.025,
            axial_clearance=min(r['axial_separation'] for r in rows)>.5)
    else:
        checks.update(no_drive=abs(travel)<=.02,no_lift=amp<=.025)
    out=dict(name=name,enabled=enabled,offset=offset,travel=travel,roller_spin=spin,amplitude=amp,
        max_tracking_error=maxerr,max_radial_gap=gapmax,max_dwell_error=dwell,max_drift=drift,
        min_displacement=min(actual),max_displacement=max(actual),checks=checks,passed=all(checks.values()),rows=rows)
    print('PHASE210B_CASE',json.dumps({k:v for k,v in out.items() if k!='rows'},allow_nan=False),flush=True)
    return out
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    cases=[run_case(n,z,e,dest) for n,z,e in [('engaged',0.,True),('separated',1.,True),('motor_off',0.,False)]]
    out=dict(complete=True,native_executed=True,approved=False,physical_gate=all(c['passed'] for c in cases),
        cases=cases,ideal_guides=True,gravity_return=True,walking_certified=False,elapsed=time.perf_counter()-start)
    (dest/'phase210_cam_contact.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE210B_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='cases'},allow_nan=False),flush=True)
if __name__=='__main__':main()
