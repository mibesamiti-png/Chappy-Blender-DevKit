"""Public native tests. Real CJM chain requires explicit local-only provider args."""
import argparse
import copy
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import bpy
from parts.blender import joint_preview as ui

p=argparse.ArgumentParser();p.add_argument('--cjm-zip');p.add_argument('--gl-root');p.add_argument('--output',required=True)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
rows=[]


def record(name,fun):
    start=time.perf_counter();fun()
    rows.append(dict(case=name,status='passed',seconds=time.perf_counter()-start))
    print('CBDK_A_CASE '+name,flush=True)


ui.register();s=bpy.context.scene.cbdk_a_joint


def op(action):
    if action in ('ADOPT', 'RESTORE'):
        return bpy.ops.cbdk_a.joint_dimension(action=action)
    return bpy.ops.cbdk_a.joint_action(action=action)
origin=ui.scene_signature(bpy.context)


def refusal():
    assert bpy.ops.cbdk_a.joint_action(action='RUN')=={'CANCELLED'}
    assert s.status=='FAILED' and ui.scene_signature(bpy.context)==origin
record('missing_provider_refused',refusal)


class Layout:
    def label(self,**kwargs): pass
    def prop(self,*args,**kwargs): pass
    def operator(self,*args,**kwargs):
        from types import SimpleNamespace
        return SimpleNamespace()


def draw():
    from types import SimpleNamespace
    ui.CBDK_A_PT_joint.draw(SimpleNamespace(layout=Layout()),bpy.context)
record('panel_draw',draw)

def sticky_block():
    s.status='BLOCKED'
    for action in ('RUN','RETRY','RESTORE','ADOPT'):
        assert op(action)=={'CANCELLED'}
        assert s.status=='BLOCKED'
    s.status='IDLE'
record('blocked_state_cannot_be_cleared_by_actions',sticky_block)

def registration_and_busy():
    try:ui.register();raise AssertionError('duplicate registration accepted')
    except RuntimeError as e:assert str(e)=='foreign_scene_property'
    s.status='RUNNING'
    old_diameter=s.diameter
    s.restore_diameter=4.
    for action in ('RUN','RETRY','ADOPT','REJECT','RESTORE'):
        assert op(action)=={'CANCELLED'}
        assert s.status=='RUNNING' and not s.cancel_requested
        assert s.diameter==old_diameter
    assert bpy.ops.cbdk_a.joint_action(action='CANCEL')=={'FINISHED'}
    assert s.cancel_requested and s.status=='RUNNING'
    for action in ('RUN','RETRY','ADOPT','REJECT','RESTORE'):
        assert op(action)=={'CANCELLED'}
    # Real RNA and action operator; controlled timer boundary, not GUI clicks.
    from types import SimpleNamespace as NS
    timer=object(); removed=[]
    operator=NS(_scene=bpy.context.scene,_timer=timer,_steps=ui.iter_run(bpy.context,s),_epoch=ui.HISTORY_EPOCH)
    context=NS(scene=bpy.context.scene,window_manager=NS(event_timer_remove=removed.append),area=None)
    assert ui.CBDK_A_OT_start.modal(operator,context,NS(type='TIMER'))=={'CANCELLED'}
    assert removed==[timer] and s.status=='CANCELLED'
    assert op('RESTORE')=={'FINISHED'}
    assert s.diameter==4.
    s.diameter=old_diameter;s.restore_diameter=old_diameter
    s.cancel_requested=False;s.status='IDLE'
record('duplicate_registration_and_cancel_timer_boundary',registration_and_busy)


def cached_provider_paths():
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as d:
        root=Path(d).resolve()
        z=root/'original.zip';g=root/'geometry'
        sentinel=object()
        old=ui.PROVIDERS,ui.PROVIDER_PATHS
        try:
            ui.PROVIDERS=sentinel;ui.PROVIDER_PATHS=(z,g)
            ui.configure(z,g)
            for a,b in ((root/'changed.zip',g),(z,root/'changed-geometry')):
                try:ui.configure(a,b);raise AssertionError('changed path accepted')
                except ValueError as e:assert str(e)=='provider_paths_changed_restart_required'
                assert ui.PROVIDERS is sentinel and ui.PROVIDER_PATHS==(z,g)
        finally:
            ui.PROVIDERS,ui.PROVIDER_PATHS=old
record('cached_provider_path_change_refused',cached_provider_paths)

def history_boundary():
    # Direct callback boundary test, not actual native Undo/Redo or GUI input.
    from types import SimpleNamespace as NS
    assert 'UNDO' in ui.CBDK_A_OT_dimension.bl_options
    assert 'UNDO' not in ui.CBDK_A_OT_action.bl_options
    assert 'UNDO' not in ui.CBDK_A_OT_start.bl_options
    for name, callback in ui.HISTORY_HANDLERS:
        assert getattr(bpy.app.handlers, name).count(callback) == 1
    old_diameter = s.diameter
    epoch = ui.HISTORY_EPOCH
    timer = object(); removed = []
    s.status = 'READY'; s.result_json = 'stale'
    ui.RUNS[bpy.context.scene.as_pointer()] = {'stale': True}
    ui.history_before(); ui.history_after()
    assert ui.HISTORY_EPOCH == epoch + 1 and not ui.RUNS
    assert s.status == 'FAILED' and s.reason == 'history_changed_rerun_required'
    assert s.result_json == '' and s.diameter == old_diameter
    assert op('ADOPT') == {'CANCELLED'} and s.diameter == old_diameter
    # Stale modal must stop without accessing invalidated RNA scene.
    operator = NS(_epoch=epoch, _timer=timer)
    context = NS(window_manager=NS(event_timer_remove=removed.append))
    assert ui.CBDK_A_OT_start.modal(operator, context, NS(type='TIMER')) == {'CANCELLED'}
    assert removed == [timer]
    # Simulate RNA restoring an earlier state; the session latch wins.
    old_latch = ui.HISTORY_BLOCKED
    try:
        s.status = 'BLOCKED'; ui.history_before()
        s.status = 'IDLE'; ui.history_after()
        assert s.status == 'BLOCKED' and op('RESTORE') == {'CANCELLED'}
    finally:
        ui.HISTORY_BLOCKED = old_latch
        s.status = 'IDLE'; s.reason = ''
    assert ui.scene_signature(bpy.context) == origin
