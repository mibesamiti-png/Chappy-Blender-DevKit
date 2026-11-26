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
        assert bpy.ops.cbdk_a.joint_action(action=action)=={'CANCELLED'}
        assert s.status=='BLOCKED'
    s.status='IDLE'
record('blocked_state_cannot_be_cleared_by_actions',sticky_block)

def registration_and_busy():
    try:ui.register();raise AssertionError('duplicate registration accepted')
    except RuntimeError as e:assert str(e)=='foreign_scene_property'
    s.status='RUNNING'
    for action in ('RUN','RETRY','ADOPT'):
        assert bpy.ops.cbdk_a.joint_action(action=action)=={'CANCELLED'}
        assert s.status=='RUNNING'
    assert bpy.ops.cbdk_a.joint_action(action='RESTORE')=={'FINISHED'}
    assert s.cancel_requested
    s.cancel_requested=False;s.status='IDLE'
record('duplicate_registration_busy_and_restore_stop',registration_and_busy)

if args.cjm_zip and args.gl_root:
    ui.configure(args.cjm_zip,args.gl_root)
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
    assert bpy.ops.cbdk_a.joint_action(action='ADOPT')=={'FINISHED'}
    assert s.status=='ADOPTED_DIMENSION_ONLY' and s.diameter==4.
    assert bpy.ops.cbdk_a.joint_action(action='RESTORE')=={'FINISHED'}
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
result=dict(blender=bpy.app.version_string,rows=rows,gui_mouse_keyboard=False,
            continuous_collision=False,printing=False,approved=False)
out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print('CBDK_A_NATIVE_PASS '+json.dumps(dict(blender=result['blender'],cases=len(rows))),flush=True)
