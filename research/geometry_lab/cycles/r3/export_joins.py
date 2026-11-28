"""Recreate all R1 synthetic candidates; no private assets or scene IO."""
import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root))
import bpy,numpy as np
from math import sin,cos,pi
from cbdk_geometry import Mesh,quality
from cbdk_geometry.fixtures import sphere
from cbdk_geometry.blender_backend import join
from benchmark import source_hashes
rows=[];before=(set(bpy.data.objects),set(bpy.data.meshes))
for name,d in [('overlap',1.),('thin_neck',1.95),('tangent',2.),('gap',2.2),('rotated_overlap',1.)]:
    a,b=sphere(),sphere(center=(d,0,0))
    if name=='rotated_overlap':
        t=.173;rot=np.array([[cos(t),-sin(t),0],[sin(t),cos(t),0],[0,0,1]])
        b=Mesh(sphere().vertices@rot.T+[1,.037,.019],sphere().faces);d=float(np.linalg.norm([1,.037,.019]))
    methods=[('exact',.15),('voxel',.15)] if name=='rotated_overlap' else [('exact',.15),('voxel',.2),('voxel',.1)]
    for method,h in methods:
        row=dict(case=name,method=method,voxel_size=h if method=='voxel' else None,distance=d)
        try:
            m=join(a,b,method,h);q=quality(m)
            volume=8*pi/3-(pi*(4+d)*(2-d)**2/12 if d<2 else 0)
            row.update(vertices=m.vertices.tolist(),faces=m.faces.tolist(),quality=q,
                       volume_relative_error=abs(q['volume']-volume)/volume,status='generated')
        except ValueError as e:row.update(status='rejected',reason=str(e))
        assert before==(set(bpy.data.objects),set(bpy.data.meshes))
        rows.append(row)
with (root/'runs/r3_join_meshes.json').open('x') as f:json.dump(dict(synthetic_only=True,blender=bpy.app.version_string,source_sha256=source_hashes(),cases=rows),f)
print('authored candidates:',len(rows),'Blender:',bpy.app.version_string)
