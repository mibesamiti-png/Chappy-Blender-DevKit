"""Phase212-F: native contact validation of generated motion-spec cam.
One powered cam and one passive follower. Ideal bearing/guide, gravity return,
no keyed shaft, no prescribed follower motion, no manufacturing claim.
"""
import math,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
import numpy as np
from phase208_motor_contact import body,constraint
from phase212_motion_spec import Knot,Track,MotionSpec
from phase212_radial_cam import CamConfig,_edges,_nearest_and_inside
from phase212_cam_part import build
from phase212_design_evaluation import Limit,evaluate,qualification

FPS=60;FRAMES=481
def fixture():
    t=Track('stroke','model_unit',(Knot(0,0),Knot(.25,0),Knot(.5,.6),Knot(.75,.6),Knot(1,0)))
    return MotionSpec((t,),math.tau),CamConfig(3.5,.25,.5,samples=360)

def setup(spec,cfg,offset,enabled):
    t=spec.tracks[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene;sc.gravity=(-9.81,0,0);sc.render.fps=FPS
    sc.frame_start=1;sc.frame_end=FRAMES
    bpy.ops.mesh.primitive_cube_add(size=.5,location=(0,0,-5))
    anchor=body(bpy.context.object,True);anchor.name='ideal guide reference';anchor.hide_render=True
    m,part=build(t,cfg,.6,.8,.5)
    assert m is not None and part['status']=='pass'
    cam=bpy.data.objects.new('generated powered cam',m);sc.collection.objects.link(cam)
    body(cam);cam.rigid_body.mass=3.;cam.color=(.25,.55,.85,1)
    constraint('ideal cam bearing','HINGE',anchor,cam,(0,0,0))
    motor=constraint('only motor','MOTOR',anchor,cam,(0,0,0),(0,-math.pi/2,0))
    motor.use_motor_lin=False;motor.use_motor_ang=enabled
    motor.motor_ang_target_velocity=math.tau/spec.period_seconds;motor.motor_ang_max_impulse=10.
    initial=cfg.pitch_base+t.sample(0)[0]
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=cfg.roller_radius,depth=.24,location=(initial,0,offset))
    roller=body(bpy.context.object);roller.name='passive roller'
    roller.rigid_body.collision_shape='CONVEX_HULL';roller.rigid_body.mass=.25
    roller.rigid_body.friction=.2;roller.color=(.9,.55,.15,1)
    guide=constraint('ideal linear guide with free spin','GENERIC',anchor,roller,(initial,0,offset))
    for axis in 'xyz':
        setattr(guide,'use_limit_lin_'+axis,True)
        setattr(guide,'limit_lin_'+axis+'_lower',-.10 if axis=='x' else 0.)
        setattr(guide,'limit_lin_'+axis+'_upper',1. if axis=='x' else 0.)
        setattr(guide,'use_limit_ang_'+axis,axis!='z')
        if axis!='z':
            setattr(guide,'limit_ang_'+axis+'_lower',0.)
            setattr(guide,'limit_ang_'+axis+'_upper',0.)
    world=sc.rigidbody_world;world.substeps_per_frame=16;world.solver_iterations=100
    world.point_cache.frame_start=1;world.point_cache.frame_end=FRAMES
    bpy.context.view_layer.update();sc.frame_set(1)
    cs=[o.rigid_body_constraint for o in sc.objects if o.rigid_body_constraint]
    assert len(cs)==3 and sum(c.type=='MOTOR' and c.use_motor_ang for c in cs)==int(enabled)
    assert all(o.animation_data is None and not o.rigid_body.kinematic for o in (cam,roller))
    assert sum(o.rigid_body is not None and o.rigid_body.type=='ACTIVE' for o in sc.objects)==2
    poly=tuple((float(v.co.x),float(v.co.y)) for v in list(m.vertices)[:cfg.samples])
    return sc,cam,roller,_edges(poly),part

