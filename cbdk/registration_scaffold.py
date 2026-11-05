"""Generate review-only failing unittest skeletons from canonical CBDK registration drafts.

The saved draft is revalidated against current allowlists before use. The
generated Python is deliberately unfinished, never imported or run by CBDK,
and is written only to an ignored local reports/latest/scaffolds/ directory.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

from .addon_builder import ROOT
from .registration_draft import MODULE_NAME, PART_ID, REPORT_DIR, propose_registration

MAX_DRAFT_BYTES = 32_768
SCAFFOLD_DIR = Path("reports/latest/scaffolds")
_DRAFT_FIELDS = frozenset({
    "schema_version", "kind", "status", "feature_id", "feature_source",
    "required_parts", "new_part", "current_trusted_features",
    "current_trusted_parts", "review_steps", "preview_only", "approved",
    "redistribution_cleared", "runtime_verified", "source_executed",
    "catalog_modified",
})


def validate_saved_draft(draft: object, *, root: Path = ROOT) -> dict:
    """Reject stale, altered, or forged drafts before interpolating any text."""
    if not isinstance(draft, dict) or set(draft) != _DRAFT_FIELDS:
        raise ValueError("Unexpected registration draft fields")
    if type(draft["schema_version"]) is not int or draft["schema_version"] != 1:
        raise ValueError("Unexpected draft schema")
    new = draft["new_part"]
    part_id = module_name = None
    if new is not None:
        if not isinstance(new, dict) or set(new) != {
                "id", "source", "approved", "license_review"}:
            raise ValueError("Malformed new part proposal")
        part_id = new["id"]
        source = new["source"]
        if not isinstance(part_id, str) or not PART_ID.fullmatch(part_id):
            raise ValueError("Invalid new part ID")
        if not isinstance(source, str) or not source.startswith("parts/blender/") or not source.endswith(".py"):
            raise ValueError("Invalid new part source")
        module_name = source[len("parts/blender/"):-3]
        if not MODULE_NAME.fullmatch(module_name):
            raise ValueError("Invalid new part module")
    # Comparing the entire canonical plan (including all warning flags and
    # checklist steps) forbids accidental promotion of a proposal to approval.
    expected = propose_registration(
        draft["feature_id"], draft["required_parts"],
        new_part_id=part_id, new_part_module=module_name, root=root,
    )
    if draft != expected:
        raise ValueError("Registration draft is stale or modified; regenerate it")
    return expected


def render_test_scaffold(draft: dict, *, root: Path = ROOT) -> str:
    """Render inert source with explicit TODO failures; never run or import it."""
    checked = validate_saved_draft(draft, root=root)
    ident = checked["feature_id"]
    class_name = "CBDK_" + ident + "_ReviewTests"
    part = checked["new_part"]
    required = tuple(checked["required_parts"])
    lines = [
        '"""UNREVIEWED CBDK TEST SCAFFOLD. Not a successful test or approved feature.',
        "",
        "Generated only for local development; TODO assertions intentionally fail.",
        "Do not copy this file into tests/ until implementation and human review.",
        '"""',
        "import unittest",
        "",
        f"FEATURE_ID = {ident!r}",
        f"FEATURE_SOURCE = {checked['feature_source']!r}",
        f"REQUIRED_PARTS = {required!r}",
        f"NEW_PART_SOURCE = {part['source'] if part else None!r}",
        "",
        f"class {class_name}(unittest.TestCase):",
        "    def test_ownership_and_dependency_review(self):",
        '        self.fail("TODO: review authored source ownership and dependency/license evidence")',
        "",
        "    def test_expected_edit_or_object_context(self):",
        '        self.fail("TODO: define supported Blender context, mode and selection behavior")',
        "",
        "    def test_expected_functional_result(self):",
        '        self.fail("TODO: implement a real unit assertion for expected behavior")',
        "",
        "    def test_rejection_does_not_mutate_user_data(self):",
        '        self.fail("TODO: verify invalid input/context leaves mesh, mode and selection intact")',
        "",
        "    def test_undo_redo_and_multi_version_smoke_contract(self):",
        '        self.fail("TODO: define Blender runtime smoke; verify Undo/Redo if destructive")',
        "",
        'if __name__ == "__main__":',
        "    unittest.main()",
        "",
    ]
    content = "\n".join(lines)
    ast.parse(content)
    return content


def _private_relative(path: str | Path, *, root: Path, suffix: str) -> Path:
    relative = Path(path)
    if (relative.is_absolute() or len(relative.parts) < 3
            or relative.parts[:2] != REPORT_DIR.parts
            or ".." in relative.parts or relative.suffix != suffix):
        raise ValueError("File must remain under reports/latest/ with suffix " + suffix)
    project = root.resolve()
    base = project / REPORT_DIR
    target = project / relative
    if not target.resolve().is_relative_to(base):
        raise ValueError("Private report path escapes reports/latest/")
    return target


def read_saved_draft(path: str | Path, *, root: Path = ROOT) -> dict:
    """Read one explicit ignored JSON draft; disallow symlinked source files."""
    target = _private_relative(path, root=root, suffix=".json")
    if target.is_symlink() or not target.is_file() or target.stat().st_size > MAX_DRAFT_BYTES:
        raise ValueError("Missing, symlinked, or oversized registration draft")
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("Invalid JSON registration draft") from exc
    return validate_saved_draft(value, root=root)


def write_test_scaffold(draft: dict, *, root: Path = ROOT) -> Path:
    """Create exactly one ignored, never-overwritten local Python scaffold."""
    checked = validate_saved_draft(draft, root=root)
    output = SCAFFOLD_DIR / ("test_" + checked["feature_id"] + "_review.py")
    target = _private_relative(output, root=root, suffix=".py")
    if target.is_symlink() or target.exists():
        raise FileExistsError("Test scaffold already exists; never overwrite: " + str(target))
    # Path resolution above checks for symlinked parent-directory escapes.
    source = render_test_scaffold(checked, root=root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        stream.write(source)
    return target


def scaffold_from_saved_draft(path: str | Path, *, root: Path = ROOT) -> Path:
    draft = read_saved_draft(path, root=root)
    return write_test_scaffold(draft, root=root)
