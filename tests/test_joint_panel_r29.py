"""Pure AST-boundary checks; native draw/operator tests run in Blender smoke."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "parts/blender/joint_panel_r29.py"


class JointPanelR29Tests(unittest.TestCase):
    def test_panel_only_and_existing_operator_bindings(self):
        tree = ast.parse(PANEL.read_text(encoding="utf-8"))
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        self.assertEqual([node.name for node in classes], ["CBDK_PT_joint_panel_r29"])
        self.assertEqual(ast.unparse(classes[0].bases[0]), "bpy.types.Panel")
        assign = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "OPERATOR_BINDINGS" for t in n.targets))
        bindings = ast.literal_eval(assign.value)
        self.assertEqual(set(bindings), {"START", "RETRY", "REJECT", "CANCEL", "ADOPT", "RESTORE"})
        self.assertEqual(bindings["START"], ("cbdk_a.joint_start", None, "INVOKE_DEFAULT"))
        self.assertEqual({v[0] for v in bindings.values()},
                         {"cbdk_a.joint_start", "cbdk_a.joint_action", "cbdk_a.joint_dimension"})
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                             and ast.unparse(n.func).startswith("bpy.ops.") for n in ast.walk(tree)))

    def test_presentation_gates(self):
        tree = ast.parse(PANEL.read_text(encoding="utf-8"))
        # Compile only the pure presentation function, no bpy import.
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "visible_actions")
        status = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "STATUSES" for t in n.targets))
        namespace = {"STATUSES": ast.literal_eval(status.value)}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(PANEL), "exec"), namespace)
        visible = namespace["visible_actions"]
        for avail in (False, True):
            for current in (False, True):
                for selected in (False, True):
                    kw = dict(available=avail, current=current, selected=selected, fixed_context=True)
                    self.assertEqual(visible("RUNNING", **kw), ("CANCEL",))
                    self.assertEqual(visible("BLOCKED", **kw), ())
                    self.assertEqual("ADOPT" in visible("READY", **kw), avail and current and selected)
                    self.assertNotIn("ADOPT", visible("FAILED", **kw))
                    self.assertNotIn("ADOPT", visible("CANCELLED", **kw))
        self.assertEqual(visible("unknown", available=True, current=True, selected=True, fixed_context=True), ())
