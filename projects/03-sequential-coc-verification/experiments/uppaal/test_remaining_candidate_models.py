import tempfile
import unittest
from pathlib import Path

from generate_remaining_candidate_models import (
    CANDIDATES,
    DEADLINES_MS,
    QUERIES,
    SEMANTICS,
    expected_deadline_safety,
    expected_orphan_response_free,
    write_models,
)


class RemainingCandidateModelTests(unittest.TestCase):
    def test_expected_semantic_differences(self) -> None:
        candidates = {candidate.scene: candidate for candidate in CANDIDATES}
        self.assertFalse(expected_deadline_safety(candidates["scene-0028"], "preserve", 3000))
        self.assertTrue(expected_deadline_safety(candidates["scene-0028"], "reset", 3000))
        self.assertFalse(expected_deadline_safety(candidates["scene-0019"], "preserve", 5000))
        self.assertTrue(
            expected_deadline_safety(candidates["scene-0019"], "deduplicate_1s", 3000)
        )
        self.assertFalse(
            expected_orphan_response_free(candidates["scene-0028"], "deduplicate_1s")
        )

    def test_model_matrix_is_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            oracle = write_models(Path(directory))
            self.assertEqual(
                oracle["model_count"],
                len(CANDIDATES) * len(SEMANTICS) * len(DEADLINES_MS),
            )
            self.assertEqual(
                (Path(directory) / "remaining-candidates.q").read_text().splitlines(),
                list(QUERIES),
            )


if __name__ == "__main__":
    unittest.main()
