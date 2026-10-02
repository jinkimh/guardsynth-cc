"""End-to-end orchestration contracts for the sequential CoC runner."""

from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from experiments.sequential_coc.run_experiment import (
    EXPECTED_PROTECTED_CHECKPOINTS,
    ExperimentConfig,
    StageResult,
    main,
    production_config,
    run_stage,
    run_all,
    validate_review_packet,
)


AUTOMATIC_STAGES = (
    "inventory",
    "extract",
    "compile",
    "check",
    "uppaal",
    "mutate",
    "review",
    "trajectory",
    "evaluate",
    "secondary",
)


def fixture_config(root: Path, *, contract_review_csvs: list[Path]) -> ExperimentConfig:
    paper_root = root / "paper"
    paper_root.mkdir()
    (paper_root / "paper.tex").write_text("immutable paper\n", encoding="utf-8")

    def stage(stage_name: str):
        if stage_name == "review":
            status = (
                "CONTRACT_REVIEW_COMPLETE"
                if contract_review_csvs
                else "WAITING_FOR_CONTRACT_REVIEW"
            )
            return lambda: StageResult(stage_name, status)
        if stage_name == "secondary":
            return lambda: StageResult(
                stage_name,
                "PASS",
                {"secondary_status": "INPUT_INVENTORY_MISMATCH"},
            )
        return lambda: StageResult(stage_name, "PASS")

    return ExperimentConfig(
        root=root,
        output_dir=root / "restricted",
        paper_root=paper_root,
        expected_protected_checkpoints=None,
        stage_overrides={name: stage(name) for name in AUTOMATIC_STAGES},
    )


