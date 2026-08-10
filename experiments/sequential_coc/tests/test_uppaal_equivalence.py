"""Runtime equivalence tests; real verifyta is required for evidence."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from experiments.sequential_coc.contract_ir import ContradictionType, EvidenceValue
from experiments.sequential_coc.run_uppaal import last_verifyta_run_metadata, run_verifyta
from experiments.sequential_coc.stateful_checker import check_stateful
from experiments.sequential_coc.tests.fixtures import hold_event, proceed_event
from experiments.sequential_coc.uppaal_generator import build_uppaal_model, write_uppaal_artifacts


PROJECT_VERIFYTA = Path(__file__).resolve().parents[3] / "runtime/solvers/uppaal-5.0.0-linux64/bin/verifyta"
VERIFYTA = Path(shutil.which("verifyta")) if shutil.which("verifyta") else PROJECT_VERIFYTA


def _runtime_availability() -> tuple[bool, str]:
    if not VERIFYTA.is_file():
        return False, "NOT_RUN: verifyta executable not found"
    probe = subprocess.run(
        [str(VERIFYTA), "--version"], capture_output=True, text=True, check=False
    )
    output = (probe.stdout + probe.stderr).lower()
    if "license" in output and ("not set" in output or "does not cover" in output or "failed" in output):
        return False, "NOT_RUN: verifyta 5.0.0 found but license is unavailable"
    if probe.returncode != 0:
        return False, f"NOT_RUN: verifyta probe exited {probe.returncode}"
    return True, ""


VERIFYTA_AVAILABLE, VERIFYTA_SKIP_REASON = _runtime_availability()


class VerifytaParserUnitTests(unittest.TestCase):
    def _write_fake_verifyta(self, root: Path, body: str) -> Path:
        executable = root / "fake-verifyta"
        executable.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        executable.chmod(0o700)
        return executable

    def _artifacts(self, root: Path):
        events = [hold_event(release=EvidenceValue.FALSE), proceed_event()]
        tree, queries = build_uppaal_model(events)
        model, query = root / "model.xml", root / "model.q"
        write_uppaal_artifacts(tree, queries, model, query)
        return model, query

    def test_parser_unit_preserves_failed_flag_and_first_event_mapping(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, query = self._artifacts(root)
            fake = self._write_fake_verifyta(
                root,
                """if [ \"$1\" = \"--version\" ]; then echo 'UPPAAL fake parser-unit 1.0'; exit 0; fi
echo 'Verifying formula 1: Formula is NOT satisfied.'
echo 'idx=0 first_violation_idx=-1'
echo 'first_violation_idx=1'
echo 'Verifying formula 2: Formula is satisfied.'
echo 'Verifying formula 3: Formula is satisfied.'
echo 'Verifying formula 4: Formula is satisfied.'
echo 'Verifying formula 5: Formula is satisfied.'
echo 'Verifying formula 6: Formula is satisfied.'
""",
            )

            result = run_verifyta(model, query, fake)

            self.assertEqual(result.verdict, "CONTRADICTION")
            self.assertEqual(result.contradiction_types, (ContradictionType.HOLD_GO_CONFLICT,))
            self.assertEqual(result.first_event_id, "proceed")
            metadata = last_verifyta_run_metadata()
            self.assertIsNotNone(metadata)
            self.assertEqual(metadata.command[1:3], ("-q", "-t1"))

    def test_parser_unit_preserves_parse_unknown_reason_with_contradiction(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, query = self._artifacts(root)
            fake = self._write_fake_verifyta(
                root,
                """echo 'Formula is NOT satisfied.'
echo 'first_violation_idx=1 sticky_hold_go_conflict=1 sticky_parse_status_unknown=1'
echo 'Formula is satisfied.'
echo 'Formula is satisfied.'
echo 'Formula is satisfied.'
echo 'Formula is NOT satisfied.'
echo 'sticky_unknown=1 sticky_parse_status_unknown=1'
echo 'Formula is satisfied.'
""",
            )

            result = run_verifyta(model, query, fake)

            self.assertEqual(result.verdict, "CONTRADICTION")
            self.assertEqual(result.unknown_reasons, ("PARSE_STATUS_UNKNOWN",))

    def test_parser_unit_never_maps_execution_or_malformed_output_to_consistent(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, query = self._artifacts(root)
            failing = self._write_fake_verifyta(root, "echo 'license failure' >&2\nexit 7\n")
            failed = run_verifyta(model, query, failing)
            self.assertEqual(failed.verdict, "UNKNOWN")
            self.assertIn("VERIFYTA_EXIT_7", failed.unknown_reasons)

            malformed = self._write_fake_verifyta(root, "echo 'unrecognized output'\n")
            parsed = run_verifyta(model, query, malformed)
            self.assertEqual(parsed.verdict, "UNKNOWN")
            self.assertIn("VERIFYTA_PARSE_FAILURE", parsed.unknown_reasons)

    def test_parser_unit_distinguishes_license_failure(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, query = self._artifacts(root)
            unlicensed = self._write_fake_verifyta(
                root, "echo 'License does not cover verifier.' >&2\nexit 1\n"
            )

            result = run_verifyta(model, query, unlicensed)

            self.assertEqual(result.verdict, "UNKNOWN")
            self.assertEqual(result.unknown_reasons, ("VERIFYTA_LICENSE_UNAVAILABLE",))

    def test_missing_paths_are_rejected_before_execution(self):
        missing = Path("/definitely/not/present")
        with self.assertRaises(FileNotFoundError):
            run_verifyta(missing, missing, missing)

    def test_reordered_or_altered_queries_abstain_before_execution(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, query = self._artifacts(root)
            fake = self._write_fake_verifyta(root, "exit 99\n")
            canonical = query.read_text(encoding="utf-8").splitlines()
            variants = (
                [canonical[1], canonical[0], *canonical[2:]],
                [*canonical[:4], "A[] not some_other_unknown", canonical[5]],
                [" " + canonical[0], *canonical[1:]],
            )
            for number, lines in enumerate(variants):
                query.write_text("\n".join(lines) + "\n", encoding="utf-8")
                with self.subTest(number=number):
                    result = run_verifyta(model, query, fake)
                    self.assertEqual(result.verdict, "UNKNOWN")
                    self.assertEqual(result.unknown_reasons, ("QUERY_CONTRACT_MISMATCH",))

    def test_missing_or_wrong_model_contract_metadata_abstains(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, query = self._artifacts(root)
            fake = self._write_fake_verifyta(root, "exit 99\n")
            original = model.read_text(encoding="utf-8")
            variants = (
                original.replace(
                    "// transition_contract_version=sequential-coc-transition-v2\n", ""
                ),
                original.replace(
                    "transition_contract_version=sequential-coc-transition-v2",
                    "transition_contract_version=sequential-coc-transition-v1",
                ),
                original.replace(
                    "e3f5e437dab029813dd4d5e515426e1079e29ce385108aea60665d87d130c4f8",
                    "0" * 64,
                ),
            )
            for number, payload in enumerate(variants):
                model.write_text(payload, encoding="utf-8")
                with self.subTest(number=number):
                    result = run_verifyta(model, query, fake)
                    self.assertEqual(result.verdict, "UNKNOWN")
                    self.assertEqual(result.unknown_reasons, ("MODEL_CONTRACT_MISMATCH",))

    def test_malformed_model_or_query_encoding_abstains_without_exception(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, query = self._artifacts(root)
            fake = self._write_fake_verifyta(root, "exit 99\n")
            model.write_bytes(b"\xff\xfe not xml")
            model_result = run_verifyta(model, query, fake)
            self.assertEqual(
                model_result.unknown_reasons, ("MODEL_METADATA_PARSE_FAILURE",)
            )

            model, query = self._artifacts(root)
            query.write_bytes(b"\xff\xfe")
            query_result = run_verifyta(model, query, fake)
            self.assertEqual(query_result.unknown_reasons, ("QUERY_READ_FAILURE",))


@unittest.skipUnless(VERIFYTA_AVAILABLE, VERIFYTA_SKIP_REASON)
class RealVerifytaEquivalenceTests(unittest.TestCase):
    def test_normal_contradiction_and_unknown_tables_match_python(self):
        normal_go = replace(
            proceed_event(),
            release_known=True,
            release_value=True,
            satisfaction_known=True,
            satisfaction_value=True,
        )
        premature = replace(
            proceed_event(event_id="premature"),
            release_known=True,
            release_value=False,
        )
        order = replace(
            proceed_event(event_id="out-of-order"),
            satisfaction_known=True,
            satisfaction_value=False,
        )
        stale = hold_event(
            timestamp_us=1,
            event_id="stale-hold",
            release=EvidenceValue.TRUE,
        )
        tables = (
            [hold_event(release=EvidenceValue.FALSE), normal_go],
            [hold_event(release=EvidenceValue.FALSE), proceed_event()],
            [premature],
            [order],
            [hold_event(release=EvidenceValue.FALSE), stale],
            [hold_event(release=EvidenceValue.UNKNOWN), proceed_event()],
            [
                hold_event(release=EvidenceValue.FALSE),
                replace(proceed_event(), parse_status="UNKNOWN_AMBIGUOUS_ORDER"),
            ],
        )
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for number, events in enumerate(tables):
                tree, queries = build_uppaal_model(events)
                model, query = root / f"model-{number}.xml", root / f"model-{number}.q"
                write_uppaal_artifacts(tree, queries, model, query)
                with self.subTest(number=number):
                    actual = run_verifyta(model, query, VERIFYTA)
                    expected = check_stateful(events)
                    self.assertEqual(actual.verdict, expected.verdict)
                    self.assertEqual(actual.contradiction_types, expected.contradiction_types)
                    self.assertEqual(actual.first_event_id, expected.first_event_id)
                    self.assertEqual(actual.unknown_reasons, expected.unknown_reasons)


if __name__ == "__main__":
    unittest.main()
