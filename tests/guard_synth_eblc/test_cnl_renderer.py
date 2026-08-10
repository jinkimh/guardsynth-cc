"""Tests for the deterministic, non-authoritative EBLC CNL projection."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.guard_synth_eblc.cnl_renderer import (
    CNL_LANGUAGE_VERSION,
    CNL_RENDERER_VERSION,
    export_cnl,
    render_bundle,
    render_program,
)
from src.guard_synth_eblc.examples import synthetic_bundle_v02, synthetic_program_v02


class CNLRendererTest(unittest.TestCase):
    def setUp(self) -> None:
        self.program = synthetic_program_v02()

    def test_program_render_is_deterministic_and_hash_bound(self) -> None:
        left = render_program(self.program)
        right = render_program(self.program)
        self.assertEqual(left, right)
        self.assertEqual(left.renderer_version, CNL_RENDERER_VERSION)
        self.assertEqual(left.language_version, CNL_LANGUAGE_VERSION)
        self.assertEqual(len(left.input_sha256), 64)
        self.assertEqual(len(left.output_sha256), 64)

    def test_program_render_preserves_binding_and_authority_boundary(self) -> None:
        document = render_program(self.program)
        self.assertIn("EBLC-P0B-PED-CZ-0001", document.text)
        self.assertIn("synthetic-pedestrian:P17", document.text)
        self.assertIn("synthetic-zone:CZ4", document.text)
        self.assertIn("ego_path_s", document.text)
        self.assertIn("not the execution authority", document.text)

    def test_program_render_explains_observability_and_unknown(self) -> None:
        text = render_program(self.program).text
        self.assertIn("pedestrian_conflict", text)
        self.assertIn("OBSERVED, PREDICTED, DERIVED", text)
        self.assertIn("maximum age 0.2 s", text)
        self.assertIn("UNKNOWN", text)

    def test_program_render_explains_lifecycle_and_fallback(self) -> None:
        text = render_program(self.program).text
        self.assertIn("2 consecutive clear frames", text)
        self.assertIn("reactivation is enabled", text)
        self.assertIn("APPROVED_HOLD", text)
        self.assertIn("HOLD_PRIOR_LIVE_OBLIGATION_ON_FRESH_UNKNOWN", text)

    def test_program_render_preserves_sourced_values_and_derivation(self) -> None:
        text = render_program(self.program).text
        self.assertIn("position_uncertainty = 0.5 m", text)
        self.assertIn("deceleration = 3 m/s^2", text)
        self.assertIn("stop_position := zone_entry_x - stop_margin", text)
        self.assertIn("stopping_distance := response_distance + braking_distance", text)
        self.assertIn("supplied evidence-bound inputs, not inferred guarantees", text)

    def test_every_program_top_level_field_is_covered(self) -> None:
        document = render_program(self.program)
        expected = {f"$.{key}" for key in self.program.raw}
        self.assertTrue(expected.issubset(set(document.covered_paths)))
        self.assertEqual(document.omitted_paths, ())

    def test_clause_evidence_never_escapes_program_source_refs(self) -> None:
        document = render_program(self.program)
        known = set(self.program.source_refs)
        for clause in document.clauses:
            self.assertTrue(set(clause.source_refs).issubset(known), clause.clause_id)

    def test_bundle_render_preserves_order_priority_and_action_composition(self) -> None:
        bundle = synthetic_bundle_v02(
            tiers=("HARD", "SERVICE"),
            allowed_actions=(("STOP", "CREEP"), ("CREEP", "PROCEED")),
        )
        document = render_bundle(bundle)
        self.assertLess(document.text.index("CONTRACT C0"), document.text.index("CONTRACT C1"))
        self.assertIn("action domain: STOP, CREEP, PROCEED", document.text)
        self.assertIn("admissible actions are the intersection", document.text)
        self.assertIn("priority tier HARD", document.text)
        self.assertIn("priority tier SERVICE", document.text)

    def test_every_bundle_top_level_field_and_component_is_covered(self) -> None:
        bundle = synthetic_bundle_v02()
        document = render_bundle(bundle)
        expected = {f"$.{key}" for key in bundle.raw}
        expected.update({"$.contracts[0].program", "$.contracts[1].program"})
        self.assertTrue(expected.issubset(set(document.covered_paths)))
        self.assertEqual(document.omitted_paths, ())

    def test_export_writes_round_trippable_text_and_mapping(self) -> None:
        document = render_program(self.program)
        with TemporaryDirectory() as directory:
            text_path, mapping_path = export_cnl(document, Path(directory))
            self.assertEqual(text_path.read_text(encoding="utf-8"), document.text)
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            self.assertEqual(mapping["input_sha256"], document.input_sha256)
            self.assertEqual(mapping["output_sha256"], document.output_sha256)
            self.assertEqual(mapping["source_id"], self.program.program_id)
            self.assertEqual(len(mapping["clauses"]), len(document.clauses))


if __name__ == "__main__":
    unittest.main()
