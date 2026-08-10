"""Regression tests for the public-src and purpose-named CLI layout."""

from pathlib import Path
import unittest

from cli.pipelines.eblc.p0b_schema_bcv import run as public_pipeline
from cli.pipelines.eblc.restricted_scene_grounding import run as restricted_pipeline
from cli.pipelines.eblc.program_conformance import run as conformance_pipeline
from cli.pipelines.eblc.composition_compile import run as composition_pipeline
from cli.pipelines.eblc.derivation_compile import run as derivation_pipeline
from cli.pipelines.eblc.indexed_collection_compile import run as indexed_collection_pipeline
from cli.pipelines.eblc.release_candidate import run as release_candidate_pipeline
from cli.pipelines.eblc.scenario_validation import run as scenario_pipeline
from cli.pipelines.guardsynth.source_aware_generate import run as generator_pipeline
from cli.pipelines.guardsynth.real_scene_readiness import run as readiness_pipeline
from cli.pipelines.guardsynth.label_light_grounding import run as label_light_pipeline
from experiments.eblc_p0b.types import Truth as CompatibilityTruth
from src.guard_synth_eblc.catalog import FIXTURE_ROOT, SCHEMA_ROOT
from src.guard_synth_eblc.types import Truth


ROOT = Path(__file__).resolve().parents[2]


class PublicLayoutTest(unittest.TestCase):
    def test_public_resources_live_under_src(self) -> None:
        self.assertEqual(SCHEMA_ROOT, ROOT / "src/guard_synth_eblc/schemas")
        self.assertEqual(FIXTURE_ROOT, ROOT / "src/guard_synth_eblc/fixtures")
        self.assertTrue((SCHEMA_ROOT / "eblc_contract.schema.json").is_file())
        self.assertTrue((SCHEMA_ROOT / "eblc_program.schema.json").is_file())
        self.assertTrue((SCHEMA_ROOT / "eblc_program_v0_2.schema.json").is_file())
        self.assertTrue((SCHEMA_ROOT / "eblc_indexed_collection.schema.json").is_file())
        self.assertTrue((FIXTURE_ROOT / "eblc_program_p0b_v0_2.json").is_file())
        self.assertTrue((FIXTURE_ROOT / "eblc_indexed_collection_p0b_v0_1.json").is_file())
        self.assertTrue((ROOT / "src/guard_synth/schemas/source_aware_generation_request.schema.json").is_file())
        self.assertTrue((ROOT / "src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json").is_file())
        self.assertTrue((ROOT / "src/guard_synth/schemas/vehicle_assurance_registry.schema.json").is_file())
        self.assertTrue((ROOT / "src/guard_synth/fixtures/vehicle_assurance_registry_empty_v0_1.json").is_file())
        self.assertTrue((ROOT / "src/guard_synth/schemas/label_light_grounding_packet.schema.json").is_file())
        self.assertTrue((ROOT / "src/guard_synth/fixtures/label_light_grounding_packet_v0_1.json").is_file())
        self.assertTrue((ROOT / "src/guard_synth/fixtures/vehicle_assurance_registry_synthetic_test_v0_1.json").is_file())

    def test_historical_type_import_is_same_public_type(self) -> None:
        self.assertIs(CompatibilityTruth, Truth)

    def test_purpose_named_cli_pipelines_resolve_project_root(self) -> None:
        self.assertEqual(public_pipeline.ROOT, ROOT)
        self.assertEqual(restricted_pipeline.ROOT, ROOT)
        self.assertEqual(conformance_pipeline.ROOT, ROOT)
        self.assertEqual(composition_pipeline.ROOT, ROOT)
        self.assertEqual(derivation_pipeline.ROOT, ROOT)
        self.assertEqual(indexed_collection_pipeline.ROOT, ROOT)
        self.assertEqual(release_candidate_pipeline.ROOT, ROOT)
        self.assertEqual(scenario_pipeline.ROOT, ROOT)
        self.assertEqual(generator_pipeline.ROOT, ROOT)
        self.assertEqual(readiness_pipeline.ROOT, ROOT)
        self.assertEqual(label_light_pipeline.ROOT, ROOT)

    def test_p0b_pipeline_selects_project_local_z3_5(self) -> None:
        runtime = public_pipeline.Z3_RUNTIME
        self.assertEqual(runtime.version, "5.0.0")
        self.assertEqual(runtime.source, "PROJECT_LOCAL_ISOLATED_BUILD")
        self.assertTrue(runtime.module_path.startswith("runtime/solvers/"))
        self.assertNotIn(str(ROOT), runtime.module_path)

    def test_experiment_tree_contains_only_schema_fixture_pointers(self) -> None:
        self.assertFalse((ROOT / "experiments/eblc_p0b/schemas/eblc_contract.schema.json").exists())
        self.assertFalse((ROOT / "experiments/eblc_p0b/fixtures/eblc_contract.json").exists())


if __name__ == "__main__":
    unittest.main()
