"""Offline, fail-closed readiness audit for CBDK's legacy preview ZIPs.

This *cannot* create, sign, approve, or distribute Blender Extensions.
All catalog-provenance flags stay unapproved. Never execute packaged Python.
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
import struct
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile
from .extension_manifest import VERSION, review_manifest_fields, manifest_field_diagnostics

KNOWN = {
    "cbdk_mesh_inspector_preview": (1, "mesh_inspector"),
    "cbdk_modular_preview": (2, "modular_preview"),
}
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_ENTRY_BYTES = 2 * 1024 * 1024
MAX_MEMBERS = 64
SHA = re.compile(r"^[0-9a-f]{64}$")


class PreviewArchiveError(ValueError):
    """A controlled, source-path-free preflight failure classification."""

    def __init__(self, category: str, code: str, message: str):
        super().__init__(message)
        self.category = category
        self.code = code


def _clean_zip_envelope(path: Path) -> bool:
    """Legacy CBDK builders write a plain ZIP, without prefix, trailer or comment.

    Restricting the format rejects polyglot/overlaid archives that zipfile can
    otherwise accept. This deliberately does not claim to prove authorship.
    """
    with path.open("rb") as stream:
        if stream.read(4) != b"PK\x03\x04":
            return False
        stream.seek(-22, 2)
        tail = stream.read(22)
    return (len(tail) == 22 and tail[:4] == b"PK\x05\x06"
            and tail[-2:] == b"\x00\x00")



def _verify_canonical_zip_layout(archive: ZipFile, infos: list) -> None:
    """Require the exact contiguous, unextended ZIP layout emitted by CBDK.

    zipfile intentionally accepts executable prefixes, concatenated archives,
    and ignores some local/central header disagreements. CBDK's authored
    builders emit none of those features. Read raw bytes from the SAME open
    handle so ZIP member names, offsets and data cannot hide other records.
    """
    def mismatch():
        raise PreviewArchiveError(
            "archive_structure", "zip_layout_mismatch",
            "Preview ZIP local headers or central directory disagree")

    def metadata():
        raise PreviewArchiveError(
            "archive_structure", "unexpected_member_metadata",
            "Unexpected ZIP member extra field or comment")

    stream = archive.fp
    if stream is None:
        mismatch()
    stream.seek(0)
    data = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(data) > MAX_ARCHIVE_BYTES or len(data) < 22:
        mismatch()

    try:
        (signature, disk, dir_disk, entries_on_disk, entries_total,
         dir_size, dir_offset, archive_comment) = struct.unpack_from(
            "<4s4H2IH", data, len(data) - 22)
        if (signature != b"PK\x05\x06" or disk or dir_disk
                or archive_comment or entries_on_disk != len(infos)
                or entries_total != len(infos) or dir_offset == 0xffffffff
                or dir_size == 0xffffffff or dir_offset + dir_size != len(data) - 22):
            mismatch()

        central_pos = dir_offset
        local_pos = 0
        central_end = dir_offset + dir_size
        for info in infos:
            if central_pos + 46 > central_end:
                mismatch()
            (marker, _made, version, flags, method, mod_time, mod_date,
             crc, compressed, expanded, name_len, extra_len, comment_len,
             start_disk, _internal, _external, local_offset) = struct.unpack_from(
                "<4s6H3I5H2I", data, central_pos)
            if marker != b"PK\x01\x02":
                mismatch()
            if extra_len or comment_len or info.extra or info.comment:
                metadata()
            if (flags or start_disk or not name_len or
                    local_offset != local_pos or local_offset != info.header_offset or
                    compressed != info.compress_size or expanded != info.file_size or
                    crc != info.CRC or method != info.compress_type):
                mismatch()
            central_name_start = central_pos + 46
            central_next = central_name_start + name_len + extra_len + comment_len
            if central_next > central_end:
                mismatch()
            try:
                expected_name = info.filename.encode("ascii")
            except UnicodeEncodeError:
                mismatch()
            central_name = data[central_name_start:central_name_start + name_len]
            if central_name != expected_name:
                mismatch()

            if local_pos + 30 > dir_offset:
                mismatch()
            (local_marker, local_version, local_flags, local_method,
             local_time, local_date, local_crc, local_compressed,
             local_expanded, local_name_len, local_extra_len) = struct.unpack_from(
                "<4s5H3I2H", data, local_pos)
            if local_extra_len:
                metadata()
            content_start = local_pos + 30 + local_name_len + local_extra_len
            content_end = content_start + compressed
            if (local_marker != b"PK\x03\x04" or local_version != version
                    or local_flags != flags or local_method != method
                    or local_time != mod_time or local_date != mod_date
                    or local_crc != crc or local_compressed != compressed
                    or local_expanded != expanded or local_name_len != name_len
                    or content_end > dir_offset
                    or data[local_pos + 30:local_pos + 30 + name_len] != central_name):
                mismatch()
            # No hidden gap, descriptor, ZIP64 block, or second archive may
            # intervene between consecutive authored files and the directory.
            local_pos = content_end
            central_pos = central_next

        if local_pos != dir_offset or central_pos != central_end:
            mismatch()
    except struct.error as exc:
        raise PreviewArchiveError(
            "archive_structure", "zip_layout_mismatch",
            "Invalid ZIP record bounds") from exc


def _json_unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreviewArchiveError("provenance", "duplicate_metadata_key", "Duplicate metadata JSON key")
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
        raise PreviewArchiveError("archive_structure", "missing_or_unsafe_input", "Missing or unsafe local preview ZIP")
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise PreviewArchiveError("archive_structure", "archive_too_large", "Preview ZIP exceeds archive byte budget")
    try:
        if not _clean_zip_envelope(path):
            raise PreviewArchiveError("archive_structure", "zip_envelope", "Unexpected ZIP prefix, trailer or comment")
        with ZipFile(path) as archive:
            if archive.comment:
                raise PreviewArchiveError("archive_structure", "zip_comment", "Unexpected ZIP archive comment")
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if (not 3 <= len(infos) <= MAX_MEMBERS or
                    len(names) != len(set(names)) or
                    len(names) != len({name.casefold() for name in names})):
                raise PreviewArchiveError("archive_structure", "duplicate_or_count", "Invalid or duplicate preview archive members")
            packages = {name.split("/")[0] for name in names}
            if len(packages) != 1:
                raise PreviewArchiveError("archive_structure", "multiple_packages", "Preview archive must contain exactly one package")
            package = next(iter(packages))
            if package not in KNOWN:
                raise PreviewArchiveError("archive_identity", "unknown_package", "Not a CBDK-authored preview ZIP")
            prefix = package + "/"
            for info in infos:
                name = info.filename
                components = name.split("/")
                if (not name.startswith(prefix) or
                        len(components) < 2 or
                        any(x in ("", ".", "..") for x in components) or
                        "\\" in name or not name.isprintable() or info.is_dir() or
                        info.file_size > MAX_ENTRY_BYTES or
                        info.compress_type not in (ZIP_DEFLATED, ZIP_STORED) or
                        info.flag_bits & (0x01 | 0x40) or
                        stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG)):
                    raise PreviewArchiveError("archive_structure", "unsafe_member", "Unsafe preview archive member")
            if sum(info.file_size for info in infos) > MAX_ARCHIVE_BYTES:
                raise PreviewArchiveError("archive_structure", "uncompressed_budget", "Preview archive uncompressed size budget exceeded")
            _verify_canonical_zip_layout(archive, infos)
            meta_path = prefix + "CBDK_BUILD_INFO.json"
            if meta_path not in names:
                raise PreviewArchiveError("provenance", "missing_metadata", "Missing CBDK build provenance")
            try:
                metadata = json.loads(
                    archive.read(meta_path).decode("utf-8"),
                    object_pairs_hook=_json_unique,
                )
            except (json.JSONDecodeError, RecursionError) as exc:
                raise PreviewArchiveError("provenance", "invalid_json", "Invalid CBDK provenance JSON") from exc
            if not isinstance(metadata, dict):
                raise PreviewArchiveError("provenance", "invalid_metadata", "Invalid CBDK provenance")
            schema, expected_template = KNOWN[package]
            if (type(metadata.get("schema_version")) is not int
                    or metadata["schema_version"] != schema
                    or metadata.get("template") != expected_template
                    or metadata.get("package_id") != package
                    or metadata.get("preview_only") is not True
                    or metadata.get("approved") is not False
                    or metadata.get("redistribution_cleared") is not False
                    or metadata.get("blender_runtime_verified_for_this_build") is not False):
                raise PreviewArchiveError("provenance", "unsafe_approval_flag", "Preview origin or approval state is not trusted")
            digests = metadata.get("files_sha256")
            if not isinstance(digests, dict):
                raise PreviewArchiveError("provenance", "missing_hash_inventory", "Missing file hash inventory")
            rels = {name.removeprefix(prefix) for name in names if name != meta_path}
            if set(digests) != rels or "__init__.py" not in rels:
                raise PreviewArchiveError("provenance", "member_inventory_mismatch", "CBDK archive members disagree with provenance")
            for rel in sorted(rels):
                digest = digests[rel]
                if not isinstance(digest, str) or not SHA.fullmatch(digest):
                    raise PreviewArchiveError("archive_integrity", "invalid_hash", "Invalid provenance SHA256")
                if hashlib.sha256(archive.read(prefix + rel)).hexdigest() != digest:
                    raise PreviewArchiveError("archive_integrity", "hash_mismatch", "CBDK preview file changed since build")
            if schema == 2:
                selected = metadata.get("features")
                if (not isinstance(selected, list) or
                        not selected or len(selected) > 5 or
                        any(type(s) is not str or s not in {
                            "object_selection", "edit_selection", "mesh_bounds",
                            "modifier_summary", "vertex_nudge"} for s in selected)
                        or len(selected) != len(set(selected))):
                    raise PreviewArchiveError("dependency_closure", "feature_inventory", "Preview feature inventory is not allowlisted")
                if {n.removeprefix("features/").removesuffix(".py")
                        for n in rels if n.startswith("features/") and
                        n != "features/__init__.py"} != set(selected):
                    raise PreviewArchiveError("dependency_closure", "feature_modules", "Preview feature modules disagree with provenance")
            parts = metadata.get("parts")
            if (not isinstance(parts, list) or not parts or len(parts) > 7
                    or any(not isinstance(p, dict) or
                           p.get("catalog_approved") is not False or
                           p.get("license_review") not in ("pending", "not_reviewed")
                           for p in parts)):
                raise PreviewArchiveError("provenance", "part_state", "Preview part approvals or license metadata are unexpected")
            from .feature_catalog import TRUSTED_FEATURES, TRUSTED_PART_SOURCES
            from .modular_builder import HELPERS
            expected_parts = ({p for f in selected for p in TRUSTED_FEATURES[f]["parts"]}
                              if schema == 2 else {"BLCTX-001", "BLCTX-002", "BME-001"})
            ids = [p.get("part_id") for p in parts]
            if any(type(p) is not str for p in ids) or len(set(ids)) != len(ids) or set(ids) != expected_parts:
                raise PreviewArchiveError("dependency_closure", "part_ids", "Preview part dependency inventory mismatch")
            expected_files = {"__init__.py", "README.txt", "helpers/__init__.py"}
            expected_files |= {HELPERS[TRUSTED_PART_SOURCES[p]] for p in expected_parts}
            if schema == 2:
                expected_files |= {"features/__init__.py"} | {"features/" + f + ".py" for f in selected}
                if metadata.get("part_ids") != sorted(expected_parts):
                    raise PreviewArchiveError("dependency_closure", "dependency_ids", "Preview dependency list mismatch")
            if rels != expected_files:
                raise PreviewArchiveError("dependency_closure", "file_inventory", "Preview contains undeclared helper or file")
            # Every part must agree with the trusted static source mapping
            # AND with the already-verified packaged helper digest. Metadata
            # itself remains self-asserted; no authorship or license clearance.
            for part in parts:
                source = TRUSTED_PART_SOURCES[part["part_id"]]
                helper = HELPERS[source]
                part_hash = part.get("source_sha256" if schema == 2 else "sha256")
                if (part.get("source") != source or
                        type(part_hash) is not str or
                        not SHA.fullmatch(part_hash) or
                        part_hash != digests[helper]):
                    raise PreviewArchiveError(
                        "provenance", "part_provenance_mismatch",
                        "Preview part source or digest disagrees with package")
            # All validation above is structural. Never import any bundled source.
            source_count = len(rels)
    except (BadZipFile, UnicodeDecodeError, KeyError, OSError, RuntimeError,
            EOFError, zlib.error, RecursionError, json.JSONDecodeError) as exc:
        raise PreviewArchiveError("archive_integrity", "corrupt_or_unreadable", "Invalid CBDK preview ZIP") from exc

    minimum_blender = metadata.get("minimum_blender", "4.4.0")
    if (type(minimum_blender) is not str or not VERSION.fullmatch(minimum_blender)
            or tuple(map(int, minimum_blender.split("."))) < (4, 2, 0)):
        raise PreviewArchiveError("provenance", "invalid_minimum_blender", "Invalid minimum Blender provenance")
    fields = {
        "schema_version": "1.0.0",
        "id": package,
        # The recipe display name is self-asserted metadata, not a trusted
        # identity field. Do not copy potentially private text into reports.
        "name": "CBDK Authored Development Preview",
        "tagline": "Authored mesh inspection development preview",
        "type": "add-on",
        "blender_version_min": minimum_blender,
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


def diagnose_preview_archive(source: str | Path) -> dict:
    """Data-only diagnostic API; an invalid archive never becomes release-blocked.

    The normal CLI still fails closed on invalid inputs. This optional API
    supplies stable failure categories without disclosing an input path,
    archive member, parser payload, or private source.
    """
    try:
        return inspect_preview_archive(source)
    except ValueError as exc:
        return {
            "schema_version": 1,
            "kind": "cbdk_extension_readiness_preflight",
            "status": "invalid_preview_archive",
            "failure_category": getattr(exc, "category", "unclassified_invalid_archive"),
            "failure_code": getattr(exc, "code", "invalid_input"),
            "archive_structure_checked": False,
            "provenance_hashes_verified": False,
            "source_authenticity_verified": False,
            "python_code_executed": False,
            "extension_zip_created": False,
            "official_blender_extension_validate_ran": False,
            "release_authorized": False,
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
