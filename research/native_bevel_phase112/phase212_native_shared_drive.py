"""Phase212-G: two generated cam stations on one integrated rigid shaft.
The shaft and cam shells are an ideal rigid assembly, not a mechanical key.
Gravity return along +X follower guides; no target-position constraints.
One fixed fixture and two negative controls; no adaptive parameter search.
"""
import math,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from phase208_motor_contact import body,constraint
from phase210_xy_cam import az,wrap,limits
from phase212_motion_spec import Knot,Track,MotionSpec
from phase212_radial_cam import CamConfig,_nearest_and_inside
from phase212_cam_assembly import Station,assemble,pose,verify
from phase212_design_evaluation import Limit,evaluate,qualification
FPS=60;FRAMES=601;IMPULSE=40.
def fixture():
    a=Track('stroke','model_unit',(Knot(0,0),Knot(.25,0),Knot(.5,.6),Knot(.75,.6),Knot(1,0)))
    b=Track('secondary','model_unit',(Knot(0,0),Knot(.4,0),Knot(.65,.4),Knot(.8,.4),Knot(1,0)),phase_offset=.125)
    spec=MotionSpec((a,b),math.tau)
    stations=tuple(Station(t.name,CamConfig(3.5,.25,.5,samples=360),.6,.8,.5,.24) for t in spec.tracks)
    return spec,stations,{'stroke':.6,'secondary':.4}

