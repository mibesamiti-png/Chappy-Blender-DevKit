"""Phase212-K: fixed four-slot Geneva, real motor/contact experiment.
Ideal bearings, zero gravity and no external load. Rigid driver contains
locking disk, pin and elevated support shells. No prescribed wheel motion.
Separate axial-control scene and motor-off scene. Retain failed results.
"""
import math,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from mathutils import Vector
from phase208_motor_contact import body,constraint
from phase210_xy_cam import az,wrap
from phase212_geneva import Geneva
from phase212_geneva_geometry import profiles
from phase212_native_geneva_geometry import part
from phase204_four_bar import prism
from phase206_hybrid_machine import closed,polygon_area
from phase212_design_evaluation import Limit,evaluate,qualification

FPS=60;FRAMES=961;IMPULSE=40.
def circle(r,n=96):
    return [(r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n)) for i in range(n)]
def combine(name,parts):
    vs=[];fs=[]
    for m,x,y,z in parts:
        n=len(vs);vs.extend((v.co.x+x,v.co.y+y,v.co.z+z) for v in m.vertices)
        fs.extend(tuple(n+i for i in p.vertices) for p in m.polygons)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vs,[],fs);mesh.update()
    for m,*_ in parts:bpy.data.meshes.remove(m)
    return mesh

def setup(separated,enabled,relief_degrees=35,impulse=IMPULSE):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene;sc.gravity=(0.,0.,0.);sc.render.fps=FPS
    sc.frame_start=1;sc.frame_end=FRAMES
    g=Geneva(4,10,.3,.05);wheel,driver,dims=profiles(g,relief_degrees)
    wm,wa=part('four slot wheel',wheel,.6,.7)
    dm,da=part('relieved lock disk',driver,.6,.5,radial=True)
    assert wa['passed'] and da['passed']
    r=g.crank_radius
    pin=prism('supported pin',circle(.3),-.3,.9)
    armxy=[(-r-.4,-.4),(.65,-.4),(.65,.4),(-r-.4,.4)]
    arm=prism('elevated support',armxy,.6,.9)
    hub=prism('driver support hub',circle(.65),-.3,.9)
    for m,xy,h in ((pin,circle(.3),1.2),(arm,armxy,.3),(hub,circle(.65),1.2)):
        assert closed(m,0,polygon_area(xy)*h)['passed']
    # Deliberately ideal rigid overlapping support shells, not welded geometry.
    m=combine('rigid supported Geneva driver',[(dm,0,0,0),(pin,-r,0,0),(arm,0,0,0),(hub,0,0,0)])
    z=2. if separated else 0.
    inp=bpy.data.objects.new('only powered driver',m);sc.collection.objects.link(inp)
    inp.location=(10.,0.,z);inp.rotation_euler.z=math.pi
    out=bpy.data.objects.new('passive four slot wheel',wm);sc.collection.objects.link(out)
    inp.color=(.9,.55,.15,1);out.color=(.25,.55,.85,1)
    for o,mass in ((inp,3.),(out,3.)):
        body(o);o.rigid_body.mass=mass;o.rigid_body.friction=.1
    bpy.ops.mesh.primitive_cube_add(size=.5,location=(0.,0.,-5.))
    anchor=body(bpy.context.object,True);anchor.name='ideal bearing reference';anchor.hide_render=True
    constraint('driver bearing','HINGE',anchor,inp,(10.,0.,z))
    constraint('passive wheel bearing','HINGE',anchor,out,(0.,0.,0.))
    c=constraint('only motor','MOTOR',anchor,inp,(10.,0.,z),(0.,-math.pi/2,0.))
    c.use_motor_lin=False;c.use_motor_ang=enabled;c.motor_ang_target_velocity=1.;c.motor_ang_max_impulse=impulse
    world=sc.rigidbody_world;world.substeps_per_frame=32;world.solver_iterations=100
    world.point_cache.frame_start=1;world.point_cache.frame_end=FRAMES
    bpy.context.view_layer.update();sc.frame_set(1)
    bodies=[o for o in sc.objects if o.rigid_body and o.rigid_body.type=='ACTIVE']
    cs=[o.rigid_body_constraint for o in sc.objects if o.rigid_body_constraint]
    assert len(bodies)==2 and len(cs)==3 and sum(q.type=='MOTOR' and q.use_motor_ang for q in cs)==int(enabled)
    assert all(o.animation_data is None and not o.rigid_body.kinematic for o in bodies)
    return sc,g,inp,out,z

