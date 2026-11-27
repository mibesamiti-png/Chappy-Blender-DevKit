"""Phase212-D: native 3D radial cam part adapter.
Reuses the previously tested ring builder and independent native mesh/ray audits.
Round polygonal bore only; no keyed torque transfer or assembly certification.
"""
import math
from phase212_design_evaluation import finite
from phase212_radial_cam import generate,audit

def build(track,cfg,thickness,bore_radius,min_wall):
    from phase206_hybrid_machine import ring
    from phase196_spacer_verification import Rays
    import bpy
    if not all(finite(v) and v>0 for v in (thickness,bore_radius,min_wall)):
        raise ValueError("positive part dimensions required")
    outer=generate(track,cfg)
    geom=audit(track,cfg,outer)
    if geom["sampled_geometry"]["status"]!="pass":
        return None,dict(status="fail",reason="profile_gate",geometry=geom)
    core=geom["sampled_geometry"]["metrics"]["core_radius"]["min"]
    wall=core-bore_radius
    if wall<min_wall:
        return None,dict(status="fail",reason="wall",conservative_wall=wall,geometry=geom)
    inner=[tuple(v*bore_radius/math.hypot(*p) for v in p) for p in outer]
    m,native=ring(track.name,list(outer),inner,h=thickness)
    try:
        rays=Rays(m);reach=2*max(core,bore_radius,thickness,1.)
        z=thickness/2+1.
        axial_clear=all(rays.cast((.8*bore_radius*math.cos(a),.8*bore_radius*math.sin(a),z),(0,0,-1),thickness+2) is None
            for a in [i*math.tau/16 for i in range(16)]) and rays.cast((0,0,z),(0,0,-1),thickness+2) is None
        radial_errors=[];cap_errors=[]
        for i in range(0,len(inner),max(1,len(inner)//24)):
            p=inner[i];r=math.hypot(*p);d=(p[0]/r,p[1]/r,0.)
            hit=rays.cast((0,0,0),d,reach)
            radial_errors.append(abs(hit-bore_radius) if hit is not None else reach)
            x,y=(v*(bore_radius+wall/2) for v in d[:2])
            hit=rays.cast((x,y,z),(0,0,-1),thickness+2)
            cap_errors.append(abs(hit-1.) if hit is not None else reach)
        tol=2e-5*max(1.,core,thickness,bore_radius)
        extent=max(v.co.z for v in m.vertices)-min(v.co.z for v in m.vertices)
        checks=dict(native_closed=bool(native["passed"]),axial_bore_open=bool(axial_clear),
            radial_bore=max(radial_errors)<=tol,solid_cap=max(cap_errors)<=tol,
            thickness=abs(extent-thickness)<=tol,wall=wall>=min_wall)
        out=dict(status="pass" if all(checks.values()) else "fail",checks=checks,
            geometry=geom,native=native,conservative_wall=wall,thickness=thickness,bore_radius=bore_radius,
            max_bore_ray_error=max(radial_errors),max_cap_ray_error=max(cap_errors),
            vertices=len(m.vertices),faces=len(m.polygons),unit=track.unit,
            physical_contact_certified=False,torque_transfer_certified=False,manufacturing_certified=False)
        if out["status"]!="pass":
            bpy.data.meshes.remove(m);return None,out
        return m,out
    except Exception:
        bpy.data.meshes.remove(m);raise
