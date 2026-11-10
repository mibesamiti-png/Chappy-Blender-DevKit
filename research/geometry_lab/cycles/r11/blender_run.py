"""R11: temporary Blender 4.4.3 Edit Mode BMesh attribute transfer audit.

Not a production add-on. Original two collar surfaces + their UV/material are
created synthetically, the detached R10 strip is inserted in Edit Mode, and
the complete source signature is checked for exact preservation.

Seamed UV islands are DELIBERATELY not auto-reconciled; this audit detects them.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import types
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import bpy
import bmesh
from cbdk_geometry.quality_router import conditional_flip_loft

saved=sys.modules.get("cycles")
pkg=types.ModuleType("cycles")
pkg.__path__=[str(ROOT/"cycles")]
sys.modules["cycles"]=pkg
try:
    from cycles.r11.fixtures import cases
finally:
    sys.modules.pop("cycles",None)
    if saved is not None:sys.modules["cycles"]=saved

ARMS=("r11_attribute_adapter","r11_zero_uv_control")


def snapshot():
    return (frozenset(x.as_pointer() for x in bpy.data.objects),
            frozenset(x.as_pointer() for x in bpy.data.meshes),
            frozenset(x.as_pointer() for x in bpy.data.materials),
            bpy.context.view_layer.objects.active.as_pointer()
            if bpy.context.view_layer.objects.active else None,
            frozenset(x.as_pointer() for x in bpy.context.selected_objects),
            bpy.context.mode)


def face_sig(face,layer,tag):
    return (int(face[tag]),int(face.material_index),
            tuple(tuple(float(x) for x in vert.co) for vert in face.verts),
            tuple(tuple(float(x) for x in loop[layer].uv) for loop in face.loops))


def uv_parameters(strip,na,nb):
    xyz=strip.vertices
    total=len(xyz)
    lower=xyz[:na]
    upper=xyz[total-nb:]
    ca=lower[:,:2].mean(axis=0)
    cb=upper[:,:2].mean(axis=0)
    zlo=float(lower[:,2].mean())
    zhi=float(upper[:,2].mean())
    if zhi-zlo<.1:raise ValueError("expected positive z envelope")
    uv={}
    for idx,vert in enumerate(xyz):
        if idx < na:
            center=ca
            v=0.0
        elif idx>=total-nb:
            center=cb
            v=1.0
        else:
            v=float(np.clip((vert[2]-zlo)/(zhi-zlo),0.,1.))
            center=(1-v)*ca+v*cb
        theta=float(np.arctan2(vert[1]-center[1],vert[0]-center[0]))
        u=float(np.mod(theta,2*np.pi)/(2*np.pi))
        uv[idx]=(u,v)
    return uv


def boundary_edges(strip):
    directed=defaultdict(list)
    for tri in strip.faces:
        for u,v in zip(tri,np.roll(tri,-1)):
            u,v=int(u),int(v)
            directed[tuple(sorted((u,v)))].append((u,v))
    return [edges[0] for edges in directed.values() if len(edges)==1]


def create_source(strip,na,nb,mode):
    total=len(strip.vertices)
    boundary=list(range(na))+list(range(total-nb,total))
    source_id={idx:i for i,idx in enumerate(boundary)}
    outer_id={idx:i+len(boundary) for i,idx in enumerate(boundary)}
    vertices=[tuple(float(v) for v in strip.vertices[i]) for i in boundary]
    for idx in boundary:
        v=np.array(strip.vertices[idx],dtype=float,copy=True)
        v[2]+=-.18 if idx<na else +.18
        vertices.append(tuple(float(x) for x in v))
    faces=[]
    material=[]
    seams=[]
    for u,v in boundary_edges(strip):
        if u not in source_id or v not in source_id:
            raise RuntimeError("strip has unexpected additional boundary")
        if (u<na)!=(v<na):
            raise RuntimeError("bridge boundary mixes lower and upper loops")
        faces.append((source_id[v],source_id[u],outer_id[u],outer_id[v]))
        material.append(0 if u<na else 1)
        seams.append((u,v))
    if len(faces)!=na+nb:
        raise RuntimeError("not exactly two strip boundary loops")
    return vertices,faces,material,source_id,outer_id,boundary,seams


def execute(case,arm):
    baseline=snapshot()
    start=time.perf_counter()
    obj=None
    me=None
    materials=[]
    try:
        a=case["a"].astype(np.float32).astype(float)
        b=case["b"].astype(np.float32).astype(float)
        na,nb=len(a),len(b)
        output=conditional_flip_loft(a,b)
        strip=output["mesh"]
        uv=uv_parameters(strip,na,nb)
        pts,collars,materials_by_face,original,outer,boundary,edges=create_source(
            strip,na,nb,case["uv_mode"])
        me=bpy.data.meshes.new("R11_TEMP_COLLARS")
        me.from_pydata(pts,[],collars)
        me.update()
        obj=bpy.data.objects.new("R11_TEMP_EDIT_MODE",me)
        bpy.context.collection.objects.link(obj)
        for name in ("R11_lower","R11_upper","R11_bridge"):
            mat=bpy.data.materials.new(name)
            materials.append(mat)
            me.materials.append(mat)
        uv_layer=me.uv_layers.new(name="R11_Test_UV")
        owner_by_base={}
        for idx,bid in original.items():owner_by_base[bid]=(idx,False)
        for idx,bid in outer.items():owner_by_base[bid]=(idx,True)
        for face_i,poly in enumerate(me.polygons):
            poly.material_index=materials_by_face[face_i]
            for loop_i in poly.loop_indices:
                vertex_id=me.loops[loop_i].vertex_index
                strip_id,is_outer=owner_by_base[vertex_id]
                u,v=uv[strip_id]
                if is_outer:v+=-.08 if strip_id<na else .08
                if case["uv_mode"]=="split" and face_i%2==0:u+=.25
                uv_layer.data[loop_i].uv=(u,v)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.mode_set(mode="EDIT")
        bm=bmesh.from_edit_mesh(me)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        uv_attr=bm.loops.layers.uv.verify()
        tag=bm.faces.layers.int.new("r11_source_face_id")
        for i,face in enumerate(bm.faces):
            face[tag]=i+1
        sig_before={int(face[tag]):face_sig(face,uv_attr,tag) for face in bm.faces}
        source_bm={s:bm.verts[d] for s,d in original.items()}
        all_bm=dict(source_bm)
        for k,point in enumerate(strip.vertices):
            if k not in all_bm:
                all_bm[k]=bm.verts.new(tuple(float(t) for t in point))
        bm.verts.index_update()
        added_faces=[]
        for tri in strip.faces:
            f=bm.faces.new(tuple(all_bm[int(i)] for i in tri))
            f[tag]=0
            f.material_index=2 if arm=="r11_attribute_adapter" else 0
            for loop in f.loops:
                # The BMesh vert is identical to one in all_bm.
                idx=next(i for i in tri if all_bm[int(i)]==loop.vert)
                target=uv[int(idx)] if arm=="r11_attribute_adapter" else (0.,0.)
                loop[uv_attr].uv=target
            added_faces.append(f)
        bm.normal_update()
        sig_after={int(face[tag]):face_sig(face,uv_attr,tag)
                   for face in bm.faces if int(face[tag])>0}
        source_unchanged=(sig_before==sig_after)
        src_face_count=len(sig_after)
        if len(added_faces)!=len(strip.faces):raise RuntimeError("missing bridge faces")

        bridge_uv=[]
        bridge_materials=[]
        by_original=defaultdict(list)
        for f in added_faces:
            bridge_materials.append(int(f.material_index))
            for loop in f.loops:
                uv_pair=tuple(float(v) for v in loop[uv_attr].uv)
                bridge_uv.append(uv_pair)
                for key,v in source_bm.items():
                    if loop.vert==v:
                        by_original[key].append(uv_pair)
                        break
        uv_gaps=[]
        for face in bm.faces:
            if int(face[tag])==0:continue
            for loop in face.loops:
                for key,v in source_bm.items():
                    if loop.vert==v:
                        uv_here=tuple(float(t) for t in loop[uv_attr].uv)
                        for value in by_original[key]:
                            uv_gaps.append(max(abs(x-y) for x,y in zip(uv_here,value)))
                        break
        max_uv_gap=max(uv_gaps) if uv_gaps else float("inf")
        bridge_uv_valid=(all(math.isfinite(v) and -1e-6 <= v <= 1+1e-6
                             for pair in bridge_uv for v in pair)
                         and any(max(abs(x),abs(y))>.0001 for x,y in bridge_uv))
        bridge_material_ok=all(i==2 for i in bridge_materials)
        angle_values=[]
        used_boundary=0
        for edge in bm.edges:
            if len(edge.link_faces)!=2:
                continue
            faces_edge=list(edge.link_faces)
            marks=[int(f[tag])>0 for f in faces_edge]
            if marks[0]!=marks[1]:
                used_boundary+=1
                normals=[np.array(f.normal,dtype=float) for f in faces_edge]
                cos=np.clip(float(np.dot(normals[0],normals[1])),-1.,1.)
                angle_values.append(float(math.degrees(math.acos(cos))))
        bad_edge_count=sum(len(edge.link_faces)>2 for edge in bm.edges)
        outer_boundaries=sum(len(edge.link_faces)==1 for edge in bm.edges)
        bmesh.update_edit_mesh(me,loop_triangles=True,destructive=True)
        bpy.ops.object.mode_set(mode="OBJECT")
        me.calc_loop_triangles()
        complete_triangles=[list(map(int,t.vertices)) for t in me.loop_triangles]
        complete_verts=[tuple(float(v) for v in vert.co) for vert in me.vertices]
        source_boundary_matches=all(
            np.max(np.abs(np.array(complete_verts[original[i]])-strip.vertices[i]))<1e-6
            for i in boundary)
        result=dict(
            case=case["name"],split=case["split"],uv_mode=case["uv_mode"],
            arm=arm,status="generated",r10_path=output["path"],
            original_source_face_count=src_face_count,
            original_source_signature_unchanged=bool(source_unchanged),
            source_boundary_unchanged=bool(source_boundary_matches),
            bridge_triangle_count=len(added_faces),
            expected_bridge_triangle_count=len(strip.faces),
            bridge_uv_finite_and_nonzero_bounded=bool(bridge_uv_valid),
            bridge_material_2=bool(bridge_material_ok),
            max_boundary_uv_gap=float(max_uv_gap),
            shared_source_to_bridge_edges=int(used_boundary),
            expected_shared_edges=int(na+nb),
            outer_boundary_edges=int(outer_boundaries),
            nonmanifold_edges=int(bad_edge_count),
            mean_normal_discontinuity_deg=float(np.mean(angle_values)),
            max_normal_discontinuity_deg=float(max(angle_values)),
            elapsed_seconds=float(time.perf_counter()-start),
            original_boundary_vertices=na+nb,
            strip_vertices=strip.vertices.tolist(),
            strip_faces=strip.faces.tolist(),
            complete_vertices=complete_verts,
            complete_triangles=complete_triangles,
        )
    finally:
        if bpy.context.mode!="OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        if obj is not None and obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj,do_unlink=True)
        if me is not None and me.name in bpy.data.meshes:
            bpy.data.meshes.remove(me)
        for mat in materials:
            if mat.name in bpy.data.materials:
                bpy.data.materials.remove(mat)
        for selected in bpy.context.selected_objects:
            selected.select_set(False)
        # Original selection / active object was not mutated or removed.
        # The verification run uses factory-startup Blender and snapshots its scene.
        if baseline[4]:
            for item in bpy.data.objects:
                if item.as_pointer() in baseline[4]:item.select_set(True)
        if baseline[3] is not None:
            for item in bpy.data.objects:
                if item.as_pointer()==baseline[3]:
                    bpy.context.view_layer.objects.active=item
                    break
        after=snapshot()
        if after!=baseline:
            raise RuntimeError("R11 scene cleanup or selection restoration failed")
    result["scene_restored"]=True
    return result


def run():
    records=[]
    for case in cases():
        for arm in ARMS:
            try:
                entry=execute(case,arm)
            except Exception as error:
                entry=dict(case=case["name"],split=case["split"],
                           uv_mode=case["uv_mode"],arm=arm,status="generation_error",
                           reason=type(error).__name__+": "+str(error))
            records.append(entry)
            print("R11_BLENDER",json.dumps({k:v for k,v in entry.items()
                if k in ("case","split","uv_mode","arm","status",
                         "reason","max_boundary_uv_gap","bridge_material_2",
                         "original_source_signature_unchanged")}),flush=True)
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
        "cycles/r11/fixtures.py","cycles/r11/blender_run.py",
        "cbdk_geometry/quality_router.py")}
    return dict(cycle="R11",synthetic_only=True,blender=bpy.app.version_string,
                source_sha256=hashes,arms=list(ARMS),cases=records,approved=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    data=run()
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x") as f:json.dump(data,f,indent=2)
    print("R11_RAW",len(data["cases"]),data["blender"],flush=True)
