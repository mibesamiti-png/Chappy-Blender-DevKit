"""Reproduce synthetic candidate validation in CI; no Blender equivalence claim."""
import argparse,json,time
import numpy as np
from benchmark import source_hashes
from cbdk_geometry.bridge import bridge_loops
from cycles.r4.fixtures import cases
from cycles.r4.evaluate import evaluate

def run():
    rows=[]
    for split in ('development','holdout'):
        for c in cases(split):
            for method in ('index','phase','dp'):
                a=c['a'].astype(np.float32).astype(float);b=c['b'].astype(np.float32).astype(float)
                start=time.perf_counter();m=bridge_loops(a,b,method)['mesh']
                rows.append(dict(name=c['name'],split=split,method=method,status='generated',vertices=m.vertices.tolist(),faces=m.faces.tolist(),median_seconds=time.perf_counter()-start))
    import hashlib
    from pathlib import Path
    data=dict(blender='not_run_python_only',source_sha256=source_hashes(),fixture_sha256=hashlib.sha256(Path('cycles/r4/fixtures.py').read_bytes()).hexdigest(),cases=rows)
    result=evaluate(data)
    if any(r['status']=='oracle_unavailable' for r in result['cases']):raise RuntimeError('independent oracle failed')
    # Every candidate on the four development controls must still meet the gate.
    assert all(r['status']=='passed' for r in result['cases'] if r['split']=='development' and r['method']!='index')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();r=run()
    with open(a.output,'x') as f:json.dump(r,f,indent=2)
    print(json.dumps(r['totals']))
