"""Behavior and integrity tests for the controlled synthetic mutation benchmark."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from experiments.sequential_coc.contract_ir import (
    Action,
    ContractEvent,
    ContradictionType,
    EventWindow,
)
from experiments.sequential_coc.event_local_checker import check_event_local
from experiments.sequential_coc.mutation_generator import (
    DEFAULT_OUTPUT,
    MutationEligibilityError,
    MutationPair,
    generate_mutation_pairs,
    jsonl_bytes,
    mutate_window,
    read_mutation_pairs,
    validate_pair_diff,
    write_mutation_pairs,
)
from experiments.sequential_coc.stateful_checker import check_stateful


ROOT = Path(__file__).resolve().parents[3]
PRIMARY = (
    ContradictionType.HOLD_GO_CONFLICT,
    ContradictionType.PREMATURE_RELEASE,
    ContradictionType.ORDER_VIOLATION,
    ContradictionType.STALE_OBLIGATION,
)


def synthetic_window(kind: ContradictionType) -> EventWindow:
    scene = "a" * 64
    common = dict(
        scene_id=scene,
        provenance="CONTROLLED_SYNTHETIC_IR",
        parse_status="PARSED",
        source_text=None,
    )
    if kind is ContradictionType.HOLD_GO_CONFLICT:
        events = (
            ContractEvent(
                event_id="h0", timestamp_us=0, action=Action.STOP_OR_HOLD,
                satisfaction_known=True, satisfaction_value=True,
                release_known=True, release_value=False, target="controlled-target", **common,
            ),
            ContractEvent(event_id="h1", timestamp_us=1, action=Action.MAINTAIN_SPEED, **common),
        )
    elif kind is ContradictionType.PREMATURE_RELEASE:
        events = (
            ContractEvent(
                event_id="p0", timestamp_us=0, action=Action.ACCELERATE_OR_PROCEED,
                satisfaction_known=True, satisfaction_value=True,
                release_known=True, release_value=True, **common,
            ),
        )
    elif kind is ContradictionType.ORDER_VIOLATION:
        events = (
            ContractEvent(
                event_id="o0", timestamp_us=0, action=Action.ACCELERATE_OR_PROCEED,
                satisfaction_known=True, satisfaction_value=True,
                release_known=True, release_value=True, **common,
            ),
        )
    elif kind is ContradictionType.STALE_OBLIGATION:
        events = (
            ContractEvent(
                event_id="s0", timestamp_us=0, action=Action.YIELD_OR_DECELERATE,
                satisfaction_known=True, satisfaction_value=True,
                release_known=True, release_value=False, target="controlled-target", **common,
            ),
            ContractEvent(
                event_id="s1", timestamp_us=1, action=Action.YIELD_OR_DECELERATE,
                satisfaction_known=True, satisfaction_value=True,
                release_known=True, release_value=False, target="controlled-target", **common,
            ),
        )
    else:  # pragma: no cover - helper is called only with the finite primary tuple
        raise AssertionError(kind)
    return EventWindow("b" * 64, scene, events)


class MutationGeneratorTests(unittest.TestCase):
    def test_each_mutation_changes_exactly_its_predeclared_single_field(self):
        expected = {
            ContradictionType.HOLD_GO_CONFLICT: ("events[1].action", Action.MAINTAIN_SPEED.value, Action.ACCELERATE_OR_PROCEED.value),
            ContradictionType.PREMATURE_RELEASE: ("events[0].release_value", True, False),
            ContradictionType.ORDER_VIOLATION: ("events[0].satisfaction_value", True, False),
            ContradictionType.STALE_OBLIGATION: ("events[1].release_value", False, True),
        }

        for kind, (path, before, after) in expected.items():
            with self.subTest(kind=kind.value):
                pair = mutate_window(synthetic_window(kind), kind)
                self.assertEqual(pair.changed_fields, (path,))
                self.assertEqual(validate_pair_diff(pair), ((path, before, after),))
                self.assertEqual(pair.original.cluster_id, pair.mutated.cluster_id)
                self.assertNotEqual(pair.original.content_hash, pair.mutated.content_hash)
                self.assertEqual(check_stateful(list(pair.original.events)).verdict, "CONSISTENT")
                changed = check_stateful(list(pair.mutated.events))
                self.assertEqual(changed.verdict, "CONTRADICTION")
                self.assertEqual(changed.contradiction_types, (kind,))

    def test_pair_is_immutable_and_round_trips_strict_json(self):
        pair = mutate_window(synthetic_window(ContradictionType.HOLD_GO_CONFLICT), ContradictionType.HOLD_GO_CONFLICT)

        restored = MutationPair.from_dict(json.loads(json.dumps(pair.to_dict())))

        self.assertEqual(restored, pair)
        self.assertNotIn("source_text", json.dumps(pair.to_dict()))
        with self.assertRaises(FrozenInstanceError):
            pair.cluster_id = "changed"
        with self.assertRaises(AttributeError):
            pair.changed_fields.append("events[0].action")

    def test_mutate_window_rejects_unsupported_ineligible_contradictory_and_unknown_bases(self):
        base = synthetic_window(ContradictionType.PREMATURE_RELEASE)
        contradictory = EventWindow(
            base.window_id,
            base.cluster_id,
            (replace(base.events[0], release_value=False),),
        )
        unknown = EventWindow(
            base.window_id,
            base.cluster_id,
            (replace(base.events[0], parse_status="UNKNOWN_SYNTHETIC"),),
        )
        ineligible = EventWindow(
            base.window_id,
            base.cluster_id,
            (replace(base.events[0], action=Action.MAINTAIN_SPEED),),
        )

        cases = (
            (base, ContradictionType.UNSUPPORTED_CARRYOVER, "UNSUPPORTED_KIND"),
            (base, "NOT_A_KIND", "UNSUPPORTED_KIND"),
            (contradictory, ContradictionType.PREMATURE_RELEASE, "BASE_ALREADY_CONTRADICTORY"),
            (unknown, ContradictionType.PREMATURE_RELEASE, "BASE_UNKNOWN"),
            (ineligible, ContradictionType.PREMATURE_RELEASE, "INELIGIBLE_PREMATURE_RELEASE"),
        )
        for window, kind, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(MutationEligibilityError, f"^{reason}$"):
                mutate_window(window, kind)

    def test_seeded_generation_is_exactly_forty_pairs_with_pair_sample_units(self):
        pairs = generate_mutation_pairs(pairs_per_type=10, seed=20260806)

        self.assertEqual(len(pairs), 40)
        self.assertEqual(len({pair.pair_id for pair in pairs}), 40)
        self.assertEqual(len({pair.cluster_id for pair in pairs}), 40)
        self.assertEqual({kind: sum(pair.oracle is kind for pair in pairs) for kind in PRIMARY}, {kind: 10 for kind in PRIMARY})
        self.assertEqual(len({pair.original.content_hash for pair in pairs}), 40)
        self.assertEqual(len({pair.mutated.content_hash for pair in pairs}), 40)
        self.assertFalse({pair.original.content_hash for pair in pairs} & {pair.mutated.content_hash for pair in pairs})
        self.assertTrue(all(pair.original.cluster_id == pair.cluster_id == pair.mutated.cluster_id for pair in pairs))
        self.assertTrue(all(pair.original.window_id == pair.mutated.window_id for pair in pairs))
        self.assertTrue(all(pair.pair_id.isalnum() and len(pair.pair_id) == 64 for pair in pairs))

    def test_checker_outputs_are_recorded_but_do_not_change_generation_quota(self):
        pairs = generate_mutation_pairs(pairs_per_type=10, seed=20260806)

        local_original = [pair.original_event_local.verdict for pair in pairs]
        local_mutated = [pair.mutated_event_local.verdict for pair in pairs]
        self.assertEqual(local_original.count("CONSISTENT"), 40)
        self.assertEqual(local_mutated.count("CONTRADICTION"), 20)
        self.assertEqual(local_mutated.count("CONSISTENT"), 20)
        self.assertTrue(all(pair.original_stateful.verdict == "CONSISTENT" for pair in pairs))
        self.assertTrue(all(pair.mutated_stateful.contradiction_types == (pair.oracle,) for pair in pairs))
        self.assertTrue(all(pair.original_event_local == check_event_local(list(pair.original.events)) for pair in pairs))

    def test_same_seed_is_byte_identical_and_different_seed_changes_order_and_ids_only(self):
        first = generate_mutation_pairs(10, 20260806)
        repeated = generate_mutation_pairs(10, 20260806)
        different = generate_mutation_pairs(10, 20260807)

        self.assertEqual(jsonl_bytes(first), jsonl_bytes(repeated))
        self.assertNotEqual(jsonl_bytes(first), jsonl_bytes(different))
        for pairs in (first, different):
            self.assertEqual({kind: sum(pair.oracle is kind for pair in pairs) for kind in PRIMARY}, {kind: 10 for kind in PRIMARY})
            self.assertEqual(sorted(pair.changed_fields for pair in pairs).count(("events[0].release_value",)), 10)

    def test_writer_is_atomic_strict_round_trip_and_restricted(self):
        pairs = generate_mutation_pairs(2, 20260806)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "restricted" / "mutations.jsonl"
            write_mutation_pairs(pairs, path)

            self.assertEqual(read_mutation_pairs(path), pairs)
            self.assertEqual(path.read_bytes(), jsonl_bytes(pairs))
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(path.parent.glob(".*.tmp")), [])

            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "DUPLICATE_PAIR_ID"):
                write_mutation_pairs((pairs[0], pairs[0]), path)
            self.assertEqual(path.read_bytes(), before)

    def test_reader_rejects_extra_fields_tampering_and_blank_rows(self):
        pair = mutate_window(synthetic_window(ContradictionType.ORDER_VIOLATION), ContradictionType.ORDER_VIOLATION)
        payload = pair.to_dict()
        variants = (
            {**payload, "unexpected": True},
            {**payload, "oracle": ContradictionType.PREMATURE_RELEASE.value},
            {**payload, "changed_fields": ["events[0].release_value"]},
            {**payload, "original": {**payload["original"], "unexpected": True}},
            {
                **payload,
                "mutated": {
                    **payload["mutated"],
                    "events": [
                        {**payload["mutated"]["events"][0], "unexpected": True}
                    ],
                },
            },
            {
                **payload,
                "checker_results": {
                    **payload["checker_results"],
                    "original": {
                        **payload["checker_results"]["original"],
                        "stateful": {
                            **payload["checker_results"]["original"]["stateful"],
                            "unexpected": True,
                        },
                    },
                },
            },
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mutations.jsonl"
            for variant in variants:
                path.write_text(json.dumps(variant) + "\n", encoding="utf-8")
                with self.assertRaises((TypeError, ValueError)):
                    read_mutation_pairs(path)
            path.write_text(json.dumps(payload) + "\n\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "BLANK_JSONL_ROW"):
                read_mutation_pairs(path)

    def test_reader_rejects_duplicate_keys_at_top_level_and_nested_objects(self):
        pair = mutate_window(
            synthetic_window(ContradictionType.ORDER_VIOLATION),
            ContradictionType.ORDER_VIOLATION,
        )
        canonical = json.dumps(pair.to_dict(), sort_keys=True, separators=(",", ":"))
        duplicates = (
            canonical.replace(
                "{",
                '{"schema_version":"duplicate-before-canonical",',
                1,
            ),
            canonical.replace(
                '"events":[{',
                '"events":[{"action":"MAINTAIN_SPEED",',
                1,
            ),
            canonical.replace(
                '"stateful":{',
                '"stateful":{"verdict":"CONSISTENT",',
                1,
            ),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mutations.jsonl"
            for row in duplicates:
                path.write_text(row + "\n", encoding="utf-8")
                with self.subTest(row=row[:40]), self.assertRaisesRegex(
                    ValueError, "^DUPLICATE_JSON_KEY$"
                ):
                    read_mutation_pairs(path)

    def test_production_jsonl_has_expected_hash_round_trip_modes_and_no_text(self):
        expected = generate_mutation_pairs(10, 20260806)

        self.assertTrue(DEFAULT_OUTPUT.is_file())
        self.assertEqual(DEFAULT_OUTPUT.read_bytes(), jsonl_bytes(expected))
        self.assertEqual(read_mutation_pairs(DEFAULT_OUTPUT), expected)
        self.assertEqual(DEFAULT_OUTPUT.stat().st_mode & 0o777, 0o600)
        self.assertEqual(DEFAULT_OUTPUT.parent.stat().st_mode & 0o777, 0o700)
        self.assertNotIn(b"source_text", DEFAULT_OUTPUT.read_bytes())
        self.assertEqual(hashlib.sha256(DEFAULT_OUTPUT.read_bytes()).hexdigest(), hashlib.sha256(jsonl_bytes(expected)).hexdigest())

    def test_direct_cli_is_deterministic_and_reports_pair_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "restricted" / "pairs.jsonl"
            result = subprocess.run(
                [sys.executable, "experiments/sequential_coc/mutation_generator.py", "--pairs-per-type", "10", "--seed", "20260806", "--output", str(output)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["pair_count"], 40)
            self.assertEqual(summary["cluster_count"], 40)
            self.assertEqual(summary["sample_unit"], "PAIR")
            self.assertEqual(summary["type_counts"], {kind.value: 10 for kind in PRIMARY})
            self.assertEqual(read_mutation_pairs(output), generate_mutation_pairs(10, 20260806))


if __name__ == "__main__":
    unittest.main()