record('history_callback_boundary_and_separate_dimension_operator', history_boundary)

if args.cjm_zip and args.gl_root:
    s.provider_zip=str(Path(args.cjm_zip).resolve())
    s.geometry_root=str(Path(args.gl_root).resolve())
    ui.configure(s.provider_zip,s.geometry_root)
    assert ui.corrected(3.,'FREE')>3.5
    try:ui.corrected(3.,'LOCKED');raise AssertionError('locked conflict accepted')
    except ValueError:pass
    rows.append(dict(case='numeric_correction_and_lock_conflict',status='passed'))
    start=time.perf_counter();payload=ui.run(bpy.context,s)
    assert [r['review']['decision'] for r in payload['rows']]==['regression','observed_improvement','target_reached']
    assert ui.scene_signature(bpy.context)==origin
    rows.append(dict(case='actual_cjm_gl_cbdk_chain',status='passed',seconds=time.perf_counter()-start,
                     measurements=payload['rows'],baseline=payload['baseline']))
    s.candidate=payload['best']
    original_zip=s.provider_zip
    s.provider_zip=original_zip+'.changed'
    assert op('ADOPT')=={'CANCELLED'}
    assert s.diameter==5. and s.status=='FAILED'
    s.provider_zip=original_zip
    payload=ui.run(bpy.context,s);s.candidate=payload['best']
    assert op('ADOPT')=={'FINISHED'}
    assert s.status=='ADOPTED_DIMENSION_ONLY' and s.diameter==4.
    assert op('RESTORE')=={'FINISHED'}
    assert s.diameter==5.
    rows.append(dict(case='native_adopt_and_restore',status='passed'))
    steps=ui.iter_run(bpy.context,s)
    s.cancel_requested=True
    try:next(steps);raise AssertionError('early cancellation ignored')
    except InterruptedError:pass
    s.cancel_requested=False
    steps=ui.iter_run(bpy.context,s)
    assert next(steps)=='baseline_measured'
    s.cancel_requested=True
    try:next(steps);raise AssertionError('between-trial cancellation ignored')
    except InterruptedError:pass
    s.cancel_requested=False;s.status='IDLE'
    assert ui.scene_signature(bpy.context)==origin
    rows.append(dict(case='native_early_and_between_trial_cancel',status='passed'))
    from cbdk.joint_integration import verified_write
    try:
        verified_write(lambda:float(s.diameter),lambda v:setattr(s,'diameter',v),5.,4.0000001,lambda:None)
        raise AssertionError('native RNA rounding accepted')
    except RuntimeError as e:assert str(e)=='rna_readback_mismatch'
    assert s.diameter==5.
    rows.append(dict(case='native_float32_rounding_restored',status='passed'))
    for fault in ('generation','boolean','interrupt','cleanup'):
        try:ui.trial(bpy.context,4.,fault=fault);raise AssertionError('fault accepted')
        except (RuntimeError,InterruptedError):pass
        assert ui.scene_signature(bpy.context)==origin
        rows.append(dict(case='injected_'+fault,status='passed'))
    for label,kw in [('pair_budget',dict(pair_budget=1)),('time_budget',dict(seconds=1e-100))]:
        try:ui.trial(bpy.context,4.,**kw);raise AssertionError('budget accepted')
        except RuntimeError as e:assert str(e)=='gl_unknown_or_intersecting'
        assert ui.scene_signature(bpy.context)==origin
        rows.append(dict(case=label,status='passed'))
    saved=ui.trial
    def fail(*a,**kw):raise RuntimeError('cleanup_or_source_changed')
    ui.trial=fail
    assert bpy.ops.cbdk_a.joint_action(action='RUN')=={'CANCELLED'} and s.status=='BLOCKED'
    assert bpy.ops.cbdk_a.joint_action(action='RETRY')=={'CANCELLED'} and s.status=='BLOCKED'
    ui.trial=saved
    rows.append(dict(case='cleanup_failure_blocks_retry',status='passed'))
else:
    rows.append(dict(case='actual_cjm_gl_cbdk_chain',status='not_run',reason='private_local_provider_not_in_ci'))

ui.unregister()
assert not hasattr(bpy.types.Scene,'cbdk_a_joint')
assert all(callback not in getattr(bpy.app.handlers, name) for name, callback in ui.HISTORY_HANDLERS)
result=dict(blender=bpy.app.version_string,rows=rows,gui_mouse_keyboard=False,
            continuous_collision=False,printing=False,approved=False)
out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print('CBDK_A_NATIVE_PASS '+json.dumps(dict(blender=result['blender'],cases=len(rows))),flush=True)
