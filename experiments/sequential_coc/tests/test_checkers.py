"""Behavior tables for event-local and stateful sequential CoC checkers."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import re
import unittest

from experiments.sequential_coc.contract_ir import (
    Action,
    CheckResult,
    ContractEvent,
    ContradictionType,
    EvidenceValue,
    ObligationState,
)
from experiments.sequential_coc.event_local_checker import check_event_local
from experiments.sequential_coc.stateful_checker import (
    transition_rule_description,
    transition_table_sha256,
    check_stateful,
)
from experiments.sequential_coc.tests.fixtures import event, hold_event, proceed_event


def with_evidence(
    item: ContractEvent,
    *,
    release: EvidenceValue | None = None,
    satisfaction: EvidenceValue | None = None,
    **changes: object,
) -> ContractEvent:
    """Return a fixture event with explicit three-valued evidence."""
    updates = dict(changes)
    if release is not None:
        updates["release_known"] = release is not EvidenceValue.UNKNOWN
        updates["release_value"] = release is EvidenceValue.TRUE
    if satisfaction is not None:
        updates["satisfaction_known"] = satisfaction is not EvidenceValue.UNKNOWN
        updates["satisfaction_value"] = satisfaction is EvidenceValue.TRUE
    return replace(item, **updates)


def expected_transition_description() -> dict[str, object]:
    """Hand-declared observer contract, independent of checker implementation."""
    contradiction_rules = [
        {
            "id": "PREMATURE_RELEASE",
            "action": "ACCELERATE_OR_PROCEED",
            "active": "ANY",
            "when": "CURRENT_RELEASE_FALSE",
            "flag": "PREMATURE_RELEASE",
        },
        {
            "id": "HOLD_GO_CONFLICT",
            "action": "ACCELERATE_OR_PROCEED",
            "active": "TRUE",
            "when": "CURRENT_RELEASE_NOT_FALSE_AND_EFFECTIVE_RELEASE_FALSE",
            "flag": "HOLD_GO_CONFLICT",
        },
        {
            "id": "ORDER_VIOLATION_NO_ACTIVE",
            "action": "ACCELERATE_OR_PROCEED",
            "active": "FALSE",
            "when": "CURRENT_SATISFACTION_FALSE",
            "flag": "ORDER_VIOLATION",
        },
        {
            "id": "ORDER_VIOLATION_ACTIVE",
            "action": "ACCELERATE_OR_PROCEED",
            "active": "TRUE",
            "when": "EFFECTIVE_SATISFACTION_FALSE",
            "flag": "ORDER_VIOLATION",
        },
        {
            "id": "STALE_OBLIGATION",
            "action": "STOP_OR_YIELD",
            "active": "SAME",
            "when": "EFFECTIVE_RELEASE_TRUE",
            "flag": "STALE_OBLIGATION",
        },
    ]
    transition_branches = [
        {"id": "HOLD_START_RELEASED", "action": "STOP_OR_YIELD", "active": "FALSE", "when": "CURRENT_RELEASE_TRUE", "active_after": "NONE", "state": "RELEASED", "unknown_reasons": []},
        {"id": "HOLD_START_SATISFIED", "action": "STOP_OR_YIELD", "active": "FALSE", "when": "CURRENT_RELEASE_NOT_TRUE_AND_CURRENT_SATISFACTION_TRUE", "active_after": "START", "state": "SATISFIED_WAIT_RELEASE", "unknown_reasons": []},
        {"id": "HOLD_START_ACTIVE", "action": "STOP_OR_YIELD", "active": "FALSE", "when": "CURRENT_RELEASE_NOT_TRUE_AND_CURRENT_SATISFACTION_NOT_TRUE", "active_after": "START", "state": "ACTIVE", "unknown_reasons": []},
        {"id": "HOLD_OVERLAP", "action": "STOP_OR_YIELD", "active": "DISTINCT", "when": "ANY", "active_after": "RETAIN", "state": "UNKNOWN", "unknown_reasons": ["OVERLAPPING_OBLIGATION"]},
        {"id": "HOLD_CONTINUE_STALE", "action": "STOP_OR_YIELD", "active": "SAME", "when": "EFFECTIVE_RELEASE_TRUE", "active_after": "RETAIN", "state": "VIOLATED", "unknown_reasons": []},
        {"id": "HOLD_CONTINUE_SATISFIED", "action": "STOP_OR_YIELD", "active": "SAME", "when": "EFFECTIVE_RELEASE_FALSE_AND_EFFECTIVE_SATISFACTION_TRUE", "active_after": "RETAIN", "state": "SATISFIED_WAIT_RELEASE", "unknown_reasons": []},
        {"id": "HOLD_CONTINUE_ACTIVE", "action": "STOP_OR_YIELD", "active": "SAME", "when": "EFFECTIVE_RELEASE_FALSE_AND_EFFECTIVE_SATISFACTION_NOT_TRUE", "active_after": "RETAIN", "state": "ACTIVE", "unknown_reasons": []},
        {"id": "HOLD_CONTINUE_UNKNOWN", "action": "STOP_OR_YIELD", "active": "SAME", "when": "EFFECTIVE_RELEASE_UNKNOWN", "active_after": "RETAIN", "state": "UNKNOWN", "unknown_reasons": ["STALE_RELEASE_UNKNOWN"]},
        {"id": "PROCEED_NO_ACTIVE_FLAGGED", "action": "ACCELERATE_OR_PROCEED", "active": "FALSE", "when": "ANY_CURRENT_CONTRADICTION_FLAG", "active_after": "NONE", "state": "VIOLATED", "unknown_reasons": []},
        {"id": "PROCEED_NO_ACTIVE_CLEAR", "action": "ACCELERATE_OR_PROCEED", "active": "FALSE", "when": "NO_CURRENT_CONTRADICTION_FLAG", "active_after": "NONE", "state": "INACTIVE", "unknown_reasons": []},
        {"id": "PROCEED_ACTIVE_FLAGGED", "action": "ACCELERATE_OR_PROCEED", "active": "TRUE", "when": "ANY_CURRENT_CONTRADICTION_FLAG", "active_after": "RETAIN", "state": "VIOLATED", "unknown_reasons": []},
        {"id": "PROCEED_ACTIVE_UNKNOWN", "action": "ACCELERATE_OR_PROCEED", "active": "TRUE", "when": "NO_FLAG_AND_ANY_REQUIRED_EFFECTIVE_EVIDENCE_UNKNOWN", "active_after": "RETAIN", "state": "UNKNOWN", "unknown_reasons": ["ACTIVE_RELEASE_UNKNOWN", "ACTIVE_SATISFACTION_UNKNOWN"], "unknown_reason_policy": "ADD_CODE_ONLY_FOR_CORRESPONDING_UNKNOWN_EVIDENCE"},
        {"id": "PROCEED_ACTIVE_RELEASED", "action": "ACCELERATE_OR_PROCEED", "active": "TRUE", "when": "NO_FLAG_AND_EFFECTIVE_RELEASE_TRUE_AND_EFFECTIVE_SATISFACTION_TRUE", "active_after": "NONE", "state": "RELEASED", "unknown_reasons": []},
        {"id": "MAINTAIN_NO_ACTIVE", "action": "MAINTAIN_SPEED", "active": "FALSE", "when": "ANY", "active_after": "NONE", "state": "INACTIVE", "unknown_reasons": []},
        {"id": "MAINTAIN_ACTIVE_RELEASED", "action": "MAINTAIN_SPEED", "active": "TRUE", "when": "EFFECTIVE_RELEASE_TRUE", "active_after": "NONE", "state": "RELEASED", "unknown_reasons": []},
        {"id": "MAINTAIN_ACTIVE_SATISFIED", "action": "MAINTAIN_SPEED", "active": "TRUE", "when": "EFFECTIVE_RELEASE_FALSE_AND_EFFECTIVE_SATISFACTION_TRUE", "active_after": "RETAIN", "state": "SATISFIED_WAIT_RELEASE", "unknown_reasons": []},
        {"id": "MAINTAIN_ACTIVE", "action": "MAINTAIN_SPEED", "active": "TRUE", "when": "EFFECTIVE_RELEASE_FALSE_AND_EFFECTIVE_SATISFACTION_NOT_TRUE", "active_after": "RETAIN", "state": "ACTIVE", "unknown_reasons": []},
        {"id": "MAINTAIN_ACTIVE_UNKNOWN", "action": "MAINTAIN_SPEED", "active": "TRUE", "when": "EFFECTIVE_RELEASE_UNKNOWN", "active_after": "RETAIN", "state": "UNKNOWN", "unknown_reasons": ["ACTIVE_RELEASE_UNKNOWN"]},
    ]
    return {
        "version": "sequential-coc-transition-v2",
        "action_count": 4,
        "state_count": 6,
        "active_obligation_capacity": 1,
        "primary_contradiction_count": 4,
        "contradiction_order": ["HOLD_GO_CONFLICT", "PREMATURE_RELEASE", "ORDER_VIOLATION", "STALE_OBLIGATION"],
        "unknown_reason_order": ["PARSE_STATUS_UNKNOWN", "OVERLAPPING_OBLIGATION", "STALE_RELEASE_UNKNOWN", "ACTIVE_RELEASE_UNKNOWN", "ACTIVE_SATISFACTION_UNKNOWN"],
        "input_validation": {"container": "LIST", "scene_count": "ZERO_OR_ONE", "key_fields": ["timestamp_us", "phase_index"], "order": "NONDECREASING_REJECT_INVALID", "empty_state_trace": ["INACTIVE"]},
        "evidence_update": {"policy": "LATER_KNOWN_ONLY", "fields": ["release", "satisfaction"], "unknown_retains_prior": True, "applies_when": ["ACTIVE_SAME", "ACTIVE_PROCEED", "ACTIVE_MAINTAIN"], "distinct_overlap": "NO_UPDATE_RETAIN_ACTIVE"},
        "event_evaluation_order": ["PARSE_UNKNOWN_REASON", "KNOWN_EVIDENCE_UPDATE", "CONTRADICTION_RULES", "TRANSITION_BRANCH", "STICKY_TRACE_OVERLAY"],
        "contradiction_rules": contradiction_rules,
        "transition_branches": transition_branches,
        "contradiction_rule_count": len(contradiction_rules),
        "transition_branch_count": len(transition_branches),
        "result_policy": {"verdict_precedence": ["CONTRADICTION", "UNKNOWN", "CONSISTENT"], "contradictions_sticky": True, "first_event_id": "EARLIEST_CONTRADICTION", "consume_complete_sequence": True, "trace_initial_state": "INACTIVE", "trace_entries_per_event": 1, "parse_unknown_reason": "PARSE_STATUS_UNKNOWN", "parse_unknown_trace_overlay": "UNKNOWN_UNLESS_STICKY_CONTRADICTION", "contradiction_trace_overlay": "VIOLATED"},
    }


class CheckerTests(unittest.TestCase):
    def test_empty_sequence_is_consistent_with_initial_trace(self):
        expected = CheckResult(
            verdict="CONSISTENT", state_trace=(ObligationState.INACTIVE,)
        )

        self.assertEqual(check_event_local([]), expected)
        self.assertEqual(check_stateful([]), expected)

    def test_inputs_reject_non_lists_non_events_cross_scene_and_bad_order(self):
        invalid_inputs = (
            (),
            [object()],
            [event(scene_id="scene-a"), event(timestamp_us=1, scene_id="scene-b")],
            [event(timestamp_us=2), event(timestamp_us=1)],
            [event(timestamp_us=2, phase_index=1), event(timestamp_us=2, phase_index=0)],
        )

        for checker in (check_event_local, check_stateful):
            for invalid in invalid_inputs:
                with self.subTest(checker=checker.__name__, invalid=type(invalid).__name__):
                    with self.assertRaises((TypeError, ValueError)):
                        checker(invalid)  # type: ignore[arg-type]

    def test_event_local_misses_hold_go_but_stateful_finds_it(self):
        events = [hold_event(release=EvidenceValue.FALSE), proceed_event()]

        local = check_event_local(events)
        stateful = check_stateful(events)

        self.assertEqual(local.verdict, "CONSISTENT")
        self.assertNotIn(
            ContradictionType.HOLD_GO_CONFLICT, local.contradiction_types
        )
        self.assertEqual(stateful.verdict, "CONTRADICTION")
        self.assertEqual(
            stateful.contradiction_types,
            (ContradictionType.HOLD_GO_CONFLICT,),
        )
        self.assertEqual(stateful.first_event_id, "proceed")
        self.assertEqual(
            stateful.state_trace,
            (
                ObligationState.INACTIVE,
                ObligationState.ACTIVE,
                ObligationState.VIOLATED,
            ),
        )

    def test_hold_go_positive_negative_and_unknown_table(self):
        negative_go = with_evidence(
            proceed_event(),
            release=EvidenceValue.TRUE,
            satisfaction=EvidenceValue.TRUE,
        )
        unknown_go = with_evidence(
            proceed_event(), satisfaction=EvidenceValue.TRUE
        )
        cases = (
            (
                [hold_event(release=EvidenceValue.FALSE), proceed_event()],
                "CONTRADICTION",
                (ContradictionType.HOLD_GO_CONFLICT,),
            ),
            (
                [hold_event(release=EvidenceValue.FALSE), negative_go],
                "CONSISTENT",
                (),
            ),
            (
                [hold_event(release=EvidenceValue.UNKNOWN), unknown_go],
                "UNKNOWN",
                (),
            ),
        )

        for events, verdict, kinds in cases:
            with self.subTest(verdict=verdict):
                result = check_stateful(events)
                self.assertEqual(result.verdict, verdict)
                self.assertEqual(result.contradiction_types, kinds)

    def test_premature_release_positive_negative_and_unknown_table(self):
        positive = with_evidence(
            proceed_event(), release=EvidenceValue.FALSE
        )
        negative = with_evidence(
            proceed_event(), release=EvidenceValue.TRUE
        )
        unknown = proceed_event()

        for checker in (check_event_local, check_stateful):
            cases = (
                (positive, "CONTRADICTION", (ContradictionType.PREMATURE_RELEASE,)),
                (negative, "CONSISTENT", ()),
                (unknown, "CONSISTENT", ()),
            )
            for item, verdict, kinds in cases:
                with self.subTest(checker=checker.__name__, verdict=verdict):
                    result = checker([item])
                    self.assertEqual(result.verdict, verdict)
                    self.assertEqual(result.contradiction_types, kinds)

        active_unknown = [
            hold_event(release=EvidenceValue.UNKNOWN),
            with_evidence(proceed_event(), satisfaction=EvidenceValue.TRUE),
        ]
        self.assertEqual(check_stateful(active_unknown).verdict, "UNKNOWN")

    def test_order_violation_positive_negative_and_unknown_table(self):
        positive = with_evidence(
            proceed_event(), satisfaction=EvidenceValue.FALSE
        )
        negative = with_evidence(
            proceed_event(), satisfaction=EvidenceValue.TRUE
        )

        for checker in (check_event_local, check_stateful):
            with self.subTest(checker=checker.__name__, case="positive"):
                result = checker([positive])
                self.assertEqual(result.verdict, "CONTRADICTION")
                self.assertEqual(
                    result.contradiction_types,
                    (ContradictionType.ORDER_VIOLATION,),
                )
            with self.subTest(checker=checker.__name__, case="negative"):
                self.assertEqual(checker([negative]).verdict, "CONSISTENT")

        active_negative = [
            with_evidence(
                hold_event(release=EvidenceValue.FALSE),
                satisfaction=EvidenceValue.TRUE,
            ),
            with_evidence(
                proceed_event(),
                release=EvidenceValue.TRUE,
                satisfaction=EvidenceValue.TRUE,
            ),
        ]
        active_unknown = [
            hold_event(release=EvidenceValue.FALSE),
            with_evidence(proceed_event(), release=EvidenceValue.TRUE),
        ]
        self.assertEqual(check_stateful(active_negative).verdict, "CONSISTENT")
        self.assertEqual(check_stateful(active_unknown).verdict, "UNKNOWN")

    def test_stale_obligation_positive_negative_and_unknown_table(self):
        continuation_true = hold_event(
            timestamp_us=1, event_id="continued-after-release", release=EvidenceValue.TRUE
        )
        continuation_false = hold_event(
            timestamp_us=1, event_id="continued-held", release=EvidenceValue.FALSE
        )
        continuation_unknown = hold_event(
            timestamp_us=1, event_id="continued-unknown", release=EvidenceValue.UNKNOWN
        )
        cases = (
            (
                [hold_event(release=EvidenceValue.FALSE), continuation_true],
                "CONTRADICTION",
                (ContradictionType.STALE_OBLIGATION,),
            ),
            (
                [hold_event(release=EvidenceValue.FALSE), continuation_false],
                "CONSISTENT",
                (),
            ),
            (
                [hold_event(release=EvidenceValue.UNKNOWN), continuation_unknown],
                "UNKNOWN",
                (),
            ),
        )

        for events, verdict, kinds in cases:
            with self.subTest(verdict=verdict):
                result = check_stateful(events)
                self.assertEqual(result.verdict, verdict)
                self.assertEqual(result.contradiction_types, kinds)

        standalone = check_event_local([continuation_true])
        self.assertEqual(standalone.verdict, "CONSISTENT")
        self.assertNotIn(
            ContradictionType.STALE_OBLIGATION, standalone.contradiction_types
        )

    def test_explicit_false_release_precedence_excludes_hold_go_for_same_fact(self):
        go = with_evidence(
            proceed_event(),
            release=EvidenceValue.FALSE,
            satisfaction=EvidenceValue.FALSE,
        )

        result = check_stateful(
            [hold_event(release=EvidenceValue.FALSE), go]
        )

        self.assertEqual(
            result.contradiction_types,
            (
                ContradictionType.PREMATURE_RELEASE,
                ContradictionType.ORDER_VIOLATION,
            ),
        )
        self.assertNotIn(ContradictionType.HOLD_GO_CONFLICT, result.contradiction_types)

    def test_sticky_flags_keep_first_event_and_consume_complete_sequence(self):
        initial = with_evidence(
            hold_event(release=EvidenceValue.FALSE),
            satisfaction=EvidenceValue.FALSE,
        )
        hold_go = proceed_event(event_id="first-conflict", timestamp_us=1)
        premature = with_evidence(
            proceed_event(event_id="second-conflict", timestamp_us=2),
            release=EvidenceValue.FALSE,
        )
        stale = hold_event(
            event_id="third-conflict", timestamp_us=3, release=EvidenceValue.TRUE
        )

        result = check_stateful([initial, hold_go, premature, stale])

        self.assertEqual(result.verdict, "CONTRADICTION")
        self.assertEqual(
            result.contradiction_types,
            (
                ContradictionType.HOLD_GO_CONFLICT,
                ContradictionType.PREMATURE_RELEASE,
                ContradictionType.ORDER_VIOLATION,
                ContradictionType.STALE_OBLIGATION,
            ),
        )
        self.assertEqual(result.first_event_id, "first-conflict")
        self.assertEqual(len(result.state_trace), 5)
        self.assertEqual(
            result.state_trace[2:],
            (ObligationState.VIOLATED,) * 3,
        )

    def test_parse_unknown_is_coded_and_known_contradiction_dominates(self):
        parse_unknown = replace(
            event(), parse_status="UNKNOWN_PRIVATE_SENTINEL_DO_NOT_COPY"
        )

        unknown = check_stateful([parse_unknown])
        contradiction = check_stateful(
            [
                parse_unknown,
                with_evidence(
                    proceed_event(timestamp_us=1),
                    release=EvidenceValue.FALSE,
                ),
            ]
        )

        self.assertEqual(unknown.verdict, "UNKNOWN")
        self.assertEqual(unknown.unknown_reasons, ("PARSE_STATUS_UNKNOWN",))
        self.assertNotIn("PRIVATE_SENTINEL", json.dumps(unknown.to_dict()))
        self.assertEqual(contradiction.verdict, "CONTRADICTION")
        self.assertEqual(
            contradiction.contradiction_types,
            (ContradictionType.PREMATURE_RELEASE,),
        )
        self.assertEqual(
            contradiction.unknown_reasons, ("PARSE_STATUS_UNKNOWN",)
        )

    def test_ordered_same_source_phases_are_unknown_not_simultaneous_conflict(self):
        hold = replace(
            hold_event(release=EvidenceValue.UNKNOWN),
            timestamp_us=10,
            phase_index=0,
            permitted_next_action=Action.ACCELERATE_OR_PROCEED,
        )
        go = replace(proceed_event(), timestamp_us=10, phase_index=1)

        result = check_stateful([hold, go])

        self.assertEqual(result.verdict, "UNKNOWN")
        self.assertNotIn(
            ContradictionType.HOLD_GO_CONFLICT, result.contradiction_types
        )

    def test_distinct_overlapping_obligation_is_unknown_and_retains_first(self):
        first = replace(
            hold_event(release=EvidenceValue.FALSE), target="pedestrian"
        )
        overlap = replace(
            hold_event(
                timestamp_us=1,
                event_id="yield-other",
                release=EvidenceValue.UNKNOWN,
            ),
            action=Action.YIELD_OR_DECELERATE,
            target="vehicle",
        )

        overlap_only = check_stateful([first, overlap])
        retained = check_stateful(
            [first, overlap, proceed_event(timestamp_us=2)]
        )

        self.assertEqual(overlap_only.verdict, "UNKNOWN")
        self.assertIn("OVERLAPPING_OBLIGATION", overlap_only.unknown_reasons)
        self.assertEqual(retained.verdict, "CONTRADICTION")
        self.assertIn(
            ContradictionType.HOLD_GO_CONFLICT, retained.contradiction_types
        )

    def test_maintain_speed_never_fabricates_proceed_conflict(self):
        maintain = event(timestamp_us=1, action=Action.MAINTAIN_SPEED)
        released = with_evidence(maintain, release=EvidenceValue.TRUE)

        held = check_stateful(
            [hold_event(release=EvidenceValue.FALSE), maintain]
        )
        cleared = check_stateful(
            [hold_event(release=EvidenceValue.FALSE), released]
        )

        self.assertEqual(held.verdict, "CONSISTENT")
        self.assertEqual(held.state_trace[-1], ObligationState.ACTIVE)
        self.assertEqual(cleared.verdict, "CONSISTENT")
        self.assertEqual(cleared.state_trace[-1], ObligationState.RELEASED)
        self.assertEqual(held.contradiction_types, ())

    def test_transition_description_equals_complete_executable_branch_matrix(self):
        description = transition_rule_description()

        self.assertEqual(description, expected_transition_description())

    def test_every_described_transition_branch_matches_executable_terminal_state(self):
        hold_false = hold_event(release=EvidenceValue.FALSE)
        hold_unknown = hold_event(release=EvidenceValue.UNKNOWN)
        maintain = event(timestamp_us=1, action=Action.MAINTAIN_SPEED)
        same_false = hold_event(timestamp_us=1, event_id="same-false", release=EvidenceValue.FALSE)
        same_unknown = hold_event(timestamp_us=1, event_id="same-unknown", release=EvidenceValue.UNKNOWN)
        same_true = hold_event(timestamp_us=1, event_id="same-true", release=EvidenceValue.TRUE)
        cases = {
            "HOLD_START_RELEASED": ([hold_event(release=EvidenceValue.TRUE)], "CONSISTENT", ObligationState.RELEASED),
            "HOLD_START_SATISFIED": ([with_evidence(hold_unknown, satisfaction=EvidenceValue.TRUE)], "CONSISTENT", ObligationState.SATISFIED_WAIT_RELEASE),
            "HOLD_START_ACTIVE": ([hold_false], "CONSISTENT", ObligationState.ACTIVE),
            "HOLD_OVERLAP": ([replace(hold_false, target="a"), replace(same_unknown, action=Action.YIELD_OR_DECELERATE, target="b")], "UNKNOWN", ObligationState.UNKNOWN),
            "HOLD_CONTINUE_STALE": ([hold_false, same_true], "CONTRADICTION", ObligationState.VIOLATED),
            "HOLD_CONTINUE_SATISFIED": ([hold_false, with_evidence(same_false, satisfaction=EvidenceValue.TRUE)], "CONSISTENT", ObligationState.SATISFIED_WAIT_RELEASE),
            "HOLD_CONTINUE_ACTIVE": ([hold_false, same_false], "CONSISTENT", ObligationState.ACTIVE),
            "HOLD_CONTINUE_UNKNOWN": ([hold_unknown, same_unknown], "UNKNOWN", ObligationState.UNKNOWN),
            "PROCEED_NO_ACTIVE_FLAGGED": ([with_evidence(proceed_event(), release=EvidenceValue.FALSE)], "CONTRADICTION", ObligationState.VIOLATED),
            "PROCEED_NO_ACTIVE_CLEAR": ([proceed_event()], "CONSISTENT", ObligationState.INACTIVE),
            "PROCEED_ACTIVE_FLAGGED": ([hold_false, proceed_event()], "CONTRADICTION", ObligationState.VIOLATED),
            "PROCEED_ACTIVE_UNKNOWN": ([hold_unknown, proceed_event()], "UNKNOWN", ObligationState.UNKNOWN),
            "PROCEED_ACTIVE_RELEASED": ([hold_false, with_evidence(proceed_event(), release=EvidenceValue.TRUE, satisfaction=EvidenceValue.TRUE)], "CONSISTENT", ObligationState.RELEASED),
            "MAINTAIN_NO_ACTIVE": ([event(action=Action.MAINTAIN_SPEED)], "CONSISTENT", ObligationState.INACTIVE),
            "MAINTAIN_ACTIVE_RELEASED": ([hold_false, with_evidence(maintain, release=EvidenceValue.TRUE)], "CONSISTENT", ObligationState.RELEASED),
            "MAINTAIN_ACTIVE_SATISFIED": ([with_evidence(hold_false, satisfaction=EvidenceValue.TRUE), maintain], "CONSISTENT", ObligationState.SATISFIED_WAIT_RELEASE),
            "MAINTAIN_ACTIVE": ([hold_false, maintain], "CONSISTENT", ObligationState.ACTIVE),
            "MAINTAIN_ACTIVE_UNKNOWN": ([hold_unknown, maintain], "UNKNOWN", ObligationState.UNKNOWN),
        }
        branches = {
            branch["id"]: branch
            for branch in transition_rule_description().get("transition_branches", [])
        }

        self.assertEqual(set(branches), set(cases))
        for branch_id, (events, verdict, state) in cases.items():
            with self.subTest(branch=branch_id):
                result = check_stateful(events)
                self.assertEqual(result.verdict, verdict)
                self.assertEqual(result.state_trace[-1], state)
                self.assertEqual(branches[branch_id]["state"], state.value)

    def test_transition_hash_is_independent_canonical_sorted_compact_json(self):
        expected = expected_transition_description()
        canonical = json.dumps(
            expected, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        independently_calculated = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        self.assertNotIn("source_text", canonical.lower())
        self.assertEqual(
            independently_calculated,
            "e3f5e437dab029813dd4d5e515426e1079e29ce385108aea60665d87d130c4f8",
        )
        self.assertEqual(transition_table_sha256(), independently_calculated)

    def test_result_serialization_is_json_safe_and_round_trips(self):
        result = check_stateful(
            [
                replace(event(), parse_status="UNKNOWN_SYNTHETIC"),
                with_evidence(
                    proceed_event(timestamp_us=1),
                    release=EvidenceValue.FALSE,
                    satisfaction=EvidenceValue.FALSE,
                ),
            ]
        )

        payload = result.to_dict()

        self.assertEqual(CheckResult.from_dict(payload), result)
        self.assertEqual(json.loads(json.dumps(payload)), payload)
        self.assertEqual(len(result.state_trace), 3)


if __name__ == "__main__":
    unittest.main()
