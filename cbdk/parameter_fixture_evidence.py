"""R26 internal fixed-parameter evidence consistency check, not an authority.

The trusted parent supplies independently expected identity and actual
observations. No source execution, path, arbitrary log or numeric recommendation.
As in R25, identical hashes/run IDs establish consistency, not authenticity.
"""
from __future__ import annotations

import re

from .extension_stage_evidence import VERSIONS

CASE = "parameter_fixture_r26"
PROPERTIES = ("sphere_radius", "bevel_width")
IDENTITY = frozenset({"case", "blender", "run_id", "source_sha256"})
STATIC_COUNTS = ("declaration_count", "same_class_self_count", "geometry_path_count")
STATIC_FLAGS = ("expected_api_observed",)
NATIVE_FLAGS = (
    "registered_on_expected_instance", "value_readback_verified",
    "target_changed_generated", "target_changed_imported",
    "unrelated_unchanged_generated", "unrelated_unchanged_imported",
)
RUN_FLAGS = ("cleanup_verified", "source_unchanged")
_HEX32 = re.compile(r"[0-9a-f]{32}")
_HEX64 = re.compile(r"[0-9a-f]{64}")


def _identity(case, blender, run_id, source_sha256):
    return (type(case) is str and case == CASE
            and type(blender) is str and blender in VERSIONS
            and type(run_id) is str and _HEX32.fullmatch(run_id) is not None
            and type(source_sha256) is str and _HEX64.fullmatch(source_sha256) is not None)


def _summary(status, reasons, *, identity=None, properties=(), cleanup=None, unchanged=None):
    return {
        "schema_version": 1, "suite": "fixed_parameter_evidence_r26",
        "status": status, "reason_codes": list(reasons),
        **(identity if identity is not None else dict.fromkeys(sorted(IDENTITY))),
        "properties": list(properties), "cleanup_verified": cleanup,
        "source_unchanged": unchanged,
        "same_fixture_observations_verified": status == "verified_fixed_observations",
        "safety": {
            "authenticates_observations": False, "causality_proven": False,
            "measurement_cause_verified": False, "optimal_value_verified": False,
            "generalizes_to_user_addons": False, "user_addon_executed": False,
            "source_execution_authorized": False, "applies_parameters": False,
            "edits_code": False, "auto_approves": False, "auto_adopts": False,
            "redistribution_authorized": False,
        },
    }


def _rows(envelope, identity, *, native):
    """None/partial property inventory is incomplete; bad records are rejected."""
    if envelope is None:
        return {}, None, None
    extra = set(RUN_FLAGS) if native else set()
    if type(envelope) is not dict or set(envelope) != IDENTITY | {"properties"} | extra:
        raise ValueError("evidence_mismatch")
    if not _identity(*(envelope[k] for k in ("case", "blender", "run_id", "source_sha256"))):
        raise ValueError("evidence_mismatch")
    if any(envelope[k] != v for k, v in identity.items()):
        raise ValueError("identity_mismatch")
    if native and any(type(envelope[k]) is not bool for k in RUN_FLAGS):
        raise ValueError("evidence_mismatch")
    rows = envelope["properties"]
    if type(rows) is not list or len(rows) > len(PROPERTIES):
        raise ValueError("evidence_mismatch")
    found = {}
    fields = {"property", *NATIVE_FLAGS} if native else {"property", *STATIC_COUNTS, *STATIC_FLAGS}
    for row in rows:
        if (type(row) is not dict or set(row) != fields
                or type(row["property"]) is not str or row["property"] not in PROPERTIES
                or row["property"] in found):
            raise ValueError("evidence_mismatch")
        if any(type(row[k]) is not bool for k in (NATIVE_FLAGS if native else STATIC_FLAGS)):
            raise ValueError("evidence_mismatch")
        if not native:
            if any(type(row[k]) is not int or not 0 <= row[k] <= 10000 for k in STATIC_COUNTS):
                raise ValueError("evidence_mismatch")
            if row["expected_api_observed"] and row["geometry_path_count"] == 0:
                raise ValueError("contradictory_observation")
        elif row["value_readback_verified"] and not row["registered_on_expected_instance"]:
            raise ValueError("contradictory_observation")
        found[row["property"]] = row
    return found, envelope.get("cleanup_verified"), envelope.get("source_unchanged")


def reduce_parameter_evidence(static, native, *, case, blender, run_id, source_sha256):
    """Reduce normalized, fixed, independently bound static/native observations.

    Missing entire envelopes or property rows produce incomplete evidence.
    Malformed/unknown/duplicate rows, contradictory flags or differing identity
    reject the whole report. Explicit negative observations never become success.
    All per-property flags refer to the fixed target/unrelated object pairing;
    the trusted parent must independently derive and check them against the
    actual seven-variant measurements (not a success marker). This reducer
    does not validate the raw meshes or establish causality.
    """
    if not _identity(case, blender, run_id, source_sha256):
        return _summary("rejected", ("evidence_mismatch",))
    identity = dict(case=case, blender=blender, run_id=run_id, source_sha256=source_sha256)
    try:
        ast, _, _ = _rows(static, identity, native=False)
        runtime, cleanup, unchanged = _rows(native, identity, native=True)
    except ValueError as exc:
        return _summary("rejected", (str(exc),))

    results = []
    reasons = []
    negative = False
    missing = False
    for prop in PROPERTIES:
        a, n = ast.get(prop), runtime.get(prop)
        issues = []
        absent = []
        if a is None:
            absent.append("static_observation_missing")
        else:
            if a["declaration_count"] != 1:
                issues.append("static_declaration_missing" if a["declaration_count"] == 0
                              else "static_declaration_ambiguous")
            if a["same_class_self_count"] == 0:
                issues.append("same_class_reference_missing")
            if a["geometry_path_count"] == 0:
                issues.append("geometry_path_missing")
            if not a["expected_api_observed"]:
                issues.append("expected_api_missing")
        if n is None:
            absent.append("native_observation_missing")
        else:
            if not n["registered_on_expected_instance"]:
                issues.append("registration_unverified")
            if not n["value_readback_verified"]:
                issues.append("readback_unverified")
            if not n["target_changed_generated"]:
                issues.append("generated_target_effect_unverified")
            if not n["target_changed_imported"]:
                issues.append("imported_target_effect_unverified")
            if not n["unrelated_unchanged_generated"]:
                issues.append("generated_unrelated_changed_or_unverified")
            if not n["unrelated_unchanged_imported"]:
                issues.append("imported_unrelated_changed_or_unverified")
        negative |= bool(issues)
        missing |= bool(absent)
        reasons.extend(issues + absent)
        results.append({
            "property": prop,
            "status": "unverified" if issues else "incomplete" if absent else "matched",
            "reason_codes": issues + absent,
            "static_observation": dict(a) if a is not None else None,
            "native_observation": dict(n) if n is not None else None,
        })
    if cleanup is not True:
        reasons.append("cleanup_unverified")
        missing |= cleanup is None
        negative |= cleanup is False
    if unchanged is not True:
        reasons.append("source_unchanged_unverified")
        missing |= unchanged is None
        negative |= unchanged is False
    status = "unverified" if negative else "incomplete" if missing else "verified_fixed_observations"
    return _summary(status, dict.fromkeys(reasons), identity=identity, properties=results,
                    cleanup=cleanup, unchanged=unchanged)
