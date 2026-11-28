"""Counterbalance sparse best cases with dense intersecting triangle soups."""
import json
from pathlib import Path
from benchmark import timed, source_hashes
from cbdk_geometry import Mesh, detect
from cbdk_geometry.fixtures import soup
import numpy as np
rows=[]
for n in (32,64):
    original=soup(n)
    triangles=original.vertices.reshape(-1,3,3)
    centers=triangles.mean(1,keepdims=True)
    dense=Mesh((triangles-centers+centers*.005).reshape(-1,3),original.faces)
    ref=detect(dense,'brute')
    for method in ('brute','sweep'):
        result,timing=timed(lambda: detect(dense,method))
        rows.append(dict(triangles=n,method=method,hits=len(result['pairs']),tested=result['tested'],
                         parity=result['pairs']==ref['pairs'],**timing))
report=dict(schema_version=1,synthetic_only=True,numpy=np.__version__,source_sha256=source_hashes(),cases=rows)
with (Path(__file__).parent/'runs'/'dense.json').open('x') as f: json.dump(report,f,indent=2)
print(json.dumps(rows))
assert all(row['parity'] for row in rows)
