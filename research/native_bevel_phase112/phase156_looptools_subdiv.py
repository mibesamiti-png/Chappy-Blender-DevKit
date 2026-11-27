"""Phase 156: replay frozen LoopTools settings and audit native subdivision.
Same synthetic fixtures as Phase 154; not an independent holdout or adoption.
"""
import json,sys,time,hashlib
from pathlib import Path
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase154_looptools import RINGS,actual,load_extension,unload_extension
from phase143_native_recheck import arrays,inspect,quad,domain,unpack
from phase112_native_benchmark import metrics
from phase120_native_sections import planes,evaluate
ROOT=Path(__file__).resolve().parent
P=ROOT/'results'
# Frozen from successful Phase 154 logs, not chosen anew.
SETTINGS={
 'offset_single':('space','axial','cubic',100,1),
 'low_wide':('keep','axial','linear',0,0),
 'corner_before':('relax','axial','cubic',100,3),
 'corner_after':('space','circ','linear',25,1),
}
def edge_ratio(V,F):
    a=V[np.asarray(F)];e=np.linalg.norm(np.roll(a,-1,axis=1)-a,axis=2)
    return float(np.max(e.max(1)/np.maximum(e.min(1),1e-30)))
def snapshot(m,ref,level,baseline=None):
    V,F=arrays(m);r=inspect(m,ref,level)
    r['edge_ratio_all']=edge_ratio(V,F)
    if baseline is not None:
        B,G=baseline
        assert F==G and V.shape==B.shape
        d=np.linalg.norm(V-B,axis=1)
        r['max_corresponding_displacement']=float(d.max())
        r['rms_corresponding_displacement']=float(np.sqrt(np.mean(d*d)))
    return r,(V,F)
def run(c,V,F,sharp,orig,ring,nb,setting,baseline=None):
    op,d,i,alpha,it=setting
    m=bpy.data.meshes.new('p156');m.from_pydata(V.tolist(),[],F);m.update()
    ob=bpy.data.objects.new('p156',m);bpy.context.scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    try:
        if op!='keep':
            paths=ring.T.tolist() if d=='axial' else ring[1:-1].tolist()
            actual(m,paths,d=='circ',op,i,alpha,it)
        X,H=arrays(m);assert H==F and X.shape==V.shape
        ref=metrics(V,F);fixed=float(np.linalg.norm(X[:nb]-V[:nb],axis=1).max())
        q=quad(X,H[c['audit_start']:])
        ratio=edge_ratio(X,H[c['audit_start']:])
        m.calc_loop_triangles();T=[tuple(t.vertices) for t in m.loop_triangles];Q=np.asarray(H)
        d0=np.concatenate([Q[:,[0,1,2]],Q[:,[0,2,3]]]);d1=np.concatenate([Q[:,[0,1,3]],Q[:,[1,2,3]]])
        checks=[domain(X,tri,sharp,unpack(c[k]),orig) for tri in (T,d0,d1) for k in ('planes','fixed_planes')]
        complete=all(z['complete'] for z in checks)
        turn=max(z['max_turn'] for z in checks) if complete else None
        extent=max(z['extent_upper'] for z in checks) if complete else None
        levels=[];coords=[]
        for level in (0,1,2):
            if level==0:r,pair=snapshot(m,ref,level,None if baseline is None else baseline[level])
            else:
                mod=ob.modifiers.new('native_subdivision','SUBSURF');mod.levels=level;mod.render_levels=level
                bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh()
                try:r,pair=snapshot(em,ref,level,None if baseline is None else baseline[level])
                finally:ev.to_mesh_clear();ob.modifiers.remove(mod)
            levels.append(r);coords.append(pair)
        passed=bool(fixed<=1e-6 and q['passed'] and complete and turn<=30 and extent<=.4 and all(z['passed'] for z in levels))
        row=dict(setting=list(setting),fixed_error=fixed,quad=q,max_edge_ratio=ratio,max_turn=turn,extent_upper=extent,sections_complete=complete,levels=levels,passed=passed,geometry_sha256=hashlib.sha256(X.astype('<f8').tobytes()).hexdigest())
        return row,coords
    finally:bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(m)
