"""A-owned fixed R26 CI bridge; not a user addon launcher."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from cbdk.glb_parameter_static_r26 import (  # noqa: E402
    FIXTURE, observe_fixed_parameter_fixture, fixed_diagnostic_candidates,
)
from cbdk.parameter_fixture_evidence import CASE, reduce_parameter_evidence  # noqa: E402
from scripts.parameter_r26_observation import EXPECTED, PROPERTIES, build_native_observation  # noqa: E402

ROOT = PROJECT / "reports" / "ci" / "parameter_experiment"
MAX_BYTES = 32 * 1024 * 1024


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path):
    require(not path.is_symlink() and path.is_file(), "fixed_file_missing")
    require(0 < path.stat().st_size <= MAX_BYTES, "fixed_file_size")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    digest(path)

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def invalid_constant(_):
        raise ValueError("invalid_json_constant")

    obj = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                     parse_constant=invalid_constant)
    require(type(obj) is dict, "invalid_json_envelope")
    return obj


def write_new(path, obj):
    with path.open("x", encoding="utf-8") as out:
        json.dump(obj, out, sort_keys=True, indent=2, allow_nan=False)
        out.write("\n")


def parent_identity():
    return dict(case_id=CASE, blender_version=os.environ["CBDK_R26_BLENDER_VERSION"],
                run_id=os.environ["CBDK_R26_RUN_ID"],
                source_sha256=os.environ["CBDK_R26_SOURCE_SHA256"])


def normalize(envelope, expected, *, native=False):
    fields = {"properties", *expected}
    if native:
        fields |= {"cleanup_verified", "source_unchanged"}
    require(type(envelope) is dict and set(envelope) == fields, "envelope_schema_mismatch")
    require(all(envelope[k] == v for k, v in expected.items()), "parent_identity_mismatch")
    return {("case" if k == "case_id" else "blender" if k == "blender_version" else k): v
            for k, v in envelope.items()}


def verify_details(details, expected, report, root):
    require(set(details) == set(expected) | {"run_id_origin", "variant_readbacks",
            "glb_sha256", "legacy_report_sha256", "unregistered_negative_control"},
            "native_details_schema_mismatch")
    require(all(details[k] == v for k, v in expected.items()), "native_details_identity_mismatch")
    require(details["run_id_origin"] == "parent_supplied" and
            details["unregistered_negative_control"] is True, "native_origin_or_negative_control")
    require(details["legacy_report_sha256"] == digest(root / "parameter_experiment.json"),
            "legacy_report_digest_mismatch")
    hashes = details["glb_sha256"]
    require(type(hashes) is dict and set(hashes) == set(EXPECTED), "glb_inventory_mismatch")
    for variant in EXPECTED:
        require(hashes[variant] == digest(root / (variant + ".glb")), "glb_digest_mismatch")
    expected_variants = [
        {"id": name, "parameters": dict(zip(PROPERTIES, values)), "glb": name + ".glb"}
        for name, values in EXPECTED.items()
    ]
    require(report["kind"] == "cbdk_trusted_blender_parameter_experiment" and
            report["schema_version"] == 1 and report["source_fixture"] == "cbdk_authored_only" and
            report["blender_version"].split()[0] == expected["blender_version"] and
            report["variables_changed_one_at_a_time"] is True and
            report["variants"] == expected_variants and
            all(v is False for v in report["safety"].values()), "legacy_report_contract")
    rows = details["variant_readbacks"]
    require(type(rows) is dict and set(rows) == set(EXPECTED), "readback_inventory_mismatch")
    return {name: rows[name] for name in EXPECTED}


def require_radius_candidate(comparison):
    require(comparison.get("passed") is False, "radius_difference_missing")
    candidates = fixed_diagnostic_candidates(comparison)
    required = {"property": "sphere_radius", "target": "CBDK_Param_Sphere",
                "category": "part_size_parameter"}
    require(required in candidates, "radius_diagnostic_mapping_missing")
    return candidates


def prepare(root, expected):
    require(digest(FIXTURE) == expected["source_sha256"], "source_digest_mismatch")
    static = observe_fixed_parameter_fixture(run_id=expected["run_id"],
                  source_sha256=expected["source_sha256"],
                  blender_version=expected["blender_version"])
    normalize(static, expected)
    write_new(root / "parameter_experiment_r26_static.json", static)


def verify(root, expected):
    static = read_json(root / "parameter_experiment_r26_static.json")
    native = read_json(root / "parameter_experiment_r26_native.json")
    details = read_json(root / "parameter_experiment_r26_details.json")
    report = read_json(root / "parameter_experiment.json")
    require(digest(FIXTURE) == expected["source_sha256"], "source_digest_mismatch")
    a = normalize(static, expected)
    n = normalize(native, expected, native=True)
    require(static == observe_fixed_parameter_fixture(run_id=expected["run_id"],
                source_sha256=expected["source_sha256"],
                blender_version=expected["blender_version"]), "static_recheck_mismatch")
    readbacks = verify_details(details, expected, report, root)
    recomputed = build_native_observation(expected["run_id"], expected["source_sha256"],
                  expected["blender_version"], readbacks,
                  report["quantified_vertex_displacement"], report["direction_probe_evidence"],
                  cleanup_verified=native["cleanup_verified"],
                  source_unchanged=digest(FIXTURE) == expected["source_sha256"])
    require(recomputed == native, "native_measurement_mismatch")
    result = reduce_parameter_evidence(a, n, case=CASE, blender=expected["blender_version"],
                   run_id=expected["run_id"], source_sha256=expected["source_sha256"])
    require(result["status"] == "verified_fixed_observations", "fixed_observations_not_verified")
    comparison_path = root / "radius_regression" / "comparison.json"
    candidates = require_radius_candidate(read_json(comparison_path))
    # The CI invokes the existing regression on these exact GLBs in this job.
    # Recheck all file digests after the regression; no authenticity claim.
    require(digest(FIXTURE) == expected["source_sha256"], "source_changed")
    verify_details(details, expected, report, root)
    summary = {"evidence": result, "diagnostic_candidates": candidates,
               "comparison_sha256": digest(comparison_path),
               "glb_sha256": details["glb_sha256"],
               "legacy_report_sha256": details["legacy_report_sha256"],
               "native_details_sha256": digest(root / "parameter_experiment_r26_details.json"),
               "static_observation_sha256": digest(root / "parameter_experiment_r26_static.json"),
               "native_observation_sha256": digest(root / "parameter_experiment_r26_native.json"),
               "variant_count": len(EXPECTED),
               "bevel_geometry_effect_is_not_diagnostic_proof": True}
    write_new(root / "parameter_experiment_r26_combined.json", summary)
    print("CBDK_R26_A_SAME_FIXTURE_PASS " + json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    require(len(sys.argv) == 2 and sys.argv[1] in ("prepare", "verify"), "fixed_command")
    (prepare if sys.argv[1] == "prepare" else verify)(ROOT, parent_identity())
