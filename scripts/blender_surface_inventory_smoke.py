"""Synthetic-only end-to-end inventory evidence; no user GLBs or addons.

Run in factory-startup Blender. Each case is exported, then reimported by the
trusted surface-review subprocess. Only aggregate assertions enter stdout.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cbdk.glb_surface_pipeline import run_glb_surface_review  # noqa: E402


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) != 1:
        raise ValueError("Expected one fresh reports/ci output directory")
    output = Path(args[0]).resolve()
    if not output.is_relative_to(ROOT / "reports" / "ci"):
        raise ValueError("Synthetic evidence must stay in reports/ci")
    output.mkdir(parents=True, exist_ok=False)
    cases = (
        ("unique", [1, 2], "review_only", [1, 2]),
        ("ambiguous", [1, 1], "review_only", []),
        ("truncated", [1] * 33, "review_only", []),
        ("over_limit_truncated", [17] * 33, "skipped", []),
    )
    for label, counts, status, candidates in cases:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        for index, count in enumerate(counts):
            vertices, faces = [], []
            for face in range(count):
                start = len(vertices)
                x, y = 3.0 * face, 3.0 * index
                vertices.extend(((x, y, 0), (x + 1, y, 0), (x, y + 1, 0)))
                faces.append((start, start + 1, start + 2))
            mesh = bpy.data.meshes.new("CBDK_Owned_Inventory")
            mesh.from_pydata(vertices, [], faces)
            mesh.update()
            obj = bpy.data.objects.new(f"CBDK_Test_{index:03d}", mesh)
            bpy.context.collection.objects.link(obj)
        source = output / (label + ".glb")
        bpy.ops.export_scene.gltf(filepath=str(source), export_format="GLB")
        before = hashlib.sha256(source.read_bytes()).digest()
        result = run_glb_surface_review(
            bpy.app.binary_path, source, source, output / (label + ".json"))
        assert hashlib.sha256(source.read_bytes()).digest() == before
        assert result["status"] == status
        for side in ("reference", "candidate"):
            assert result[side + "_triangles"] == sum(counts)
            assert result["part_inventory"][side + "_object_count"] == len(counts)
            assert result["part_inventory"][side + "_triangle_counts"] == sorted(
                counts, reverse=True)[:32]
        hints = result["part_count_hints"]
        assert hints["weak_candidate_triangle_counts"] == candidates
        assert hints["complete_inventories"] is (len(counts) <= 32)
        assert hints["correspondence_verified"] is False
        assert hints["auto_apply"] is False
        if status == "review_only":
            assert result["surface_observation"] == "no_difference_observed_at_samples"
        else:
            assert result["surface_observation"] == "not_measured"
            assert "fixed_surface" not in result
        print("CBDK inventory synthetic case passed: " + label)
    print("CBDK_SURFACE_INVENTORY_PASS")


if __name__ == "__main__":
    main()
