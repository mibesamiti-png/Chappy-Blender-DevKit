"""R19 fixed authored recipe to an isolated, non-release Extension fixture.

No external ZIP, recipe, metadata, root or source path accepted. No public
installer. Only code-owned read-only mesh inspection features are included.
"""
from __future__ import annotations

import ast
import io
from pathlib import Path
import stat
import tempfile
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from .addon_builder import _trusted_read
from .extension_preflight import (MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS,
                                  inspect_preview_archive)
from .extension_synthetic_build import _render_fixture_manifest
from .modular_builder import PACKAGE_ID, build_modular

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ID = "cbdk_authored_runtime_fixture"
_FEATURES = ("mesh_bounds", "mesh_center")
_SOURCE_MAP = {
    "features/mesh_bounds.py": "templates/modular_preview/features/mesh_bounds.py",
    "features/mesh_center.py": "templates/modular_preview/features/mesh_center.py",
    "helpers/context.py": "parts/blender/context.py",
    "helpers/measure.py": "parts/blender/measure.py",
}
_PYTHON = frozenset({"__init__.py", "features/__init__.py", "helpers/__init__.py",
                     *_SOURCE_MAP})
_PREVIEW = _PYTHON | {"README.txt", "CBDK_BUILD_INFO.json"}
_MEMBERS = _PYTHON | {"blender_manifest.toml"}


def fixture_metadata():
    # Explicit test-only SPDX sample, NOT a rights or license decision.
    return {
        "schema_version": "1.0.0", "id": FIXTURE_ID, "version": "0.0.1",
        "name": "CBDK authored runtime fixture",
        "tagline": "Isolated mesh inspection test",
        "maintainer": "CBDK CI fixture", "type": "add-on",
        "blender_version_min": "4.4.0", "license": ["SPDX:GPL-3.0-or-later"],
    }


def _recipe():
    return {"schema_version": 2, "template": "modular_preview",
            "package_id": PACKAGE_ID, "display_name": "CBDK authored runtime fixture",
            "features": list(_FEATURES), "purpose": "local_development_preview",
            # Fixed internal integration case; still no caller-provided recipe.
            "ui_layout": {"schema_version": 1,
                "kind": "cbdk_authored_preview_ui_layout", "preview_only": True,
                "sections": [{"id": "center", "title": "Center",
                    "visible_in": "object", "layout": "row",
                    "controls": [
                        {"feature_id": "mesh_center", "label": "Find center",
                         "parameters": {"precision": {"default": 2, "min": 1, "max": 4}}},
                        {"feature_id": "mesh_bounds", "label": "Read bounds"}]}]}}


def _without_legacy_info(data):
    # Only remove the single top-level literal legacy metadata assignment;
    # Extension metadata is in the manifest. Preserve all runtime source.
    source = data.decode("utf-8")
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == "bl_info" for t in n.targets)]
    if len(nodes) != 1 or len(nodes[0].targets) != 1 or not isinstance(nodes[0].value, ast.Dict):
        raise ValueError("Unexpected authored legacy metadata")
    node = nodes[0]
    lines = source.splitlines(keepends=True)
    output = "".join(lines[:node.lineno - 1] + lines[node.end_lineno:])
    ast.parse(output)
    return output.encode("utf-8")


def _read_generated_preview(path):
    report = inspect_preview_archive(path)
    if (report["status"] != "blocked_for_extension_release"
            or report["preview_only"] is not True
            or report["python_code_executed"] is not False):
        raise ValueError("Unexpected authored preview approval state")
    with ZipFile(path) as archive:
        prefix = PACKAGE_ID + "/"
        if set(archive.namelist()) != {prefix + n for n in _PREVIEW}:
            raise ValueError("Unexpected authored fixture inventory")
        return {name: archive.read(prefix + name) for name in _PREVIEW}


def _generated_members():
    with tempfile.TemporaryDirectory(prefix="cbdk-r19-build-") as folder:
        first, second = (Path(folder) / n for n in ("a.zip", "b.zip"))
        for path in (first, second):
            result = build_modular(_recipe(), path, preview_unapproved=True, root=ROOT)
            if (set(result["features"]) != set(_FEATURES)
                    or result["approved"] is not False or result["preview_only"] is not True):
                raise ValueError("Unexpected authored recipe output")
        left, right = _read_generated_preview(first), _read_generated_preview(second)
        if left != right:
            raise ValueError("Authored generation is not repeatable")
        for member, source in _SOURCE_MAP.items():
            if left[member] != _trusted_read(source, root=ROOT):
                raise ValueError("Authored source bytes differ")
        members = {name: left[name] for name in _PYTHON}
    members["__init__.py"] = _without_legacy_info(members["__init__.py"])
    # Legacy README/provenance (which hashes the original init) are not copied.
    # Preflight's release-blocked state remains unchanged.
    members["blender_manifest.toml"] = _render_fixture_manifest(fixture_metadata(), FIXTURE_ID)
    return members


def build_authored_fixture_bytes():
    members = _generated_members()
    if (set(members) != _MEMBERS or len(members) > MAX_MEMBERS
            or any(len(data) > MAX_ENTRY_BYTES for data in members.values())
            or sum(map(len, members.values())) > MAX_ARCHIVE_BYTES):
        raise ValueError("Authored fixture exceeds inventory budget")
    output = io.BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED, allowZip64=False) as archive:
        for name, data in sorted(members.items()):
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = ZIP_STORED
            archive.writestr(info, data)
    blob = output.getvalue()
    if not 0 < len(blob) <= MAX_ARCHIVE_BYTES:
        raise ValueError("Authored fixture ZIP exceeds budget")
    with ZipFile(io.BytesIO(blob)) as archive:
        if (len(archive.infolist()) != len(members) or set(archive.namelist()) != _MEMBERS
                or any(archive.read(n) != b for n, b in members.items())):
            raise ValueError("Authored fixture ZIP content mismatch")
    return blob


def write_authored_fixture(output):
    """Only the fixed fixture; caller-owned fresh temporary directory."""
    path = Path(output)
    data = build_authored_fixture_bytes()
    if (path.suffix != ".zip" or not path.parent.is_dir()
            or path.parent.is_symlink() or path.is_symlink()):
        raise ValueError("Expected fresh fixture ZIP")
    with path.open("xb") as stream:
        stream.write(data)
    return {"member_count": len(_MEMBERS), "release_authorized": False,
            "install_authorized": False, "real_component_license_chosen": False}
