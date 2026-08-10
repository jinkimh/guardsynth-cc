import tempfile
import unittest
from pathlib import Path

from generate_cohort_models import QUERIES, VARIANTS, write_models


class CohortModelGenerationTest(unittest.TestCase):
    def test_generates_every_scene_and_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            oracle = write_models(output)
            self.assertEqual(oracle["model_count"], 13 * len(VARIANTS))
            self.assertEqual(len(list(output.glob("*.xml"))), oracle["model_count"])
            self.assertEqual((output / "cohort.q").read_text().splitlines(), list(QUERIES))
            self.assertEqual(
                oracle["expected_satisfaction"]["scene-0028"]["baseline"],
                [True, True, False, True],
            )


if __name__ == "__main__":
    unittest.main()
