"""Fixed corpus, three interleaved repeats; optional hash-bound R2 fixtures."""
import argparse,json,hashlib,time
from pathlib import Path
from statistics import median
from importlib.metadata import version
from cbdk_geometry import Mesh
from cbdk_geometry.exact import detect_exact
from cbdk_geometry.accelerated import detect_accelerated
from cbdk_geometry.fixtures import soup
from cycles.r3.fixtures import torus,sheet
from cycles.r2.oracle import mesh_hits
from benchmark import source_hashes


def run(include_blender):
    cases=[('torus',torus()),('saddle',sheet()),('folded',sheet(True)),('sparse',soup(64))]
    if include_blender:
        p=Path('runs/r2_meshes.json');binding=json.loads(Path('cycles/r2/blender_results.json').read_text())
        assert hashlib.sha256(p.read_bytes()).hexdigest()==binding['input_sha256']
        for c in json.loads(p.read_text())['cases']:
            cases.append((c['name'],Mesh(c['vertices'],c['faces'])))
    rows=[];start=time.monotonic()
    for name,m in cases:
        oracle=mesh_hits(m);results={};samples={k:[] for k in ('r2','cached','shortcut')}
        for rep in range(3):
            order=list(samples);order=order[rep:]+order[:rep]
            for method in order:
                if time.monotonic()-start>270:raise TimeoutError('cycle budget exceeded')
                f=detect_exact if method=='r2' else detect_accelerated
                kw={} if method=='r2' else {'shortcuts':method=='shortcut'}
                t=time.perf_counter();r=f(m,pair_budget=2000000,seconds=60,**kw)
                samples[method].append(time.perf_counter()-t)
                assert r['status']=='measured' and r['pairs']==oracle,(name,method,r['status'])
                results[method]=r
        row=dict(case=name,triangles=len(m.faces),oracle_hits=len(oracle),
                 methods={k:dict(median_seconds=median(v),samples_seconds=v,
                 hits=len(results[k]['pairs']),paths=results[k].get('paths'),oracle_match=True) for k,v in samples.items()})
        rows.append(row);print(json.dumps(row),flush=True)
    return dict(schema_version=3,cycle='R3',synthetic_only=True,cgal=version('cgal'),
                source_sha256=source_hashes(),repeats=3,warmup=0,
                timing_order='rotating_method_order',cases=rows,elapsed_seconds=time.monotonic()-start)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--include-blender',action='store_true');a=p.parse_args()
    r=run(a.include_blender);path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(r,f,indent=2)
