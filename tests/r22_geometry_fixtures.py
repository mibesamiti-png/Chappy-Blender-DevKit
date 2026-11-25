"""R22 preregistered synthetic detection-limit fixtures and aggregate observations.

No product path changes. All dimensional expectations are independent of the
sampled distance implementation; positive differences can be missed.
"""
from __future__ import annotations

import math
from cbdk.glb_boundary_audit import boundary_audit
from cbdk.glb_feature_priority import geometry_feature_hints
from cbdk.glb_sampling_audit import probe_sampling_sensitivity
from cbdk.glb_surface_distance import _validated_triangles
from cbdk.glb_multires_surface import compare_expanded_triangle_surfaces
from cbdk.glb_part_match import review_part_surfaces

EPS = 1e-6
ROUNDTRIP_TOL = 2e-5
MAX_ROWS = 16
MAX_FACES = 64
MAX_PARTS = 3


def quad(a, b, c, d, alternate=False):
    return [(a,b,d),(b,c,d)] if alternate else [(a,b,c),(a,c,d)]


def sheet(z=0., alternate=False):
    return quad((-1.,-1.,z),(1.,-1.,z),(1.,1.,z),(-1.,1.,z),alternate)


def grid_sheet(width, cut):
    h = width / 2
    points = [-1.,-h,h,1.]
    faces = []
    for i in range(3):
        for j in range(3):
            if cut and i == j == 1:
                continue
            x,y = points[i], points[j]
            u,v = points[i+1],points[j+1]
            faces.extend(quad((x,y,0.),(u,y,0.),(u,v,0.),(x,v,0.)))
    return faces


def box(lo, hi, alternate=False):
    x,y,z = lo
    u,v,w = hi
    p = [(x,y,z),(u,y,z),(u,v,z),(x,v,z),
         (x,y,w),(u,y,w),(u,v,w),(x,v,w)]
    result = []
    for a,b,c,d in ((0,3,2,1),(4,5,6,7),(0,1,5,4),
                    (1,2,6,5),(2,3,7,6),(3,0,4,7)):
        result.extend(quad(p[a],p[b],p[c],p[d],alternate))
    return result


def flatten(groups):
    return [face for group in groups for face in group], [len(g) for g in groups]


def cases():
    def row(family, name, left, right, maximum, *, exact=False, reverse_zero=False,
            physical="not_proven", dimension=None):
        return dict(family=family, name=name, left=left, right=right,
                    true_surface_max=maximum, exact_sample_max=exact,
                    reference_to_candidate_zero=reverse_zero, physical=physical,
                    dimension=dimension)

    result = []
    for width in (.5,.02):
        result.append(row("aperture",f"hole_{width}",[sheet()],
                          [grid_sheet(width,True)],width/2,
                          physical="constructed_planar_aperture_not_solid_hole",
                          dimension=width))
    result.append(row("aperture","outer_border_control",[sheet()],
                      [grid_sheet(.5,False)],0.,exact=True,
                      physical="outer_edge_subdivision_not_hole"))
    for gap in (.02,.002):
        result.append(row("thin_wall",f"wall_{gap}",[sheet()],
                          [sheet()+sheet(gap)],gap,exact=True,reverse_zero=True,
                          physical="known_parallel_sheet_spacing_not_minimum_thickness",
                          dimension=gap))
    result.append(row("thin_wall","wall_control",[sheet()],[sheet(alternate=True)],
                      0.,exact=True))
    first = box((0.,0.,0.),(1.,1.,1.))
    second = box((1.,0.,0.),(2.,1.,1.))
    for delta in (.2,.02,-.2,-.02):
        shifted = box((1.+delta,0.,0.),(2.+delta,1.,1.))
        result.append(row("joint",f"joint_{delta}",[first,second],[first,shifted],
                          abs(delta),exact=True,
                          physical="constructed_gap" if delta>0 else "constructed_overlap",
                          dimension=delta))
    result.append(row("joint","touch_control",[first,second],[first,second],
                      0.,exact=True,physical="constructed_touch_not_proven_by_distance"))
    result.append(row("joint","coincident_copy",[first,second],[first,second,first],
                      0.,exact=True,physical="duplicate_part_not_proven_intersection"))
    outer = box((-1.,-1.,-1.),(1.,1.,1.))
    for h in (.5,.25):
        inner = box((-h,-h,-h),(h,h,h))
        result.append(row("internal",f"inner_{h}",[outer],[outer+inner],
                          1.-h,exact=True,reverse_zero=True,
                          physical="explicit_internal_faces_not_void_proof",dimension=h))
    result.append(row("internal","outer_control",[outer],
                      [box((-1.,-1.,-1.),(1.,1.,1.),True)],0.,exact=True))
    result.append(row("internal","hidden_interior_unknown",[outer],[outer],None,
                      physical="unencoded_interior_information_absent"))
    assert len(result) == MAX_ROWS
    return result


