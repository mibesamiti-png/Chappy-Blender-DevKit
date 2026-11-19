"""Exercise Blender's *native legacy add-on enable* path (not direct register()).

This reproduces the Preferences > Add-ons route where Blender 4.2.4 used to
raise tuple.__format__ when bl_info['blender'] exceeded bpy.app.version.
Synthetic, non-private developer-authored add-on only.
"""
import importlib
import pathlib
import shutil
import sys

import bpy
import addon_utils

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
assert len(args) == 1, "Pass a single addon source .py path"
source = pathlib.Path(args[0]).resolve()
assert source.is_file(), source
# Run on a fresh factory-startup session and isolate the copied source by name.
module = "Chappy_Dual_Reflector_Maker"
destination = pathlib.Path(bpy.utils.user_resource("SCRIPTS", path="addons", create=True))
destination.mkdir(parents=True, exist_ok=True)
target = destination / (module + ".py")
shutil.copy2(source, target)
addon_utils.modules_refresh()
assert module not in bpy.context.preferences.addons
result = bpy.ops.preferences.addon_enable(module=module)
assert result == {"FINISHED"}, result
assert module in bpy.context.preferences.addons
addon = importlib.import_module(module)
assert tuple(addon.bl_info["blender"]) <= tuple(bpy.app.version)
assert hasattr(bpy.types.Scene, "chappy_dual_reflector")
assert bpy.ops.chappy.build_dual_reflector() == {"FINISHED"}, bpy.app.version_string
result = bpy.ops.preferences.addon_disable(module=module)
assert result == {"FINISHED"}, result
assert module not in bpy.context.preferences.addons
assert not hasattr(bpy.types.Scene, "chappy_dual_reflector")
print("CBDK_DUAL_REFLECTOR_NATIVE_ENABLE_PASS " + bpy.app.version_string)
