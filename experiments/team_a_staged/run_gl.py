"""Synthetic-only A experiment. External frozen GL source, no product imports."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(root):
    manifest = json.loads((HERE / 'gl_manifest.json').read_text())
    for name, digest in manifest['files'].items():
        if sha((root / name).read_bytes()) != digest:
            raise ValueError('frozen_source_mismatch')
    return manifest


def fixture(name, np, Mesh):
    # Authored independently of GL fixtures; IDs express connectivity, no weld.
    v = [[0, 0, 0], [2, 0, 0], [0, 2, 0]]
    f = [[0, 1, 2]]
    expected = []
    if name == 'shared_edge':
        v += [[0, 0, 2]]; f += [[1, 0, 3]]
    elif name == 'duplicate':
        f += [[2, 1, 0]]; expected = [(0, 1)]
    elif name == 'shared_overlap':
        v += [[1, 1, 0]]; f += [[0, 1, 3]]; expected = [(0, 1)]
    elif name in ('cross', 'gap', 'unwelded_touch'):
        other = {'cross': [[.5, .5, -1], [.5, .5, 1], [1, .5, 0]],
                 'gap': [[0, 0, .125], [2, 0, .125], [0, 2, .125]],
                 'unwelded_touch': [[0, 0, 0], [-1, 0, 1], [0, -1, 1]]}[name]
        v += other; f += [[3, 4, 5]]
        if name != 'gap': expected = [(0, 1)]
    elif name.startswith('sparse'):
        n = 513 if name == 'sparse513' else 64
        v = [[3*i+x, y, 0] for i in range(n) for x, y in ((0, 0), (1, 0), (0, 1))]
        f = [[3*i, 3*i+1, 3*i+2] for i in range(n)]
    elif name == 'grid128':
        v = [[x, y, 0] for y in range(9) for x in range(9)]
        f = []
        for y in range(8):
            for x in range(8):
                a = 9*y+x
                f += [[a, a+1, a+10], [a, a+10, a+9]]
    else:
        raise ValueError('unknown_fixture')
    return np.array(v, dtype=float), np.array(f, dtype=int), expected


def worker(root, case, method, control, scale):
    verify(root)
    sys.path.insert(0, str(root))
    import numpy as np
    from cbdk_geometry import Mesh
    from cbdk_geometry.exact import detect_exact
    from cbdk_geometry.accelerated import detect_accelerated
    v, f, expected = fixture(case, np, Mesh)
    v *= scale
    before = (sha(v.tobytes()), sha(f.tobytes()))
    if len(f) > 512:
        return dict(status='budget_exceeded', pairs=None, reason='a_face_limit', passed=True)
    m = Mesh(v, f)
    options = dict(pair_budget=20000, seconds=2)
    if control == 'pair_limit': options['pair_budget'] = 1
    if control == 'time_limit': options['seconds'] = 1e-100
    fun = detect_exact if method == 'r2' else detect_accelerated
    samples = []
    for _ in range(3):
        start = time.perf_counter(); result = fun(m, **options)
        samples.append(time.perf_counter()-start)
    preserved = before == (sha(v.tobytes()), sha(f.tobytes()))
    preserved &= before == (sha(m.vertices.tobytes()), sha(m.faces.tobytes()))
    if control == 'normal':
        valid = result['status'] == 'measured' and result['pairs'] == expected
    else:
        valid = result['status'] == 'budget_exceeded' and result['pairs'] is None
    return dict(**result, samples_seconds=samples, median_seconds=statistics.median(samples),
                input_preserved=bool(preserved), passed=bool(valid and preserved),
                numpy=np.__version__, input_sha256=sha(v.tobytes()+f.tobytes()))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--gl-root', type=Path, required=True)
    p.add_argument('--output', type=Path)
    p.add_argument('--worker', action='store_true')
    p.add_argument('--case'); p.add_argument('--method')
    p.add_argument('--control', default='normal'); p.add_argument('--scale', type=float, default=1)
    a = p.parse_args(); root = a.gl_root.resolve(); manifest = verify(root)
    if a.worker:
        print(json.dumps(worker(root, a.case, a.method, a.control, a.scale))); return
    if a.output is None or a.output.exists(): raise ValueError('fresh_output_required')
    rows = []
    jobs = [(case, 'normal', scale) for case in (
        'cross', 'gap', 'shared_edge', 'duplicate', 'shared_overlap', 'unwelded_touch')
        for scale in (.125, 1, 8)]
    jobs += [('sparse64', 'normal', 1), ('grid128', 'normal', 1),
             ('sparse64', 'pair_limit', 1), ('sparse64', 'time_limit', 1),
             ('sparse513', 'normal', 1)]
    for case, control, scale in jobs:
        for method in ('r2', 'r3'):
            cmd = [sys.executable, str(Path(__file__).resolve()), '--worker', '--gl-root', str(root),
                   '--case', case, '--method', method, '--control', control, '--scale', str(scale)]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                result = json.loads(proc.stdout) if proc.returncode == 0 else dict(status='worker_error', pairs=None, passed=False)
            except subprocess.TimeoutExpired:
                result = dict(status='process_timeout', pairs=None, passed=False)
            rows.append(dict(case=case, control=control, scale=scale, method=method, result=result))
    result = dict(schema=1, gl_head=manifest['head'], python=platform.python_version(),
                  platform=platform.platform(), adapter_sha256=sha(Path(__file__).read_bytes()),
                  caps=dict(faces=512, pairs=20000, cooperative_seconds=2, process_seconds=10),
                  independent_oracle='analytic expectations; CGAL not installed locally',
                  auto_adopt=False, approved=False, passed=sum(r['result']['passed'] for r in rows),
                  total=len(rows), rows=rows)
    with a.output.open('x', encoding='utf-8') as out: json.dump(result, out, indent=2)
    print(json.dumps({k:v for k,v in result.items() if k != 'rows'}))
    if result['passed'] != result['total']: raise SystemExit(1)


if __name__ == '__main__': main()
