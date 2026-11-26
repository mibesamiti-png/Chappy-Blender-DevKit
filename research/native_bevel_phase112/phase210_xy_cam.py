"""Phase210-C3: shared shaft, two physical cam contacts and XY carriage.
Ideal bearings/guides, two nonspinning sliders with hinged free rollers,
and two cross-slide couplers transmit independent coordinates to a real
dynamic output body. Gravity components are -9.81 along both test axes
(an artificial laboratory preload, not a field-ready return mechanism).
No target-position constraints, keyframes, or follower motors.
"""
import json,math,time,sys
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase208_motor_contact import active,body,constraint
from phase206_hybrid_machine import ring,BORE,key_check
from phase210_inverse_cam import profile,law,ROLLER
from phase210_stride_contact import START,SPAN
FPS=60;FRAMES=601;IMPULSE=60.
def box(name,location,dimensions,mass):
    bpy.ops.mesh.primitive_cube_add(size=1.,location=location)
    ob=bpy.context.object;ob.name=name;ob.dimensions=dimensions
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    body(ob);ob.rigid_body.collision_shape='BOX';ob.rigid_body.mass=mass
    return ob
def limits(c,linear,angular):
    # Explicitly leave every unspecified coordinate free.
    for prefix,values in [('lin',linear),('ang',angular)]:
        for axis in 'xyz':
            key=prefix+'_'+axis
            setattr(c,'use_limit_'+key,axis in values)
            if axis in values:
                lo,hi=values[axis]
                setattr(c,'limit_'+key+'_lower',lo)
                setattr(c,'limit_'+key+'_upper',hi)
    return c
def setup(separated,enabled,substeps=16,duty=.75,start=START,spring=None,preload=0.):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene
    sc.gravity=(-9.81,-9.81,0.) if spring is None else (0.,-9.81,0.);sc.render.fps=FPS;sc.frame_start=1;sc.frame_end=FRAMES
    bpy.ops.mesh.primitive_cube_add(size=.5,location=(0.,0.,-5.))
    anchor=body(bpy.context.object,True);anchor.name='ideal fixed guide reference';anchor.hide_render=True
    shaft=box('common keyed shaft',(0.,0.,.5),(.18,.18,1.5),.2)
    shaft.rotation_euler.z=-start;shaft.color=(.5,.5,.55,1)
    constraint('shaft bearing','HINGE',anchor,shaft,(0.,0.,.5))
    motor=constraint('only shaft motor','MOTOR',anchor,shaft,(0.,0.,.5),(0.,-math.pi/2,0.))
    motor.use_motor_lin=False;motor.use_motor_ang=enabled
    motor.motor_ang_target_velocity=1.;motor.motor_ang_max_impulse=IMPULSE
    assert preload>=0 and (preload==0 or (spring is not None and spring>0))
    items=[];zero={a:(0.,0.) for a in 'xyz'}
    for kind,axis,base,z,phi in [('stride','x',7.,0.,0.),('lift','y',2.5,1.,math.pi/2)]:
        c=profile(kind,base,duty=duty)
        # Rotate the actual keyed profile relative to the shaft for the Y
        # follower; the square bore is invariant under this 90-degree index.
        rot=np.array([[math.cos(phi),-math.sin(phi)],[math.sin(phi),math.cos(phi)]])
        xy=c@rot.T
        m,a=ring(kind+' cam',[tuple(v) for v in xy],[tuple(v*BORE/max(abs(v))) for v in xy])
        assert a['passed'] and key_check(m)
        cam=bpy.data.objects.new(kind+' keyed cam',m);sc.collection.objects.link(cam)
        cam.location=(0.,0.,z);cam.rotation_euler.z=-start
        body(cam);cam.rigid_body.mass=3.;cam.color=(.8,.55,.15,1) if axis=='y' else (.25,.55,.8,1)
        constraint(kind+' rigid shaft coupling','FIXED',shaft,cam,(0.,0.,z))
        initial=base+float(law(start,kind,duty));rz=z+((-1. if axis=='x' else 1.) if separated else 0.)
        side=-1. if axis=='x' else 1.
        pos=(initial,0.,rz) if axis=='x' else (0.,initial,rz)
        bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=ROLLER,depth=.24,location=pos)
        roller=body(bpy.context.object);roller.name=kind+' free roller'
        roller.rigid_body.collision_shape='CONVEX_HULL';roller.rigid_body.mass=.25
        roller.rigid_body.friction=.2;roller.color=(.25,.75,.4,1)
        spos=(pos[0],pos[1],rz+side*.4)
        slide=box(kind+' nonspinning slider',spos,(.18,.18,.18),.1)
        slide.color=(.3,.75,.5,1)
        constraint(kind+' free roller bearing','HINGE',slide,roller,pos)
        lin=dict(zero);lin[axis]=(-.15,3. if axis=='x' else 1.)
        limits(constraint(kind+' prismatic guide','GENERIC',anchor,slide,spos),lin,zero)
        weight=None;weight_origin=None
        if axis=='x' and spring is not None and spring>0:
            spring_anchor=anchor
            if preload>0:
                # Gravity moves the initially relaxed spring anchor down and inward.
                weight_origin=(0.,-1.,-3.)
                weight=box('passive spring preload weight',weight_origin,(.4,.4,.4),3.)
                guide=dict(zero);guide['x']=(-math.sqrt(2)*preload,0.)
                limits(constraint('preload diagonal guide','GENERIC',anchor,weight,weight_origin,(0.,0.,math.pi/4)),guide,zero)
                spring_anchor=weight
            c=limits(constraint('passive stride return spring','GENERIC_SPRING',spring_anchor,slide,spos),{}, {})
            c.spring_type='SPRING2';c.use_spring_x=True;c.spring_stiffness_x=spring;c.spring_damping_x=.5
        items.append(dict(kind=kind,axis=axis,base=base,z=z,rz=rz,initial=initial,cam=cam,roller=roller,slide=slide,xy=xy,weight=weight,weight_origin=weight_origin))
    outpos=(items[0]['initial'],items[1]['initial'],3.5)
    carriage=box('physical XY output carriage',outpos,(.32,.32,.25),.1);carriage.color=(.9,.3,.2,1)
    limits(constraint('output planar guide','GENERIC',anchor,carriage,outpos),{'z':(0.,0.)},zero)
    for it in items:
        # Only one linear component is constrained per cross-slide. Since
        # each slider is nonspinning, its constraint frame stays aligned.
        limits(constraint(it['kind']+' output cross-slide','GENERIC',it['slide'],carriage,outpos),
            {it['axis']:(0.,0.)},{})
    world=sc.rigidbody_world;world.substeps_per_frame=substeps;world.solver_iterations=100
    world.point_cache.frame_start=1;world.point_cache.frame_end=FRAMES
    bpy.context.view_layer.update();sc.frame_set(1)
    objs=[shaft,carriage]+[it[k] for it in items for k in ('cam','roller','slide')]
    objs.extend(it['weight'] for it in items if it['weight'] is not None)
    cs=[o.rigid_body_constraint for o in sc.objects if o.rigid_body_constraint]
    assert len(cs)==11+int(spring is not None and spring>0)+int(preload>0) and sum(c.type=='MOTOR' and c.use_motor_ang for c in cs)==int(enabled)
    assert all(o.animation_data is None and not o.rigid_body.kinematic for o in objs)
    return sc,shaft,carriage,items
