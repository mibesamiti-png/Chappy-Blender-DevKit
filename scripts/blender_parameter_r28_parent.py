"""A-owned R28 fixed source trial bridge; no public launcher or adoption."""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from scripts.blender_parameter_r27_parent import SOURCE, SOURCE_SHA, sha, summaries
from scripts.verify_parameter_r26 import ROOT, digest, read_json, require, write_new, parent_identity, verify_details

TRIALS = ("wrong_direction", "cross_part", "intermediate", "target")
TOKENS = (("0.55", "0.08"), ("1.15", "0.20"), ("0.95", "0.08"), ("1.15", "0.08"))
DIGESTS = (
    "b8a70b569e5004a43842d31c6799bf13c18730b1a06a6a511691e720ec92566f",
    "b029567c83fa1f1aaf527fd9d24e5fa864c1ec6d67c861e7940e814c69c8428f",
    "8da8748483ec5c318bd951fee5766860fb7f4e4027e617227e6509527177db2a",
    "edde3abe885bf40830052068fcdd6cab57d3d945fdccbc5f3625cff4594c72d7",
)
PROPS = ("sphere_radius", "bevel_width")
STAGES = ("original", "candidate", "restored")
PHASES = ("before_compile", "registered", "generated_mesh", "imported_glb_mesh", "cleaned")
REFERENCES = ("baseline", "sphere_radius_changed", "bevel_width_changed",
              "sphere_probe_up", "sphere_probe_down", "bevel_probe_up", "bevel_probe_down")
DECISIONS = ("target_regression", "protected_part_regression", "observed_improvement", "observed_target_reached")


def fixed_pair(original, trial_id):
    require(type(original) is bytes and sha(original) == SOURCE_SHA, "r28_pinned_source")
    require(type(trial_id) is str and trial_id in TRIALS, "r28_fixed_trial")
    index = TRIALS.index(trial_id)
    before = ast.parse(original.decode("utf-8"))
    classes = [n for n in before.body if isinstance(n, ast.ClassDef)
               and n.name == "CBDKParameterExperimentSettings"]
    require(len(classes) == 1, "r28_class")
    tokens = []
    candidate = original
    for prop, old, new in zip(PROPS, ("0.75", "0.08"), TOKENS[index]):
        decls = [n for n in classes[0].body if isinstance(n, ast.AnnAssign)
                 and isinstance(n.target, ast.Name) and n.target.id == prop]
        require(len(decls) == 1 and decls[0].value is None
                and isinstance(decls[0].annotation, ast.Call), "r28_declaration")
        call = decls[0].annotation
        require(ast.unparse(call.func) == "bpy.props.FloatProperty" and not call.args, "r28_constructor")
        defaults = [kw.value for kw in call.keywords if kw.arg == "default"]
        require(len(defaults) == 1 and isinstance(defaults[0], ast.Constant)
                and type(defaults[0].value) is float and defaults[0].value == float(old),
                "r28_default")
        needle = ("default=" + old).encode("ascii")
        require(original.count(needle) == 1, "r28_unique_token")
        offset = original.index(needle) + len(b"default=")
        node = defaults[0]
        require(node.lineno == node.end_lineno
                and offset == sum(map(len, original.splitlines(keepends=True)[:node.lineno-1])) + node.col_offset
                and node.end_col_offset - node.col_offset == 4, "r28_ast_span")
        if old != new:
            tokens.append(dict(property=prop, byte_offset=offset, old_token=old, new_token=new))
            candidate = candidate[:offset] + new.encode("ascii") + candidate[offset+4:]
            node.value = float(new)
    require(len(tokens) == (2 if index == 1 else 1) and sha(candidate) == DIGESTS[index]
            and ast.dump(before) == ast.dump(ast.parse(candidate.decode("utf-8"))), "r28_exact_diff")
    require(reverse_pair(candidate, tokens) == original, "r28_exact_inverse")
    return candidate, dict(tokens=tokens, ast_diff_verified=True, exact_diff_verified=True,
                           restored_sha256=SOURCE_SHA)


