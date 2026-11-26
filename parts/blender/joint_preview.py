"""Opt-in artificial rotary preview. External CJM remains local, never bundled.

No existing object is edited. All generated geometry belongs to one disposable
collection. The panel's adoption changes its own dimension setting only.
"""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import zipfile

import bpy
from bpy.props import FloatProperty, EnumProperty, StringProperty, PointerProperty, IntProperty
from bpy.types import Operator, Panel, PropertyGroup
from cbdk.joint_integration import proposals, review, score, verified_write, checked_provider_folder

ZIP_SHA = '91700f02210e03940eee38f1939f6a7d9778ed9406f902e9359f73bf5f4a88c1'
PROVIDERS = None
PROVIDER_PATHS = None
TEMP = None
RUNS = {}
OWNED = False


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',',':')).encode()).hexdigest()


def configure(zip_path, gl_root):
    global PROVIDERS, PROVIDER_PATHS, TEMP
    zip_path, root = Path(zip_path).resolve(), Path(gl_root).resolve()
    requested = (zip_path, root)
    if PROVIDERS is not None:
        if requested != PROVIDER_PATHS:
            raise ValueError('provider_paths_changed_restart_required')
        return
    raw = zip_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ZIP_SHA: raise ValueError('local_provider_hash_mismatch')
    if 'chappy_joint_maker' in sys.modules: raise ValueError('external_provider_already_loaded')
    from experiments.team_a_staged.run_gl import verify
    verify(root)
    if 'cbdk_geometry' in sys.modules: raise ValueError('external_geometry_already_loaded')
    TEMP = tempfile.TemporaryDirectory(prefix='cbdk-a-local-')
    with zipfile.ZipFile(zip_path) as archive:
        if sum(x.file_size for x in archive.infolist()) > 20_000_000: raise ValueError('provider_size')
        folder = checked_provider_folder(TEMP.name, (x.filename for x in archive.infolist()))
        archive.extractall(folder)
    sys.path.insert(0,str(folder)); sys.path.insert(0,str(root))
    cjm = importlib.import_module('chappy_joint_maker')
    geometry = importlib.import_module('cbdk_geometry')
    detector = importlib.import_module('cbdk_geometry.accelerated')
    PROVIDERS = (cjm, geometry, detector)
    PROVIDER_PATHS = requested


def object_state(o):
    geometry = None
    if o.type == 'MESH':
        geometry = ([list(v.co) for v in o.data.vertices],
                    [list(e.vertices) for e in o.data.edges],
                    [list(p.vertices) for p in o.data.polygons])
    return (o.as_pointer(), tuple(x for row in o.matrix_world for x in row), digest(geometry))


def scene_signature(context):
    return digest([sorted(object_state(o) for o in bpy.data.objects),
                   sorted(x.as_pointer() for x in bpy.data.meshes),
                   sorted(x.as_pointer() for x in bpy.data.collections),
                   sorted(o.as_pointer() for o in context.selected_objects),
                   context.view_layer.objects.active.as_pointer() if context.view_layer.objects.active else None,
                   list(context.scene.cursor.location), context.mode,
                   context.scene.unit_settings.system, context.scene.unit_settings.scale_length])


