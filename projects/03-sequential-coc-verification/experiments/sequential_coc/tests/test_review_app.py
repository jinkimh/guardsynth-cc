"""Behavior tests for the restricted, blinded natural-sequence review packet."""

from __future__ import annotations

import csv
import io
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from experiments.sequential_coc.extract_windows import (
    NATURAL_WINDOWS_PATH,
    RawEvent,
    build_raw_event_windows,
    read_natural_windows,
)
from experiments.sequential_coc.build_review_app import (
    CONTRACT_CHOICES,
    CONTRACT_REVIEW_FIELDS,
    OUTPUT_DIR,
    REVIEW_DIR,
    ReviewItem,
    build_contract_review_page,
    order_for_reviewer,
    review_already_started,
    select_review_items,
    _protocol,
    _write_restricted,
)


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())


def _synthetic_windows():
    scenes = {
        "source-private-1": [
            RawEvent("source-private-1", 1_000_000, "Please stop for the marker."),
            RawEvent("source-private-1", 2_500_000, "Then proceed carefully."),
        ],
        "source-private-2": [
            RawEvent("source-private-2", 1_000_000, "Please yield for the marker."),
            RawEvent("source-private-2", 2_000_000, "Maintain the current speed."),
        ],
    }
    return build_raw_event_windows(scenes)


