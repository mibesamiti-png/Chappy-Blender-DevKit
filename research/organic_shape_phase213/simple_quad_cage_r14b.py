"""R14B: same 27-point cage with a shorter side and raised leg openings."""
import bpy
import math
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from visibility_diagnostic import raster,png

# Three rows, five points each. Front and rear share side endpoints.
# Each row: x positions, absolute depth, heights.
FRONT=[
    ((-.77,-.45,0,.45,.77),(0,.35,.43,.35,0),(.49,.50,.51,.50,.49)),
    ((-.95,-.50,0,.50,.95),(0,.38,.42,.38,0),(.36,.22,.17,.22,.36)),
    ((-.92,-.21,0,.21,.92),(0,.30,.38,.30,0),(.25,-.19,-.33,-.19,.25)),
]
BACK=[
    ((-.77,-.45,0,.45,.77),(0,.38,.48,.38,0),(.49,.54,.56,.54,.49)),
    ((-.95,-.50,0,.50,.95),(0,.50,.59,.50,0),(.36,.19,.13,.19,.36)),
    ((-.92,-.28,0,.28,.92),(0,.43,.51,.43,0),(.25,-.29,-.37,-.29,.25)),
]

def cage():
    p=[];q=[];panels=[]
    for sign,data in ((-1,FRONT),(1,BACK)):
        rows=[]
        for j,(xx,yy,zz) in enumerate(data):
            row=[]
            for i,(x,y,z) in enumerate(zip(xx,yy,zz)):
                if sign==1 and i in (0,4):
                    idx=panels[0][j][i]
                    if p[idx]!=(x,sign*y,z):raise ValueError("side mismatch")
                else:
                    idx=len(p);p.append((x,sign*y,z))
                row.append(idx)
            rows.append(row)
        panels.append(rows)
        for j in range(2):
            for i in range(4):
                face=(rows[j][i],rows[j+1][i],rows[j+1][i+1],rows[j][i+1])
                q.append(face if sign==-1 else face[::-1])
    mid=[]
    for x,z in ((-.15,-.43),(0.,-.46),(.15,-.43)):
        mid.append(len(p));p.append((x,.025,z))
    rows=[panels[0][-1][1:4],mid,panels[1][-1][1:4]]
    for j in range(2):
        for i in range(2):
            q.append((rows[j][i],rows[j+1][i],rows[j+1][i+1],rows[j][i+1]))
    return p,q

def main():
    dest=Path("results/simple_cage_r14b").resolve();dest.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    p,q=cage()
    from simple_quad_cage import cage as baseline_cage
    old_p,old_q=baseline_cage()
    if len(p)!=27 or len(q)!=20 or q!=old_q:
        raise RuntimeError("cage topology changed")
    mesh=bpy.data.meshes.new("27-point editable cage")
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
    file=dest/"simple_garment_r14b.blend"
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
    report=dict(complete=True,stage="R14B",same_topology_as_r14a=True,blender_version=bpy.app.version_string,**counts,
        save_reopen=True,subdivision=3,solidify_optional=True,
        visual_review_required=True,anatomical_fit_verified=False,collision_verified=False)
    (dest/"report.json").write_text(json.dumps(report,indent=2))
    print("PHASE213SIMPLECAGE_R14B_SUMMARY",json.dumps(report))
if __name__=="__main__":main()
