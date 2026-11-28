"""Blender native objects, non-applied thickness, actual saved mesh readback."""
import bpy,sys,json,argparse,math
from pathlib import Path
from mathutils import Vector

def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=m.node_tree.nodes.get("Principled BSDF");n.inputs["Base Color"].default_value=(*color,1);n.inputs["Roughness"].default_value=.68
    return m
def build(parts):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cloth=material("Woven teal",(.055,.24,.26));trim=material("Elastic",(.025,.09,.11));fastener=material("Closure fabric",(.28,.23,.12))
    for p in parts:
        mesh=bpy.data.meshes.new(p["name"]);mesh.from_pydata(p["vertices"],[],p["faces"]);mesh.update()
        ob=bpy.data.objects.new(p["name"],mesh);bpy.context.collection.objects.link(ob)
        layer=mesh.uv_layers.new(name="PanelUV")
        for f in mesh.polygons:
            f.use_smooth=True
            for k in f.loop_indices:layer.data[k].uv=p["uv"][mesh.loops[k].vertex_index]
        mesh.materials.append(fastener if p["name"]=="closure" else trim if p["name"].startswith("strap") or p["name"]=="band" else cloth)
        mod=ob.modifiers.new("Editable fabric thickness","SOLIDIFY");mod.thickness=.0012;mod.offset=0
        ob["generator"]="synthetic_panel_pilot";ob["part"]=p["name"]
def read():
    rows={}
    for ob in bpy.context.scene.objects:
        if ob.type!="MESH":continue
        m=ob.data;m.calc_loop_triangles();u=m.uv_layers["PanelUV"]
        ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh()
        try:
            em.calc_loop_triangles()
            rows[ob.name]=dict(vertices=[list(v.co) for v in m.vertices],quads=[list(p.vertices) for p in m.polygons],triangles=[list(t.vertices) for t in m.loop_triangles],corner_uv=[[list(u.data[k].uv) for k in t.loops] for t in m.loop_triangles],thickness=ob.modifiers[0].thickness,evaluated_vertices=[list(v.co) for v in em.vertices],evaluated_triangles=[list(t.vertices) for t in em.loop_triangles])
        finally:ev.to_mesh_clear()
    return rows
def point(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()
def render(out):
    scene=bpy.context.scene;scene.render.engine="CYCLES";scene.cycles.device="CPU";scene.cycles.samples=32;scene.cycles.seed=27
    scene.render.resolution_x=scene.render.resolution_y=512;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG";scene.view_settings.view_transform="AgX";scene.world=bpy.data.worlds.new("Studio");scene.world.use_nodes=True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.13,.13,.13,1);scene.world.node_tree.nodes["Background"].inputs[1].default_value=.5
    target=(0,0,.22)
    for name,loc,energy in (("Key",(.45,-.5,.65),35),("Fill",(-.5,-.2,.35),15),("Rim",(.1,.5,.6),20)):
        d=bpy.data.lights.new(name,"AREA");d.energy=energy;d.shape="DISK";d.size=.55;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;point(o,target)
    d=bpy.data.cameras.new("Camera");d.type="ORTHO";d.ortho_scale=.53;c=bpy.data.objects.new("Camera",d);bpy.context.collection.objects.link(c);scene.camera=c
    for name,loc in (("front",(0,-1,.24)),("back",(0,1,.24)),("side",(1,0,.24)),("three_quarter",(.7,-.9,.38))):
        c.location=loc;point(c,target);scene.render.filepath=str((out/(name+".png")).resolve());bpy.ops.render.render(write_still=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--output",required=True);a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True);spec=json.loads(Path(a.input).read_text());raw={}
    for arm,parts in spec.items():
        build(parts);before=read();f=out/(arm+".blend");bpy.ops.wm.save_as_mainfile(filepath=str(f.resolve()))
        bpy.ops.wm.open_mainfile(filepath=str(f.resolve()));after=read()
        if before!=after:raise ValueError("native roundtrip differs")
        raw[arm]=after
        if arm=="baseline":render(out)
    (out/"raw.json").write_text(json.dumps(raw))