def inspect_case(case, ref, cand, rc, cc, report=None):
    assert 1 <= len(ref) <= MAX_FACES and 1 <= len(cand) <= MAX_FACES
    assert 1 <= len(rc) <= MAX_PARTS and 1 <= len(cc) <= MAX_PARTS
    assert sum(rc) == len(ref) and sum(cc) == len(cand)
    if report is None:
        report = compare_expanded_triangle_surfaces(ref,cand)
        if report["status"] == "review_only":
            report["part_review"] = review_part_surfaces(ref,cand,rc,cc)
    result = {k:case[k] for k in ("family","name","true_surface_max","physical","dimension")}
    result["global_status"] = report["status"]
    if report["status"] != "review_only":
        result.update(classification="not_measured",reason=report.get("reason"),
                      work=report.get("work_budget",{}))
        return result
    fixed,adaptive = report["fixed_surface"],report["adaptive_surface"]
    fmax,amax = fixed["symmetric_sampled_max"],adaptive["refined_symmetric_sampled_max"]
    expected = case["true_surface_max"]
    for value in (fmax,amax):
        assert math.isfinite(value) and value >= 0
        if expected is not None:
            assert value <= expected+ROUNDTRIP_TOL, (case["name"],value,expected)
            if case["exact_sample_max"]:
                assert abs(value-expected) <= ROUNDTRIP_TOL,(case["name"],value,expected)
        else:
            # Same exported surface; the physical hidden interior is unknown.
            assert value <= ROUNDTRIP_TOL
    if case["reference_to_candidate_zero"]:
        assert fixed["reference_to_candidate"]["sampled_max"] <= ROUNDTRIP_TOL
        assert adaptive["reference_to_candidate"]["refined_sampled_max"] <= ROUNDTRIP_TOL
    assert fixed["exact_surface_equivalence_verified"] is False
    assert fixed["enclosed_cavities_verified"] is False
    assert adaptive["enclosed_cavities_verified"] is False
    assert adaptive["complete_surface_coverage"] is False
    def classify(value):
        if expected is None:
            return "information_absent"
        if expected > EPS:
            return "detected" if value > EPS else "missed"
        return "false_warning" if value > EPS else "negative_control"
    def hint_counts(faces,counts):
        audit = boundary_audit(faces,counts)
        hints = geometry_feature_hints(_validated_triangles(faces,"fixture"))
        return {"boundary_edges":audit["summary"]["boundary_edges"],
                "nonmanifold_edges":audit["summary"]["nonmanifold_edge_incidence"],
                "interior_boundary_hint_faces":sum(h["flags"]["bbox_interior_boundary_hint"] for h in hints),
                "sharp_hint_faces":sum(h["flags"]["sharp_shared_edge_hint"] for h in hints)}
    points = [p for f in ref+cand for p in f]
    diag = math.sqrt(sum((max(p[k] for p in points)-min(p[k] for p in points))**2
                         for k in range(3)))
    low = max(diag*.01,1e-7)
    high = max(diag*.05,low*2)
    probe = probe_sampling_sensitivity(ref,cand,low,high)
    assert probe["unobserved_regions_verified"] is False
    part = report["part_review"]
    assert part["auto_apply"] is False and part["cross_file_part_identity_proven"] is False
    rows = part.get("reference_parts",[])
    observations = [o for row in rows for o in row["observations"]]
    result.update(
        fixed_max=fmax, adaptive_max=amax,
        fixed_class=classify(fmax),adaptive_class=classify(amax),
        classification=classify(max(fmax,amax)),
        ref_hints=hint_counts(ref,rc),cand_hints=hint_counts(cand,cc),
        probe_sensitive_faces=probe["reference_summary"]["sensitive_faces"]+probe["candidate_summary"]["sensitive_faces"],
        probe_max_gain=max(probe["reference_summary"]["max_observed_increase"],
                           probe["candidate_summary"]["max_observed_increase"]),
        probe_query_samples=48*(len(ref)+len(cand)),
        probe_evaluation_upper_bound=96*len(ref)*len(cand),
        part_status=part["status"],
        part_suggested=sum(row["status"]=="suggested" for row in rows),
        part_ambiguous=sum(row["status"]=="ambiguous" for row in rows),
        part_unmatched=sum(row["status"]=="unmatched" for row in rows),
        part_unpaired_candidate=len(part.get("unpaired_candidate_part_ids",[])),
        part_not_measured=sum(o["status"]=="not_measured" for o in observations),
        part_pairs=part.get("pair_attempts",0),
        global_work=report["work_budget"]["used"],
        part_work=part.get("work_budget",{}).get("used",{}),
    )
    if case["name"] == "outer_border_control":
        assert result["ref_hints"]["boundary_edges"] == 4
        assert result["cand_hints"]["boundary_edges"] == 12
    if case["name"] == "coincident_copy":
        assert result["part_ambiguous"] >= 1
    if case["family"] == "internal":
        assert result["ref_hints"]["boundary_edges"] == 0
        assert result["cand_hints"]["boundary_edges"] == 0
    return result


def summarize(results):
    summary = {}
    labels = ("detected","missed","false_warning","negative_control","information_absent","not_measured")
    for metric in ("fixed_class","adaptive_class","classification"):
        summary[metric] = {label:sum(row.get(metric,"not_measured")==label for row in results)
                           for label in labels}
    return summary
