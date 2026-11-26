"""Regression tests for AST-only parameter inventory and review-plan linking."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cbdk.__main__ import main
from cbdk.glb_property_map import (
    MAX_SOURCE_BYTES, PropertyMappingError, _inventory,
    map_repair_plan_properties, map_properties_from_file, write_local_mapping,
)


def review_plan(candidates=("ball_diameter", "socket_opening_diameter", "shaft_diameter")):
    return {
        "schema_version": 1,
        "kind": "cbdk_glb_repair_plan",
        "status": "review_only",
        "recommendation_count": 1,
        "recommendations": [{
            "target": "Ball",
            "suspected_category": "part_size_parameter",
            "requires_human_parameter_mapping": True,
            "possible_parameter_families": list(candidates),
        }],
        "unmapped_difference_codes": [],
        "safety": {
            "edits_code": False, "applies_parameters": False,
            "runs_untrusted_addons": False, "auto_approves": False,
            "auto_merges": False, "private_geometry_required": False,
        },
    }


class GLBPropertyMapTests(unittest.TestCase):
    def test_shadowed_constructor_aliases_are_not_property_evidence(self):
        for source in (
            'from bpy.props import FloatProperty\nFloatProperty = fake\nclass P:\n x: FloatProperty()\n',
            'import bpy as b\nif condition:\n b = fake\nclass P:\n x: b.props.FloatProperty()\n',
            'from bpy import props as p\nclass P:\n p = fake\n x: p.FloatProperty()\n',
            'from bpy.props import FloatProperty as F\ndef F(): pass\nclass P:\n x: F()\n',
        ):
            with self.subTest(source=source):
                path = self.make_source(source)
                self.assertEqual(_inventory(path, file_index=1), [])

    def test_unrelated_nested_binding_does_not_hide_module_constructor(self):
        path = self.make_source('from bpy.props import FloatProperty as F\n'
                                'def helper():\n F = fake\n'
                                'class P:\n x: F()\n')
        self.assertEqual(len(_inventory(path, file_index=1)), 1)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def make_source(self, content, name="private_input.py"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_ast_annotated_float_property_matches_exact_only(self):
        source = self.make_source(
            "from bpy.props import FloatProperty\n"
            "class Settings:\n"
            "    ball_diameter: FloatProperty(name='Ball Diameter', default=2.0)\n")
        out = map_repair_plan_properties(review_plan(), [source])
        self.assertEqual(out["source_files_scanned"], 1)
        self.assertEqual(out["static_property_declarations_found"], 1)
        row = out["recommendations"][0]
        self.assertTrue(row["has_declared_name_match"])
        match = row["exact_name_matches"][0]
        self.assertEqual(match["candidate_family"], "ball_diameter")
        self.assertEqual(match["match"], "exact_declaration_name_only")
        self.assertEqual(match["declarations"][0]["class_name"], "Settings")
        self.assertEqual(match["declarations"][0]["property_constructor"], "FloatProperty")
        self.assertEqual(match["declarations"][0]["line"], 3)
        self.assertEqual(row["unmatched_parameter_families"],
                         ["socket_opening_diameter", "shaft_diameter"])
        self.assertFalse(row["validated_geometry_effect"])
        self.assertFalse(out["safety"]["source_executed"])

    def test_bpy_props_dot_constructor(self):
        source = self.make_source(
            "import bpy\nclass Props:\n"
            "    ball_diameter = bpy.props.FloatProperty(default=2.0)\n")
        out = map_repair_plan_properties(review_plan(("ball_diameter",)), [source])
        self.assertEqual(out["static_property_declarations_found"], 1)
        self.assertEqual(out["recommendations"][0]["exact_name_matches"][0]
                         ["declarations"][0]["property_constructor"], "FloatProperty")

    def test_bpy_alias_and_from_bpy_props_alias(self):
        source = self.make_source(
            "import bpy as blender\nfrom bpy import props as property_api\n"
            "class Config:\n"
            "    ball_diameter: blender.props.FloatProperty(default=2)\n"
            "    shaft_diameter: property_api.FloatProperty(default=3)\n")
        out = map_repair_plan_properties(review_plan(), [source])
        self.assertEqual(out["static_property_declarations_found"], 2)
        self.assertEqual(len(out["recommendations"][0]["exact_name_matches"]), 2)

    def test_from_bpy_props_named_alias(self):
        source = self.make_source(
            "from bpy.props import FloatProperty as FP\n"
            "class Config:\n    ball_diameter: FP(default=2)\n")
        out = map_repair_plan_properties(review_plan(("ball_diameter",)), [source])
        self.assertEqual(out["static_property_declarations_found"], 1)
        self.assertEqual(out["recommendations"][0]["exact_name_matches"][0]
                         ["declarations"][0]["property_constructor"], "FloatProperty")

    def test_plain_unimported_property_function_is_not_trusted(self):
        source = self.make_source(
            "def FloatProperty(**kwargs):\n    return None\n"
            "class Settings:\n    ball_diameter: FloatProperty(default=3)\n")
        out = map_repair_plan_properties(review_plan(), [source])
        self.assertEqual(out["static_property_declarations_found"], 0)

    def test_function_locals_and_instance_fields_are_not_class_declarations(self):
        source = self.make_source(
            "import bpy\n"
            "def create():\n    ball_diameter = bpy.props.FloatProperty(default=5)\n"
            "class Settings:\n"
            "    def __init__(self):\n"
            "        self.ball_diameter = bpy.props.FloatProperty(default=8)\n")
        out = map_repair_plan_properties(review_plan(), [source])
        self.assertEqual(out["static_property_declarations_found"], 0)

    def test_no_execution_of_malicious_top_level_code(self):
        marker = self.root / "should_never_exist.txt"
        source = self.make_source(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('BAD')\n"
            "raise RuntimeError('MUST NOT EXECUTE')\n"
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty(default=2)\n")
        out = map_repair_plan_properties(review_plan(), [source])
        self.assertEqual(out["static_property_declarations_found"], 1)
        self.assertFalse(marker.exists())

    def test_private_source_content_or_paths_never_enter_report(self):
        sensitive = "PRIVATE_VALUE_DO_NOT_LEAK"
        src = self.make_source(
            "from bpy.props import StringProperty\n"
            "class Secrets:\n"
            "    ball_diameter: StringProperty(default='PRIVATE_VALUE_DO_NOT_LEAK')\n",
            "private_project/secret_journal.py")
        report = map_repair_plan_properties(review_plan(("ball_diameter",)), [src])
        encoded = json.dumps(report)
        self.assertNotIn(sensitive, encoded)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn("secret_journal.py", encoded)
        self.assertIn("source_1.py", encoded)

    def test_renamed_properties_remain_unmatched_not_verified(self):
        source = self.make_source(
            "from bpy.props import FloatProperty\n"
            "class Props:\n    diameter_ball: FloatProperty(default=3)\n")
        output = map_repair_plan_properties(review_plan(("ball_diameter",)), [source])
        self.assertFalse(output["recommendations"][0]["has_declared_name_match"])
        self.assertEqual(output["recommendations"][0]["exact_name_matches"], [])

    def test_multifile_and_duplicate_declaration_are_reported_as_ambiguous(self):
        a = self.make_source(
            "from bpy.props import FloatProperty\n"
            "class A:\n    ball_diameter: FloatProperty()\n", "a.py")
        b = self.make_source(
            "from bpy.props import FloatProperty\n"
            "class B:\n    ball_diameter: FloatProperty()\n", "b.py")
        result = map_repair_plan_properties(review_plan(("ball_diameter",)), [a, b])
        declarations = result["recommendations"][0]["exact_name_matches"][0]["declarations"]
        self.assertEqual(len(declarations), 2)
        self.assertEqual({x["source_label"] for x in declarations}, {"source_1.py", "source_2.py"})
        self.assertTrue(all(x["registered_in_blender"] == "not_checked" for x in declarations))

    def test_other_property_types_recognized(self):
        source = self.make_source(
            "from bpy.props import EnumProperty, BoolProperty, IntVectorProperty\n"
            "class Options:\n"
            "    split_mode: EnumProperty(items=[])\n"
            "    is_visible: BoolProperty(default=True)\n"
            "    segment_count: IntVectorProperty(size=3)\n")
        result = map_repair_plan_properties(review_plan(("split_mode", "segment_count")), [source])
        self.assertEqual(result["static_property_declarations_found"], 3)
        self.assertEqual(len(result["recommendations"][0]["exact_name_matches"]), 2)

    def test_static_parse_syntax_error_refused(self):
        source = self.make_source("not valid Python code !!!")
        with self.assertRaises(PropertyMappingError):
            map_repair_plan_properties(review_plan(), [source])

    def test_source_file_size_and_extension_checked(self):
        large = self.make_source("x" * (MAX_SOURCE_BYTES + 2))
        with self.assertRaisesRegex(PropertyMappingError, "size"):
            map_repair_plan_properties(review_plan(), [large])
        text_file = self.make_source("class Settings: pass\n", "data.txt")
        with self.assertRaises(PropertyMappingError):
            map_repair_plan_properties(review_plan(), [text_file])

    def test_symlinked_source_is_rejected(self):
        source = self.make_source("from bpy.props import FloatProperty\n")
        link = self.root / "link.py"
        try:
            link.symlink_to(source)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(PropertyMappingError):
            map_repair_plan_properties(review_plan(), [link])

    def test_plan_inconsistent_count_rejected(self):
        plan = review_plan()
        plan["recommendation_count"] = 2
        source = self.make_source("class Empty: pass")
        with self.assertRaises(PropertyMappingError):
            map_repair_plan_properties(plan, [source])

    def test_approval_flags_cannot_be_forged(self):
        source = self.make_source("class Empty: pass")
        for key in ("edits_code", "applies_parameters", "auto_approves",
                    "private_geometry_required", "runs_untrusted_addons", "auto_merges"):
            plan = review_plan()
            plan["safety"][key] = True
            with self.subTest(key=key), self.assertRaises(PropertyMappingError):
                map_repair_plan_properties(plan, [source])

    def test_candidate_identifier_validation(self):
        source = self.make_source("class Empty: pass")
        for candidate in ("a.b", "../secret", "bad\nname", "x" * 130, 123, None):
            with self.subTest(candidate=repr(candidate)):
                with self.assertRaises(PropertyMappingError):
                    map_repair_plan_properties(review_plan((candidate,)), [source])

    def test_empty_sources_and_limits_rejected(self):
        source = self.make_source("class Empty: pass")
        with self.assertRaises(PropertyMappingError):
            map_repair_plan_properties(review_plan(), [])
        with self.assertRaises(PropertyMappingError):
            map_repair_plan_properties(review_plan(), [source] * 17)

    def test_duplicate_json_keys_refused(self):
        file = self.root / "plan.json"
        json_text = json.dumps(review_plan())
        file.write_text(json_text[:-1] + ', "status":"review_only"}', encoding="utf-8")
        source = self.make_source("class Empty: pass")
        with self.assertRaisesRegex(PropertyMappingError, "Duplicate"):
            map_properties_from_file(file, [source], root=self.root)

    def test_write_only_ignored_local_report_without_overwriting(self):
        src = self.make_source(
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    ball_diameter: FloatProperty(default=3)\n")
        plan = self.root / "plan.json"
        plan.write_text(json.dumps(review_plan()), encoding="utf-8")
        out = "reports/latest/property_map.json"
        report = map_properties_from_file(plan, [src], out, root=self.root)
        saved = self.root / out
        self.assertEqual(json.loads(saved.read_text("utf-8")), report)
        self.assertEqual(report["kind"], "cbdk_glb_property_mapping")
        self.assertEqual(report["recommendations"][0]["exact_name_matches"][0]
                         ["candidate_family"], "ball_diameter")
        with self.assertRaises(FileExistsError):
            map_properties_from_file(plan, [src], out, root=self.root)
        self.assertFalse((self.root / "addon_generated.py").exists())

    def test_output_absolute_and_traversal_rejected(self):
        result = {"kind": "cbdk_glb_property_mapping"}
        for dest in ("/tmp/mapping.json", "../mapping.json", "reports/latest/../../../escape.json",
                     "reports/ci/mapping.json", "dist/mapping.json"):
            with self.subTest(dest=dest), self.assertRaises(PropertyMappingError):
                write_local_mapping(result, dest, root=self.root)

    def test_output_symlink_escape_refused(self):
        external = self.root / "external"
        external.mkdir()
        rep = self.root / "reports"
        rep.mkdir()
        try:
            (rep / "latest").symlink_to(external, target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(PropertyMappingError):
            write_local_mapping({"kind": "cbdk_glb_property_mapping"},
                                "reports/latest/output.json", root=self.root)
        self.assertEqual(list(external.iterdir()), [])

    def test_no_matches_does_not_claim_a_fix(self):
        source = self.make_source(
            "from bpy.props import FloatProperty\n"
            "class Settings:\n    other_thing: FloatProperty()\n")
        report = map_repair_plan_properties(review_plan(("socket_opening_diameter",)), [source])
        self.assertEqual(report["recommendations"][0]["unmatched_parameter_families"],
                         ["socket_opening_diameter"])
        self.assertFalse(report["recommendations"][0]["validated_geometry_effect"])
        self.assertEqual(report["next_action"], "review_exact_declarations_and_actual_blender_registration")

    def test_cli_wiring_no_implicit_source_scan(self):
        with patch("cbdk.__main__.map_properties_from_file", return_value={
            "kind": "cbdk_glb_property_mapping", "source_files_scanned": 1
        }) as mapped:
            import contextlib
            import io
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["glb-map-properties", "reports/latest/repair_plan.json",
                               "--source", "input_sources_private/addon.py",
                               "--output", "reports/latest/map.json"])
        self.assertEqual(result, 0)
        mapped.assert_called_once_with("reports/latest/repair_plan.json",
                                       ["input_sources_private/addon.py"],
                                       "reports/latest/map.json")
        self.assertIn("cbdk_glb_property_mapping", output.getvalue())




class R26FixedParameterStaticTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        from cbdk.glb_parameter_static_r26 import FIXTURE
        self.fixture = FIXTURE
        self.digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def observe(self, text):
        from cbdk.glb_parameter_static_r26 import _observe_source
        path = Path(self.tmp.name) / "synthetic.py"
        path.write_text(text, encoding="utf-8")
        return {row["property"]: row for row in _observe_source(path)}

    def test_r26_fixed_identity_and_exact_observations(self):
        from cbdk.glb_parameter_static_r26 import observe_fixed_parameter_fixture
        for version in ("4.4.3", "4.5.15", "5.2.1"):
            result = observe_fixed_parameter_fixture(run_id="a"*32,
                source_sha256=self.digest, blender_version=version)
            self.assertEqual(result, {
                "case_id": "parameter_fixture_r26", "run_id": "a"*32,
                "source_sha256": self.digest, "blender_version": version,
                "properties": [
                    dict(property=prop, declaration_count=1,
                         same_class_self_count=1, geometry_path_count=1,
                         expected_api_observed=True)
                    for prop in ("sphere_radius", "bevel_width")
                ],
            })
            self.assertNotIn(str(self.fixture), json.dumps(result))

    def test_r26_fixed_identity_rejects_mismatch(self):
        from cbdk.glb_parameter_static_r26 import observe_fixed_parameter_fixture
        base = dict(run_id="a"*32, source_sha256=self.digest, blender_version="4.4.3")
        for patch_values in (dict(run_id=True), dict(run_id="A"*32),
                             dict(source_sha256="0"*64), dict(blender_version="5.2")):
            with self.subTest(patch_values=patch_values), self.assertRaises(ValueError):
                observe_fixed_parameter_fixture(**dict(base, **patch_values))

    def test_r26_duplicate_receiver_class_and_missing_path_controls(self):
        source = self.fixture.read_text(encoding="utf-8")
        original = "radius=self.sphere_radius"
        self.assertIn(original, source)
        for replacement in ("radius=other.sphere_radius", "radius=0.75"):
            observed = self.observe(source.replace(original,replacement))["sphere_radius"]
            self.assertEqual(observed["declaration_count"],1)
            self.assertEqual(observed["same_class_self_count"],0)
            self.assertEqual(observed["geometry_path_count"],0)
            self.assertIs(observed["expected_api_observed"],False)
        other = source.replace(original,"radius=0.75") + (
            "\nclass Unrelated:\n"
            "    sphere_radius: bpy.props.FloatProperty()\n"
            "    def build_geometry(self):\n"
            "        bpy.ops.mesh.primitive_uv_sphere_add(radius=self.sphere_radius)\n")
        observed = self.observe(other)["sphere_radius"]
        self.assertEqual(observed["declaration_count"],2)
        self.assertEqual(observed["same_class_self_count"],0)
        self.assertEqual(observed["geometry_path_count"],0)
        self.assertIs(observed["expected_api_observed"],False)
        duplicate = source.replace("    def build_geometry(self):",
            "    sphere_radius: bpy.props.FloatProperty()\n\n    def build_geometry(self):",1)
        observed = self.observe(duplicate)["sphere_radius"]
        self.assertEqual(observed["declaration_count"],2)
        self.assertIs(observed["expected_api_observed"],False)
        with self.assertRaisesRegex(ValueError,"ambiguous_class"):
            self.observe(source + "\nclass CBDKParameterExperimentSettings:\n    pass\n")

    def test_r26_declaration_and_reference_are_not_geometry_paths(self):
        source = self.fixture.read_text(encoding="utf-8")
        source = source.replace("radius=self.sphere_radius","radius=0.75")
        source = source.replace("        sphere = bpy.context.object",
                                "        observed = self.sphere_radius\n        sphere = bpy.context.object")
        row = self.observe(source)["sphere_radius"]
        self.assertEqual(row["declaration_count"],1)
        self.assertEqual(row["same_class_self_count"],1)
        self.assertEqual(row["geometry_path_count"],0)
        self.assertIs(row["expected_api_observed"],False)

    def test_r26_diagnostic_candidates_do_not_invent_absent_category(self):
        from cbdk.glb_parameter_static_r26 import fixed_diagnostic_candidates
        def comparison(diffs):
            return {"kind":"cbdk_glb_scene_comparison","schema_version":1,
                    "passed":not diffs,"summary":{"errors":len(diffs)},
                    "differences":diffs}
        sphere = {"code":"object_dimensions","severity":"error",
                  "metrics":{"reference_object":"CBDK_Param_Sphere"}}
        unrelated = {"code":"object_dimensions","severity":"error",
                     "metrics":{"reference_object":"CBDK_Param_BevelCube"}}
        self.assertEqual(fixed_diagnostic_candidates(comparison([])),[])
        self.assertEqual(fixed_diagnostic_candidates(comparison([sphere,unrelated])),
                         [{"property":"sphere_radius","target":"CBDK_Param_Sphere",
                           "category":"part_size_parameter"}])
        # Even a fixed synthetic topology category is only a review candidate.
        bevel = dict(unrelated,code="object_topology")
        self.assertEqual(fixed_diagnostic_candidates(comparison([bevel])),
                         [{"property":"bevel_width","target":"CBDK_Param_BevelCube",
                           "category":"topology_or_modifier_difference"}])




class R27FixedSourceCandidateTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        from cbdk.parameter_source_candidate_r27 import FIXTURE, SOURCE_SHA256
        self.original = FIXTURE.read_bytes()
        self.assertEqual(hashlib.sha256(self.original).hexdigest(), SOURCE_SHA256)
        self.identity = dict(run_id="b"*32, source_sha256=SOURCE_SHA256,
                             blender_version="4.4.3")

    def test_r27_exact_candidate_and_reverse(self):
        import hashlib
        from cbdk.parameter_source_candidate_r27 import (
            build_fixed_source_candidate, restore_fixed_source_candidate, FIXTURE)
        needle = b"default=0.75"
        self.assertEqual(self.original.count(needle),1)
        offset = self.original.index(needle)+len(b"default=")
        independently_expected = self.original.replace(needle,b"default=1.15",1)
        for version in ("4.4.3","4.5.15","5.2.1"):
            identity = dict(self.identity,blender_version=version)
            candidate, report = build_fixed_source_candidate(**identity)
            self.assertEqual(candidate,independently_expected)
            self.assertEqual(len(candidate),len(self.original))
            self.assertEqual(candidate[:offset],self.original[:offset])
            self.assertEqual(candidate[offset+4:],self.original[offset+4:])
            self.assertEqual(report,dict(identity,case_id="parameter_source_r27",
                property="sphere_radius",before=0.75,after=1.15,
                old_token="0.75",new_token="1.15",byte_offset=offset,
                single_difference_verified=True,
                candidate_sha256=hashlib.sha256(candidate).hexdigest(),
                restored_sha256=identity["source_sha256"]))
            self.assertEqual(restore_fixed_source_candidate(candidate),self.original)
            self.assertEqual(FIXTURE.read_bytes(),self.original)

    def test_r27_reject_wrong_identity_and_source_digest(self):
        from cbdk.parameter_source_candidate_r27 import build_fixed_source_candidate
        for bad in (dict(run_id=True),dict(run_id="B"*32),
                    dict(source_sha256="0"*64),dict(blender_version="5.2")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                build_fixed_source_candidate(**dict(self.identity,**bad))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"cbdk_parameter_experiment.py"
            path.write_bytes(self.original+b"\n")
            with patch("cbdk.parameter_source_candidate_r27.FIXTURE",path):
                with self.assertRaisesRegex(ValueError,"fixed_source_sha_mismatch"):
                    build_fixed_source_candidate(**self.identity)

    def test_r27_reject_ambiguous_declaration_and_unknown_value(self):
        from cbdk.parameter_source_candidate_r27 import _derive_candidate
        variants = (
            self.original+b"\n# unrelated 0.75\n",
            self.original.replace(b"default=0.75",b"default=0.76"),
            self.original.replace(b"default=0.75",b"default=.75"),
            self.original.replace(b"default=0.75",b"default=True"),
            self.original.replace(b"default=0.08",b"default=0.09"),
            self.original.replace(b"    def build_geometry(self):",
                b"    sphere_radius: bpy.props.FloatProperty(default=0.75)\n"
                b"    def build_geometry(self):",1),
            self.original+b"\nclass Other:\n    sphere_radius: bpy.props.FloatProperty(default=0.4)\n",
            self.original+b"\nclass CBDKParameterExperimentSettings:\n    pass\n",
            self.original.replace(b"bpy.props.FloatProperty(",b"fake.FloatProperty(",1),
        )
        for index, value in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                _derive_candidate(value)

    def test_r27_reject_multiple_edits_and_invalid_reverse(self):
        from cbdk.parameter_source_candidate_r27 import (
            build_fixed_source_candidate, restore_fixed_source_candidate, _check_pair)
        candidate, report = build_fixed_source_candidate(**self.identity)
        offset = report["byte_offset"]
        for bad in (candidate+b"\n", candidate.replace(b"default=0.08",b"default=0.09"),
                    candidate.replace(b"default=1.15",b"default=1.16"),
                    candidate.replace(b"segments=24",b"segments=25"),
                    self.original):
            with self.subTest(bad_sha=__import__("hashlib").sha256(bad).hexdigest()):
                with self.assertRaises(ValueError):
                    _check_pair(self.original,bad,offset)
                with self.assertRaises(ValueError):
                    restore_fixed_source_candidate(bad)
        for wrong in (True,offset+1,-1):
            with self.assertRaises(ValueError):
                _check_pair(self.original,candidate,wrong)
        with self.assertRaises(ValueError):
            restore_fixed_source_candidate(bytearray(candidate))


if __name__ == "__main__":
    unittest.main()