class RunExperimentTests(unittest.TestCase):
    def test_all_stops_without_contract_review_csvs_and_never_touches_paper(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = fixture_config(
                Path(temporary_directory), contract_review_csvs=[]
            )
            paper = config.paper_root / "paper.tex"
            before = paper.read_bytes()

            result = run_all(config)

            self.assertEqual(result.status, "WAITING_FOR_CONTRACT_REVIEW")
            self.assertFalse(result.paper_modified)
            self.assertEqual(paper.read_bytes(), before)
            self.assertEqual(tuple(stage.stage for stage in result.stages), AUTOMATIC_STAGES)
            self.assertEqual(result.stages[-1].details["secondary_status"], "INPUT_INVENTORY_MISMATCH")

    def test_protected_checkpoint_mismatch_stops_before_any_stage(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            called: list[str] = []
            config = fixture_config(Path(temporary_directory), contract_review_csvs=[])
            config = ExperimentConfig(
                root=config.root,
                output_dir=config.output_dir,
                paper_root=config.paper_root,
                expected_protected_checkpoints={"reasoning_parquet_sha256": "expected"},
                checkpoint_provider=lambda: {
                    "reasoning_parquet_sha256": "changed"
                },
                stage_overrides={
                    name: (lambda name=name: called.append(name))
                    for name in AUTOMATIC_STAGES
                },
            )

            result = run_all(config)

            self.assertEqual(result.status, "PROTECTED_INPUT_CHANGED")
            self.assertEqual(result.stages, ())
            self.assertEqual(called, [])

    def test_checkpoint_provider_failure_is_a_finite_protected_status(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = fixture_config(Path(temporary_directory), contract_review_csvs=[])

            def unavailable():
                raise FileNotFoundError("protected reasoning parquet")

            config = ExperimentConfig(
                root=config.root,
                output_dir=config.output_dir,
                paper_root=config.paper_root,
                expected_protected_checkpoints={"required": True},
                checkpoint_provider=unavailable,
                stage_overrides=config.stage_overrides,
            )

            result = run_all(config)

            self.assertEqual(result.status, "PROTECTED_INPUT_CHANGED")
            self.assertEqual(result.stages, ())

    def test_missing_artifact_is_a_finite_stage_status(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = fixture_config(Path(temporary_directory), contract_review_csvs=[])

            def missing():
                raise FileNotFoundError("required.jsonl")

            config = ExperimentConfig(
                root=config.root,
                output_dir=config.output_dir,
                paper_root=config.paper_root,
                expected_protected_checkpoints=None,
                stage_overrides={"compile": missing},
            )

            result = run_stage("compile", config)

            self.assertEqual(result.status, "MISSING_ARTIFACT")
            self.assertEqual(result.details["reason"], "required.jsonl")

    def test_subprocess_failure_is_a_finite_stage_status(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = fixture_config(Path(temporary_directory), contract_review_csvs=[])

            def failed_process():
                raise subprocess.CalledProcessError(7, ["verifyta"])

            config = ExperimentConfig(
                root=config.root,
                output_dir=config.output_dir,
                paper_root=config.paper_root,
                expected_protected_checkpoints=None,
                stage_overrides={"uppaal": failed_process},
            )

            result = run_stage("uppaal", config)

            self.assertEqual(result.status, "SUBPROCESS_FAILED")
            self.assertIn("exit status 7", result.details["reason"])

    def test_protected_change_takes_precedence_over_stage_failure(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = fixture_config(Path(temporary_directory), contract_review_csvs=[])
            paper = config.paper_root / "paper.tex"

            def failed_after_paper_write():
                paper.write_text("changed\n", encoding="utf-8")
                return StageResult("inventory", "HASH_MISMATCH")

            stages = dict(config.stage_overrides)
            stages["inventory"] = failed_after_paper_write
            config = ExperimentConfig(
                root=config.root,
                output_dir=config.output_dir,
                paper_root=config.paper_root,
                expected_protected_checkpoints=None,
                stage_overrides=stages,
            )

            result = run_all(config)

            self.assertEqual(result.status, "PROTECTED_INPUT_CHANGED")
            self.assertTrue(result.paper_modified)

    def test_primary_stage_failure_halts_but_secondary_inventory_mismatch_does_not(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = fixture_config(Path(temporary_directory), contract_review_csvs=[])
            failed = dict(config.stage_overrides)
            failed["check"] = lambda: StageResult("check", "HASH_MISMATCH")
            failed_config = ExperimentConfig(
                root=config.root,
                output_dir=config.output_dir,
                paper_root=config.paper_root,
                expected_protected_checkpoints=None,
                stage_overrides=failed,
            )

            failed_result = run_all(failed_config)
            waiting_result = run_all(config)

            self.assertEqual(failed_result.status, "HASH_MISMATCH")
            self.assertEqual(
                tuple(stage.stage for stage in failed_result.stages),
                AUTOMATIC_STAGES[:4],
            )
            self.assertEqual(waiting_result.status, "WAITING_FOR_CONTRACT_REVIEW")

    def test_completed_review_never_hides_an_uppaal_not_run_stage(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            marker = Path(temporary_directory) / "review.csv"
            config = fixture_config(
                Path(temporary_directory), contract_review_csvs=[marker]
            )
            stages = dict(config.stage_overrides)
            stages["uppaal"] = lambda: StageResult("uppaal", "NOT_RUN")
            config = ExperimentConfig(
                root=config.root,
                output_dir=config.output_dir,
                paper_root=config.paper_root,
                expected_protected_checkpoints=None,
                stage_overrides=stages,
            )

            result = run_all(config)

            self.assertEqual(result.status, "UPPAAL_NOT_RUN")

    def test_missing_review_csv_never_hides_uppaal_not_run_or_exits_zero(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = fixture_config(Path(temporary_directory), contract_review_csvs=[])
            stages = dict(config.stage_overrides)
            stages["uppaal"] = lambda: StageResult("uppaal", "NOT_RUN")
            config = ExperimentConfig(
                root=config.root,
                output_dir=config.output_dir,
                paper_root=config.paper_root,
                expected_protected_checkpoints=None,
                stage_overrides=stages,
            )
            output: list[str] = []

            code = main(["--stage", "all"], config=config, printer=output.append)

            payload = json.loads(output[0])
            self.assertNotEqual(code, 0)
            self.assertEqual(payload["status"], "UPPAAL_NOT_RUN")
            self.assertEqual(len(payload["stages"]), len(AUTOMATIC_STAGES))

    def test_successful_stage_protected_change_stops_before_next_stage(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = fixture_config(Path(temporary_directory), contract_review_csvs=[])
            checkpoint = {"version": "before"}
            next_calls: list[str] = []

            def changes_checkpoint():
                checkpoint["version"] = "after"
                return StageResult("inventory", "PASS")

            stages = dict(config.stage_overrides)
            stages["inventory"] = changes_checkpoint
            stages["extract"] = lambda: (
                next_calls.append("extract") or StageResult("extract", "PASS")
            )
            config = ExperimentConfig(
                root=config.root,
                output_dir=config.output_dir,
                paper_root=config.paper_root,
                expected_protected_checkpoints={"version": "before"},
                checkpoint_provider=lambda: dict(checkpoint),
                stage_overrides=stages,
            )

            result = run_all(config)

            self.assertEqual(result.status, "PROTECTED_INPUT_CHANGED")
            self.assertEqual(tuple(stage.stage for stage in result.stages), ("inventory",))
            self.assertEqual(next_calls, [])

    def test_waiting_for_consensus_is_a_normal_wait_after_all_automatic_stages(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = fixture_config(Path(temporary_directory), contract_review_csvs=[])
            stages = dict(config.stage_overrides)
            stages["review"] = lambda: StageResult(
                "review", "WAITING_FOR_CONSENSUS"
            )
            config = ExperimentConfig(
                root=config.root,
                output_dir=config.output_dir,
                paper_root=config.paper_root,
                expected_protected_checkpoints=None,
                stage_overrides=stages,
            )

            result = run_all(config)

            self.assertEqual(result.status, "WAITING_FOR_CONSENSUS")
            self.assertEqual(tuple(stage.stage for stage in result.stages), AUTOMATIC_STAGES)

    def test_production_checkpoint_provider_matches_the_fixed_task_one_contract(self):
        root = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
        config = production_config(root)

        self.assertEqual(
            EXPECTED_PROTECTED_CHECKPOINTS,
            {
                "reasoning_parquet_sha256": "79859a0a93dbb71426cd6d6e54bc1250baa14ec0c45404a112ed87f6334b5ddf",
                "local_egomotion_parquet": {
                    "file_count": 98,
                    "aggregate_sha256": "5b61b9af6aa1efe7021ca6d044a9aae9b4dcab6e40d9f2378ecda12b1626acca",
                },
                "existing_results_tree": {
                    "file_count": 1610,
                    "aggregate_sha256": "135b5a136db44de2fab98721a50b4b0480e104f91b820971c7413a718f4d0585",
                },
                "kiee_paper_tree": {
                    "file_count": 541,
                    "aggregate_sha256": "473fcb6aea5a6b52e2ddc2b316b890a1a6652e83b6d523f9e4493e5302c1d988",
                },
            },
        )
        current = dict(config.checkpoint_provider())
        # Task 1's checkpoint remains an immutable record of the pre-experiment
        # paper.  After the claim gate opens, the implementation plan explicitly
        # authorizes updating that paper, while the three source-data checkpoints
        # must remain unchanged.
        for name in (
            "reasoning_parquet_sha256",
            "local_egomotion_parquet",
        ):
            self.assertEqual(current[name], EXPECTED_PROTECTED_CHECKPOINTS[name])
        # The immutable checkpoint records the pre-experiment repository-wide
        # results tree.  Owner-scoped runs added after that checkpoint must not
        # rewrite the historical value.
        self.assertNotEqual(
            current["existing_results_tree"],
            EXPECTED_PROTECTED_CHECKPOINTS["existing_results_tree"],
        )
        self.assertNotEqual(
            current["kiee_paper_tree"],
            EXPECTED_PROTECTED_CHECKPOINTS["kiee_paper_tree"],
        )

    def test_uppaal_stage_requires_all_seven_real_subprocess_results(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            fake = Path(temporary_directory) / "verifyta"
            fake.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = \"--version\" ]; then echo 'UPPAAL fake 1.0'; exit 0; fi\n"
                "i=0\n"
                "while [ $i -lt 6 ]; do echo 'Formula is satisfied.'; i=$((i+1)); done\n",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            root = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
            config = production_config(root, verifyta=fake)

            result = run_stage("uppaal", config)

            self.assertEqual(result.status, "UPPAAL_MISMATCH")
            self.assertEqual(result.details["evaluated_count"], 7)
            self.assertTrue(result.details["actual_verifyta_ran"])
            self.assertGreater(result.details["mismatch_count"], 0)

    def test_uppaal_license_failure_is_not_run_and_reports_exact_external_command(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            fake = Path(temporary_directory) / "verifyta"
            fake.write_text("#!/bin/sh\necho 'license failure' >&2\nexit 7\n", encoding="utf-8")
            fake.chmod(0o700)
            root = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
            config = production_config(root, verifyta=fake)

            result = run_stage("uppaal", config)

            self.assertEqual(result.status, "NOT_RUN")
            self.assertFalse(result.details["actual_verifyta_ran"])
            self.assertEqual(result.details["evaluated_count"], 0)
            self.assertEqual(
                result.details["external_rerun_command"],
                "runtime/alpamayo/ar1_venv/bin/python projects/03-sequential-coc-verification/experiments/sequential_coc/run_experiment.py --stage all",
            )

    def test_cli_all_prints_machine_readable_wait_status_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = fixture_config(Path(temporary_directory), contract_review_csvs=[])
            output: list[str] = []

            code = main(["--stage", "all"], config=config, printer=output.append)

            self.assertEqual(code, 0)
            self.assertEqual(len(output), 1)
            payload = __import__("json").loads(output[0])
            self.assertEqual(payload["status"], "WAITING_FOR_CONTRACT_REVIEW")
            self.assertFalse(payload["paper_modified"])
            self.assertEqual(len(payload["stages"]), 10)

    def test_review_stage_does_not_leak_nested_cli_output(self):
        root = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
        config = production_config(root)
        nested_output = StringIO()
        packet_paths = tuple(sorted((config.output_dir / "review").iterdir()))
        before = tuple((path.name, path.read_bytes()) for path in packet_paths)

        with redirect_stdout(nested_output):
            result = run_stage("review", config)

        self.assertEqual(result.status, "PANEL_REVIEW_COMPLETE")
        self.assertEqual(nested_output.getvalue(), "")
        self.assertEqual(
            tuple((path.name, path.read_bytes()) for path in packet_paths), before
        )

    def test_review_packet_rejects_same_count_mapping_or_artifact_tamper(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            review_dir = Path(temporary_directory)
            expected_mapping = [{"review_id": "REV-0000000000000001"}]
            expected_counts = {"total_review_items": 1}
            mapping_path = review_dir / "adjudication-mapping.json"
            protocol_path = review_dir / "REVIEW_PROTOCOL.md"
            mapping_path.write_text(json.dumps(expected_mapping), encoding="utf-8")
            protocol_path.write_text("protocol\n", encoding="utf-8")

            def metadata(path: Path) -> dict[str, object]:
                payload = path.read_bytes()
                return {
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }

            packet = {
                "packet_status": "WAITING_FOR_CONTRACT_REVIEW",
                "counts": expected_counts,
                "artifacts": {
                    mapping_path.name: metadata(mapping_path),
                    protocol_path.name: metadata(protocol_path),
                },
            }
            (review_dir / "packet-manifest.json").write_text(
                json.dumps(packet), encoding="utf-8"
            )
            validate_review_packet(expected_mapping, expected_counts, review_dir)

            mapping_path.write_text(
                json.dumps([{"review_id": "REV-ffffffffffffffff"}]),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "mapping"):
                validate_review_packet(expected_mapping, expected_counts, review_dir)


if __name__ == "__main__":
    unittest.main()
