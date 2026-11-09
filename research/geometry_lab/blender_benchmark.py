"""blender --background --factory-startup --disable-autoexec --python-exit-code 1
--python blender_benchmark.py -- --output runs/blender.json
No user files opened; temporary authored meshes only.
"""
import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
from benchmark import timed, source_hashes
from cbdk_geometry import quality, detect
from cbdk_geometry.fixtures import sphere
from cbdk_geometry.blender_backend import join
from math import pi


def run():
    rows = []
    original_objects = set(bpy.data.objects)
    original_meshes = set(bpy.data.meshes)
    original_selection = set(bpy.context.selected_objects)
    original_active = bpy.context.view_layer.objects.active
    for case, d in [('overlap', 1.0), ('thin_neck', 1.95), ('tangent', 2.0), ('gap', 2.2)]:
        a, b = sphere(), sphere(center=(d,0,0))
        for method, voxel in [('exact', .15), ('voxel', .2), ('voxel', .1)]:
            row = dict(case=case, distance=d, method=method, voxel_size=voxel if method == 'voxel' else None)
            try:
                mesh, timing = timed(lambda: join(a, b, method, voxel))
                q = quality(mesh)
                start = perf_counter()
                collision = detect(mesh, pair_budget=300000)
                detection_ms = (perf_counter()-start)*1000
                reference_volume = 8*pi/3 - (pi*(4+d)*(2-d)**2/12 if d < 2 else 0)
                error = abs(q['volume']-reference_volume)/reference_volume
                # Tangency is reported as ambiguous, not arbitrarily a pass.
                topology = q['boundary_edges'] == 0 and q['nonmanifold_edges'] == 0 and q['components'] == (1 if d < 2 else 2)
                success = topology and error < .08 and collision['status'] == 'measured' and not collision['pairs']
                row.update(status='ambiguous_contact' if d == 2 else ('passed' if success else 'failed'),
                           quality=q, volume_relative_error=error, intersection_pairs=None if collision['pairs'] is None else len(collision['pairs']),
                           detector_status=collision['status'], detection_ms=detection_ms, **timing)
            except Exception as exc:
                row.update(status='error', error_type=type(exc).__name__, reason=str(exc))
            rows.append(row)
            print('RESEARCH_CASE', json.dumps(row), flush=True)
            assert set(bpy.data.objects) == original_objects
            assert set(bpy.data.meshes) == original_meshes
            assert set(bpy.context.selected_objects) == original_selection
            assert bpy.context.view_layer.objects.active == original_active
    return dict(schema_version=1, synthetic_only=True, blender=bpy.app.version_string,
                source_sha256=source_hashes(), cases=rows,
                success_count=sum(r['status']=='passed' for r in rows),
                failure_count=sum(r['status'] in ('failed','error') for r in rows),
                ambiguous_count=sum(r['status']=='ambiguous_contact' for r in rows),
                scene_preserved=True, detector_certified=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = run()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(report, f, indent=2, allow_nan=False)
    # Expected research failures remain observations, backend exceptions fail the runner.
    raise SystemExit(1 if any(r['status']=='error' for r in report['cases']) else 0)
