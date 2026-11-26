"""R28 C fixed four-trial native observations, not a candidate selector."""
import json
import os
import sys
import types
import uuid

import bpy

from scripts import blender_parameter_experiment_smoke as r26
from scripts import blender_parameter_source_r27_smoke as r27
from scripts.parameter_r26_observation import run_identity
from scripts.parameter_source_r28_copy import (
    SOURCE, SOURCE_SHA256, COPY_NAME, TRIALS, candidate_bytes, inverse_bytes, isolated_trial, sha,
)

CASE_ID = "parameter_source_r28"
MODULE_NAME = "_cbdk_r28_fixed_fixture"
POINTER = r27.POINTER
PROPS = r27.PROPS
STAGES = ("original", "candidate", "restored")
VARIANTS = tuple(row[0] for row in r26.VARIANTS)
SPHERE, CUBE = "CBDK_Param_Sphere", "CBDK_Param_BevelCube"


def _absent():
    return r27._absent() and MODULE_NAME not in sys.modules


def _stage(tx, stage, radius, width, reference, *, snapshot, clean_scene, observe):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not _absent():
        raise AssertionError("R28 fresh registration required")
    glb = tx.path.parent / (stage + ".glb")
    def notify(phase):
        if observe is not None:
            observe(tx.trial_id, stage, phase, tx.path, glb)
    def verified():
        blob = tx.read_verified(stage)
        expected = candidate_bytes(tx.original, tx.trial_id) if stage == "candidate" else tx.original
        if blob != expected or sha(tx.original) != SOURCE_SHA256:
            raise AssertionError("R28 actual executable bytes mismatch")
        return blob

    notify("before_compile")
    blob = verified()
    actual_sha = sha(blob)
    module = types.ModuleType(MODULE_NAME)
    module.__file__ = str(tx.path)
    sys.modules[MODULE_NAME] = module
    owned = ()
    try:
        # Execute precisely the verified in-memory bytes, never an import of
        # the work copy or a re-read of executable source.
        exec(compile(blob, str(tx.path), "exec", dont_inherit=True), module.__dict__)
        owned = tuple(module.CLASSES)
        if tuple(cls.__name__ for cls in owned) != r27.CLASSES:
            raise AssertionError("R28 fixed classes mismatch")
        module.register()
        before = r27._read_defaults(module)
        if any(abs(before[p] - v) > 1e-6 for p, v in zip(PROPS, (radius, width))):
            raise AssertionError("R28 wrong actual RNA default")
        notify("registered")
        if verified() != blob or bpy.ops.mesh.cbdk_parameter_experiment_build() != {"FINISHED"}:
            raise AssertionError("R28 fixed build failed")
        after = r27._read_defaults(module)
        if before != after:
            raise AssertionError("R28 operator changed defaults")
        notify("generated_mesh")
        generated = r27._measure(snapshot)
        if glb.exists() or bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB") != {"FINISHED"} or not glb.is_file():
            raise AssertionError("R28 GLB export failed")
        digest = sha(glb.read_bytes())
        clean_scene()
        if bpy.ops.import_scene.gltf(filepath=str(glb)) != {"FINISHED"}:
            raise AssertionError("R28 GLB reimport failed")
        notify("imported_glb_mesh")
        imported = r27._measure(snapshot)
        if (sha(glb.read_bytes()) != digest or verified() != blob
                or r27._read_defaults(module) != before):
            raise AssertionError("R28 stage integrity mismatch")
        if generated != reference["generated_mesh"] or imported != reference["imported_glb_mesh"]:
            raise AssertionError("R28 fixed reference measurement mismatch")
    finally:
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
    if not _absent() or any(cls.is_registered for cls in owned):
        raise AssertionError("R28 stage cleanup incomplete")
    notify("cleaned")
    if not _absent() or verified() != blob or sha(glb.read_bytes()) != digest:
        raise AssertionError("R28 post-cleanup integrity mismatch")
    return dict(stage=stage, actual_source_sha256=actual_sha, rna_defaults=before,
                rna_after_build=after, registered=True, unregistered=True,
                generated_mesh=generated, imported_glb_mesh=imported, glb_sha256=digest)


def _digest_tree(directory):
    if not directory.is_dir() or directory.is_symlink():
        raise AssertionError("R28 missing R27 evidence directory")
    rows = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise AssertionError("R28 unexpected R27 symlink")
        if path.is_file():
            rows[path.relative_to(directory).as_posix()] = sha(path.read_bytes())
    required = {COPY_NAME, "native.json", "details.json", "a_combined.json",
                "original.glb", "candidate.glb", "restored.glb"}
    if not required.issubset(rows):
        raise AssertionError("R28 missing R27 evidence file")
    return rows


