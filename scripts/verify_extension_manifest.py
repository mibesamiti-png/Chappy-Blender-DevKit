"""Official validator on data-only synthetic fixtures, never CBDK components.

The sample SPDX string is a test value, not a license decision for this repo.
No extension ZIP/build/install, no addon import or runtime approval.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cbdk.extension_manifest import compare_official_validation

FIXTURE = {
    "schema_version": "1.0.0", "id": "cbdk_validator_fixture", "version": "0.0.1",
    "name": "CBDK validator fixture", "tagline": "Synthetic validation fixture",
    "maintainer": "CBDK synthetic test", "type": "add-on",
    "blender_version_min": "4.4.0", "license": ["SPDX:GPL-3.0-or-later"],
}


def verify(blender, output):
    root = Path(output)
    if not root.parent.resolve().is_relative_to(ROOT / "reports/ci") or root.exists():
        raise ValueError("Expected fresh reports/ci fixture directory")
    root.mkdir(parents=True)
    results = []
    for name, change, expected in (("valid_subset", {}, True),
                                    ("missing_license", {"license": None}, False),
                                    ("punctuated_tagline", {"tagline": "Invalid tagline!"}, False),
                                    ("invalid_id", {"id": "invalid-id"}, False),
                                    ("invalid_version", {"version": "not-version"}, False),
                                    ("empty_maintainer", {"maintainer": ""}, False)):
        fields = {**FIXTURE, **change}
        folder = root / name
        folder.mkdir()
        # JSON literals for the fixture's ASCII strings/arrays are also TOML
        # literals. No user text, code, license inference or general serializer.
        (folder / "blender_manifest.toml").write_text("\n".join(
            key + " = " + json.dumps(value) for key, value in fields.items() if value is not None) + "\n", encoding="utf-8")
        (folder / "__init__.py").write_text('raise RuntimeError("validator must never import fixture")\n', encoding="utf-8")
        proc = subprocess.run([blender, "--background", "--factory-startup", "--disable-autoexec",
                               "--command", "extension", "validate", str(folder.resolve())],
                              capture_output=True, text=True, timeout=90)
        compared = compare_official_validation(fields, proc.returncode, proc.stdout + "\n" + proc.stderr)
        if ((proc.returncode == 0) != expected or not compared["complete_diagnostic_agreement"]):
            raise AssertionError("Official manifest validator disagrees with synthetic case: " + name)
        results.append({"case": name, "official_accepted": proc.returncode == 0,
                        "local_status": compared["local_status"], "diagnostic_comparison": compared})
    report = {"kind": "cbdk_synthetic_official_manifest_validation", "cases": results,
              "real_component_license_chosen": False, "real_extension_validated": False,
              "source_executed": False, "extension_zip_created": False}
    (root / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("CBDK_SYNTHETIC_OFFICIAL_MANIFEST_PASS (not a component license or release approval)")
    print("CBDK_MANIFEST_DIAGNOSTIC_AGREEMENT_PASS: six synthetic cases, exit codes and fields checked")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    verify(args.blender, args.output)