def run(name,spec,cfg,offset,enabled,dest):
    sc,cam,roller,edges,part=setup(spec,cfg,offset,enabled)
    if name=='engaged':bpy.ops.wm.save_as_mainfile(filepath=str(dest/'contact_cam.blend'))
    rows=[];travel=0.;last=None;t=spec.tracks[0]
    for f in range(1,FRAMES+1):
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        A=cam.evaluated_get(dg).matrix_world.copy();B=roller.evaluated_get(dg).matrix_world.copy()
        ang=math.atan2(A[1][0],A[0][0])
        if last is not None:travel+=math.atan2(math.sin(ang-last),math.cos(ang-last))
        last=ang
        u=-travel/math.tau;expected=t.sample(u)[0]
        local=A.inverted()@B.translation;gap,inside=_nearest_and_inside((local.x,local.y),edges)
        actual=float(B.translation.x)-cfg.pitch_base
        rows.append(dict(frame=f,travel=travel,expected=expected,actual=actual,
            error=abs(actual-expected),gap=abs(gap-cfg.roller_radius),inside=int(inside),
            axial=abs(local.z),drift=max(A.translation.length,math.hypot(B.translation.y,B.translation.z-offset))))
    obs={};limits=[]
    def series(k,upper=None,lower=None,subset=None):
        limits.append(Limit(k,lower=lower,upper=upper))
        obs[k]=[(r['frame'],name,r[k]) for r in (rows if subset is None else subset)]
    def scalar(k,v,upper=None,lower=None):
        limits.append(Limit(k,lower=lower,upper=upper));obs[k]=[(FRAMES,name,v)]
    actual=[r['actual'] for r in rows];span=max(actual)-min(actual)
    series('drift',upper=.015)
    if enabled:scalar('full_turn',-travel,lower=math.tau)
    if name=='engaged':
        series('error',upper=.025);series('gap',upper=.025);series('inside',upper=0);series('axial',upper=.05)
        scalar('stroke',span,lower=.55,upper=.65)
        scalar('dwell_error',max(abs(r['actual']) for r in rows if abs(r['expected'])<=1e-8),upper=.025)
    elif name=='separated':
        series('axial',lower=.5)
        scalar('positive_lift',max(actual),upper=.025)
        scalar('settled_span',max(actual[60:])-min(actual[60:]),upper=.025)
    else:
        scalar('no_drive',abs(travel),upper=.15)
        scalar('no_lift',span,upper=.025)
    evaluation=evaluate(limits,obs)
    out=dict(name=name,enabled=enabled,offset=offset,part_status=part['status'],travel=travel,span=span,
        max_tracking_error=max(r['error'] for r in rows),max_radial_gap=max(r['gap'] for r in rows),
        evaluation=evaluation,rows=rows)
    print('PHASE212F_CASE',json.dumps({k:v for k,v in out.items() if k!='rows'},allow_nan=False),flush=True)
    return out

def main():
    assert bpy.app.version_string=='4.4.3'
    dest=ROOT/'results'/'phase212_contact';dest.mkdir(parents=True,exist_ok=True)
    spec,cfg=fixture()
    cases=[run(n,spec,cfg,z,e,dest) for n,z,e in [('engaged',0.,True),('separated',1.,True),('motor_off',0.,False)]]
    states={r['name']:r['evaluation']['status'] for r in cases}
    stages=dict(geometry='pass' if all(r['part_status']=='pass' for r in cases) else 'fail',
        full_motion=states['engaged'],
        negative_controls='pass' if all(states[n]=='pass' for n in ('separated','motor_off')) else 'fail')
    # Single-actuator fixture gate only; not whole-machine qualification.
    fixture_gate=qualification(stages,required=('geometry','full_motion','negative_controls'))
    out=dict(complete=True,native_executed=True,fixture_gate=fixture_gate,
        spec=spec.to_dict(),cases=cases,frames=FRAMES,ideal_guides=True,gravity_return=True,
        keyframed=False,whole_machine_certified=False,manufacturing_certified=False)
    (dest/'report.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE212F_SUMMARY',json.dumps(dict(fixture_gate=fixture_gate,states=states),allow_nan=False),flush=True)
if __name__=='__main__':main()
