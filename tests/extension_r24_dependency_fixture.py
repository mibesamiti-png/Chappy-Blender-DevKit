"""Fixed internal R24 graph. Never exposed as a recipe option or root override."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from cbdk import feature_catalog
from test_ui_recipe_r17 import make_r23_recipe

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / feature_catalog.CATALOG_PATH
ORDER = ("mesh_bounds", "edit_selection", "mesh_center", "vertex_nudge")
PARTS = ("BLCTX-001", "BLGEO-001", "BME-001", "BME-002", "BME-003")
EDGES = {"vertex_nudge": ["edit_selection", "mesh_center"],
         "edit_selection": ["mesh_bounds"], "mesh_center": ["mesh_bounds"]}
MEMBERS = {
    "__init__.py", "blender_manifest.toml", "features/__init__.py", "helpers/__init__.py",
    "features/mesh_bounds.py", "features/edit_selection.py", "features/mesh_center.py",
    "features/vertex_nudge.py", "helpers/context.py", "helpers/measure.py",
    "helpers/edit_mesh.py", "helpers/edit_transform.py", "helpers/edit_audit.py",
}


def dependency_recipe():
    recipe = make_r23_recipe("grouped")
    recipe["features"] = ["vertex_nudge"]
    return recipe


@contextmanager
def dependency_catalog(case="wide"):
    """Patch only the trusted catalog reader in this process; no disk writes."""
    if case not in ("wide", "min", "max", "disjoint", "cycle", "missing"):
        raise ValueError("Unknown internal dependency fixture")
    original = CATALOG.read_bytes()
    source = json.loads(original)
    if any(f["requires_features"] for f in source["features"]):
        raise AssertionError("R24 production catalog unexpectedly contains dependencies")
    rows = {f["id"]: f for f in source["features"]}
    for key, parents in EDGES.items():
        rows[key]["requires_features"] = list(parents)
    if case == "min":
        rows["mesh_bounds"]["min_blender"] = "4.5.0"
    elif case == "max":
        rows["mesh_center"]["max_blender"] = "5.2.1"
    elif case == "disjoint":
        rows["mesh_bounds"]["min_blender"] = "5.0.0"
        rows["mesh_center"]["max_blender"] = "4.5.15"
    elif case == "cycle":
        rows["mesh_bounds"]["requires_features"] = ["vertex_nudge"]
    elif case == "missing":
        rows["mesh_center"]["requires_features"] = ["unknown_feature"]

    def load(*, root):
        if root.resolve() != ROOT:
            raise AssertionError("R24 fixture root mismatch")
        return feature_catalog.validate_feature_catalog(source)

    try:
        with patch.object(feature_catalog, "load_feature_catalog", side_effect=load):
            yield hashlib.sha256(original).hexdigest()
    finally:
        if CATALOG.read_bytes() != original:
            raise AssertionError("R24 production catalog changed")
