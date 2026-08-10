import tempfile
import unittest
import xml.etree.ElementTree as ET
import json
from pathlib import Path

from generate_chained_models import EXPECTED, QUERIES, VARIANTS, write_models


class ChainedModelGenerationTest(unittest.TestCase):
    def test_generates_variants_queries_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_models(output)
            self.assertEqual(len(list(output.glob("*.xml"))), len(VARIANTS))
            self.assertEqual(
                (output / "scene-0001-chained.q").read_text().splitlines(),
                list(QUERIES),
            )
            root = ET.parse(output / "scene-0001-chained-normal.xml").getroot()
            names = {item.text for item in root.findall("./template/name")}
            self.assertEqual(names, {"ScenarioSource", "ChainProtocol", "DeadlineMonitor", "SafetyGate"})
            profile = json.loads(
                (output / "scene-0001-chained-profile.json").read_text()
            )
            self.assertIn("synthetic_feasibility_assumptions", profile)
            self.assertIn(
                "HEURISTIC_SPEED_TRACE",
                profile["observed"]["response_semantics"],
            )

    def test_provenance_separates_training_and_mutation_roles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_models(output)
            provenance = json.loads(
                (output / "scene-0001-chained-profile.json").read_text()
            )["provenance"]
            self.assertEqual(
                provenance["source_reference_validation"]["status"], "PASS"
            )
            chained = provenance["chained_four_phase"]
            traced = provenance["source_trace_episode"]
            self.assertEqual(chained["traceability"]["source_backed_events"], 2)
            self.assertEqual(chained["gates"]["positive_sequence_training_eligible"], "FAIL")
            self.assertEqual(traced["traceability"]["source_coverage"], 1.0)
            self.assertEqual(traced["traceability"]["synthetic"], 0)
            self.assertEqual(
                traced["gates"]["positive_sequence_training_eligible"],
                "PASS_WITH_WEAK_RESPONSE_LABEL",
            )
            self.assertTrue(
                all(
                    mutation["training_role"] == "HARD_NEGATIVE_ONLY"
                    for mutation in chained["mutation_lineage"]
                )
            )
            training = json.loads(
                (output / "scene-0001-training-manifest.json").read_text()
            )
            self.assertEqual(
                training["positive_sequence_candidates"][0]["source_coverage"],
                1.0,
            )
            self.assertEqual(
                training["excluded_positive_sequences"][0]["allowed_role"],
                "MODEL_CHECKING_AND_MUTATION_ONLY",
            )
            self.assertEqual(len(training["hard_negative_templates"]), 4)

    def test_mutation_oracles_cover_every_query(self) -> None:
        self.assertEqual(set(EXPECTED), {variant.name for variant in VARIANTS})
        self.assertTrue(all(len(values) == len(QUERIES) for values in EXPECTED.values()))


if __name__ == "__main__":
    unittest.main()
