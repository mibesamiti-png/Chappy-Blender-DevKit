"""Phase115: frozen retrospective visual comparison; no adoption gate."""
import json, hashlib, math
from pathlib import Path
import bpy, bmesh
from mathutils import Vector
from collections import Counter

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'/'visual'
OUT.mkdir(parents=True,exist_ok=True)
fixtures=json.loads((ROOT/'phase111_fixtures.json').read_text())['cases']
raw=json.loads((ROOT/'results'/'native.json').read_text())
widths={'single':.25,'double':.25,'four':.25,'rectangular':.25,'shallow':.25,'deep':.25,'flat_dense':.25,'flat_rect':.5,'flat_narrow':.25,'holdout_tall':.5,'holdout_wide':.9,'holdout_corner':.5}
assert raw['complete'] and raw['blender_version']=='4.4.3'
rows={x['name']:x for x in raw['rows']}
assert set(rows)==set(widths)=={x['name'] for x in fixtures}
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=16
scene.cycles.use_denoising=False
scene.cycles.seed=115
scene.render.resolution_x=384
scene.render.resolution_y=384
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGB'
scene.render.film_transparent=False
scene.render.threads_mode='FIXED'
scene.render.threads=4
scene.view_settings.view_transform='Standard'
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.22,.22,.22,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
mat=bpy.data.materials.new('Neutral clay')
mat.use_nodes=True
bsdf=mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value=(.48,.52,.58,1)
bsdf.inputs['Roughness'].default_value=.38
camera=bpy.data.objects.new('Comparison camera',bpy.data.cameras.new('Comparison camera'))
scene.collection.objects.link(camera)
scene.camera=camera
camera.data.type='ORTHO'
def aim(obj,target):
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
lights=[]
for name,power,size in [('key',450,3),('fill',200,4),('rim',300,2)]:
    data=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj);lights.append((obj,power,size))
def mesh_for(case,config):
    src=case['custom'] if config is None else case['sharp']
    m=bpy.data.meshes.new('candidate')
    m.from_pydata(src['vertices'],[],src['faces']);m.update()
    if config is not None:
        bm=bmesh.new()
        try:
            bm.from_mesh(m);bm.verts.ensure_lookup_table();bm.verts.index_update()
            ids={tuple(sorted(e)) for e in src['edges']}
            geom=[e for e in bm.edges if tuple(sorted(v.index for v in e.verts)) in ids]
            assert len(geom)==len(ids)
            bmesh.ops.bevel(bm,geom=geom,offset=config['offset'],offset_type='OFFSET',segments=config['segments'],profile=config['profile'],affect='EDGES',clamp_overlap=True,loop_slide=True,miter_outer='SHARP',miter_inner='SHARP')
            bm.normal_update();bm.to_mesh(m);m.update()
        finally:bm.free()
    return m
def mean(v):
    return sum(v,Vector((0,0,0)))/len(v)
manifest=[]
for case in fixtures:
    name=case['name'];row=rows[name]
    good=[a for a in row['candidates'] if a['screened']]
    best=min(good,key=lambda a:(a['subdivision'][1]['global_max_dihedral'],a['metrics']['faces']))
    cfg=best['config']
    assert (cfg['width_ratio'],cfg['segments'],cfg['profile'])==(widths[name],1,.5),name
    six=next(a for a in good if a['config']['segments']==6 and a['config']['profile']==.5 and a['config']['width_ratio']==widths[name])
    v=[Vector(p) for p in case['sharp']['vertices']]
    rootids=sorted({i for e in case['sharp']['edges'] for i in e})
    n=len(rootids);root=mean([v[i] for i in rootids])
    assert rootids==list(range(len(v)-n,len(v)))
    tip=mean(v[-2*n:-n]);axis=(tip-root).normalized()
    up=Vector((0,0,1));side=up.cross(axis).normalized()
    target=(root+tip)/2
    scale=2.4*max((tip-root).length,2*max((v[i]-root).length for i in rootids))
    direction=(1.6*axis+1.1*side+.65*up).normalized()
    camera.location=target+direction*scale*3;aim(camera,target);camera.data.ortho_scale=scale
    camera.data.clip_end=scale*20
    for (obj,power,size),delta in zip(lights,[2*axis-1.6*side+2*up,1.5*axis+2*side+up,-axis+1.5*side+2*up]):
        obj.location=target+scale*delta;aim(obj,target);obj.data.energy=power*scale**2;obj.data.size=size*scale
    for arm,cfg,expected in [('native1',best['config'],best),('native6',six['config'],six),('custom',None,{'metrics':row['custom'],'subdivision':row['custom']['subdivision']})]:
        m=mesh_for(case,cfg);o=bpy.data.objects.new(arm,m);scene.collection.objects.link(o);m.materials.append(mat)
        assert len(m.vertices)==expected['metrics']['vertices'] and len(m.polygons)==expected['metrics']['faces'],(name,arm)
        for level in (0,2):
            for p in m.polygons:p.use_smooth=bool(level)
            if level:
                mod=o.modifiers.new('Fixed Catmull-Clark','SUBSURF');mod.levels=level;mod.render_levels=level
                bpy.context.view_layer.update()
                dg=bpy.context.evaluated_depsgraph_get();ev=o.evaluated_get(dg);em=ev.to_mesh()
                assert len(em.polygons)==expected['subdivision'][1]['faces'] and len(em.vertices)==expected['subdivision'][1]['vertices'],(name,arm,level)
                ev.to_mesh_clear()
            filename=f'{name}_{arm}_L{level}.png'
            scene.render.filepath=str(OUT/filename)
            bpy.ops.render.render(write_still=True)
            data=(OUT/filename).read_bytes()
            assert data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)>1000
            manifest.append(dict(case=name,arm=arm,level=level,config=cfg,base_faces=len(m.polygons),filename=filename,sha256=hashlib.sha256(data).hexdigest(),camera=list(camera.location),target=list(target),ortho_scale=scale))
        bpy.data.objects.remove(o,do_unlink=True);bpy.data.meshes.remove(m)
    print('PHASE115 CASE',name,flush=True)
assert len(manifest)==72
(OUT/'manifest.json').write_text(json.dumps(dict(approved=False,visual_review='pending',blender=bpy.app.version_string,render_count=len(manifest),images=manifest),indent=2))
print('PHASE115 RENDER COMPLETE',len(manifest))
