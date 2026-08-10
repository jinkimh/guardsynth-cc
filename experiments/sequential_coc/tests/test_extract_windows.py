import hashlib
import json
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pandas as pd

from experiments.sequential_coc.extract_windows import (
    LEXICAL_PATTERNS,
    OUTPUT_DIR,
    PAPER_ROOT,
    RawEvent,
    RawEventWindow,
    _checkpoint_inventory,
    build_raw_event_windows,
    build_event_windows,
    build_inventory,
    load_local_trajectory_raw_events,
    load_reasoning_events,
    local_egomotion_scene_ids,
    read_natural_windows,
    screen_transition_candidates,
    write_natural_windows,
    write_inventory,
)
from experiments.sequential_coc.tests.fixtures import event


ROOT = Path(__file__).resolve().parents[3]
REASONING = ROOT / "data/baseline/coc_nusc/reasoning/ood_reasoning.parquet"
EGO_DIR = ROOT / "data/baseline/coc_nusc/labels/egomotion"


class ExtractWindowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = load_reasoning_events(REASONING)
        cls.inventory = build_inventory(cls.events, local_egomotion_scene_ids(EGO_DIR))

    def test_inventory_preserves_known_chunk0_counts(self):
        inventory = self.inventory

        self.assertEqual(inventory["trajectory_subset"]["scene_count"], 94)
        self.assertEqual(inventory["trajectory_subset"]["event_count"], 403)
        self.assertEqual(inventory["trajectory_subset"]["scenes_with_two_or_more"], 90)
        self.assertEqual(inventory["trajectory_subset"]["adjacent_pair_count"], 309)

    def test_window_keeps_scene_cluster_and_up_to_three_followups(self):
        events = [event(3_000_000), event(1_000_000), event(2_000_000), event(4_000_000)]

        windows = build_event_windows("scene-a", events, max_followups=3)

        self.assertEqual(
            [item.timestamp_us for item in windows[0].events],
            [1_000_000, 2_000_000, 3_000_000, 4_000_000],
        )
        self.assertEqual(windows[0].cluster_id, "scene-a")

    def test_windows_stably_sort_and_preserve_duplicate_events(self):
        events = [
            event(2, event_id="later"),
            event(1, event_id="first-duplicate"),
            event(1, event_id="second-duplicate"),
            event(3, event_id="last"),
        ]

        windows = build_event_windows("scene-a", events)

        self.assertEqual(len(windows), 3)
        self.assertEqual([len(window.events) for window in windows], [4, 3, 2])
        self.assertEqual(
            [item.event_id for item in windows[0].events],
            ["first-duplicate", "second-duplicate", "later", "last"],
        )

    def test_window_ids_are_deterministic_anonymous_and_content_sensitive(self):
        events = [
            replace(event(1, event_id="one", scene_id="scene-private"), source_text="restricted one"),
            replace(event(2, event_id="two", scene_id="scene-private"), source_text="restricted two"),
        ]

        first = build_event_windows("scene-private", events)[0]
        second = build_event_windows("scene-private", events)[0]
        changed = build_event_windows(
            "scene-private", [replace(events[0], source_text="different"), events[1]]
        )[0]

        self.assertEqual(first.window_id, second.window_id)
        self.assertNotIn("scene-private", first.window_id)
        self.assertEqual(len(first.window_id), 64)
        self.assertNotEqual(first.window_id, changed.window_id)

    def test_public_windows_reject_cross_scene_mixing(self):
        with self.assertRaises(ValueError):
            build_event_windows("scene-a", [event(1), event(2, scene_id="scene-b")])

    def test_raw_extraction_preserves_all_local_scene_windows(self):
        raw_scenes = load_local_trajectory_raw_events(REASONING, EGO_DIR)
        windows = build_raw_event_windows(raw_scenes)

        self.assertEqual(len(raw_scenes), 94)
        self.assertEqual(len(windows), 309)
        self.assertEqual(len({window.cluster_id for window in windows}), 90)
        self.assertTrue(all(2 <= len(window.events) <= 4 for window in windows))
        self.assertTrue(all(window.cluster_id == window.events[0].scene_id for window in windows))

    def test_transition_screening_reports_candidate_windows_and_clusters(self):
        candidates = screen_transition_candidates(
            build_raw_event_windows(load_local_trajectory_raw_events(REASONING, EGO_DIR))
        )

        self.assertEqual(set(candidates), {"candidate_window_ids", "candidate_cluster_ids"})
        self.assertEqual(len(candidates["candidate_window_ids"]), 23)
        self.assertEqual(len(candidates["candidate_cluster_ids"]), 15)

    def test_natural_windows_jsonl_round_trip_is_restricted(self):
        windows = build_raw_event_windows(
            {
                "scene-test": [
                    RawEvent("scene-test", 1, "one"),
                    RawEvent("scene-test", 2, "two"),
                ]
            }
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "restricted" / "natural-windows.jsonl"
            write_natural_windows(windows, path)

            self.assertEqual(read_natural_windows(path), windows)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_raw_window_rejects_malformed_or_tampered_jsonl_identity(self):
        window = build_raw_event_windows(
            {"scene-test": [RawEvent("scene-test", 1, "one"), RawEvent("scene-test", 2, "two")]}
        )[0]
        payload = window.to_dict()

        malformed_id = {**payload, "window_id": "g" * 64}
        missing_hash = {
            **payload,
            "events": [{key: value for key, value in payload["events"][0].items() if key != "source_text_sha256"}]
            + payload["events"][1:],
        }
        mismatched_hash = {
            **payload,
            "events": [{**payload["events"][0], "source_text_sha256": "0" * 64}]
            + payload["events"][1:],
        }
        tampered_content = {
            **payload,
            "events": [
                {
                    **payload["events"][0],
                    "source_text": "changed",
                    "source_text_sha256": RawEvent("scene-test", 1, "changed").source_text_sha256,
                }
            ]
            + payload["events"][1:],
        }

        for invalid in (malformed_id, missing_hash, mismatched_hash, tampered_content):
            with self.subTest(invalid=invalid is malformed_id):
                with self.assertRaises((TypeError, ValueError)):
                    RawEventWindow.from_dict(invalid)

    def test_raw_window_rejects_extra_keys_and_five_event_rows(self):
        window = build_raw_event_windows(
            {"scene-test": [RawEvent("scene-test", 1, "one"), RawEvent("scene-test", 2, "two")]}
        )[0]
        payload = window.to_dict()
        extra_window_key = {**payload, "unexpected": True}
        extra_event_key = {
            **payload,
            "events": [{**payload["events"][0], "unexpected": True}] + payload["events"][1:],
        }
        five_events = {**payload, "events": payload["events"] * 2 + [payload["events"][0]]}

        for invalid in (extra_window_key, extra_event_key, five_events):
            with self.subTest(invalid=invalid is extra_window_key):
                with self.assertRaises((TypeError, ValueError)):
                    RawEventWindow.from_dict(invalid)

    def test_manifest_includes_restricted_natural_windows_hash_only(self):
        manifest = (OUTPUT_DIR / "MANIFEST.sha256").read_text(encoding="utf-8")

        self.assertIn("natural-windows.jsonl", manifest)

    def test_manifest_covers_final_outputs_once_and_every_hash_matches(self):
        entries = [
            line.split(maxsplit=1)
            for line in (OUTPUT_DIR / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        paths = [path for _, path in entries]
        restricted_outputs = {
            path.relative_to(OUTPUT_DIR).as_posix()
            for path in OUTPUT_DIR.rglob("*")
            if path.is_file() and path.name != "MANIFEST.sha256"
        }

        self.assertTrue(restricted_outputs.issubset(set(paths)))
        self.assertIn(
            "../../../../papers/demestic-journal/latex-kiee-review-2022-coc-audit/main.pdf",
            paths,
        )
        self.assertEqual(len(paths), len(set(paths)))
        for expected_hash, relative_path in entries:
            target = OUTPUT_DIR / relative_path
            self.assertTrue(target.is_file(), relative_path)
            self.assertEqual(
                hashlib.sha256(target.read_bytes()).hexdigest(),
                expected_hash,
                relative_path,
            )

    def test_review_packet_manifest_waits_for_contract_review(self):
        packet = json.loads(
            (OUTPUT_DIR / "review" / "packet-manifest.json").read_text(encoding="utf-8")
        )

        self.assertEqual(packet["packet_status"], "WAITING_FOR_CONTRACT_REVIEW")

    def test_direct_script_entrypoint_loads_package_imports(self):
        result = subprocess.run(
            [sys.executable, "experiments/sequential_coc/extract_windows.py", "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--write-windows", result.stdout)

    def test_inventory_preserves_all_reasoning_counts(self):
        self.assertEqual(
            self.inventory["all_reasoning"],
            {
                "scene_count": 743,
                "event_count": 3218,
                "scenes_with_two_or_more": 677,
                "adjacent_pair_count": 2475,
            },
        )

    def test_inventory_preserves_all_lexical_counts_with_conservative_predicate(self):
        self.assertEqual(LEXICAL_PATTERNS["pedestrian_or_crosswalk"], r"\b(?:pedestrian|crosswalk)\b")
        self.assertEqual(
            self.inventory["trajectory_subset_lexical"],
            {
                "stop": 49,
                "yield": 17,
                "accelerate": 112,
                "decelerate": 108,
                "pedestrian_or_crosswalk": 23,
            },
        )

    def test_inventory_preserves_transparent_transition_selector(self):
        selector = self.inventory["trajectory_subset_transition_selector"]
        self.assertEqual(selector["pair_count"], 23)
        self.assertEqual(selector["scene_count"], 15)
        self.assertEqual(selector["candidate_status"], "AUTOMATED_CANDIDATE_NOT_GROUND_TRUTH")
        self.assertEqual(selector["prior_count_status"], "PRIOR_COUNT_NOT_REPRODUCIBLE")

    def test_loader_sorts_events_by_integer_timestamp(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "reasoning.parquet"
            pd.DataFrame(
                {
                    "events": [
                        json.dumps(
                            [
                                {"event_start_timestamp": 20, "cot": "later"},
                                {"event_start_timestamp": 3, "cot": "earlier"},
                            ]
                        )
                    ]
                },
                index=["scene-test"],
            ).to_parquet(path)

            loaded = load_reasoning_events(path)

        self.assertEqual(
            [event["event_start_timestamp"] for event in loaded["scene-test"]], [3, 20]
        )

    def test_checkpoint_targets_current_kiee_paper_tree(self):
        expected = ROOT / "papers/demestic-journal/latex-kiee-review-2022-coc-audit"
        self.assertEqual(PAPER_ROOT, expected)
        self.assertGreater(_checkpoint_inventory()["kiee_paper_tree"]["file_count"], 0)

    def test_written_inventory_excludes_source_text_and_restricts_permissions(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "restricted" / "inventory.json"
            write_inventory({"test_inventory": {"event_count": 0}}, path)

            contents = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("cot", contents)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_build_inventory_never_serializes_restricted_event_text_or_fields(self):
        sentinel = "UNIQUE_RESTRICTED_TEXT_SENTINEL_9b7d3a"
        inventory = build_inventory(
            {
                "scene-synthetic": [
                    {
                        "event_start_timestamp": 123,
                        "cot": sentinel,
                        "quality": {"internal": "metadata"},
                        "quality_pass": True,
                    }
                ]
            },
            {"scene-synthetic"},
        )

        serialized = json.dumps(inventory, sort_keys=True)
        self.assertNotIn(sentinel, serialized)
        self.assertNotIn('"cot"', serialized)
        self.assertNotIn('"event_start_timestamp"', serialized)
        self.assertNotIn('"quality"', serialized)

    def test_production_task1_outputs_have_restricted_permissions(self):
        self.assertEqual(OUTPUT_DIR.stat().st_mode & 0o777, 0o700)
        for name in ("inventory.json", "RUN_LOG.md", "MANIFEST.sha256"):
            self.assertEqual((OUTPUT_DIR / name).stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