def trial(context, diameter, *, pair_budget=200000, seconds=10, fault=None):
    if PROVIDERS is None: raise RuntimeError('local_providers_missing')
    if context.mode != 'OBJECT': raise ValueError('object_mode_required')
    if tuple(context.scene.cursor.location) != (0.,0.,0.): raise ValueError('synthetic_origin_required')
    if context.scene.unit_settings.scale_length != 1.: raise ValueError('synthetic_unit_scale_required')
    cjm, geometry, detector = PROVIDERS
    before = scene_signature(context)
    selected = list(context.selected_objects); active = context.view_layer.objects.active
    col = bpy.data.collections.new('CBDK_A_Trial')
    context.scene.collection.children.link(col)
    mesh = None
    try:
        if fault == 'generation': raise RuntimeError('injected_generation_failure')
        settings = NS(outer_diameter=diameter, axle_diameter=2., a_width=3.5,b_width=3.5,
                      radial_clearance=.4,axial_gap=.4,cap_wall=.8,radial_wall=.35,
                      tip_clearance=.4,shoulder_enabled=False,axis='Z',reverse_axis=False)
        old_boolean = cjm.ball_joint.boolean_apply
        if fault == 'boolean':
            def fail(*args, **kwargs): raise RuntimeError('injected_boolean_failure')
            cjm.ball_joint.boolean_apply = fail
        try:
            objects = cjm.common_tools.build_rotary(context,settings,col)
        finally:
            cjm.ball_joint.boolean_apply = old_boolean
        if fault == 'interrupt': raise InterruptedError('injected_interruption')
        dimensions, results, closed = [], [], True
        for o in objects:
            context.view_layer.update()
            # Fresh evaluated mesh, IDs retained per part. Do not weld or combine parts.
            ev = o.evaluated_get(context.evaluated_depsgraph_get()); mesh = ev.to_mesh()
            try:
                mesh.calc_loop_triangles()
                vertices = [list(o.matrix_world@v.co) for v in mesh.vertices]
                faces = [list(t.vertices) for t in mesh.loop_triangles]
                if len(faces) > 512: raise RuntimeError('face_budget_exceeded')
                detached = geometry.Mesh(vertices, faces)
                result = detector.detect_accelerated(detached,pair_budget=pair_budget,seconds=seconds)
                # Skip/timeout/missing pairs cannot certify a result.
                if result['status'] != 'measured' or result['pairs'] != []:
                    raise RuntimeError('gl_unknown_or_intersecting')
                results.append(result)
                dimensions.append([max(v[k] for v in vertices)-min(v[k] for v in vertices) for k in range(3)])
                closed &= cjm.hinge_maker.face_hinge._closed_mesh_volume(mesh) is not None
            finally:
                ev.to_mesh_clear(); mesh = None
        measurement = dict(dimensions=dimensions, protected_sha=before,gl=results,closed=bool(closed))
    finally:
        for o in list(col.objects):
            data = o.data if o.type == 'MESH' else None
            bpy.data.objects.remove(o,do_unlink=True)
            if data is not None and data.users == 0: bpy.data.meshes.remove(data)
        bpy.data.collections.remove(col)
        for o in list(context.selected_objects): o.select_set(False)
        for o in selected: o.select_set(True)
        context.view_layer.objects.active = active
        if fault == 'cleanup' or scene_signature(context) != before:
            raise RuntimeError('cleanup_or_source_changed')
    return measurement


def corrected(diameter, policy):
    if PROVIDERS is None: raise RuntimeError('local_providers_missing')
    cm = PROVIDERS[0].constraints.cm
    values = dict(outer_diameter=diameter, axle_diameter=2., a_width=3.5,b_width=3.5,
                  radial_clearance=.4,axial_gap=.4,cap_wall=.8,radial_wall=.35,tip_clearance=.4)
    bounds = {'outer_diameter':(.1,20.),'axle_diameter':(.1,20.)}
    result = cm.repair('rotary',values,{'shoulder':False},bounds,
                       locked=('axle_diameter',) + (('outer_diameter',) if policy=='LOCKED' else ()),
                       preferred=('outer_diameter',) if policy=='PREFERRED' else ())
    if not result.ok: raise ValueError('numeric_constraints_unsatisfied')
    return float(result.values['outer_diameter'])


def iter_run(context, settings):
    if settings.status == 'BLOCKED': raise RuntimeError('restoration_blocked')
    original = float(settings.diameter)
    target, policy = float(settings.target), settings.policy
    settings.status = 'RUNNING'
    if settings.cancel_requested: raise InterruptedError('cancelled_between_trials')
    baseline = trial(context, corrected(original,settings.policy))
    best_score = score(baseline,target); best = None; rows = []
    yield 'baseline_measured'
    for name, proposal in proposals(original,target,policy):
        if settings.cancel_requested: raise InterruptedError('cancelled_between_trials')
        if (float(settings.diameter),float(settings.target),settings.policy)!=(original,target,policy):
            raise ValueError('stale_inputs')
        diameter = corrected(proposal,settings.policy)
        measured = trial(context,diameter)
        result = review(baseline,measured,target,best_score)
        rows.append(dict(id=name,diameter=diameter,measurement=measured,review=result))
        if result['accepted_for_review']:
            best_score = result['score']; best = len(rows)-1
        settings.result_json=json.dumps(dict(rows=rows,status='incomplete'))
        yield name
        if result['decision']=='target_reached': break
    if settings.cancel_requested: raise InterruptedError('cancelled_between_trials')
    payload = dict(original=original,target=target,policy=policy,
                   signature=scene_signature(context),baseline=baseline,rows=rows,best=best)
    RUNS[context.scene.as_pointer()] = payload
    settings.result_json = json.dumps(payload)
    settings.status = 'READY' if best is not None else 'NO_CANDIDATE'


