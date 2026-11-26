"""R27 fixed source-change evidence reducer. No file I/O or execution.

Parent-owned actual observations, not arbitrary source, are inputs. SHA
consistency is not authenticity or permission. Only the pinned fixture's
one allowed edit and its restoration are within this contract.
"""
from __future__ import annotations

import math

from .extension_stage_evidence import VERSIONS, _is_digest
from .parameter_fixture_evidence import _HEX32

CASE = "parameter_source_r27"
PROPERTY = "sphere_radius"
SOURCE_SHA256 = "e645723ff89a99530841e1ccd37ea8d059952eec0f980ac1782d8228e46588e3"
CANDIDATE_SHA256 = "edde3abe885bf40830052068fcdd6cab57d3d945fdccbc5f3625cff4594c72d7"
BYTE_OFFSET = 570
STAGES = ("original", "candidate", "restored")
SPHERE = "CBDK_Param_Sphere"
CUBE = "CBDK_Param_BevelCube"
MESH_FIELDS = {"mesh_vertex_count", "mesh_polygon_count", "mesh_coordinate_sha256", "world_dimensions"}
MEASUREMENT_FIELDS = {"glb_sha256", "generated_mesh", "imported_glb_mesh"}
IDENTITY = {"case_id", "run_id", "blender_version", "source_sha256", "candidate_sha256", "property"}
DIFF_FIELDS = {"before", "after", "old_token", "new_token", "byte_offset",
               "single_diff_verified", "ast_diff_verified", "restored_sha256"}
RUN_FLAGS = {"isolated_copy_verified", "restoration_verified", "original_source_unchanged",
             "reference_sha_unchanged"}
STAGE_FIELDS = IDENTITY | MEASUREMENT_FIELDS | {
    "stage", "actual_source_sha256", "sphere_radius", "bevel_width",
    "registered", "cleanup_verified"}


def _fail(code):
    raise ValueError(code)


def _identity(run_id, blender_version):
    if (type(run_id) is not str or _HEX32.fullmatch(run_id) is None
            or type(blender_version) is not str or blender_version not in VERSIONS):
        _fail("identity_mismatch")
    return dict(case_id=CASE, run_id=run_id, blender_version=blender_version,
                source_sha256=SOURCE_SHA256, candidate_sha256=CANDIDATE_SHA256,
                property=PROPERTY)


def _record(data, fields):
    if type(data) is not dict or set(data) != fields:
        _fail("evidence_mismatch")


def _bound(data, identity):
    if any(type(data[k]) is not str or data[k] != v for k, v in identity.items()):
        _fail("identity_mismatch")


def _number(value):
    return (type(value) in (int, float) and -10000 <= value <= 10000
            and math.isfinite(value))


def _flags(data, keys):
    if any(type(data[k]) is not bool for k in keys):
        _fail("evidence_mismatch")


def _mesh(data):
    _record(data, {SPHERE, CUBE})
    for row in data.values():
        _record(row, MESH_FIELDS)
        for key in ("mesh_vertex_count", "mesh_polygon_count"):
            if type(row[key]) is not int or not 0 < row[key] <= 100000:
                _fail("measurement_invalid")
        if not _is_digest(row["mesh_coordinate_sha256"]):
            _fail("measurement_invalid")
        dims = row["world_dimensions"]
        if (type(dims) is not list or len(dims) != 3
                or any(not _number(x) or x <= 0 for x in dims)):
            _fail("measurement_invalid")


def _measurement(row):
    if not _is_digest(row["glb_sha256"]):
        _fail("measurement_invalid")
    for key in ("generated_mesh", "imported_glb_mesh"):
        _mesh(row[key])


def _summary(status, reasons, identity=None):
    return {"schema_version": 1, "suite": "fixed_parameter_source_evidence_r27",
            "status": status, "reason_codes": list(dict.fromkeys(reasons)),
            **(identity if identity is not None else dict.fromkeys(sorted(IDENTITY))),
            "same_fixture_change_restoration_verified": status == "verified_fixed_observations",
            "safety": {k: False for k in (
                "authenticates_observations", "causality_proven", "optimal_value_verified",
                "general_geometry_equivalence_verified", "generalizes_to_user_addons",
                "user_addon_executed", "source_execution_authorized", "applies_parameters",
                "edits_user_code", "auto_approves", "auto_adopts", "redistribution_authorized")}}


