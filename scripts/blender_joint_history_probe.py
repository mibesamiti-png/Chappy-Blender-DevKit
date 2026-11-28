"""Isolated native Blender history experiment, not a GUI or release gate.

One explicit baseline push initializes history in the factory-startup process.
No manual push after ADOPT; actual ed.undo/redo must traverse the operator's
history. A background limitation or failed assertion stays explicit in JSON.
"""
import argparse
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bpy
from parts.blender import joint_preview as ui

p = argparse.ArgumentParser()
p.add_argument('--cjm-zip', required=True)
p.add_argument('--gl-root', required=True)
p.add_argument('--output', required=True)
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
assert bpy.app.background, 'fresh background Blender only'


def semantic_source():
    # History may replace RNA pointers even when actual content is unchanged.
    c = bpy.context
    objects = []
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        mesh = None
        if o.type == 'MESH':
            mesh = dict(vertices=[list(v.co) for v in o.data.vertices],
                        edges=[list(e.vertices) for e in o.data.edges],
                        polygons=[list(f.vertices) for f in o.data.polygons])
        objects.append(dict(name=o.name, type=o.type,
                            matrix=[list(row) for row in o.matrix_world],
                            data=o.data.name if o.data else None,
                            mesh=mesh))
    return dict(objects=objects, meshes=sorted(m.name for m in bpy.data.meshes),
                collections=sorted(x.name for x in bpy.data.collections),
                selected=sorted(o.name for o in c.selected_objects),
                active=c.view_layer.objects.active.name if c.view_layer.objects.active else None,
                mode=c.mode, cursor=list(c.scene.cursor.location),
                unit_system=c.scene.unit_settings.system,
                unit_scale=c.scene.unit_settings.scale_length)


def settings():
    return bpy.context.scene.cbdk_a_joint


report = dict(blender=bpy.app.version_string, background=True, gui_mouse_keyboard=False,
              explicit_baseline_push=True, explicit_post_adopt_push=False,
              approved=False, status='failed', stage='setup', rows=[])
try:
    bpy.context.preferences.edit.use_global_undo = True
    ui.register()
    s = settings()
    s.provider_zip = str(Path(args.cjm_zip).resolve())
    s.geometry_root = str(Path(args.gl_root).resolve())
    ui.configure(s.provider_zip, s.geometry_root)
    original = semantic_source()
    report['stage'] = 'generate'
    payload = ui.run(bpy.context, s)
    assert s.status == 'READY' and payload['best'] is not None
    s.candidate = payload['best']
    assert s.diameter == 5. and semantic_source() == original
    report['stage'] = 'baseline_push'
    if not bpy.ops.ed.undo_push.poll():
        report['status'] = 'unavailable'
        raise RuntimeError('background_baseline_push_poll_false')
    assert bpy.ops.ed.undo_push(message='CBDK synthetic baseline') == {'FINISHED'}
    report['rows'].append(dict(case='baseline_push', diameter=5.))
    report['stage'] = 'adopt'
    assert bpy.ops.cbdk_a.joint_dimension(action='ADOPT') == {'FINISHED'}
    assert settings().diameter == 4. and semantic_source() == original
    report['rows'].append(dict(case='operator_adopt', diameter=4.))
    report['stage'] = 'native_undo'
    if not bpy.ops.ed.undo.poll():
        report['status'] = 'unavailable'
        raise RuntimeError('background_undo_poll_false')
    epoch = ui.HISTORY_EPOCH
    assert bpy.ops.ed.undo() == {'FINISHED'}
    assert settings().diameter == 5. and semantic_source() == original
    assert not ui.RUNS and ui.HISTORY_EPOCH > epoch
    assert settings().status != 'READY'
    report['rows'].append(dict(case='native_undo', diameter=5., stale_candidates=False))
    report['stage'] = 'native_redo'
    if not bpy.ops.ed.redo.poll():
        report['status'] = 'unavailable'
        raise RuntimeError('background_redo_poll_false')
    epoch = ui.HISTORY_EPOCH
    assert bpy.ops.ed.redo() == {'FINISHED'}
    assert settings().diameter == 4. and semantic_source() == original
    assert not ui.RUNS and ui.HISTORY_EPOCH > epoch
    report['rows'].append(dict(case='native_redo', diameter=4., stale_candidates=False))
    report['stage'] = 'stale_adopt_refusal'
    assert bpy.ops.cbdk_a.joint_dimension(action='ADOPT') == {'CANCELLED'}
    assert settings().diameter == 4. and semantic_source() == original
    report['rows'].append(dict(case='stale_adopt_refusal', diameter=4.))
    report['stage'] = 'complete'
    report['status'] = 'passed'
except Exception as error:
    report['error'] = type(error).__name__ + ': ' + str(error)
    traceback.print_exc()
finally:
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print('CBDK_A_NATIVE_HISTORY_PROBE ' + json.dumps(report), flush=True)
# The experiment is not a release gate: failed/unavailable are evidence, not
# passes. A crash or missing report still fails the workflow infrastructure.
