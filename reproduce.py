"""Replay the exported authored artifact without the development repository."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def same_xml(generated, retained):
    return ET.tostring(ET.fromstring(generated)) == ET.tostring(ET.parse(retained).getroot())


def verify_inventory():
    manifest = read(ROOT / "artifact_manifest.json")
    expected = manifest["files"]
    actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()
              and "__pycache__" not in p.parts and ".git" not in p.parts
              and p.name != "artifact_manifest.json"}
    assert actual == set(expected), "Artifact contains missing or unexpected files"
    for name, record in expected.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == record["sha256"], name
    return len(expected) + 1


def replay_added_evidence(output):
    from experiments.sequential_coc.mutation_generator import generate_mutation_pairs, jsonl_bytes, read_mutation_pairs
    from experiments.sequential_coc.stateful_checker import check_stateful
    from experiments.sequential_coc.event_local_checker import check_event_local
    path = ROOT / "evidence/regression/mutations.jsonl"
    pairs = read_mutation_pairs(path)
    assert len(pairs) == 40
    assert jsonl_bytes(generate_mutation_pairs(pairs_per_type=10, seed=20260806)) == path.read_bytes()
    counts = {}
    for pair in pairs:
        label = pair.oracle.value
        record = counts.setdefault(label, {"pairs": 0, "stateful": 0, "event_local": 0})
        record["pairs"] += 1
        assert check_stateful(list(pair.original.events)).verdict == "CONSISTENT"
        assert check_event_local(list(pair.original.events)).verdict == "CONSISTENT"
        record["stateful"] += check_stateful(list(pair.mutated.events)).verdict == "CONTRADICTION"
        record["event_local"] += check_event_local(list(pair.mutated.events)).verdict == "CONTRADICTION"
    assert len(counts) == 4 and all(r["pairs"] == r["stateful"] == 10 for r in counts.values())
    assert {k: r["event_local"] for k, r in counts.items()} == {
        "HOLD_GO_CONFLICT": 0, "PREMATURE_RELEASE": 10, "ORDER_VIOLATION": 10, "STALE_OBLIGATION": 0}
    regression = {"status": "PASS", "pairs": 40, "byte_identical_regeneration": True, "by_type": counts}
    save(output / "regression_replay.json", regression)
    replay = load("agreement_replay", "agreement_replay.py")
    stats = load("agreement_coefficients", "agreement_coefficients.py")
    agreement = replay.calculate(ROOT / "evidence/human/ratings.csv", stats.coefficients, stats.pairwise_exact_check)
    assert agreement == read(ROOT / "evidence/human/agreement.json")
    save(output / "agreement_replay.json", agreement)
    print(json.dumps({"regression": regression, "anonymous_panel": {"subjects": 27, "raters": 4,
                      "agreement_reproduced": True}}), flush=True)


def replay_python(output):
    from experiments.kiee_review_revision import scenario_evaluation as scenario
    from experiments.kiee_review_revision import condition_model as condition
    from experiments.sequential_coc.contract_compiler import compile_text
    from experiments.sequential_coc.stateful_checker import check_stateful
    from experiments.sequential_coc.event_local_checker import check_event_local
    from experiments.sequential_coc.uppaal_generator import build_uppaal_model

    boundary = load("boundary_model", "experiments/cross_scene_constraints/run.py")
    controlled = ROOT / "evidence/controlled"
    cases = read(controlled / "cases.json")
    assert scenario.build_cases() == cases, "144-case generation changed"
    saved = [json.loads(line) for line in (controlled / "results.jsonl").read_text().splitlines()]
    matches = {name: 0 for name in ("legacy_full", "legacy_local", "fsm", "previous_1", "previous_3", "previous_5", "legacy_auto_text")}
    for case, record in zip(cases, saved):
        assert case["case_id"] == record["case_id"]
        events, _ = scenario.project_frames(case)
        predictions = {"legacy_full": check_stateful(events).to_dict(),
                       "legacy_local": check_event_local(events).to_dict(),
                       "fsm": scenario.check_fsm(case["events"])}
        for n in (1, 3, 5):
            predictions[f"previous_{n}"] = scenario.window_check(events, n)
        auto = []
        for frame in case["events"]:
            auto.extend(compile_text(frame["text"], frame["event_id"], case["case_id"], frame["timestamp_us"]))
        predictions["legacy_auto_text"] = check_stateful(auto).to_dict()
        for name, prediction in predictions.items():
            retained = record["predictions"][name]
            assert prediction["verdict"] == retained["verdict"], (case["case_id"], name)
            if name != "legacy_auto_text":
                assert prediction.get("first_event_id") == retained.get("first_event_id"), (case["case_id"], name)
            matches[name] += prediction["verdict"] == case["expected"]["verdict"]
        tree, queries = build_uppaal_model(events)
        folder = controlled / "uppaal" / case["case_id"]
        assert same_xml(ET.tostring(tree.getroot()), folder / "model.xml")
        assert "\n".join(queries) + "\n" == (folder / "queries.q").read_text()
    assert len(cases) == len(saved) == 144
    assert matches == {"legacy_full": 96, "legacy_local": 72, "fsm": 144,
                       "previous_1": 84, "previous_3": 90, "previous_5": 90, "legacy_auto_text": 36}

    condition_rows = read(ROOT / "evidence/condition/results.json")
    assert len(condition_rows) == 144
    for case, row in zip(cases, condition_rows):
        encoded = condition.encode(case["events"])
        assert row["case_id"] == case["case_id"] and encoded == row["encoded"]
        assert same_xml(condition.model_bytes(encoded), ROOT / "evidence/condition" / case["case_id"] / "model.xml")
    boundary_cases = read(ROOT / "evidence/boundary/cases.json")
    assert len(boundary_cases) == 81 and boundary.build_cases() == boundary_cases
    for case in boundary_cases:
        for mode in ("carry", "reset"):
            model = ROOT / "evidence/boundary/models" / case["case_id"] / mode / "model.xml"
            assert same_xml(boundary.model_bytes(boundary.encode(case["events"], mode == "reset")), model)
    result = {"status": "PASS", "controlled_cases": 144, "boundary_cases": 81,
              "python_verdict_matches_expected": matches, "all_450_models_reconstructed": True,
              "condition_and_boundary_solver_verdicts_replayed": False}
    save(output / "python_replay.json", result)
    print(json.dumps(result), flush=True)
    return scenario, condition, boundary, cases, boundary_cases


def replay_bounded(output):
    source = ROOT / "experiments/bounded_conformance"
    retained = ROOT / "evidence/bounded"
    folder = output / "bounded"
    folder.mkdir()
    shutil.copyfile(retained / "frozen_targets.hpp", folder / "frozen_targets.hpp")
    # Verify that native step bodies really match the retained XML declarations.
    header = (folder / "frozen_targets.hpp").read_text()
    for name in ("condition", "boundary"):
        declaration = ET.parse(retained / (name + "_frozen.xml")).findtext("declaration")
        assert declaration[declaration.index("void step()"):] in header
    compiler = subprocess.run(["c++", "-std=c++17", "-O2", "-I", str(folder), "-I", str(source),
                               str(source / "enumerate.cpp"), "-o", str(folder / "enumerator")], capture_output=True, text=True)
    (folder / "compile_stdout.txt").write_text(compiler.stdout)
    (folder / "compile_stderr.txt").write_text(compiler.stderr)
    compiler.check_returncode()
    with (folder / "stdout.jsonl").open("w") as stdout, (folder / "stderr.txt").open("w") as stderr:
        subprocess.run([str(folder / "enumerator"), str(folder / "mismatches.jsonl"),
                        str(folder / "fault_control_mismatches.jsonl")], stdout=stdout, stderr=stderr, check=True, timeout=1800)
    rows = [json.loads(line) for line in (folder / "stdout.jsonl").read_text().splitlines()]
    expected = read(retained / "RESULT.json")
    assert rows == expected["profiles"] + [expected["fault_control"]]
    for name in ("mismatches.jsonl", "fault_control_mismatches.jsonl"):
        actual = [json.loads(line) for line in (folder / name).read_text().splitlines()]
        original = [json.loads(line) for line in (retained / name).read_text().splitlines()]
        assert actual == original, name
    result = {"status": "PASS", "cases": expected["case_count"], "mismatches": expected["mismatches"],
              "fault_control_cases": expected["fault_control"]["cases"], "fault_control_mismatches": expected["fault_control"]["mismatches"]}
    save(output / "bounded_replay.json", result)
    print(json.dumps(result), flush=True)


def replay_solver(output, verifyta, scenario, condition, boundary, cases, boundary_cases):
    from experiments.sequential_coc.run_uppaal import run_verifyta
    from experiments.kiee_review_revision.audit_terminal_evidence import parse_terminal
    counts = {"legacy_models": 0, "terminal_diagnoses": 0, "condition_models": 0, "boundary_models": 0}
    legacy_rows = {r["case_id"]: r for r in [json.loads(line) for line in (ROOT / "evidence/controlled/results.jsonl").read_text().splitlines()]}
    condition_rows = {r["case_id"]: r for r in read(ROOT / "evidence/condition/results.json")}
    terminal_rows = {r["case_id"]: r for r in read(ROOT / "evidence/terminal/terminal_results.json")}
    boundary_rows = {r["case_id"]: r for r in read(ROOT / "evidence/boundary/results.json")}
    folder = output / "solver"
    folder.mkdir()

    def invoke(name, model, queries):
        completed = subprocess.run([str(verifyta), "-q", "-t1", str(model), str(queries)], capture_output=True, text=True, timeout=120)
        (folder / (name + "_stdout.txt")).write_text(completed.stdout)
        (folder / (name + "_stderr.txt")).write_text(completed.stderr)
        completed.check_returncode()
        return completed.stdout + "\n" + completed.stderr

    for case in cases:
        cid = case["case_id"]
        model = ROOT / "evidence/controlled/uppaal" / cid / "model.xml"
        actual = run_verifyta(model, model.with_name("queries.q"), verifyta).to_dict()
        original = legacy_rows[cid]["predictions"]["uppaal"]
        for key in ("verdict", "contradiction_types", "first_event_id", "unknown_reasons"):
            assert actual[key] == original[key], (cid, key)
        counts["legacy_models"] += 1
        raw = invoke(cid + "_terminal", model, ROOT / "evidence/terminal" / cid / "terminal.q")
        assert parse_terminal(raw) == terminal_rows[cid]["terminal_reasons"]
        counts["terminal_diagnoses"] += 1
        model = ROOT / "evidence/condition" / cid / "model.xml"
        raw = invoke(cid + "_condition", model, model.with_name("queries.q"))
        encoded = condition.encode(case["events"])
        assert condition.parse_result(raw, encoded["event_ids"], encoded["obligation_ids"]) == condition_rows[cid]["prediction"]
        counts["condition_models"] += 1
    for case in boundary_cases:
        cid = case["case_id"]
        for mode in ("carry", "reset"):
            model = ROOT / "evidence/boundary/models" / cid / mode / "model.xml"
            raw = invoke(cid + "_" + mode, model, model.with_name("queries.q"))
            actual = boundary.parse_result(raw, boundary.encode(case["events"], mode == "reset"))
            for key, value in actual.items():
                assert value == boundary_rows[cid][mode][key], (cid, mode, key)
            counts["boundary_models"] += 1
    result = {"status": "PASS", "runs": counts, "total_runs": sum(counts.values())}
    save(output / "solver_replay.json", result)
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verifyta", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("Write reproduction output outside this immutable artifact tree")
    file_count = verify_inventory()
    output.mkdir(parents=True, exist_ok=False)
    replay_added_evidence(output)
    modules = replay_python(output)
    replay_bounded(output)
    if args.verifyta:
        replay_solver(output, args.verifyta.resolve(), *modules)
    save(output / "RESULT.json", {"status": "PASS", "artifact_files_verified": file_count,
                                  "solver_rerun": bool(args.verifyta), "natural_data_required": False})


if __name__ == "__main__":
    main()
