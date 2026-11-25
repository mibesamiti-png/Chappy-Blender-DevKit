"""Offline subset of Blender's manifest rules, separate from legal approval.

No TOML emission, license selection, package build or source execution. Optional
fields outside this bounded subset need the official Blender validator.
"""
from __future__ import annotations
import re

REQUIRED = ("schema_version", "id", "version", "name", "tagline", "maintainer",
            "type", "blender_version_min", "license")
OPTIONAL = ("blender_version_max", "permissions")
SUPPORTED = REQUIRED + OPTIONAL
PERMISSION_KEYS = frozenset(("files", "network", "clipboard", "camera", "microphone"))
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
    "blender_version_max": "Optional exclusive upper Blender version; use three numeric components above the minimum",
    "permissions": "Optional table of known add-on permission names and short printable purpose descriptions; owner must review actual needs",
}


def _version_tuple(value):
    if (type(value) is str and 1 <= len(value) <= 256
            and value.isascii() and VERSION.fullmatch(value)):
        return tuple(map(int, value.split(".")))
    return None


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
    # Optional absence is not a missing owner input. Explicit invalid values
    # are distinct from an unknown field outside the reviewed subset.
    if "blender_version_max" in fields:
        maximum = fields["blender_version_max"]
        valid = _version_tuple(maximum) is not None
        minimum = _version_tuple(fields.get("blender_version_min"))
        if valid and minimum is not None:
            valid = _version_tuple(maximum) > minimum
        if not valid:
            errors.append({"field": "blender_version_max", "code": "invalid_blender_version_max"})
    if "permissions" in fields:
        permissions = fields["permissions"]
        valid = (type(permissions) is dict and len(permissions) <= len(PERMISSION_KEYS)
                 and all(type(k) is str and k in PERMISSION_KEYS
                         and type(v) is str and 1 <= len(v) <= 64
                         and v == v.strip() and v.isprintable()
                         and (v[-1].isalnum() or v[-1] in ")]}")
                         for k, v in permissions.items()))
        # This bounded policy only supports the known add-on permission table.
        if valid and permissions and fields.get("type") != "add-on":
            valid = False
        if not valid:
            errors.append({"field": "permissions", "code": "invalid_permissions"})
    # Never return unknown key names, even from the dictionary-level API.
    for _ in set(fields) - set(SUPPORTED):
        errors.append({"field": "unsupported_field", "code": "unsupported_field_requires_official_validation"})
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
                       "invalid" if field in invalid else
                       "optional_not_provided" if field in OPTIONAL and field not in fields else
                       "valid_in_supported_subset",
             "guidance": RULES[field]} for field in SUPPORTED]


def observe_official_validation(returncode, output):
    """Normalize bounded official CLI output; never trust exit status alone.

    Treat unknown, repeated, or contradictory diagnostics and parser status
    lines as unclassified. The only ignored noise is a known Blender version
    banner, its clean shutdown line, and blank lines. Unknown free-form
    messages cannot silently turn a partial result into full agreement.
    Original validator values, paths and free-form log text are not returned.
    This checks consistency, NOT authenticity of the supplied observation.
    """
    if type(returncode) is not int or not isinstance(output, str) or len(output) > 200_000:
        raise ValueError("Invalid or oversized official validation observation")
    diagnostics = set()
    success = False
    error_header = False
    unknown = False
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "Blender quit" or re.fullmatch(
                r"Blender \d+\.\d+\.\d+(?: LTS)?(?: \(hash [0-9a-f]{7,} built \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\))?", line):
            continue
        if line.startswith('Success parsing TOML in "'):
            if (not re.fullmatch(r'Success parsing TOML in "[^"]+"', line)
                    or success or error_header or diagnostics):
                unknown = True
            success = True
            continue
        if line.startswith('Error parsing TOML '):
            # A generic error header is only meaningful alongside recognized
            # field diagnostics; duplicate headers and success conflicts are
            # never a successful observation.
            if (not re.fullmatch(r'Error parsing TOML "[^"]+"', line)
                    or error_header or success or diagnostics):
                unknown = True
            error_header = True
            continue
        if line.startswith('missing "'):
            match = re.fullmatch(r'missing "([a-z_]+)"', line)
            if (match and match[1] in REQUIRED and not success
                    and not any(field == match[1] for field, _ in diagnostics)):
                diagnostics.add((match[1], "missing"))
            else:
                unknown = True
            continue
        if line.startswith('key "'):
            match = re.match(r'key "([a-z_]+)" invalid:', line)
            if (match and match[1] in SUPPORTED and not success
                    and not any(field == match[1] for field, _ in diagnostics)):
                diagnostics.add((match[1], "invalid"))
            else:
                unknown = True
            continue
        # Fail closed even for unfamiliar wording such as "validator halted".
        # Never echo this text in the observation or downstream comparison.
        unknown = True
    status = ("accepted" if returncode == 0 and success and not diagnostics
              and not unknown and not error_header else
              "rejected" if returncode > 0 and diagnostics and not success
              and not unknown else
              "unclassified")
    return {"status": status,
            "diagnostics": [{"field": field, "code": code} for field, code in sorted(diagnostics)],
            "has_unrecognized_diagnostics": unknown,
            "authenticates_log": False}



def compare_official_validation(fields, returncode, output):
    local = review_manifest_fields(fields)
    observed = observe_official_validation(returncode, output)
    expected = {(field, "missing") for field in local["missing_required_fields"]}
    expected |= {(row["field"], "invalid") for row in local["errors"]}
    actual = {(row["field"], row["code"]) for row in observed["diagnostics"]}
    if any(row["field"] not in SUPPORTED for row in local["errors"]):
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
