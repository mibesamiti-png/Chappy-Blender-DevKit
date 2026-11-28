"""Export ONLY authored fixtures for independent process comparison; no user IO."""
import json
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root))
import bpy
import numpy as np
from cbdk_geometry import Mesh
from cbdk_geometry.fixtures import sphere
from cbdk_geometry.blender_backend import join
from benchmark import source_hashes
from math import sin, cos
cases=[]
for name,method,d,rotate in [('voxel_overlap','voxel',1.,False),('exact_thin_neck','exact',1.95,False),('exact_rotated','exact',1.,True)]:
    a,b=sphere(),sphere(center=(d,0,0))
    if rotate:
        angle=.173;rotation=np.array([[cos(angle),-sin(angle),0],[sin(angle),cos(angle),0],[0,0,1]])
        unit=sphere();b=Mesh(unit.vertices@rotation.T+[1,.037,.019],unit.faces)
    m=join(a,b,method,.2)
    cases.append(dict(name=name,vertices=m.vertices.tolist(),faces=m.faces.tolist()))
p=root/'runs'/'r2_meshes.json'
with p.open('x') as f:json.dump(dict(synthetic_only=True,blender=bpy.app.version_string,source_sha256=source_hashes(),cases=cases),f)
print('exported',len(cases),'authored fixtures',bpy.app.version_string)
