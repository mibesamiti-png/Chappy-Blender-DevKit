"""Fixed Phase212-L native gate: geometry, sampled lock, contact and controls."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import bpy
from phase212_geneva_swept_relief import swept_profiles,ERROR_DEGREES
from phase212_native_geneva_geometry import main as geometry
from phase212_native_geneva_contact import run,FRAMES
from phase212_design_evaluation import qualification

def main():
    assert bpy.app.version_string=="4.4.3"
    dest=ROOT/"results"/"phase212_geneva_swept";dest.mkdir(parents=True,exist_ok=True)
    geom=geometry(swept_profiles,dest/"geometry",ERROR_DEGREES)
    stages=dict(geometry="pass" if geom["geometry_gate"] else "fail",
        sampled_lock="pass" if geom["sampled_lock_gate"] else "fail",
        perturbed_disk="pass" if geom["perturbed_disk_gate"] else "fail",
        full_motion="unverified",negative_controls="unverified")
    cases=[]
    if all(stages[k]=="pass" for k in ("geometry","sampled_lock","perturbed_disk")):
        physical=dest/"physical";physical.mkdir(exist_ok=True)
        c=run("engaged",False,True,physical,profile_factory=swept_profiles)
        cases.append(c)
        stages["full_motion"]=c["evaluation"]["status"]
        if stages["full_motion"]=="pass":
            for name,s,e in (("separated",True,True),("motor_off",False,False)):
                cases.append(run(name,s,e,physical,profile_factory=swept_profiles))
            stages["negative_controls"]=qualification(
                {c["name"]:c["evaluation"]["status"] for c in cases},
                required=("separated","motor_off"))["status"]
        for c in cases:
            (physical/(c["name"]+".json")).write_text(json.dumps(c,indent=2,allow_nan=False))
    gate=qualification(stages,required=tuple(stages))
    out=dict(complete=True,native_executed=True,frames=FRAMES,gate=gate,stages=stages,
        lock_fraction=geom["lock_fraction"],perturbed_count=len(geom["perturbed_disk_rows"]),
        perturbed_hits=sum(r["disk_overlap"] for r in geom["perturbed_disk_rows"]),
        dimensions=geom["dimensions"],cases=[{k:v for k,v in c.items() if k!="rows"} for c in cases],
        continuous_sweep_proven=False,manufacturing_certified=False)
    (dest/"report.json").write_text(json.dumps(out,indent=2,allow_nan=False))
    print("PHASE212L_SUMMARY",json.dumps({**out,"dimensions":{k:v for k,v in out["dimensions"].items() if k not in ("radius_before","radius_after")}},allow_nan=False),flush=True)
if __name__=="__main__":main()
