"""R27 fixed-source candidate: only one preapproved numeric token.

Internal CI helper, no writing, execution, user paths or configurable values.
The trusted parent must independently verify the bytes it actually executes.
"""
from __future__ import annotations

import ast
import hashlib
import re

from .glb_parameter_static_r26 import (
    FIXTURE, EXPECTED_CLASS, VERSIONS, observe_fixed_parameter_fixture,
)
from .glb_property_usage import MAX_FILE_BYTES

CASE_ID = "parameter_source_r27"
SOURCE_SHA256 = "e645723ff89a99530841e1ccd37ea8d059952eec0f980ac1782d8228e46588e3"
PROPERTY = "sphere_radius"
BEFORE = 0.75
AFTER = 1.15
OLD_TOKEN = b"0.75"
NEW_TOKEN = b"1.15"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _parse(data):
    if type(data) is not bytes or not 1 <= len(data) <= MAX_FILE_BYTES:
        raise ValueError("invalid_fixed_source_bytes")
    try:
        # The fixed fixture is UTF-8; AST columns are UTF-8 byte offsets.
        return ast.parse(data.decode("utf-8"), filename="<fixed_fixture>")
    except (SyntaxError, UnicodeError, ValueError) as exc:
        raise ValueError("invalid_fixed_source_ast") from exc


def _default_node(tree, prop, expected):
    """Locate one direct annotated FloatProperty declaration in the fixed class."""
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)
               and n.name == EXPECTED_CLASS]
    if len(classes) != 1 or classes[0] not in tree.body:
        raise ValueError("fixed_class_not_unique")
    cls = classes[0]
    # Even a same-named property in another class is not an eligible fixture.
    declarations = []
    for owner in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        for node in owner.body:
            targets = ([node.target] if isinstance(node, ast.AnnAssign)
                       else node.targets if isinstance(node, ast.Assign) else [])
            if any(isinstance(t, ast.Name) and t.id == prop for t in targets):
                declarations.append((owner, node))
    if len(declarations) != 1 or declarations[0][0] is not cls:
        raise ValueError("fixed_declaration_not_unique")
    node = declarations[0][1]
    if not isinstance(node, ast.AnnAssign) or node.value is not None:
        raise ValueError("fixed_declaration_shape")
    call = node.annotation
    if (not isinstance(call, ast.Call)
            or ast.dump(call.func) != ast.dump(ast.parse("bpy.props.FloatProperty",
                                                        mode="eval").body)
            or call.args or any(kw.arg is None for kw in call.keywords)):
        raise ValueError("fixed_constructor_shape")
    defaults = [kw.value for kw in call.keywords if kw.arg == "default"]
    if (len(defaults) != 1 or not isinstance(defaults[0], ast.Constant)
            or type(defaults[0].value) is not float or defaults[0].value != expected):
        raise ValueError("fixed_default_value")
    return defaults[0]


def _byte_span(data, node):
    if node.lineno != node.end_lineno:
        raise ValueError("fixed_token_not_single_line")
    lines = data.splitlines(keepends=True)
    prefix = sum(map(len, lines[:node.lineno - 1]))
    return prefix + node.col_offset, prefix + node.end_col_offset


def _derive_candidate(original):
    """Private pure transform; called only with fixed bytes or test controls."""
    tree = _parse(original)
    node = _default_node(tree, PROPERTY, BEFORE)
    _default_node(tree, "bevel_width", 0.08)
    offset, end = _byte_span(original, node)
    if original[offset:end] != OLD_TOKEN or original.count(OLD_TOKEN) != 1:
        raise ValueError("fixed_old_token_not_unique")
    candidate = original[:offset] + NEW_TOKEN + original[end:]
    _check_pair(original, candidate, offset)
    return candidate, offset


