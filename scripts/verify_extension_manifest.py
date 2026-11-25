"""Official synthetic validator and isolated fixed authored runtime fixture.

The sample SPDX string is a test value, not a license decision for this repo.
R19 executes only code-owned read-only generated fixtures in a temporary repo.
No public installer or release approval.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cbdk.extension_manifest import compare_official_validation
from cbdk.extension_stage_evidence import (STAGES, VERSIONS, generation_diagnostic,
                                          official_validate_observation, reduce_stage_records)
from cbdk.undo_probe_report import R25_PREFIX, validate_grouped_observation
from r25_stage_observer import (STAGE_PREFIX, stage_record, archive_digest, parse_records,
                                finish_failure)
from cbdk.extension_recipe_preview import ci_recipe, write_recipe_extension
from cbdk.extension_authored_fixture import fixture_metadata, write_authored_fixture
from cbdk.extension_preflight import MAX_ARCHIVE_BYTES
from cbdk.extension_synthetic_build import (
    FIXTURE_ID, synthetic_extension_members, write_synthetic_extension_zip,
    verify_synthetic_extension_bytes,
)

FIXTURE = {
    "schema_version": "1.0.0", "id": "cbdk_validator_fixture", "version": "0.0.1",
    "name": "CBDK validator fixture", "tagline": "Synthetic validation fixture",
    "maintainer": "CBDK synthetic test", "type": "add-on",
    "blender_version_min": "4.4.0", "license": ["SPDX:GPL-3.0-or-later"],
}


def verify_synthetic_package(blender, root):
    """Exercise both generated ZIP and official build on the fixed source."""
    fields = {**FIXTURE, "id": FIXTURE_ID,
              "name": "CBDK synthetic extension fixture",
              "blender_version_max": "5.3.0",
              "permissions": {"files": "Synthetic declaration only"}}
    source = root / "r18_synthetic_source"
    source.mkdir()
    for name, data in synthetic_extension_members(fields).items():
        (source / name).write_bytes(data)
    generated = root / "r18_generated.zip"
    direct_report = write_synthetic_extension_zip(fields, generated)
    # A duplicate output request must fail without replacing the archive.
    before = generated.read_bytes()
    try:
        write_synthetic_extension_zip(fields, generated)
    except ValueError:
        pass
    else:
        raise AssertionError("R18 duplicate output was accepted")
    if generated.read_bytes() != before:
        raise AssertionError("R18 duplicate output changed archive")
    invalid = root / "r18_invalid.zip"
    try:
        write_synthetic_extension_zip({**fields, "license": None}, invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("R18 invalid manifest accepted")
    if invalid.exists():
        raise AssertionError("R18 invalid manifest emitted ZIP")

    prefix = [blender, "--background", "--factory-startup", "--disable-autoexec",
              "--command", "extension"]

    def validate(path):
        proc = subprocess.run([*prefix, "validate", str(path.resolve())],
                              capture_output=True, text=True, timeout=90)
        checked = compare_official_validation(
            fields, proc.returncode, proc.stdout + "\n" + proc.stderr)
        if proc.returncode != 0 or not checked["complete_diagnostic_agreement"]:
            raise AssertionError("R18 official ZIP validation did not agree")
        return checked

    direct_validation = validate(generated)
    # Official build uses an isolated, fixed source inventory; output is
    # outside that folder so it cannot become another member.
    built = root / "r18_official_build.zip"
    if built.exists():
        raise AssertionError("R18 official output already exists")
    proc = subprocess.run([*prefix, "build", "--source-dir", str(source.resolve()),
                           "--output-filepath", str(built.resolve())],
                          capture_output=True, text=True, timeout=90)
    if proc.returncode != 0 or not built.is_file() or built.is_symlink():
        raise AssertionError("R18 official synthetic ZIP build failed")
    with built.open("rb") as stream:
        official_bytes = stream.read(MAX_ARCHIVE_BYTES + 1)
    official_report = verify_synthetic_extension_bytes(official_bytes, fields)
    official_validation = validate(built)
    print("CBDK_R18_SYNTHETIC_ZIP_VALIDATE_PASS: generated and official-built archives; exact two-member contents")
    print("CBDK_R18_OFFICIAL_BUILD_PASS: build and validate exercised separately; no install or release approval")
    return {
        "generated_archive": direct_report,
        "generated_archive_official_comparison": direct_validation,
        "official_built_archive": official_report,
        "official_built_archive_comparison": official_validation,
        "official_build_exit": proc.returncode,
        "synthetic_extension_zip_created": True,
        "invalid_input_emitted_zip": False,
        "source_executed": False,
        "real_component_license_chosen": False,
        "release_authorized": False,
    }


def verify_authored_package(blender):
    """Do not retain the executable ZIP in reports/CI artifacts."""
    with tempfile.TemporaryDirectory(prefix="cbdk-r19-runtime-") as folder:
        root = Path(folder).resolve()
        archive = root / "authored.zip"
        report = write_authored_fixture(archive)
        env = dict(os.environ)
        for name in ("RESOURCES", "CONFIG", "SCRIPTS", "EXTENSIONS", "DATAFILES"):
            target = root / name.lower()
            target.mkdir()
            env["BLENDER_USER_" + name] = str(target)
        env["CBDK_R19_TEMP"] = str(root)
        prefix = [blender, "--background", "--factory-startup", "--disable-autoexec",
                  "--offline-mode"]
        proc = subprocess.run([*prefix, "--command", "extension", "validate", str(archive)],
                              env=env, capture_output=True, text=True, timeout=90)
        checked = compare_official_validation(
            fixture_metadata(), proc.returncode, proc.stdout + "\n" + proc.stderr)
        if proc.returncode != 0 or not checked["complete_diagnostic_agreement"]:
            raise AssertionError("R19 official authored ZIP validation failed")
        print("CBDK_R19_AUTHORED_EXTENSION_VALIDATE_PASS: actual generated root ZIP")
        proc = subprocess.run([*prefix, "--python-exit-code", "1", "--python",
                               str(ROOT / "scripts/verify_authored_extension_runtime.py")],
                              env=env, capture_output=True, text=True, timeout=120)
        marker = "CBDK_R19_AUTHORED_EXTENSION_RUNTIME_PASS:"
        typed_marker = "CBDK_R19_TYPED_EXTENSION_VERTICAL_PASS:"
        if (proc.returncode != 0
                or not any(line.startswith(marker) for line in proc.stdout.splitlines())
                or not any(line.startswith(typed_marker) for line in proc.stdout.splitlines())):
            for line in (proc.stdout + "\n" + proc.stderr).splitlines():
                if line.startswith("AssertionError: R19 "):
                    print(line[:200])
            raise AssertionError("R19 isolated Extension runtime failed")
        print(marker + " real local repo namespace, bounds/center, disable; manual staging only")
        print(typed_marker + " same validated ZIP, inline precision 2 -> 1, native result and cleanup")
        return {**report, "official_validation": checked,
                "typed_extension_vertical_verified": True,
                "isolated_authored_source_executed": True,
                "native_namespace_runtime_verified": True,
                "official_install_exercised": False,
                "manual_local_repository_staging": True,
                "temporary_archive_retained": False}


def verify_recipe_packages(blender, output):
    """Actual stage observations for fixed local-only recipe variants."""
    version = os.environ.get("BLENDER_VERSION")
    if version not in VERSIONS:
        raise ValueError("R25 requires fixed CI Blender target version")
    results = {}
    for case in ("read", "edit", "grouped"):
        run_id = uuid.uuid4().hex
        records = []
        digest = None
        def add(stage, status, *, sha=None, diagnostic=None):
            records.append(stage_record(case, version, run_id, sha, stage, status, diagnostic))
        def save():
            summary = reduce_stage_records(records, case=case, blender=version, run_id=run_id)
            evidence = {"summary": summary}
            if summary["status"] != "rejected":
                evidence["records"] = records
            (output / ("r25_stage_" + case + ".json")).write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print("CBDK_R25_STAGE_SUMMARY " + json.dumps(summary, sort_keys=True), flush=True)
            return summary
        def fail():
            finish_failure(records)
            save()
            raise AssertionError("R25 fixed stage verification failed: " + case)
        with tempfile.TemporaryDirectory(prefix="cbdk-r23-runtime-") as folder:
            root = Path(folder).resolve()
            archive = root / "authored.zip"
            try:
                if case == "grouped":
                    sys.path.insert(0, str(ROOT / "tests"))
                    from test_ui_recipe_r17 import make_r23_recipe
                    recipe_path = root / "recipe.json"
                    source = json.dumps(make_r23_recipe("grouped"), ensure_ascii=False).encode("utf-8")
                    recipe_path.write_bytes(source)
                    built = subprocess.run([sys.executable, "-m", "cbdk", "build-extension-preview",
                                            "--recipe", str(recipe_path), "--output", str(archive),
                                            "--preview-unapproved"], cwd=ROOT, capture_output=True,
                                           text=True, timeout=90)
                    if built.returncode != 0:
                        raise AssertionError("R23 combined CLI generation failed: " + built.stderr[-400:])
                    report = json.loads(built.stdout)
                    if (recipe_path.read_bytes() != source or report["feature_count"] != 4
                            or report["preview_only"] is not True or report["approved"] is not False
                            or report["install_authorized"] is not False or report["release_authorized"] is not False
                            or report["original_preview_unchanged"] is not True):
                        raise AssertionError("R23 combined CLI report mismatch")
                else:
                    report = write_recipe_extension(ci_recipe(case), archive, preview_unapproved=True)
                digest = archive_digest(archive)
                if digest is None:
                    raise ValueError("Missing generated archive")
            except Exception as exc:
                add("generation", "failed", diagnostic=generation_diagnostic(exc))
                fail()
            add("generation", "passed", sha=digest)
            env = dict(os.environ)
            for name in ("RESOURCES", "CONFIG", "SCRIPTS", "EXTENSIONS", "DATAFILES"):
                target = root / name.lower()
                target.mkdir()
                env["BLENDER_USER_" + name] = str(target)
            env["CBDK_R19_TEMP"] = str(root)
            env["CBDK_R23_CASE"] = case
            env["CBDK_R25_RUN_ID"] = run_id
            prefix = [blender, "--background", "--factory-startup", "--disable-autoexec",
                      "--offline-mode"]
            try:
                proc = subprocess.run([*prefix, "--command", "extension", "validate", str(archive)],
                                      env=env, capture_output=True, text=True, timeout=90)
                status, diagnostic = official_validate_observation(
                    fixture_metadata(), proc.returncode, proc.stdout + "\n" + proc.stderr)
            except (OSError, subprocess.TimeoutExpired):
                status, diagnostic = "failed", "official_unclassified"
            add("validate", status, sha=archive_digest(archive), diagnostic=diagnostic)
            if status != "passed" or records[-1]["artifact_sha256"] != digest:
                fail()
            checked = compare_official_validation(
                fixture_metadata(), proc.returncode, proc.stdout + "\n" + proc.stderr)
            print("CBDK_R23_RECIPE_EXTENSION_VALIDATE_PASS: " + case)
            try:
                proc = subprocess.run([*prefix, "--python-exit-code", "1", "--python",
                                       str(ROOT / "scripts/verify_recipe_extension_runtime.py")],
                                      env=env, capture_output=True, text=True, timeout=120)
                records.extend(parse_records(proc.stdout, STAGE_PREFIX, max_records=3))
            except (OSError, subprocess.TimeoutExpired, ValueError):
                save()
                raise AssertionError("R25 child evidence unavailable: " + case) from None
            marker = "CBDK_R23_RECIPE_EXTENSION_RUNTIME_PASS: " + case
            partial = reduce_stage_records(records, case=case, blender=version, run_id=run_id)
            if (proc.returncode != 0 or marker not in proc.stdout.splitlines()
                    or partial["status"] != "incomplete"
                    or partial["passed_stages"] != list(STAGES[:5])):
                fail()
            print(marker)
            grouped = None
            if case == "grouped":
                vertical = "CBDK_R23_A_MULTIPANEL_EXTENSION_VERTICAL_PASS: two panels, four features, typed read/edit and cleanup"
                try:
                    observations = parse_records(proc.stdout, R25_PREFIX, max_records=1)
                    if len(observations) != 1:
                        raise ValueError("Missing grouped observation")
                    grouped = validate_grouped_observation(observations[0])
                    if (grouped["artifact_sha256"] != digest or grouped["blender_version"] != version
                            or vertical not in proc.stdout.splitlines()):
                        raise ValueError("Grouped evidence mismatch")
                except ValueError:
                    save()
                    raise AssertionError("R25 grouped Undo evidence invalid") from None
                print(vertical)
            after = archive_digest(archive)
            add("sha_unchanged", "passed" if after == digest else "failed", sha=after)
            summary = save()
            if summary["status"] != "verified_fixed_stages":
                raise AssertionError("R25 final stage evidence rejected")
            if grouped is not None:
                print(R25_PREFIX + json.dumps(grouped, sort_keys=True), flush=True)
                report.update(same_archive_sha_unchanged=True, extension_sha256=digest,
                              cli_generated=True, native_two_panel_draw_verified=True,
                              real_windows_gui_tested=False, r25_grouped_undo=grouped)
            results[case] = {**report, "official_validation": checked,
                             "native_namespace_runtime_verified": True,
                             "manual_local_repository_staging": True,
                             "official_install_exercised": False,
                             "temporary_archive_retained": False,
                             "r25_stage_summary": summary}
    print("CBDK_R23_RECIPE_EXTENSION_MATRIX_PASS: two separate generated ZIPs")
    print("CBDK_R23_A_COMBINED_MATRIX_PASS: additional same-artifact four-feature CLI vertical")
    print("CBDK_R25_A_SAME_ARTIFACT_STAGE_MATRIX_PASS: read/edit/grouped; grouped Undo separate")
    return results


def verify_dependency_package(blender):
    """Fixed internal graph only; same artifact is validated and executed."""
    import hashlib
    sys.path.insert(0, str(ROOT / "tests"))
    from extension_r24_dependency_fixture import dependency_catalog, dependency_recipe, MEMBERS, ORDER, PARTS
    from test_ui_recipe_r17 import (prepare_r24_root, make_r24_recipe, r24_source_hashes,
                                   R24_ORDER, R24_PARTS, R24_MEMBERS)
    from cbdk.modular_builder import build_modular, PACKAGE_ID
    from cbdk.extension_authored_fixture import _without_legacy_info
    from zipfile import ZipFile
    with tempfile.TemporaryDirectory(prefix="cbdk-r24-runtime-") as folder:
        root = Path(folder).resolve()
        archive = root / "authored.zip"
        source_hashes = r24_source_hashes()
        recipe = make_r24_recipe()
        if recipe != dependency_recipe() or ORDER != R24_ORDER or PARTS != R24_PARTS:
            raise AssertionError("R24 A specialist fixture disagreement")
        c_root = prepare_r24_root(root / "c_fixture")
        legacy = root / "c_preview.zip"
        built = build_modular(recipe, legacy, preview_unapproved=True, root=c_root)
        if (tuple(built["features"]) != R24_ORDER or tuple(built["part_ids"]) != R24_PARTS
                or built["approved"] is not False):
            raise AssertionError("R24 A legacy build closure mismatch")
        legacy_sha = hashlib.sha256(legacy.read_bytes()).hexdigest()
        with dependency_catalog() as catalog_sha:
            report = write_recipe_extension(dependency_recipe(), archive, preview_unapproved=True)
        with ZipFile(archive) as z:
            if len(z.infolist()) != len(MEMBERS) or set(z.namelist()) != MEMBERS:
                raise AssertionError("R24 dependency Extension inventory mismatch")
        prefix = PACKAGE_ID + "/"
        with ZipFile(legacy) as old, ZipFile(archive) as new:
            if (len(old.infolist()) != len(R24_MEMBERS)
                    or set(old.namelist()) != {prefix+n for n in R24_MEMBERS}
                    or MEMBERS != (set(R24_MEMBERS) - {"README.txt", "CBDK_BUILD_INFO.json"}
                                   | {"blender_manifest.toml"})):
                raise AssertionError("R24 A cross-format inventory mismatch")
            meta = json.loads(old.read(prefix+"CBDK_BUILD_INFO.json"))
            if (meta["requested_features"] != ["vertex_nudge"]
                    or tuple(meta["features"]) != R24_ORDER
                    or tuple(meta["part_ids"]) != R24_PARTS):
                raise AssertionError("R24 A requested/resolved provenance mismatch")
            for name in sorted(MEMBERS - {"blender_manifest.toml"}):
                payload = old.read(prefix+name)
                if name == "__init__.py":
                    payload = _without_legacy_info(payload)
                if new.read(name) != payload:
                    raise AssertionError("R24 A cross-format executable bytes mismatch")
        print("CBDK_R24_A_CROSS_FORMAT_PAYLOAD_PASS: requested 1, resolved 4, shared 5 parts")
        if (report["feature_count"] != 4 or report["approved"] is not False
                or report["release_authorized"] is not False or report["install_authorized"] is not False
                or report["original_preview_unchanged"] is not True):
            raise AssertionError("R24 dependency Extension report mismatch")
        archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        env = dict(os.environ)
        for name in ("RESOURCES", "CONFIG", "SCRIPTS", "EXTENSIONS", "DATAFILES"):
            target = root / name.lower()
            target.mkdir()
            env["BLENDER_USER_" + name] = str(target)
        env["CBDK_R19_TEMP"] = str(root)
        env["CBDK_R23_CASE"] = "dependency"
        prefix = [blender, "--background", "--factory-startup", "--disable-autoexec", "--offline-mode"]
        proc = subprocess.run([*prefix, "--command", "extension", "validate", str(archive)],
                              env=env, capture_output=True, text=True, timeout=90)
        checked = compare_official_validation(fixture_metadata(), proc.returncode,
                                              proc.stdout + "\n" + proc.stderr)
        if proc.returncode != 0 or not checked["complete_diagnostic_agreement"]:
            raise AssertionError("R24 dependency Extension official validation failed")
        print("CBDK_R24_DEPENDENCY_EXTENSION_VALIDATE_PASS: fixed graph root ZIP")
        proc = subprocess.run([*prefix, "--python-exit-code", "1", "--python",
                               str(ROOT / "scripts/verify_recipe_extension_runtime.py")],
                              env=env, capture_output=True, text=True, timeout=120)
        marker = "CBDK_R24_DEPENDENCY_EXTENSION_RUNTIME_PASS: requested 1, resolved 4, typed read/edit and cleanup"
        vertical = "CBDK_R24_A_EXTENSION_ORDER_ROLLBACK_PASS: actual register/reverse, midpoint rollback"
        if (proc.returncode != 0 or marker not in proc.stdout.splitlines()
                or vertical not in proc.stdout.splitlines()):
            for line in (proc.stdout + "\n" + proc.stderr).splitlines():
                if line.startswith(("AssertionError: R24 ", "AssertionError: R23 ")):
                    print(line[:200])
            raise AssertionError("R24 isolated dependency runtime failed")
        if (hashlib.sha256(archive.read_bytes()).hexdigest() != archive_sha
                or hashlib.sha256((ROOT / "catalog/addon_features.json").read_bytes()).hexdigest() != catalog_sha
                or hashlib.sha256(legacy.read_bytes()).hexdigest() != legacy_sha
                or r24_source_hashes() != source_hashes):
            raise AssertionError("R24 archive or real catalog changed")
        print(marker)
        print("CBDK_R24_DEPENDENCY_EXTENSION_SAME_ZIP_PASS: SHA unchanged")
        print(vertical)
        print("CBDK_R24_A_COMBINED_VERTICAL_PASS: C payload, D official validate, same ZIP runtime and rollback")
        return {**report, "requested_feature_count": 1, "official_validation": checked,
                "extension_sha256": archive_sha, "catalog_sha_unchanged": True,
                 "legacy_sha256": legacy_sha, "legacy_sha_unchanged": True,
                 "cross_format_payload_equal": True, "native_actual_order_and_rollback_verified": True,
                "same_archive_sha_unchanged": True, "native_namespace_runtime_verified": True,
                "official_install_exercised": False, "manual_local_repository_staging": True,
                "temporary_archive_retained": False}


def verify(blender, output):
    root = Path(output)
    if not root.parent.resolve().is_relative_to(ROOT / "reports/ci") or root.exists():
        raise ValueError("Expected fresh reports/ci fixture directory")
    root.mkdir(parents=True)
    results = []
    required_cases = (("valid_subset", {}, True),
                                    ("missing_license", {"license": None}, False),
                                    ("punctuated_tagline", {"tagline": "Invalid tagline!"}, False),
                                    ("invalid_id", {"id": "invalid-id"}, False),
                                    ("invalid_version", {"version": "not-version"}, False),
                                    ("empty_maintainer", {"maintainer": ""}, False))
    # Local expectations are intentionally separate from official observations:
    # some Blender releases may accept a locally unsupported declaration.
    optional_cases = (
        ("optional_valid", {"blender_version_max": "5.3.0",
                            "permissions": {"files": "Read synthetic data"}}, "structurally_valid_subset"),
        ("optional_bad_max", {"blender_version_max": "not-version"}, "invalid"),
        ("optional_equal_max", {"blender_version_max": "4.4.0"}, "invalid"),
        ("optional_bad_permissions_type", {"permissions": 7}, "invalid"),
        ("optional_unknown_permission", {"permissions": {"synthetic_unknown": "Read data"}}, "invalid"),
        ("optional_legacy_permissions", {"permissions": ["files"]}, "invalid"),
        ("optional_unsupported_website", {"website": "https://example.invalid"}, "invalid"),
    )
    cases = [(name, change, expected, None) for name, change, expected in required_cases]
    cases += [(name, change, None, local) for name, change, local in optional_cases]
    for name, change, expected, local_expected in cases:
        fields = {**FIXTURE, **change}
        folder = root / name
        folder.mkdir()
        # JSON literals for the fixture's ASCII strings/arrays are also TOML
        # literals. No user text, code, license inference or general serializer.
        (folder / "blender_manifest.toml").write_text("\n".join(
            key + " = " + (
                "{ " + ", ".join(k + " = " + json.dumps(v) for k, v in value.items()) + " }"
                if isinstance(value, dict) else json.dumps(value)
            ) for key, value in fields.items() if value is not None) + "\n", encoding="utf-8")
        (folder / "__init__.py").write_text('raise RuntimeError("validator must never import fixture")\n', encoding="utf-8")
        proc = subprocess.run([blender, "--background", "--factory-startup", "--disable-autoexec",
                               "--command", "extension", "validate", str(folder.resolve())],
                              capture_output=True, text=True, timeout=90)
        compared = compare_official_validation(fields, proc.returncode, proc.stdout + "\n" + proc.stderr)
        if expected is not None:
            # The original six cases remain strict regression gates.
            if ((proc.returncode == 0) != expected or not compared["complete_diagnostic_agreement"]):
                raise AssertionError("Official manifest validator disagrees with synthetic case: " + name)
        else:
            if compared["local_status"] != local_expected:
                raise AssertionError("Unexpected local optional fixture classification: " + name)
            if name == "optional_valid" and (
                    proc.returncode != 0 or not compared["complete_diagnostic_agreement"]):
                raise AssertionError("Official validator rejected supported optional positive")
            # A permissive CLI or unfamiliar wording is evidence of a limit,
            # not grounds to expand local approval. A crash is not a fixture
            # verdict. Other unclassified outcomes remain visible in the log.
            if proc.returncode < 0:
                raise AssertionError("Official validator terminated abnormally: " + name)
            print("CBDK_R17_OPTIONAL_CASE", name,
                  "exit=" + str(proc.returncode),
                  "official=" + compared["official_observation"]["status"],
                  "comparison=" + compared["status"])
        results.append({"case": name, "official_accepted": proc.returncode == 0,
                        "local_status": compared["local_status"], "diagnostic_comparison": compared})
    package = verify_synthetic_package(blender, root)
    authored = verify_authored_package(blender)
    recipes = verify_recipe_packages(blender, root)
    dependency = verify_dependency_package(blender)
    report = {"kind": "cbdk_synthetic_official_manifest_validation", "cases": results,
              "synthetic_package": package,
              "authored_runtime_fixture": authored,
              "r23_recipe_runtime_fixtures": recipes,
              "r24_dependency_runtime_fixture": dependency,
              "top_level_source_executed_scope": "synthetic_fixture_only",
              "real_component_license_chosen": False, "real_extension_validated": False,
              "source_executed": False, "extension_zip_created": True,
              "real_extension_zip_created": False}
    (root / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("CBDK_SYNTHETIC_OFFICIAL_MANIFEST_PASS (not a component license or release approval)")
    print("CBDK_MANIFEST_DIAGNOSTIC_AGREEMENT_PASS: six synthetic cases, exit codes and fields checked")
    print("CBDK_R17_OPTIONAL_OBSERVATIONS_COMPLETE: seven synthetic cases; see individual comparisons")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    verify(args.blender, args.output)
