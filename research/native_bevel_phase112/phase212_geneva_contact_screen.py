"""K2: bounded diagnosis of the K stalled drive. Do not relax K limits.
Try 40 degrees first. If it fails, test 45 degrees and increased impulse
separately. Re-run negative controls only for the first passing candidate.
A passing physical fixture does not imply the J2 98% sampled-lock gate.
"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from phase212_native_geneva_contact import run,FRAMES
from phase212_design_evaluation import qualification
PLAN=(("relief40",40,40.),("relief45",45,40.),("impulse160",35,160.))

def main():
    assert bpy.app.version_string=="4.4.3"
    dest=ROOT/"results"/"phase212_geneva_k2";dest.mkdir(parents=True,exist_ok=True)
    history=[];selected=None;action="stop_and_redesign"
    for cid,relief,impulse in PLAN:
        d=dest/cid;d.mkdir(exist_ok=True)
        case=run("engaged",False,True,d,relief,impulse)
        (d/"engaged.json").write_text(json.dumps(case,indent=2,allow_nan=False))
        entry=dict(candidate=cid,relief_degrees=relief,impulse=impulse,
            motion=case["evaluation"],input=case["input"],output=case["output"],controls={})
        history.append(entry)
        if case["evaluation"]["status"]=="unverified":
            action="collect_missing_evidence";break
        if case["evaluation"]["status"]!="pass":continue
        for n,s,e in [("separated",True,True),("motor_off",False,False)]:
            c=run(n,s,e,d,relief,impulse)
            (d/(n+".json")).write_text(json.dumps(c,indent=2,allow_nan=False))
            entry["controls"][n]=c["evaluation"]
        ctrl=qualification({k:v["status"] for k,v in entry["controls"].items()},required=("separated","motor_off"))
        entry["fixture_gate"]=qualification(dict(full_motion=case["evaluation"]["status"],negative_controls=ctrl["status"]),required=("full_motion","negative_controls"))
        if entry["fixture_gate"]["status"]=="unverified":
            action="collect_missing_evidence";break
        if entry["fixture_gate"]["certified"]:
            selected=cid;action="physical_fixture_pass_lock_recheck_required";break
    result=dict(complete=True,native_executed=True,frames=FRAMES,budget=len(PLAN),plan=PLAN,
        selected=selected,action=action,history=history,sampled_lock_reverified=False,
        whole_design_certified=False,manufacturing_certified=False)
    (dest/"report.json").write_text(json.dumps(result,indent=2,allow_nan=False))
    print("PHASE212K2_SUMMARY",json.dumps(result,allow_nan=False),flush=True)
if __name__=="__main__":main()
