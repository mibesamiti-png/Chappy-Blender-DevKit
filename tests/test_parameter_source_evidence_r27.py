"""Synthetic R27 reducer controls; never native measurement evidence."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from cbdk.parameter_source_evidence_r27 import (
    CASE, PROPERTY, SOURCE_SHA256, CANDIDATE_SHA256, BYTE_OFFSET, STAGES,
    SPHERE, CUBE, RUN_FLAGS, reduce_source_evidence,
)

RUN = "1" * 32
PRIVATE = "private/path/never-copy"
ROOT = Path(__file__).resolve().parents[1]


def identity(version="4.4.3"):
    return dict(case_id=CASE, run_id=RUN, blender_version=version,
                source_sha256=SOURCE_SHA256, candidate_sha256=CANDIDATE_SHA256,
                property=PROPERTY)


def mesh(digest, dimension):
    return dict(mesh_vertex_count=32, mesh_polygon_count=24,
                mesh_coordinate_sha256=digest*64, world_dimensions=[dimension]*3)


def measurement(digest, *, changed=False):
    generated = {SPHERE: mesh("b" if changed else "a", 2.3 if changed else 1.5),
                 CUBE: mesh("c", 2.0)}
    imported = {SPHERE: mesh("e" if changed else "d", 2.3 if changed else 1.5),
                CUBE: mesh("f", 2.0)}
    return dict(glb_sha256=digest*64, generated_mesh=generated, imported_glb_mesh=imported)


def observations(version="4.4.3"):
    key = identity(version)
    diff = {**key, "before": .75, "after": 1.15, "old_token": "0.75",
            "new_token": "1.15", "byte_offset": BYTE_OFFSET,
            "single_diff_verified": True, "ast_diff_verified": True,
            "restored_sha256": SOURCE_SHA256}
    measured = {stage: measurement(digest, changed=stage=="candidate")
                for stage, digest in zip(STAGES, "123")}
    references = {"baseline": measurement("4"), "sphere_radius_changed": measurement("5", changed=True)}
    native = {**key, **dict.fromkeys(RUN_FLAGS, True), "restored_copy_sha256": SOURCE_SHA256,
              "reference_glb_sha256": {k:v["glb_sha256"] for k,v in references.items()},
              "stages": [{**key, **copy.deepcopy(measured[stage]), "stage": stage,
                          "actual_source_sha256": CANDIDATE_SHA256 if stage=="candidate" else SOURCE_SHA256,
                          "sphere_radius": 1.15 if stage=="candidate" else .75, "bevel_width": .08,
                          "registered": True, "cleanup_verified": True} for stage in STAGES]}
    return diff, native, measured, references


def reduce(diff, native, measured, references, version="4.4.3", **overrides):
    expected = dict(run_id=RUN, blender_version=version, source_sha256=SOURCE_SHA256,
                    candidate_sha256=CANDIDATE_SHA256)
    return reduce_source_evidence(diff, native, measured=measured, references=references,
                                  **{**expected, **overrides})


class SourceEvidenceTests(unittest.TestCase):
    def blocked(self, report, reason=None, status=None):
        self.assertFalse(report["same_fixture_change_restoration_verified"])
        self.assertFalse(any(report["safety"].values()))
        self.assertNotIn(PRIVATE, json.dumps(report))
        if reason:
            self.assertIn(reason, report["reason_codes"])
        if status:
            self.assertEqual(report["status"], status)

    def test_independent_pinned_bytes_and_reverse(self):
        path = ROOT / "fixtures/cbdk_parameter_experiment.py"
        checkout = path.read_bytes()
        source = checkout
        # Windows Git checkout may materialize the exact tracked LF fixture
        # with CRLF. Only this static test can recover canonical test bytes;
        # the actual runtime reducer must still reject the raw CRLF digest.
        crlf_sha = "eec6968b7cb5208e0af92279b7b32dc0c8d617ebad6d1cdbb5ca39cc64d1918f"
        if hashlib.sha256(checkout).hexdigest() == crlf_sha:
            source = checkout.replace(b"\r\n", b"\n")
            self.assertEqual(source.replace(b"\n", b"\r\n"), checkout)
        self.assertEqual(hashlib.sha256(source).hexdigest(), SOURCE_SHA256)
        self.assertEqual(hashlib.sha256(source.replace(b"\n", b"\r\n")).hexdigest(), crlf_sha)
        self.blocked(reduce(*observations(), source_sha256=crlf_sha),
                     "source_digest_mismatch", "rejected")
        self.assertEqual(path.read_bytes(), checkout)
        self.assertEqual(source.count(b"0.75"), 1)
        self.assertEqual(source[BYTE_OFFSET:BYTE_OFFSET+4], b"0.75")
        candidate = source[:BYTE_OFFSET] + b"1.15" + source[BYTE_OFFSET+4:]
        self.assertEqual(hashlib.sha256(candidate).hexdigest(), CANDIDATE_SHA256)
        self.assertEqual(candidate[:BYTE_OFFSET] + b"0.75" + candidate[BYTE_OFFSET+4:], source)

    def test_fixed_matrix_geometry_not_glb_byte_equality(self):
        for version in ("4.4.3", "4.5.15", "5.2.1"):
            args = observations(version)
            before = copy.deepcopy(args)
            self.assertEqual(len({v["glb_sha256"] for v in (*args[2].values(), *args[3].values())}), 5)
            report = reduce(*args, version)
            self.assertEqual(report["status"], "verified_fixed_observations")
            self.assertTrue(report["same_fixture_change_restoration_verified"])
            self.assertFalse(any(report["safety"].values()))
            self.assertEqual(args, before)

    def test_missing_never_passes(self):
        for index in range(4):
            args = list(observations()); args[index] = None
            self.blocked(reduce(*args), status="incomplete")
        for index in range(3):
            a, n, m, r = observations()
            del n["stages"][index]
            self.blocked(reduce(a,n,m,r), "stage_missing", "incomplete")
        a,n,m,r = observations(); del m["restored"]
        self.blocked(reduce(a,n,m,r), "parent_measurement_missing", "incomplete")
        a,n,m,r = observations(); del r["baseline"]
        self.blocked(reduce(a,n,m,r), "reference_missing", "incomplete")

    def test_fixed_diff_and_restoration(self):
        for key,value in (("before", True), ("after", 1.16), ("old_token", "0.08"),
                          ("new_token", PRIVATE), ("byte_offset", 571),
                          ("byte_offset", float(BYTE_OFFSET)), ("restored_sha256", "a"*64)):
            a,n,m,r = observations(); a[key]=value
            self.blocked(reduce(a,n,m,r), "fixed_diff_mismatch", "rejected")
        a,n,m,r = observations(); a["single_diff_verified"]=False
        self.blocked(reduce(a,n,m,r), "single_change_unverified", "unverified")
        a,n,m,r = observations(); a["ast_diff_verified"]=False
        self.blocked(reduce(a,n,m,r), "single_change_unverified", "unverified")
        a,n,m,r = observations(); n["restored_copy_sha256"]=CANDIDATE_SHA256
        self.blocked(reduce(a,n,m,r), "restoration_mismatch", "rejected")

    def test_independent_identity_and_stage_source(self):
        for key,value in (("case_id", PRIVATE), ("run_id", "2"*32), ("blender_version", "5.2.1"),
                          ("source_sha256","a"*64), ("candidate_sha256","b"*64), ("property","bevel_width")):
            for index in (0,1,2):
                a,n,m,r = observations()
                (a,n,n["stages"][1])[index][key]=value
                self.blocked(reduce(a,n,m,r), "identity_mismatch", "rejected")
        a,n,m,r = observations()
        self.blocked(reduce(a,n,m,r, candidate_sha256="b"*64), "source_digest_mismatch", "rejected")
        n["stages"][2]["actual_source_sha256"]=CANDIDATE_SHA256
        self.blocked(reduce(a,n,m,r), "stage_source_mismatch", "rejected")

    def test_extra_duplicate_malformed_and_overclaim(self):
        changes = (
            lambda a,n,m,r:n["stages"].append(n["stages"][0]),
            lambda a,n,m,r:n["stages"].__setitem__(1,n["stages"][0]),
            lambda a,n,m,r:n["stages"][0].update(stage=PRIVATE),
            lambda a,n,m,r:n["stages"][0].update(stage=[]),
            lambda a,n,m,r:a.update(auto_approves=True),
            lambda a,n,m,r:n.update(optimal_value_verified=True),
            lambda a,n,m,r:n["stages"][0].update(cleanup_verified=1),
            lambda a,n,m,r:n["stages"][0].update(sphere_radius=True),
            lambda a,n,m,r:n["stages"][0].update(bevel_width=float("nan")),
            lambda a,n,m,r:n.update(isolated_copy_verified=1),
            lambda a,n,m,r:n["stages"][0]["generated_mesh"][SPHERE].update(mesh_vertex_count=True),
            lambda a,n,m,r:n["stages"][0]["generated_mesh"][SPHERE].update(world_dimensions=[1,2,False]),
            lambda a,n,m,r:n["stages"][0]["generated_mesh"][SPHERE].update(mesh_coordinate_sha256=PRIVATE),
            lambda a,n,m,r:n["stages"][0]["generated_mesh"].update(extra=mesh("a",1)),
            lambda a,n,m,r:m["original"].update(glb_sha256="A"*64),
            lambda a,n,m,r:r["baseline"].update(glb_sha256=PRIVATE),
        )
        for change in changes:
            args=observations(); change(*args)
            self.blocked(reduce(*args), status="rejected")

    def test_failed_observation_or_wrong_defaults(self):
        for flag in RUN_FLAGS:
            a,n,m,r=observations(); n[flag]=False
            self.blocked(reduce(a,n,m,r), flag+"_false", "unverified")
        for flag,reason in (("registered","registration_unverified"),("cleanup_verified","cleanup_unverified")):
            a,n,m,r=observations(); n["stages"][1][flag]=False
            self.blocked(reduce(a,n,m,r), reason,"unverified")
        for key,value in (("sphere_radius",.75),("bevel_width",.35)):
            a,n,m,r=observations(); n["stages"][1][key]=value
            self.blocked(reduce(a,n,m,r), "rna_default_mismatch","unverified")

    def test_measurement_binding_and_reference_digest(self):
        a,n,m,r=observations(); n["stages"][1]["glb_sha256"]="9"*64
        self.blocked(reduce(a,n,m,r), "measurement_mismatch","rejected")
        a,n,m,r=observations(); m["original"]["generated_mesh"][SPHERE]["mesh_vertex_count"]+=1
        self.blocked(reduce(a,n,m,r), "measurement_mismatch","rejected")
        a,n,m,r=observations(); n["reference_glb_sha256"]["baseline"]="9"*64
        self.blocked(reduce(a,n,m,r), "reference_digest_mismatch","rejected")

    def test_geometry_negative_controls_even_when_parent_agrees(self):
        for key in ("generated_mesh","imported_glb_mesh"):
            for stage,object_name,replacement,reason in (
                ("candidate",SPHERE,mesh("a" if key=="generated_mesh" else "d",1.5),"target_effect_unverified"),
                ("candidate",CUBE,mesh("9",2.1),"unrelated_geometry_changed"),
                ("restored",SPHERE,mesh("9",1.7),"restored_geometry_mismatch"),
            ):
                a,n,m,r=observations()
                m[stage][key][object_name]=replacement
                next(row for row in n["stages"] if row["stage"]==stage)[key][object_name]=copy.deepcopy(replacement)
                self.blocked(reduce(a,n,m,r), reason,"unverified")
            a,n,m,r=observations()
            r["sphere_radius_changed"][key][SPHERE]["mesh_polygon_count"]+=1
            self.blocked(reduce(a,n,m,r), "fixed_reference_geometry_mismatch","unverified")


if __name__=="__main__":
    unittest.main()
