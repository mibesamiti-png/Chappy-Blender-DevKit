"""Offline subset of Blender's manifest rules, separate from legal approval.

No TOML emission, license selection, package build or source execution. Optional
fields outside this bounded subset need the official Blender validator.
"""
from __future__ import annotations
import re

REQUIRED = ("schema_version", "id", "version", "name", "tagline", "maintainer",
            "type", "blender_version_min", "license")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$")
VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SPDX = re.compile(r"^SPDX:[A-Za-z0-9][A-Za-z0-9.+-]{0,99}$")


def review_manifest_fields(fields):
    if not isinstance(fields, dict) or any(type(k) is not str for k in fields):
        raise ValueError("Manifest fields must be an object")
    missing, errors = [], []
    for key in REQUIRED:
        value = fields.get(key)
        if value is None:
            missing.append(key)
            continue
        valid = True
        if key == "license":
            valid = (type(value) is list and 1 <= len(value) <= 16
                     and all(type(v) is str and SPDX.fullmatch(v) for v in value)
                     and len(set(value)) == len(value))
        elif not (type(value) is str and 1 <= len(value) <= 256
                  and value == value.strip() and value.isprintable()):
            valid = False
        elif key == "schema_version":
            valid = value == "1.0.0"
        elif key == "id":
            valid = value.isascii() and value.isidentifier() and "__" not in value and not value.startswith("_") and not value.endswith("_")
        elif key == "version":
            valid = value.isascii() and SEMVER.fullmatch(value) is not None
            if valid and "-" in value.split("+", 1)[0]:
                identifiers = value.split("+", 1)[0].split("-", 1)[1].split(".")
                valid = all(s and not (s.isdigit() and len(s) > 1 and s.startswith("0")) for s in identifiers)
        elif key == "type":
            valid = value in ("add-on", "theme")
        elif key == "tagline":
            valid = len(value) <= 64 and (value[-1].isalnum() or value[-1] in ")]}")
        elif key == "blender_version_min":
            valid = value.isascii() and VERSION.fullmatch(value) is not None and tuple(map(int, value.split("."))) >= (4, 2, 0)
        if not valid:
            errors.append({"field": key, "code": "invalid_" + key})
    for key in sorted(set(fields) - set(REQUIRED)):
        errors.append({"field": key, "code": "unsupported_field_requires_official_validation"})
    return {"status": "invalid" if errors else "incomplete" if missing else "structurally_valid_subset",
            "missing_required_fields": missing, "errors": errors,
            "license_identifier_syntax_checked": "license" not in missing and not any(e["field"] == "license" for e in errors),
            "license_registry_or_compatibility_verified": False,
            "owner_approval_verified": False, "official_validation_ran": False}
