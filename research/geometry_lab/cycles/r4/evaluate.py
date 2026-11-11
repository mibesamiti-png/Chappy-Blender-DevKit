"""Independent CGAL, analytic boundary topology and sampled analytic loft goal."""
import sys,json,hashlib,argparse
from pathlib import Path
from collections import Counter
from importlib.metadata import version
import numpy as np
from cbdk_geometry import Mesh,quality
from cycles.r2.oracle import mesh_hits
from cycles.r4.fixtures import cases,ring
from benchmark import source_hashes


def evaluate(data):
    lookup={c['name']:c for split in ('development','holdout') for c in cases(split)}
    rows=[]
    for raw in data['cases']:
        r={k:v for k,v in raw.items() if k not in ('vertices','faces')};c=lookup[r['name']]
        if r['status']=='generated':
            try:
                mesh=Mesh(raw['vertices'],raw['faces']);hits=mesh_hits(mesh);q=quality(mesh)
                expected=np.vstack((c['a'],c['b'])).astype(np.float32).astype(float)
                # Native ordering may differ; compare coordinate multisets.
                boundary_preserved=sorted(map(tuple,expected))==sorted(map(tuple,mesh.vertices))
                edges=Counter(tuple(sorted((int(f[i]),int(f[(i+1)%3])))) for f in mesh.faces for i in range(3))
                euler=len(mesh.vertices)-len(edges)+len(mesh.faces)
                centers=mesh.vertices[mesh.faces].mean(1);d=[]
                ca=ring(2048,0,c['kind']);cb=ring(2048,1,c['kind'],c['radius'],c['offset'])
                for p in centers:
                    goal=(1-p[2])*ca+p[2]*cb
                    d.append(float(np.min(np.linalg.norm(goal[:,:2]-p[:2],axis=1))))
                rms=float(np.sqrt(np.mean(np.square(d))));maximum=max(d)
                topology=q['boundary_edges']==len(expected) and q['nonmanifold_edges']==0 and q['components']==1 and euler==0
                success=boundary_preserved and topology and not hits and q['min_triangle_quality']>=.1 and rms<=.08 and maximum<=.2
                r.update(status='passed' if success else 'failed',intersection_pairs=len(hits),quality=q,euler=euler,boundary_preserved=boundary_preserved,
                         sampled_loft_rms=rms,sampled_loft_max=maximum)
            except Exception as e:r.update(status='oracle_unavailable',reason=type(e).__name__+': '+str(e))
        rows.append(r)
    return dict(synthetic_only=True,blender=data['blender'],cgal=version('cgal'),source_sha256=source_hashes(),generator_sha256=data['source_sha256'],
                fixture_sha256=data['fixture_sha256'],cases=rows,
                totals={split:{method:dict(passed=sum(r['status']=='passed' for r in rows if r['split']==split and r['method']==method),
                total=sum(r['split']==split and r['method']==method for r in rows)) for method in ('index','phase','dp','blender_native')} for split in ('development','holdout')})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    path=Path(a.input);data=json.loads(path.read_text());assert data['synthetic_only'] is True
    result=evaluate(data);result['input_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    with Path(a.output).open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result['totals']))
    if any(r['status']=='oracle_unavailable' for r in result['cases']):raise SystemExit(1)
