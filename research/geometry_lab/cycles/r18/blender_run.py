"""R18 retrospective Blender Edit Mode integration of frozen R17 outputs."""
import argparse, hashlib, json, sys, types
from pathlib import Path
from collections import defaultdict
import numpy as np
import bpy, bmesh
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
saved=sys.modules.get("cycles")
pkg=types.ModuleType("cycles"); pkg.__path__=[str(ROOT/"cycles")]; sys.modules["cycles"]=pkg
try:
    from cycles.r17.fixtures import cases
    from cycles.r16.cut_uv import source_loop
    from cycles.r11.blender_run import snapshot,face_sig
finally:
    sys.modules.pop("cycles",None)
    if saved is not None: sys.modules["cycles"]=saved

def execute(row,case,arm):
    original_state=snapshot(); obj=None; mesh=None; mats=[]
    try:
        v=np.asarray(row["vertices"],np.float32); f=np.asarray(row["faces"],int)
        uv=np.asarray(row[arm+"_uv"],np.float32)
        # Source collar comes from the original input rings, not candidate UVs.
        lo=source_loop(case["a"],0.); hi=source_loop(case["b"],1.)
        source=lo+hi
        lookup={tuple(p):i for i,p in enumerate(v.astype(float))}
        efaces=defaultdict(list)
        for i,t in enumerate(f):
            for a,b in zip(t,np.roll(t,-1)): efaces[tuple(sorted((int(a),int(b))))].append((int(a),int(b)))
        boundary={e:x[0] for e,x in efaces.items() if len(x)==1}
        pins={}; source_vertices=[]; source_map={}; outer={}
        for x,y,ux,uy in source:
            for p in (x,y):
                if p not in source_map:
                    source_map[p]=len(source_vertices); source_vertices.append(p)
        n=len(source_vertices)
        for p,i in sorted(source_map.items(),key=lambda x:x[1]):
            h=0 if i<len(lo) else 1
            outer[p]=len(source_vertices); source_vertices.append((p[0],p[1],p[2]+(-.18 if h==0 else .18)))
        polygons=[]; cuv=[]; sm=[]
        for x,y,ux,uy in source:
            a,b=lookup[x],lookup[y]; e=tuple(sorted((a,b))); pins[e]={a:ux,b:uy}
            if boundary[e]==(a,b): x,y,ux,uy=y,x,uy,ux
            h=int(ux[1]); ov=-.18 if h==0 else 1.18
            polygons.append([source_map[x],source_map[y],outer[y],outer[x]])
            cuv.append([ux,uy,(uy[0],ov),(ux[0],ov)]); sm.append(h)
        if set(pins)!=set(boundary): raise ValueError("source edges mismatch")
        mesh=bpy.data.meshes.new("R18_TEMP"); mesh.from_pydata(source_vertices,[],polygons); mesh.update()
        obj=bpy.data.objects.new("R18_TEMP",mesh); bpy.context.collection.objects.link(obj)
        for name in ("lower","upper","bridge"):
            mat=bpy.data.materials.new("R18_"+name); mats.append(mat); mesh.materials.append(mat)
        layer=mesh.uv_layers.new(name="UVMap")
        for i,p in enumerate(mesh.polygons):
            p.material_index=sm[i]
            for j,k in enumerate(p.loop_indices): layer.data[k].uv=cuv[i][j]
        bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active=obj
        bpy.ops.object.mode_set(mode="EDIT"); bm=bmesh.from_edit_mesh(mesh); bm.verts.ensure_lookup_table()
        tag=bm.faces.layers.int.new("r18_id"); uvl=bm.loops.layers.uv.verify()
        for i,p in enumerate(bm.faces): p[tag]=i+1
        before={int(p[tag]):face_sig(p,uvl,tag) for p in bm.faces}
        vertices={lookup[p]:bm.verts[i] for p,i in source_map.items()}
        for i,p in enumerate(v):
            if i not in vertices: vertices[i]=bm.verts.new(p.tolist())
        reverse={vert:i for i,vert in vertices.items()}
        expected_seams=set()
        for e,refs in efaces.items():
            if len(refs)!=2: continue
            a,b=e; incident=[i for i,t in enumerate(f) if a in t and b in t]
            i,j=incident
            p=dict(zip(f[i],uv[i])); q=dict(zip(f[j],uv[j]))
            if max(np.max(np.abs(p[k]-q[k])) for k in e)>1e-5: expected_seams.add(e)
        for i,t in enumerate(f):
            face=bm.faces.new([vertices[int(j)] for j in t]); face[tag]=-(i+1); face.material_index=2
            for l in face.loops: l[uvl].uv=uv[i,int(np.flatnonzero(t==reverse[l.vert])[0])].tolist()
        for edge in bm.edges:
            a,b=edge.verts
            if a in reverse and b in reverse and tuple(sorted((reverse[a],reverse[b]))) in expected_seams: edge.seam=True
            # Extend the explicit seam along each collar's 0/1 edge.
            if len(edge.link_faces)==2:
                vals=[]
                for face in edge.link_faces:
                    vals.append({l.vert:tuple(l[uvl].uv) for l in face.loops})
                if max(abs(vals[0][k][j]-vals[1][k][j]) for k in (a,b) for j in (0,1))>1e-5: edge.seam=True
        bmesh.update_edit_mesh(mesh,loop_triangles=True,destructive=True)
        bpy.ops.object.mode_set(mode="OBJECT")
        # Read actual stored Mesh, then independently re-enter Edit Mode for source signatures.
        mesh.calc_loop_triangles()
        tag_data=mesh.attributes["r18_id"].data; layer=mesh.uv_layers["UVMap"]
        ids=[int(x.value) for x in tag_data]
        actual_v=[list(x.co) for x in mesh.vertices]
        triangles=[]; corners=[]; face_ids=[]; materials=[]
        for t in mesh.loop_triangles:
            triangles.append(list(t.vertices)); corners.append([list(layer.data[k].uv) for k in t.loops])
            face_ids.append(ids[t.polygon_index]); materials.append(mesh.polygons[t.polygon_index].material_index)
        seam_flags=[list(e.vertices) for e in mesh.edges if e.use_seam]
        bpy.ops.object.mode_set(mode="EDIT"); bm=bmesh.from_edit_mesh(mesh)
        tag=bm.faces.layers.int["r18_id"]; uvl=bm.loops.layers.uv.verify()
        after={int(p[tag]):face_sig(p,uvl,tag) for p in bm.faces if p[tag]>0}
        # Face loop start may rotate on roundtrip; canonicalize jointly, not separate UVs.
        def canon(s):
            k,m,xyz,uv=s; pairs=list(zip(xyz,uv)); return (k,m,min(tuple(pairs[i:]+pairs[:i]) for i in range(len(pairs))))
        preserved={k:canon(s) for k,s in before.items()}=={k:canon(s) for k,s in after.items()}
        bpy.ops.object.mode_set(mode="OBJECT")
        result=dict(case=row["case"],arm=arm,status="generated",source_preserved=preserved,vertices=actual_v,triangles=triangles,corner_uv=corners,face_ids=face_ids,materials=materials,seam_flags=seam_flags,source_faces=n,expected_bridge_faces=len(f))
    finally:
        if bpy.context.mode!="OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
        if obj is not None: bpy.data.objects.remove(obj,do_unlink=True)
        if mesh is not None: bpy.data.meshes.remove(mesh)
        for mat in mats: bpy.data.materials.remove(mat)
        for o in bpy.context.selected_objects: o.select_set(False)
        for o in bpy.data.objects:
            if o.as_pointer() in original_state[4]: o.select_set(True)
            if o.as_pointer()==original_state[3]: bpy.context.view_layer.objects.active=o
        if snapshot()!=original_state: raise RuntimeError("scene not restored")
    result["scene_restored"]=True
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",required=True)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:]); inp=Path(a.input); raw=json.loads(inp.read_text())
    if raw["cycle"]!="R17" or not raw["gate"] or raw["approved"] or len(raw["rows"])!=12: raise ValueError("bad R17 evidence")
    by={c["name"]:c for c in cases()}; rows=[]
    for row in raw["rows"]:
        for arm in ("baseline","candidate"):
            try: out=execute(row,by[row["case"]],arm)
            except Exception as exc: out=dict(case=row["case"],arm=arm,status="error",reason=type(exc).__name__+": "+str(exc))
            rows.append(out); print("R18_BLENDER",json.dumps({k:out.get(k) for k in ("case","arm","status","reason","source_preserved")}),flush=True)
    with Path(a.output).open("x") as f: json.dump(dict(cycle="R18",approved=False,synthetic_only=True,blender=bpy.app.version_string,input_sha256=hashlib.sha256(inp.read_bytes()).hexdigest(),rows=rows),f,allow_nan=False)
