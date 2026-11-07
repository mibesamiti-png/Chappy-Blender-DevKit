"""Offline, fail-closed readiness audit for CBDK's legacy preview ZIPs.

This *cannot* create, sign, approve, or distribute Blender Extensions.
All catalog-provenance flags stay unapproved. Never execute packaged Python.
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from .extension_manifest import review_manifest_fields, manifest_field_diagnostics

KNOWN = {
    "cbdk_mesh_inspector_preview": (1, "mesh_inspector"),
    "cbdk_modular_preview": (2, "modular_preview"),
}
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_ENTRY_BYTES = 2 * 1024 * 1024
MAX_MEMBERS = 64
SHA = re.compile(r"^[0-9a-f]{64}$")


def _json_unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate metadata JSON key")
        result[key] = value
    return result


def inspect_preview_archive(source: str | Path) -> dict:
    """Verify exact allowlisted archive members/hashes, then list release blockers.

    This is a local static preflight and NOT official Blender manifest validation.
    Never ingest user/private add-on source in public CI. Output intentionally
    contains only authored package IDs and aggregate counts, no source paths.
    """
    path = Path(source)
    if not path.is_file() or path.is_symlink():
        raise ValueError("Missing or unsafe local preview ZIP")
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("Preview ZIP exceeds archive byte budget")
    try:
        with ZipFile(path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if not 3 <= len(infos) <= MAX_MEMBERS or len(names) != len(set(names)):
                raise ValueError("Invalid or duplicate preview archive members")
            packages = {name.split("/")[0] for name in names}
            if len(packages) != 1:
                raise ValueError("Preview archive must contain exactly one package")
            package = next(iter(packages))
            if package not in KNOWN:
                raise ValueError("Not a CBDK-authored preview ZIP")
            prefix = package + "/"
            for info in infos:
                name = info.filename
                components = name.split("/")
                if (not name.startswith(prefix) or
                        len(components) < 2 or
                        any(x in ("", ".", "..") for x in components) or
                        "\\" in name or info.is_dir() or
                        info.file_size > MAX_ENTRY_BYTES or
                        stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK):
                    raise ValueError("Unsafe preview archive member")
            if sum(info.file_size for info in infos) > MAX_ARCHIVE_BYTES:
                raise ValueError("Preview archive uncompressed size budget exceeded")
            meta_path = prefix + "CBDK_BUILD_INFO.json"
            if meta_path not in names:
                raise ValueError("Missing CBDK build provenance")
            metadata = json.loads(
                archive.read(meta_path).decode("utf-8"),
                object_pairs_hook=_json_unique,
            )
            if not isinstance(metadata, dict):
                raise ValueError("Invalid CBDK provenance")
            schema, expected_template = KNOWN[package]
            if (type(metadata.get("schema_version")) is not int
                    or metadata["schema_version"] != schema
                    or metadata.get("template") != expected_template
                    or metadata.get("package_id") != package
                    or metadata.get("preview_only") is not True
                    or metadata.get("approved") is not False
                    or metadata.get("redistribution_cleared") is not False
                    or metadata.get("blender_runtime_verified_for_this_build") is not False):
                raise ValueError("Preview origin or approval state is not trusted")
            digests = metadata.get("files_sha256")
            if not isinstance(digests, dict):
                raise ValueError("Missing file hash inventory")
            rels = {name.removeprefix(prefix) for name in names if name != meta_path}
            if set(digests) != rels or "__init__.py" not in rels:
                raise ValueError("CBDK archive members disagree with provenance")
            for rel in sorted(rels):
                digest = digests[rel]
                if not isinstance(digest, str) or not SHA.fullmatch(digest):
                    raise ValueError("Invalid provenance SHA256")
                if hashlib.sha256(archive.read(prefix + rel)).hexdigest() != digest:
                    raise ValueError("CBDK preview file changed since build")
            if schema == 2:
                selected = metadata.get("features")
                if (not isinstance(selected, list) or
                        not selected or len(selected) > 5 or
                        any(type(s) is not str or s not in {
                            "object_selection", "edit_selection", "mesh_bounds",
                            "modifier_summary", "vertex_nudge"} for s in selected)
                        or len(selected) != len(set(selected))):
                    raise ValueError("Preview feature inventory is not allowlisted")
                if {n.removeprefix("features/").removesuffix(".py")
                        for n in rels if n.startswith("features/") and
                        n != "features/__init__.py"} != set(selected):
                    raise ValueError("Preview feature modules disagree with provenance")
            parts = metadata.get("parts")
            if (not isinstance(parts, list) or not parts or len(parts) > 7
                    or any(not isinstance(p, dict) or
                           p.get("catalog_approved") is not False or
                           p.get("license_review") not in ("pending", "not_reviewed")
                           for p in parts)):
                raise ValueError("Preview part approvals or license metadata are unexpected")
            from .feature_catalog import TRUSTED_FEATURES, TRUSTED_PART_SOURCES
            from .modular_builder import HELPERS
            expected_parts = ({p for f in selected for p in TRUSTED_FEATURES[f]["parts"]}
                              if schema == 2 else {"BLCTX-001", "BLCTX-002", "BME-001"})
            ids = [p.get("part_id") for p in parts]
            if any(type(p) is not str for p in ids) or len(set(ids)) != len(ids) or set(ids) != expected_parts:
                raise ValueError("Preview part dependency inventory mismatch")
            expected_files = {"__init__.py", "README.txt", "helpers/__init__.py"}
            expected_files |= {HELPERS[TRUSTED_PART_SOURCES[p]] for p in expected_parts}
            if schema == 2:
                expected_files |= {"features/__init__.py"} | {"features/" + f + ".py" for f in selected}
                if metadata.get("part_ids") != sorted(expected_parts):
                    raise ValueError("Preview dependency list mismatch")
            if rels != expected_files:
                raise ValueError("Preview contains undeclared helper or file")
            # All validation above is structural. Never import any bundled source.
            source_count = len(rels)
    except (BadZipFile, UnicodeDecodeError, KeyError) as exc:
        raise ValueError("Invalid CBDK preview ZIP") from exc

    fields = {
        "schema_version": "1.0.0",
        "id": package,
        "name": metadata.get("display_name", "CBDK Mesh Inspector Preview"),
        "tagline": "Authored mesh inspection development preview",
        "type": "add-on",
        "blender_version_min": metadata.get("minimum_blender", "4.4.0"),
        "version": None,
        "maintainer": None,
        "license": None,
    }
    # Missing owner decisions are intentionally JSON null, never an invalid
    # placeholder blender_manifest.toml or a fabricated SPDX declaration.
    return {
        "schema_version": 1,
        "kind": "cbdk_extension_readiness_preflight",
        "status": "blocked_for_extension_release",
        "package_id": package,
        "archive_structure_checked": True,
        "provenance_hashes_verified": True,
        "source_authenticity_verified": False,
        "verified_source_file_count": source_count,
        "python_code_executed": False,
        "preview_only": True,
        "extension_zip_created": False,
        "manifest_toml_emitted": False,
        "official_blender_extension_validate_ran": False,
        "manifest_fields_review_only": fields,
        "manifest_structure_review": review_manifest_fields(fields),
        "manifest_field_diagnostics": manifest_field_diagnostics(fields),
        "blocker_categories": {
            "owner_metadata": ["version", "maintainer", "license"],
            "approval": ["component_approval", "redistribution_authorization"],
            "packaging": ["extension_archive_layout"],
            "verification": ["official_manifest_validation", "extension_runtime_test"],
        },
        "blockers": [
            "owner_must_set_and_review_version",
            "owner_must_provide_maintainer",
            "owner_must_choose_license_and_review_all_parts",
            "authored_components_not_formally_approved",
            "legacy_preview_zip_not_extension_archive",
            "official_blender_extension_validate_and_runtime_test_pending",
            "owner_release_and_redistribution_authorization_required",
        ],
        "safe_next_steps": [
            "review_ownership_and_spdx_licensing_outside_automation",
            "create_a_separate_explicit_extension_build_path_after_approval",
            "validate_result_with_blender_command_extension_validate",
            "test_extension_install_disable_remove_in_trusted_blender",
            "request_explicit_owner_release_approval",
        ],
    }


def write_preflight_report(source: str | Path, output: str | Path) -> dict:
    report = inspect_preview_archive(source)
    target = Path(output)
    if target.exists():
        raise FileExistsError("Existing readiness report will not be overwritten")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=2, sort_keys=True)
        out.write("\n")
    return report
