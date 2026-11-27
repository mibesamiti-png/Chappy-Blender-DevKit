"""Phase212-E: bounded coaxial cam stack, native kinematic assembly.
Round bore and ideal shared rotation: no actual shaft coupling, bearings,
guides, return force or rigid-body simulation. Keyframes are a preview.
"""
import math
from dataclasses import dataclass
from phase212_design_evaluation import finite,Limit,evaluate
from phase212_motion_spec import MotionSpec
from phase212_radial_cam import CamConfig,_edges,_nearest_and_inside
from phase212_cam_part import build

@dataclass(frozen=True)
class Station:
    track: str
    cam: CamConfig
    thickness: float
    bore_radius: float
    min_wall: float
    roller_thickness: float
    azimuth: float=0.
    def __post_init__(self):
        if not isinstance(self.cam,CamConfig) or not self.track or not all(finite(v) and v>0 for v in (self.thickness,self.bore_radius,self.min_wall,self.roller_thickness)) or not finite(self.azimuth):
            raise ValueError("invalid station dimensions")

def layout(spec,stations,shaft_radius,axial_gap,end_margin):
    stations=tuple(stations)
    if not isinstance(spec,MotionSpec) or not stations or len(stations)>8:
        raise ValueError("one to eight stations required")
    tracks={t.name:t for t in spec.tracks}
    if len({s.track for s in stations})!=len(stations) or set(s.track for s in stations)!=set(tracks):
        raise ValueError("one station per track required")
    if len({t.unit for t in tracks.values()})!=1 or next(iter(tracks.values())).unit not in ("mm","model_unit"):
        raise ValueError("common translation units required")
    if not all(finite(v) and v>0 for v in (shaft_radius,axial_gap,end_margin)):
        raise ValueError("positive assembly dimensions required")
    if any(shaft_radius>=s.bore_radius for s in stations):
        raise ValueError("shaft exceeds nominal bore")
    rows=[];z=0.
    for s in stations:
        half=max(s.thickness,s.roller_thickness)/2
        rows.append(dict(station=s,track=tracks[s.track],z=z+half,half=half))
        z+=2*half+axial_gap
    return rows,-end_margin,z-axial_gap+end_margin

def cylinder(name,radius,depth,location):
    import bpy
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=radius,depth=depth,location=location)
    ob=bpy.context.object;ob.name=name
    return ob

def assemble(spec,stations,shaft_radius,axial_gap,end_margin):
    import bpy
    from phase206_hybrid_machine import closed,polygon_area
    rows,lo,hi=layout(spec,stations,shaft_radius,axial_gap,end_margin)
    objects=[];data=[]
    try:
        shaft=cylinder("common shaft (ideal coupling)",shaft_radius,hi-lo,(0,0,(lo+hi)/2))
        objects.append(shaft)
        def cyl_audit(ob,r,h):
            xy=[(r*math.cos(i*math.tau/128),r*math.sin(i*math.tau/128)) for i in range(128)]
            return closed(ob.data,0,polygon_area(xy)*h)["passed"]
        if not cyl_audit(shaft,shaft_radius,hi-lo):
            raise ValueError("shaft mesh audit failed")
        for row in rows:
            s=row["station"];t=row["track"];z=row["z"]
            m,report=build(t,s.cam,s.thickness,s.bore_radius,s.min_wall)
            if m is None:raise ValueError("cam part rejected: "+s.track)
            cam=bpy.data.objects.new(s.track+" cam",m);bpy.context.collection.objects.link(cam);objects.append(cam)
            cam.location.z=z;cam.color=(.2,.45,.8,1)
            roller=cylinder(s.track+" roller",s.cam.roller_radius,s.roller_thickness,(0,0,z));objects.append(roller)
            roller.color=(.9,.55,.15,1)
            if not cyl_audit(roller,s.cam.roller_radius,s.roller_thickness):
                raise ValueError("roller mesh audit failed")
            # Native ring vertex layout is outer, inner, repeated at upper Z.
            n=s.cam.samples
            outer=tuple((float(v.co.x),float(v.co.y)) for v in list(m.vertices)[:n])
            inner=tuple((float(v.co.x),float(v.co.y)) for v in list(m.vertices)[n:2*n])
            bore_clear,inside=_nearest_and_inside((0,0),_edges(inner))
            if not inside or bore_clear-shaft_radius<=1e-6:
                raise ValueError("polygonal bore interferes with shaft")
            data.append(dict(**row,cam=cam,roller=roller,edges=_edges(outer),bore_clear=bore_clear-shaft_radius,report=report))
        return dict(shaft=shaft,stations=data,objects=objects,lo=lo,hi=hi,shaft_radius=shaft_radius,axial_gap=axial_gap)
    except Exception:
        for ob in reversed(objects):
            mesh=ob.data;bpy.data.objects.remove(ob,do_unlink=True)
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise

