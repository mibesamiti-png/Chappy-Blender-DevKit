"""Optional Blender-free GLB geometry preview using trimesh + matplotlib.

This is a fallback for environments where Blender cannot run. It is deliberately
lower fidelity than the trusted Blender renderer and must never be labelled as a
Blender-exact preview. External URI references are rejected before optional
third-party loaders are invoked.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

from .glb_inspector import inspect_glb


class GLBQuickRenderError(ValueError):
    pass


EXPECTED_QUICK_VIEWS = {
    "front.png", "back.png", "right.png", "left.png",
    "top.png", "bottom.png", "iso.png",
}
MAX_QUICK_VERTICES = 500_000
MAX_QUICK_FACES = 250_000
MAX_OBJECT_THUMBNAILS = 32


def _load_optional_dependencies():
    try:
        np = importlib.import_module("numpy")
        trimesh = importlib.import_module("trimesh")
        matplotlib = importlib.import_module("matplotlib")
        matplotlib.use("Agg", force=True)
        plt = importlib.import_module("matplotlib.pyplot")
        art3d = importlib.import_module("mpl_toolkits.mplot3d.art3d")
    except (ImportError, ModuleNotFoundError) as exc:
        raise GLBQuickRenderError(
            'Quick preview needs optional dependencies: pip install -e ".[glb-quick]"'
        ) from exc
    return np, trimesh, plt, art3d.Poly3DCollection


def _view_definitions() -> dict[str, tuple[float, float]]:
    # Matplotlib elevation/azimuth. These are evidence views, not a promise of
    # Blender viewport naming conventions.
    return {
        "front.png": (0.0, -90.0),
        "back.png": (0.0, 90.0),
        "right.png": (0.0, 0.0),
        "left.png": (0.0, 180.0),
        "top.png": (90.0, -90.0),
        "bottom.png": (-90.0, -90.0),
        "iso.png": (28.0, -45.0),
    }


def _validate_budget(rows: list[dict[str, Any]]) -> tuple[int, int]:
    total_vertices = sum(int(row["vertex_count"]) for row in rows)
    total_faces = sum(int(row["face_count"]) for row in rows)
    if total_vertices > MAX_QUICK_VERTICES:
        raise GLBQuickRenderError(
            f"Quick preview vertex limit exceeded: {total_vertices} > {MAX_QUICK_VERTICES}"
        )
    if total_faces > MAX_QUICK_FACES:
        raise GLBQuickRenderError(
            f"Quick preview face limit exceeded: {total_faces} > {MAX_QUICK_FACES}"
        )
    return total_vertices, total_faces


def _scene_meshes(scene, np):
    rows = []
    for node_name in sorted(scene.graph.nodes_geometry, key=str):
        transform, geometry_name = scene.graph.get(node_name)
        geometry = scene.geometry[geometry_name]
        vertices = np.asarray(geometry.vertices)
        faces = np.asarray(geometry.faces)
        if vertices.ndim != 2 or vertices.shape[1] != 3:
            raise GLBQuickRenderError(f"Unsupported vertex shape for {node_name!r}")
        if faces.ndim != 2 or faces.shape[1] != 3:
            raise GLBQuickRenderError(f"Quick preview requires triangular faces: {node_name!r}")
        world_vertices = scene.geometry[geometry_name].vertices
        world_vertices = np.asarray(world_vertices)
        # The node transform is applied later without mutating source geometry.
        rows.append({
            "object": str(node_name),
            "mesh": str(geometry_name),
            "transform": np.asarray(transform, dtype=float),
            "vertices_local": world_vertices,
            "faces": faces,
            "vertex_count": int(len(vertices)),
            "face_count": int(len(faces)),
        })
    return rows


def _apply_transforms(rows, trimesh, np):
    for row in rows:
        row["vertices"] = trimesh.transform_points(
            np.asarray(row.pop("vertices_local"), dtype=float),
            row["transform"],
        )
    return rows


def _bounds(rows, np):
    all_vertices = np.vstack([row["vertices"] for row in rows])
    minimum = all_vertices.min(axis=0)
    maximum = all_vertices.max(axis=0)
    center = (minimum + maximum) * 0.5
    extent = maximum - minimum
    radius = max(float(extent.max()) * 0.5, 1e-6) * 1.12
    return minimum, maximum, center, extent, radius


def _render(rows, output: Path, *, elev: float, azim: float, resolution: int,
            np, plt, Poly3DCollection):
    _minimum, _maximum, center, _extent, radius = _bounds(rows, np)
    dpi = 100
    fig = plt.figure(figsize=(resolution / dpi, resolution / dpi), dpi=dpi)
    ax = fig.add_subplot(111, projection="3d")
    background = (0.055, 0.06, 0.07)

    for index, row in enumerate(rows):
        triangles = row["vertices"][row["faces"]]
        shade = max(0.28, min(0.78, 0.54 + 0.07 * ((index % 5) - 2)))
        collection = Poly3DCollection(triangles, linewidths=0.0, alpha=1.0)
        collection.set_facecolor((shade, shade, shade, 1.0))
        collection.set_edgecolor("none")
        ax.add_collection3d(collection)

    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_proj_type("ortho")
    ax.set_axis_off()
    fig.patch.set_facecolor(background)
    ax.set_facecolor(background)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(output, facecolor=fig.get_facecolor(), dpi=dpi)
    plt.close(fig)


def quick_render_glb(source: str | Path, output_dir: str | Path,
                     *, resolution: int = 640) -> dict:
    source_path = Path(source)
    target = Path(output_dir)
    if not source_path.is_file() or source_path.suffix.lower() != ".glb":
        raise GLBQuickRenderError("Input must be an existing .glb file")
    if not 256 <= resolution <= 1600:
        raise GLBQuickRenderError("resolution must be between 256 and 1600")

    static_report = inspect_glb(source_path)
    external = static_report.get("external_uris", [])
    if external:
        raise GLBQuickRenderError(
            "Quick preview refuses GLB files with external URI references"
        )

    np, trimesh, plt, Poly3DCollection = _load_optional_dependencies()
    try:
        scene = trimesh.load(
            source_path,
            force="scene",
            process=False,
            skip_materials=True,
        )
    except Exception as exc:
        raise GLBQuickRenderError(f"trimesh could not load GLB: {exc}") from exc

    rows = _scene_meshes(scene, np)
    if not rows:
        raise GLBQuickRenderError("GLB contains no triangular mesh geometry")
    _validate_budget(rows)
    rows = _apply_transforms(rows, trimesh, np)

    target.mkdir(parents=True, exist_ok=True)
    views = _view_definitions()
    for filename, (elev, azim) in views.items():
        _render(
            rows, target / filename,
            elev=elev, azim=azim, resolution=resolution,
            np=np, plt=plt, Poly3DCollection=Poly3DCollection,
        )

    thumb_dir = target / "objects"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumbnails = []
    for index, row in enumerate(rows[:MAX_OBJECT_THUMBNAILS]):
        filename = f"objects/{index:03d}.png"
        _render(
            [row], target / filename,
            elev=28.0, azim=-45.0, resolution=min(resolution, 512),
            np=np, plt=plt, Poly3DCollection=Poly3DCollection,
        )
        thumbnails.append({"object": row["object"], "mesh": row["mesh"], "file": filename})

    minimum, maximum, center, extent, _radius = _bounds(rows, np)
    metadata = {
        "schema_version": 1,
        "kind": "cbdk_glb_quick_scene_metadata",
        "source_name": source_path.name,
        "renderer": "trimesh+matplotlib",
        "fidelity": "fallback_not_blender",
        "object_count": len(rows),
        "total_vertices": sum(row["vertex_count"] for row in rows),
        "total_faces": sum(row["face_count"] for row in rows),
        "bounds": {
            "min": [float(v) for v in minimum],
            "max": [float(v) for v in maximum],
            "center": [float(v) for v in center],
            "size": [float(v) for v in extent],
        },
        "objects": [{
            "object": row["object"],
            "mesh": row["mesh"],
            "vertex_count": row["vertex_count"],
            "face_count": row["face_count"],
        } for row in rows],
        "views": list(views),
        "object_thumbnails": thumbnails,
        "thumbnail_limit": MAX_OBJECT_THUMBNAILS,
        "thumbnail_truncated": len(rows) > MAX_OBJECT_THUMBNAILS,
        "safety": {
            "external_uri_references_rejected": True,
            "materials_skipped": True,
            "source_glb_modified": False,
            "blender_used": False,
        },
    }
    metadata_path = target / "quick_scene_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "kind": "cbdk_glb_quick_preview",
        "metadata": str(metadata_path),
        "views": [str(target / name) for name in views],
        "object_thumbnails": [
            {"object": row["object"], "mesh": row["mesh"], "file": str(target / row["file"])}
            for row in thumbnails
        ],
        "object_count": len(rows),
        "fidelity": "fallback_not_blender",
    }
