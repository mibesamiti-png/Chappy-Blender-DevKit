"""Verify two independent real synthetic runs plus a controlled failed run.

Timing/peak allocation measurements cover in-memory comparison only, excluding
Blender and disk loading. Sixteen-input load uses replicated synthetic evidence,
not sixteen independent Blender experiments. No speed thresholds are asserted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cbdk.glb_synthetic_run_compare import compare_run_reviews, write_run_comparison
from cbdk.glb_synthetic_run_review import read_run_review


def measure(reviews):
    if tracemalloc.is_tracing():
        raise ValueError("Benchmark requires its own tracing session")
    compare_run_reviews(reviews)
    milliseconds, peaks = [], []
    for _ in range(3):
        tracemalloc.start()
        try:
            start = time.perf_counter()
            result = compare_run_reviews(reviews)
            milliseconds.append((time.perf_counter() - start) * 1000)
            peaks.append(tracemalloc.get_traced_memory()[1])
        finally:
            tracemalloc.stop()
        assert result["comparison_available"] is True
    return {
        "input_count": len(reviews), "trials": 3, "python_version": sys.version.split()[0],
        "median_elapsed_ms": round(statistics.median(milliseconds), 6),
        "peak_python_allocated_bytes": max(peaks),
        "includes_disk_or_blender": False, "speedup_claimed": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="CBDK same-condition synthetic comparison CI")
    parser.add_argument("--first", required=True)
    parser.add_argument("--second", required=True)
    parser.add_argument("--failed", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).absolute()
    ci = (ROOT / "reports/ci").resolve()
    if output.parent.resolve() != ci or output.exists() or output.is_symlink():
        raise ValueError("Use a fresh reports/ci comparison directory")
    sources = [Path(value) for value in (args.first, args.second, args.failed)]
    if any(not path.resolve().is_relative_to(ci) for path in sources):
        raise ValueError("CI evidence must remain repo-local")
    first, second, failed = [read_run_review(path) for path in sources]
    result = compare_run_reviews([first, second, failed])
    assert result["eligible_runs"] == 2
    assert result["excluded_runs"] == 1
    assert result["rows"][1]["comparison_status"] == "no_meaningful_difference"
    assert result["rows"][2]["exclusion_reason"] == "run_failed"
    assert result["rows"][2]["sampled_max_delta_from_anchor"] is None
    assert all(not value for value in result["safety"].values())
    output.mkdir(parents=True, exist_ok=False)
    write_run_comparison(result, output)
    metrics = [measure([first, second]), measure([first, second] * 8)]
    metrics[0]["replicated_for_load_only"] = False
    metrics[1]["replicated_for_load_only"] = True
    with (output / "comparison_resource_observations.json").open("x", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print("CBDK_GLB023_SAME_CONDITION_REVIEW_PASS")
    print(json.dumps(metrics, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
