"""Phase 208-A: actual Bullet contact drive, not prescribed gear kinematics.
Two reused 24-tooth Phase206 meshes; ideal fixed bearings, no gravity/load.
Only the input has a motor. No keyframes, gear ratio constraints or drivers.
Three independent scenes: engaged, separated, motor off.
A negative result is retained, not silently counted as physical validation.
"""
import math,json,time,sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase206_hybrid_machine import gear
FPS=60
FRAMES=481
def active(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True);bpy.context.view_layer.objects.active=ob
def body(ob,passive=False):
    active(ob);bpy.ops.rigidbody.object_add()
    rb=ob.rigid_body
    rb.type='PASSIVE' if passive else 'ACTIVE'
    rb.collision_shape='BOX' if passive else 'MESH'
    rb.use_margin=True;rb.collision_margin=.0005
    if not passive:
        rb.mass=1.;rb.friction=.3;rb.restitution=0.
        rb.linear_damping=.04;rb.angular_damping=.04
        rb.use_deactivation=False;rb.kinematic=False
    return ob
def constraint(name,kind,anchor,obj,location,rotation=(0.,0.,0.)):
    e=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(e)
    e.location=location;e.rotation_euler=rotation;e.empty_display_size=.15
    active(e);bpy.ops.rigidbody.constraint_add()
    c=e.rigid_body_constraint;c.type=kind;c.object1=anchor;c.object2=obj;c.disable_collisions=True
    return c
def setup(distance,enabled):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.gravity=(0.,0.,0.);scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=FRAMES
    bpy.ops.mesh.primitive_cube_add(size=.5,location=(0.,0.,-5.))
    anchor=body(bpy.context.object,True);anchor.name='fixed bearing reference'
    anchor.hide_render=True
    objects=[]
    for i,x in enumerate((0.,distance)):
        mesh,audit=gear(24);assert audit['passed']
        ob=bpy.data.objects.new('input' if i==0 else 'unpowered_output',mesh)
        bpy.context.collection.objects.link(ob)
        ob.location=(x,0.,0.);ob.rotation_euler.z=0. if i==0 else math.pi/24
        ob.color=(.24,.55,.85,1) if i==0 else (.85,.55,.18,1)
        body(ob);objects.append(ob)
        constraint('ideal bearing '+str(i),'HINGE',anchor,ob,(x,0.,0.))
    motor=constraint('only motor','MOTOR',anchor,objects[0],(0.,0.,0.),(0.,-math.pi/2,0.))
    motor.use_motor_lin=False;motor.use_motor_ang=enabled
    motor.motor_ang_target_velocity=1.0;motor.motor_ang_max_impulse=2.0
    world=scene.rigidbody_world;world.substeps_per_frame=12;world.solver_iterations=80
    world.point_cache.frame_start=1;world.point_cache.frame_end=FRAMES
    bpy.context.view_layer.update();scene.frame_set(1)
    assert all(o.animation_data is None and not o.rigid_body.kinematic for o in objects)
    cs=[o.rigid_body_constraint for o in scene.objects if o.rigid_body_constraint]
    assert len(cs)==3 and sum(c.type=='MOTOR' and c.use_motor_ang for c in cs)==int(enabled)
    return scene,objects
def run_case(name,distance,enabled,dest):
    scene,obs=setup(distance,enabled)
    if name=='engaged':
        bpy.ops.wm.save_as_mainfile(filepath=str(dest/'phase208_motor_contact.blend'))
    rows=[];last=None;travel=[0.,0.];drift=0.
    for frame in range(1,FRAMES+1):
        scene.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get()
        mats=[o.evaluated_get(dg).matrix_world.copy() for o in obs]
        a=[math.atan2(M[1][0],M[0][0]) for M in mats]
        if last is not None:
            for i in range(2):travel[i]+=math.atan2(math.sin(a[i]-last[i]),math.cos(a[i]-last[i]))
        last=a
        drift=max(drift,*( (M.translation-Vector((x,0.,0.))).length for M,x in zip(mats,(0.,distance)) ))
        rows.append(dict(frame=frame,input=travel[0],output=travel[1],center_drift=drift))
    inp,out=travel;ratio=out/inp if abs(inp)>1e-8 else None
    max_phase_error=max(abs(q['input']+q['output']) for q in rows)
    if name=='engaged':
        passed=abs(inp)>=6.0 and ratio is not None and -.97>=ratio>=-1.03 and max_phase_error<=.13 and drift<.02
    elif name=='separated':
        passed=abs(inp)>=6.0 and abs(out)<.02 and drift<.02
    else:
        passed=abs(inp)<.02 and abs(out)<.02 and drift<.02
    result=dict(name=name,enabled=enabled,distance=distance,input=inp,output=out,ratio=ratio,max_phase_error=max_phase_error,center_drift=drift,passed=bool(passed),rows=rows)
    print('PHASE208_CASE',json.dumps({k:v for k,v in result.items() if k!='rows'},allow_nan=False),flush=True)
    return result
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    cases=[run_case(n,d,e,dest) for n,d,e in [('engaged',2.4,True),('separated',3.0,True),('motor_off',2.4,False)]]
    gate=all(c['passed'] for c in cases)
    out=dict(complete=True,native_executed=True,approved=False,gate=gate,cases=cases,physical_walk_certified=False,ideal_bearings=True,elapsed=time.perf_counter()-start)
    (dest/'phase208_motor_contact.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE208_SUMMARY',json.dumps(dict(gate=gate,passed=sum(c['passed'] for c in cases),count=len(cases),elapsed=out['elapsed'])),flush=True)
    assert gate
if __name__=='__main__':main()
