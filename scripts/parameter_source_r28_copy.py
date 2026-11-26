"""Internal R28 fixed candidate byte transaction. No public patch or source input."""
from contextlib import contextmanager
import ast

from scripts.parameter_source_r27_copy import (
    SOURCE, SOURCE_SHA256, COPY_NAME, sha, FixedCopy,
)

TRIALS = (
    ("wrong_direction", .55, .08, "sphere_probe_down", "sphere_probe_down"),
    ("cross_part", 1.15, .20, "sphere_radius_changed", "bevel_probe_up"),
    ("intermediate", .95, .08, "sphere_probe_up", "sphere_probe_up"),
    ("target", 1.15, .08, "sphere_radius_changed", "sphere_radius_changed"),
)
TRIAL_IDS = tuple(row[0] for row in TRIALS)
# These are fixed byte tokens, not configurable numeric formatting.
TOKENS = {
    "wrong_direction": (b"0.55", b"0.08"),
    "cross_part": (b"1.15", b"0.20"),
    "intermediate": (b"0.95", b"0.08"),
    "target": (b"1.15", b"0.08"),
}
PROPS = ("sphere_radius", "bevel_width")
OLD = (b"0.75", b"0.08")


def _node(tree, prop, value):
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)
               and n.name == "CBDKParameterExperimentSettings"]
    if len(classes) != 1 or classes[0] not in tree.body:
        raise ValueError("R28 fixed class mismatch")
    declarations = [(owner, n) for owner in ast.walk(tree) if isinstance(owner, ast.ClassDef)
                    for n in owner.body if isinstance(n, ast.AnnAssign)
                    and isinstance(n.target, ast.Name) and n.target.id == prop]
    if len(declarations) != 1 or declarations[0][0] is not classes[0]:
        raise ValueError("R28 fixed declaration mismatch")
    decl = declarations[0][1]
    call = decl.annotation
    if (decl.value is not None or not isinstance(call, ast.Call) or call.args
            or ast.dump(call.func) != ast.dump(ast.parse("bpy.props.FloatProperty", mode="eval").body)):
        raise ValueError("R28 fixed constructor mismatch")
    defaults = [kw.value for kw in call.keywords if kw.arg == "default"]
    if len(defaults) != 1 or not isinstance(defaults[0], ast.Constant) or type(defaults[0].value) is not float or defaults[0].value != value:
        raise ValueError("R28 fixed default mismatch")
    return defaults[0]


def _span(data, node):
    if node.lineno != node.end_lineno:
        raise ValueError("R28 multiline token")
    base = sum(map(len, data.splitlines(keepends=True)[:node.lineno - 1]))
    return base + node.col_offset, base + node.end_col_offset


def _derive(original, trial_id):
    if type(trial_id) is not str or trial_id not in TOKENS:
        raise ValueError("R28 unknown fixed trial")
    if type(original) is not bytes or sha(original) != SOURCE_SHA256:
        raise ValueError("R28 pinned source mismatch")
    before = ast.parse(original.decode("utf-8"))
    edits = []
    for prop, old, new in zip(PROPS, OLD, TOKENS[trial_id]):
        node = _node(before, prop, float(old))
        start, end = _span(original, node)
        if original[start:end] != old or original.count(old) != 1 or len(old) != len(new):
            raise ValueError("R28 unique fixed token mismatch")
        if old != new:
            edits.append((start, old, new))
            node.value = float(new)
    if len(edits) != (2 if trial_id == "cross_part" else 1):
        raise ValueError("R28 unauthorized edit count")
    candidate = original
    for start, old, new in edits:
        candidate = candidate[:start] + new + candidate[start+len(old):]
    after = ast.parse(candidate.decode("utf-8"))
    for prop, new in zip(PROPS, TOKENS[trial_id]):
        node = _node(after, prop, float(new))
        start, end = _span(candidate, node)
        if candidate[start:end] != new:
            raise ValueError("R28 candidate token mismatch")
    if ast.dump(before) != ast.dump(after):
        raise ValueError("R28 candidate AST mismatch")
    return candidate, tuple(edits)


def candidate_bytes(original, trial_id):
    return _derive(original, trial_id)[0]


def inverse_bytes(candidate, original, trial_id):
    expected, edits = _derive(original, trial_id)
    if type(candidate) is not bytes or candidate != expected:
        raise ValueError("R28 candidate differs from permitted bytes")
    restored = candidate
    for start, old, new in reversed(edits):
        restored = restored[:start] + old + restored[start+len(new):]
    if restored != original or sha(restored) != SOURCE_SHA256:
        raise ValueError("R28 inverse mismatch")
    return restored


class TrialCopy(FixedCopy):
    """Reuse R27 verified read, apply and failure recovery; fixed trial only."""
    def __init__(self, directory, original, trial_id):
        self.trial_id = trial_id
        self.path = directory / COPY_NAME
        self.original = original
        self.candidate = candidate_bytes(original, trial_id)
        with self.path.open("xb") as stream:
            stream.write(original)

    def restore(self):
        self._write(inverse_bytes(self.read_verified("candidate"), self.original, self.trial_id))
        self.read_verified("restored")


@contextmanager
def isolated_trial(directory, trial_id):
    original = SOURCE.read_bytes()
    candidate_bytes(original, trial_id)
    directory.mkdir(exist_ok=False)
    tx = TrialCopy(directory, original, trial_id)
    try:
        yield tx
    finally:
        tx.recover()
        if SOURCE.read_bytes() != original:
            raise AssertionError("R28 original source changed")