def reduce_source_evidence(diff, native, *, run_id, blender_version,
                           source_sha256, candidate_sha256, measured, references):
    """Reconcile fixed records with independent parent expectations.

    measured: mapping original/candidate/restored -> actual GLB SHA and
    generated/imported fixed object measurements. references: baseline and
    sphere_radius_changed -> same measurement shape, from the same R26 job.
    Parent must derive these from real source copies/files/observations,
    not copy assertions or success markers from the submitted records.
    The reducer itself never reads or executes any file.
    """
    try:
        identity = _identity(run_id, blender_version)
        if (type(source_sha256) is not str or source_sha256 != SOURCE_SHA256
                or type(candidate_sha256) is not str or candidate_sha256 != CANDIDATE_SHA256):
            _fail("source_digest_mismatch")
        reasons = []
        missing = []
        if diff is None:
            missing.append("diff_missing")
        else:
            _record(diff, IDENTITY | DIFF_FIELDS)
            _bound(diff, identity)
            _flags(diff, {"single_diff_verified", "ast_diff_verified"})
            if (not _number(diff["before"]) or diff["before"] != 0.75
                    or not _number(diff["after"]) or diff["after"] != 1.15
                    or type(diff["old_token"]) is not str or diff["old_token"] != "0.75"
                    or type(diff["new_token"]) is not str or diff["new_token"] != "1.15"
                    or type(diff["byte_offset"]) is not int or diff["byte_offset"] != BYTE_OFFSET
                    or diff["restored_sha256"] != SOURCE_SHA256
                    or type(diff["restored_sha256"]) is not str):
                _fail("fixed_diff_mismatch")
            if not diff["single_diff_verified"] or not diff["ast_diff_verified"]:
                reasons.append("single_change_unverified")
        rows = {}
        if native is None:
            missing.append("native_missing")
        else:
            _record(native, IDENTITY | RUN_FLAGS | {"stages", "restored_copy_sha256", "reference_glb_sha256"})
            _bound(native, identity)
            _flags(native, RUN_FLAGS)
            if type(native["restored_copy_sha256"]) is not str or native["restored_copy_sha256"] != SOURCE_SHA256:
                _fail("restoration_mismatch")
            _record(native["reference_glb_sha256"], {"baseline", "sphere_radius_changed"})
            if not all(_is_digest(v) for v in native["reference_glb_sha256"].values()):
                _fail("measurement_invalid")
            for key in sorted(RUN_FLAGS):
                if not native[key]:
                    reasons.append(key + "_false")
            if type(native["stages"]) is not list or len(native["stages"]) > 3:
                _fail("evidence_mismatch")
            for row in native["stages"]:
                _record(row, STAGE_FIELDS)
                _bound(row, identity)
                stage = row["stage"]
                if type(stage) is not str or stage not in STAGES or stage in rows:
                    _fail("evidence_mismatch")
                expected_sha = CANDIDATE_SHA256 if stage == "candidate" else SOURCE_SHA256
                if type(row["actual_source_sha256"]) is not str or row["actual_source_sha256"] != expected_sha:
                    _fail("stage_source_mismatch")
                _flags(row, {"registered", "cleanup_verified"})
                radius = 1.15 if stage == "candidate" else 0.75
                for key, expected in (("sphere_radius", radius), ("bevel_width", 0.08)):
                    if not _number(row[key]):
                        _fail("evidence_mismatch")
                    if abs(row[key] - expected) > 1e-6:
                        reasons.append("rna_default_mismatch")
                if not row["registered"]:
                    reasons.append("registration_unverified")
                if not row["cleanup_verified"]:
                    reasons.append("cleanup_unverified")
                _measurement(row)
                rows[stage] = row
        if set(rows) != set(STAGES):
            missing.append("stage_missing")

        for mapping, keys, label in ((measured, set(STAGES), "parent_measurement_missing"),
                                     (references, {"baseline", "sphere_radius_changed"}, "reference_missing")):
            if mapping is None:
                missing.append(label)
                continue
            if type(mapping) is not dict or not set(mapping) <= keys:
                _fail("measurement_invalid")
            if set(mapping) != keys:
                missing.append(label)
            for row in mapping.values():
                _record(row, MEASUREMENT_FIELDS)
                _measurement(row)
        if measured is not None:
            for stage in set(rows) & set(measured):
                if any(rows[stage][k] != measured[stage][k] for k in MEASUREMENT_FIELDS):
                    _fail("measurement_mismatch")
        if native is not None and references is not None:
            for key, ref in references.items():
                if native["reference_glb_sha256"][key] != ref["glb_sha256"]:
                    _fail("reference_digest_mismatch")
        if references is not None:
            for stage, row in rows.items():
                ref = references.get("sphere_radius_changed" if stage == "candidate" else "baseline")
                if ref is not None:
                    for key in ("generated_mesh", "imported_glb_mesh"):
                        if row[key] != ref[key]:
                            reasons.append("fixed_reference_geometry_mismatch")
        for key in ("generated_mesh", "imported_glb_mesh"):
            if "original" in rows and "candidate" in rows:
                a, b = rows["original"][key], rows["candidate"][key]
                if a[SPHERE]["mesh_coordinate_sha256"] == b[SPHERE]["mesh_coordinate_sha256"]:
                    reasons.append("target_effect_unverified")
                if a[CUBE] != b[CUBE]:
                    reasons.append("unrelated_geometry_changed")
            if "original" in rows and "restored" in rows and rows["original"][key] != rows["restored"][key]:
                reasons.append("restored_geometry_mismatch")
        status = "unverified" if reasons else "incomplete" if missing else "verified_fixed_observations"
        return _summary(status, reasons + missing, identity)
    except ValueError as exc:
        return _summary("rejected", (str(exc),))
