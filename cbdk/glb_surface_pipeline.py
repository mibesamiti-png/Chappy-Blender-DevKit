"""Safe local opt-in bridge from GLB files to bounded surface diagnostics.

Only the fixed CBDK Blender script is executed. The two GLB files are static
preflight-inspected locally. No addon Python, source code, screenshots or raw
triangle coordinates enter the generated JSON or any network workflow.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess

from .glb_inspector import GLBInspectionError, inspect_glb
from .glb_part_hints import count_based_part_hints
from .glb_part_match import _part_review_header, PART_PAIR_LIMIT, PART_BOUNDARY_RESERVATION_LIMIT, PART_RELATIVE_REVIEW_THRESHOLD, MAX_PARTS, MAX_SCORE
from .glb_surface_distance import MAX_TRIANGLES, EXPANDED_MAX_TRIANGLES, _SurfaceWorkBudget
from .glb_multires_surface import COARSE_SAMPLES, FINE_SAMPLES, MAX_SUSPECT_FACES, EXPLORATION_FACES

MAX_INPUT_BYTES = 24 * 1024 * 1024
MAX_VERTEX_REFERENCES = 100_000
MAX_REPORT_BYTES = 1024 * 1024
MARKER = "CBDK_GLB_SURFACE_REVIEW_PASS "


class GLBSurfacePipelineError(ValueError):
    pass


def _reject_duplicate_keys(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("duplicate JSON key")
        output[key] = value
    return output


def _reject_nonfinite_constant(value):
    raise ValueError("nonfinite JSON constant: " + value)


def _strict_json(text):
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys,
                      parse_constant=_reject_nonfinite_constant)


def _preflight(source: str | Path) -> Path:
    path = Path(source).resolve()
    if not path.is_file() or path.suffix.lower() != ".glb":
        raise GLBSurfacePipelineError("A local .glb file is required")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise GLBSurfacePipelineError("GLB exceeds the conservative 24 MiB import limit")
    try:
        inspection = inspect_glb(path)
    except (GLBInspectionError, OSError, RecursionError) as exc:
        raise GLBSurfacePipelineError("GLB failed static preflight") from exc
    if inspection["external_uris"]:
        raise GLBSurfacePipelineError("External GLB URI resources are not allowed")
    if inspection["counts"]["meshes"] < 1:
        raise GLBSurfacePipelineError("GLB contains no mesh")
    if inspection["counts"]["approximate_vertex_references"] > MAX_VERTEX_REFERENCES:
        raise GLBSurfacePipelineError("GLB references too many vertices for safe import")
    return path


def run_glb_surface_review(
    blender: str | Path,
    reference: str | Path,
    candidate: str | Path,
    output: str | Path,
    *,
    timeout: int = 180,
    profile: str = "legacy_512",
) -> dict:
    """Load two local GLBs in factory-startup Blender and save aggregate-only JSON.

    Returns status='review_only' for measured differences (including zero), or
    status='skipped' for triangle-count limits. Never interprets zero as proof.
    """
    if profile not in ("legacy_512", "expanded_2048", "expanded_2048_parts"):
        raise GLBSurfacePipelineError("Unknown surface review profile")
    expanded = profile != "legacy_512"
    parts = profile == "expanded_2048_parts"
    limit = EXPANDED_MAX_TRIANGLES if expanded else MAX_TRIANGLES
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 10 <= timeout <= 900:
        raise GLBSurfacePipelineError("timeout must be between 10 and 900 seconds")
    executable = Path(blender).resolve()
    if not executable.is_file():
        raise GLBSurfacePipelineError("The Blender executable does not exist")
    ref = _preflight(reference)
    cand = _preflight(candidate)
    target = Path(output).resolve()
    if target.suffix.lower() != ".json" or target in (ref, cand):
        raise GLBSurfacePipelineError("Output must be a separate .json file")
    script = Path(__file__).resolve().parent.parent / "scripts" / "blender_glb_surface_review.py"
    if not script.is_file():
        raise GLBSurfacePipelineError("Trusted CBDK Blender surface runner was not found")

    target.parent.mkdir(parents=True, exist_ok=True)
    # Avoid accidentally trusting stale evidence after a failed/partial run.
    if target.exists():
        target.unlink()
    cmd = [
        str(executable), "--background", "--factory-startup", "--disable-autoexec",
        "--python-exit-code", "7", "--python", str(script),
        "--", str(ref), str(cand), str(target),
    ]
    if expanded:
        cmd.append(profile)
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        if expanded:
            target.unlink(missing_ok=True)
        raise GLBSurfacePipelineError("Trusted Blender surface review timed out") from exc
    except OSError as exc:
        raise GLBSurfacePipelineError("Could not start Blender for GLB review") from exc

    payloads = [line.split(MARKER, 1)[1] for line in result.stdout.splitlines()
                if line.startswith(MARKER)]
    if result.returncode != 0 or len(payloads) != 1:
        if expanded:
            target.unlink(missing_ok=True)
        raise GLBSurfacePipelineError("Blender surface review failed; no report was accepted")
    try:
        payload = _strict_json(payloads[0])
        if not isinstance(payload, dict) or set(payload) != {"kind", "status"}:
            raise ValueError("invalid runner acknowledgment")
        if payload["kind"] != "cbdk_glb_surface_review":
            raise ValueError("unexpected kind")
        if payload["status"] not in ("review_only", "skipped"):
            raise ValueError("unexpected status")
        if not target.is_file() or target.stat().st_size > MAX_REPORT_BYTES:
            raise ValueError("report is missing or too large")
        report = _strict_json(target.read_text(encoding="utf-8"))
        if not isinstance(report, dict) or report.get("kind") != payload["kind"]:
            raise ValueError("invalid report kind")
        if (report.get("status") != payload["status"]
                or type(report.get("schema_version")) is not int
                or report["schema_version"] != (3 if parts else 2 if expanded else 1)):
            raise ValueError("invalid report status or version")
        if report.get("source") != "local_blender_import_aggregate_only":
            raise ValueError("unexpected report source")
        if report.get("complete_surface_equivalence_proven") is not False:
            raise ValueError("invalid equality safety flag")
        if report.get("auto_apply") is not False:
            raise ValueError("automatic action must be disabled")
        if not isinstance(report.get("safety"), dict) or any(
            report["safety"].get(key) is not False
            for key in ("executes_addon_code", "uploads_private_glb",
                        "saves_raw_mesh_vertices", "changes_source_glbs")
        ):
            raise ValueError("invalid safety flags")
        if payload["status"] == "review_only" and (
            not isinstance(report.get("fixed_surface"), dict)
            or not isinstance(report.get("adaptive_surface"), dict)
        ):
            raise ValueError("missing surface evidence")
        if payload["status"] == "skipped" and report.get("reason") not in (
            ("triangle_limit", "work_budget") if expanded else ("triangle_limit",)
        ):
            raise ValueError("unknown skip reason")
        # A Blender process is an external evidence producer, not an authority.
        # Reject malformed aggregate metrics instead of passing through NaN,
        # non-finite scores or clearly inconsistent status fields.
        for name in ("reference_triangles", "candidate_triangles"):
            count = report.get(name)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("invalid triangle count")
        inventory = report.get("part_inventory")
        if inventory is not None:
            if not isinstance(inventory, dict) or set(inventory) != {
                "reference_object_count", "candidate_object_count",
                "reference_triangle_counts", "candidate_triangle_counts",
                "max_listed_per_side", "correspondence_verified",
                "identifies_changed_part", "notes",
            }:
                raise ValueError("invalid part inventory schema")
            if (type(inventory["max_listed_per_side"]) is not int
                    or inventory["max_listed_per_side"] != 32
                    or inventory["correspondence_verified"] is not False
                    or inventory["identifies_changed_part"] is not False
                    or inventory["notes"] !=
                    "Anonymous size-ranked inventory, not matched objects"):
                raise ValueError("invalid part inventory disclaimers")
            for side in ("reference", "candidate"):
                total = inventory[side + "_object_count"]
                counts = inventory[side + "_triangle_counts"]
                if (isinstance(total, bool) or not isinstance(total, int)
                        or total < 1 or not isinstance(counts, list)
                        or len(counts) != min(total, 32)
                        or any(isinstance(v, bool) or not isinstance(v, int)
                               or v < 0 or (payload["status"] == "review_only" and v > limit)
                               for v in counts)
                        or counts != sorted(counts, reverse=True)):
                    raise ValueError("invalid anonymous part counts")
                # A truncated, size-ranked inventory still bounds the total:
                # each unlisted object has at most the last listed face count.
                # Apply these constraints to skipped reports as well.
                listed = sum(counts)
                maximum = listed + (total - len(counts)) * counts[-1]
                if not listed <= report[side + "_triangles"] <= maximum:
                    raise ValueError("part inventory contradicts total triangles")
        hints = report.get("part_count_hints")
        if hints is not None:
            if inventory is None or not isinstance(hints, dict):
                raise ValueError("part hints require a valid inventory")
            expected_hints = count_based_part_hints(
                inventory["reference_triangle_counts"],
                inventory["candidate_triangle_counts"],
                reference_total=inventory["reference_object_count"],
                candidate_total=inventory["candidate_object_count"],
            )
            # Python equality aliases False/0 and True/1 (including in lists).
            # Canonical JSON preserves these scalar types while ignoring key order.
            if json.dumps(hints, sort_keys=True, allow_nan=False) != json.dumps(
                expected_hints, sort_keys=True, allow_nan=False
            ):
                raise ValueError("part hints contradict anonymous inventory")
        observation = report.get("surface_observation")
        if payload["status"] == "review_only":
            if observation not in (
                "sampled_difference_detected", "no_difference_observed_at_samples"
            ):
                raise ValueError("invalid surface observation")
            for group, metric in (
                ("fixed_surface", "symmetric_sampled_max"),
                ("adaptive_surface", "refined_symmetric_sampled_max"),
            ):
                value = report[group].get(metric)
                if (isinstance(value, bool) or not isinstance(value, (int, float))
                        or not math.isfinite(value) or value < 0):
                    raise ValueError("invalid surface metric")
            measured_difference = max(
                report["fixed_surface"]["symmetric_sampled_max"],
                report["adaptive_surface"]["refined_symmetric_sampled_max"],
            ) > 1e-6
            if measured_difference != (observation == "sampled_difference_detected"):
                raise ValueError("surface observation contradicts metrics")
            if any(not 1 <= report[name] <= limit for name in (
                "reference_triangles", "candidate_triangles"
            )):
                raise ValueError("measured triangle count is outside the safe range")
        else:
            if observation != "not_measured" or (
                "fixed_surface" in report or "adaptive_surface" in report
            ):
                raise ValueError("skipped evidence must not contain measurements")
            if (report.get("reason") == "triangle_limit" and
                    max(report["reference_triangles"], report["candidate_triangles"]) <= limit):
                raise ValueError("triangle-limit skip requires an over-limit scene")
        if parts:
            if report.get('profile') != profile:
                raise ValueError('invalid part review profile')
            global_report = dict(report, schema_version=2, profile='expanded_2048')
            global_report.pop('part_review', None)
            _validate_expanded_report(global_report)
            _validate_part_review(report)
        elif expanded:
            if 'part_review' in report:
                raise ValueError('unexpected part review')
            _validate_expanded_report(report)
        elif 'part_review' in report:
            raise ValueError('unexpected part review')
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError,
            OverflowError, RecursionError) as exc:
        if expanded:
            target.unlink(missing_ok=True)
        raise GLBSurfacePipelineError("Untrusted or corrupt Blender surface report") from exc
    return report


def _validate_expanded_report(report):
    """Check the explicitly selected schema-2 work evidence independently."""
    def integer(value, lo, hi):
        return type(value) is int and lo <= value <= hi

    def metric(value):
        return (type(value) in (int, float) and 0 <= value <= 4_000_000
                and math.isfinite(value))

    if (type(report.get("schema_version")) is not int or report["schema_version"] != 2
            or report.get("profile") != "expanded_2048" or
            type(report.get("triangle_limit_per_scene")) is not int or
            report["triangle_limit_per_scene"] != EXPANDED_MAX_TRIANGLES):
        raise ValueError("invalid expanded profile")
    ref, cand = report["reference_triangles"], report["candidate_triangles"]
    reason = report.get("reason")
    if report["status"] == "skipped" and reason == "triangle_limit":
        if any(k in report for k in ("work_budget", "bvh_build_count",
                                     "exhausted_counter", "stopped_stage")):
            raise ValueError("triangle limit cannot contain query evidence")
        return
    if not all(integer(n, 1, EXPANDED_MAX_TRIANGLES) for n in (ref, cand)):
        raise ValueError("expanded input count outside bounds")
    if type(report.get("bvh_build_count")) is not int or report["bvh_build_count"] != 2:
        raise ValueError("invalid BVH build count")
    def finite_tree(value):
        if isinstance(value, dict):
            return all(finite_tree(v) for v in value.values())
        if isinstance(value, list):
            return all(finite_tree(v) for v in value)
        return not isinstance(value, float) or math.isfinite(value)

    if not finite_tree(report):
        raise ValueError("nonfinite expanded report")
    budget = report.get("work_budget")
    limits = _SurfaceWorkBudget.LIMITS
    if (not isinstance(budget, dict) or set(budget) != {"limits", "used"}
            or not isinstance(budget["limits"], dict)
            or not isinstance(budget["used"], dict)
            or set(budget["limits"]) != set(limits)
            or set(budget["used"]) != set(limits)
            or any(type(budget["limits"][k]) is not int or budget["limits"][k] != v
                   or not integer(budget["used"][k], 0, v)
                   for k, v in limits.items())):
        raise ValueError("invalid work counters")
    used = budget["used"]
    fixed_samples = 24 * (ref + cand)
    maximum_samples = fixed_samples + COARSE_SAMPLES * (ref + cand) + (
        FINE_SAMPLES - COARSE_SAMPLES) * (
        min(ref, MAX_SUSPECT_FACES + EXPLORATION_FACES) +
        min(cand, MAX_SUSPECT_FACES + EXPLORATION_FACES))
    if (used["samples"] > maximum_samples or
            used["triangle_evaluations"] > used["samples"] * max(ref, cand) or
            used["node_visits"] > used["samples"] * (2 * max(ref, cand) - 1)):
        raise ValueError("work counters contradict geometry")
    if report["status"] == "skipped":
        key = report.get("exhausted_counter")
        stage = report.get("stopped_stage")
        if (reason != "work_budget" or type(key) is not str or key not in limits
                or used[key] != limits[key] or stage not in ("fixed", "adaptive")
                or (stage == "fixed" and used["samples"] > fixed_samples)
                or (stage == "adaptive" and used["samples"] < fixed_samples)):
            raise ValueError("invalid exhausted work evidence")
        return
    if any(k in report for k in ("reason", "exhausted_counter", "stopped_stage")):
        raise ValueError("completed work cannot claim exhaustion")
    samples = evaluations = 0
    directions = (("reference_to_candidate", ref, cand),
                  ("candidate_to_reference", cand, ref))
    for name in ("fixed_surface", "adaptive_surface"):
        group = report[name]
        fixed = name == "fixed_surface"
        if (type(group.get("schema_version")) is not int or group["schema_version"] != 2
                or group.get("status") != "review_only"
                or type(group.get("reference_triangles")) is not int
                or type(group.get("candidate_triangles")) is not int
                or group["reference_triangles"] != ref or group["candidate_triangles"] != cand):
            raise ValueError("invalid nested expanded schema")
        safety = group.get("safety")
        required = (("executes_addon", "modifies_source", "auto_approves",
                     "auto_applies_parameters", "uploads_private_geometry") if fixed else
                    ("user_addon_executed", "private_glb_uploaded", "source_modified",
                     "automatic_parameter_changes"))
        if not isinstance(safety, dict) or set(safety) != set(required) or any(
                safety[k] is not False for k in required):
            raise ValueError("invalid nested safety")
        flags = (("exact_surface_equivalence_verified", "watertight_solid_equivalence_verified",
                  "enclosed_cavities_verified") if fixed else
                 ("complete_surface_coverage", "exact_hausdorff_verified",
                  "enclosed_cavities_verified", "auto_approve"))
        if any(group.get(k) is not False for k in flags):
            raise ValueError("invalid nested proof flags")
        for direction, n, target in directions:
            row = group.get(direction)
            if not isinstance(row, dict):
                raise ValueError("invalid direction")
            if fixed:
                count = row.get("sample_count")
                if (not integer(count, 24*n, 24*n)
                        or not integer(row.get("brute_force_evaluations"), count*target, count*target)):
                    raise ValueError("invalid fixed samples")
                pairs = (("mean", "sampled_max"),)
            else:
                refined = row.get("refined_face_count")
                coarse = row.get("coarse_sample_count")
                extra = row.get("additional_sample_count")
                count = row.get("total_sample_count")
                if (not integer(refined, 0, min(n, MAX_SUSPECT_FACES+EXPLORATION_FACES))
                        or not integer(coarse, COARSE_SAMPLES*n, COARSE_SAMPLES*n)
                        or not integer(extra, refined*(FINE_SAMPLES-COARSE_SAMPLES),
                                       refined*(FINE_SAMPLES-COARSE_SAMPLES))
                        or not integer(count, coarse+extra, coarse+extra)):
                    raise ValueError("invalid adaptive samples")
                pairs = (("coarse_mean", "coarse_sampled_max"),
                         ("refined_mean", "refined_sampled_max"))
            for mean, worst in pairs:
                if (not metric(row.get(mean)) or not metric(row.get(worst))
                        or row[mean] > row[worst]):
                    raise ValueError("invalid directional distance")
            performed = row.get("triangle_distance_evaluations")
            if not integer(performed, count, count*target):
                raise ValueError("invalid precise evaluation count")
            samples += count
            evaluations += performed
        for mean, worst in pairs:
            rows = [group[direction] for direction, _, _ in directions]
            prefix = "" if fixed else mean.split("_")[0] + "_"
            sm, sx = prefix+"symmetric_mean", prefix+"symmetric_sampled_max"
            if (not metric(group.get(sm)) or not metric(group.get(sx))
                    or group[sm] != round((rows[0][mean]+rows[1][mean])*0.5, 7)
                    or group[sx] != max(row[worst] for row in rows)):
                raise ValueError("invalid symmetric distances")
    if (used["samples"] != samples or used["triangle_evaluations"] != evaluations
            or used["node_visits"] < samples):
        raise ValueError("work counters contradict measurements")


def _validate_part_review(report):
    """Validate schema-3 anonymous part evidence; no geometry in parent report."""
    def integer(x, lo, hi):
        return type(x) is int and lo <= x <= hi

    def number(x, lo=0, hi=4_000_000):
        return type(x) in (int, float) and lo <= x <= hi and math.isfinite(x)

    def same_types(a, b):
        return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(
            b, sort_keys=True, allow_nan=False)

    header = _part_review_header()
    part = report.get("part_review")
    inventory = report.get("part_inventory")
    if (not isinstance(part, dict) or not isinstance(inventory, dict) or
            any(not same_types(part.get(k), v) for k, v in header.items())):
        raise ValueError("invalid part review header")
    if part.get("status") == "skipped":
        if set(part) != set(header) | {"status", "reason"}:
            raise ValueError("skipped part review contains unexpected evidence")
        reason = part["reason"]
        if report["status"] != "review_only":
            if reason != "global_surface_not_measured":
                raise ValueError("invalid global skip reason")
        elif reason == "part_limit":
            if max(inventory["reference_object_count"], inventory["candidate_object_count"]) <= MAX_PARTS:
                raise ValueError("invalid part limit skip")
        elif reason == "empty_part":
            for side in ("reference", "candidate"):
                if inventory[side + "_object_count"] <= 32 and 0 in inventory[side + "_triangle_counts"]:
                    break
                if inventory[side + "_object_count"] > 32 and (
                        report[side + "_triangles"] < inventory[side + "_object_count"] or
                        inventory[side + "_triangle_counts"][-1] == 0):
                    break
            else:
                # Truncated inventory cannot always independently establish empty parts.
                if max(inventory["reference_object_count"], inventory["candidate_object_count"]) <= 32:
                    raise ValueError("invalid empty part skip")
        elif reason not in ("invalid_geometry", "invalid_part_layout"):
            raise ValueError("unknown part skip reason")
        return
    if part.get("status") != "review_only" or report["status"] != "review_only":
        raise ValueError("part review requires measured global surface")
    keys = {"status", "reference_triangle_counts", "candidate_triangle_counts",
            "reference_parts", "unpaired_candidate_part_ids", "pair_attempts",
            "bvh_build_count", "boundary_comparison_reservation", "work_budget"}
    if set(part) != set(header) | keys:
        raise ValueError("unexpected part review evidence")
    counts = []
    for side in ("reference", "candidate"):
        values = part[side + "_triangle_counts"]
        if (not isinstance(values, list) or not 1 <= len(values) <= MAX_PARTS
                or len(values) != inventory[side + "_object_count"]
                or any(not integer(x, 1, EXPANDED_MAX_TRIANGLES) for x in values)
                or sum(values) != report[side + "_triangles"]
                or sorted(values, reverse=True)[:32] != inventory[side + "_triangle_counts"]):
            raise ValueError("part order inventory contradiction")
        counts.append(values)
    ref, cand = counts
    candidate_ids = [f"part_{j+1:03d}" for j in range(len(cand))]
    rows = part["reference_parts"]
    limits = _SurfaceWorkBudget.LIMITS
    budget = part["work_budget"]
    if (not isinstance(budget, dict) or set(budget) != {"limits", "used"}
            or not same_types(budget["limits"], limits)
            or not isinstance(budget["used"], dict) or set(budget["used"]) != set(limits)
            or any(not integer(budget["used"][k], 0, v) for k, v in limits.items())
            or not integer(part["boundary_comparison_reservation"], 0, PART_BOUNDARY_RESERVATION_LIMIT)
            or not integer(part["pair_attempts"], 0, PART_PAIR_LIMIT)
            or not integer(part["bvh_build_count"], 0, len(ref)+len(cand))
            or not isinstance(rows, list) or len(rows) != len(ref)):
        raise ValueError("invalid part review budget or layout")
    topology_reasons = {
        "boundary_edge_count_mismatch", "nonmanifold_edge_count_mismatch",
        "weld_collapsed_triangles_observed", "boundary_layout_budget_exceeded",
        "boundary_spatial_layout_mismatch", "boundary_component_count_mismatch",
        "cumulative_boundary_budget_exceeded",
    }
    used = set()
    spatial_used = set()
    expected_work = dict.fromkeys(limits, 0)
    attempted = 0
    exhausted = False
    expected_trees = set()
    for i, row in enumerate(rows):
        if (not isinstance(row, dict) or set(row) != {
                "reference_part_id", "status", "candidate_part_ids", "normalized_score",
                "topology_review_required", "topology_review_reasons", "spatial_status",
                "observations", "surface_review_reasons"}
                or row["reference_part_id"] != f"part_{i+1:03d}"
                or row["spatial_status"] not in ("suggested", "ambiguous", "unmatched")
                or not number(row["normalized_score"], hi=2)):
            raise ValueError("invalid part row")
        ids = row["candidate_part_ids"]
        observations = row["observations"]
        topo = row["topology_review_reasons"]
        if (not isinstance(ids, list) or len(ids) > 2 or
                any(not isinstance(j, str) or j not in candidate_ids for j in ids)
                or len(set(ids)) != len(ids)
                or not isinstance(observations, list) or len(observations) != len(ids)
                or not isinstance(topo, list) or
                any(not isinstance(x, str) or x not in topology_reasons for x in topo)
                or len(set(topo)) != len(topo)
                or row["topology_review_required"] is not bool(topo)):
            raise ValueError("invalid candidate or topology evidence")
        if row["spatial_status"] == "suggested" and (
                len(ids) != 1 or topo or row["normalized_score"] > MAX_SCORE):
            raise ValueError("invalid spatial suggestion")
        if row["spatial_status"] == "suggested":
            if ids[0] in spatial_used:
                raise ValueError("duplicate spatial suggestion")
            spatial_used.add(ids[0])
        if row["spatial_status"] == "unmatched" and ids:
            raise ValueError("unmatched row cannot have candidates")
        if row["spatial_status"] == "ambiguous" and not ids:
            raise ValueError("ambiguous row requires candidate")
        surface_reasons = []
        difference = unmeasured = False
        for cid, obs in zip(ids, observations):
            if not isinstance(obs, dict) or obs.get("candidate_part_id") != cid:
                raise ValueError("candidate observation order mismatch")
            j = candidate_ids.index(cid)
            n, m = ref[i], cand[j]
            work = obs.get("work")
            if obs.get("status") == "not_measured":
                unmeasured = True
                if obs.get("reason") != "cumulative_work_budget":
                    raise ValueError("invalid missing measurement")
                if work is None:
                    if set(obs) != {"candidate_part_id", "status", "reason"} or not (
                            exhausted or attempted >= PART_PAIR_LIMIT):
                        raise ValueError("unexplained skipped pair")
                    continue
                if (set(obs) != {"candidate_part_id", "status", "reason", "exhausted_counter", "work"}
                        or exhausted or obs.get("exhausted_counter") not in limits):
                    raise ValueError("invalid exhausted pair")
                exhausted = True
            elif obs.get("status") == "measured":
                if (set(obs) != {"candidate_part_id", "status", "local_scale",
                                 "reference_to_candidate", "candidate_to_reference",
                                 "relative_sampled_max", "surface_difference_observed", "work"}
                        or exhausted or not number(obs["local_scale"]) or obs["local_scale"] <= 0):
                    raise ValueError("invalid measured pair")
                samples = evaluations = 0
                worst = 0
                for key, source, target in (("reference_to_candidate", n, m),
                                            ("candidate_to_reference", m, n)):
                    v = obs[key]
                    count = 24*source
                    if (not isinstance(v, dict) or set(v) != {"mean", "sampled_max",
                            "sample_count", "triangle_distance_evaluations", "brute_force_evaluations"}
                            or not number(v["mean"]) or not number(v["sampled_max"])
                            or v["mean"] > v["sampled_max"]
                            or not integer(v["sample_count"], count, count)
                            or not integer(v["triangle_distance_evaluations"], count, count*target)
                            or not integer(v["brute_force_evaluations"], count*target, count*target)):
                        raise ValueError("invalid directed pair metrics")
                    samples += count
                    evaluations += v["triangle_distance_evaluations"]
                    worst = max(worst, v["sampled_max"])
                rel = worst / obs["local_scale"]
                diff = worst > max(1e-6, obs["local_scale"] * PART_RELATIVE_REVIEW_THRESHOLD)
                if (not number(obs["relative_sampled_max"], hi=1e15)
                        or obs["relative_sampled_max"] != rel
                        or obs["surface_difference_observed"] is not diff):
                    raise ValueError("inconsistent local difference")
                difference = difference or diff
            else:
                raise ValueError("unknown pair state")
            if (not isinstance(work, dict) or set(work) != set(limits)
                    or any(not integer(work[k], 0, limits[k]) for k in limits)
                    or work["samples"] > 24*(n+m)
                    or work["triangle_evaluations"] > work["samples"]*max(n,m)
                    or work["node_visits"] > work["samples"]*(2*max(n,m)-1)):
                raise ValueError("invalid pair work")
            attempted += 1
            expected_trees.add((1,j))
            if obs["status"] == "measured":
                expected_trees.add((0,i))
                if (work["samples"] != samples or work["triangle_evaluations"] != evaluations
                        or work["node_visits"] < samples):
                    raise ValueError("measured pair work contradicts metrics")
            for k in limits:
                expected_work[k] += work[k]
            if obs["status"] == "not_measured":
                if expected_work[obs["exhausted_counter"]] != limits[obs["exhausted_counter"]]:
                    raise ValueError("claimed exhaustion not at limit")
                # Reverse target tree may or may not have been built.
                if work["samples"] > 24*n:
                    expected_trees.add((0,i))
        if unmeasured:
            surface_reasons.append("candidate_surface_not_measured")
        if difference:
            surface_reasons.append("candidate_surface_difference")
        status = row["spatial_status"]
        if status == "suggested" and surface_reasons:
            status = "ambiguous"
        if row["status"] != status or row["surface_review_reasons"] != surface_reasons:
            raise ValueError("invalid part promotion or demotion")
        if status == "suggested":
            if ids[0] in used:
                raise ValueError("duplicate suggested candidate")
            used.add(ids[0])
    if (part["pair_attempts"] != attempted or budget["used"] != expected_work
            or not len(expected_trees) <= part["bvh_build_count"] <= len(expected_trees)+int(exhausted)
            or part["unpaired_candidate_part_ids"] != [j for j in candidate_ids if j not in used]):
        raise ValueError("part aggregate evidence contradiction")
