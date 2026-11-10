"""R5 preregistered one-cycle CGAL + sampled-loft comparison.

Run in the research directory, not against private models. R4's previous
holdout is DEVELOPMENT here. New R5 holdout lacks a Blender-native baseline.
"""
import argparse
from collections import Counter
from importlib.metadata import version
import hashlib
import json
from pathlib import Path
from statistics import median
import sys
import time

import numpy as np
from cbdk_geometry import quality
from cbdk_geometry.bridge import bridge_loops
from cbdk_geometry.radial_loft import radial_loft
from cycles.r2.oracle import mesh_hits
from cycles.r4.fixtures import ring
from cycles.r5.fixtures import cases

ROOT = Path(__file__).resolve().parents[2]


def _edge_signature(verts, edge):
    return tuple(sorted((tuple(verts[edge[0]]), tuple(verts[edge[1]]))))


def _assess(mesh, case):
    a = case["a"].astype(np.float32).astype(float)
    b = case["b"].astype(np.float32).astype(float)
    original = np.vstack((a, b))
    actual = {tuple(v) for v in mesh.vertices}
    preserved = all(tuple(v) in actual for v in original)
    edges = Counter(tuple(sorted((int(f[i]), int(f[(i+1) % 3]))))
                    for f in mesh.faces for i in range(3))
    boundary = {_edge_signature(mesh.vertices, edge)
                for edge, count in edges.items() if count == 1}
    expected = {_edge_signature(a, (i, (i+1) % len(a))) for i in range(len(a))}
    expected |= {_edge_signature(b, (i, (i+1) % len(b))) for i in range(len(b))}
    exact_boundary = boundary == expected
    q = quality(mesh)
    euler = len(mesh.vertices) - len(edges) + len(mesh.faces)
    # Same R4 centroid oracle and thresholds (not an area-weighted metric).
    centroid = mesh.vertices[mesh.faces].mean(axis=1)
    ca = ring(2048, 0, case["kind"])
    cb = ring(2048, 1, case["kind"], case["radius"], case["offset"])
    residuals = []
    for point in centroid:
        goal = (1-point[2])*ca + point[2]*cb
        residuals.append(float(np.min(np.linalg.norm(goal[:, :2]-point[:2], axis=1))))
    rms = float(np.sqrt(np.mean(np.square(residuals))))
    worst = max(residuals)
    hits = mesh_hits(mesh)  # external CGAL; an oracle error is NOT a clean mesh
    valid_topology = (q["boundary_edges"] == len(a)+len(b)
                      and q["nonmanifold_edges"] == 0
                      and q["components"] == 1 and euler == 0)
    passed = bool(preserved and exact_boundary and valid_topology and not hits
                  and q["min_triangle_quality"] >= .1 and rms <= .08 and worst <= .2)
    return dict(status="passed" if passed else "failed",
                original_vertices_preserved=bool(preserved), original_boundary_edges_preserved=bool(exact_boundary),
                topology_valid=bool(valid_topology), euler=euler, intersection_pairs=len(hits),
                quality=q, sampled_loft_rms=rms, sampled_loft_max=worst,
                vertex_count=len(mesh.vertices), face_count=len(mesh.faces))


def run():
    rows = []
    for case in cases():
        a = case["a"].astype(np.float32).astype(float)
        b = case["b"].astype(np.float32).astype(float)
        for method in (("radial_loft_3cuts", "phase") if case["split"] == "holdout"
                       else ("radial_loft_3cuts",)):
            result = dict(name=case["name"], split=case["split"],
                          origin=case["origin"], method=method)
            samples = []
            generated = []
            stage = "generation"
            try:
                for _ in range(3):
                    begin = time.perf_counter()
                    mesh = (radial_loft(a, b)["mesh"] if method == "radial_loft_3cuts"
                            else bridge_loops(a, b, method="phase")["mesh"])
                    samples.append(time.perf_counter()-begin)
                    generated.append(mesh)
                if not all(np.array_equal(mesh.vertices, generated[0].vertices)
                           and np.array_equal(mesh.faces, generated[0].faces) for mesh in generated):
                    raise RuntimeError("nondeterministic geometry")
                if not (np.array_equal(a, case["a"].astype(np.float32).astype(float))
                        and np.array_equal(b, case["b"].astype(np.float32).astype(float))):
                    raise RuntimeError("input mutation")
                stage = "oracle"
                result.update(_assess(generated[0], case))
                result["samples_seconds"] = samples
                result["median_seconds"] = median(samples)
            except Exception as exc:
                result.update(status="oracle_unavailable" if stage == "oracle" else "generation_error",
                              reason=type(exc).__name__ + ": " + str(exc))
            rows.append(result)
            print("CASE", json.dumps({k: v for k, v in result.items()
                                      if k in ("name", "method", "split", "status", "reason", "sampled_loft_rms",
                                               "sampled_loft_max", "median_seconds", "intersection_pairs")},
                                     ensure_ascii=False), flush=True)
    holdout = [r for r in rows if r["split"] == "holdout"]
    development = [r for r in rows if r["split"] == "development"]
    def summary(rows, method):
        selected = [r for r in rows if r["method"] == method]
        return dict(passed=sum(r["status"] == "passed" for r in selected), total=len(selected))
    archived = json.loads((ROOT/"cycles/r4/results/blender443.json").read_text())
    native = [r for r in archived["cases"]
              if r["split"] == "holdout" and r["method"] == "blender_native"]
    native_reference = dict(passed=sum(r["status"] == "passed" for r in native),
                            total=len(native), blender=archived["blender"],
                            source="R4 archived; not rerun in R5")
    totals = dict(r4_seen_loft=summary(development[4:], "radial_loft_3cuts"),
                  r4_all_development=summary(development, "radial_loft_3cuts"),
                  r4_archived_native=native_reference,
                  fresh_holdout_loft=summary(holdout, "radial_loft_3cuts"),
                  fresh_holdout_phase=summary(holdout, "phase"))
    hashes = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
              for p in ("cbdk_geometry/radial_loft.py", "cycles/r5/fixtures.py",
                        "cycles/r5/run.py", "cycles/r4/results/blender443.json")}
    return dict(cycle="R5", synthetic_only=True, blender="not_run_in_r5",
                python=sys.version.split()[0], numpy=np.__version__, cgal=version("cgal"),
                source_sha256=hashes, cases=rows, totals=totals,
                holdout_blender_native_available=False, approved=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    opts = parser.parse_args()
    result = run()
    path = Path(opts.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as dest:
        json.dump(result, dest, indent=2, ensure_ascii=False)
    print("TOTALS", json.dumps(result["totals"], ensure_ascii=False), flush=True)
    if any(r["status"] == "oracle_unavailable" for r in result["cases"]):
        raise SystemExit("independent oracle unavailable: research run is invalid")
