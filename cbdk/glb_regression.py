"""Orchestrate reference/candidate Blender GLB previews and compare them."""
from __future__ import annotations

from pathlib import Path

from .glb_compare import write_scene_comparison
from .glb_inspector import write_glb_inspection
from .glb_render import render_glb_preview


def run_glb_regression(
    blender: str | Path,
    reference: str | Path,
    candidate: str | Path,
    output_dir: str | Path,
    *,
    resolution: int = 384,
    timeout: int = 180,
    profile: str = "shape",
    dimension_rel_tol: float = 0.05,
    center_rel_tol: float = 0.03,
    scene_rel_tol: float = 0.05,
) -> dict:
    root = Path(output_dir)
    ref_dir = root / "reference"
    cand_dir = root / "candidate"
    ref_dir.mkdir(parents=True, exist_ok=True)
    cand_dir.mkdir(parents=True, exist_ok=True)

    write_glb_inspection(reference, ref_dir / "structure.json")
    write_glb_inspection(candidate, cand_dir / "structure.json")
    render_glb_preview(blender, reference, ref_dir, resolution=resolution, timeout=timeout)
    render_glb_preview(blender, candidate, cand_dir, resolution=resolution, timeout=timeout)

    comparison_path = root / "comparison.json"
    report = write_scene_comparison(
        ref_dir / "scene_metadata.json",
        cand_dir / "scene_metadata.json",
        comparison_path,
        profile=profile,
        dimension_rel_tol=dimension_rel_tol,
        center_rel_tol=center_rel_tol,
        scene_rel_tol=scene_rel_tol,
    )
    return {
        "kind": "cbdk_glb_regression",
        "passed": report["passed"],
        "profile": profile,
        "reference_preview": str(ref_dir),
        "candidate_preview": str(cand_dir),
        "comparison": str(comparison_path),
        "summary": report["summary"],
    }
