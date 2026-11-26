"""Internal fixed R26 C observations from existing synthetic native measurements."""
import math
import re

CASE_ID = "parameter_fixture_r26"
PROPERTIES = ("sphere_radius", "bevel_width")
VERSIONS = ("4.4.3", "4.5.15", "5.2.1")
EXPECTED = {
    "baseline": (0.75, 0.08),
    "sphere_radius_changed": (1.15, 0.08),
    "bevel_width_changed": (0.75, 0.35),
    "sphere_probe_up": (0.95, 0.08),
    "sphere_probe_down": (0.55, 0.08),
    "bevel_probe_up": (0.75, 0.20),
    "bevel_probe_down": (0.75, 0.03),
}
CASES = {
    "sphere_radius": ("sphere_radius_changed", "CBDK_Param_Sphere", "CBDK_Param_BevelCube",
                      "sphere_probe_up", "sphere_probe_down", 0.2),
    "bevel_width": ("bevel_width_changed", "CBDK_Param_BevelCube", "CBDK_Param_Sphere",
                    "bevel_probe_up", "bevel_probe_down", 0.01),
}


def _hex(value, width):
    return type(value) is str and re.fullmatch("[0-9a-f]{" + str(width) + "}", value) is not None


def run_identity(run_id, expected_source_sha256, expected_blender_version, *,
                 source_sha256, blender_version, independent_id):
    if not _hex(source_sha256, 64) or blender_version not in VERSIONS:
        raise ValueError("Invalid fixed fixture source or Blender version")
    if all(value is None for value in (run_id, expected_source_sha256, expected_blender_version)):
        if not _hex(independent_id, 32):
            raise ValueError("Invalid independent run ID")
        return independent_id, "independent_specialist"
    if (not _hex(run_id, 32) or expected_source_sha256 != source_sha256
            or expected_blender_version != blender_version):
        raise ValueError("R26 parent run/source/version mismatch")
    return run_id, "parent_supplied"


def _number(value):
    return type(value) in (float, int) and math.isfinite(value)


def _metric(record):
    count = record["changed_vertex_count"]
    max_delta = record["max_local_displacement"]
    if (type(count) is not int or count < 0 or not _number(max_delta) or max_delta < 0
            or type(record["vertex_count"]) is not int or not 0 < record["vertex_count"]
            or count > record["vertex_count"]
            or record["metric"] != "index_aligned_local_vertex_distance"
            or record["valid_for_arbitrary_glb"] is not False
            or record["tolerance"] != 1e-6):
        raise ValueError("Invalid fixed vertex displacement measurement")
    if (count == 0 and max_delta > 1e-6) or (count > 0 and max_delta < 1e-6):
        raise ValueError("Contradictory fixed vertex displacement measurement")
    return count, max_delta


def build_native_observation(run_id, source_sha256, blender_version, readbacks,
                             displacement, direction_evidence, *, cleanup_verified, source_unchanged):
    if (not _hex(run_id, 32) or not _hex(source_sha256, 64) or blender_version not in VERSIONS
            or type(cleanup_verified) is not bool or type(source_unchanged) is not bool):
        raise ValueError("Invalid native observation identity/cleanup")
    if type(readbacks) is not dict or tuple(readbacks) != tuple(EXPECTED):
        raise ValueError("Fixed variant set/order mismatch")
    for row in readbacks.values():
        if type(row) is not dict or set(row) != {"registered", "before", "after"}:
            raise ValueError("Invalid fixed readback")
        for key in row:
            if type(row[key]) is not dict or set(row[key]) != set(PROPERTIES):
                raise ValueError("Unexpected fixed readback property")
        if any(type(v) is not bool for v in row["registered"].values()):
            raise ValueError("Invalid registration observation")
        if any(not _number(v) for key in ("before", "after") for v in row[key].values()):
            raise ValueError("Invalid RNA numeric readback")
    if set(displacement) != {"generated", "imported"} or set(direction_evidence) != set(displacement):
        raise ValueError("Missing fixed measurement stage")
    rows = []
    for index, prop in enumerate(PROPERTIES):
        changed, target, unrelated, up, down, threshold = CASES[prop]
        row = {
            "property": prop,
            "registered_on_expected_instance": all(v["registered"][prop] for v in readbacks.values()),
            "value_readback_verified": all(abs(readbacks[name][phase][prop] - expected[index]) <= 1e-6
                                           for name, expected in EXPECTED.items()
                                           for phase in ("before", "after")),
        }
        for stage in ("generated", "imported"):
            measured = displacement[stage][changed]
            if set(measured) != {target, unrelated}:
                raise ValueError("Fixed affected/unrelated object mismatch")
            target_count, target_delta = _metric(measured[target])
            other_count, other_delta = _metric(measured[unrelated])
            direction = direction_evidence[stage][prop]
            controls = direction["unrelated_probe_changed_vertices"]
            if (direction["affected_fixture_object"] != target
                    or direction["unrelated_fixture_object"] != unrelated
                    or direction["known_reference_variant"] != changed
                    or set(controls) != {up, down}
                    or any(type(value) is not int or value < 0 for value in controls.values())):
                raise ValueError("Invalid fixed direction controls")
            row["target_changed_" + stage] = target_count > 0 and target_delta > threshold
            row["unrelated_unchanged_" + stage] = (
                other_count == 0 and other_delta <= 1e-6 and all(v == 0 for v in controls.values()))
        rows.append(row)
    return {"case_id": CASE_ID, "run_id": run_id, "source_sha256": source_sha256,
            "blender_version": blender_version, "properties": rows,
            "cleanup_verified": cleanup_verified, "source_unchanged": source_unchanged}
