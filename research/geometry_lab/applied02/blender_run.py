"""Synthetic editable eyewear. No private source data. Blender 4.4.3."""
import bpy, math, json, sys, argparse
from pathlib import Path
from mathutils import Vector, Matrix
from math import sin, cos, pi

def mat(name,color,metal=0,rough=.3,trans=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=m.node_tree.nodes.get("Principled BSDF")
    for k,v in (("Base Color",(*color,1)),("Metallic",metal),("Roughness",rough),("Transmission Weight",trans)):
        n.inputs[k].default_value=v
    return m
def mesh(name,v,f,m):
    d=bpy.data.meshes.new(name);d.from_pydata(v,[],f);d.update()
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);d.materials.append(m)
    for p in d.polygons:p.use_smooth=True
    return o
def mods(o,thick,bevel):
    mir=o.modifiers.new("Paired symmetry","MIRROR");mir.use_axis[0]=True;mir.use_axis[1]=False;mir.use_axis[2]=False;mir.use_mirror_merge=False
    s=o.modifiers.new("Editable depth","SOLIDIFY");s.thickness=thick;s.offset=0
    b=o.modifiers.new("Rounded edges","BEVEL");b.width=bevel;b.segments=3
    b.limit_method="ANGLE"
def contour(t,rx,rz):
    x=.0345+rx*cos(t);z=rz*sin(t)
    return (x,.003*(x/.07)**2,z)
def curve(name,points,rad,m,parent=None):
    d=bpy.data.curves.new(name,"CURVE");d.dimensions="3D";d.resolution_u=10;d.bevel_resolution=3;d.bevel_depth=rad;d.use_fill_caps=True
    s=d.splines.new("BEZIER");s.bezier_points.add(len(points)-1)
    for b,p in zip(s.bezier_points,points):
        b.co=p;b.handle_left_type=b.handle_right_type="AUTO"
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);d.materials.append(m);o.parent=parent
    return o
def cylinder(name,center,r,h,m,parent=None):
    n=16;v=[(center[0]+r*cos(2*pi*i/n),center[1]+r*sin(2*pi*i/n),center[2]+z) for z in (-h/2,h/2) for i in range(n)]
    f=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]+[tuple(reversed(range(n))),tuple(range(n,2*n))]
    o=mesh(name,v,f,m);o.parent=parent;return o
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.unit_settings.system="METRIC"
    acetate=mat("Deep petrol acetate",(.025,.12,.13),.15,.26)
    gold=mat("Brushed champagne alloy",(.52,.31,.12),.78,.3)
    lensmat=mat("Light smoke lens",(.82,.91,.96),0,.11,.9)
    n=32
    v=[contour(2*pi*i/n,rx,rz) for rx,rz in ((.0265,.0175),(.030,.021)) for i in range(n)]
    f=[(i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n)]
    rim=mesh("Rim_master",v,f,acetate);mods(rim,.005,.0007)
    v=[contour(2*pi*i/n,.02665,.01765) for i in range(n)]+[(.0345,.003*(.0345/.07)**2,0)]
    f=[(n,(i+1)%n,i) for i in range(n)]
    lens=mesh("Lens_master",v,f,lensmat);mods(lens,.0016,.00025)
    curve("Bridge",[(-.009,.0005,.004),(-.005,-.001,.010),(0,-.002,.012),(.005,-.001,.010),(.009,.0005,.004)],.00155,gold)
    for sign,label in ((1,"R"),(-1,"L")):
        pivot=bpy.data.objects.new("Hinge_"+label,None);bpy.context.collection.objects.link(pivot);pivot.empty_display_type="ARROWS";pivot.empty_display_size=.008;pivot.location=(sign*.069,.005,.003)
        curve("Endpiece_"+label,[(sign*.062,.002,.004),(sign*.066,.003,.003),(sign*.069,.005,.003)],.0018,acetate)
        cylinder("Pin_"+label,(sign*.069,.005,.003),.0014,.006,gold)
        cylinder("Sleeve_"+label,(0,0,0),.0022,.0032,gold,pivot)
        curve("Temple_"+label,[(0,0,0),(sign*.001,.02,0),(sign*.0005,.073,-.001),(-sign*.004,.108,-.004),(-sign*.009,.131,-.020)],.00145,gold,pivot)
        curve("Tip_"+label,[(-sign*.003,.102,-.003),(-sign*.005,.115,-.008),(-sign*.009,.131,-.020)],.00225,acetate,pivot)
    for o in bpy.context.scene.objects:
        if o.type in ("MESH","CURVE"):o["synthetic_research"]=True
def snapshot():
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();out={}
    for o in bpy.context.scene.objects:
        if o.type not in ("MESH","CURVE"):continue
        ev=o.evaluated_get(dg);m=ev.to_mesh()
        try:
            m.calc_loop_triangles()
            out[o.name]={"vertices":[list(ev.matrix_world@v.co) for v in m.vertices],"triangles":[list(t.vertices) for t in m.loop_triangles],"base_vertices":len(o.data.vertices) if o.type=="MESH" else 0,"control_points":sum(len(s.bezier_points) for s in o.data.splines) if o.type=="CURVE" else 0,"modifiers":[x.type for x in o.modifiers],"parent":o.parent.name if o.parent else None}
        finally:ev.to_mesh_clear()
    return out
def pose(label=None):
    for l,s in (("R",1),("L",-1)):bpy.data.objects["Hinge_"+l].rotation_euler.z=math.radians(s*85) if label==l else 0
    bpy.context.view_layer.update()
def point(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat("-Z","Y").to_euler()
def render(out):
    sc=bpy.context.scene;sc.render.engine="CYCLES";sc.cycles.device="CPU";sc.cycles.samples=32;sc.cycles.seed=19
    sc.render.resolution_x=640;sc.render.resolution_y=480;sc.render.resolution_percentage=100;sc.render.image_settings.file_format="PNG";sc.view_settings.view_transform="AgX"
    sc.world=bpy.data.worlds.new("Studio");sc.world.use_nodes=True;sc.world.node_tree.nodes["Background"].inputs[0].default_value=(.2,.2,.2,1);sc.world.node_tree.nodes["Background"].inputs[1].default_value=.6
    target=(0,.055,-.002)
    for name,loc,energy in (("Key",(.12,-.15,.22),12),("Fill",(-.18,.02,.13),8),("Rim",(.03,.20,.17),10)):
        d=bpy.data.lights.new(name,"AREA");d.energy=energy;d.shape="DISK";d.size=.18;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;point(o,target)
    d=bpy.data.cameras.new("Camera");d.type="ORTHO";d.ortho_scale=.22;c=bpy.data.objects.new("Camera",d);bpy.context.collection.objects.link(c);sc.camera=c
    for name,loc,label,t in (("front",(0,-.42,.025),None,(0,.02,0)),("three_quarter",(.22,-.30,.18),None,target),("folded_R",(.22,-.30,.18),"R",target)):
        pose(label);c.location=loc;point(c,t);sc.render.filepath=str((out/(name+".png")).resolve());bpy.ops.render.render(write_still=True)
    pose()
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args(sys.argv[sys.argv.index("--")+1:]);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    build();pose();before=snapshot();file=out/"INK_02_editable.blend";bpy.ops.wm.save_as_mainfile(filepath=str(file.resolve()));bpy.ops.wm.open_mainfile(filepath=str(file.resolve()))
    after=snapshot();raw={"open":after,"roundtrip_exact":before==after}
    for l in ("R","L"):pose(l);raw["fold_"+l]=snapshot()
    pose();(out/"raw.json").write_text(json.dumps(raw));render(out)