def main():
    start=time.perf_counter();assert bpy.app.version_string=='4.4.3'
    old=json.loads((P/'phase154_looptools.json').read_text())
    assert old['complete'] and old['native_executed'] and not old['approved']
    assert old['extension']['sha256']=='ff1ca3b3fff73094379da8b1fa2c1acbc9d88d26b7dfc73bb9de5941a6b50108'
    prior={r['name']:r for r in old['rows']}
    fixtures={r['fixture']['name']:r['fixture'] for r in json.loads((ROOT/'phase133_holdout_frozen.json').read_text())['cases']}
    data={r['name']:r for r in json.loads((ROOT/'phase141_frozen_meshes.json').read_text())['cases']}
    out=dict(approved=False,native_executed=True,complete=False,version=bpy.app.version_string,rows=[])
    module=load_extension()
    try:
        for name,label in [('offset_single','offset_single'),('low_wide','low_wide'),('corner_two','corner_before'),('corner_two','corner_after')]:
            c=data[name];F=[tuple(f) for f in c['faces']];V=np.asarray(c['vertices'],dtype=np.float32).astype(float)
            if label=='corner_after':
                lines=(ROOT/'phase142_corner_two_selected.obj').read_text().splitlines()
                V=np.asarray([list(map(float,l.split()[1:])) for l in lines if l.startswith('v ')],dtype=np.float32).astype(float)
                assert F==[tuple(int(i)-1 for i in l.split()[1:]) for l in lines if l.startswith('f ')]
            nb,a,b=RINGS[name];n=len(a);steps=c['config']['steps'];assert len(V)==nb+(steps-1)*n
            ring=np.vstack([a,np.arange(nb,len(V)).reshape(steps-1,n),b])
            sharp=fixtures[name]['sharp'];orig=evaluate(sharp['vertices'],sharp['faces'],planes(fixtures[name]));assert orig['complete']
            baseline,coords=run(c,V,F,sharp,orig,ring,nb,('keep','axial','linear',0,0))
            setting=SETTINGS[label];selected=prior[label]['selected']
            assert tuple(selected[k] for k in ('op','direction','interpolation','influence','iterations'))==setting
            edited=None
            if setting[0]!='keep':
                edited,newcoords=run(c,V,F,sharp,orig,ring,nb,setting,coords)
                X,H=newcoords[0]
                obj=P/('phase156_'+label+'.obj')
                obj.write_text(''.join('v %.9g %.9g %.9g\n'%tuple(v) for v in X)+''.join('f '+' '.join(str(i+1) for i in f)+'\n' for f in H))
            result=edited or baseline
            reproducible=all(abs(result[k]-selected[k])<=1e-6 for k in ('max_edge_ratio','max_turn','extent_upper','fixed_error'))
            row=dict(name=label,baseline=baseline,edited=edited,reproducible=reproducible,selected_passed=result['passed'])
            out['rows'].append(row)
            print('PHASE156_ROW',json.dumps(row,allow_nan=False),flush=True)
    finally:unload_extension(module)
    out.update(complete=True,elapsed=time.perf_counter()-start)
    (P/'phase156_looptools_subdiv.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE156_SUMMARY',json.dumps(dict(cases=len(out['rows']),meshes=sum(1+(r['edited'] is not None) for r in out['rows']),selected_passed=sum(r['selected_passed'] for r in out['rows']),reproducible=sum(r['reproducible'] for r in out['rows']),elapsed=out['elapsed'])),flush=True)
    assert len(out['rows'])==4 and all(r['reproducible'] for r in out['rows'])
if __name__=='__main__':main()
