"""Phase 120: native Blender section comparison, frozen base meshes only.
Use identical source/child anchors for sharp, custom, and native candidates.
Run with Blender --background --factory-startup --python-exit-code 1 --python this.py
Or Python this.py --preflight (no Blender). No production adoption.
"""
import argparse, json, sys, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from phase119_section_quality import section, controls


def planes(c):
    V=np.array(c['sharp']['vertices'],float);F=c['sharp']['faces']
    n=len(c['sharp']['edges']);nf=len(c['source_faces']);tol=max(np.ptp(V,axis=0))*4e-7
    result=[]
    for j in range(n):
        f=F[nf+j];g=F[nf+n+j]
        A=V[f[:2]].mean(0);B=V[g[2:]].mean(0);C=V[f[2:]].mean(0)
        N=np.cross(C-A,B-C)
        if np.linalg.norm(N)<tol:raise ValueError('degenerate_plane')
        result.append((A,B,N,tol))
    return result


def evaluate(V,F,P):
    records=[]
    for j,(A,B,N,tol) in enumerate(P):
        try:r=section(V,F,A,B,N,tol)
        except ValueError as e:r={'error':str(e)}
        records.append(dict(section=j,**r))
    good=[r for r in records if 'error' not in r]
    # No partial section ranking: all pre-registered sections must be measurable.
    complete=len(good)==len(P)
    return dict(valid=len(good),total=len(P),complete=complete,
        max_turn=max(r['max_turn'] for r in good) if complete else None,
        p95_turn=float(np.percentile([r['max_turn'] for r in good],95)) if complete else None,
        mean_turn=float(np.mean([r['max_turn'] for r in good])) if complete else None,
        max_sum_turn=max(r['sum_turn'] for r in good) if complete else None,
        sections=records)


def make_mesh(c,mode,config=None):
    import bpy,bmesh
    src=c[mode];m=bpy.data.meshes.new('phase120');m.from_pydata(src['vertices'],[],src['faces']);m.update()
    if config is None:return m
    bm=bmesh.new()
    try:
        bm.from_mesh(m);bm.verts.ensure_lookup_table();bm.verts.index_update()
        wanted={tuple(sorted(e)) for e in src['edges']}
        geom=[e for e in bm.edges if tuple(sorted(v.index for v in e.verts)) in wanted]
        assert len(geom)==len(wanted) and all(e.is_manifold for e in geom)
        bmesh.ops.bevel(bm,geom=geom,offset=config['offset'],offset_type='OFFSET',segments=config['segments'],profile=config['profile'],affect='EDGES',clamp_overlap=True,loop_slide=True,miter_outer='SHARP',miter_inner='SHARP')
        bm.normal_update();bm.to_mesh(m);m.update()
    except Exception:
        bpy.data.meshes.remove(m);raise
    finally:bm.free()
    return m


def measure_native(c,mode,P,config=None,expected=None):
    import bpy
    m=make_mesh(c,mode,config)
    try:
        V=[tuple(v.co) for v in m.vertices];F=[tuple(p.vertices) for p in m.polygons]
        if expected is not None:assert (len(V),len(F))==(expected['vertices'],expected['faces'])
        m.calc_loop_triangles();T=[tuple(t.vertices) for t in m.loop_triangles]
        r=evaluate(V,T,P);r.update(vertices=len(V),faces=len(F),triangles=len(T))
        return r
    finally:bpy.data.meshes.remove(m)


def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true');p.add_argument('--fixtures',type=Path,default=ROOT/'phase111_fixtures.json');p.add_argument('--native',type=Path,default=ROOT/'results'/'native.json');p.add_argument('--out',type=Path,default=ROOT/'results'/'phase120_sections.json');a=p.parse_args(args)
    start=time.perf_counter();cc=controls();D=json.loads(a.fixtures.read_text())['cases'];assert len(D)==12
    raw=json.loads(a.native.read_text()) if not a.preflight else None
    if raw:
        import bpy
        assert raw['complete'] and raw['blender_version']==bpy.app.version_string=='4.4.3'
        old={x['name']:x for x in raw['rows']};assert set(old)=={c['name'] for c in D}
    out=dict(approved=False,native_executed=not a.preflight,controls=len(cc),complete=False,rows=[])
    a.out.parent.mkdir(parents=True,exist_ok=True)
    for c in D:
        P=planes(c);row=dict(name=c['name'],sections=len(P),candidates=[])
        for arm in ('sharp','custom'):
            if a.preflight:
                src=c[arm];r=evaluate(np.array(src['vertices'],dtype=np.float32),src['faces'],P)
            else:r=measure_native(c,arm,P,expected=old[c['name']]['custom'] if arm=='custom' else None)
            row[arm]=r
        if raw:
            for prev in old[c['name']]['candidates']:
                cfg=prev['config'];record=dict(config=cfg,prior_screened=prev['screened'],prior_screen_reasons=prev['screen_reasons'])
                # Preserve the earlier quality exclusions; never select an excluded mesh.
                if prev['screened']:
                    try:record['measurement']=measure_native(c,'sharp',P,cfg,prev['metrics'])
                    except Exception as e:record['error']=repr(e)
                row['candidates'].append(record)
        out['rows'].append(row)
        print(c['name'],row['sharp']['valid'],row['custom']['valid'],sum(x.get('measurement',{}).get('complete',False) for x in row['candidates']),flush=True)
        a.out.write_text(json.dumps(out,allow_nan=False))
    out['complete']=True;out['elapsed']=time.perf_counter()-start
    a.out.write_text(json.dumps(out,allow_nan=False))
    assert all(x['sharp']['complete'] and x['custom']['complete'] for x in out['rows'])
    if raw:
        assert sum(len(x['candidates']) for x in out['rows'])==252
        assert sum(x['prior_screened'] for row in out['rows'] for x in row['candidates'])==245
        assert not any('error' in x for row in out['rows'] for x in row['candidates'])
    print('PHASE120',out['elapsed'])
if __name__=='__main__':main()
