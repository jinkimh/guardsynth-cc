"""Generator-level tests for the sequential CoC UPPAAL observer."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import xml.etree.ElementTree as ET

from experiments.sequential_coc.contract_ir import Action, EvidenceValue
from experiments.sequential_coc.stateful_checker import transition_table_sha256
from experiments.sequential_coc.tests.fixtures import (
    conflict_then_valid_release,
    event,
    hold_event,
    proceed_event,
)
from experiments.sequential_coc.uppaal_generator import (
    build_uppaal_model,
    serialize_uppaal_model,
    write_uppaal_artifacts,
)


EXPECTED_HASH = "e3f5e437dab029813dd4d5e515426e1079e29ce385108aea60665d87d130c4f8"
EXPECTED_QUERIES = [
    "A[] not sticky_hold_go_conflict",
    "A[] not sticky_premature_release",
    "A[] not sticky_order_violation",
    "A[] not sticky_stale_obligation",
    "A[] not sticky_unknown",
    "A<> Observer.Done",
]


class UppaalGeneratorTests(unittest.TestCase):
    def test_model_encodes_inputs_without_collapsing_unknown_and_target_equality(self):
        first = replace(
            hold_event(event_id="h1", release=EvidenceValue.UNKNOWN),
            target="pedestrian-a",
            satisfaction_known=True,
            satisfaction_value=False,
        )
        second = replace(
            hold_event(timestamp_us=1, event_id="h2", release=EvidenceValue.TRUE),
            target="pedestrian-a",
        )
        third = replace(
            event(timestamp_us=2, event_id="m", action=Action.MAINTAIN_SPEED),
            target="pedestrian-b",
            parse_status="UNKNOWN_AMBIGUOUS_ORDER",
        )

        tree, _ = build_uppaal_model([first, second, third])
        declaration = tree.getroot().findtext("declaration") or ""

        self.assertIn("const int event_action[3] = {0, 0, 3};", declaration)
        self.assertIn("const int event_target[3] = {1, 1, 2};", declaration)
        self.assertIn("const bool satisfaction_known[3] = {true, false, false};", declaration)
        self.assertIn("const bool satisfaction_value[3] = {false, false, false};", declaration)
        self.assertIn("const bool release_known[3] = {false, true, false};", declaration)
        self.assertIn("const bool release_value[3] = {false, true, false};", declaration)
        self.assertIn("const bool parse_unknown[3] = {false, false, true};", declaration)

    def test_model_has_v2_metadata_sticky_flags_full_consumption_and_ordered_queries(self):
        tree, queries = build_uppaal_model(list(conflict_then_valid_release()))
        xml = serialize_uppaal_model(tree).decode("utf-8")

        self.assertEqual(transition_table_sha256(), EXPECTED_HASH)
        self.assertIn("transition_contract_version=sequential-coc-transition-v2", xml)
        self.assertIn(f"transition_contract_sha256={EXPECTED_HASH}", xml)
        for flag in (
            "sticky_hold_go_conflict",
            "sticky_premature_release",
            "sticky_order_violation",
            "sticky_stale_obligation",
            "sticky_parse_status_unknown",
            "sticky_overlapping_obligation",
            "sticky_stale_release_unknown",
            "sticky_active_release_unknown",
            "sticky_active_satisfaction_unknown",
        ):
            self.assertIn(flag, xml)
        self.assertIn("idx++", xml)
        self.assertIn("first_violation_idx", xml)
        self.assertNotIn("Miss", xml)
        self.assertEqual(queries, EXPECTED_QUERIES)

    def test_empty_model_is_valid_deterministic_and_immediately_completes(self):
        first_tree, first_queries = build_uppaal_model([])
        second_tree, second_queries = build_uppaal_model([])
        declaration = first_tree.getroot().findtext("declaration") or ""

        self.assertEqual(serialize_uppaal_model(first_tree), serialize_uppaal_model(second_tree))
        self.assertEqual(first_queries, second_queries)
        self.assertIn("const int EVENT_COUNT = 0;", declaration)
        self.assertIn("const int event_action[1] = {3};", declaration)
        self.assertEqual(first_tree.getroot().find("template/init").attrib["ref"], "run")

    def test_observer_instance_has_distinct_template_and_parse_unknown_final_overlay(self):
        uncertain = replace(event(), parse_status="UNKNOWN_MISSING_TARGET")
        tree, _ = build_uppaal_model([uncertain])
        root = tree.getroot()
        declaration = root.findtext("declaration") or ""

        self.assertEqual(root.findtext("template/name"), "ObserverTemplate")
        self.assertEqual(root.findtext("system"), "Observer = ObserverTemplate();\nsystem Observer;")
        run_children = list(root.find("template/location[@id='run']"))
        self.assertEqual(run_children[-1].tag, "committed")
        self.assertGreater(
            declaration.rindex("if (parse_unknown[idx])"),
            declaration.rindex("sticky_order_violation || sticky_stale_obligation"),
        )

    def test_event_metadata_is_xml_escaped_and_round_trips(self):
        special = replace(event(event_id='id<&"quoted"'), scene_id="scene<&")
        tree, _ = build_uppaal_model([special])
        payload = serialize_uppaal_model(tree)

        self.assertIn(b"id&lt;&amp;\"quoted\"", payload)
        reparsed = ET.fromstring(payload)
        comments = [node.text for node in reparsed.findall(".//label[@kind='comments']")]
        self.assertIn('event[0]=id<&"quoted"', comments)

    def test_invalid_sequences_match_python_checker_validation(self):
        invalid = (
            (),
            [object()],
            [event(scene_id="a"), event(timestamp_us=1, scene_id="b")],
            [event(timestamp_us=2), event(timestamp_us=1)],
        )
        for value in invalid:
            with self.subTest(value=type(value).__name__):
                with self.assertRaises((TypeError, ValueError)):
                    build_uppaal_model(value)  # type: ignore[arg-type]

    def test_writer_emits_exact_deterministic_xml_and_query_text(self):
        tree, queries = build_uppaal_model([proceed_event()])
        expected_query_text = "\n".join(EXPECTED_QUERIES) + "\n"
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = root / "observer.xml"
            query = root / "observer.q"

            write_uppaal_artifacts(tree, queries, model, query)

            self.assertEqual(model.read_bytes(), serialize_uppaal_model(tree))
            self.assertEqual(query.read_text(encoding="utf-8"), expected_query_text)
            self.assertEqual(model.stat().st_mode & 0o777, 0o600)
            self.assertEqual(query.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
