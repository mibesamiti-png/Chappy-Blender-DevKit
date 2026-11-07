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
RULES = {
    "schema_version": "Use manifest schema 1.0.0",
    "id": "Use an ASCII identifier without leading/trailing or doubled underscores",
    "version": "Use SemVer major.minor.patch with valid optional prerelease/build identifiers",
    "name": "Provide a nonempty printable name without surrounding whitespace",
    "tagline": "Use at most 64 characters ending in a letter, digit or closing bracket",
    "maintainer": "Owner must provide printable maintainer metadata without surrounding whitespace",
    "type": "Choose add-on or theme",
    "blender_version_min": "Use three numeric components and at least Blender 4.2.0",
    "license": "Owner must review SPDX identifiers and component license compatibility separately",
}


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


def manifest_field_diagnostics(fields):
    """Actionable known-field diagnostics without copying any input values."""
    review = review_manifest_fields(fields)
    invalid = {row["field"] for row in review["errors"]}
    return [{"field": field,
             "status": "missing" if field in review["missing_required_fields"] else
                       "invalid" if field in invalid else "valid_in_supported_subset",
             "guidance": RULES[field]} for field in REQUIRED]


def observe_official_validation(returncode, output):
    """Normalize bounded CLI output, omitting paths, values and unknown text.

    An exit code alone is insufficient. Unknown/new output formats are
    unclassified, never silently promoted to validator success or rejection.
    This recognizes observations; it does not authenticate the caller/log.
    """
    if type(returncode) is not int or not isinstance(output, str) or len(output) > 200_000:
        raise ValueError("Invalid or oversized official validation observation")
    diagnostics = set()
    success = False
    for line in output.splitlines():
        line = line.strip()
        if line.startswith('Success parsing TOML in "'):
            success = True
        missing = re.fullmatch(r'missing "([a-z_]+)"', line)
        invalid = re.match(r'key "([a-z_]+)" invalid:', line)
        if missing and missing[1] in REQUIRED:
            diagnostics.add((missing[1], "missing"))
        if invalid and invalid[1] in REQUIRED:
            diagnostics.add((invalid[1], "invalid"))
    status = ("accepted" if returncode == 0 and success and not diagnostics else
              "rejected" if returncode > 0 and diagnostics and not success else "unclassified")
    return {"status": status,
            "diagnostics": [{"field": field, "code": code} for field, code in sorted(diagnostics)],
            "authenticates_log": False}


def compare_official_validation(fields, returncode, output):
    local = review_manifest_fields(fields)
    observed = observe_official_validation(returncode, output)
    expected = {(field, "missing") for field in local["missing_required_fields"]}
    expected |= {(row["field"], "invalid") for row in local["errors"]}
    actual = {(row["field"], row["code"]) for row in observed["diagnostics"]}
    if any(row["field"] not in REQUIRED for row in local["errors"]):
        status = "outside_supported_subset"
    elif observed["status"] == "unclassified":
        status = "unclassified"
    elif observed["status"] == "accepted":
        status = "agreement" if local["status"] == "structurally_valid_subset" else "disagreement"
    elif expected == actual:
        status = "agreement"
    elif actual and actual < expected:
        status = "partial_diagnostic_agreement"
    else:
        status = "disagreement"
    return {"status": status, "local_status": local["status"], "official_observation": observed,
            "complete_diagnostic_agreement": status == "agreement",
            "owner_approval_verified": False, "license_compatibility_verified": False}
