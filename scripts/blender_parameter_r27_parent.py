"""A-owned R27 fixed native integration; no arbitrary input or execution."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from cbdk.parameter_source_candidate_r27 import (
    build_fixed_source_candidate, restore_fixed_source_candidate,
)
from cbdk.parameter_source_evidence_r27 import reduce_source_evidence
from scripts.verify_parameter_r26 import (
    ROOT, digest, read_json, require, write_new, parent_identity, verify_details,
)

SOURCE = PROJECT / "fixtures/cbdk_parameter_experiment.py"
SOURCE_SHA = "e645723ff89a99530841e1ccd37ea8d059952eec0f980ac1782d8228e46588e3"
CANDIDATE_SHA = "edde3abe885bf40830052068fcdd6cab57d3d945fdccbc5f3625cff4594c72d7"
OFFSET = 570
STAGES = ("original", "candidate", "restored")
REFERENCES = ("baseline", "sphere_radius_changed")
PROPERTIES = ("sphere_radius", "bevel_width")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def exact_pair(original, candidate):
    """Independent pinned-byte and AST check, not candidate self-attestation."""
    require(type(original) is bytes and sha(original) == SOURCE_SHA, "r27_source_sha")
    require(type(candidate) is bytes and sha(candidate) == CANDIDATE_SHA, "r27_candidate_sha")
    require(original[OFFSET:OFFSET + 4] == b"0.75" and original.count(b"0.75") == 1
            and candidate == original[:OFFSET] + b"1.15" + original[OFFSET + 4:],
            "r27_single_diff")
    before, after = (ast.parse(x.decode("utf-8")) for x in (original, candidate))
    classes = [node for node in before.body if isinstance(node, ast.ClassDef)
               and node.name == "CBDKParameterExperimentSettings"]
    require(len(classes) == 1, "r27_class")
    declarations = [node for node in classes[0].body if isinstance(node, ast.AnnAssign)
                    and isinstance(node.target, ast.Name) and node.target.id == "sphere_radius"]
    require(len(declarations) == 1 and isinstance(declarations[0].annotation, ast.Call),
            "r27_declaration")
    defaults = [kw.value for kw in declarations[0].annotation.keywords if kw.arg == "default"]
    require(len(defaults) == 1 and isinstance(defaults[0], ast.Constant)
            and defaults[0].value == .75, "r27_ast_default")
    defaults[0].value = 1.15
    require(ast.dump(before) == ast.dump(after), "r27_ast_difference")
    restored = candidate[:OFFSET] + b"0.75" + candidate[OFFSET + 4:]
    require(restored == original, "r27_reverse")
    return restored


def summaries(raw):
    return {name: {k: v for k, v in row.items() if k != "local_vertices_for_trusted_fixture"}
            for name, row in raw.items()}


def run():
    import bpy
    from scripts import blender_parameter_experiment_smoke as r26
    from scripts import blender_parameter_source_r27_smoke as c
    from scripts.parameter_source_r27_copy import candidate_bytes

    version = os.environ["CBDK_R27_BLENDER_VERSION"]
    run_id = os.environ["CBDK_R27_RUN_ID"]
    source_sha = os.environ["CBDK_R27_SOURCE_SHA256"]
    prior = parent_identity()
    require(bpy.app.background and ".".join(map(str, bpy.app.version)) == version
            and prior["blender_version"] == version and prior["source_sha256"] == source_sha
            and run_id != prior["run_id"] and source_sha == SOURCE_SHA, "r27_parent_identity")
    require(digest(SOURCE) == SOURCE_SHA, "r27_parent_source")
    original = SOURCE.read_bytes()
    candidate, observation = build_fixed_source_candidate(
        run_id=run_id, source_sha256=source_sha, blender_version=version)
    restored = exact_pair(original, candidate)
    require(candidate == candidate_bytes(original)
            and restore_fixed_source_candidate(candidate) == restored, "r27_b_c_pair")
    identity = dict(case_id="parameter_source_r27", run_id=run_id, blender_version=version,
                    source_sha256=source_sha, candidate_sha256=sha(candidate), property="sphere_radius")
    require(all(observation[k] == v for k, v in identity.items()), "r27_b_identity")
    require(observation["single_difference_verified"] is True, "r27_b_diff")
    diff = {k: v for k, v in observation.items() if k != "single_difference_verified"}
    diff.update(single_diff_verified=observation["single_difference_verified"], ast_diff_verified=True)

    # R26 remains the same native seven-variant experiment. Its measured
    # report and hashes are bound before and after the separate R27 stages.
    r26.run(ROOT, run_id=prior["run_id"], expected_source_sha256=source_sha,
            expected_blender_version=version)
    legacy = read_json(ROOT / "parameter_experiment.json")
    old_detail = read_json(ROOT / "parameter_experiment_r26_details.json")
    verify_details(old_detail, prior, legacy, ROOT)
    detail_sha = digest(ROOT / "parameter_experiment_r26_details.json")
    reference_hashes = dict(old_detail["glb_sha256"])
    report_sha = old_detail["legacy_report_sha256"]
    work = ROOT / "parameter_source_r27"
    copy_path = work / SOURCE.name
    captured = []

    def observe_snapshot():
        index = len(captured)
        require(index < 6, "r27_unexpected_snapshot")
        stage = STAGES[index // 2]
        phase = "generated_mesh" if index % 2 == 0 else "imported_glb_mesh"
        permitted = candidate if stage == "candidate" else original
        require(digest(copy_path) == sha(permitted) and copy_path.read_bytes() == permitted,
                "r27_actual_copy_mismatch")
        module = sys.modules.get(c.MODULE_NAME)
        require(module is not None and all(cls.is_registered for cls in module.CLASSES),
                "r27_parent_registration")
        settings = getattr(bpy.context.scene, c.POINTER)
        require(isinstance(settings, module.CBDKParameterExperimentSettings)
                and settings.id_data == bpy.context.scene, "r27_parent_settings")
        readback = {}
        for prop in PROPERTIES:
            row = settings.bl_rna.properties.get(prop)
            value = float(getattr(settings, prop))
            require(row is not None and row.type == "FLOAT" and not row.is_array
                    and not settings.is_property_set(prop)
                    and abs(value - float(row.default)) <= 1e-6, "r27_parent_rna")
            readback[prop] = value
        raw = r26._snapshot()
        glb = work / (stage + ".glb")
        if phase == "generated_mesh":
            require(not glb.exists(), "r27_premature_export")
        captured.append(dict(stage=stage, phase=phase, source_sha=sha(permitted),
                             rna=readback, mesh=summaries(raw),
                             glb_sha=None if phase == "generated_mesh" else digest(glb)))
        return raw

    native = c.run_source_experiment(ROOT, snapshot=observe_snapshot, clean_scene=r26._clean_scene)
    require(len(captured) == 6 and native == read_json(work / "native.json"), "r27_native_records")
    require(all(native[k] == v for k, v in identity.items()), "r27_native_identity")
    details = read_json(work / "details.json")
    require(details["case_id"] == identity["case_id"] and details["run_id"] == run_id
            and details["blender_version"] == version and details["run_id_origin"] == "parent_supplied"
            and details["reference_run_id"] == prior["run_id"]
            and details["reference_report_sha256"] == report_sha
            and details["reference_glb_sha256"] == reference_hashes, "r27_reference_identity")
    require(digest(copy_path) == SOURCE_SHA and copy_path.read_bytes() == restored
            and details["restored_copy_sha256"] == SOURCE_SHA, "r27_actual_restore")
    require(digest(SOURCE) == SOURCE_SHA and SOURCE.read_bytes() == original, "r27_source_changed")
    require(digest(ROOT / "parameter_experiment_r26_details.json") == detail_sha
            and digest(ROOT / "parameter_experiment.json") == report_sha, "r27_reference_report_changed")
    verify_details(old_detail, prior, legacy, ROOT)
    require(c._absent() and c.MODULE_NAME not in sys.modules, "r27_parent_cleanup")

    measured, stages = {}, []
    require(type(native["stages"]) is list and len(native["stages"]) == 3, "r27_stage_count")
    for index, stage in enumerate(STAGES):
        generated, imported = captured[2 * index:2 * index + 2]
        row = native["stages"][index]
        require(generated["stage"] == imported["stage"] == row["stage"] == stage
                and generated["source_sha"] == imported["source_sha"] == row["actual_source_sha256"]
                and generated["rna"] == imported["rna"] == row["rna_defaults"] == row["rna_after_build"],
                "r27_stage_link")
        actual = dict(glb_sha256=digest(work / (stage + ".glb")),
                      generated_mesh=generated["mesh"], imported_glb_mesh=imported["mesh"])
        require(actual["glb_sha256"] == imported["glb_sha"]
                and all(row[k] == v for k, v in actual.items()), "r27_stage_measurement")
        measured[stage] = actual
        stages.append(dict(**identity, stage=stage, actual_source_sha256=row["actual_source_sha256"],
                           sphere_radius=row["rna_defaults"]["sphere_radius"],
                           bevel_width=row["rna_defaults"]["bevel_width"],
                           registered=row["registered"], cleanup_verified=row["unregistered"],
                           **{k: row[k] for k in actual}))

    # Reimport the two actual reference files separately in Blender; generated
    # metrics are the real earlier R26 observations, not R27 report assertions.
    references = {}
    for name in REFERENCES:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        path = ROOT / (name + ".glb")
        require(digest(path) == reference_hashes[name], "r27_reference_sha")
        require(bpy.ops.import_scene.gltf(filepath=str(path)) == {"FINISHED"}, "r27_reference_import")
        imported = summaries(r26._snapshot())
        require(imported == legacy["imported_glb_mesh"][name], "r27_reference_measurement")
        references[name] = dict(glb_sha256=digest(path), generated_mesh=legacy["generated_mesh"][name],
                                imported_glb_mesh=imported)
        r26._clean_scene()
    verify_details(old_detail, prior, legacy, ROOT)
    require(SOURCE.read_bytes() == original and copy_path.read_bytes() == restored
            and c._absent(), "r27_final_integrity")
    normalized = dict(**identity, stages=stages, isolated_copy_verified=True,
                      restoration_verified=native["inverse_restored"],
                      original_source_unchanged=native["source_unchanged"],
                      reference_sha_unchanged=native["references_unchanged"],
                      restored_copy_sha256=digest(copy_path),
                      reference_glb_sha256={name: reference_hashes[name] for name in REFERENCES})
    require(native["cleanup_verified"] is True, "r27_native_cleanup")
    result = reduce_source_evidence(diff, normalized, run_id=run_id, blender_version=version,
                                    source_sha256=source_sha, candidate_sha256=sha(candidate),
                                    measured=measured, references=references)
    require(result["status"] == "verified_fixed_observations", "r27_reducer_rejected")
    record = dict(evidence=result, diff=diff, measured=measured, references=references,
                  reference_run_id=prior["run_id"], reference_report_sha256=report_sha,
                  all_reference_glb_sha256=reference_hashes, restored_copy_sha256=digest(copy_path),
                  observed_snapshot_count=len(captured), native_sha256=digest(work / "native.json"),
                  details_sha256=digest(work / "details.json"))
    write_new(work / "a_combined.json", record)
    print("CBDK_R27_A_SOURCE_RESTORE_PASS " + json.dumps(record, sort_keys=True), flush=True)


if __name__ == "__main__":
    require(sys.argv[sys.argv.index("--") + 1:] == ["reports/ci/parameter_experiment"],
            "r27_fixed_output")
    run()
    from scripts.blender_parameter_source_r28_smoke import run_source_trials
    run_source_trials(ROOT)
