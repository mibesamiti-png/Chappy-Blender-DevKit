"""Build one CBDK-authored horizontal layout fixture without editing sources."""
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cbdk.modular_builder import build_modular


def build(output):
    with tempfile.TemporaryDirectory(prefix="cbdk-ui-variant-") as directory:
        root = Path(directory).resolve()
        for folder in ("catalog", "templates", "parts"):
            shutil.copytree(ROOT / folder, root / folder)
        path = root / "catalog/ui_layouts.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        # Exercise one genuinely mixed Object/Edit section in every Blender CI version.
        data["sections"][0].update(layout="row", boxed=False, visible_in="always")
        data["sections"][1]["visible_in"] = "edit_mesh"
        nudge = data["sections"][1]["controls"].pop()
        nudge["visible_in"] = "edit_mesh"
        data["sections"][0]["controls"].append(nudge)
        for control in data["sections"][0]["controls"]:
            if control["feature_id"] != "vertex_nudge":
                control["visible_in"] = "object"
        for section in data["sections"]:
            for control in section["controls"]:
                if control["feature_id"] == "vertex_nudge":
                    control["parameters"] = {"offset": {"default": [0.125, -0.25, 0.5],
                                                         "min": -1, "max": 1}}
        path.write_text(json.dumps(data), encoding="utf-8")
        recipe = json.loads((ROOT / "recipes/modular_all.json").read_text(encoding="utf-8"))
        build_modular(recipe, output, root=root, preview_unapproved=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise ValueError("Expected one fresh authored preview ZIP output")
    build(sys.argv[1])
