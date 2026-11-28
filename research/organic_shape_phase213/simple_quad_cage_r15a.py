"""R15A: local leg-opening control columns on the R14B cage."""
import bpy
import math
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from visibility_diagnostic import raster,png

from simple_quad_cage_r14b import cage as baseline_cage

def cage():
    # Preserve every original control point. Split only the two outer
    # columns of each front/rear panel; leave the crotch strip untouched.
    p,q0=baseline_cage()
    p=list(p)
    front=[[0,1,2,3,4],[5,6,7,8,9],[10,11,12,13,14]]
    rear=[[0,15,16,17,4],[5,18,19,20,9],[10,21,22,23,14]]
    faces=[]
    # New outer-column points: waist, middle, leg opening.
    # Positive absolute depth; symmetric left/right.
    profiles=(
        ((.61,.18,.495),(.72,.23,.30),(.565,.18,.14)),
        ((.61,.20,.515),(.72,.29,.28),(.60,.25,.035)),
    )
    for panel,sign,profile in zip((front,rear),(-1,1),profiles):
        rows=[]
        for row,(x,y,z) in zip(panel,profile):
            left=len(p);p.append((-x,sign*y,z))
            right=len(p);p.append((x,sign*y,z))
            rows.append([row[0],left,row[1],row[2],row[3],right,row[4]])
        for j in range(2):
            for i in range(6):
                f=(rows[j][i],rows[j+1][i],rows[j+1][i+1],rows[j][i+1])
                faces.append(f if sign==-1 else f[::-1])
    faces.extend(q0[-4:])
    return p,faces

def main():
    dest=Path("results/simple_cage_r15a").resolve();dest.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    p,q=cage()
    old_p,old_q=baseline_cage()
    if len(p)!=39 or len(q)!=28 or p[:27]!=old_p or q[-4:]!=old_q[-4:]:
        raise RuntimeError("unexpected local cage edit")
    from collections import Counter
    edges=Counter(tuple(sorted((a,b))) for f in q for a,b in zip(f,f[1:]+f[:1]))
    if max(edges.values())>2 or len(p)-len(edges)+len(q)!=-1:
        raise RuntimeError("invalid open cage topology")
    mesh=bpy.data.meshes.new("39-point editable cage")
    mesh.from_pydata(p,[],q)
    if mesh.validate(verbose=False):raise RuntimeError("invalid source cage")
    mesh.update()
    obj=bpy.data.objects.new("Simple garment - edit cage",mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    for poly in mesh.polygons:poly.use_smooth=True
    mat=bpy.data.materials.new("Neutral blue fabric")
    mat.diffuse_color=(.23,.43,.65,1.)
    mesh.materials.append(mat)
    sub=obj.modifiers.new("Smooth form","SUBSURF");sub.levels=3;sub.render_levels=3
    solid=obj.modifiers.new("Optional fabric thickness","SOLIDIFY");solid.thickness=.018
    solid.offset=-1.
    # Preserve the simplest editable cage and an optional thin shell.
    solid.show_viewport=False;solid.show_render=False
    from mathutils import Quaternion
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=="VIEW_3D":
                area.spaces.active.region_3d.view_distance=3.8
                area.spaces.active.region_3d.view_rotation=Quaternion((1,0,0),math.pi/2)
                area.spaces.active.region_3d.view_perspective="ORTHO"
    file=dest/"simple_garment_r15a.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(file))
    bpy.ops.wm.open_mainfile(filepath=str(file))
    obj=bpy.data.objects["Simple garment - edit cage"]
    deps=bpy.context.evaluated_depsgraph_get()
    evaluated=obj.evaluated_get(deps);m=evaluated.to_mesh();m.calc_loop_triangles()
    v=[tuple(x.co) for x in m.vertices];t=[tuple(x.vertices) for x in m.loop_triangles]
    counts=dict(cage_vertices=len(obj.data.vertices),cage_quads=len(obj.data.polygons),
        evaluated_vertices=len(v),evaluated_triangles=len(t))
    evaluated.to_mesh_clear()
    for label,angle in (("front",math.pi),("quarter",math.pi*.75),("side",math.pi/2),("back",0.)):
        side,light=raster(v,t,angle,width=430,height=340,scale=150)
        if not any(side):raise RuntimeError("empty preview")
        png(dest/(label+".png"),side,light,False,width=430,height=340)
    report=dict(complete=True,stage="R15A",original_control_points_preserved=True,crotch_faces_preserved=True,blender_version=bpy.app.version_string,**counts,
        save_reopen=True,subdivision=3,solidify_optional=True,
        visual_review_required=True,anatomical_fit_verified=False,collision_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2))
    print("PHASE213SIMPLECAGE_R15A_SUMMARY",json.dumps(report))
if __name__=="__main__":main()
