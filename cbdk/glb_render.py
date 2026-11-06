"""Launch the trusted CBDK GLB renderer inside a supplied Blender executable."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess


class GLBRenderError(ValueError):
    pass


EXPECTED_SCENE_VIEWS = {
    "front.png", "back.png", "right.png", "left.png",
    "top.png", "bottom.png", "iso.png",
}


def _safe_output_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\x00" in relative:
        raise GLBRenderError("Blender GLB preview returned an invalid output path")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise GLBRenderError("Blender GLB preview attempted a path escape")
    resolved_root = root.resolve()
    resolved = (root / candidate).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise GLBRenderError("Blender GLB preview attempted a path escape")
    return resolved


def render_glb_preview(blender: str | Path, source: str | Path, output_dir: str | Path,
                       *, resolution: int = 768, timeout: int = 180) -> dict:
    blender_path = Path(blender)
    source_path = Path(source)
    target = Path(output_dir)
    if not blender_path.is_file():
        raise GLBRenderError(f"Blender executable not found: {blender_path}")
    if not source_path.is_file() or source_path.suffix.lower() != ".glb":
        raise GLBRenderError("Input must be an existing .glb file")
    if not 256 <= resolution <= 2048:
        raise GLBRenderError("resolution must be between 256 and 2048")
    if not 10 <= timeout <= 1800:
        raise GLBRenderError("timeout must be between 10 and 1800 seconds")

    script = Path(__file__).resolve().parent.parent / "scripts" / "blender_glb_render.py"
    if not script.is_file():
        raise GLBRenderError(f"Trusted Blender renderer missing: {script}")
    target.mkdir(parents=True, exist_ok=True)
    command = [
        str(blender_path), "--background", "--factory-startup", "--python-exit-code", "7",
        "--python", str(script), "--", str(source_path.resolve()), str(target.resolve()), str(resolution),
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GLBRenderError("Blender GLB preview timed out") from exc
    except OSError as exc:
        raise GLBRenderError(f"Could not launch Blender: {exc}") from exc

    marker = "CBDK_GLB_RENDER_PASS "
    payloads = [line.split(marker, 1)[1] for line in result.stdout.splitlines() if marker in line]
    if result.returncode != 0 or len(payloads) != 1:
        tail = "\n".join((result.stdout + "\n" + result.stderr).splitlines()[-40:])
        raise GLBRenderError("Blender GLB preview failed" + (f"\n{tail}" if tail else ""))
    try:
        payload = json.loads(payloads[0])
    except json.JSONDecodeError as exc:
        raise GLBRenderError("Blender GLB preview returned invalid JSON") from exc

    required = {"metadata", "views", "object_thumbnails", "blender_version", "object_count"}
    if not isinstance(payload, dict) or not required <= set(payload):
        raise GLBRenderError("Blender GLB preview result is incomplete")
    if payload["metadata"] != "scene_metadata.json":
        raise GLBRenderError("Unexpected GLB preview metadata path")
    if not isinstance(payload["views"], list) or set(payload["views"]) != EXPECTED_SCENE_VIEWS:
        raise GLBRenderError("Blender GLB preview did not return the complete seven-view set")
    if len(payload["views"]) != len(EXPECTED_SCENE_VIEWS):
        raise GLBRenderError("Blender GLB preview returned duplicate scene views")
    if not isinstance(payload["object_count"], int) or isinstance(payload["object_count"], bool) or payload["object_count"] < 1:
        raise GLBRenderError("Blender GLB preview returned an invalid object count")
    if not isinstance(payload["object_thumbnails"], list):
        raise GLBRenderError("Blender GLB preview returned invalid object thumbnails")

    metadata_path = _safe_output_path(target, payload["metadata"])
    if not metadata_path.is_file():
        raise GLBRenderError("Blender did not write scene_metadata.json")

    for view in payload["views"]:
        path = _safe_output_path(target, view)
        if path.suffix.lower() != ".png" or not path.is_file():
            raise GLBRenderError(f"Missing rendered view: {view!r}")

    thumb_files = set()
    for row in payload["object_thumbnails"]:
        if not isinstance(row, dict) or set(row) != {"object", "file"}:
            raise GLBRenderError("Invalid object thumbnail record")
        if not isinstance(row["object"], str) or not row["object"]:
            raise GLBRenderError("Invalid object thumbnail name")
        if row["file"] in thumb_files:
            raise GLBRenderError("Duplicate object thumbnail path")
        thumb_files.add(row["file"])
        path = _safe_output_path(target, row["file"])
        if path.suffix.lower() != ".png" or not path.is_file():
            raise GLBRenderError(f"Missing object thumbnail: {row['file']!r}")

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GLBRenderError("Invalid scene_metadata.json") from exc
    if not isinstance(metadata, dict) or metadata.get("kind") != "cbdk_glb_blender_scene_metadata":
        raise GLBRenderError("Unexpected scene metadata kind")
    if metadata.get("object_count") != payload["object_count"]:
        raise GLBRenderError("Scene metadata object count does not match Blender payload")
    if metadata.get("views") != payload["views"]:
        raise GLBRenderError("Scene metadata views do not match Blender payload")
    if metadata.get("object_thumbnails") != payload["object_thumbnails"]:
        raise GLBRenderError("Scene metadata thumbnails do not match Blender payload")
    return payload
