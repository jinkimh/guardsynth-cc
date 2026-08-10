import tempfile
import unittest
from pathlib import Path

from generate_scene0074_protocol import EXPECTED, QUERIES, TRACE_EVENTS, write_model


class Scene0074ProtocolModelTests(unittest.TestCase):
    def test_trace_is_strictly_ordered(self) -> None:
        times = [at_ms for at_ms, _ in TRACE_EVENTS]
        self.assertEqual(times, sorted(times))
        self.assertEqual(len(times), len(set(times)))

    def test_model_and_queries_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model_path, query_path = write_model(Path(directory))
            model = model_path.read_text(encoding="utf-8")
            self.assertIn("PreserveFirstDeadline", model)
            self.assertIn("ResetOnRepeat", model)
            self.assertEqual(query_path.read_text().splitlines(), list(QUERIES))
            self.assertEqual(len(EXPECTED), len(QUERIES))


if __name__ == "__main__":
    unittest.main()
