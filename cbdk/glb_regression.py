"""Orchestrate reference/candidate Blender GLB previews and compare them."""
from __future__ import annotations

from pathlib import Path

from .glb_compare import write_scene_comparison
from .glb_inspector import write_glb_inspection
from .glb_diagnose import diagnose_comparison, write_diagnosis_report
from .glb_repair_plan import build_repair_plan, write_repair_plan
from .glb_render import render_glb_preview
from .glb_surface_pipeline import run_glb_surface_review


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
    silhouette_iou_min: float = 0.90,
    surface_review: bool = False,
) -> dict:
    if not isinstance(surface_review, bool):
        raise ValueError("surface_review must be boolean")
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
        silhouette_iou_min=silhouette_iou_min,
    )
    diagnosis_path = root / "diagnosis.json"
    diagnosis = diagnose_comparison(report)
    write_diagnosis_report(diagnosis, diagnosis_path)
    repair_path = root / 'repair_plan.json'
    repair_plan = build_repair_plan(diagnosis)
    write_repair_plan(repair_plan, repair_path)
    surface = None
    surface_path = root / "surface_review.json"
    if surface_review:
        surface = run_glb_surface_review(
            blender, reference, candidate, surface_path, timeout=timeout,
        )
    return {
        "kind": "cbdk_glb_regression",
        "passed": report["passed"],
        "profile": profile,
        "reference_preview": str(ref_dir),
        "candidate_preview": str(cand_dir),
        "comparison": str(comparison_path),
        "diagnosis": str(diagnosis_path),
        "repair_plan": str(repair_path),
        "parameter_review_candidates": repair_plan["recommendation_count"],
        "summary": report["summary"],
        "diagnostic_hypotheses": diagnosis["hypothesis_count"],
        "surface_review": str(surface_path) if surface is not None else None,
        "surface_status": surface["status"] if surface else "not_requested",
        "surface_observation": (surface.get("surface_observation")
                                if surface else "not_measured"),
        "surface_does_not_auto_approve": True,
        "passed_is_metadata_only": True,
    }
