"""R10A: native Blender readback of accepted R9F surfaces and optional Solidify.
Run in Blender background with --python-exit-code 1. No addons or user files.
"""
import json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from intersection import triangle_hit

SOURCE=Path("results/cap_fairing")
DEST=Path("results/native_blender")
NAMES=("standard","front_wrap","rear_wrap","both_wrap")
THICKNESS=.012

def read_obj(path):
    p=[];q=[]
    for line in path.read_text().splitlines():
        a=line.split()
        if not a:continue
        if a[0]=="v":p.append(tuple(map(float,a[1:])))
        elif a[0]=="f":q.append(tuple(int(x.split("/")[0])-1 for x in a[1:]))
    if not p or not q or any(len(f)!=4 or min(f)<0 or max(f)>=len(p) for f in q):raise ValueError("invalid exported quad OBJ")
    return p,q

def native_audit(mesh):
    bm=bmesh.new();bm.from_mesh(mesh)
    try:
        boundary=sum(e.is_boundary for e in bm.edges)
        other=sum(not e.is_boundary and not e.is_manifold for e in bm.edges)
        orientation=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
        return dict(vertices=len(bm.verts),edges=len(bm.edges),faces=len(bm.faces),
            quads=sum(len(f.verts)==4 for f in bm.faces),boundary_edges=boundary,
            nonmanifold_nonboundary=other,orientation_errors=orientation,
            min_face_area=min(f.calc_area() for f in bm.faces),
            euler=len(bm.verts)-len(bm.edges)+len(bm.faces))
    finally:bm.free()

def native_contacts(mesh):
    mesh.calc_loop_triangles()
    p=[tuple(v.co) for v in mesh.vertices]
    t=[tuple(f.vertices) for f in mesh.loop_triangles]
    tree=BVHTree.FromPolygons(p,t,all_triangles=True,epsilon=1e-9)
    pairs=tree.overlap(tree)
    if len(pairs)>2000000:raise ValueError("native BVH overlap budget")
    pairs={tuple(sorted((a,b))) for a,b in pairs if a!=b}
    tested=hits=excluded=0
    for a,b in sorted(pairs):
        if set(t[a])&set(t[b]):
            excluded+=1;continue
        tested+=1
        if triangle_hit([p[i] for i in t[a]],[p[i] for i in t[b]]):hits+=1
    return dict(triangles=len(t),native_bvh_pairs=len(pairs),incident_pairs_excluded=excluded,
                nonincident_pairs_tested=tested,contacts=hits,incident_overlap_verified=False)

def run_case(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    p,q=read_obj(SOURCE/(name+".obj"))
    mesh=bpy.data.meshes.new(name+"_surface")
    mesh.from_pydata(p,[],q);mesh.update()
    corrected=mesh.validate(verbose=False)
    obj=bpy.data.objects.new(name+"_surface",mesh)
    bpy.context.collection.objects.link(obj)
    for face in mesh.polygons:face.use_smooth=True
    s=native_audit(mesh)
    readback=max(math.dist(a,tuple(b.co)) for a,b in zip(p,mesh.vertices))
    contacts=native_contacts(mesh)
    surface_gate=(not corrected and s["vertices"]==len(p) and s["faces"]==len(q)
        and s["quads"]==len(q) and s["euler"]==-1 and s["boundary_edges"]>0
        and s["nonmanifold_nonboundary"]==s["orientation_errors"]==0
        and s["min_face_area"]>0 and readback<1e-6 and contacts["contacts"]==0)
    mod=obj.modifiers.new("Optional thickness","SOLIDIFY")
    mod.thickness=THICKNESS;mod.offset=-1.;mod.use_rim=True
    bpy.context.view_layer.update()
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    solid=bpy.data.meshes.new_from_object(evaluated)
    shell_corrected=solid.validate(verbose=False)
    shell=native_audit(solid)
    shell_contacts=native_contacts(solid)
    shell_gate=(not shell_corrected and shell["vertices"]==2*s["vertices"]
        and shell["faces"]==2*s["faces"]+s["boundary_edges"] and shell["euler"]==-2
        and shell["boundary_edges"]==shell["nonmanifold_nonboundary"]==shell["orientation_errors"]==0
        and shell["min_face_area"]>0 and shell_contacts["contacts"]==0)
    # Preserve editable surface and optional, initially disabled modifier.
    bpy.data.meshes.remove(solid)
    mod.show_viewport=False;mod.show_render=False
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    path=DEST/(name+".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(path.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))
    reopened=bpy.data.objects.get(name+"_surface")
    reopen_gate=(reopened is not None and len(reopened.data.vertices)==len(p)
        and len(reopened.data.polygons)==len(q) and len(reopened.modifiers)==1
        and not reopened.modifiers[0].show_viewport)
    return dict(name=name,source_vertices=len(p),source_faces=len(q),readback_max_error=readback,
        surface=s,surface_validate_changed=corrected,surface_contacts=contacts,surface_gate=surface_gate,
        shell=shell,shell_validate_changed=shell_corrected,shell_contacts=shell_contacts,shell_gate=shell_gate,
        reopen_gate=reopen_gate,passed=surface_gate and shell_gate and reopen_gate)

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    source=json.loads((SOURCE/"report.json").read_text())
    if not source["fixture_gate"] or {c["name"] for c in source["cases"] if c["passed"]}!=set(NAMES):
        raise ValueError("R9F input gate not satisfied")
    results=[run_case(name) for name in NAMES]
    report=dict(complete=True,blender_version=bpy.app.version_string,thickness=THICKNESS,
        cases=results,surface_gate=all(c["surface_gate"] for c in results),
        shell_gate=all(c["shell_gate"] for c in results),fixture_gate=all(c["passed"] for c in results),
        global_intersection_verified=False,lower_body_fit_verified=False)
    (DEST/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print("PHASE213NATIVE_SUMMARY",json.dumps(report,allow_nan=False))
if __name__=="__main__":main()