def run_source_trials(root, *, run_id=None, expected_source_sha256=None,
                      expected_blender_version=None, snapshot=r26._snapshot,
                      clean_scene=r26._clean_scene, observe=None):
    """Fixed internal entry; trusted A may observe actual copy/RNA/mesh/GLB.

    observe(trial_id, stage, phase, copy_path, glb_path) is read-only.
    See docs/UI_PARAMETER_SOURCE_R28.md for the fixed phase contract.
    """
    if not bpy.app.background or not _absent():
        raise AssertionError("R28 background and clean registration required")
    version = ".".join(map(str, bpy.app.version))
    # Explicit parent inputs or all three fixed environment values; no user
    # source, values, executable path, or candidate selection.
    if all(v is None for v in (run_id, expected_source_sha256, expected_blender_version)):
        run_id = os.environ.get("CBDK_R28_RUN_ID")
        expected_source_sha256 = os.environ.get("CBDK_R28_SOURCE_SHA256")
        expected_blender_version = os.environ.get("CBDK_R28_BLENDER_VERSION")
    identity, origin = run_identity(run_id, expected_source_sha256, expected_blender_version,
        source_sha256=SOURCE_SHA256, blender_version=version, independent_id=uuid.uuid4().hex)
    original = SOURCE.read_bytes()
    if sha(original) != SOURCE_SHA256:
        raise AssertionError("R28 original source mismatch")
    report_path = root / "parameter_experiment.json"
    details_path = root / "parameter_experiment_r26_details.json"
    native_path = root / "parameter_experiment_r26_native.json"
    old_bytes = {p: p.read_bytes() for p in (report_path, details_path, native_path)}
    legacy = json.loads(old_bytes[report_path])
    detail = json.loads(old_bytes[details_path])
    prior = json.loads(old_bytes[native_path])
    if (detail["source_sha256"] != SOURCE_SHA256 or detail["blender_version"] != version
            or detail["legacy_report_sha256"] != sha(old_bytes[report_path])
            or detail["run_id"] != prior["run_id"] or prior["source_sha256"] != SOURCE_SHA256
            or prior["blender_version"] != version or identity == detail["run_id"]
            or detail["run_id_origin"] != "parent_supplied"):
        raise AssertionError("R28 R26 reference identity mismatch")
    old_glbs = {name: sha((root / (name + ".glb")).read_bytes()) for name in VARIANTS}
    if old_glbs != detail["glb_sha256"]:
        raise AssertionError("R28 R26 GLB SHA mismatch")
    r27_dir = root / "parameter_source_r27"
    prior_r27 = _digest_tree(r27_dir)
    r27_detail = json.loads((r27_dir / "details.json").read_bytes())
    if (r27_detail["reference_run_id"] != detail["run_id"]
            or r27_detail["blender_version"] != version or identity == r27_detail["run_id"]
            or r27_detail["run_id_origin"] != "parent_supplied"
            or prior_r27[COPY_NAME] != SOURCE_SHA256):
        raise AssertionError("R28 R27 reference identity mismatch")

    def reference(sphere, cube):
        # Cross-part reference is a pair of existing per-object measurements,
        # never a claim that a mixed R26 GLB exists.
        return {key: {SPHERE: legacy[key][sphere][SPHERE], CUBE: legacy[key][cube][CUBE]}
                for key in ("generated_mesh", "imported_glb_mesh")}

    def unchanged():
        return (SOURCE.read_bytes() == original
                and all(path.read_bytes() == data for path, data in old_bytes.items())
                and all(sha((root / (name + ".glb")).read_bytes()) == digest
                        for name, digest in old_glbs.items())
                and _digest_tree(r27_dir) == prior_r27)

    work = root / "parameter_source_r28"
    work.mkdir(exist_ok=False)
    trials = []
    try:
        for trial_id, radius, width, sphere_ref, cube_ref in TRIALS:
            with isolated_trial(work / trial_id, trial_id) as tx:
                candidate = candidate_bytes(original, trial_id)
                if tx.candidate != candidate or inverse_bytes(candidate, original, trial_id) != original:
                    raise AssertionError("R28 independent candidate/inverse mismatch")
                stages = []
                for stage in STAGES:
                    if stage == "candidate":
                        tx.apply()
                    elif stage == "restored":
                        tx.restore()
                    active = stage == "candidate"
                    stages.append(_stage(tx, stage, radius if active else .75, width if active else .08,
                        reference(sphere_ref, cube_ref) if active else reference("baseline", "baseline"),
                        snapshot=snapshot, clean_scene=clean_scene, observe=observe))
                restored = tx.read_verified("restored") == original
            if not restored or tx.path.read_bytes() != original or not _absent() or not unchanged():
                raise AssertionError("R28 trial restoration or prior evidence integrity mismatch")
            trials.append(dict(trial_id=trial_id, candidate_sha256=sha(candidate), stages=stages,
                inverse_restored=restored, restored_copy_sha256=sha(tx.path.read_bytes()),
                cleanup_verified=_absent(), source_unchanged=SOURCE.read_bytes()==original,
                references_unchanged=unchanged()))
    finally:
        if not unchanged() or not _absent():
            raise AssertionError("R28 final preservation/cleanup failure")
    if len(trials) != len(TRIALS):
        raise AssertionError("R28 incomplete fixed trial set")
    result = dict(case_id=CASE_ID, run_id=identity, blender_version=version,
                  source_sha256=SOURCE_SHA256, reference_run_id=detail["run_id"],
                  trials=trials, source_unchanged=True, references_unchanged=True,
                  cleanup_verified=True, auto_apply=False, auto_adopt=False, auto_approve=False)
    details = dict(case_id=CASE_ID, run_id=identity, blender_version=version,
                   source_sha256=SOURCE_SHA256, run_id_origin=origin,
                   reference_run_id=detail["run_id"], reference_report_sha256=sha(old_bytes[report_path]),
                   reference_glb_sha256=old_glbs, prior_r27_run_id=r27_detail["run_id"],
                   prior_r27_sha256=prior_r27)
    for name, record in (("native.json", result), ("details.json", details)):
        with (work / name).open("x", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True, indent=2)
            stream.write("\n")
    print("CBDK_R28_PARAMETER_SOURCE_NATIVE_PASS " + json.dumps(result, sort_keys=True), flush=True)
    print("CBDK_R28_PARAMETER_SOURCE_NATIVE_DETAILS " + json.dumps(details, sort_keys=True), flush=True)
    return result