def run(name,separated,enabled,dest,relief_degrees=35,impulse=IMPULSE):
    sc,g,inp,out,z=setup(separated,enabled,relief_degrees,impulse)
    if name=='engaged':bpy.ops.wm.save_as_mainfile(filepath=str(dest/'geneva_physical_trial.blend'))
    rows=[];last=None;travel=[0.,0.]
    for f in range(1,FRAMES+1):
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        A=inp.evaluated_get(dg).matrix_world.copy();B=out.evaluated_get(dg).matrix_world.copy()
        angles=[az(A),az(B)]
        if last is not None:
            for i in range(2):travel[i]+=wrap(angles[i]-last[i])
        last=angles;u=-travel[0]/math.tau;expected=g.sample(u)[0]
        phase=u%1
        # Exclude engagement handovers from dwell-only check, not full tracking.
        dwell=phase<g.start-.02 or phase>g.end+.02
        pin=A@Vector((-g.crank_radius,0,0))
        rows.append(dict(frame=f,input=travel[0],output=travel[1],expected=expected,
            error=abs(travel[1]-expected),dwell=dwell,phase=phase,
            pin_x=pin.x,pin_y=pin.y,axial_clearance=abs(A.translation.z-B.translation.z)-.6,
            drift=max((A.translation-Vector((10,0,z))).length,B.translation.length)))
    obs={};bounds=[]
    def series(k,upper=None,lower=None,subset=None):
        bounds.append(Limit(k,lower=lower,upper=upper))
        obs[k]=[(q['frame'],name,q[k]) for q in (rows if subset is None else subset)]
    def scalar(k,v,upper=None,lower=None):
        bounds.append(Limit(k,lower=lower,upper=upper));obs[k]=[(FRAMES,name,v)]
    series('drift',upper=.015)
    scalar('two_turns' if enabled else 'no_input',-travel[0] if enabled else abs(travel[0]),
        lower=2*math.tau if enabled else None,upper=None if enabled else .02)
    if name=='engaged':
        series('error',upper=.07)
        # Independent dwell-center checkpoints across completed input cycles.
        checkpoints=[]
        for n in range(1,int(max(0.,-travel[0])/math.tau)+1):
            q=min(rows,key=lambda v:abs(-v['input']/math.tau-n))
            checkpoints.append((q['frame'],name,abs(q['output']-n*g.advance)))
        bounds.append(Limit('indexed_steps',upper=.045));obs['indexed_steps']=checkpoints
        bounds.append(Limit('dwell_tracking',upper=.045));obs['dwell_tracking']=[(q['frame'],name,q['error']) for q in rows if q['dwell']]
        scalar('two_index_minimum',travel[1],lower=math.pi-.07)
    else:
        scalar('no_output',max(abs(q['output']) for q in rows),upper=.02)
        if separated:series('axial_clearance',lower=1.3)
    ev=evaluate(bounds,obs)
    out=dict(name=name,relief_degrees=relief_degrees,impulse=impulse,input=travel[0],output=travel[1],max_error=max(q['error'] for q in rows),
        evaluation=ev,rows=rows)
    print('PHASE212K_CASE',json.dumps({k:v for k,v in out.items() if k!='rows'},allow_nan=False),flush=True)
    return out
def main():
    assert bpy.app.version_string=='4.4.3'
    dest=ROOT/'results'/'phase212_geneva_contact';dest.mkdir(parents=True,exist_ok=True)
    cases=[run(n,s,e,dest) for n,s,e in [('engaged',False,True),('separated',True,True),('motor_off',False,False)]]
    states={c['name']:c['evaluation']['status'] for c in cases}
    controls=qualification(states,required=('separated','motor_off'))['status']
    gate=qualification(dict(full_motion=states['engaged'],negative_controls=controls),required=('full_motion','negative_controls'))
    out=dict(complete=True,native_executed=True,frames=FRAMES,cases=cases,fixture_gate=gate,
        motor_count=1,active_bodies=2,keyframed=False,ideal_bearings=True,ideal_rigid_driver=True,
        zero_external_load=True,manufacturing_certified=False)
    (dest/'report.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE212K_SUMMARY',json.dumps(dict(gate=gate,states=states),allow_nan=False),flush=True)
if __name__=='__main__':main()
