"""R12K: native qualification of the frozen R12J candidate meshes.
Reuse the unchanged R10E native evaluator and positive/negative controls.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import native_blender as native
from pattern_coverage import PLAN

SOURCE = Path("results/pattern_bridge")
DEST = Path("results/native_pattern_bridge")

def main():
    source_path = SOURCE / "report.json"
    raw = source_path.read_bytes()
    source = json.loads(raw)
    names = tuple(spec[0] for spec in PLAN)
    cases = source["cases"]
    if (not source["complete"] or not source["fixture_gate"]
            or len(cases) != len(names)
            or {c["name"] for c in cases if c["passed"]} != set(names)):
        raise ValueError("R12J source gate not satisfied")
    DEST.mkdir(parents=True, exist_ok=True)
    native.SOURCE, native.DEST = SOURCE, DEST
    controls = native.controls()
    results = []
    for name in names:
        try:
            result = native.run_case(name + "_candidate")
            result["name"] = name
            results.append(result)
        except Exception as exc:
            results.append(dict(name=name, error=repr(exc), passed=False,
                                surface_gate=False, shell_gate=False,
                                reopen_gate=False))
    grid_gate = all(c["grid_pass"] for c in controls)
    report = dict(complete=True, source_stage="R12J",
                  source_report_sha256=hashlib.sha256(raw).hexdigest(),
                  blender_version=bpy.app.version_string,
                  thickness=native.THICKNESS, cases=results, controls=controls,
                  grid_control_gate=grid_gate,
                  bvh_control_gate=all(c["bvh_pass"] for c in controls),
                  surface_gate=grid_gate and all(c["surface_gate"] for c in results),
                  shell_gate=grid_gate and all(c["shell_gate"] for c in results),
                  reopen_gate=all(c["reopen_gate"] for c in results),
                  fixture_gate=grid_gate and all(c["passed"] for c in results),
                  global_intersection_verified=False,
                  anatomical_fit_verified=False, visual_review_required=True)
    (DEST / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print("PHASE213NATIVEPATTERNBRIDGE_SUMMARY", json.dumps(report, allow_nan=False))
    # A negative research gate is an explicit failure, not a green CI claim.
    if not report["fixture_gate"]:
        raise RuntimeError("R12K native qualification gate failed; inspect saved evidence")

if __name__ == "__main__":
    main()