def _check_pair(original, candidate, offset):
    """Independent structural and byte comparison, plus exact reverse transform."""
    old_tree = _parse(original)
    new_tree = _parse(candidate)
    old = _default_node(old_tree, PROPERTY, BEFORE)
    new = _default_node(new_tree, PROPERTY, AFTER)
    _default_node(old_tree, "bevel_width", 0.08)
    _default_node(new_tree, "bevel_width", 0.08)
    if (type(offset) is not int
            or _byte_span(original, old) != (offset, offset+len(OLD_TOKEN))
            or _byte_span(candidate, new) != (offset, offset+len(NEW_TOKEN))
            or original[offset:offset+len(OLD_TOKEN)] != OLD_TOKEN
            or candidate[offset:offset+len(NEW_TOKEN)] != NEW_TOKEN
            or original.count(OLD_TOKEN) != 1):
        raise ValueError("fixed_token_span_mismatch")
    if candidate != original[:offset] + NEW_TOKEN + original[offset+len(OLD_TOKEN):]:
        raise ValueError("fixed_candidate_has_other_byte_changes")
    old.value = AFTER
    if ast.dump(old_tree, include_attributes=False) != ast.dump(new_tree, include_attributes=False):
        raise ValueError("fixed_candidate_has_other_ast_changes")
    restored = candidate[:offset] + OLD_TOKEN + candidate[offset+len(NEW_TOKEN):]
    if restored != original or _sha(restored) != _sha(original):
        raise ValueError("fixed_reverse_mismatch")
    return restored


def _read_fixed():
    if FIXTURE.is_symlink() or not FIXTURE.is_file() or FIXTURE.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("fixed_fixture_unavailable")
    original = FIXTURE.read_bytes()
    if len(original) > MAX_FILE_BYTES or _sha(original) != SOURCE_SHA256:
        raise ValueError("fixed_source_sha_mismatch")
    return original


def build_fixed_source_candidate(*, run_id: str, source_sha256: str,
                                 blender_version: str) -> tuple[bytes, dict]:
    """Return permitted candidate bytes and fixed observation, without writing."""
    if (type(run_id) is not str or re.fullmatch("[0-9a-f]{32}", run_id) is None
            or type(source_sha256) is not str or source_sha256 != SOURCE_SHA256
            or type(blender_version) is not str or blender_version not in VERSIONS):
        raise ValueError("invalid_fixed_source_identity")
    original = _read_fixed()
    static = observe_fixed_parameter_fixture(run_id=run_id,
        source_sha256=source_sha256, blender_version=blender_version)
    expected = [
        dict(property=p, declaration_count=1, same_class_self_count=1,
             geometry_path_count=1, expected_api_observed=True)
        for p in (PROPERTY, "bevel_width")
    ]
    if static["properties"] != expected:
        raise ValueError("fixed_static_evidence_mismatch")
    candidate, offset = _derive_candidate(original)
    restored = _check_pair(original, candidate, offset)
    if _read_fixed() != original or restored != original or _sha(restored) != SOURCE_SHA256:
        raise ValueError("fixed_source_or_reverse_mismatch")
    return candidate, {
        "case_id": CASE_ID, "run_id": run_id, "blender_version": blender_version,
        "source_sha256": SOURCE_SHA256, "candidate_sha256": _sha(candidate),
        "property": PROPERTY, "before": BEFORE, "after": AFTER,
        "old_token": OLD_TOKEN.decode("ascii"), "new_token": NEW_TOKEN.decode("ascii"),
        "byte_offset": offset, "single_difference_verified": True,
        "restored_sha256": _sha(restored),
    }


def restore_fixed_source_candidate(candidate: bytes) -> bytes:
    """Pure reverse: accept only the exact fixed candidate, not arbitrary patches."""
    original = _read_fixed()
    expected, offset = _derive_candidate(original)
    if type(candidate) is not bytes or candidate != expected:
        raise ValueError("fixed_candidate_bytes_mismatch")
    restored = _check_pair(original, candidate, offset)
    if restored != original or _sha(restored) != SOURCE_SHA256:
        raise ValueError("fixed_reverse_mismatch")
    return restored