def pose(assembly,u):
    assembly["shaft"].rotation_euler.z=-math.tau*u
    for row in assembly["stations"]:
        s=row["station"];r=s.cam.pitch_base+row["track"].sample(u)[0]
        row["cam"].rotation_euler.z=s.azimuth-math.tau*u
        row["roller"].location=(r*math.cos(s.azimuth),r*math.sin(s.azimuth),row["z"])

def observe(assembly,u):
    import bpy
    from phase210_xy_cam import az,wrap
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    mat=lambda o:o.evaluated_get(dg).matrix_world.copy()
    S=mat(assembly["shaft"]);out=[];intervals=[]
    for row in assembly["stations"]:
        s=row["station"];t=row["track"];C=mat(row["cam"]);R=mat(row["roller"])
        p=C.inverted()@R.translation
        gap,inside=_nearest_and_inside((p.x,p.y),row["edges"])
        x,y,z=R.translation
        expected=s.cam.pitch_base+t.sample(u)[0]
        row_lo=min(C.translation.z-s.thickness/2,z-s.roller_thickness/2)
        row_hi=max(C.translation.z+s.thickness/2,z+s.roller_thickness/2)
        intervals.append((row_lo,row_hi))
        out.append(dict(track=s.track,contact_gap=gap-s.cam.roller_radius,inside=int(inside),
            tracking=abs(x*math.cos(s.azimuth)+y*math.sin(s.azimuth)-expected),
            axis_error=abs(-x*math.sin(s.azimuth)+y*math.cos(s.azimuth)),
            axial_error=abs(z-C.translation.z),sync=abs(wrap(az(C)-az(S)-s.azimuth)),
            shaft_center=math.hypot(C.translation.x-S.translation.x,C.translation.y-S.translation.y),
            bore_clear=row["bore_clear"],shaft_roller_gap=math.hypot(x-S.translation.x,y-S.translation.y)-assembly["shaft_radius"]-s.cam.roller_radius,
            axial_overlap=min(C.translation.z+s.thickness/2,z+s.roller_thickness/2)-max(C.translation.z-s.thickness/2,z-s.roller_thickness/2)))
    separation=min((b[0]-a[1] for a,b in zip(intervals,intervals[1:])),default=assembly["axial_gap"])
    return out,separation

def verify(assembly,samples=241,animate=False,mutation=None):
    import bpy
    if type(samples) is not int or not 2<=samples<=1441:raise ValueError("bounded samples required")
    observations={}
    def add(k,f,p,v):observations.setdefault(k,[]).append((f,p,v))
    sc=bpy.context.scene
    for i in range(samples):
        u=i/(samples-1);pose(assembly,u)
        if mutation:mutation(assembly,u)
        rows,sep=observe(assembly,u)
        for r in rows:
            name=r["track"]
            for k,v in r.items():
                if k!="track":add(name+":"+k,i+1,name,v)
        add("station_gap",i+1,"stack",sep)
        if animate:
            for ob in assembly["objects"]:
                ob.keyframe_insert(data_path="location",frame=i+1)
                ob.keyframe_insert(data_path="rotation_euler",frame=i+1)
    limits=[Limit("station_gap",lower=assembly["axial_gap"]-1e-5)]
    for row in assembly["stations"]:
        s=row["station"]
        for key,lo,hi in (("contact_gap",-s.cam.gap_tolerance,s.cam.gap_tolerance),("inside",None,0),
            ("tracking",None,1e-5),("axis_error",None,1e-5),("axial_error",None,1e-5),("sync",None,1e-5),
            ("shaft_center",None,1e-5),("bore_clear",1e-6,None),("shaft_roller_gap",1e-6,None),("axial_overlap",1e-6,None)):
            limits.append(Limit(s.track+":"+key,lower=lo,upper=hi))
    if animate:
        for ob in assembly["objects"]:
            for fc in ob.animation_data.action.fcurves:
                for k in fc.keyframe_points:k.interpolation="LINEAR"
        sc.frame_start=1;sc.frame_end=samples;sc.frame_set(1)
    return dict(evaluation=evaluate(limits,observations),samples=samples,kinematic_preview=animate,
        physical_motion_certified=False,torque_transfer_certified=False,manufacturing_certified=False)
