"""Review-only registration plan for new CBDK-authored preview features.

This does not modify trusted catalogs, install a feature, generate Python code,
execute a source file, approve licensing, or mark Blender runtime tests passed.
All suggested changes must be reviewed and implemented in a separate PR.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .addon_builder import ROOT, _read_catalog
from .feature_catalog import (
    TRUSTED_FEATURES, TRUSTED_PART_SOURCES, load_feature_catalog,
)

FEATURE_ID = re.compile(r"[a-z][a-z0-9_]{2,39}\Z")
PART_ID = re.compile(r"[A-Z]{2,8}-[0-9]{3}\Z")
MODULE_NAME = re.compile(r"[a-z][a-z0-9_]{1,39}\Z")
MAX_PARTS = 8
REPORT_DIR = Path("reports/latest")


def _checked_text(value: object, pattern: re.Pattern, label: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError("Invalid " + label)
    return value


def propose_registration(
    feature_id: str,
    required_parts: list[str] | tuple[str, ...],
    *,
    new_part_id: str | None = None,
    new_part_module: str | None = None,
    root: Path = ROOT,
) -> dict:
    """Plan a manually reviewed *proposal*, never an executable registration."""
    project = Path(root).resolve()
    feature = _checked_text(feature_id, FEATURE_ID, "feature ID")
    if (new_part_id is None) != (new_part_module is None):
        raise ValueError("New part ID and module must be supplied together")

    parts = _read_catalog(root=project)
    catalog = load_feature_catalog(root=project)
    if set(parts) != set(TRUSTED_PART_SOURCES) or set(catalog) != set(TRUSTED_FEATURES):
        raise ValueError("Trusted catalog is inconsistent with the code allowlist")
    for key, entry in parts.items():
        if (entry.get("source") != TRUSTED_PART_SOURCES[key]
                or entry.get("approved") is not False
                or entry.get("license_review") != "pending"):
            raise ValueError("Existing part is not in its expected review state: " + key)
    if feature in catalog or feature in TRUSTED_FEATURES:
        raise ValueError("Feature ID is already registered")

    feature_source = f"templates/modular_preview/features/{feature}.py"
    if (project / feature_source).exists() or (project / feature_source).is_symlink():
        raise ValueError("Proposed feature source path already exists")

    proposed_part = None
    if new_part_id is not None:
        part_id = _checked_text(new_part_id, PART_ID, "part ID")
        module = _checked_text(new_part_module, MODULE_NAME, "part module")
        if part_id in parts or part_id in TRUSTED_PART_SOURCES:
            raise ValueError("Part ID is already registered")
        part_source = f"parts/blender/{module}.py"
        if (project / part_source).exists() or (project / part_source).is_symlink():
            raise ValueError("Proposed part source path already exists")
        proposed_part = {"id": part_id, "source": part_source,
                         "approved": False, "license_review": "pending"}

    if (not isinstance(required_parts, (list, tuple))
            or not 1 <= len(required_parts) <= MAX_PARTS
            or any(not isinstance(key, str) or not PART_ID.fullmatch(key)
                   for key in required_parts)
            or len(set(required_parts)) != len(required_parts)):
        raise ValueError("Required parts must be a nonempty unique list of part IDs")

    possible = set(TRUSTED_PART_SOURCES)
    if proposed_part is not None:
        possible.add(proposed_part["id"])
        if proposed_part["id"] not in required_parts:
            raise ValueError("Newly proposed part must be a required dependency")
    if not set(required_parts) <= possible:
        raise ValueError("Unregistered required part ID")

    return {
        "schema_version": 1,
        "kind": "cbdk_registration_draft",
        "status": "proposal_only",
        "feature_id": feature,
        "feature_source": feature_source,
        "required_parts": sorted(required_parts),
        "new_part": proposed_part,
        "current_trusted_features": sorted(catalog),
        "current_trusted_parts": sorted(parts),
        "review_steps": [
            "Implement and independently review the CBDK-authored feature and optional part; never run scanned private inputs",
            "Review ownership, SPDX licensing, provenance and attribution; do not grant approval from this draft",
            "Update catalog/authored_parts.json for any new part with approved=false and license_review=pending",
            "Update catalog/addon_features.json and the source/part allowlists in cbdk/feature_catalog.py",
            "Update cbdk/modular_builder.py helper mappings and templates/modular_preview/__init__.py if necessary",
            "Review recipes/modular_all.json and cbdk/recipe_matrix.py EXPECTED_RECIPES; add appropriate example recipes",
            "Update Blender smoke scripts, unit tests, expected IDs and GitHub Actions paths/matrices",
            "Update docs/project/STATE.json, regenerate docs/PROJECT_HANDOFF.md, and open a review PR",
            "Run Python, Windows and real Blender tests; record actual CI evidence before merge or release",
        ],
        "preview_only": True,
        "approved": False,
        "redistribution_cleared": False,
        "runtime_verified": False,
        "source_executed": False,
        "catalog_modified": False,
    }


def write_draft(report: dict, *, root: Path = ROOT,
                relative_path: str = "reports/latest/registration_draft.json") -> Path:
    """Write an opt-in private report under reports/latest, never tracked code."""
    project = Path(root).resolve()
    relative = Path(relative_path)
    if (relative.is_absolute() or len(relative.parts) < 3
            or relative.parts[:2] != REPORT_DIR.parts
            or any(piece in {".", ".."} for piece in relative.parts)
            or relative.suffix != ".json"):
        raise ValueError("Draft output must be a JSON file under reports/latest/")
    target = project / relative
    # Reject a symbolic-link escape through any existing parent directory.
    if not target.resolve().is_relative_to(project / REPORT_DIR):
        raise ValueError("Draft report escapes private output directory")
    if target.is_symlink() or target.exists():
        raise FileExistsError("Draft report already exists; no overwrite: " + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
    return target
