"""Fixed internal R25 C native experiment; reuse A's existing verifier.

Observe the registered grouped Extension immediately before the verifier's
real disable. No independent installer, no caller-selected artifact or code.
The test adapter is not an integration API; A calls probe_registered_fixture
directly in its own same-artifact integration.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
from blender_undo_redo_smoke import probe_registered_fixture
from cbdk.extension_authored_fixture import FIXTURE_ID
from cbdk.undo_probe_report import R25_PREFIX, validate_grouped_observation
from verify_recipe_extension_runtime import verify


def scene_snapshot():
    # Existing read/edit fixture must not change across our probe.
    return {
        obj.name: (tuple(tuple(v.co) for v in obj.data.vertices),
                   tuple(tuple(e.vertices) for e in obj.data.edges),
                   tuple(tuple(p.vertices) for p in obj.data.polygons),
                   tuple(v.select for v in obj.data.vertices),
                   tuple(e.select for e in obj.data.edges),
                   tuple(p.select for p in obj.data.polygons),
                   tuple(obj.location), obj.select_get())
        for obj in bpy.context.scene.objects if obj.type == "MESH"
    }


def run():
    if os.environ.get("CBDK_R23_CASE") != "grouped" or not bpy.app.background or bpy.app.online_access:
        raise AssertionError("R25 requires fixed isolated grouped test")
    root = Path(os.environ["CBDK_R19_TEMP"]).resolve()
    archive = root / "authored.zip"
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    real_disable = addon_utils.disable
    observations = []

    def observed_disable(namespace, *args, **kwargs):
        if namespace.startswith("bl_ext.") and namespace.endswith("." + FIXTURE_ID):
            try:
                module = sys.modules[namespace]
                if (observations or not addon_utils.check(namespace)[1]
                        or set(module._FEATURE_IDS) != {"mesh_bounds", "mesh_center", "edit_selection", "vertex_nudge"}
                        or len(module._PANEL_CLASSES) != 2
                        or any(not cls.is_registered for cls in module._CLASSES)):
                    raise AssertionError("R25 grouped Extension not registered")
                before = scene_snapshot()
                report = probe_registered_fixture(module)
                if scene_snapshot() != before:
                    raise AssertionError("R25 Undo probe altered earlier fixture geometry")
                observations.append(report)
            finally:
                real_disable(namespace, *args, **kwargs)
        else:
            return real_disable(namespace, *args, **kwargs)

    with patch.object(addon_utils, "disable", observed_disable):
        verify()
    # verify() already independently checks class/RNA/addon cleanup.
    if len(observations) != 1 or hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
        raise AssertionError("R25 grouped observation missing or input changed")
    result = validate_grouped_observation({
        "schema_version": 1, "case_id": "grouped",
        "blender_version": ".".join(map(str, bpy.app.version)), "artifact_sha256": digest,
        "undo_probe": observations[0], "registered_during_probe": True,
        "fixture_cleanup_verified": True, "extension_cleanup_verified": True,
        "input_sha_unchanged": True,
    })
    print(R25_PREFIX + json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    run()
