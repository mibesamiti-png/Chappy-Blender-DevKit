"""Build a local-only Blender add-on preview from an allowlisted CBDK recipe.

Never execute source code or merge user-supplied scanned add-ons. A catalog
entry is not permission or proof of runtime compatibility; unapproved code
requires an explicit, auditable preview opt-in, and release packaging is not
implemented here. This deliberately handles one reviewed, authored demo.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = "mesh_inspector"
PACKAGE_ID = "cbdk_mesh_inspector_preview"
PART_IDS = frozenset({"BLCTX-001", "BLCTX-002", "BME-001"})
SOURCES = {
    "parts/blender/context.py": "helpers/context.py",
    "parts/blender/edit_mesh.py": "helpers/edit_mesh.py",
}
README = """CBDK MESH INSPECTOR - DEVELOPMENT PREVIEW ONLY

This is a local test build, not an official release or Blender Extensions upload.
The three included CBDK-authored parts are NOT formally approved or license-cleared.
Only build and install in your own test environment; do not redistribute.

In Blender 4.4+, use Preferences > Add-ons > Install from Disk / Install
Legacy Add-on and choose the ZIP. Enable "CBDK Mesh Inspector Preview".
In the 3D View Sidebar > CBDK, click "Inspect Mesh Selection".
Object Mode: count selected meshes. Edit Mode: count selected V/E/F.
No mesh topology, current mode or selection is changed.

Disable this preview before installing a replacement build.
"""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _trusted_read(relative: str, *, root: Path) -> bytes:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or (root / relative).is_symlink():
        raise ValueError("Missing or unsafe trusted source: " + relative)
    return path.read_bytes().replace(b"\r\n", b"\n")


def _validate_recipe(recipe: dict) -> None:
    if not isinstance(recipe, dict) or set(recipe) != {
        "schema_version", "template", "package_id", "part_ids", "purpose"
    }:
        raise ValueError("Unknown or missing recipe keys")
    if (recipe["schema_version"] != 1 or recipe["template"] != TEMPLATE or
            recipe["package_id"] != PACKAGE_ID or
            recipe["purpose"] != "local_development_preview"):
        raise ValueError("Only the allowlisted private Mesh Inspector preview is supported")
    ids = recipe["part_ids"]
    if not isinstance(ids, list) or len(ids) != 3 or len(set(map(str, ids))) != 3 or set(ids) != PART_IDS:
        raise ValueError("Recipe must specify exactly the three authored Mesh Inspector parts")


def _read_catalog(*, root: Path) -> dict:
    catalog = json.loads(_trusted_read("catalog/authored_parts.json", root=root))
    if catalog.get("schema_version") != 1 or not isinstance(catalog.get("parts"), list):
        raise ValueError("Unsupported authored parts catalog")
    entries = {}
    for part in catalog["parts"]:
        if not isinstance(part, dict) or not isinstance(part.get("part_id"), str):
            raise ValueError("Invalid authored parts catalog entry")
        key = part["part_id"]
        if key in entries:
            raise ValueError("Duplicate part IDs in catalog")
        entries[key] = part
    return entries


def build_addon(
    recipe_path: str | Path,
    output: str | Path,
    *,
    preview_unapproved: bool = False,
    root: Path | None = None,
) -> dict:
    """Deterministically package trusted files; no third-party code execution."""
    project = (root or ROOT).resolve()
    recipe = json.loads(Path(recipe_path).read_text(encoding="utf-8"))
    _validate_recipe(recipe)
    entries = _read_catalog(root=project)
    chosen = {}
    for part_id in sorted(PART_IDS):
        if part_id not in entries:
            raise ValueError("Missing authored part: " + part_id)
        entry = entries[part_id]
        source = entry.get("source")
        if source not in SOURCES:
            raise ValueError("Unexpected source for " + part_id)
        if part_id in {"BLCTX-001", "BLCTX-002"} and source != "parts/blender/context.py":
            raise ValueError("Context part source mismatch")
        if part_id == "BME-001" and source != "parts/blender/edit_mesh.py":
            raise ValueError("Edit part source mismatch")
        chosen[part_id] = entry

    if not preview_unapproved:
        # The sole available template is a private development preview.
        # Release mode needs an independent license/provenance process.
        raise ValueError("Not a distributable addon: pass --preview-unapproved for a LOCAL development build")
    assets = {
        "__init__.py": _trusted_read("templates/mesh_inspector/__init__.py", root=project),
        "helpers/__init__.py": b'"""CBDK authored helpers (local development preview)."""\n',
        **{dest: _trusted_read(src, root=project) for src, dest in SOURCES.items()},
        "README.txt": README.encode("utf-8"),
    }
    provenance = {
        "schema_version": 1,
        "template": TEMPLATE, "package_id": PACKAGE_ID,
        "preview_only": True, "redistribution_cleared": False,
        "approved": False, "blender_runtime_verified_for_this_build": False,
        "parts": [{"part_id": pid, "catalog_approved": chosen[pid].get("approved") is True,
                   "license_review": chosen[pid].get("license_review", "pending"),
                   "source": chosen[pid]["source"],
                   "sha256": _sha(assets[SOURCES[chosen[pid]["source"]]])}
                  for pid in sorted(PART_IDS)],
        "files_sha256": {path: _sha(blob) for path, blob in sorted(assets.items())},
        "warning": "Developer-only preview. Source hashes do not prove license or runtime behavior.",
    }
    assets["CBDK_BUILD_INFO.json"] = (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode("utf-8")
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Output already exists (won't overwrite): {target}")
    # ZIP contains exactly one addon folder, installable as a legacy addon.
    with ZipFile(target, "x", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for rel, blob in sorted(assets.items()):
            filename = f"{PACKAGE_ID}/{rel}"
            info = ZipInfo(filename, (2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, blob)
    return {"output": str(target), "package_id": PACKAGE_ID, "part_ids": sorted(PART_IDS),
            "files": len(assets), "preview_only": True, "approved": False}
