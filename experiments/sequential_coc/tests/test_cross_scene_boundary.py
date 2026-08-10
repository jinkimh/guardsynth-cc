"""Synthetic-only tests for the cross-scene provenance boundary policy."""

from __future__ import annotations

import unittest
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from experiments.sequential_coc.contract_ir import ContradictionType, ObligationState
from experiments.sequential_coc.cross_scene_boundary import (
    build_secondary_result,
    evaluate_boundary_policy,
    write_secondary_result,
)


def fixture_chain() -> dict[str, object]:
    """A synthetic boundary descriptor with no natural scene identity or text."""
    return {"fixture_kind": "SYNTHETIC_BOUNDARY", "boundary_count": 1}


class CrossSceneBoundaryTests(unittest.TestCase):
    def test_unproven_carryover_is_policy_error_not_natural_semantic_conflict(self):
        """Removing the unsupported branch must fail this policy-error check."""
        result = evaluate_boundary_policy(fixture_chain(), True, False)

        self.assertEqual(
            result.contradiction_types,
            (ContradictionType.UNSUPPORTED_CARRYOVER,),
        )

    def test_discard_and_supported_carryover_have_distinct_nonsemantic_states(self):
        """Changing either policy branch must fail its independently declared state."""
        discarded = evaluate_boundary_policy(fixture_chain(), False, False)
        supported = evaluate_boundary_policy(fixture_chain(), True, True)

        self.assertEqual(discarded.verdict, "CONSISTENT")
        self.assertEqual(discarded.contradiction_types, ())
        self.assertEqual(discarded.state_trace, (ObligationState.INACTIVE,))
        self.assertEqual(supported.verdict, "CONSISTENT")
        self.assertEqual(supported.contradiction_types, ())
        self.assertEqual(supported.state_trace, (ObligationState.ACTIVE,))

    def test_secondary_artifact_is_aggregate_only_and_fails_closed_without_raw_input(self):
        """Dropping a policy count or source gate must fail the public artifact contract."""
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "cross-scene-secondary.json"
            payload = build_secondary_result(Path(temporary) / "absent-official-trainval")
            write_secondary_result(output, payload)

            self.assertEqual(payload["evidence_level"], "PROVENANCE_POLICY_EXAMPLE")
            self.assertFalse(payload["global_model_claim"])
            self.assertEqual(payload["input_inventory"]["status"], "INPUT_INVENTORY_MISMATCH")
            self.assertEqual(
                payload["input_inventory"]["expected"],
                {"chain_count": 13, "unique_scene_count": 29, "boundary_count": 16},
            )
            self.assertEqual(payload["natural_semantic_conflict_count"], 0)
            self.assertEqual(
                payload["policy_aggregate"]["UNSUPPORTED_CARRYOVER"],
                {"policy_error_count": 1, "natural_semantic_conflict_count": 0},
            )
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_direct_script_entrypoint_writes_the_restricted_aggregate(self):
        """Removing direct-entrypoint import setup must fail this subprocess contract."""
        module_path = Path(__file__).parents[1] / "cross_scene_boundary.py"
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "cross-scene-secondary.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(module_path),
                    "--official-trainval-root",
                    str(root / "absent-official-trainval"),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
