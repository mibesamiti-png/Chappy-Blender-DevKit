"""Official validator on data-only synthetic fixtures, never CBDK components.

The sample SPDX string is a test value, not a license decision for this repo.
Synthetic ZIP/build/validate only; no install, addon import or runtime approval.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cbdk.extension_manifest import compare_official_validation
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
    report = {"kind": "cbdk_synthetic_official_manifest_validation", "cases": results,
              "synthetic_package": package,
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
