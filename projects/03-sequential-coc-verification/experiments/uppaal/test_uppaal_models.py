import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from generate_models import EXPECTED, QUERIES, VARIANTS, load_scene_profile, write_models
from run_verification import classify_output


class UppaalModelGenerationTest(unittest.TestCase):
    def test_generates_all_variants_and_queries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_models(output)
            self.assertEqual(len(list(output.glob("*.xml"))), len(VARIANTS))
            self.assertEqual(
                (output / "scene-0001.q").read_text().splitlines(), list(QUERIES)
            )
            for model in output.glob("*.xml"):
                self.assertIn("DTD Flat System 1.1", model.read_text())
                root = ET.parse(model).getroot()
                names = {item.text for item in root.findall("./template/name")}
                self.assertEqual(
                    names,
                    {
                        "CoCSource",
                        "EgoTrace",
                        "ObligationManager",
                        "ReactionObserver",
                        "DecisionValidator",
                    },
                )

    def test_mutation_oracles_are_complete(self) -> None:
        self.assertEqual(set(EXPECTED), {variant.name for variant in VARIANTS})
        self.assertTrue(all(len(values) == len(QUERIES) for values in EXPECTED.values()))

    def test_profile_is_derived_from_episode_evidence(self) -> None:
        profile = load_scene_profile()
        self.assertEqual(profile.trigger_us, 2_500_000)
        self.assertEqual(
            (profile.repeat_1_ms, profile.repeat_2_ms, profile.response_ms, profile.untrusted_ms),
            (1000, 2300, 2160, 6800),
        )

    def test_classifies_verifyta_verdicts(self) -> None:
        output = "\n".join(
            "Property is satisfied" if value else "Property is NOT satisfied"
            for value in EXPECTED["normal"]
        )
        self.assertEqual(classify_output(output), ("EXECUTED", EXPECTED["normal"]))

    def test_classifies_uppaal_5_formula_wording(self) -> None:
        output = "\n".join(
            "Formula is satisfied" if value else "Formula is NOT satisfied"
            for value in EXPECTED["deadline_2s"]
        )
        self.assertEqual(
            classify_output(output), ("EXECUTED", EXPECTED["deadline_2s"])
        )

    def test_classifies_license_block(self) -> None:
        self.assertEqual(
            classify_output("License does not cover verifier."),
            ("NOT_RUN_LICENSE_BLOCKED", []),
        )


if __name__ == "__main__":
    unittest.main()
