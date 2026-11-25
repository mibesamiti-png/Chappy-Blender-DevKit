"""Simple visual eyewear variant. Owner direction 2026-11-25: prioritize low
vertex count, recognizable appearance, editable structure; exact mechanical
reconstruction is a separate custom task. Applied02B stays frozen.

Applied03 closed as diagnostic evidence, not adopted: CI job 138941587435
reproduced 48 baseline, 16 rear6, 6 vertical3, 4 vertical4/5, 5 tilt4.
No zero-contact result in tested candidates. Keep conventional symmetric
pivots and decorative hinge; no claim of folding clearance, physical fit,
watertight printable assembly, optics or production approval.

One candidate, before measurement: 24 samples per rim/lens contour (32 prior),
one bevel segment per mesh, curve resolution 6 and bevel resolution 2.
Keep physical envelope, lens material, 85 mm straight regions, native
modifiers, 28-vertex temples and symmetric pivot placements.
Target <= 292 editable controls and <= 4524 evaluated triangles (>=20%
reduction from 5656). Existing native/CGAL per-object gate remains.
Visual inspection required, not a numeric proof of appearance.
"""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from applied02 import blender_run as old
from applied02 import region_run as region

N = 24

def replace_mesh(o, vertices, faces):
    prior = o.data
    data = bpy.data.meshes.new(o.name + "_simple")
    data.from_pydata(vertices, [], faces)
    data.update()
    for mat in prior.materials:
        data.materials.append(mat)
    for p in data.polygons:
        p.use_smooth = True
    o.data = data
    if prior.users == 0:
        bpy.data.meshes.remove(prior)

def build():
    region.build()
    n = N
    rim = bpy.data.objects["Rim_master"]
    verts = [old.contour(2*math.pi*i/n, rx, rz)
             for rx,rz in ((.0265,.0175),(.030,.021)) for i in range(n)]
    faces = [(i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n)]
    replace_mesh(rim, verts, faces)
    lens = bpy.data.objects["Lens_master"]
    verts = [old.contour(2*math.pi*i/n,.02665,.01765) for i in range(n)]
    verts.append((.0345,.003*(.0345/.07)**2,0))
    replace_mesh(lens,verts,[(n,(i+1)%n,i) for i in range(n)])
    for o in bpy.context.scene.objects:
        if o.type == "CURVE":
            o.data.resolution_u = 6
            o.data.bevel_resolution = 2
        for mod in o.modifiers:
            if mod.type == "BEVEL":
                mod.segments = 1
    bpy.context.scene["eyewear_scope"] = "visual proxy only; decorative hinges; no mechanical/print certification"

def run(out):
    out.mkdir(parents=True, exist_ok=True)
    build()
    old.pose()
    before = old.snapshot()
    ib = region.info()
    f = out / "INK_simple_editable.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(f.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(f.resolve()))
    after = old.snapshot()
    ia = region.info()
    raw = dict(open=after, roundtrip_exact=before==after and ib==ia, temple_base=ia)
    for label in ("R","L"):
        old.pose(label)
        raw["fold_"+label] = old.snapshot()
    old.pose()
    (out/"raw.json").write_text(json.dumps(raw))
    old.render(out)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args(sys.argv[sys.argv.index("--")+1:])
    run(a.output)
