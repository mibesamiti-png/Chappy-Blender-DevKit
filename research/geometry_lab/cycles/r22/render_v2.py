"""R22 actual Blender Cycles renders; no geometry optimization."""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

MODES=("checker","flat","smooth")
VIEWS=(0,180)
SIZE=384

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text())
def material(mode):
    m=bpy.data.materials.new("Diagnostic_"+mode); m.use_nodes=True
    n=m.node_tree.nodes; n.clear(); l=m.node_tree.links
    output=n.new("ShaderNodeOutputMaterial")
    if mode=="checker":
        uv=n.new("ShaderNodeTexCoord"); check=n.new("ShaderNodeTexChecker")
        check.inputs["Scale"].default_value=16
        check.inputs["Color1"].default_value=(.035,.065,.095,1)
        check.inputs["Color2"].default_value=(.85,.84,.70,1)
        l.new(uv.outputs["UV"],check.inputs["Vector"])
        em=n.new("ShaderNodeEmission"); l.new(check.outputs["Color"],em.inputs["Color"])
        l.new(em.outputs[0],output.inputs["Surface"])
    else:
        bs=n.new("ShaderNodeBsdfPrincipled")
        bs.inputs["Base Color"].default_value=(.43,.48,.54,1)
        bs.inputs["Roughness"].default_value=.38
        l.new(bs.outputs[0],output.inputs["Surface"])
    return m

def build(row,mode):
    v=np.asarray(row["vertices"],np.float32); f=np.asarray(row["triangles"],int)
    uv=np.asarray(row["corner_uv"],np.float32)
    mesh=bpy.data.meshes.new("EvidenceMesh"); mesh.from_pydata(v.tolist(),[],f.tolist()); mesh.update()
    obj=bpy.data.objects.new("Evidence",mesh); bpy.context.collection.objects.link(obj)
    layer=mesh.uv_layers.new(name="UVMap")
    mesh.materials.append(material(mode))
    ids=mesh.attributes.new(name="source_face_id",type="INT",domain="FACE")
    mats=mesh.attributes.new(name="original_material_id",type="INT",domain="FACE")
    flags={tuple(sorted(e)) for e in row["seam_flags"]}
    for i,p in enumerate(mesh.polygons):
        if tuple(p.vertices)!=tuple(f[i]): raise ValueError("triangle mismatch")
        p.use_smooth=mode=="smooth"
        ids.data[i].value=row["face_ids"][i]; mats.data[i].value=row["materials"][i]
        for j,k in enumerate(p.loop_indices): layer.data[k].uv=uv[i,j]
    for e in mesh.edges: e.use_seam=tuple(sorted(e.vertices)) in flags
    if not np.array_equal(np.array([list(x.co) for x in mesh.vertices],np.float32),v): raise ValueError("XYZ mismatch")
    actual=np.array([[list(layer.data[k].uv) for k in p.loop_indices] for p in mesh.polygons],np.float32)
    if not np.array_equal(actual,uv): raise ValueError("UV mismatch")
    if {tuple(sorted(e.vertices)) for e in mesh.edges if e.use_seam}!=flags: raise ValueError("seam mismatch")
    return obj

def point(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
def setup(center,radius,az):
    scene=bpy.context.scene
    scene.render.engine="CYCLES"; scene.cycles.device="CPU"; scene.cycles.samples=32; scene.cycles.use_denoising=False; scene.cycles.seed=27
    scene.render.threads_mode="FIXED"; scene.render.threads=2
    scene.render.resolution_x=scene.render.resolution_y=SIZE; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"; scene.render.image_settings.color_mode="RGB"; scene.render.image_settings.color_depth="8"
    scene.view_settings.view_transform="Standard"
    scene.render.film_transparent=False
    scene.world=bpy.data.worlds.new("World"); scene.world.use_nodes=True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.08,.08,.08,1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value=.5
    a=math.radians(az); d=Vector((math.cos(a),math.sin(a),.22)).normalized()
    center=Vector(center); camera=bpy.data.objects.new("Camera",bpy.data.cameras.new("Camera")); bpy.context.collection.objects.link(camera)
    camera.location=center+d*radius*5; point(camera,center); camera.data.type="ORTHO"; camera.data.ortho_scale=radius*2.35; scene.camera=camera
    right=Vector((-math.sin(a),math.cos(a),0))
    for name,offset,power,size in (("Key",d*3+right*2+Vector((0,0,3)),800,2),("Fill",d*2-right*3+Vector((0,0,1)),350,3),("Rim",-d*2+Vector((0,0,3)),500,2)):
        data=bpy.data.lights.new(name,"AREA"); data.energy=.125*power*radius**2; data.shape="DISK"; data.size=size*radius
        obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj); obj.location=center+offset*radius; point(obj,center)

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--input-dir",required=True); p.add_argument("--output-dir",required=True); a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    src=Path(a.input_dir); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    ev=load(src/"eval.json"); base=load(src/"baseline-raw.json"); final=load(src/"selected-raw.json")
    if not ev["gate"] or ev["approved"] or len(ev["rows"])!=8 or not all(r["passed"] and r["all_triangles_exact"] and r["source_exact"] for r in ev["rows"]): raise ValueError("R21 gate missing")
    if any(r["blender"]!="4.4.3" or r["approved"] for r in (base,final)): raise ValueError("provenance")
    b={r["case"]:r for r in base["rows"]}; f={r["case"]:r for r in final["rows"]}; rows=[]
    if set(b)!=set(f) or set(b)!={r["case"] for r in ev["rows"]}: raise ValueError("case mismatch")
    for r in ev["rows"]:
        case=r["case"]; both=np.vstack((b[case]["vertices"],f[case]["vertices"])); center=(both.min(axis=0)+both.max(axis=0))/2
        radius=float(np.linalg.norm(both-center,axis=1).max())
        for mode in MODES:
            for az in VIEWS:
                for arm,source in (("baseline",b[case]),("selected",f[case])):
                    bpy.ops.wm.read_factory_settings(use_empty=True)
                    build(source,mode); setup(center,radius,az)
                    dest=out/f"{case}_{mode}_{az}_{arm}.png"
                    bpy.context.scene.render.filepath=str(dest.resolve()); bpy.ops.render.render(write_still=True)
                    if not dest.is_file(): raise ValueError("missing render")
                    rows.append(dict(case=case,mode=mode,azimuth=az,arm=arm,file=dest.name,sha256=sha(dest)))
                    if mode=="smooth" and az==0 and arm=="selected" and case in ("r21_sparse","r21_round"):
                        bpy.ops.wm.save_as_mainfile(filepath=str((out/f"{case}_selected.blend").resolve()))
                    print("R22_RENDER",case,mode,az,arm,flush=True)
    manifest=dict(cycle="R22",render_revision=2,approved=False,blender=bpy.app.version_string,renderer="Cycles CPU",size=SIZE,source_hashes={n:sha(src/n) for n in ("eval.json","baseline-raw.json","selected-raw.json")},cases=[dict(case=r["case"],method=r["method"],p95_gain=r["p95_gain"]) for r in ev["rows"]],renders=rows,blend_files=[dict(file=p.name,sha256=sha(p)) for p in sorted(out.glob("*.blend"))])
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2))