def run(context, settings):
    settings.cancel_requested=False
    for stage in iter_run(context,settings): pass
    return RUNS[context.scene.as_pointer()]


class CBDK_A_Settings(PropertyGroup):
    provider_zip: StringProperty(name='ローカルCJM ZIP',subtype='FILE_PATH')
    geometry_root: StringProperty(name='凍結GLフォルダー',subtype='DIR_PATH')
    diameter: FloatProperty(name='外径 内部座標単位',default=5.,min=3.6,max=10.)
    target: FloatProperty(name='比較目標外径',default=4.,min=3.6,max=10.)
    policy: EnumProperty(name='外径の補正方針',items=[(x,x,'') for x in ('FREE','PREFERRED','LOCKED')])
    status: StringProperty(default='IDLE')
    reason: StringProperty()
    result_json: StringProperty()
    candidate: IntProperty(name='候補行',default=0,min=0,max=2)
    restore_diameter: FloatProperty(default=5.)
    cancel_requested: bpy.props.BoolProperty(default=False)


class CBDK_A_OT_start(Operator):
    bl_idname='cbdk_a.joint_start'
    bl_label='人工関節の検証開始'
    _timer=None
    _steps=None
    _scene=None

    def invoke(self, context, event):
        s=context.scene.cbdk_a_joint
        if s.status in ('BLOCKED','RUNNING'): return {'CANCELLED'}
        try:
            configure(bpy.path.abspath(s.provider_zip),bpy.path.abspath(s.geometry_root))
            s.restore_diameter=s.diameter
            s.cancel_requested=False;s.status='RUNNING'
            self._scene=context.scene
            RUNS.pop(context.scene.as_pointer(),None)
            self._steps=iter_run(context,s)
            self._timer=context.window_manager.event_timer_add(.1,window=context.window)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        except Exception:
            s.status='FAILED';s.reason='provider_configuration_failed';return {'CANCELLED'}

    def modal(self, context, event):
        s=self._scene.cbdk_a_joint
        if context.scene!=self._scene:
            context.window_manager.event_timer_remove(self._timer)
            RUNS.pop(self._scene.as_pointer(),None)
            s.status='FAILED';s.reason='context_scene_changed'
            return {'CANCELLED'}
        if event.type=='ESC': s.cancel_requested=True
        if event.type!='TIMER': return {'PASS_THROUGH'}
        try:
            next(self._steps)
            if context.area: context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        except StopIteration:
            context.window_manager.event_timer_remove(self._timer)
            return {'FINISHED'}
        except Exception as error:
            context.window_manager.event_timer_remove(self._timer)
            reason=str(error)
            s.reason=reason if reason.isascii() and len(reason)<80 and '/' not in reason and '\\' not in reason else 'provider_or_geometry_failure'
            s.status=('BLOCKED' if any(x in reason for x in ('cleanup','rollback','source_changed'))
                      else 'CANCELLED' if isinstance(error,InterruptedError) else 'FAILED')
            RUNS.pop(context.scene.as_pointer(),None)
            return {'CANCELLED'}


