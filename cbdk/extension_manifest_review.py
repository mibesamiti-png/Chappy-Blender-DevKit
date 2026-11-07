"""Data-only TOML review. Never imports addon code or emits manifest values."""
import json
from pathlib import Path
import tomllib

from .addon_builder import ROOT
from .extension_manifest import REQUIRED, manifest_field_diagnostics, review_manifest_fields

MAX_BYTES = 32 * 1024


def review_manifest_file(source):
    path = Path(source)
    if path.suffix.lower() != ".toml" or path.is_symlink() or not path.is_file():
        raise ValueError("Expected a regular manifest TOML file")
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ValueError("Manifest file could not be read") from exc
    if len(data) > MAX_BYTES:
        raise ValueError("Manifest exceeds review byte limit")
    try:
        fields = tomllib.loads(data.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError("Manifest TOML could not be parsed; no values accepted") from exc
    if len(fields) > 64:
        raise ValueError("Manifest field count exceeds review limit")
    structure = review_manifest_fields(fields)
    # Unknown key names may themselves be private. Keep only a count and a
    # generic placeholder; no original values or source path in the report.
    for error in structure["errors"]:
        if error["field"] not in REQUIRED:
            error["field"] = "unsupported_field"
    return {"schema_version": 1, "kind": "cbdk_extension_manifest_review",
            "status": "review_only", "structure": structure,
            "field_diagnostics": manifest_field_diagnostics(fields),
            "source_executed": False, "source_modified": False,
            "official_validation_ran": False, "release_authorized": False}


def write_manifest_review(source, output, *, root=ROOT):
    report = review_manifest_file(source)
    relative = Path(output)
    root = Path(root).resolve()
    if (relative.is_absolute() or relative.suffix != ".json" or len(relative.parts) < 3
            or relative.parts[:2] != ("reports", "latest") or ".." in relative.parts):
        raise ValueError("Manifest review must be fresh JSON under reports/latest")
    target = root / relative
    if target.exists() or target.is_symlink() or not target.resolve().is_relative_to(root / "reports/latest"):
        raise ValueError("Unsafe or existing manifest review output")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report
