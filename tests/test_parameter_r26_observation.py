"""C-only pure tests; no bpy or fixture execution."""
import copy
import unittest
from scripts.parameter_r26_observation import (
    EXPECTED, PROPERTIES, CASES, build_native_observation, run_identity,
)


class NativeParameterR26Tests(unittest.TestCase):
    def setUp(self):
        self.reads = {name: {"registered": {p: True for p in PROPERTIES},
                             "before": dict(zip(PROPERTIES, vals)),
                             "after": dict(zip(PROPERTIES, vals))}
                      for name, vals in EXPECTED.items()}
        def metric(count, delta):
            return {"changed_vertex_count": count, "max_local_displacement": delta,
                    "vertex_count": 24, "metric": "index_aligned_local_vertex_distance",
                    "valid_for_arbitrary_glb": False, "tolerance": 1e-6}
        self.displacement = {}
        self.directions = {}
        for stage in ("generated", "imported"):
            self.displacement[stage] = {}
            self.directions[stage] = {}
            for p, (changed, target, unrelated, up, down, _) in CASES.items():
                self.displacement[stage][changed] = {target: metric(24, .4), unrelated: metric(0, 0.)}
                self.directions[stage][p] = {"affected_fixture_object": target,
                    "unrelated_fixture_object": unrelated, "known_reference_variant": changed,
                    "unrelated_probe_changed_vertices": {up: 0, down: 0}}

    def observation(self, **flags):
        return build_native_observation("a"*32, "b"*64, "4.4.3", self.reads,
            self.displacement, self.directions,
            **{"cleanup_verified": True, "source_unchanged": True, **flags})

    def test_positive_fixed_observation_and_independent_parent_identity(self):
        record = self.observation()
        self.assertEqual(record["case_id"], "parameter_fixture_r26")
        self.assertEqual([row["property"] for row in record["properties"]], list(PROPERTIES))
        self.assertTrue(all(value is True for row in record["properties"]
                            for key, value in row.items() if key != "property"))
        kw = {"source_sha256": "b"*64, "blender_version": "4.4.3", "independent_id": "c"*32}
        self.assertEqual(run_identity(None, None, None, **kw), ("c"*32, "independent_specialist"))
        self.assertEqual(run_identity("a"*32, "b"*64, "4.4.3", **kw), ("a"*32, "parent_supplied"))
        for inputs in (("a"*32, None, None), ("a"*32, "d"*64, "4.4.3"),
                       ("a"*32, "b"*64, "5.2.1"), ("A"*32, "b"*64, "4.4.3")):
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                run_identity(*inputs, **kw)

    def test_static_names_do_not_prove_registration_or_readback(self):
        self.reads["baseline"]["registered"]["sphere_radius"] = False
        self.reads["bevel_probe_up"]["after"]["bevel_width"] = 0.08
        a, b = self.observation()["properties"]
        self.assertFalse(a["registered_on_expected_instance"])
        self.assertTrue(a["value_readback_verified"])
        self.assertFalse(b["value_readback_verified"])
        self.assertTrue(b["registered_on_expected_instance"])

    def test_effects_are_observed_not_hardcoded_or_swapped(self):
        self.displacement["imported"]["bevel_width_changed"]["CBDK_Param_BevelCube"].update(
            changed_vertex_count=0, max_local_displacement=0.)
        self.directions["generated"]["sphere_radius"]["unrelated_probe_changed_vertices"]["sphere_probe_down"] = 1
        a, b = self.observation()["properties"]
        self.assertFalse(a["unrelated_unchanged_generated"])
        self.assertTrue(a["unrelated_unchanged_imported"])
        self.assertFalse(b["target_changed_imported"])
        self.assertTrue(b["target_changed_generated"])
        self.assertFalse(self.observation(cleanup_verified=False)["cleanup_verified"])

    def test_bool_numeric_missing_and_inconsistent_observations_rejected(self):
        original = copy.deepcopy(self.reads)
        self.reads["baseline"]["registered"]["sphere_radius"] = 1
        with self.assertRaises(ValueError):
            self.observation()
        self.reads = copy.deepcopy(original)
        self.reads["baseline"]["before"]["sphere_radius"] = True
        with self.assertRaises(ValueError):
            self.observation()
        self.reads = copy.deepcopy(original)
        self.reads.pop("baseline")
        with self.assertRaises(ValueError):
            self.observation()
        self.reads = copy.deepcopy(original)
        self.displacement["generated"]["sphere_radius_changed"]["CBDK_Param_Sphere"]["changed_vertex_count"] = 0
        with self.assertRaises(ValueError):
            self.observation()

    def test_source_unchanged_cannot_be_replaced_by_probe_control_mapping(self):
        with self.assertRaises(ValueError):
            self.observation(source_unchanged={"bevel_probe_up": 0, "bevel_probe_down": 0})
        self.assertTrue(self.observation()["source_unchanged"])
        self.assertFalse(self.observation(source_unchanged=False)["source_unchanged"])