class ReviewAppTests(unittest.TestCase):
    def test_page_blinds_source_and_checker_metadata_in_all_content(self):
        item = ReviewItem(
            review_id="REV-0123456789abcdef",
            event_texts=("Please stop for the marker.", "Then proceed carefully."),
            relative_times_s=(0.0, 1.5),
        )

        page = build_contract_review_page("A", [item])

        for forbidden in (
            "source-private-1",
            "1000000",
            "/restricted/source/path",
            "candidate",
            "control",
            "checker",
            "UPPAAL",
            "oracle",
            "mutation",
        ):
            self.assertNotIn(forbidden, page)
        self.assertIn("CSV 저장", page)
        self.assertIn("AMBIGUOUS", page)

    def test_page_escapes_text_and_keeps_coc_out_of_javascript(self):
        attack = '</p><script src="https://bad.invalid/x.js">alert(1)</script><p>'
        item = ReviewItem("REV-fedcba9876543210", (attack, "Proceed."), (0.0, 1.0))

        page = build_contract_review_page("B", [item])

        self.assertNotIn(attack, page)
        self.assertIn("&lt;script", page)
        script = page.split("<script>", 1)[1].split("</script>", 1)[0]
        self.assertNotIn("bad.invalid", script)
        self.assertIn("default-src 'none'", page)
        self.assertNotIn('<script src="https://', page)

    def test_contract_review_never_asks_actual_satisfaction_or_release_state(self):
        item = ReviewItem("REV-0123456789abcdef", ("Stop.", "Proceed."), (0.0, 1.0))

        page = build_contract_review_page("A", [item])

        self.assertNotIn("satisfaction_state", page)
        self.assertNotIn("release_state", page)
        self.assertIn("temporal_requirement_explicit", page)
        self.assertIn("textual_consistency", page)

    def test_korean_manual_and_embedded_guide_explain_text_only_relations(self):
        item = ReviewItem("REV-0123456789abcdef", ("Stop.", "Proceed."), (0.0, 1.0))

        protocol = _protocol()
        page = build_contract_review_page("A", [item])

        for required in (
            "설문 프로토콜 — 한국어판",
            "TEXTUAL_CONTRADICTION",
            "TEXTUALLY_CONSISTENT",
            "UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED",
            "AMBIGUOUS_TEXT",
            "NOT_APPLICABLE_NO_TEMPORAL_REQUIREMENT",
            "문장 자체가 모호",
            "실제 상태 증거",
            "신호가 아직 적색이므로 출발한다",
            "보행자가 실제로 지나갔는지",
        ):
            self.assertIn(required, protocol)
        self.assertIn("<details", page)
        self.assertIn("판정 도움말과 합성 예제", page)
        self.assertIn("TEXTUAL_CONTRADICTION", page)
        self.assertIn("UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED", page)
        self.assertIn("실제 상태나 안전을 추측하지 마십시오", page)

    def test_contract_review_csv_contract_is_exact(self):
        self.assertEqual(
            CONTRACT_REVIEW_FIELDS,
            (
                "review_id",
                "temporal_requirement_explicit",
                "required_action_sequence",
                "textual_consistency",
                "notes",
            ),
        )
        self.assertEqual(
            CONTRACT_CHOICES["textual_consistency"],
            (
                "TEXTUAL_CONTRADICTION",
                "TEXTUALLY_CONSISTENT",
                "UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED",
                "AMBIGUOUS_TEXT",
                "NOT_APPLICABLE_NO_TEMPORAL_REQUIREMENT",
            ),
        )
        item = ReviewItem("REV-0123456789abcdef", ("Stop.", "Proceed."), (0.0, 1.0))
        page = build_contract_review_page("A", [item])
        self.assertIn(json.dumps(list(CONTRACT_REVIEW_FIELDS), separators=(",", ":")), page)
        self.assertIn("Object.keys(fields).every", page)
        self.assertIn('new Blob(["\ufeff"', page)
        self.assertIn("contract_review_A.csv", page)

    def test_ordered_action_builder_covers_stop_then_acceleration(self):
        item = ReviewItem(
            "REV-0123456789abcdef",
            (
                "Stop at the line.",
                "Remain stopped.",
                "Then accelerate to proceed.",
                "Continue accelerating.",
            ),
            (0.0, 1.0, 2.0, 3.0),
        )

        page = build_contract_review_page("A", [item])
        protocol = _protocol()

        self.assertIn('type="hidden" name="required_action_sequence"', page)
        self.assertIn('data-action="STOP_OR_HOLD"', page)
        self.assertIn('data-action="ACCELERATE_OR_PROCEED"', page)
        self.assertIn("appendAction", page)
        self.assertIn("undoAction", page)
        self.assertIn("STOP_OR_HOLD&gt;ACCELERATE_OR_PROCEED", page)
        self.assertIn("STOP_OR_HOLD>ACCELERATE_OR_PROCEED", protocol)
        for removed in (
            "obligation_explicit",
            "required_action\"",
            "persistence_explicit",
            "release_condition_explicit",
            "ordered_steps_explicit",
            "textual_relation",
            "state_evidence_needed",
            "evidence_sufficiency",
            "confidence\"",
        ):
            self.assertNotIn(removed, page)

    def test_common_action_sequences_are_visible_one_click_choices(self):
        item = ReviewItem(
            "REV-0123456789abcdef",
            ("Stop at the intersection and then accelerate to proceed.", "Proceed."),
            (0.0, 1.0),
        )

        page = build_contract_review_page("A", [item])

        self.assertIn("자주 쓰는 행동열 바로 선택", page)
        self.assertIn(
            'data-sequence="STOP_OR_HOLD&gt;ACCELERATE_OR_PROCEED"', page
        )
        self.assertIn("정지·유지 → 가속·진행", page)
        self.assertIn(
            'data-sequence="YIELD_OR_DECELERATE&gt;ACCELERATE_OR_PROCEED"', page
        )
        self.assertIn("setActionSequence", page)

    def test_each_survey_question_has_korean_explanation_and_example(self):
        item = ReviewItem(
            "REV-0123456789abcdef",
            ("Stop until the pedestrian passes.", "Then proceed."),
            (0.0, 1.0),
        )

        page = build_contract_review_page("A", [item])
        protocol = _protocol()

        for required in (
            "1. 시간적 요구가 명시되어 있습니까?",
            "시간적 요구란 행동을 언제까지 유지하거나 언제 다음 행동으로 바꿀지",
            "예: ‘보행자가 지나갈 때까지 정지한다.’",
            "2. 요구 행동열은 무엇입니까?",
            "정지·대기 (STOP_OR_HOLD)",
            "가속·진행 (ACCELERATE_OR_PROCEED)",
            "3. 텍스트 자체의 시간적 관계는 어떻습니까?",
            "텍스트상 모순 (TEXTUAL_CONTRADICTION)",
            "예: ‘신호가 녹색이 될 때까지 정지한다.’ 다음에",
            "외부 증거 필요 (UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED)",
            "실제로 지나갔는지는 영상이나 상태 정보가 필요",
        ):
            self.assertIn(required, page)
        self.assertIn("세 문항 작성 예", protocol)
        self.assertIn("시간적 요구=YES", protocol)
        self.assertIn("행동열=STOP_OR_HOLD>ACCELERATE_OR_PROCEED", protocol)

    def test_review_already_started_conservatively_detects_every_human_csv(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            review_dir = Path(temporary_directory)
            self.assertFalse(review_already_started(review_dir))

            for name in (
                "contract_review_A.csv",
                "contract_review_B.csv",
                "review_A.csv",
                "review_B.csv",
                "panel_consensus.csv",
                "human_notes.csv",
            ):
                (review_dir / name).write_text("review_id\n", encoding="utf-8")
                self.assertTrue(review_already_started(review_dir))
                (review_dir / name).unlink()

    def test_restricted_writer_publishes_verified_mode_0600_content(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "review.html"

            _write_restricted(path, "verified content")

            self.assertEqual(path.read_text(encoding="utf-8"), "verified content")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_selection_uses_earliest_candidate_and_eligible_noncandidate_control(self):
        items, mapping, stats = select_review_items(_synthetic_windows())

        self.assertEqual(stats["candidate_raw_pairs"], 1)
        self.assertEqual(stats["candidate_raw_scenes"], 1)
        self.assertEqual(stats["selected_candidate_windows"], 1)
        self.assertEqual(stats["selected_control_windows"], 1)
        self.assertEqual(stats["independent_clusters"], 2)
        self.assertEqual(len(items), 2)
        self.assertEqual(len({row["cluster_id"] for row in mapping}), 2)
        self.assertEqual({row["group"] for row in mapping}, {"CANDIDATE", "CONTROL"})

    def test_reviewer_orders_have_identical_membership_and_distinct_fixed_order(self):
        items = [
            ReviewItem(f"REV-{index:016x}", ("Stop.", "Proceed."), (0.0, 1.0))
            for index in range(10)
        ]

        a_first = order_for_reviewer("A", items)
        a_second = order_for_reviewer("A", items)
        b_order = order_for_reviewer("B", items)

        self.assertEqual(a_first, a_second)
        self.assertEqual({item.review_id for item in a_first}, {item.review_id for item in b_order})
        self.assertNotEqual(
            [item.review_id for item in a_first], [item.review_id for item in b_order]
        )

    def test_production_selector_matches_approved_counts_without_checker_input(self):
        _, mapping, stats = select_review_items(read_natural_windows(NATURAL_WINDOWS_PATH))

        self.assertEqual(stats["candidate_raw_pairs"], 23)
        self.assertEqual(stats["candidate_raw_scenes"], 15)
        self.assertEqual(stats["selected_candidate_windows"], 15)
        self.assertEqual(stats["selected_candidate_scenes"], 15)
        # Only 12 non-candidate scenes satisfy the predeclared immediate-successor
        # eligibility rule.  The policy forbids duplicates or broader fallbacks.
        self.assertEqual(stats["selected_control_windows"], 12)
        self.assertEqual(stats["selected_control_scenes"], 12)
        self.assertEqual(stats["independent_clusters"], 27)
        self.assertEqual(len({row["cluster_id"] for row in mapping}), 27)

    def test_production_packet_files_are_restricted_and_mapping_is_separate(self):
        expected = {
            "REVIEW_PROTOCOL.md",
            "REVIEW_A.html",
            "REVIEW_B.html",
            "adjudication-mapping.json",
            "packet-manifest.json",
        }
        present = {path.name for path in REVIEW_DIR.iterdir() if path.is_file()}
        # Completed human exports and post-review adjudication artifacts may now
        # coexist with the immutable blinded packet.  The packet membership is
        # still checked below against its own manifest.
        self.assertTrue(expected <= present)
        allowed_post_review = {
            "contract_review_A(cjh).csv",
            "contract_review_A(ljy).csv",
            "contract_review_B(cjw).csv",
            "contract_review_B(lsj).csv",
            "panel-review-summary.json",
            "PANEL_ADJUDICATION.html",
            "contract_review_consensus.csv",
        }
        self.assertFalse(present - expected - allowed_post_review)
        self.assertEqual(os.stat(REVIEW_DIR).st_mode & 0o777, 0o700)
        for name in present:
            self.assertEqual(os.stat(REVIEW_DIR / name).st_mode & 0o777, 0o600)

        mapping = json.loads((REVIEW_DIR / "adjudication-mapping.json").read_text())
        reviewer_orders = []
        for reviewer in ("A", "B"):
            page = (REVIEW_DIR / f"REVIEW_{reviewer}.html").read_text(encoding="utf-8")
            for row in mapping:
                self.assertNotIn(row["cluster_id"], page)
                self.assertNotIn(row["window_id"], page)
            self.assertNotIn("adjudication-mapping.json", page)
            self.assertNotIn("satisfaction_state", page)
            self.assertNotIn("release_state", page)
            self.assertIn("temporal_requirement_explicit", page)
            self.assertIn("required_action_sequence", page)
            self.assertIn("textual_consistency", page)
            reviewer_orders.append(
                [part.split('"', 1)[0] for part in page.split('data-review-id="')[1:]]
            )
        self.assertEqual(set(reviewer_orders[0]), set(reviewer_orders[1]))
        self.assertNotEqual(reviewer_orders[0], reviewer_orders[1])

        packet = json.loads((REVIEW_DIR / "packet-manifest.json").read_text())
        self.assertEqual(packet["packet_status"], "WAITING_FOR_CONTRACT_REVIEW")
        self.assertEqual(packet["evidence_availability"], "COC_TEXT_AND_RELATIVE_TIME_ONLY")
        for name, checkpoint in packet["artifacts"].items():
            path = REVIEW_DIR / name
            self.assertEqual(checkpoint["bytes"], path.stat().st_size)
            self.assertEqual(checkpoint["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_restricted_source_text_occurs_only_in_authorized_html_and_natural_jsonl(self):
        windows = read_natural_windows(NATURAL_WINDOWS_PATH)
        protected = {event.source_text for window in windows for event in window.events if event.source_text}
        targets = [
            OUTPUT_DIR / "inventory.json",
            OUTPUT_DIR / "mutations.jsonl",
            OUTPUT_DIR / "RUN_LOG.md",
            OUTPUT_DIR / "MANIFEST.sha256",
            REVIEW_DIR / "REVIEW_PROTOCOL.md",
            REVIEW_DIR / "adjudication-mapping.json",
            REVIEW_DIR / "packet-manifest.json",
            ROOT / ".superpowers/sdd/2026-08-06-sequential-coc-consistency-implementation/task-8-report.md",
        ]
        for target in targets:
            if not target.exists():
                continue
            content = target.read_text(encoding="utf-8")
            self.assertFalse(any(text in content for text in protected), target)


if __name__ == "__main__":
    unittest.main()