class CBDK_A_OT_action(Operator):
    bl_idname = 'cbdk_a.joint_action'
    bl_label = '人工関節の限定検証'
    action: EnumProperty(items=[(x,x,'') for x in ('RUN','ADOPT','REJECT','CANCEL','RESTORE','RETRY')])

    def execute(self, context):
        s = context.scene.cbdk_a_joint
        if s.status=='RUNNING':
            if self.action == 'CANCEL':
                s.cancel_requested=True
                RUNS.pop(context.scene.as_pointer(),None)
                s.reason='cancellation_requested'
                return {'FINISHED'}
            return {'CANCELLED'}
        try:
            if s.status == 'BLOCKED': raise RuntimeError('restoration_blocked')
            if self.action in ('RUN','RETRY'):
                configure(bpy.path.abspath(s.provider_zip),bpy.path.abspath(s.geometry_root))
                s.restore_diameter = s.diameter
                run(context,s)
            elif self.action == 'ADOPT':
                p = RUNS.get(context.scene.as_pointer())
                if not p or s.status != 'READY': raise ValueError('no_current_candidate')
                configure(bpy.path.abspath(s.provider_zip),bpy.path.abspath(s.geometry_root))
                if (s.diameter,s.target,s.policy,scene_signature(context)) != (p['original'],p['target'],p['policy'],p['signature']):
                    raise ValueError('stale_inputs')
                row = p['rows'][s.candidate]
                if not row['review']['accepted_for_review']: raise ValueError('rejected_candidate')
                measured = trial(context,row['diameter'])
                if measured != row['measurement']: raise ValueError('fresh_measurement_changed')
                original = float(s.diameter)
                verified_write(lambda:float(s.diameter),lambda x:setattr(s,'diameter',x),
                               original,row['diameter'],lambda:None)
                s.status = 'ADOPTED_DIMENSION_ONLY'
            elif self.action == 'RESTORE':
                original = float(s.diameter)
                verified_write(lambda:float(s.diameter),lambda x:setattr(s,'diameter',x),
                               original,float(s.restore_diameter),lambda:None)
                s.status = 'RESTORED'
                RUNS.pop(context.scene.as_pointer(),None)
            else:
                s.cancel_requested=True
                RUNS.pop(context.scene.as_pointer(),None)
                s.status = 'CANCELLED' if self.action=='CANCEL' else 'REJECTED'
            s.reason = ''
            return {'FINISHED'}
        except Exception as error:
            reason = str(error)
            s.reason = reason if reason.isascii() and len(reason)<80 and '/' not in reason and '\\' not in reason else 'provider_or_geometry_failure'
            s.status = 'BLOCKED' if s.status == 'BLOCKED' or any(x in reason for x in ('rollback','cleanup','source_changed','restoration_blocked')) else 'FAILED'
            return {'CANCELLED'}


class CBDK_A_PT_joint(Panel):
    bl_label = 'CBDK A 統合候補 人工回転関節'
    bl_idname = 'CBDK_A_PT_joint'
    bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = 'CBDK'
    def draw(self, context):
        s = context.scene.cbdk_a_joint; layout = self.layout
        layout.label(text='合成単体関節専用 製品採用未承認')
        for key in ('provider_zip','geometry_root','diameter','target','policy'): layout.prop(s,key)
        layout.label(text='軸Z 原点 単位scale=1 軸径2 隙間0.4固定')
        layout.operator('cbdk_a.joint_start',text='候補生成と形状検査 または再試行')
        p = RUNS.get(context.scene.as_pointer())
        if p:
            for i,row in enumerate(p['rows']):
                layout.label(text=f"{i}: {row['diameter']:.4f} / {row['review']['decision']} / {row['review']['score']:.5f}")
            layout.prop(s,'candidate')
        for text,action in [('寸法だけ採用','ADOPT'),('拒否','REJECT'),('中断 後続工程停止','CANCEL'),('元の寸法へ復元','RESTORE')]:
            layout.operator('cbdk_a.joint_action',text=text).action = action
        layout.label(text=s.status)
        if s.reason: layout.label(text=s.reason,icon='ERROR')
        layout.label(text='中断とEscは候補の境界で停止 検査中は待機')


CLASSES = (CBDK_A_Settings,CBDK_A_OT_action,CBDK_A_OT_start,CBDK_A_PT_joint)


def register():
    global OWNED
    if hasattr(bpy.types.Scene,'cbdk_a_joint'): raise RuntimeError('foreign_scene_property')
    done = []
    try:
        for cls in CLASSES: bpy.utils.register_class(cls); done.append(cls)
        bpy.types.Scene.cbdk_a_joint = PointerProperty(type=CBDK_A_Settings)
        OWNED=True
    except Exception:
        for cls in reversed(done): bpy.utils.unregister_class(cls)
        raise


def unregister():
    global OWNED
    if not OWNED: raise RuntimeError('registration_not_owned')
    prop=bpy.types.Scene.bl_rna.properties.get('cbdk_a_joint')
    if prop is None or prop.fixed_type != CBDK_A_Settings.bl_rna:
        raise RuntimeError('foreign_scene_property')
    if hasattr(bpy.types.Scene,'cbdk_a_joint'): del bpy.types.Scene.cbdk_a_joint
    for cls in reversed(CLASSES): bpy.utils.unregister_class(cls)
    RUNS.clear()
    OWNED=False
