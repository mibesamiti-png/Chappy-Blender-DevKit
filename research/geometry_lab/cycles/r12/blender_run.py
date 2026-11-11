"""R12: frozen Blender Edit Mode UV chart transfer and R11 baseline comparator.

The candidate reads *actual* original face-corner UV values, not the fixture
chart labels. Original faces and their UV/material remain unchanged. Deliberate
internal seams are exposed and counted, not silently called a seamless unwrap.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import types
import numpy as np
import bpy
import bmesh

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from cbdk_geometry.quality_router import conditional_flip_loft
from cbdk_geometry.uv_charts import label_chart_offsets

saved=sys.modules.get("cycles")
research=types.ModuleType("cycles")
research.__path__=[str(ROOT/"cycles")]
sys.modules["cycles"]=research
try:
    from cycles.r11.blender_run import snapshot,face_sig,uv_parameters,create_source
    from cycles.r12.fixtures import cases
finally:
    sys.modules.pop("cycles",None)
    if saved is not None:sys.modules["cycles"]=saved

ARMS=("r12_chart_transfer","r11_baseline_uv")


def _source_chart_offset(mode,face_index,nfaces):
    # ONLY the synthetic source UV fixture generator uses these labels.
    # Candidate code below sees ONLY real BMesh loop UV readings.
    if mode=="continuous":
        return 0.
    if mode=="split":
        return .25 if face_index%2==0 else 0.
    if mode=="blocks":
        return .20 if (face_index//4)%2==0 else 0.
    if mode=="multi":
        return (0.,.125,-.125,.25)[face_index%4]
    raise ValueError("unknown source fixture chart mode")


def _face_uv(face,vertex,layer):
    selected=[tuple(float(v) for v in loop[layer].uv)
              for loop in face.loops if loop.vert==vertex]
    if len(selected)!=1:
        raise ValueError("source or new face must have one corner at this vertex")
    return np.array(selected[0],dtype=float)


def _boundary_face_indices(faces):
    lookup=defaultdict(list)
    for i,tri in enumerate(faces):
        for a,b in zip(tri,np.roll(tri,-1)):
            lookup[tuple(sorted((int(a),int(b))))].append(i)
    return {e:indices[0] for e,indices in lookup.items() if len(indices)==1}


def _triangle_signed_uv_area(corners):
    p=np.asarray(corners,dtype=float)
    return float(.5*np.linalg.det(np.array([p[1]-p[0],p[2]-p[0]])))


def execute(case,arm):
    beginning=snapshot()
    started=time.perf_counter()
    obj=None
    me=None
    materials=[]
    result=None
    try:
        a=case["a"].astype(np.float32).astype(float)
        b=case["b"].astype(np.float32).astype(float)
        na,nb=len(a),len(b)
        output=conditional_flip_loft(a,b)
        strip=output["mesh"]
        base_uv=uv_parameters(strip,na,nb)
        pts,collars,mats,source_id,outer_id,boundary,ordered_edges=create_source(
            strip,na,nb,case["uv_mode"])
        me=bpy.data.meshes.new("R12_TEMP_COLLARS")
        me.from_pydata(pts,[],collars)
        me.update()
        obj=bpy.data.objects.new("R12_TEMP_EDIT_MODE",me)
        bpy.context.collection.objects.link(obj)
        for name in ("R12_lower","R12_upper","R12_bridge"):
            mat=bpy.data.materials.new(name)
            materials.append(mat)
            me.materials.append(mat)
        layer=me.uv_layers.new(name="R12_Test_UV")
        source_owner={idx:(key,False) for key,idx in source_id.items()}
        source_owner.update({idx:(key,True) for key,idx in outer_id.items()})
        for face_i,poly in enumerate(me.polygons):
            poly.material_index=mats[face_i]
            offset=_source_chart_offset(case["uv_mode"],face_i,len(me.polygons))
            for loop_i in poly.loop_indices:
                key,outer=source_owner[me.loops[loop_i].vertex_index]
                u,v=base_uv[key]
                if outer:v+=-.08 if key<na else .08
                layer.data[loop_i].uv=(u+offset,v)

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.mode_set(mode="EDIT")
        bm=bmesh.from_edit_mesh(me)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        uv_attr=bm.loops.layers.uv.verify()
        tag=bm.faces.layers.int.new("r12_source_face_id")
        for i,face in enumerate(bm.faces):
            face[tag]=i+1
        before={int(face[tag]):face_sig(face,uv_attr,tag) for face in bm.faces}
        original_verts={key:bm.verts[vert_id] for key,vert_id in source_id.items()}
        source_faces=list(bm.faces) # stable BMFace refs after BMesh table invalidation
        # The collar polygons were created in exactly the strip boundary-edge order.
        edge_to_bridge_face=_boundary_face_indices(strip.faces)
        boundary_offsets={}
        for face_i,(u,v) in enumerate(ordered_edges):
            source_face=source_faces[face_i]
            du=_face_uv(source_face,original_verts[u],uv_attr)-np.array(base_uv[u])
            dv=_face_uv(source_face,original_verts[v],uv_attr)-np.array(base_uv[v])
            if np.max(np.abs(du-dv))>1e-5:
                raise ValueError("unsupported source UV affine/rotation inside edge")
            key=tuple(sorted((u,v)))
            if key not in edge_to_bridge_face:
                raise ValueError("original collar edge not present on strip boundary")
            boundary_offsets[key]=tuple((.5*(du+dv)).tolist())
        if len(boundary_offsets)!=na+nb:
            raise ValueError("incomplete source boundary UV correspondence")
        if arm=="r12_chart_transfer":
            offsets,metrics=label_chart_offsets(strip.vertices,strip.faces,boundary_offsets)
        else:
            offsets=np.zeros((len(strip.faces),2),dtype=float)
            metrics=dict(boundary_count=na+nb,chart_count=1,internal_edges=0,
                         internal_seam_edges=0,internal_seam_fraction=0.,
                         internal_seam_length=0.)

        bridge_verts=dict(original_verts)
        for idx,point in enumerate(strip.vertices):
            if idx not in bridge_verts:
                bridge_verts[idx]=bm.verts.new(tuple(float(k) for k in point))
        new_faces=[]
        for face_i,tri in enumerate(strip.faces):
            face=bm.faces.new(tuple(bridge_verts[int(i)] for i in tri))
            face[tag]=0
            face.material_index=2
            for loop in face.loops:
                idx=next(int(i) for i in tri if bridge_verts[int(i)]==loop.vert)
                loop[uv_attr].uv=tuple((np.asarray(base_uv[idx])+offsets[face_i]).tolist())
            new_faces.append(face)
        bm.normal_update()
        after={int(face[tag]):face_sig(face,uv_attr,tag)
               for face in bm.faces if int(face[tag])>0}
        source_unchanged=before==after
        max_gap=0.0
        pairs=0
        boundary_pair_uv_samples=[]
        for face_i,(u,v) in enumerate(ordered_edges):
            source_face=source_faces[face_i]
            edge=tuple(sorted((u,v)))
            new_face=new_faces[edge_to_bridge_face[edge]]
            for key in (u,v):
                lhs=_face_uv(source_face,original_verts[key],uv_attr)
                rhs=_face_uv(new_face,original_verts[key],uv_attr)
                max_gap=max(max_gap,float(np.max(np.abs(lhs-rhs))))
                boundary_pair_uv_samples.append([lhs.tolist(),rhs.tolist()])
                pairs+=1
        corner_uvs=[]
        area_max_delta=0.
        new_mat_indices=[]
        for face_i,(tri,face) in enumerate(zip(strip.faces,new_faces)):
            corners=[]
            new_mat_indices.append(int(face.material_index))
            for key in tri:
                corners.append(tuple(_face_uv(face,bridge_verts[int(key)],uv_attr)))
            corner_uvs.append(corners)
            old_area=_triangle_signed_uv_area([base_uv[int(idx)] for idx in tri])
            area_max_delta=max(area_max_delta,
                               abs(old_area-_triangle_signed_uv_area(corners)))
        # Infer interior seams from *actual per-face-corner UVs* independently
        # of chart propagation output (not only the algorithm's seam count).
        edge_incidence=defaultdict(list)
        for i,tri in enumerate(strip.faces):
            for u,v in zip(tri,np.roll(tri,-1)):
                edge_incidence[tuple(sorted((int(u),int(v))))].append(i)
        actual_seam_edges=0
        actual_seam_length=0.
        total_internal=0
        for (u,v),adj in edge_incidence.items():
            if len(adj)!=2:continue
            total_internal+=1
            p,q=adj
            uvp={int(vi):corner_uvs[p][j] for j,vi in enumerate(strip.faces[p])}
            uvq={int(vi):corner_uvs[q][j] for j,vi in enumerate(strip.faces[q])}
            discrepancy=max(abs(float(uvp[k][coord])-float(uvq[k][coord]))
                            for k in (u,v) for coord in (0,1))
            if discrepancy>1e-5:
                actual_seam_edges+=1
                actual_seam_length+=float(np.linalg.norm(strip.vertices[u]-strip.vertices[v]))
        shared_edges=0
        for edge in bm.edges:
            if len(edge.link_faces)==2:
                linked=list(edge.link_faces)
                if (int(linked[0][tag])==0)!=(int(linked[1][tag])==0):
                    shared_edges+=1
        outer_boundary_edges=sum(len(e.link_faces)==1 for e in bm.edges)
        nonmanifold_edges=sum(len(e.link_faces)>2 for e in bm.edges)
        bmesh.update_edit_mesh(me,loop_triangles=True,destructive=True)
        bpy.ops.object.mode_set(mode="OBJECT")
        me.calc_loop_triangles()
        complete_vertices=[tuple(float(v) for v in x.co) for x in me.vertices]
        complete_faces=[list(map(int,t.vertices)) for t in me.loop_triangles]
        source_xyz_preserved=all(np.max(np.abs(
            np.array(complete_vertices[source_id[i]])-strip.vertices[i]))<1e-6
            for i in boundary)
        result=dict(case=case["name"],split=case["split"],uv_mode=case["uv_mode"],
                    arm=arm,status="generated",r10_path=output["path"],
                    original_source_signature_unchanged=bool(source_unchanged),
                    source_xyz_preserved=bool(source_xyz_preserved),
                    bridge_material_2=all(n==2 for n in new_mat_indices),
                    source_boundary_uv_pair_count=pairs,
                    boundary_pair_uv_samples=boundary_pair_uv_samples,
                    source_boundary_max_uv_error=max_gap,
                    internal_seam_edges=int(actual_seam_edges),
                    internal_edges=int(total_internal),
                    internal_seam_fraction=(actual_seam_edges/total_internal if total_internal else 0.),
                    internal_seam_length=actual_seam_length,
                    chart_count=metrics["chart_count"],
                    signed_triangle_uv_area_max_delta=area_max_delta,
                    bridge_uv_finite=all(math.isfinite(v)
                                         for triangle in corner_uvs for uv in triangle for v in uv),
                    bridge_face_count=len(new_faces),expected_bridge_face_count=len(strip.faces),
                    source_to_bridge_shared_edges=shared_edges,
                    expected_shared_edges=na+nb,
                    outer_boundary_edges=outer_boundary_edges,
                    expected_outer_boundary_edges=na+nb,
                    nonmanifold_edges=nonmanifold_edges,
                    elapsed_seconds=time.perf_counter()-started,
                    bridge_corner_uvs=corner_uvs,
                    bridge_vertex_base_uv=[base_uv[i] for i in range(len(strip.vertices))],
                    strip_vertices=strip.vertices.tolist(),strip_faces=strip.faces.tolist(),
                    joined_vertices=complete_vertices,joined_triangles=complete_faces)
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
        if beginning[4]:
            for item in bpy.data.objects:
                if item.as_pointer() in beginning[4]:item.select_set(True)
        if beginning[3] is not None:
            for item in bpy.data.objects:
                if item.as_pointer()==beginning[3]:
                    bpy.context.view_layer.objects.active=item
                    break
        if snapshot()!=beginning:
            raise RuntimeError("R12 temporary Blender scene not fully restored")
    result["scene_restored"]=True
    return result


def run(development_only=False):
    rows=[]
    for case in cases():
        if development_only and case["split"]!="development":
            continue
        for arm in ARMS:
            try:
                row=execute(case,arm)
            except Exception as exc:
                row=dict(case=case["name"],split=case["split"],uv_mode=case["uv_mode"],
                         arm=arm,status="generation_error",
                         reason=type(exc).__name__+": "+str(exc))
            rows.append(row)
            print("R12_RUN",json.dumps({k:row.get(k) for k in
                ("case","uv_mode","arm","status","reason",
                 "source_boundary_max_uv_error","internal_seam_fraction")}),flush=True)
    return dict(cycle="R12",blender=bpy.app.version_string,synthetic_only=True,
                dev_only=development_only,
                arms=list(ARMS),approved=False,
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                    for p in ("cbdk_geometry/uv_charts.py","cycles/r12/fixtures.py",
                              "cycles/r12/blender_run.py")},cases=rows)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    p.add_argument("--development-only",action="store_true")
    options=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    data=run(development_only=options.development_only)
    path=Path(options.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x") as file:json.dump(data,file,indent=2)
    print("R12_RAW",len(data["cases"]),data["blender"],flush=True)
