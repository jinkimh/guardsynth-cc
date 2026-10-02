import json
from pathlib import Path
import subprocess
import sys
import unittest

from experiments.sequential_coc.contract_compiler import (
    build_summary,
    compile_text,
    compile_window,
)
from experiments.sequential_coc.contract_ir import (
    Action,
    ContractEvent,
    EvidenceValue,
    EventWindow,
)
from experiments.sequential_coc.extract_windows import (
    NATURAL_WINDOWS_PATH,
    RawEvent,
    build_raw_event_windows,
    read_natural_windows,
)


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())


class ContractCompilerTests(unittest.TestCase):
    def test_yield_then_accelerate_is_ordered_not_simultaneous(self):
        compiled = compile_text(
            "Yield to the pedestrian and then accelerate to proceed.", "e0", "s", 0
        )

        self.assertEqual(
            [item.action for item in compiled],
            [Action.YIELD_OR_DECELERATE, Action.ACCELERATE_OR_PROCEED],
        )
        self.assertLess(compiled[0].phase_index, compiled[1].phase_index)
        self.assertEqual(compiled[0].permitted_next_action, compiled[1].action)
        self.assertEqual(compiled[0].release_evidence, EvidenceValue.UNKNOWN)

    def test_missing_clearance_stays_unknown(self):
        compiled = compile_text("Yield to the pedestrian.", "e0", "s", 0)

        self.assertEqual(compiled[0].release_evidence, EvidenceValue.UNKNOWN)

    def test_conditions_are_descriptions_not_observational_evidence(self):
        cases = (
            (
                "Yield to the pedestrian until the pedestrian clears.",
                "release_condition",
                "the pedestrian clears",
            ),
            ("Once the signal is green, proceed.", "trigger", "the signal is green"),
            ("Proceed after the path is clear.", "trigger", "the path is clear"),
        )

        for text, field, expected in cases:
            with self.subTest(field=field):
                compiled = compile_text(text, "condition", "scene", 7)
                self.assertEqual(len(compiled), 1)
                self.assertEqual(getattr(compiled[0], field), expected)
                self.assertEqual(compiled[0].release_evidence, EvidenceValue.UNKNOWN)
                self.assertEqual(compiled[0].satisfaction_evidence, EvidenceValue.UNKNOWN)

    def test_all_four_declared_action_classes_are_recognized(self):
        cases = (
            ("Stop at the stop sign.", Action.STOP_OR_HOLD),
            ("Slow down for the cyclist.", Action.YIELD_OR_DECELERATE),
            ("Accelerate to proceed.", Action.ACCELERATE_OR_PROCEED),
            ("Maintain the current speed.", Action.MAINTAIN_SPEED),
        )

        for text, expected in cases:
            with self.subTest(action=expected):
                compiled = compile_text(text, "action", "scene", 1)
                self.assertEqual([item.action for item in compiled], [expected])
                self.assertEqual(compiled[0].parse_status, "PARSED")

    def test_noun_and_adjective_mentions_do_not_fabricate_actions(self):
        texts = (
            "A stop sign is visible ahead.",
            "A stopped bus occupies the curb.",
            "The bus stop is visible ahead.",
            "A holding area is beside the junction.",
            "The acceleration lane is on the right.",
            "The vehicle has adequate deceleration capability.",
            "A yield sign is visible ahead.",
        )

        for text in texts:
            with self.subTest(kind=text.split()[1]):
                self.assertEqual(compile_text(text, "noun", "scene", 1), [])

    def test_action_words_require_positive_verb_context(self):
        noun_uses = (
            "The next stop is downtown.",
            "The cargo hold is full.",
            "The crop yield is high.",
            "Press the resume button.",
        )
        explicit_actions = (
            ("Stop at the stop sign.", Action.STOP_OR_HOLD),
            ("Hold position.", Action.STOP_OR_HOLD),
            ("Yield to the pedestrian.", Action.YIELD_OR_DECELERATE),
            ("Resume driving.", Action.ACCELERATE_OR_PROCEED),
            ("The vehicle should stop at the stop sign.", Action.STOP_OR_HOLD),
            ("The vehicle is yielding to the pedestrian.", Action.YIELD_OR_DECELERATE),
            ("Please stop at the stop sign.", Action.STOP_OR_HOLD),
        )

        for text in noun_uses:
            with self.subTest(context="noun"):
                self.assertEqual(compile_text(text, "context", "scene", 1), [])
        for text, action in explicit_actions:
            with self.subTest(context="action", action=action):
                self.assertEqual(
                    [item.action for item in compile_text(text, "context", "scene", 1)],
                    [action],
                )

    def test_action_complements_never_prove_verbhood(self):
        noun_uses = (
            "The stop at the museum is scheduled.",
            "The yield to maturity increased.",
            "The hold before release expires.",
            "The resume to service is scheduled.",
            "The resume driving option is enabled.",
        )

        for text in noun_uses:
            with self.subTest():
                self.assertEqual(compile_text(text, "complement-noun", "scene", 1), [])

    def test_unordered_actions_are_retained_as_unknown_single_phase(self):
        compiled = compile_text(
            "Yield to the pedestrian and accelerate through the junction.",
            "unordered",
            "scene",
            2,
        )

        self.assertEqual(
            [item.action for item in compiled],
            [Action.YIELD_OR_DECELERATE, Action.ACCELERATE_OR_PROCEED],
        )
        self.assertEqual({item.phase_index for item in compiled}, {0})
        self.assertEqual(
            {item.parse_status for item in compiled}, {"UNKNOWN_AMBIGUOUS_ORDER"}
        )
        self.assertTrue(all(item.permitted_next_action is None for item in compiled))

    def test_repeated_unordered_action_class_keeps_occurrences_and_local_targets(self):
        compiled = compile_text(
            "Stop at the stop sign and stop before the crosswalk.",
            "repeated",
            "scene",
            2,
        )

        self.assertEqual(
            [item.action for item in compiled],
            [Action.STOP_OR_HOLD, Action.STOP_OR_HOLD],
        )
        self.assertEqual([item.target for item in compiled], ["stop sign", "crosswalk"])
        self.assertEqual({item.phase_index for item in compiled}, {0})
        self.assertEqual(
            {item.parse_status for item in compiled}, {"UNKNOWN_AMBIGUOUS_ORDER"}
        )
        self.assertEqual(len({item.event_id for item in compiled}), 2)

    def test_yield_action_without_identifiable_target_is_retained_unknown(self):
        compiled = compile_text("Yield now.", "missing-target", "scene", 3)

        self.assertEqual([item.action for item in compiled], [Action.YIELD_OR_DECELERATE])
        self.assertEqual(compiled[0].parse_status, "UNKNOWN_MISSING_TARGET")
        self.assertIsNone(compiled[0].target)

    def test_phase_ids_are_deterministic_distinct_and_timestamp_preserving(self):
        arguments = ("Yield to the pedestrian then proceed.", "source-event", "scene", 19)

        first = compile_text(*arguments)
        second = compile_text(*arguments)

        self.assertEqual([item.event_id for item in first], [item.event_id for item in second])
        self.assertEqual(len({item.event_id for item in first}), 2)
        self.assertEqual([item.timestamp_us for item in first], [19, 19])
        self.assertEqual(
            [(item.timestamp_us, item.phase_index) for item in first],
            sorted((item.timestamp_us, item.phase_index) for item in first),
        )

    def test_preposed_conditions_cross_then_without_becoming_evidence(self):
        cases = (
            ("Once the signal is green, then proceed.", "the signal is green"),
            ("After the path is clear, then proceed.", "the path is clear"),
        )

        for text, expected_trigger in cases:
            with self.subTest():
                compiled = compile_text(text, "preposed", "scene", 21)
                self.assertEqual(len(compiled), 1)
                self.assertEqual(compiled[0].trigger, expected_trigger)
                self.assertEqual(compiled[0].release_evidence, EvidenceValue.UNKNOWN)
                self.assertEqual(compiled[0].satisfaction_evidence, EvidenceValue.UNKNOWN)

    def test_until_then_is_condition_text_not_an_ordered_phase_connector(self):
        compiled = compile_text("Hold position until then.", "until-then", "scene", 22)

        self.assertEqual([item.action for item in compiled], [Action.STOP_OR_HOLD])
        self.assertEqual(compiled[0].release_condition, "then")
        self.assertEqual(compiled[0].phase_index, 0)
        self.assertIsNone(compiled[0].permitted_next_action)
        self.assertEqual(compiled[0].release_evidence, EvidenceValue.UNKNOWN)

    def test_phase_ids_include_scene_timestamp_and_window_source_occurrence(self):
        base_arguments = ("Proceed.", "shared-source-id")
        distinct_contexts = (
            compile_text(*base_arguments, "scene-a", 10)[0].event_id,
            compile_text(*base_arguments, "scene-b", 10)[0].event_id,
            compile_text(*base_arguments, "scene-a", 11)[0].event_id,
        )
        duplicate_sources = tuple(
            ContractEvent(
                scene_id="scene-window",
                event_id="duplicate-source-id",
                timestamp_us=30,
                action=Action.MAINTAIN_SPEED,
                provenance="ORIGINAL",
                parse_status="UNCOMPILED",
                source_text="Proceed.",
            )
            for _ in range(2)
        )
        compiled_window = compile_window(
            EventWindow("duplicate-window", "scene-window", duplicate_sources)
        )

        self.assertEqual(len(set(distinct_contexts)), 3)
        self.assertEqual(len(compiled_window), 2)
        self.assertEqual(len({item.event_id for item in compiled_window}), 2)

    def test_compile_raw_window_preserves_identity_fields_and_is_deterministic(self):
        raw_window = build_raw_event_windows(
            {
                "scene-raw": [
                    RawEvent("scene-raw", 10, "Yield to the pedestrian.", original_position=0),
                    RawEvent("scene-raw", 20, "Then proceed.", original_position=1),
                ]
            }
        )[0]

        first = compile_window(raw_window)
        second = compile_window(raw_window)

        self.assertEqual(first, second)
        self.assertEqual([item.scene_id for item in first], ["scene-raw", "scene-raw"])
        self.assertEqual([item.timestamp_us for item in first], [10, 20])
        self.assertEqual([item.source_text for item in first], [event.source_text for event in raw_window.events])
        self.assertEqual(len({item.event_id for item in first}), 2)
        self.assertEqual(
            [(item.timestamp_us, item.phase_index) for item in first],
            sorted((item.timestamp_us, item.phase_index) for item in first),
        )

    def test_compile_source_text_event_window_preserves_provenance(self):
        source = ContractEvent(
            scene_id="scene-window",
            event_id="source-id",
            timestamp_us=8,
            action=Action.MAINTAIN_SPEED,
            provenance="ORIGINAL_PROVENANCE",
            parse_status="UNCOMPILED",
            source_text="Stop at the stop sign.",
        )
        window = EventWindow("window", "scene-window", (source,))

        compiled = compile_window(window)

        self.assertEqual(len(compiled), 1)
        self.assertEqual(compiled[0].action, Action.STOP_OR_HOLD)
        self.assertEqual(compiled[0].provenance, "ORIGINAL_PROVENANCE")

    def test_compiled_event_serialization_is_text_safe_by_default(self):
        sentinel = "SYNTHETIC_PRIVATE_SENTINEL_d0bb0f"
        compiled = compile_text(
            f"Yield to the pedestrian. {sentinel}", "safe", "scene", 4
        )[0]

        self.assertEqual(compiled.source_text.endswith(sentinel), True)
        self.assertNotIn(sentinel, json.dumps(compiled.to_dict()))
        self.assertIn(sentinel, json.dumps(compiled.to_dict(include_text=True)))

    def test_natural_summary_deduplicates_overlapping_windows_to_399_sources(self):
        summary = build_summary(read_natural_windows(NATURAL_WINDOWS_PATH))

        self.assertEqual(summary["unique_source_events"], 399)
        self.assertEqual(
            summary["compiled_phase_count"], sum(summary["parsed_status_counts"].values())
        )
        self.assertEqual(
            summary["unique_source_events"],
            summary["source_events_with_actions"] + summary["no_action_count"],
        )
        self.assertGreaterEqual(summary["unknown_rate"], 0.0)
        self.assertLessEqual(summary["unknown_rate"], 1.0)

    def test_summary_cli_emits_count_only_json(self):
        result = subprocess.run(
            [sys.executable, "projects/03-sequential-coc-verification/experiments/sequential_coc/contract_compiler.py", "--summary"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["unique_source_events"], 399)
        self.assertEqual(
            set(payload),
            {
                "compiled_phase_count",
                "no_action_count",
                "parsed_status_counts",
                "source_events_with_actions",
                "unique_source_events",
                "unknown_rate",
            },
        )
        self.assertNotIn("accuracy", result.stdout.lower())
        self.assertNotIn("source_text", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
