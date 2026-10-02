"""TDD contract for the M15 common baseline protocol and channel firewall."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth.baseline_protocol import (
    ALL_BASELINES,
    BASELINE_REGISTRY,
    baseline_manifest,
    run_baseline,
)
from guard_synth.frontend_matrix import build_locked_frontend_cases
from guard_synth.source_catalog import KR_FIXTURE_PATH, load_source_catalog


class BaselineProtocolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_source_catalog(KR_FIXTURE_PATH)
        cls.request = build_locked_frontend_cases()[0]["request"]

    def test_registry_locks_b0_through_b8_and_b13(self) -> None:
        self.assertEqual(tuple(BASELINE_REGISTRY), ALL_BASELINES)
        manifest = baseline_manifest()
        self.assertEqual(len(manifest["baselines"]), 10)
        self.assertTrue(manifest["locked_after_evaluation_start"])

    def test_all_adapters_return_schema_valid_deterministic_records(self) -> None:
        for baseline_id in ALL_BASELINES:
            with self.subTest(baseline=baseline_id):
                first = run_baseline(
                    baseline_id, request_raw=self.request, catalog=self.catalog
                )
                second = run_baseline(
                    baseline_id, request_raw=self.request, catalog=self.catalog
                )
                self.assertEqual(first, second)
                self.assertEqual(first["baseline_id"], baseline_id)
                self.assertTrue(
                    set(first["used_channels"]).issubset(first["declared_channels"])
                )

    def test_missing_external_or_numeric_inputs_abstain_without_defaults(self) -> None:
        expected = {
            "B1": "EXTERNAL_FREE_FORM_MODEL_PROVIDER_NOT_CONFIGURED",
            "B2": "EXTERNAL_SCENE_MODEL_PROVIDER_NOT_CONFIGURED",
            "B7": "MISSING_PHYSICS_OR_ASSURANCE_INPUT",
            "B8": "MISSING_REACHABILITY_OR_RULE_ACTION_SET",
        }
        for baseline_id, reason in expected.items():
            with self.subTest(baseline=baseline_id):
                result = run_baseline(
                    baseline_id, request_raw=self.request, catalog=self.catalog
                )
                self.assertEqual(result["status"], "UNSUPPORTED")
                self.assertIn(reason, result["reason_codes"])
                self.assertIsNone(result["numeric_parameters"])

    def test_physics_and_action_filters_use_only_declared_explicit_inputs(self) -> None:
        physics = run_baseline(
            "B7",
            request_raw=self.request,
            catalog=self.catalog,
            auxiliary={
                "ego_speed_mps": 6.0,
                "distance_to_boundary_m": 10.0,
                "deceleration_mps2": 3.0,
                "response_time_s": 0.5,
                "physics_evidence_refs": ["synthetic:physics", "synthetic:assurance"],
            },
        )
        self.assertEqual(physics["status"], "EXECUTED")
        self.assertEqual(physics["numeric_parameters"]["stopping_distance_m"], 9.0)
        self.assertTrue(physics["numeric_parameters"]["within_boundary"])

        actions = run_baseline(
            "B8",
            request_raw=self.request,
            catalog=self.catalog,
            auxiliary={
                "reachable_actions": ["STOP", "CREEP"],
                "rule_permitted_actions": ["STOP", "PROCEED"],
                "reachability_evidence_ref": "synthetic:reachability",
            },
        )
        self.assertEqual(actions["status"], "EXECUTED")
        self.assertEqual(actions["action_set"], ["STOP"])

    def test_external_model_adapters_receive_channel_limited_views(self) -> None:
        seen = {}

        def coc_provider(view: dict) -> list[str]:
            seen["coc"] = set(view)
            return ["KR-RTA-27-1-CROSSWALK-STOP"]

        def scene_provider(view: dict) -> list[str]:
            seen["scene"] = set(view)
            return ["KR-RTA-27-1-CROSSWALK-STOP"]

        coc = run_baseline(
            "B1",
            request_raw=self.request,
            catalog=self.catalog,
            auxiliary={"coc_model_provider": coc_provider},
        )
        scene = run_baseline(
            "B2",
            request_raw=self.request,
            catalog=self.catalog,
            auxiliary={"scene_model_provider": scene_provider},
        )
        self.assertEqual(coc["status"], "EXECUTED")
        self.assertEqual(scene["status"], "EXECUTED")
        self.assertEqual(seen["coc"], {"slice", "coc"})
        self.assertEqual(seen["scene"], {"slice", "scene_tags", "scene_facts"})
        self.assertNotIn("SCENE", coc["used_channels"])
        self.assertNotIn("COC", scene["used_channels"])

        invalid = run_baseline(
            "B1",
            request_raw=self.request,
            catalog=self.catalog,
            auxiliary={"coc_model_provider": lambda _: ["UNKNOWN-RULE"]},
        )
        self.assertEqual(invalid["status"], "UNSUPPORTED")
        self.assertEqual(invalid["reason_codes"], ["INVALID_EXTERNAL_MODEL_PROVIDER_OUTPUT"])

    def test_locked_24_by_10_smoke_matrix_has_no_hidden_adapter_failure(self) -> None:
        records = []
        for case in build_locked_frontend_cases():
            for baseline_id in ALL_BASELINES:
                result = run_baseline(
                    baseline_id,
                    request_raw=case["request"],
                    catalog=self.catalog,
                    auxiliary=case["baseline_auxiliary"],
                )
                records.append(result)
        self.assertEqual(len(records), 240)
        self.assertTrue(all(
            item["status"] in {"EXECUTED", "REVIEW_REQUIRED", "UNSUPPORTED", "CONFLICT"}
            for item in records
        ))
        self.assertTrue(all(
            set(item["used_channels"]).issubset(item["declared_channels"])
            for item in records
        ))


if __name__ == "__main__":
    unittest.main()
