"""Bounded synthetic Extension generation, not a real-addon conversion API.

No caller-supplied source, members, directories to scan, license inference,
installation or distribution. Manifest text is an intentional artifact;
diagnostics contain only fixed reason codes/counts, never metadata values.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import stat
import tomllib
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from .extension_manifest import PERMISSION_KEYS, SUPPORTED, review_manifest_fields
from .extension_manifest_review import MAX_BYTES
from .extension_preflight import MAX_ARCHIVE_BYTES, MAX_ENTRY_BYTES, MAX_MEMBERS

FIXTURE_ID = "cbdk_synthetic_extension_fixture"
# Fail visibly if anyone attempts to import/install this validation fixture.
FIXTURE_INIT = b'raise RuntimeError("CBDK synthetic validation fixture; do not install")\n'
MANIFEST_NAME = "blender_manifest.toml"
MEMBER_NAMES = ("__init__.py", MANIFEST_NAME)


def render_synthetic_manifest(fields: dict) -> bytes:
    """Emit only reviewed fields for the reserved, non-installable fixture.

    Explicit metadata required: no defaults for author, license or purpose.
    JSON quoting with ensure_ascii=False is TOML basic-string compatible for
    the bounded printable subset. Parse and compare to detect any mismatch.
    """
    if type(fields) is not dict or len(fields) > len(SUPPORTED):
        raise ValueError("Unsupported synthetic manifest structure")
    review = review_manifest_fields(fields)
    if review["status"] != "structurally_valid_subset":
        raise ValueError("Synthetic manifest incomplete or unsupported")
    if fields["id"] != FIXTURE_ID or fields["type"] != "add-on":
        raise ValueError("Only the reserved synthetic add-on fixture is supported")

    def quoted(value):
        return json.dumps(value, ensure_ascii=False)

    lines = []
    for key in SUPPORTED:
        if key not in fields or key == "permissions":
            continue
        value = fields[key]
        literal = ("[" + ", ".join(quoted(item) for item in value) + "]"
                   if key == "license" else quoted(value))
        lines.append(key + " = " + literal)
    if "permissions" in fields:
        lines.extend(("", "[permissions]"))
        for key in sorted(fields["permissions"]):
            if key not in PERMISSION_KEYS:
                raise ValueError("Unsupported permission")
            lines.append(key + " = " + quoted(fields["permissions"][key]))
    try:
        data = ("\n".join(lines) + "\n").encode("utf-8")
        if len(data) > MAX_BYTES or tomllib.loads(data.decode("utf-8")) != fields:
            raise ValueError("Synthetic manifest round-trip mismatch")
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError("Synthetic manifest encoding failed") from None
    if review_manifest_fields(tomllib.loads(data.decode("utf-8"))) != review:
        raise ValueError("Synthetic manifest review mismatch")
    return data


def synthetic_extension_members(fields: dict) -> dict[str, bytes]:
    """The only available inventory is code-owned and two root members."""
    return {"__init__.py": FIXTURE_INIT, MANIFEST_NAME: render_synthetic_manifest(fields)}


def verify_synthetic_extension_bytes(data: bytes, fields: dict) -> dict:
    """Verify exact two-member contents of a locally generated fixture.

    Accept the official CLI's normal stored/deflated ZIP encoding as well
    as our deterministic stored ZIP. Not a general untrusted ZIP validator.
    No extraction; check names, declared sizes, duplicate names, modes,
    CRC (ZipFile.read), and byte-for-byte content against fixed inventory.
    """
    expected = synthetic_extension_members(fields)
    if type(data) is not bytes or not 0 < len(data) <= MAX_ARCHIVE_BYTES:
        raise ValueError("Synthetic archive size outside limit")
    try:
        with ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if (not len(infos) == len(expected) <= MAX_MEMBERS
                    or len({info.filename for info in infos}) != len(infos)
                    or {info.filename for info in infos} != set(expected)
                    or sum(info.file_size for info in infos) > MAX_ARCHIVE_BYTES):
                raise ValueError("Synthetic archive inventory mismatch")
            for info in infos:
                mode = stat.S_IFMT(info.external_attr >> 16)
                if (info.orig_filename != info.filename or info.is_dir()
                        or mode not in (0, stat.S_IFREG)
                        or info.flag_bits & 1
                        or info.compress_type not in (ZIP_STORED, ZIP_DEFLATED)
                        or info.file_size > MAX_ENTRY_BYTES
                        or info.file_size != len(expected[info.filename])):
                    raise ValueError("Synthetic archive member invalid")
                if archive.read(info) != expected[info.filename]:
                    raise ValueError("Synthetic archive content mismatch")
    except (BadZipFile, OSError, RuntimeError, NotImplementedError, KeyError):
        raise ValueError("Synthetic archive cannot be verified") from None
    return {
        "kind": "cbdk_synthetic_extension_fixture",
        "status": "synthetic_archive_verified",
        "member_count": len(expected),
        "manifest_roundtrip_verified": True,
        "exact_fixture_content_verified": True,
        "official_validation_ran": False,
        "source_executed": False,
        "real_component_license_chosen": False,
        "owner_approval_verified": False,
        "release_authorized": False,
        "install_authorized": False,
    }


def build_synthetic_extension_bytes(fields: dict) -> bytes:
    """Deterministic root ZIP; fixed timestamp, order, mode and no compression."""
    members = synthetic_extension_members(fields)
    if (len(members) > MAX_MEMBERS or any(len(v) > MAX_ENTRY_BYTES for v in members.values())
            or sum(map(len, members.values())) > MAX_ARCHIVE_BYTES):
        raise ValueError("Synthetic archive exceeds content budget")
    stream = io.BytesIO()
    with ZipFile(stream, "w", compression=ZIP_STORED, allowZip64=False) as archive:
        for name in MEMBER_NAMES:
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = ZIP_STORED
            archive.writestr(info, members[name])
    data = stream.getvalue()
    verify_synthetic_extension_bytes(data, fields)
    return data


def write_synthetic_extension_zip(fields: dict, output: str | Path) -> dict:
    """Write only to a fresh ZIP under a caller-chosen existing directory.

    Validate fully before creating output, never replace an existing file,
    no directory creation. The caller must control the output directory;
    this is not a sandbox for concurrent hostile filesystem changes.
    """
    data = build_synthetic_extension_bytes(fields)
    path = Path(output)
    if (path.suffix != ".zip" or not path.parent.is_dir()
            or path.parent.is_symlink() or path.is_symlink()):
        raise ValueError("Expected fresh synthetic ZIP destination")
    try:
        with path.open("xb") as stream:
            stream.write(data)
    except OSError:
        raise ValueError("Synthetic ZIP destination unavailable") from None
    return verify_synthetic_extension_bytes(data, fields)
