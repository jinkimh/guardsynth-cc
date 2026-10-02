import unittest
from dataclasses import FrozenInstanceError

from experiments.sequential_coc.contract_ir import (
    Action,
    CheckResult,
    ContractEvent,
    ContradictionType,
    EvidenceValue,
    EventWindow,
    ObligationState,
)
from experiments.sequential_coc.tests.fixtures import (
    accelerating_trace,
    clear_then_go_window,
    conflict_then_valid_release,
    event,
    fixture_results,
    hold_event,
    known_hold,
    proceed_event,
    unknown_release,
)


class ContractIrTests(unittest.TestCase):
    def test_unknown_release_is_not_false_after_round_trip(self):
        event = ContractEvent(
            scene_id="scene-x",
            event_id="e0",
            timestamp_us=0,
            action=Action.STOP_OR_HOLD,
            release_known=False,
            release_value=False,
        )

        restored = ContractEvent.from_dict(event.to_dict())

        self.assertEqual(restored.release_evidence, EvidenceValue.UNKNOWN)
        self.assertEqual(restored.satisfaction_evidence, EvidenceValue.UNKNOWN)

    def test_evidence_values_map_only_valid_known_value_pairs(self):
        self.assertEqual(EvidenceValue.from_known_value(False, False), EvidenceValue.UNKNOWN)
        self.assertEqual(EvidenceValue.from_known_value(True, False), EvidenceValue.FALSE)
        self.assertEqual(EvidenceValue.from_known_value(True, True), EvidenceValue.TRUE)
        with self.assertRaisesRegex(ValueError, "unknown evidence"):
            EvidenceValue.from_known_value(False, True)

    def test_event_rejects_contradictory_evidence_pair(self):
        with self.assertRaisesRegex(ValueError, "release"):
            ContractEvent(
                scene_id="scene-x",
                event_id="e0",
                timestamp_us=0,
                action=Action.STOP_OR_HOLD,
                release_known=False,
                release_value=True,
            )

    def test_event_serialization_omits_source_text_unless_explicitly_requested(self):
        event = ContractEvent(
            scene_id="scene-x",
            event_id="e0",
            timestamp_us=0,
            action=Action.STOP_OR_HOLD,
            source_text="restricted fixture text",
        )

        safe = event.to_dict()
        restored_safe = ContractEvent.from_dict(safe)
        with_text = event.to_dict(include_text=True)
        restored_with_text = ContractEvent.from_dict(with_text)

        self.assertNotIn("source_text", safe)
        self.assertIsNone(restored_safe.source_text)
        self.assertEqual(with_text["source_text"], "restricted fixture text")
        self.assertEqual(restored_with_text.source_text, "restricted fixture text")

    def test_window_hash_is_stable_and_changes_for_contract_content(self):
        first = ContractEvent("scene-x", "e0", 0, Action.STOP_OR_HOLD)
        second = ContractEvent(
            "scene-x",
            "e1",
            1,
            Action.ACCELERATE_OR_PROCEED,
            release_known=True,
            release_value=True,
        )
        window = EventWindow("window-x", "scene-x", (first, second))
        restored = EventWindow.from_dict(window.to_dict())
        changed = EventWindow(
            "window-x",
            "scene-x",
            (
                first,
                ContractEvent(
                    "scene-x",
                    "e1",
                    1,
                    Action.MAINTAIN_SPEED,
                    release_known=True,
                    release_value=True,
                ),
            ),
        )

        self.assertEqual(restored.content_hash, window.content_hash)
        self.assertNotEqual(changed.content_hash, window.content_hash)

    def test_window_rejects_cross_scene_and_out_of_order_events(self):
        first = ContractEvent("scene-x", "e0", 1, Action.STOP_OR_HOLD)
        other_scene = ContractEvent("scene-y", "e1", 2, Action.MAINTAIN_SPEED)
        earlier = ContractEvent("scene-x", "e2", 0, Action.MAINTAIN_SPEED)

        with self.assertRaisesRegex(ValueError, "scene"):
            EventWindow("window-x", "scene-x", (first, other_scene))
        with self.assertRaisesRegex(ValueError, "order"):
            EventWindow("window-x", "scene-x", (first, earlier))
        with self.assertRaisesRegex(ValueError, "cluster"):
            EventWindow("window-x", "not-scene-x", (first,))

    def test_window_accepts_timestamp_ties_only_in_phase_order(self):
        phase_zero = ContractEvent("scene-x", "e0", 1, Action.YIELD_OR_DECELERATE, phase_index=0)
        phase_one = ContractEvent("scene-x", "e1", 1, Action.ACCELERATE_OR_PROCEED, phase_index=1)

        EventWindow("window-x", "scene-x", (phase_zero, phase_one))
        with self.assertRaisesRegex(ValueError, "order"):
            EventWindow("window-x", "scene-x", (phase_one, phase_zero))

    def test_contract_containers_are_immutable_tuples(self):
        window = EventWindow(
            "window-x",
            "scene-x",
            [ContractEvent("scene-x", "e0", 0, Action.STOP_OR_HOLD)],
        )
        result = CheckResult(
            verdict="UNKNOWN",
            contradiction_types=[ContradictionType.HOLD_GO_CONFLICT],
            first_event_id="e0",
            state_trace=[ObligationState.ACTIVE.value],
            unknown_reasons=["release evidence unavailable"],
        )

        self.assertIsInstance(window.events, tuple)
        self.assertIsInstance(result.contradiction_types, tuple)
        self.assertIsInstance(result.state_trace, tuple)
        self.assertIsInstance(result.unknown_reasons, tuple)
        with self.assertRaises(FrozenInstanceError):
            window.cluster_id = "scene-y"
        with self.assertRaises(AttributeError):
            window.events.append("not possible")

    def test_check_result_round_trips_to_json_safe_values(self):
        result = CheckResult(
            verdict="CONTRADICTION",
            contradiction_types=(ContradictionType.HOLD_GO_CONFLICT,),
            first_event_id="e1",
            state_trace=(ObligationState.ACTIVE.value, ObligationState.RELEASED.value),
            unknown_reasons=(),
        )

        serialized = result.to_dict()
        restored = CheckResult.from_dict(serialized)

        self.assertEqual(serialized["contradiction_types"], ["HOLD_GO_CONFLICT"])
        self.assertEqual(serialized["state_trace"], ["ACTIVE", "RELEASED"])
        self.assertEqual(restored, result)

    def test_check_result_normalizes_state_trace_to_obligation_states(self):
        result = CheckResult(
            verdict="UNKNOWN",
            state_trace=["ACTIVE", ObligationState.SATISFIED_WAIT_RELEASE],
        )

        self.assertEqual(
            result.state_trace,
            (ObligationState.ACTIVE, ObligationState.SATISFIED_WAIT_RELEASE),
        )
        self.assertTrue(all(isinstance(state, ObligationState) for state in result.state_trace))
        self.assertEqual(
            CheckResult.from_dict(result.to_dict()).state_trace,
            result.state_trace,
        )

    def test_check_result_rejects_invalid_or_scalar_state_trace(self):
        for trace in ("ACTIVE", b"ACTIVE", {"ACTIVE": True}, ["NOT_A_STATE"]):
            with self.subTest(trace=trace), self.assertRaisesRegex((TypeError, ValueError), "state_trace"):
                CheckResult(verdict="UNKNOWN", state_trace=trace)

    def test_named_fixture_factories_return_real_ordered_ir_values(self):
        generic = event(3, event_id="generic")
        hold_true = hold_event(release=EvidenceValue.TRUE)
        hold_false = hold_event(release=EvidenceValue.FALSE)
        hold_unknown = hold_event(release=EvidenceValue.UNKNOWN)
        proceed = proceed_event()
        window = clear_then_go_window()
        conflict = conflict_then_valid_release()
        known = known_hold()
        unknown = unknown_release()
        trace = accelerating_trace()
        results = fixture_results()

        self.assertIsInstance(generic, ContractEvent)
        self.assertEqual(hold_true.release_evidence, EvidenceValue.TRUE)
        self.assertEqual(hold_false.release_evidence, EvidenceValue.FALSE)
        self.assertEqual(hold_unknown.release_evidence, EvidenceValue.UNKNOWN)
        self.assertEqual(proceed.action, Action.ACCELERATE_OR_PROCEED)
        self.assertIsInstance(window, EventWindow)
        self.assertTrue(all(isinstance(item, ContractEvent) for item in window.events))
        self.assertEqual(
            [(item.timestamp_us, item.phase_index) for item in window.events],
            sorted((item.timestamp_us, item.phase_index) for item in window.events),
        )
        self.assertTrue(all(isinstance(item, ContractEvent) for item in conflict + known + unknown))
        self.assertEqual(known[0].release_evidence, EvidenceValue.FALSE)
        self.assertEqual(unknown[0].release_evidence, EvidenceValue.UNKNOWN)
        self.assertEqual(trace[0]["speed_mps"], 0.0)
        self.assertGreater(trace[-1]["speed_mps"], trace[0]["speed_mps"])
        self.assertTrue(all(isinstance(item, CheckResult) for item in results))
        self.assertTrue(
            all(isinstance(state, ObligationState) for result in results for state in result.state_trace)
        )
        self.assertEqual(results[1].state_trace, (ObligationState.ACTIVE,))
        self.assertEqual(results[2].state_trace, (ObligationState.UNKNOWN,))

    def test_public_hold_fixture_rejects_non_evidence_release(self):
        for release in (None, "TRUE", True):
            with self.subTest(release=release), self.assertRaisesRegex(TypeError, "EvidenceValue"):
                hold_event(release=release)

    def test_enum_members_cover_primary_and_secondary_contradictions(self):
        self.assertEqual(
            {kind.value for kind in ContradictionType},
            {
                "HOLD_GO_CONFLICT",
                "PREMATURE_RELEASE",
                "ORDER_VIOLATION",
                "STALE_OBLIGATION",
                "UNSUPPORTED_CARRYOVER",
            },
        )
        self.assertEqual(ContradictionType.UNSUPPORTED_CARRYOVER.value, "UNSUPPORTED_CARRYOVER")
        self.assertEqual(
            {state.value for state in ObligationState},
            {
                "INACTIVE",
                "ACTIVE",
                "SATISFIED_WAIT_RELEASE",
                "RELEASED",
                "VIOLATED",
                "UNKNOWN",
            },
        )
        self.assertEqual(
            {action.value for action in Action},
            {
                "STOP_OR_HOLD",
                "YIELD_OR_DECELERATE",
                "ACCELERATE_OR_PROCEED",
                "MAINTAIN_SPEED",
            },
        )


if __name__ == "__main__":
    unittest.main()
