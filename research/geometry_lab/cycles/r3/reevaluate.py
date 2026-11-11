"""CGAL-driven re-evaluation, explicitly not the new detector grading itself."""
import json,hashlib
from pathlib import Path
from importlib.metadata import version
from cbdk_geometry import Mesh
from cycles.r2.oracle import mesh_hits
from benchmark import source_hashes
root=Path(__file__).resolve().parents[2];p=root/'runs/r3_join_meshes.json'
data=json.loads(p.read_text());assert data['synthetic_only'] is True
old=json.loads((root/'results/blender.json').read_text())['cases']
old+= [dict(x,case='rotated_overlap',voxel_size=.15 if x['method']=='voxel' else None) for x in json.loads((root/'results/rotated.json').read_text())['cases']]
rows=[]
for case in data['cases']:
    baseline=next(x for x in old if all(x[k]==case[k] for k in ('case','method','voxel_size')))
    row={k:v for k,v in case.items() if k not in ('vertices','faces')}
    row['old_status']=baseline['status']
    if case['status']=='generated':
        try:
            hits=mesh_hits(Mesh(case['vertices'],case['faces']))
            q=case['quality'];d=case['distance']
            passed=(q['boundary_edges']==q['nonmanifold_edges']==0 and q['components']==(1 if d<2 else 2)
                    and case['volume_relative_error']<.08 and not hits)
            row.update(status='ambiguous_contact' if case['case']=='tangent' else ('passed' if passed else 'failed'),oracle_hits=len(hits))
        except Exception as e:row.update(status='oracle_unavailable',reason=type(e).__name__)
    rows.append(row)
report=dict(schema_version=3,synthetic_only=True,blender=data['blender'],cgal=version('cgal'),
            source_sha256=source_hashes(),generator_sha256=data['source_sha256'],input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),cases=rows)
with (root/'runs/r3_reevaluation.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps([{k:r.get(k) for k in ('case','method','voxel_size','old_status','status','oracle_hits')} for r in rows]))
if any(r['status']=='oracle_unavailable' for r in rows):raise SystemExit(1)
