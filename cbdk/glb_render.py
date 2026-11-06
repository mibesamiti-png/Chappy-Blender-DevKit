"""Launch the trusted CBDK GLB renderer inside a supplied Blender executable."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess


class GLBRenderError(ValueError):
    pass


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
    command = [str(blender_path), "--background", "--factory-startup", "--python-exit-code", "7",
               "--python", str(script), "--", str(source_path.resolve()), str(target.resolve()), str(resolution)]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False)
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
    required = {"metadata", "views", "blender_version", "object_count"}
    if not isinstance(payload, dict) or not required <= set(payload):
        raise GLBRenderError("Blender GLB preview result is incomplete")
    if not (target / "scene_metadata.json").is_file():
        raise GLBRenderError("Blender did not write scene_metadata.json")
    for view in payload["views"]:
        if not isinstance(view, str) or not (target / view).is_file():
            raise GLBRenderError(f"Missing rendered view: {view!r}")
    return payload
