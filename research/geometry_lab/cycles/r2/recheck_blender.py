"""Compare three bounded synthetic Blender outputs against independent CGAL."""
import json
import time
from statistics import median
import hashlib
from pathlib import Path
from importlib.metadata import version
from cbdk_geometry import Mesh,detect
from cbdk_geometry.exact import detect_exact
from cycles.r2.oracle import mesh_hits
from benchmark import source_hashes
root=Path(__file__).resolve().parents[2]
source=root/'runs'/'r2_meshes.json'
data=json.loads(source.read_text())
assert data['synthetic_only'] is True
rows=[]
for case in data['cases']:
    m=Mesh(case['vertices'],case['faces'])
    results={}
    for name,fn in [('legacy',lambda:detect(m)),('exact',lambda:detect_exact(m,pair_budget=2000000,seconds=90)),('CGAL',lambda:mesh_hits(m))]:
        samples=[];previous=None
        for repeat in range(3):
            start=time.perf_counter();r=fn();samples.append(time.perf_counter()-start)
            if name=='CGAL':r=dict(status='measured',pairs=r)
            if previous is not None and r['pairs']!=previous['pairs']:
                raise AssertionError('nondeterministic pairs')
            previous=r
        results[name]=dict(**r,seconds=median(samples),samples_seconds=samples,repeats=3,warmup=0)
    oracle=set(map(tuple,results['CGAL']['pairs']))
    for name in ('legacy','exact'):
        r=results[name]
        if r['pairs'] is not None:
            hits=set(map(tuple,r['pairs']))
            r.update(false_positive=len(hits-oracle),false_negative=len(oracle-hits))
    row=dict(case=case['name'],triangles=len(m.faces),results=results)
    rows.append(row)
    print(json.dumps(row),flush=True)
report=dict(schema_version=2,synthetic_only=True,blender=data['blender'],cgal=version('cgal'),
            source_sha256=source_hashes(),generator_sha256=data['source_sha256'],
            input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),cases=rows)
with (root/'runs'/'r2_blender.json').open('x') as f:json.dump(report,f,indent=2)
if any(r['results']['exact']['status']!='measured' or r['results']['exact'].get('false_positive') or r['results']['exact'].get('false_negative') for r in rows):raise SystemExit(1)
