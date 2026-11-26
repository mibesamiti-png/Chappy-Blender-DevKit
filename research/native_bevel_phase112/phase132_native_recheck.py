"""Phase 132: frozen synthetic collars, Blender native validation; no adoption."""
import json, time, hashlib
from pathlib import Path
import numpy as np
import bpy
from mathutils.bvhtree import BVHTree
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from phase112_native_benchmark import metrics, topology_ok
from phase120_native_sections import planes, evaluate
from phase123_section_extent import measure, controls
ROOT=Path(__file__).resolve().parent
P=ROOT/'results';P.mkdir(exist_ok=True)
def arrays(m):
    return np.array([tuple(v.co) for v in m.vertices],float),[tuple(p.vertices) for p in m.polygons]
def inspect(m,ref,level):
    V,F=arrays(m);r=metrics(V,F)
    m.calc_loop_triangles();T=[tuple(t.vertices) for t in m.loop_triangles];vs=[v.co.copy() for v in m.vertices]
    tree=BVHTree.FromPolygons(vs,T,all_triangles=True,epsilon=0.)
    pairs=[(i,j) for i,j in tree.overlap(tree) if i<j and not set(T[i])&set(T[j])]
    r.update(level=level,nonincident_overlap=len(pairs),degenerate_triangles=sum(t.area<=1e-12 for t in m.loop_triangles),examples=pairs[:12])
    r['passed']=bool(topology_ok(r,ref) and r['boundary_edges']==ref['boundary_edges']*2**level and r['faces']==ref['faces']*4**level and r['quads']==r['faces'] and not r['nonincident_overlap'] and not r['degenerate_triangles'])
    return r
def unpack(seq):
    return [(np.array(p['A']),np.array(p['B']),np.array(p['N']),p['tol']) for p in seq]
def unit(a):
    return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1e-30)
def quad(V,F):
    A=V[np.array(F)];e=np.roll(A,-1,axis=1)-A
    n=unit(np.cross(e,np.roll(e,-1,axis=1)).sum(1))
    signed=np.einsum('fij,fj->fi',np.cross(unit(e),unit(-np.roll(e,1,axis=1))),n)
    warp=[]
    for k in (0,1):
        W=np.roll(A,-k,axis=1);x=unit(np.cross(W[:,1]-W[:,0],W[:,2]-W[:,0]));y=unit(np.cross(W[:,2]-W[:,0],W[:,3]-W[:,0]))
        warp.append(np.degrees(np.arccos(np.clip(np.sum(x*y,axis=-1),-1,1))))
    out=dict(min_signed_corner=float(signed.min()),max_warp=float(np.max(warp)),min_edge=float(np.linalg.norm(e,axis=-1).min()))
    out['passed']=out['min_signed_corner']>=.5 and out['max_warp']<=30 and out['min_edge']>=1e-9
    return out
def domain(V,T,ref,domain,original):
    sharp=evaluate(ref['vertices'],ref['faces'],domain)
    after=evaluate(V,T,domain)
    if not sharp['complete'] or not after['complete']:return dict(complete=False,sharp_valid=sharp['valid'],valid=after['valid'],total=after['total'])
    extent=[]
    for a,b,o in zip(sharp['sections'],after['sections'],original['sections']):
        assert a['section']==b['section']==o['section']
        q=measure(a['points'],b['points'])
        extent.append((q['symmetric']+q['error_bound'])*a['profile_length']/o['profile_length'])
    return dict(complete=True,max_turn=after['max_turn'],extent_upper=max(extent),valid=after['valid'],total=after['total'])
def main():
    start=time.perf_counter();p=ROOT/'phase131_frozen_meshes.json';sha=hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha=='d553b9541e8a080164b8550cdb270daf12423899aaf3f503a4c925e59bd91ed3'
    d=json.loads(p.read_text());fixtures={x['name']:x for x in json.loads((ROOT/'phase111_fixtures.json').read_text())['cases']}
    assert len(d['cases'])==6 and bpy.app.version_string=='4.4.3'
    out=dict(approved=False,native_executed=True,complete=False,version=bpy.app.version_string,fixture_sha256=sha,controls=controls(),rows=[])
    for c in d['cases']:
        m=bpy.data.meshes.new(c['name']);m.from_pydata(c['vertices'],[],c['faces']);m.update()
        ob=bpy.data.objects.new(c['name'],m);bpy.context.scene.collection.objects.link(ob)
        try:
            V,F=arrays(m);exact=bool(np.array_equal(V,np.asarray(c['vertices'],dtype=np.float32).astype(float)) and F==[tuple(f) for f in c['faces']])
            ref=metrics(c['vertices'],c['faces']);sharp=fixtures[c['name']]['sharp'];orig=evaluate(sharp['vertices'],sharp['faces'],planes(fixtures[c['name']]))
            assert orig['complete']
            m.calc_loop_triangles();T=[tuple(t.vertices) for t in m.loop_triangles]
            checks=[domain(V,T,sharp,unpack(c[k]),orig) for k in ('planes','fixed_planes')]
            q=quad(V,F[c['audit_start']:]);levels=[inspect(m,ref,0)]
            for level in (1,2):
                mod=ob.modifiers.new('native_subdivision','SUBSURF');mod.levels=level;mod.render_levels=level
                bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh()
                try:levels.append(inspect(em,ref,level))
                finally:ev.to_mesh_clear();ob.modifiers.remove(mod)
            passed=bool(exact and q['passed'] and all(k['passed'] for k in levels) and all(k['complete'] and k['max_turn']<=30 and k['extent_upper']<=.4 for k in checks))
            row=dict(name=c['name'],expected=c['expected'],exact_import=exact,quad=q,domains=checks,levels=levels,passed=passed)
            out['rows'].append(row);print('PHASE132_ROW',json.dumps(row,allow_nan=False),flush=True)
        finally:bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(m)
        (P/'phase132_native.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    out.update(complete=True,elapsed=time.perf_counter()-start)
    (P/'phase132_native.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE132_SUMMARY',json.dumps(dict(measured=len(out['rows']),passed=sum(r['passed'] for r in out['rows']),elapsed=out['elapsed'],approved=False)),flush=True)
    assert len(out['rows'])==6
if __name__=='__main__':main()