def wrap(a):return math.atan2(math.sin(a),math.cos(a))
def az(M):return math.atan2(M[1][0],M[0][0])
def run_case(name,separated,enabled,dest,substeps=16,duty=.75,start=START,spring=None,preload=0.):
    sc,shaft,carriage,items=setup(separated,enabled,substeps,duty,start,spring,preload)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/('phase210_xy_'+name+'.blend')))
    rows=[];last=None;travel=0.
    for f in range(1,FRAMES+1):
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        mat=lambda o:o.evaluated_get(dg).matrix_world.copy()
        S=mat(shaft);O=mat(carriage);a=az(S)
        if last is not None:travel+=wrap(a-last)
        last=a;phase=(start-travel)%math.tau
        row=dict(frame=f,travel=travel,phase=phase,shaft_drift=(S.translation-Vector((0.,0.,.5))).length,
            output_z_drift=abs(O.translation.z-3.5))
        for i,it in enumerate(items):
            kind=it['kind'];A=mat(it['cam']);B=mat(it['roller']);D=mat(it['slide'])
            local=A.inverted()@B.translation;p=np.array((local.x,local.y));c=it['xy']
            edge=np.roll(c,-1,axis=0)-c;delta=p-c
            t=np.clip(np.sum(delta*edge,axis=1)/np.sum(edge*edge,axis=1),0.,1.)
            gap=float(np.linalg.norm(delta-t[:,None]*edge,axis=1).min()-ROLLER)
            expected=float(law(phase,kind,duty));actual=float(B.translation[i]-it['base'])
            output=float(O.translation[i]-it['base'])
            row.update({kind+'_expected':expected,kind+'_follower':actual,kind+'_output':output,
                kind+'_error':output-expected,kind+'_coupler_error':output-actual,
                kind+'_gap':gap,kind+'_axial':abs(local.z),
                kind+'_sync':abs(wrap(az(A)-a)),kind+'_cam_drift':(A.translation-Vector((0.,0.,it['z']))).length,
                kind+'_guide_drift':math.hypot(B.translation[1-i],B.translation.z-it['rz']),
                kind+'_slider_drift':abs(D.translation[1-i]),
                kind+'_slide_displacement':float(D.translation[i]-it['initial']),
                kind+'_roller_slide_error':float(B.translation[i]-D.translation[i]),
                kind+'_slide_output_error':float(O.translation[i]-D.translation[i])})
        it=items[0]
        if it['weight'] is not None:
            W=mat(it['weight']);dw=W.translation-Vector(it['weight_origin'])
            row['preload_anchor_x']=float(dw.x)
            row['preload_anchor_y']=float(dw.y)
            row['spring_extension_x']=row['stride_slide_displacement']-float(dw.x)
            row['spring_force_proxy']=spring*row['spring_extension_x']
        row['xy_error']=math.hypot(row['stride_error'],row['lift_error'])
        rows.append(row)
    peak=lambda k:max(abs(r[k]) for r in rows)
    span=lambda k:max(r[k] for r in rows)-min(r[k] for r in rows)
    amp={k:span(k+'_output') for k in ('stride','lift')}
    sync=max(peak(k+'_sync') for k in amp)
    coupler=max(peak(k+'_coupler_error') for k in amp)
    drift=max(peak(k) for k in ['shaft_drift','output_z_drift']+[a+b for a in amp for b in ('_cam_drift','_guide_drift','_slider_drift')])
    gaps=max(peak(k+'_gap') for k in amp)
    stance=[r for r in rows if r['phase']<=duty*math.tau]
    dwell=max((abs(r['lift_output']) for r in stance),default=0.)
    checks=dict(shaft_sync=sync<=.015,coupling=coupler<=.015,guide_drift=drift<=.015)
    span_expected=SPAN if duty==.75 else float(np.ptp(law(np.arange(36000)*math.tau/36000,'stride',duty)))
    if name=='engaged':
        checks.update(full_cycle=travel<=-math.tau,xy_tracking=peak('xy_error')<=.04,
            axis_tracking=all(peak(k+'_error')<=.025 for k in amp),
            stride=abs(amp['stride']-span_expected)<=.05,lift=.55<=amp['lift']<=.65,
            stance_height=bool(stance) and dwell<=.025,contact=gaps<=.025,
            axial_overlap=all(peak(k+'_axial')<.05 for k in amp))
    elif name=='separated':
        checks.update(full_cycle=travel<=-math.tau,
            no_periodic_output=all(max(r[k+'_output'] for r in rows[120:])-min(r[k+'_output'] for r in rows[120:])<=.025 for k in amp),
            axial_clearance=all(min(r[k+'_axial'] for r in rows)>.5 for k in amp))
    else:
        # Combined gravity may backdrive to a nearby energy minimum. No
        # brake is added; reject sustained rotation or large output motion.
        checks.update(no_sustained_drive=abs(travel)<=.4,
            no_large_output=amp['stride']<=.25 and amp['lift']<=.15)
    out=dict(name=name,separated=separated,enabled=enabled,substeps=substeps,duty=duty,spring=spring,preload=preload,travel=travel,amplitude=amp,
        max_xy_error=peak('xy_error'),max_axis_error={k:peak(k+'_error') for k in amp},
        max_sync=sync,max_coupler_error=coupler,max_drift=drift,max_contact_gap=gaps,
        max_stance_height=dwell,checks=checks,passed=all(checks.values()),rows=rows)
    print('PHASE210C3_CASE',json.dumps({k:v for k,v in out.items() if k!='rows'},allow_nan=False),flush=True)
    return out
def main():
    assert bpy.app.version_string=='4.4.3'
    start=time.perf_counter();dest=ROOT/'results';dest.mkdir(exist_ok=True)
    cases=[run_case(n,s,e,dest) for n,s,e in [('engaged',False,True),('separated',True,True),('motor_off',False,False)]]
    out=dict(complete=True,native_executed=True,approved=False,physical_gate=all(c['passed'] for c in cases),
        cases=cases,frames=FRAMES,impulse=IMPULSE,ideal_guides=True,ideal_shaft_coupling=True,
        gravity_preload=[-9.81,-9.81,0.],physical_output_body=True,walking_certified=False,
        elapsed=time.perf_counter()-start)
    (dest/'phase210_xy_cam.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE210C3_SUMMARY',json.dumps({k:v for k,v in out.items() if k!='cases'},allow_nan=False),flush=True)
if __name__=='__main__':main()
