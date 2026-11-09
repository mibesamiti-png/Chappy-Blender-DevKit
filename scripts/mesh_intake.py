"""Local-only inventory of untrusted mesh inputs.

Does not parse geometry, import bpy, load a .blend, extract archives or send data.
The manifest intentionally stays in an ignored private directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

MESH_SUFFIXES = frozenset({
    ".blend", ".glb", ".gltf", ".obj", ".stl", ".fbx", ".ply", ".3mf"
})
IMAGE_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif",
    ".heic", ".avif"
})
ALLOWED_SUFFIXES = MESH_SUFFIXES | IMAGE_SUFFIXES
ROLES = ("unassigned", "reference", "candidate", "edge_case")
ASSET_STATES = ("work_in_progress", "declared_complete", "declared_reference")
MAX_FILE_BYTES = 4 * 1024 * 1024 * 1024
SCHEMA = "cbdk_private_mesh_intake_v2"


def _digest_regular_file(path: Path) -> tuple[str, int] | None:
    """Read only bytes from a regular file; decline links and oversized files."""
    if path.is_symlink():
        return None
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not (0 < info.st_size <= MAX_FILE_BYTES):
            return None
        digest = hashlib.sha256()
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
        if stream.tell() != info.st_size:
            raise ValueError("Input changed while reading")
        return digest.hexdigest(), info.st_size


def collect_meshes(
    root: Path, role: str = "unassigned", state: str = "work_in_progress"
) -> dict:
    """Inventory mesh/image bytes privately; assume unfinished unless explicitly labeled.

    A role such as "reference" describes usage, never correctness or completion.
    """
    if role not in ROLES:
        raise ValueError("Unsupported intake role")
    if state not in ASSET_STATES:
        raise ValueError("Unsupported asset state")
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Input must be an existing non-symlink directory")
    entries: list[dict] = []
    skipped = 0
    for folder, subdirs, filenames in os.walk(root, followlinks=False):
        base = Path(folder)
        subdirs[:] = sorted(d for d in subdirs if not (base / d).is_symlink())
        for filename in sorted(filenames):
            path = base / filename
            if path.suffix.lower() not in ALLOWED_SUFFIXES or path.is_symlink():
                skipped += 1
                continue
            try:
                result = _digest_regular_file(path)
            except (OSError, ValueError):
                result = None
            if result is None:
                skipped += 1
                continue
            digest, byte_size = result
            asset_kind = "mesh" if path.suffix.lower() in MESH_SUFFIXES else "image"
            asset_id = ("MESH-" if asset_kind == "mesh" else "IMG-") + digest[:16].upper()
            entry = {
                "asset_id": asset_id,
                "asset_kind": asset_kind,
                "relative_path": path.relative_to(root).as_posix(),
                "format": path.suffix.lower(),
                "byte_size": byte_size,
                "sha256": digest,
                "role": role,
                "asset_state": state,
                "state_basis": "default_unfinished" if state == "work_in_progress"
                               else "explicit_manual_label",
                "reference_truth": "user_declared" if state == "declared_reference"
                                   else "not_established",
                "geometry_validation": "not_run",
                "image_interpretation": "not_run",
                "usage_approval": "pending",
            }
            if asset_kind == "mesh":
                entry["model_id"] = asset_id  # compatibility with private v1 consumers
            entries.append(entry)
    entries.sort(key=lambda e: e["relative_path"])
    return {
        "schema": SCHEMA,
        "scope": "private_local_only",
        "source_files_executed": False,
        "geometry_validated": False,
        "items": entries,
        "counts": {"accepted": len(entries), "skipped": skipped},
    }


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="Inventory private CBDK meshes and images")
    parser.add_argument("--role", choices=ROLES, default="unassigned")
    parser.add_argument("--status", choices=ASSET_STATES, default="work_in_progress",
                        help="Change only when the user has explicitly declared the state")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    input_root = repo_root / "test_meshes_private"
    output_root = repo_root / "reports" / "private_mesh_intake"
    if input_root.is_symlink() or output_root.is_symlink():
        parser.error("Private input/output directories cannot be symlinks")
    input_root.mkdir(exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)
    if input_root.resolve().is_relative_to(output_root.resolve()) or output_root.resolve().is_relative_to(input_root.resolve()):
        parser.error("Private input/output directories overlap")
    report = collect_meshes(input_root, role=args.role, state=args.status)
    output = output_root / "manifest.json"
    if output.is_symlink():
        parser.error("Manifest output cannot be a symlink")
    temporary = output_root / "manifest.json.tmp"
    if temporary.is_symlink():
        parser.error("Temporary manifest cannot be a symlink")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    print("Private inventory saved. Accepted:", report["counts"]["accepted"],
          "Skipped:", report["counts"]["skipped"])
    print("Mesh/image content validation: NOT RUN; sharing permission: NOT VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
