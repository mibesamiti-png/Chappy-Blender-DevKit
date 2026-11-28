"""Reproducible *observational* wall-clock timings for trusted surface fixtures.

Use only repository-authored synthetic meshes in CI. The measured end-to-end
search includes deterministic BVH construction and surface sampling. Results
depend on CPU load, interpreter, and runners; never gate CI on a speed ratio.
"""
from __future__ import annotations

import math
import statistics
import time

from .glb_surface_distance import (
    MAX_TRIANGLES, SurfaceDistanceError, _directed, _validated_triangles,
)

MAX_BRUTE_TRIANGLE_PAIRS = 4096
MAX_REPEATS = 5


def benchmark_surface_search(reference: list, candidate: list, *,
                             repeats: int = 3,
                             include_brute_force: bool = True) -> dict:
    """Benchmark identical input with/without BVH (small), or BVH alone (large).

    The brute-force option is deliberately disabled for large inputs to keep CI
    responsive. Do not treat timing ratios as guarantees on other machines.
    """
    if isinstance(repeats, bool) or not isinstance(repeats, int) or not 1 <= repeats <= MAX_REPEATS:
        raise SurfaceDistanceError("repeats must be an integer from 1 to 5")
    if not isinstance(include_brute_force, bool):
        raise SurfaceDistanceError("include_brute_force must be boolean")
    ref = _validated_triangles(reference, "reference")
    cand = _validated_triangles(candidate, "candidate")
    if include_brute_force and len(ref) * len(cand) > MAX_BRUTE_TRIANGLE_PAIRS:
        raise SurfaceDistanceError("Full brute-force timing is restricted to small trusted inputs")

    def trial(accelerated):
        start = time.perf_counter_ns()
        result = _directed(ref, cand, accelerated=accelerated)
        elapsed_ns = time.perf_counter_ns() - start
        if elapsed_ns < 0:
            raise SurfaceDistanceError("Invalid monotonic clock reading")
        return result, elapsed_ns

    # Ensure that imports/first-use effects are not part of recorded samples.
    warm_fast, _ = trial(True)
    warm_brute = trial(False)[0] if include_brute_force else None
    timings = {"bvh": []}
    if include_brute_force:
        timings["brute_force"] = []
    expected = {"bvh": warm_fast}
    if warm_brute is not None:
        expected["brute_force"] = warm_brute

    for attempt in range(repeats):
        # Alternate order to reduce systematic clock/runner drift.
        methods = (("brute_force", False), ("bvh", True)) if attempt % 2 else (
            ("bvh", True), ("brute_force", False))
        for key, accelerate in methods:
            if key not in timings:
                continue
            result, elapsed_ns = trial(accelerate)
            if result != expected[key]:
                raise SurfaceDistanceError("Nondeterministic geometry score during benchmarking")
            timings[key].append(elapsed_ns)

    if warm_brute is not None:
        for field in ("mean", "sampled_max", "sample_count"):
            if warm_fast[field] != warm_brute[field]:
                raise SurfaceDistanceError("BVH and brute force geometry scores differ")

    summarized = {}
    for key, values in timings.items():
        median_ms = statistics.median(values) / 1_000_000.0
        if not math.isfinite(median_ms):
            raise SurfaceDistanceError("Nonfinite measured duration")
        summarized[key] = {
            "median_elapsed_ms": round(median_ms, 6),
            "min_elapsed_ms": round(min(values) / 1_000_000.0, 6),
            "max_elapsed_ms": round(max(values) / 1_000_000.0, 6),
            "repeats": repeats,
            "triangle_distance_evaluations": expected[key]["triangle_distance_evaluations"],
        }

    speedup = None
    if "brute_force" in summarized and summarized["bvh"]["median_elapsed_ms"] > 0:
        speedup = round(
            summarized["brute_force"]["median_elapsed_ms"] /
            summarized["bvh"]["median_elapsed_ms"], 3)
        if not math.isfinite(speedup):
            raise SurfaceDistanceError("Nonfinite observed speed ratio")

    return {
        "schema_version": 1,
        "kind": "cbdk_trusted_surface_search_benchmark",
        "status": "observational_only",
        "reference_triangles": len(ref),
        "candidate_triangles": len(cand),
        "triangle_limit": MAX_TRIANGLES,
        "brute_force_pair_limit": MAX_BRUTE_TRIANGLE_PAIRS,
        "benchmarks": summarized,
        "observed_brute_vs_bvh_median_ratio": speedup,
        "scores_agree_with_brute_force": warm_brute is not None,
        "sampled_mean": warm_fast["mean"],
        "sampled_max": warm_fast["sampled_max"],
        "scope": "end_to_end_single_direction_including_bvh_build_and_sampling",
        "elapsed_time_unit": "milliseconds",
        "relative_timings_portable": False,
        "performance_regression_gate": False,
        "safety": {
            "executes_user_addon": False,
            "publishes_private_mesh": False,
            "auto_applies_parameters": False,
        },
    }
