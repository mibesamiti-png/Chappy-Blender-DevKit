"""Phase212-H native end-to-end integration fixture.
Frozen two-candidate plan, same two-axis specification and tested native
contact backend. Only geometry-rejected candidates are cheap to skip.
No generic mechanism synthesis or manufacturing qualification.
"""
import json,sys
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from phase212_design_engine import design
from phase212_design_evaluation import qualification
from phase212_radial_cam import generate,audit
from phase212_cam_assembly import assemble,verify
from phase212_native_shared_drive import fixture,run

def main():
    assert bpy.app.version_string=='4.4.3'
    dest=ROOT/'results'/'phase212_engine';dest.mkdir(parents=True,exist_ok=True)
    spec,stations,strokes=fixture()
    candidates={"compact":tuple(replace(s,cam=replace(s.cam,pitch_base=.7)) for s in stations),
                "reference":stations}
    calls=[]
    def backend(cid,stage):
        calls.append([cid,stage])
        ss=candidates[cid]
        folder=dest/cid;folder.mkdir(exist_ok=True)
        if stage=="geometry":
            reports={}
            for t,s in zip(spec.tracks,ss):
                assert t.name==s.track
                reports[t.name]=audit(t,s.cam,generate(t,s.cam))
            gate=qualification({k:r["sampled_geometry"]["status"] for k,r in reports.items()},required=tuple(reports))
            return dict(status=gate["status"],evidence=reports)
        if stage=="screen":
            bpy.ops.wm.read_factory_settings(use_empty=True)
            assembly=assemble(spec,ss,.6,.4,.4)
            r=verify(assembly,241,animate=True)
            if r["evaluation"]["status"]=="pass":
                bpy.context.scene.render.fps=60
                # Preview is ideal kinematics, not captured physical motion.
                bpy.ops.wm.save_as_mainfile(filepath=str(folder/'kinematic_preview.blend'))
            return dict(status=r["evaluation"]["status"],evidence=r)
        if stage=="full_motion":
            r=run("engaged",spec,ss,strokes,False,True,folder)
            (folder/"engaged.json").write_text(json.dumps(r,indent=2,allow_nan=False))
            return dict(status=r["evaluation"]["status"],evidence={k:v for k,v in r.items() if k!="rows"})
        if stage=="negative_controls":
            results={}
            for n,s,e in [("separated",True,True),("motor_off",False,False)]:
                r=run(n,spec,ss,strokes,s,e,folder)
                (folder/(n+".json")).write_text(json.dumps(r,indent=2,allow_nan=False))
                results[n]={k:v for k,v in r.items() if k!="rows"}
            gate=qualification({k:v["evaluation"]["status"] for k,v in results.items()},required=tuple(results))
            return dict(status=gate["status"],evidence=results)
        raise ValueError("unknown stage")
    result=design(tuple(candidates),2,backend)
    out=dict(complete=True,native_executed=True,design=result,calls=calls,spec=spec.to_dict(),
        candidate_parameters={k:[dict(track=s.track,pitch_base=s.cam.pitch_base,roller_radius=s.cam.roller_radius) for s in ss] for k,ss in candidates.items()},
        ideal_rigid_camshaft=True,ideal_guides=True,gravity_return=True,manufacturing_certified=False)
    (dest/"report.json").write_text(json.dumps(out,indent=2,allow_nan=False))
    print('PHASE212H_SUMMARY',json.dumps(dict(action=result["action"],selected=result["selected"],calls=calls,
        stages=[dict(candidate=h["candidate"],qualification=h["qualification"]) for h in result["history"]]),allow_nan=False),flush=True)
if __name__=='__main__':main()
