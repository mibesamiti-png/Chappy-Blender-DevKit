"""Native Blender visual model; source geometry shared with standalone spec."""
import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from applied04.geometry import parts,COLORS
from applied02.blender_run import snapshot,mat

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene
    sc.unit_settings.system="METRIC"
    mats={k:mat(k,tuple(c/255 for c in rgba[:3]),metal=.65 if k=="metal" else .1,rough=.24 if k in ("lens","metal") else .48) for k,rgba in COLORS.items()}
    for name,(v,f,labels) in parts().items():
        mesh=bpy.data.meshes.new(name);mesh.from_pydata([tuple(c/1000 for c in p) for p in v],[],f);mesh.update()
        o=bpy.data.objects.new(name,mesh);sc.collection.objects.link(o)
        keys=list(dict.fromkeys(labels))
        for k in keys:mesh.materials.append(mats[k])
        for p,k in zip(mesh.polygons,labels):
            p.material_index=keys.index(k);p.use_smooth=name!="Switch" and len(p.vertices)==4
        o["visual_only"]=True
    sc["scope"]="Synthetic visual flashlight, no functional internals or print certification"
def aim(o,p=(0,0,0)):
    o.rotation_euler=(Vector(p)-o.location).to_track_quat("-Z","Y").to_euler()
def run(out):
    out.mkdir(parents=True,exist_ok=True)
    build();before=snapshot();f=out/"flashlight.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(f.resolve()));bpy.ops.wm.open_mainfile(filepath=str(f.resolve()))
    after=snapshot();(out/"raw.json").write_text(json.dumps(dict(open=after,roundtrip_exact=before==after)))
    sc=bpy.context.scene;sc.render.engine="CYCLES";sc.cycles.device="CPU";sc.cycles.samples=24
    sc.render.resolution_x=640;sc.render.resolution_y=640;sc.render.resolution_percentage=100
    sc.world=bpy.data.worlds.new("Studio");sc.world.use_nodes=True;sc.world.node_tree.nodes["Background"].inputs[0].default_value=(.2,.2,.2,1);sc.world.node_tree.nodes["Background"].inputs[1].default_value=.65
    for name,loc,power in (("Key",(.16,-.14,.19),18),("Fill",(-.15,-.06,.06),10),("Rim",(.02,.12,.18),14)):
        d=bpy.data.lights.new(name,"AREA");d.energy=power;d.shape="DISK";d.size=.16;o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=loc;aim(o)
    d=bpy.data.cameras.new("Camera");d.type="ORTHO";d.ortho_scale=.15;c=bpy.data.objects.new("Camera",d);sc.collection.objects.link(c);sc.camera=c
    for name,loc in (("three_quarter",(.18,-.22,.12)),("head",(.13,-.14,.35))):
        c.location=loc;aim(c);sc.render.filepath=str((out/(name+".png")).resolve());bpy.ops.render.render(write_still=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args(sys.argv[sys.argv.index("--")+1:]);run(a.output)
