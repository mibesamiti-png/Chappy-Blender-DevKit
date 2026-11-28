"""R27 C: fixed source default, native registration, regeneration, restoration.

Only the exact pinned repository fixture or its single permitted token
replacement is executed. No arbitrary module path, patch, setting or code.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import types
import uuid

import bpy

from scripts.parameter_source_r27_copy import SOURCE, SOURCE_SHA256, sha, isolated_copy
from scripts.parameter_r26_observation import run_identity

CASE_ID = "parameter_source_r27"
MODULE_NAME = "_cbdk_r27_fixed_fixture"
POINTER = "cbdk_parameter_experiment"
PROPS = ("sphere_radius", "bevel_width")
CLASSES = ("CBDKParameterExperimentSettings", "CBDK_OT_parameter_experiment_build")
OBJECTS = {"CBDK_Param_Sphere", "CBDK_Param_BevelCube"}
STAGES = (("original", .75, "baseline"), ("candidate", 1.15, "sphere_radius_changed"),
          ("restored", .75, "baseline"))


def _absent():
    return (not hasattr(bpy.types.Scene, POINTER)
            and bpy.types.Scene.bl_rna.properties.get(POINTER) is None
            and all(not hasattr(bpy.types, name) for name in CLASSES))


def _read_defaults(module):
    scene = bpy.context.scene
    cls = module.CBDKParameterExperimentSettings
    pointer = bpy.types.Scene.bl_rna.properties.get(POINTER)
    settings = getattr(scene, POINTER)
    if (pointer is None or pointer.type != "POINTER"
            or pointer.fixed_type.identifier != cls.bl_rna.identifier
            or not cls.is_registered or not isinstance(settings, cls)
            or settings.id_data != scene or any(not c.is_registered for c in module.CLASSES)):
        raise AssertionError("R27 actual Scene/PropertyGroup registration mismatch")
    values = {}
    for prop in PROPS:
        rna = settings.bl_rna.properties.get(prop)
        declared = cls.bl_rna.properties.get(prop)
        if rna is None or declared is None or rna.type != "FLOAT" or rna.is_array or declared.type != "FLOAT":
            raise AssertionError("R27 expected FloatProperty RNA missing")
        value = float(getattr(settings, prop))
        if abs(value - float(rna.default)) > 1e-6 or abs(value - float(declared.default)) > 1e-6:
            raise AssertionError("R27 value differs from registered RNA default")
        if settings.is_property_set(prop):
            raise AssertionError("R27 default was explicitly assigned")
        values[prop] = value
    return values


def _measure(snapshot):
    rows = snapshot()
    if set(rows) != OBJECTS:
        raise AssertionError("R27 unexpected fixed mesh set")
    for stats in rows.values():
        del stats["local_vertices_for_trusted_fixture"]
    return rows


def _stage(tx, stage, radius, reference, work, *, snapshot, clean_scene):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not _absent() or MODULE_NAME in sys.modules:
        raise AssertionError("R27 stage did not start with fresh registration")
    # Compile the same verified bytes we actually read from the fixed copy.
    # Never import the copy or re-read executable source after verification.
    blob = tx.read_verified(stage)
    actual_sha = sha(blob)
    module = types.ModuleType(MODULE_NAME)
    module.__file__ = str(tx.path)
    sys.modules[MODULE_NAME] = module
    owned = ()
    try:
        exec(compile(blob, str(tx.path), "exec", dont_inherit=True), module.__dict__)
        owned = tuple(module.CLASSES)
        if tuple(c.__name__ for c in owned) != CLASSES:
            raise AssertionError("R27 fixed class mismatch")
        module.register()
        before = _read_defaults(module)
        if abs(before["sphere_radius"] - radius) > 1e-6 or abs(before["bevel_width"] - .08) > 1e-6:
            raise AssertionError("R27 wrong actual RNA default")
        if bpy.ops.mesh.cbdk_parameter_experiment_build() != {"FINISHED"}:
            raise AssertionError("R27 fixed operator did not finish")
        after = _read_defaults(module)
        if before != after:
            raise AssertionError("R27 operator changed default values")
        generated = _measure(snapshot)
        glb = work / (stage + ".glb")
        if glb.exists():
            raise AssertionError("R27 stage output already exists")
        if bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB") != {"FINISHED"} or not glb.is_file():
            raise AssertionError("R27 GLB export failed")
        digest = sha(glb.read_bytes())
        clean_scene()
        if bpy.ops.import_scene.gltf(filepath=str(glb)) != {"FINISHED"}:
            raise AssertionError("R27 GLB reimport failed")
        imported = _measure(snapshot)
        if sha(glb.read_bytes()) != digest or tx.read_verified(stage) != blob:
            raise AssertionError("R27 stage input/output changed")
        if generated != reference["generated"] or imported != reference["imported"]:
            raise AssertionError("R27 fixed generated/imported reference mismatch")
    finally:
        # Attempt cleanup even for a partially registered module. No success
        # marker on an exception, including a cleanup or restoration failure.
        try:
            clean_scene()
        finally:
            try:
                if hasattr(bpy.types.Scene, POINTER):
                    delattr(bpy.types.Scene, POINTER)
                for cls in reversed(owned):
                    if cls.is_registered:
                        bpy.utils.unregister_class(cls)
            finally:
                sys.modules.pop(MODULE_NAME, None)
    if not _absent() or any(c.is_registered for c in owned) or MODULE_NAME in sys.modules:
        raise AssertionError("R27 stage cleanup incomplete")
    return {"stage": stage, "actual_source_sha256": actual_sha,
            "rna_defaults": before, "rna_after_build": after,
            "registered": True, "unregistered": True,
            "generated_mesh": generated, "imported_glb_mesh": imported,
            "glb_sha256": digest}


def run_source_experiment(root, *, snapshot, clean_scene):
    """Called only by existing trusted CI smoke, after seven fixed variants."""
    if not bpy.app.background:
        raise AssertionError("R27 background fixture only")
    version = ".".join(map(str, bpy.app.version))
    identity, origin = run_identity(os.environ.get("CBDK_R27_RUN_ID"),
        os.environ.get("CBDK_R27_SOURCE_SHA256"), os.environ.get("CBDK_R27_BLENDER_VERSION"),
        source_sha256=SOURCE_SHA256, blender_version=version, independent_id=uuid.uuid4().hex)
    old_report = root / "parameter_experiment.json"
    old_bytes = old_report.read_bytes()
    legacy = json.loads(old_bytes)
    detail = json.loads((root / "parameter_experiment_r26_details.json").read_bytes())
    if (detail["source_sha256"] != SOURCE_SHA256 or detail["blender_version"] != version
            or detail["legacy_report_sha256"] != sha(old_bytes)):
        raise AssertionError("R27 reference measurement identity mismatch")
    references = {}
    reference_hashes = {}
    # Preserve all seven input GLBs, compare geometry only with fixed two.
    for variant in ("baseline", "sphere_radius_changed", "bevel_width_changed",
                    "sphere_probe_up", "sphere_probe_down", "bevel_probe_up", "bevel_probe_down"):
        digest = sha((root / (variant + ".glb")).read_bytes())
        if detail["glb_sha256"][variant] != digest:
            raise AssertionError("R27 R26 reference GLB digest mismatch")
        reference_hashes[variant] = digest
        references[variant] = {"generated": legacy["generated_mesh"][variant],
                               "imported": legacy["imported_glb_mesh"][variant]}
    work = root / "parameter_source_r27"
    records = []
    with isolated_copy(work) as tx:
        candidate_sha = sha(tx.candidate)
        for stage, radius, ref in STAGES:
            if stage == "candidate":
                tx.apply()
            elif stage == "restored":
                tx.restore()
            records.append(_stage(tx, stage, radius, references[ref], work,
                                  snapshot=snapshot, clean_scene=clean_scene))
        inverse_restored = tx.read_verified("restored") == tx.original
    source_unchanged = sha(SOURCE.read_bytes()) == SOURCE_SHA256
    references_unchanged = (old_report.read_bytes() == old_bytes and all(
        sha((root / (variant + ".glb")).read_bytes()) == digest
        for variant, digest in reference_hashes.items()))
    unrelated = "CBDK_Param_BevelCube"
    target = "CBDK_Param_Sphere"
    for key in ("generated_mesh", "imported_glb_mesh"):
        if not (records[0][key] == records[2][key]
                and records[0][key][unrelated] == records[1][key][unrelated]
                and records[0][key][target] != records[1][key][target]):
            raise AssertionError("R27 restored/target/unrelated observation mismatch")
    if not (source_unchanged and references_unchanged and inverse_restored and _absent()
            and sha((work / tx.path.name).read_bytes()) == SOURCE_SHA256):
        raise AssertionError("R27 final integrity or restoration check failed")
    result = {"case_id": CASE_ID, "run_id": identity, "blender_version": version,
              "source_sha256": SOURCE_SHA256, "candidate_sha256": candidate_sha,
              "property": "sphere_radius", "stages": records,
              "source_unchanged": source_unchanged, "references_unchanged": references_unchanged,
              "inverse_restored": inverse_restored, "cleanup_verified": _absent()}
    details = {"case_id": CASE_ID, "run_id": identity, "blender_version": version,
               "run_id_origin": origin, "reference_run_id": detail["run_id"],
               "reference_report_sha256": sha(old_bytes), "reference_glb_sha256": reference_hashes,
               "restored_copy_sha256": sha(tx.path.read_bytes())}
    (work / "native.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (work / "details.json").write_text(json.dumps(details, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("CBDK_R27_PARAMETER_SOURCE_NATIVE_PASS " + json.dumps(result, sort_keys=True), flush=True)
    print("CBDK_R27_PARAMETER_SOURCE_NATIVE_DETAILS " + json.dumps(details, sort_keys=True), flush=True)
    return result
