"""Run: python benchmark.py --output runs/python.json (synthetic inputs only)."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
from statistics import median
from time import perf_counter
import numpy as np
from cbdk_geometry import detect, guarded_step, Mesh
from cbdk_geometry.fixtures import pair, soup


def source_hashes():
    root = Path(__file__).resolve().parent
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*.py')) if 'runs' not in p.parts and '.venv' not in p.parts}


def timed(fn, repeats=3):
    fn()  # warmup, excluded
    times = []
    for _ in range(repeats):
        start = perf_counter()
        result = fn()
        times.append((perf_counter()-start)*1000)
    return result, dict(samples_ms=times, median_ms=median(times), repeats=repeats)


def run():
    rows = []
    for scale in (1e-6, 1, 1e6):
        for kind, expected in [('cross', True), ('separate', False), ('coplanar', True),
                ('coplanar_separate', False), ('touch', True), ('near_miss', False)]:
            for method in ('brute', 'sweep'):
                result, timing = timed(lambda: detect(pair(kind, scale), method))
                rows.append(dict(case=kind, scale=scale, method=method, expected=expected,
                                 success=bool(result['pairs']) == expected, **result, **timing))
    perf = []
    for n in (32, 128, 256):
        mesh = soup(n)
        reference = detect(mesh, 'brute')
        for method in ('brute', 'sweep'):
            result, timing = timed(lambda: detect(mesh, method))
            perf.append(dict(triangles=n, method=method,
                             parity=result['pairs'] == reference['pairs'], **result, **timing))
    m = pair('separate')
    d = np.zeros_like(m.vertices)
    d[3:, 2] = -2
    result, timing = timed(lambda: guarded_step(m, d))
    motion = dict(case='endpoint_clean_tunneling', status=result['status'], alpha=result['alpha'],
                  endpoint_hits=len(detect(Mesh(m.vertices+d, m.faces))['pairs']),
                  midpoint_hits=len(detect(Mesh(m.vertices+d*.5, m.faces))['pairs']), **timing)
    return dict(schema_version=1, synthetic_only=True, python=platform.python_version(),
                numpy=np.__version__, platform=platform.system(), source_sha256=source_hashes(),
                detection=rows, performance=perf, motion=motion,
                success_count=sum(r['success'] for r in rows), failure_count=sum(not r['success'] for r in rows))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = run()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(report, f, indent=2, allow_nan=False)
    print(json.dumps({k: report[k] for k in ('success_count', 'failure_count', 'motion')}))
    raise SystemExit(0 if report['failure_count'] == 0 and all(r['parity'] for r in report['performance']) else 1)