def reverse_pair(candidate, tokens):
    result = candidate
    for row in reversed(tokens):
        offset = row["byte_offset"]
        require(result[offset:offset+4] == row["new_token"].encode("ascii"), "r28_reverse_token")
        result = result[:offset] + row["old_token"].encode("ascii") + result[offset+4:]
    require(sha(result) == SOURCE_SHA, "r28_reverse_digest")
    return result


def normalize_history(review):
    require(review["status"] in ("completed", "budget_exhausted", "incomplete")
            and all(v is False for v in review["safety"].values()), "r28_b_rejected")
    return dict(budget=review["budget"], rows=[
        dict(trial_id=row["trial_id"], generated_score=row["scores"]["generated_mesh"],
             imported_score=row["scores"]["imported_glb_mesh"], decision=row["decision"],
             best_before=row["best_trial_before"], best_after=row["best_trial_after"])
        for row in review["trials"]], best_id=review["best_trial_id"],
        stop_reason="target_reached" if review["stop_reason"] == "observed_target_reached" else review["stop_reason"],
        target_reached=review["observed_target_reached"])


def run():
    import bpy
    from scripts import blender_parameter_r27_parent as r27
    from scripts import blender_parameter_experiment_smoke as r26
    from scripts import blender_parameter_source_r28_smoke as c
    from scripts import parameter_source_r28_copy as copy
    from cbdk.parameter_candidate_review_r28 import review_fixed_candidates
    from cbdk.parameter_candidate_evidence_r28 import reduce_candidate_evidence

    prior = parent_identity()
    run_id, version, source_sha = (os.environ["CBDK_R28_" + k] for k in
                                  ("RUN_ID", "BLENDER_VERSION", "SOURCE_SHA256"))
    r27_id = os.environ["CBDK_R27_RUN_ID"]
    require(bpy.app.background and ".".join(map(str, bpy.app.version)) == version
            and prior["blender_version"] == version and prior["source_sha256"] == source_sha == SOURCE_SHA
            and len({run_id, prior["run_id"], r27_id}) == 3
            and len(run_id) == 32 and all(x in "0123456789abcdef" for x in run_id), "r28_parent_identity")
    original = SOURCE.read_bytes()
    require(digest(SOURCE) == SOURCE_SHA, "r28_source")
    allowed, diffs, c_diffs = {}, {}, {}
    for trial in TRIALS:
        allowed[trial], diffs[trial] = fixed_pair(original, trial)
        c_bytes, c_edits = copy._derive(original, trial)
        require(c_bytes == allowed[trial] and copy.inverse_bytes(c_bytes, original, trial) == original,
                "r28_c_pair")
        c_tokens = [dict(property="sphere_radius" if old == b"0.75" else "bevel_width",
                         byte_offset=offset, old_token=old.decode("ascii"), new_token=new.decode("ascii"))
                    for offset, old, new in c_edits]
        c_diffs[trial] = dict(tokens=c_tokens, ast_diff_verified=True, exact_diff_verified=True,
                              restored_sha256=sha(copy.inverse_bytes(c_bytes, original, trial)))
        require(c_diffs[trial] == diffs[trial], "r28_c_diff")

    # The existing R27 entry's run() is unchanged; its specialist __main__
    # hook is not invoked, so C R28 is run exactly once.
    r27.run()
    legacy = read_json(ROOT / "parameter_experiment.json")
    detail = read_json(ROOT / "parameter_experiment_r26_details.json")
    verify_details(detail, prior, legacy, ROOT)
    prior_files = {ROOT / name: digest(ROOT / name) for name in
                   ("parameter_experiment.json", "parameter_experiment_r26_native.json",
                    "parameter_experiment_r26_static.json", "parameter_experiment_r26_details.json")}
    reference_hashes = {name: digest(ROOT / (name + ".glb")) for name in REFERENCES}
    require(reference_hashes == detail["glb_sha256"], "r28_reference_sha")
    prior_files.update({ROOT / (name + ".glb"): value for name, value in reference_hashes.items()})
    prior_dir = ROOT / "parameter_source_r27"
    def tree_hashes():
        require(prior_dir.is_dir() and not prior_dir.is_symlink(), "r28_prior_dir")
        paths = sorted(prior_dir.rglob("*"))
        require(not any(p.is_symlink() for p in paths), "r28_prior_symlink")
        return {p.relative_to(prior_dir).as_posix(): digest(p) for p in paths if p.is_file()}
    prior_tree = tree_hashes()
    require(set(prior_tree) == {SOURCE.name, "native.json", "details.json", "a_combined.json",
                                "original.glb", "candidate.glb", "restored.glb"}, "r28_prior_inventory")
    old_r27 = read_json(prior_dir / "a_combined.json")
    require(old_r27["evidence"]["run_id"] == r27_id and old_r27["reference_run_id"] == prior["run_id"]
            and old_r27["evidence"]["status"] == "verified_fixed_observations"
            and prior_tree[SOURCE.name] == SOURCE_SHA, "r28_prior_binding")

    def preserved():
        return (SOURCE.read_bytes() == original and all(digest(p) == v for p,v in prior_files.items())
                and tree_hashes() == prior_tree)

    # Independently reimport all seven same-job references. Generated metrics
    # are the earlier actual R26 observations from the trusted run above.
    references = {}
    for name in REFERENCES:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        path = ROOT / (name + ".glb")
        require(digest(path) == reference_hashes[name] and
                bpy.ops.import_scene.gltf(filepath=str(path)) == {"FINISHED"}, "r28_reference_import")
        imported = summaries(r26._snapshot())
        require(imported == legacy["imported_glb_mesh"][name], "r28_reference_measurement")
        references[name] = dict(glb_sha256=digest(path), generated_mesh=legacy["generated_mesh"][name],
                                imported_glb_mesh=imported)
        r26._clean_scene()
    require(preserved(), "r28_prior_changed")

    work = ROOT / "parameter_source_r28"
    require(not work.exists() and not work.is_symlink(), "r28_fresh_work")
    identity = dict(case_id="parameter_source_r28", run_id=run_id, blender_version=version,
                    source_sha256=SOURCE_SHA, reference_run_id=prior["run_id"])
    events, measured, actual_candidates, stage_owners = [], {}, {}, {}
    stage_data = {}
    completed = set()

    def absent():
        return (c.MODULE_NAME not in sys.modules
                and not hasattr(bpy.types.Scene, c.POINTER)
                and bpy.types.Scene.bl_rna.properties.get(c.POINTER) is None
                and all(not hasattr(bpy.types, name) for name in
                        ("CBDKParameterExperimentSettings", "CBDK_OT_parameter_experiment_build")))

    def readback():
        mod = sys.modules.get(c.MODULE_NAME)
        require(mod is not None and all(cls.is_registered for cls in mod.CLASSES), "r28_registration")
        cls = mod.CBDKParameterExperimentSettings
        pointer = bpy.types.Scene.bl_rna.properties.get(c.POINTER)
        settings = getattr(bpy.context.scene, c.POINTER)
        require(pointer is not None and pointer.type == "POINTER"
                and pointer.fixed_type.identifier == cls.bl_rna.identifier
                and isinstance(settings, cls) and settings.id_data == bpy.context.scene,
                "r28_actual_settings")
        values = {}
        for prop in PROPS:
            row = settings.bl_rna.properties.get(prop)
            val = float(getattr(settings, prop))
            require(row is not None and row.type == "FLOAT" and not row.is_array
                    and not settings.is_property_set(prop) and abs(val-float(row.default)) <= 1e-6,
                    "r28_rna_default")
            values[prop] = val
        return values, tuple(mod.CLASSES)

    def observe(trial, stage, phase, path, glb):
        pos = len(events)
        require(pos < 60 and (trial, stage, phase) ==
                (TRIALS[pos//15], STAGES[(pos//5)%3], PHASES[pos%5]), "r28_observer_order")
        key = (trial, stage)
        require(path == work / trial / SOURCE.name and glb == work / trial / (stage + ".glb")
                and all(not p.is_symlink() for p in (work, path.parent, path, glb))
                and path.is_file(), "r28_isolated_paths")
        expected = allowed[trial] if stage == "candidate" else original
        blob = path.read_bytes()
        require(blob == expected and digest(path) == sha(expected), "r28_actual_copy")
        if phase == "before_compile":
            require(absent() and not glb.exists(), "r28_before_compile")
            if stage == "original":
                require(preserved() and all((work / t / SOURCE.name).read_bytes() == original for t in completed),
                        "r28_previous_trial_changed")
            if stage == "candidate":
                actual_candidates[trial] = blob
            if stage == "restored":
                require(reverse_pair(actual_candidates[trial], diffs[trial]["tokens"]) == blob,
                        "r28_observed_inverse")
            stage_data[key] = dict(actual_source_sha256=sha(blob))
        row = stage_data[key]
        if phase in ("registered", "generated_mesh", "imported_glb_mesh"):
            values, owners = readback()
            expected_values = tuple(map(float, TOKENS[TRIALS.index(trial)])) if stage == "candidate" else (.75,.08)
            require(all(abs(values[p]-v) <= 1e-6 for p,v in zip(PROPS, expected_values)), "r28_actual_values")
            if phase == "registered":
                require(not glb.exists(), "r28_premature_glb")
                stage_owners[key] = owners
                row.update(rna_defaults=values, registered=True)
            else:
                require(owners == stage_owners[key] and values == row["rna_defaults"], "r28_readback_changed")
                row[phase] = summaries(r26._snapshot())
                if phase == "generated_mesh":
                    require(not glb.exists(), "r28_premature_glb")
                    row["rna_after_build"] = values
                else:
                    row["glb_sha256"] = digest(glb)
        if phase == "cleaned":
            require(absent() and all(not cls.is_registered for cls in stage_owners[key])
                    and not bpy.context.scene.objects and digest(glb) == row["glb_sha256"],
                    "r28_cleanup")
            row["cleanup_verified"] = True
            if stage == "restored":
                require(preserved(), "r28_trial_preservation")
                completed.add(trial)
        events.append(dict(trial_id=trial, stage=stage, phase=phase, source_sha256=sha(blob)))

    native = c.run_source_trials(ROOT, run_id=run_id, expected_source_sha256=SOURCE_SHA,
                                 expected_blender_version=version, observe=observe)
    require(native == read_json(work / "native.json") and len(events) == 60 and completed == set(TRIALS)
            and actual_candidates == allowed and absent() and preserved(), "r28_observations")
    details = read_json(work / "details.json")
    require(all(native[k] == v and details[k] == v for k,v in identity.items())
            and details["run_id_origin"] == "parent_supplied"
            and details["reference_report_sha256"] == prior_files[ROOT / "parameter_experiment.json"]
            and details["reference_glb_sha256"] == reference_hashes
            and details["prior_r27_run_id"] == r27_id and details["prior_r27_sha256"] == prior_tree
            and all(native[k] is True for k in ("cleanup_verified", "source_unchanged", "references_unchanged"))
            and all(native[k] is False for k in ("auto_apply", "auto_adopt", "auto_approve"))
            and len(native["trials"]) == 4, "r28_native_identity")

    claimed = []
    for trial, observed in zip(TRIALS, native["trials"]):
        path = work / trial / SOURCE.name
        require(observed["trial_id"] == trial and observed["candidate_sha256"] == sha(actual_candidates[trial])
                and path.read_bytes() == original and digest(path) == SOURCE_SHA
                and len(observed["stages"]) == 3, "r28_trial_identity")
        ti = dict(**identity, trial_id=trial, candidate_sha256=sha(actual_candidates[trial]))
        parent_stages, c_stages = [], []
        for stage, cr in zip(STAGES, observed["stages"]):
            actual = stage_data[(trial, stage)]
            require(cr["stage"] == stage and digest(work / trial / (stage + ".glb")) == actual["glb_sha256"],
                    "r28_stage_file")
            parent_stages.append(dict(**ti, stage=stage, **actual))
            c_stages.append(dict(**ti, stage=cr["stage"], actual_source_sha256=cr["actual_source_sha256"],
                rna_defaults=cr["rna_defaults"], rna_after_build=cr["rna_after_build"],
                registered=cr["registered"], cleanup_verified=cr["unregistered"],
                glb_sha256=cr["glb_sha256"], generated_mesh=cr["generated_mesh"],
                imported_glb_mesh=cr["imported_glb_mesh"]))
        measured[trial] = dict(**ti, diff=diffs[trial], stages=parent_stages,
            isolated_copy_verified=True, restoration_verified=reverse_pair(actual_candidates[trial], diffs[trial]["tokens"]) == path.read_bytes(),
            original_source_unchanged=SOURCE.read_bytes()==original, reference_sha_unchanged=preserved(),
            restored_copy_sha256=digest(path), reference_glb_sha256=reference_hashes)
        # C supplies stage observations; isolation is independently established
        # by the parent path/byte checks, not a C self-attested flag.
        claimed.append(dict(**ti, diff=c_diffs[trial], stages=c_stages,
            isolated_copy_verified=True, restoration_verified=observed["inverse_restored"],
            original_source_unchanged=observed["source_unchanged"], reference_sha_unchanged=observed["references_unchanged"],
            restored_copy_sha256=observed["restored_copy_sha256"], reference_glb_sha256=details["reference_glb_sha256"]))
        require(observed["cleanup_verified"] is True and measured[trial] == claimed[-1], "r28_independent_trial_mismatch")

    bound_refs = dict(**prior, variants=references)
    rows = [dict(trial_id=trial, measurement={k: measured[trial]["stages"][1][k] for k in
            ("glb_sha256", "generated_mesh", "imported_glb_mesh")}) for trial in TRIALS]
    histories = {}
    for budget in range(1,5):
        review = review_fixed_candidates(references["baseline"], references["sphere_radius_changed"], rows[:budget], budget=budget)
        history = normalize_history(review)
        selection = reduce_candidate_evidence(claimed[:budget], history, run_id=run_id, blender_version=version,
            reference_run_id=prior["run_id"], source_bytes=original,
            allowed_candidates={t:actual_candidates[t] for t in TRIALS[:budget]},
            measured={t:measured[t] for t in TRIALS[:budget]}, references=bound_refs, budget=budget)
        require(selection["status"] == ("verified_fixed_history" if budget == 4 else "verified_budget_exhausted")
                and selection["history"] == history and not selection["reason_codes"]
                and all(v is False for v in selection["safety"].values())
                and selection["same_fixture_selection_verified"] is (budget == 4)
                and tuple(r["decision"] for r in history["rows"]) == DECISIONS[:budget]
                and history["best_id"] == ("baseline","baseline","intermediate","target")[budget-1],
                "r28_independent_replay")
        histories[str(budget)] = dict(b_review=review, d_evidence=selection)
    require(preserved() and absent(), "r28_final_preservation")
    record = dict(identity=identity, histories=histories, measured=measured, reference_run_id=prior["run_id"],
                  reference_glb_sha256=reference_hashes, reference_report_sha256=details["reference_report_sha256"],
                  prior_r27_run_id=r27_id, prior_r27_sha256=prior_tree, observed_callback_count=len(events),
                  observed_events=events, native_sha256=digest(work / "native.json"),
                  details_sha256=digest(work / "details.json"), prefix_replay_is_not_native_early_stop=True)
    write_new(work / "a_combined.json", record)
    # Full evidence stays in the fixed CI output. Compact marker carries the
    # independent histories, run binding and summary counts, not raw vertices.
    print("CBDK_R28_A_CANDIDATE_REVIEW_PASS " + json.dumps(dict(
        identity=identity, histories=histories, reference_glb_sha256=reference_hashes,
        reference_report_sha256=record["reference_report_sha256"], prior_r27_run_id=r27_id,
        prior_r27_sha256=prior_tree, observed_callback_count=len(events),
        actual_candidate_sha256={k:sha(v) for k,v in actual_candidates.items()},
        measured_glb_sha256={t:{s["stage"]:s["glb_sha256"] for s in measured[t]["stages"]} for t in TRIALS},
        combined_sha256=digest(work / "a_combined.json"), native_sha256=record["native_sha256"],
        details_sha256=record["details_sha256"], prefix_replay_is_not_native_early_stop=True),
        sort_keys=True, allow_nan=False), flush=True)


if __name__ == "__main__":
    require(sys.argv[sys.argv.index("--")+1:] == ["reports/ci/parameter_experiment"], "r28_fixed_output")
    run()
