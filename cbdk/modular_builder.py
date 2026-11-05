"""CBDK v0.11 deterministic *preview-only* modular Blender add-on composer.

Recipes are declarative data and can only select reviewed, CBDK-authored
feature modules from the allowlist below. Arbitrary Python, arbitrary paths,
extra JSON keys and untrusted scan candidates are rejected. This is NOT a
release, not a license grant, and not an endorsement of third-party code.
"""
from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .addon_builder import _read_catalog, _sha, _trusted_read

PACKAGE_ID = "cbdk_modular_preview"
TEMPLATE = "modular_preview"
FEATURES = {
    "object_selection": {
        "parts": frozenset({"BLCTX-001", "BLCTX-002"}),
        "source": "templates/modular_preview/features/object_selection.py",
    },
    "edit_selection": {
        "parts": frozenset({"BLCTX-001", "BME-001"}),
        "source": "templates/modular_preview/features/edit_selection.py",
    },
}
PART_SOURCES = {
    "BLCTX-001": "parts/blender/context.py",
    "BLCTX-002": "parts/blender/context.py",
    "BME-001": "parts/blender/edit_mesh.py",
}
HELPERS = {
    "parts/blender/context.py": "helpers/context.py",
    "parts/blender/edit_mesh.py": "helpers/edit_mesh.py",
}
MAX_DISPLAY_NAME = 72


def validate_modular_recipe(recipe: object) -> tuple[str, tuple[str, ...]]:
    if not isinstance(recipe, dict) or set(recipe) != {
        "schema_version", "template", "package_id", "display_name",
        "features", "purpose"
    }:
        raise ValueError("Only the declared modular-preview recipe keys are supported")
    if (recipe["schema_version"] != 2 or recipe["template"] != TEMPLATE
            or recipe["package_id"] != PACKAGE_ID
            or recipe["purpose"] != "local_development_preview"):
        raise ValueError("This builder only creates the allowlisted development-preview addon")
    name = recipe["display_name"]
    if (not isinstance(name, str) or not 3 <= len(name) <= MAX_DISPLAY_NAME or
            any(ord(ch) < 32 or ord(ch) == 127 for ch in name)):
        raise ValueError("Invalid printable display_name")
    features = recipe["features"]
    if (not isinstance(features, list) or not 1 <= len(features) <= len(FEATURES) or
            any(not isinstance(feature, str) or feature not in FEATURES for feature in features)
            or len(set(features)) != len(features)):
        raise ValueError("features must be a nonempty unique list of allowlisted feature names")
    return name, tuple(sorted(features))


def build_modular(
    recipe: object,
    output: str | Path,
    *,
    preview_unapproved: bool,
    root: Path,
) -> dict:
    """Compose only exact CBDK-owned feature templates, no arbitrary imports."""
    name, feature_ids = validate_modular_recipe(recipe)
    if not preview_unapproved:
        raise ValueError("Not approved for release: --preview-unapproved is required for LOCAL builds")
    catalog = _read_catalog(root=root)
    part_ids = sorted(set().union(*(FEATURES[f]["parts"] for f in feature_ids)))
    for part_id in part_ids:
        entry = catalog.get(part_id)
        if not isinstance(entry, dict) or entry.get("source") != PART_SOURCES[part_id]:
            raise ValueError("Authored part/source missing or mismatched: " + part_id)
        # This does not approve catalog entries; license and review still apply.

    init_template = _trusted_read("templates/modular_preview/__init__.py", root=root).decode("utf-8")
    for marker in ("__CBDK_DISPLAY_NAME__", "__CBDK_FEATURE_IDS__"):
        if init_template.count(marker) != 1:
            raise ValueError("Modular template placeholder must occur exactly once: " + marker)
    init_code = (init_template
                 .replace("__CBDK_DISPLAY_NAME__", repr(name))
                 .replace("__CBDK_FEATURE_IDS__", repr(feature_ids)))
    # Python repr is an escaped Python *literal*, not code supplied by recipes.
    sources = sorted({PART_SOURCES[part_id] for part_id in part_ids})
    assets: dict[str, bytes] = {
        "__init__.py": init_code.encode("utf-8"),
        "helpers/__init__.py": b'"""Locally authored CBDK helpers. Preview use only."""\n',
        "features/__init__.py": b'"""Allowlisted feature modules selected by a v2 recipe."""\n',
        "README.txt": (
            f"{name}\nPRIVATE DEVELOPMENT PREVIEW ONLY\n\n"
            f"Included feature IDs: {', '.join(feature_ids)}\n"
            "Blender 4.4+ > Preferences > Add-ons > Install Legacy Add-on.\n"
            "3D View > Sidebar > CBDK. Use the shown inspection buttons.\n"
            "Do not install multiple modular-preview variants simultaneously.\n"
            "This ZIP is not reviewed or cleared for redistribution.\n"
        ).encode("utf-8"),
    }
    for source in sources:
        assets[HELPERS[source]] = _trusted_read(source, root=root)
    for feature_id in feature_ids:
        assets["features/" + feature_id + ".py"] = _trusted_read(
            FEATURES[feature_id]["source"], root=root
        )

    provenance = {
        "schema_version": 2, "template": TEMPLATE, "package_id": PACKAGE_ID,
        "display_name": name, "features": list(feature_ids), "part_ids": part_ids,
        "preview_only": True, "redistribution_cleared": False, "approved": False,
        "blender_runtime_verified_for_this_build": False,
        "parts": [
            {"part_id": pid, "source": PART_SOURCES[pid],
             "source_sha256": _sha(assets[HELPERS[PART_SOURCES[pid]]]),
             "catalog_approved": catalog[pid].get("approved") is True,
             "license_review": catalog[pid].get("license_review", "pending")}
            for pid in part_ids
        ],
        "files_sha256": {k: _sha(v) for k, v in sorted(assets.items())},
        "warning": ("Local preview only. Source hashes do not authenticate runtime results, "
                    "ownership, licensing, equivalence or formal approval."),
    }
    assets["CBDK_BUILD_INFO.json"] = (
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Output already exists; refusing overwrite: {target}")
    # Fixed timestamps/order for deterministic, comparable archives.
    with ZipFile(target, "x", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for rel, blob in sorted(assets.items()):
            info = ZipInfo(f"{PACKAGE_ID}/{rel}", (2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, blob)
    return {"output": str(target), "package_id": PACKAGE_ID, "features": list(feature_ids),
            "part_ids": part_ids, "files": len(assets), "preview_only": True,
            "approved": False}
