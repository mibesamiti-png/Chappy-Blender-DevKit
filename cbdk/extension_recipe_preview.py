"""R23 local preview Extension assembly from bounded declarative recipes.

Trust is limited to the current CBDK checkout and its code-owned allowlist.
No external ZIP, source root, executable user text, installer or rights grant.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
import stat
import tempfile
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from .addon_builder import _trusted_read
from .extension_authored_fixture import FIXTURE_ID, fixture_metadata, _without_legacy_info
from .extension_preflight import (MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS,
                                  inspect_preview_archive)
from .extension_synthetic_build import _render_fixture_manifest
from .feature_catalog import TRUSTED_FEATURES, TRUSTED_PART_SOURCES, feature_runtime_contract
from .modular_builder import PACKAGE_ID, HELPERS, build_modular, plan_modular_recipe

ROOT = Path(__file__).resolve().parents[1]
_MAX_RECIPE_BYTES = 32768


def ci_recipe(case):
    base = {"schema_version": 2, "template": "modular_preview", "package_id": PACKAGE_ID,
            "display_name": "CBDK R23 local test", "purpose": "local_development_preview"}
    if case == "read":
        return {**base, "features": ["mesh_bounds", "mesh_center"]}
    if case == "edit":
        return {**base, "features": ["edit_selection", "vertex_nudge"]}
    raise ValueError("Unknown R23 fixture case")


def _snapshot_recipe(recipe):
    # Bound JSON-like input before serialization; no custom encoders, arbitrary
    # objects, code or caller-provided metadata/root. Planner validates semantics.
    budget = 1024
    def visit(value, depth=0):
        nonlocal budget
        budget -= 1
        if budget < 0 or depth > 12:
            raise ValueError("Recipe complexity exceeds local preview budget")
        if type(value) is dict:
            for key, child in value.items():
                if type(key) is not str or len(key) > 256:
                    raise ValueError("Invalid recipe key")
                visit(child, depth + 1)
        elif type(value) is list:
            for child in value:
                visit(child, depth + 1)
        elif type(value) is str:
            if len(value) > 1024:
                raise ValueError("Recipe text exceeds budget")
        elif type(value) not in (int, float, bool, type(None)):
            raise ValueError("Recipe must be plain JSON data")
        elif type(value) is int and value.bit_length() > 64:
            raise ValueError("Recipe integer exceeds budget")
    if type(recipe) is not dict:
        raise ValueError("Recipe must be a JSON object")
    visit(recipe)
    try:
        data = json.dumps(recipe, ensure_ascii=True, allow_nan=False)
    except (ValueError, TypeError):
        raise ValueError("Invalid local preview recipe") from None
    if len(data) > _MAX_RECIPE_BYTES:
        raise ValueError("Recipe byte budget exceeded")
    return json.loads(data)


def _expected_sources(recipe, plan):
    selected = tuple(plan["ordered_features"])
    parts = {p for f in selected for p in TRUSTED_FEATURES[f]["parts"]}
    if set(plan["part_ids"]) != parts or not set(recipe["features"]) <= set(selected):
        raise ValueError("Recipe dependency closure mismatch")
    mapping = {"features/" + f + ".py": TRUSTED_FEATURES[f]["source"] for f in selected}
    mapping.update({HELPERS[TRUSTED_PART_SOURCES[p]]: TRUSTED_PART_SOURCES[p] for p in parts})
    sources = {member: _trusted_read(path, root=ROOT) for member, path in mapping.items()}
    template = _trusted_read("templates/modular_preview/__init__.py", root=ROOT)
    replacements = {"__CBDK_DISPLAY_NAME__": repr(recipe["display_name"]),
                    "__CBDK_FEATURE_IDS__": repr(selected),
                    "__CBDK_UI_SECTIONS__": repr(plan["ui_layout"]["sections"]),
                    "__CBDK_UI_OPTIONS__": repr(plan["ui_layout"]["options"]),
                    "__CBDK_FEATURE_CONTRACT__": repr(feature_runtime_contract(selected))}
    code = template.decode("utf-8")
    if any(code.count(key) != 1 for key in replacements):
        raise ValueError("Unexpected authored init template")
    sources["__init__.py"] = re.sub("|".join(map(re.escape, replacements)),
                                     lambda m: replacements[m.group()], code).encode("utf-8")
    sources["helpers/__init__.py"] = b'"""Locally authored CBDK helpers. Preview use only."""\n'
    sources["features/__init__.py"] = b'"""Allowlisted feature modules selected by a v2 recipe."""\n'
    return sources, mapping, template


def _assemble(recipe):
    recipe = _snapshot_recipe(recipe)
    plan = plan_modular_recipe(recipe, root=ROOT, include_ui=True)
    # The test manifest is fixed, not derived from the selected features.
    # Reject narrower closures before any build or output: do not advertise
    # compatibility that the authored feature catalog does not declare.
    fields = fixture_metadata()
    if (plan["minimum_blender"] != fields["blender_version_min"]
            or plan["maximum_blender"] is not None):
        raise ValueError("Recipe compatibility does not match fixed Extension fixture range")
    expected, mapping, template = _expected_sources(recipe, plan)
    prefix = PACKAGE_ID + "/"
    inventory = set(expected) | {"README.txt", "CBDK_BUILD_INFO.json"}
    hashes = []
    with tempfile.TemporaryDirectory(prefix="cbdk-r23-recipe-") as folder:
        for index in (0, 1):
            path = Path(folder) / (str(index) + ".zip")
            result = build_modular(recipe, path, preview_unapproved=True, root=ROOT)
            if (result["approved"] is not False or result["preview_only"] is not True
                    or result["features"] != plan["ordered_features"]
                    or result["part_ids"] != plan["part_ids"]):
                raise ValueError("Unexpected local preview build result")
            checked = inspect_preview_archive(path)
            if (checked["status"] != "blocked_for_extension_release"
                    or checked["python_code_executed"] is not False):
                raise ValueError("Unexpected preview preflight")
            raw = path.read_bytes()
            before = hashlib.sha256(raw).hexdigest()
            with ZipFile(path) as z:
                if len(z.infolist()) != len(inventory) or set(z.namelist()) != {prefix+n for n in inventory}:
                    raise ValueError("Preview inventory mismatch")
                if any(z.read(prefix+n) != b for n,b in expected.items()):
                    raise ValueError("Preview bytes differ from trusted authored source")
            if hashlib.sha256(path.read_bytes()).hexdigest() != before:
                raise ValueError("Original preview changed")
            hashes.append(before)
        if hashes[0] != hashes[1]:
            raise ValueError("Preview generation is not deterministic")
    if (_trusted_read("templates/modular_preview/__init__.py", root=ROOT) != template
            or any(_trusted_read(p, root=ROOT) != expected[n] for n,p in mapping.items())):
        raise ValueError("Trusted source changed during assembly")
    members = dict(expected)
    members["__init__.py"] = _without_legacy_info(members["__init__.py"])
    members["blender_manifest.toml"] = _render_fixture_manifest(fields, FIXTURE_ID)
    if (len(members) > MAX_MEMBERS or any(len(b) > MAX_ENTRY_BYTES for b in members.values())
            or sum(map(len, members.values())) > MAX_ARCHIVE_BYTES):
        raise ValueError("Extension inventory exceeds budget")
    output = io.BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED, allowZip64=False) as z:
        for name, data in sorted(members.items()):
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = ZIP_STORED
            z.writestr(info, data)
    blob = output.getvalue()
    if len(blob) > MAX_ARCHIVE_BYTES:
        raise ValueError("Extension ZIP exceeds budget")
    with ZipFile(io.BytesIO(blob)) as z:
        if (len(z.infolist()) != len(members) or set(z.namelist()) != set(members)
                or any(z.read(n) != b for n,b in members.items())):
            raise ValueError("Extension ZIP verification failed")
    return blob, {"member_count": len(members), "feature_count": len(plan["ordered_features"]),
                  "original_preview_sha256": hashes[0], "original_preview_unchanged": True,
                  "approved": False, "release_authorized": False, "install_authorized": False,
                  "real_component_license_chosen": False, "preview_only": True}


def build_recipe_extension_bytes(recipe, *, preview_unapproved=False):
    if preview_unapproved is not True:
        raise ValueError("Explicit local preview opt-in required")
    return _assemble(recipe)[0]


def write_recipe_extension(recipe, output, *, preview_unapproved=False):
    if preview_unapproved is not True:
        raise ValueError("Explicit local preview opt-in required")
    path = Path(output)
    if (path.suffix != ".zip" or not path.parent.is_dir()
            or path.parent.is_symlink() or path.is_symlink()):
        raise ValueError("Expected fresh local preview ZIP")
    blob, report = _assemble(recipe)
    with path.open("xb") as stream:
        stream.write(blob)
    return report
