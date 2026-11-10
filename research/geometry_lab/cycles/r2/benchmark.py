"""Run with an oracle venv: python -m cycles.r2.benchmark --output runs/r2.json."""
import argparse
import hashlib
import json
import platform
import time
import tracemalloc
from importlib.metadata import version
from pathlib import Path
from statistics import median
import numpy as np
from cbdk_geometry import detect
from cbdk_geometry.exact import classify_pair
from cycles.r2.fixtures import analytic_cases
from cycles.r2.oracle import triangle_hit, mesh_hits
from benchmark import source_hashes


def measured(fn):
    fn()
    samples=[]
    for _ in range(3):
        start=time.perf_counter();result=fn();samples.append(1000*(time.perf_counter()-start))
    return result,dict(median_ms=median(samples),samples_ms=samples)


def run():
    started=time.monotonic()
    rows=[]
    for c in analytic_cases():
        if time.monotonic()-started>240:raise TimeoutError('cycle budget')
        m=c.pop('mesh');a,b=m.vertices[m.faces]
        old,ot=measured(lambda:bool(detect(m)['pairs']))
        new,nt=measured(lambda:classify_pair(a,b,*m.faces) in ('intersection','duplicate'))
        full,ft=measured(lambda:classify_pair(a,b,*m.faces,prefilter=False) in ('intersection','duplicate'))
        common=set(m.faces[0])&set(m.faces[1])
        if not common:
            external=triangle_hit(a,b);oracle='CGAL do_intersect (EPICK predicates)'
        elif len(common)==2:
            external=bool(mesh_hits(m));oracle='CGAL PMP self_intersections'
        else:
            external=None;oracle='analytic only (pair is not manifold / duplicate)'
        rows.append(dict(**c,legacy=old,exact=new,unfiltered=full,oracle=oracle,
                         oracle_hit=external,timing=dict(legacy=ot,exact=nt,unfiltered=ft)))
    rng=np.random.default_rng(20261110)
    random_rows=[]
    for i in range(128):
        a=rng.integers(-8,9,(3,3))/8
        b=rng.integers(-8,9,(3,3))/8
        # Fixed generator; reject rather than silently resample degenerate input.
        try: result=classify_pair(a,b)
        except ValueError:
            random_rows.append(dict(index=i,status='degenerate_rejected'));continue
        external=triangle_hit(a,b)
        random_rows.append(dict(index=i,status='measured',exact=result!='disjoint',oracle_hit=external))
    # Memory is measured separately, not contaminating reported timing.
    tracemalloc.start()
    for c in analytic_cases():
        m=c['mesh'];classify_pair(*m.vertices[m.faces],*m.faces)
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    summary={}
    for method in ('legacy','exact','unfiltered'):
        summary[method]=dict(false_positive=sum(r[method] and not r['expected'] for r in rows),
                             false_negative=sum(not r[method] and r['expected'] for r in rows))
    return dict(schema_version=2,cycle='R2',synthetic_only=True,python=platform.python_version(),
                numpy=np.__version__,cgal=version('cgal'),source_sha256=source_hashes(),
                analytic=rows,random=random_rows,summary=summary,python_peak_bytes=peak,
                native_memory_measured=False,elapsed_seconds=time.monotonic()-started,
                external_mismatches=sum(r['exact']!=r['oracle_hit'] for r in rows if r['oracle_hit'] is not None)+
                    sum(r['exact']!=r['oracle_hit'] for r in random_rows if r['status']=='measured'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    report=run();path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(report,f,indent=2,allow_nan=False)
    print(json.dumps({k:report[k] for k in ('summary','external_mismatches','python_peak_bytes','elapsed_seconds')}))
    if report['external_mismatches'] or any(report['summary']['exact'].values()):raise SystemExit(1)