def setup(spec,stations,separated,enabled):
    if len(stations)!=2 or any(s.azimuth!=0 for s in stations) or any(t.unit!='model_unit' for t in spec.tracks):
        raise ValueError('bounded two-station +X model-unit fixture only')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene;sc.gravity=(-9.81,0,0);sc.render.fps=FPS;sc.frame_start=1;sc.frame_end=FRAMES
    a=assemble(spec,stations,.6,.4,.4)
    kinematic=verify(a,241)
    assert kinematic['evaluation']['status']=='pass'
    pose(a,0.);bpy.context.view_layer.update()
    shaft=a['shaft'];inverse=shaft.matrix_world.inverted()
    vs=[tuple(v.co) for v in shaft.data.vertices];fs=[tuple(p.vertices) for p in shaft.data.polygons]
    for row in a['stations']:
        cam=row['cam'];local=inverse@cam.matrix_world;row['cam_local']=local.copy()
        n=len(vs);vs.extend(tuple(local@v.co) for v in cam.data.vertices)
        fs.extend(tuple(n+i for i in p.vertices) for p in cam.data.polygons)
        mesh=cam.data;bpy.data.objects.remove(cam,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
        row['cam']=None
    old=shaft.data;m=bpy.data.meshes.new('ideal integrated shaft and two cam shells')
    m.from_pydata(vs,[],fs);m.update();shaft.data=m
    if old.users==0:bpy.data.meshes.remove(old)
    shaft.name='integrated powered camshaft';body(shaft);shaft.rigid_body.mass=6.5
    shaft.color=(.25,.55,.85,1)
    origin=shaft.location.copy()
    bpy.ops.mesh.primitive_cube_add(size=.5,location=(0,0,-5))
    anchor=body(bpy.context.object,True);anchor.name='ideal stationary reference';anchor.hide_render=True
    constraint('ideal shaft bearing','HINGE',anchor,shaft,origin)
    motor=constraint('only motor','MOTOR',anchor,shaft,origin,(0,-math.pi/2,0))
    motor.use_motor_lin=False;motor.use_motor_ang=enabled
    motor.motor_ang_target_velocity=math.tau/spec.period_seconds;motor.motor_ang_max_impulse=IMPULSE
    shift=a['hi']-a['lo']+1. if separated else 0.
    for row in a['stations']:
        roller=row['roller'];roller.location.z+=shift;row['roller_z']=float(roller.location.z)
        body(roller);roller.rigid_body.mass=.25;roller.rigid_body.collision_shape='CONVEX_HULL';roller.rigid_body.friction=.2
        roller.color=(.9,.55,.15,1)
        c=constraint(row['track'].name+' ideal guide','GENERIC',anchor,roller,roller.location)
        limits(c,{'x':(-.1,1.),'y':(0.,0.),'z':(0.,0.)},{'x':(0.,0.),'y':(0.,0.)})
    world=sc.rigidbody_world;world.substeps_per_frame=16;world.solver_iterations=100
    world.point_cache.frame_start=1;world.point_cache.frame_end=FRAMES
    bpy.context.view_layer.update();sc.frame_set(1)
    active=[o for o in sc.objects if o.rigid_body and o.rigid_body.type=='ACTIVE']
    cs=[o.rigid_body_constraint for o in sc.objects if o.rigid_body_constraint]
    assert len(active)==3 and len(cs)==4 and sum(c.type=='MOTOR' and c.use_motor_ang for c in cs)==int(enabled)
    assert all(o.animation_data is None and not o.rigid_body.kinematic for o in active)
    return sc,a,origin,kinematic

def run(name,spec,stations,strokes,separated,enabled,dest):
    sc,a,origin,kinematic=setup(spec,stations,separated,enabled)
    if name=='engaged':bpy.ops.wm.save_as_mainfile(filepath=str(dest/'physical_cam_stack.blend'))
    rows=[];travel=0.;last=None;shaft=a['shaft'];obs={};bounds=[]
    for f in range(1,FRAMES+1):
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        S=shaft.evaluated_get(dg).matrix_world.copy();ang=az(S)
        if last is not None:travel+=wrap(ang-last)
        last=ang;u=-travel/math.tau
        r=dict(frame=f,travel=travel,shaft_drift=(S.translation-origin).length)
        for item in a['stations']:
            t=item['track'];s=item['station'];A=S@item['cam_local']
            B=item['roller'].evaluated_get(dg).matrix_world.copy()
            p=A.inverted()@B.translation;gap,inside=_nearest_and_inside((p.x,p.y),item['edges'])
            k=t.name+':';actual=float(B.translation.x)-s.cam.pitch_base;expected=t.sample(u)[0]
            # All cam stations, not only the intended one, are axially separated in the negative control.
            clearance=min(abs(B.translation.z-other['z'])-(s.roller_thickness+other['station'].thickness)/2 for other in a['stations'])
            r.update({k+'actual':actual,k+'expected':expected,k+'error':abs(actual-expected),
                k+'gap':abs(gap-s.cam.roller_radius),k+'inside':int(inside),k+'axial':abs(p.z),
                k+'drift':math.hypot(B.translation.y,B.translation.z-item['roller_z']),k+'all_cam_axial_clearance':clearance})
        rows.append(r)
    def series(k,upper=None,lower=None):
        bounds.append(Limit(k,lower=lower,upper=upper));obs[k]=[(r['frame'],k,r[k]) for r in rows]
    def scalar(k,v,upper=None,lower=None):
        bounds.append(Limit(k,lower=lower,upper=upper));obs[k]=[(FRAMES,k,v)]
    series('shaft_drift',upper=.015)
    scalar('full_turn' if enabled else 'no_drive',-travel if enabled else abs(travel),lower=math.tau if enabled else None,upper=None if enabled else .15)
    outputs={}
    for t in spec.tracks:
        k=t.name+':';vals=[r[k+'actual'] for r in rows];span=max(vals)-min(vals)
        series(k+'drift',upper=.015)
        if name=='engaged':
            series(k+'error',upper=.025);series(k+'gap',upper=.025);series(k+'inside',upper=0);series(k+'axial',upper=.05)
            scalar(k+'stroke',span,lower=strokes[t.name]-.05,upper=strokes[t.name]+.05)
            dwell=[abs(r[k+'actual']) for r in rows if abs(r[k+'expected'])<=1e-8]
            scalar(k+'dwell_error',max(dwell),upper=.025)
        elif separated:
            series(k+'all_cam_axial_clearance',lower=.5)
            scalar(k+'positive_lift',max(vals),upper=.025)
            scalar(k+'settled_span',max(vals[60:])-min(vals[60:]),upper=.025)
        else:scalar(k+'no_lift',span,upper=.025)
        outputs[t.name]=dict(span=span,max_error=max(r[k+'error'] for r in rows),max_gap=max(r[k+'gap'] for r in rows))
    evaluation=evaluate(bounds,obs)
    result=dict(name=name,travel=travel,outputs=outputs,evaluation=evaluation,
        kinematic_status=kinematic['evaluation']['status'],rows=rows)
    print('PHASE212G_CASE',json.dumps({k:v for k,v in result.items() if k!='rows'},allow_nan=False),flush=True)
    return result

def main():
    assert bpy.app.version_string=='4.4.3'
    dest=ROOT/'results'/'phase212_shared_drive';dest.mkdir(parents=True,exist_ok=True)
    spec,stations,strokes=fixture()
    cases=[run(n,spec,stations,strokes,s,e,dest) for n,s,e in [('engaged',False,True),('separated',True,True),('motor_off',False,False)]]
    states={c['name']:c['evaluation']['status'] for c in cases}
    stages=dict(geometry='pass' if all(c['kinematic_status']=='pass' for c in cases) else 'fail',
        full_motion=states['engaged'],negative_controls='pass' if all(states[k]=='pass' for k in ('separated','motor_off')) else 'fail')
    gate=qualification(stages,required=('geometry','full_motion','negative_controls'))
    d=dict(complete=True,native_executed=True,fixture_gate=gate,cases=cases,spec=spec.to_dict(),
        frames=FRAMES,cam_count=2,active_bodies=3,motor_count=1,ideal_rigid_camshaft=True,
        ideal_guides=True,gravity_return=True,keyframed=False,torque_transfer_certified=False,manufacturing_certified=False)
    (dest/'report.json').write_text(json.dumps(d,indent=2,allow_nan=False))
    print('PHASE212G_SUMMARY',json.dumps(dict(fixture_gate=gate,states=states),allow_nan=False),flush=True)
if __name__=='__main__':main()
