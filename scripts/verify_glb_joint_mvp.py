"""Assert GLB-020 review-only MVP acceptance on CBDK synthetic joint fixtures.

All fixture inputs/HTML are synthetic and local. Never print source vertices,
private paths, addon source code or untrusted model metadata.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys


def verify(root):
    root = Path(root)
    reports = {
        mode: json.loads((root / ("review_" + mode) / "review.json").read_text(
            encoding="utf-8"))
        for mode in ("identical", "narrow", "shifted", "uncapped")
    }
    reference_part_sizes = [8, 24, 96]  # Ball, Shaft, Socket; 12-sided ring
    for mode, report in reports.items():
        assert report["kind"] == "cbdk_glb_diff_visualization", mode
        assert report["status"] == "review_only", mode
        assert report["auto_apply"] is False, mode
        assert report["sampled_only"] is True, mode
        assert report["complete_surface_equivalence_proven"] is False, mode
        assert report["cross_file_part_identity_proven"] is False, mode
        assert report["viewer_local_only"] is True, mode
        assert report["viewer_contains_derived_geometry"] is True, mode
        assert report["safety"] == {
            "executes_addon_code": False,
            "uploads_private_glb": False,
            "saves_raw_mesh_vertices_in_json": False,
            "changes_source_glbs": False,
        }, mode
        assert len(report["parts"]["reference"]) == 3, mode
        assert len(report["parts"]["candidate"]) == 3, mode
        sizes = [r["triangle_count"] for r in report["parts"]["reference"]]
        assert sizes == reference_part_sizes, (mode, sizes)
        assert report["part_match_candidates"]["auto_apply"] is False, mode
        assert report["part_match_candidates"]["cross_file_part_identity_proven"] is False
        assert report["boundary_edge_audit"]["fully_watertight_proven"] is False
        assert report["boundary_edge_audit"]["hole_locations_verified"] is False
        assert report["sampling_sensitivity_audit"]["unobserved_regions_verified"] is False
        assert report["sampling_sensitivity_audit"]["complete_surface_equivalence_proven"] is False
        # Geometry-bearing artifacts stay within CI's local workspace; do not
        # upload them as artifacts, publish in JSON or dump their content in logs.
        folder = root / ("review_" + mode)
        for output in ("reference_diff.glb", "candidate_diff.glb",
                       "compare_viewer.html"):
            assert (folder / output).is_file(), (mode, output)
        text = json.dumps(report)
        for forbidden in ("CBDK_SYNTH_Ball", "CBDK_SYNTH_Socket",
                          "CBDK_SYNTH_Shaft", "reference.glb",
                          "narrow.glb", "shifted.glb", "uncapped.glb"):
            assert forbidden not in text, (mode, "source name leaked")
        html = (folder / "compare_viewer.html").read_text(encoding="utf-8")
        assert 'id="canvas-reference"' in html
        assert 'id="canvas-candidate"' in html
        assert "__CBDK_VIEWER_DATA__" not in html
        assert "connect-src 'none'" in html
        assert "CBDK_SYNTH_Ball" not in html
        assert "CBDK_SYNTH_Socket" not in html
        assert "CBDK_SYNTH_Shaft" not in html

    # Strict negative control: same synthetic joint, no sampled change.
    baseline = reports["identical"]
    for side in ("reference", "candidate"):
        assert baseline[side]["medium"] == 0, side
        assert baseline[side]["high"] == 0, side
        assert baseline["boundary_edge_audit"][side]["boundary_edges"] == 0, side
        assert baseline["boundary_edge_audit"][side]["nonmanifold_edge_incidence"] == 0
        assert baseline["sampling_sensitivity_audit"][side]["sensitive_faces"] == 0

    # A narrowed socket opening changes the inner cylindrical wall and top/bottom lip.
    narrow = reports["narrow"]
    for side in ("reference", "candidate"):
        socket = narrow["parts"][side][2]
        assert socket["high"] + socket["medium"] > 0, (side, "narrowed lip unnoticed")
        assert narrow["boundary_edge_audit"][side]["boundary_edges"] == 0
    assert narrow["parts"]["candidate"][2]["triangle_count"] == 96

    # Displace only the faceted ball: its sampled surface must change.
    shifted = reports["shifted"]
    assert shifted["parts"]["reference"][0]["high"] + shifted["parts"]["reference"][0]["medium"] > 0
    assert shifted["parts"]["candidate"][0]["high"] + shifted["parts"]["candidate"][0]["medium"] > 0
    assert shifted["parts"]["candidate"][0]["triangle_count"] == 8

    # Remove exactly one top-lip quad: open boundary warning and two fewer triangles.
    uncapped = reports["uncapped"]
    assert uncapped["parts"]["candidate"][2]["triangle_count"] == 94
    assert uncapped["boundary_edge_audit"]["reference"]["boundary_edges"] == 0
    assert uncapped["boundary_edge_audit"]["candidate"]["boundary_edges"] == 4
    assert uncapped["boundary_edge_audit"]["parts"]["candidate"][2]["observed_boundary"]
    assert uncapped["boundary_edge_audit"]["parts"]["candidate"][2]["topology_proven"] is False

    print("CBDK_GLB020_JOINT_MVP_PASS")
    print("identical / narrowed socket / shifted ball / missing lip: checked")
    print("review-only, aggregate-only JSON, no source mutation or identity claim")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Pass one temporary synthetic fixture output directory")
    verify(sys.argv[1])


if __name__ == "__main__":
    main()
