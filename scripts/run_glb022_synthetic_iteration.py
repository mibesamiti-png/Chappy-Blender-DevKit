"""Execute the fixed GLB-022 MVP loop with trusted CBDK synthetic Blender code.

Only the source-controlled Blender fixture script is run, never user addons.
Fixed sequence: narrow baseline -> unrelated-ball placebo (reject) ->
known reference socket restoration (accept); stop on sampled zero errors.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cbdk.glb_diff_visualize import run_glb_diff_visualize
from cbdk.glb_synthetic_iteration import (
    BASELINE, CANDIDATES, _decision, _score, _safe_rows,
    build_synthetic_iteration_history, write_iteration_history,
)
from cbdk.glb_synthetic_multi import (
    CANDIDATES as MULTI_CANDIDATES,
    build_multi_iteration_history, write_multi_iteration_history,
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(blender, output, *, protocol="basic"):
    if protocol not in ("basic", "cross_part"):
        raise ValueError("Only the two CBDK-owned synthetic protocols are allowed")
    trial_ids = CANDIDATES if protocol == "basic" else MULTI_CANDIDATES
    trusted_script = REPO / "scripts/blender_make_glb_joint_mvp_fixtures.py"
    if trusted_script.is_symlink() or not trusted_script.is_file():
        raise ValueError("Missing CBDK-owned fixture generator")
    executable = Path(blender).resolve()
    if not executable.is_file():
        raise ValueError("Explicit trusted Blender executable required")
    root = Path(output).absolute()
    # CI output only; do not accept arbitrary user directories or existing
    # data. This stage never consumes private input GLBs or addon Python.
    allowed_parent = (REPO / "reports" / "ci").resolve()
    if (root.parent.resolve() != allowed_parent or root.exists()
            or root.is_symlink()):
        raise ValueError("Synthetic iteration must create a new reports/ci folder")
    root.mkdir(parents=True, exist_ok=False)
    candidates = root / "synthetic_inputs"
    candidates.mkdir()
    before_script_hash = _sha256(trusted_script)
    glb_hashes = {}

    def generate(kind):
        if kind not in ("reference", BASELINE, *trial_ids):
            raise ValueError("Non-allowlisted generator condition")
        folder = candidates / kind
        if folder.exists() or folder.is_symlink():
            raise FileExistsError("Synthetic condition already generated")
        cmd = [
            str(executable), "--background", "--factory-startup",
            "--disable-autoexec", "--python-exit-code", "7",
            "--python", str(trusted_script), "--",
            str(folder), "--single", kind,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True,
                                encoding="utf-8", errors="replace",
                                timeout=180, check=False)
        if result.returncode or result.stdout.count("CBDK_JOINT_MVP_FIXTURES_PASS") != 1:
            raise RuntimeError("Trusted CBDK fixture regeneration failed")
        target = folder / (kind + ".glb")
        if target.is_symlink() or not target.is_file() or target.stat().st_size < 100:
            raise RuntimeError("Missing synthetic generated GLB")
        glb_hashes[target] = _sha256(target)
        return target

    reference = generate("reference")
    baseline = generate(BASELINE)
    reports = {
        BASELINE: run_glb_diff_visualize(
            str(executable), reference, baseline, root / "review_narrow",
            timeout=180,
        )
    }
    current = BASELINE
    executed = 0
    for kind in trial_ids:
        candidate = generate(kind)
        report = run_glb_diff_visualize(
            str(executable), reference, candidate,
            root / ("review_" + kind), timeout=180,
        )
        reports[kind] = report
        accepted, _ = _decision(_score(_safe_rows(reports[current])),
                                _score(_safe_rows(report)))
        executed += 1
        if accepted:
            current = kind
        score = _score(_safe_rows(reports[current]))
        if (score["socket_sampled_affected_faces"] == 0
                and score["other_parts_sampled_affected_faces"] == 0):
            break
    if (executed != len(trial_ids)
            or set(reports) != set((BASELINE, *trial_ids))
            or current != "identical"):
        raise ValueError("Fixed allowlisted synthetic protocol did not converge")
    history = (build_synthetic_iteration_history(reports)
               if protocol == "basic" else
               build_multi_iteration_history(reports))
    if (before_script_hash != _sha256(trusted_script)
            or any(_sha256(path) != sha for path, sha in glb_hashes.items())):
        raise ValueError("Source-controlled generator or generated inputs changed")
    paths = (write_iteration_history(history, root)
             if protocol == "basic" else
             write_multi_iteration_history(history, root))
    if not all(p.is_file() for p in paths):
        raise ValueError("Missing local iteration evidence")
    print("CBDK_GLB022_SYNTHETIC_ITERATION_PASS")
    if protocol == "basic":
        print("Two real regenerated comparisons: unrelated edit rejected, known restoration accepted")
    else:
        print("CBDK_GLB022_MULTI_SYNTHETIC_PASS")
        print("Three fresh candidates: no improvement rejected, cross-part regression rejected, restore accepted")
    print("Stopped on sampled zero; sources unchanged; real addon validation unclaimed")
    return history


def main(argv=None):
    parser = argparse.ArgumentParser(description="CBDK-only GLB-022 synthetic iteration CI")
    parser.add_argument("--blender", required=True, help="CI-verified Blender executable")
    parser.add_argument("--output", default="reports/ci/glb022_iteration",
                        help="New synthetic CI folder under reports/ci only")
    parser.add_argument("--protocol", choices=("basic", "cross_part"),
                        default="basic", help="CBDK-owned fixed synthetic protocol")
    args = parser.parse_args(argv)
    run(args.blender, args.output, protocol=args.protocol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
