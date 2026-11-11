"""Measure deterministic rejection and verify cleanup on failure."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import json
from time import perf_counter
from statistics import median
import bpy
from cbdk_geometry.fixtures import sphere
from cbdk_geometry.blender_backend import join
from benchmark import source_hashes
objects, meshes = set(bpy.data.objects), set(bpy.data.meshes)
a,b=sphere(),sphere(center=(1,0,0))
rows=[]
for name,kwargs in [('symmetric_exact',dict(method='exact')),('grid_budget',dict(method='voxel',voxel_size=.0001))]:
    samples=[]
    for _ in range(3):
        start=perf_counter()
        try:
            join(a,b,**kwargs)
        except ValueError as e:
            samples.append(dict(ms=(perf_counter()-start)*1000,reason=str(e)))
        else:
            raise AssertionError('expected rejection did not occur')
        assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    rows.append(dict(case=name,status='expected_rejection',samples=samples,median_ms=median(s['ms'] for s in samples)))
report=dict(synthetic_only=True,blender=bpy.app.version_string,source_sha256=source_hashes(),cases=rows,cleanup_preserved=True)
with (Path(__file__).parent/'runs'/'failures.json').open('x') as f: json.dump(report,f,indent=2)
print(json.dumps(rows))
