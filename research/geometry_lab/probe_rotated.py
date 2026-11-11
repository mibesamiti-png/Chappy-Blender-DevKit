"""Additional nonsymmetric sphere union experiment; same quality gate."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import json
import numpy as np
import bpy
from cbdk_geometry import Mesh, quality, detect
from cbdk_geometry.fixtures import sphere
from cbdk_geometry.blender_backend import join
from benchmark import timed, source_hashes
from math import sin, cos, pi
angle = .173
rotation = np.array([[cos(angle), -sin(angle), 0], [sin(angle), cos(angle), 0], [0,0,1]])
a, unit = sphere(), sphere()
b = Mesh(unit.vertices @ rotation.T + [1, .037, .019], unit.faces)
d = float(np.linalg.norm([1,.037,.019]))
rows = []
for method in ('exact','voxel'):
    try:
        mesh, timing = timed(lambda: join(a,b,method,.15))
        q = quality(mesh)
        collision = detect(mesh)
        expected = 8*pi/3-pi*(4+d)*(2-d)**2/12
        err = abs(q['volume']-expected)/expected
        passed = q['boundary_edges']==0 and q['nonmanifold_edges']==0 and q['components']==1 and err<.08 and collision['pairs']==[]
        rows.append(dict(method=method, status='passed' if passed else 'failed', quality=q,
                         volume_relative_error=err, intersection_pairs=len(collision['pairs']), **timing))
    except ValueError as exc:
        rows.append(dict(method=method,status='rejected',reason=str(exc)))
report = dict(schema_version=1,synthetic_only=True,blender=bpy.app.version_string,
              source_sha256=source_hashes(),cases=rows)
path = Path(__file__).parent/'runs'/'rotated.json'
with path.open('x') as f: json.dump(report,f,indent=2)
print(json.dumps(rows))
