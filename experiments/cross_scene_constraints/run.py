"""Authored cross-scene lifecycle feasibility; not natural-scene accuracy.

Pedestrian clearance, signal permission, and obstacle clearance each forbid GO
until their own release predicate is true. Boundary identity/applicability and
evidence validity are supplied inputs, never inferred from scene numbers.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").exists())
OWNER = ROOT / "projects/03-sequential-coc-verification"
DOMAINS = ("pedestrian", "signal", "obstacle")
QUERIES = ["A[] not bad", "A[] not missing", "A<> Observer.Done",
           "E<> Observer.Done && bad", "E<> Observer.Done && missing"]
VARIANTS = {
    "held_across_boundary": "CONTRADICTION",
    "released_next_scene": "CONSISTENT",
    "missing_release": "UNKNOWN",
    "wrong_entity_release": "UNKNOWN",
    "identity_uncertain": "UNKNOWN",
    "evidence_expired": "UNKNOWN",
    "scope_ended": "CONSISTENT",
    "reactivated_blocked": "CONTRADICTION",
    "reactivated_unknown": "UNKNOWN",
}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame(scene, action="WAIT", creates=None, evidence=None, boundary=None):
    return {"scene_id": scene, "action": action, "creates": creates,
            "evidence": evidence or {}, "boundary": boundary or {}}


def binding(status="VERIFIED", persist=False):
    return {"status": status, "evidence_valid_across_boundary": persist}


def case(case_id, events, verdict, issue=None, obligation=None):
    for i, event in enumerate(events):
        event["event_id"] = f"{case_id}:e{i}"
    return {"case_id": case_id, "source_kind": "AUTHORED_SYMBOLIC",
            "events": events, "expected": {"verdict": verdict,
            "issue_event_id": events[issue]["event_id"] if issue is not None else None,
            "obligation_id": obligation}}


def build_cases():
    cases = []
    # All 3^3 release vectors, with one or two actual scene boundaries.
    # -1 means absent evidence, 0 means known unreleased, 1 means released.
    for scene_count in (2, 3):
        for values in product((-1, 0, 1), repeat=3):
            events = [frame("authored-scene-a", "STOP", d) for d in DOMAINS]
            links = {d: binding() for d in DOMAINS}
            if scene_count == 3:
                events.append(frame("authored-scene-b", boundary=links))
            events.append(frame("authored-scene-c", "GO", evidence={
                d: v for d, v in zip(DOMAINS, values) if v != -1}, boundary=links))
            verdict = "CONTRADICTION" if 0 in values else "UNKNOWN" if -1 in values else "CONSISTENT"
            issue_value = 0 if verdict == "CONTRADICTION" else -1
            oid = DOMAINS[values.index(issue_value)] if verdict != "CONSISTENT" else None
            cid = f"joint-{scene_count}scenes-" + "-".join({-1: "u", 0: "f", 1: "t"}[v] for v in values)
            item = case(cid, events, verdict, -1 if oid else None, oid)
            item.update(group="joint_release_vectors", release_vector=list(values))
            cases.append(item)
    for domain in DOMAINS:
        for variant, verdict in VARIANTS.items():
            initial = {} if variant in ("missing_release", "wrong_entity_release") else {domain: 0}
            events = [frame("authored-scene-a", "STOP", domain, initial)]
            status = "UNCERTAIN" if variant == "identity_uncertain" else "ENDED" if variant == "scope_ended" else "VERIFIED"
            persist = variant == "held_across_boundary"
            final = frame("authored-scene-b", "GO", boundary={domain: binding(status, persist)})
            if variant in ("released_next_scene", "identity_uncertain"):
                final["evidence"] = {domain: 1}
            elif variant == "wrong_entity_release":
                final["evidence"] = {domain + ":different-target": 1}
            elif variant.startswith("reactivated_"):
                events.append(frame("authored-scene-a", evidence={domain: 1}))
                events.append(frame("authored-scene-b", "STOP", domain,
                                    boundary={domain: binding()}))
                final["boundary"] = {}
                if variant == "reactivated_blocked":
                    final["evidence"] = {domain: 0}
            events.append(final)
            oid = domain if verdict != "CONSISTENT" else None
            item = case(f"{domain}-{variant.replace('_', '-')}", events, verdict, -1 if oid else None, oid)
            item.update(group="boundary_lifecycle", domain=domain, variant=variant)
            cases.append(item)
    return cases


def encode(events, reset_at_boundary=False):
    ids = list(dict.fromkeys(e["creates"] for e in events if e["creates"]))
    encoded = {"event_ids": [e["event_id"] for e in events], "obligation_ids": ids,
               "actions": [], "creates": [], "carry": [], "persist": [], "observations": []}
    previous_scene = None
    for e in events:
        changed = previous_scene is not None and e["scene_id"] != previous_scene
        if e["boundary"] and not changed:
            raise ValueError("Boundary bindings must occur at a scene change")
        encoded["actions"].append({"STOP": 0, "WAIT": 1, "GO": 2}[e["action"]])
        encoded["creates"].append(ids.index(e["creates"]) if e["creates"] else -1)
        for oid in ids:
            link = e["boundary"].get(oid, binding("UNCERTAIN"))
            status = link["status"]
            carry = {"VERIFIED": 1, "ENDED": 0, "UNCERTAIN": -1}[status] if changed else 2
            if changed and reset_at_boundary:
                carry = 0
            encoded["carry"].append(carry)
            encoded["persist"].append(int(changed and status == "VERIFIED" and link["evidence_valid_across_boundary"]))
            value = e["evidence"].get(oid, -1)
            if value not in (-1, 0, 1):
                raise ValueError("Release evidence must be -1, 0, or 1")
            encoded["observations"].append(value)
        previous_scene = e["scene_id"]
    return encoded


def model_bytes(e):
    def array(values):
        return "{" + ",".join(map(str, values)) + "}"
    n, k = len(e["event_ids"]), len(e["obligation_ids"])
    declaration = f"""const int N={n}; const int K={k};
const int actions[N]={array(e['actions'])};
const int creates[N]={array(e['creates'])};
const int carry[N*K]={array(e['carry'])};
const int persist[N*K]={array(e['persist'])};
const int observations[N*K]={array(e['observations'])};
bool active[K]; bool linked[K]; int known[K]={array([-1]*k)};
int idx=0; bool bad=false; bool missing=false;
int first_bad_idx=-1; int first_missing_idx=-1;
int first_bad_obligation=-1; int first_missing_obligation=-1;
void step() {{
  int j; int p;
  for (j=0; j<K; j++) {{
    p=idx*K+j;
    if (carry[p] != 2) {{
      linked[j]=(carry[p] == 1);
      if (carry[p] == 0) active[j]=false;
      if (carry[p] != 1 || persist[p] == 0) known[j]=-1;
    }}
  }}
  if (creates[idx] >= 0) {{
    active[creates[idx]]=true;
    linked[creates[idx]]=true;
    known[creates[idx]]=-1;
  }}
  for (j=0; j<K; j++) {{
    p=idx*K+j;
    if (linked[j] && observations[p] >= 0) known[j]=observations[p];
    if (active[j] && linked[j] && known[j] == 1) active[j]=false;
  }}
  if (actions[idx] == 2) {{
    for (j=0; j<K; j++) {{
      if (active[j] && linked[j] && known[j] == 0) {{
        bad=true;
        if (first_bad_idx < 0) {{ first_bad_idx=idx; first_bad_obligation=j; }}
      }}
      if (active[j] && (!linked[j] || known[j] == -1)) {{
        missing=true;
        if (first_missing_idx < 0) {{ first_missing_idx=idx; first_missing_obligation=j; }}
      }}
    }}
  }}
}}"""
    root = ET.Element("nta")
    ET.SubElement(root, "declaration").text = declaration
    template = ET.SubElement(root, "template")
    ET.SubElement(template, "name").text = "CrossSceneObserver"
    for identifier, name in (("run", "Run"), ("done", "Done")):
        location = ET.SubElement(template, "location", {"id": identifier})
        ET.SubElement(location, "name").text = name
        if identifier == "run":
            ET.SubElement(location, "committed")
    ET.SubElement(template, "init", {"ref": "run"})
    for target, guard, update in (("run", "idx < N", "step(), idx++"), ("done", "idx == N", None)):
        transition = ET.SubElement(template, "transition")
        ET.SubElement(transition, "source", {"ref": "run"})
        ET.SubElement(transition, "target", {"ref": target})
        ET.SubElement(transition, "label", {"kind": "guard"}).text = guard
        if update:
            ET.SubElement(transition, "label", {"kind": "assignment"}).text = update
    ET.SubElement(root, "system").text = "Observer=CrossSceneObserver(); system Observer;"
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def parse_result(raw, encoded):
    flags = [not bool(x) for x in re.findall(r"Formula\s+is\s+(?:(NOT)\s+)?satisfied", raw)]
    if len(flags) != len(QUERIES) or not flags[2] or flags[0] == flags[3] or flags[1] == flags[4]:
        raise ValueError("Missing, incomplete, or inconsistent UPPAAL query results")
    verdict = "CONTRADICTION" if not flags[0] else "UNKNOWN" if not flags[1] else "CONSISTENT"
    issue_event = obligation = None
    if verdict != "CONSISTENT":
        prefix = "first_bad" if verdict == "CONTRADICTION" else "first_missing"
        def index(name):
            values = [int(x) for x in re.findall(r"\b" + name + r"\s*=\s*(-?\d+)", raw)]
            return next(x for x in values if x >= 0)
        issue_event = encoded["event_ids"][index(prefix + "_idx")]
        obligation = encoded["obligation_ids"][index(prefix + "_obligation")]
    return {"verdict": verdict, "issue_event_id": issue_event, "obligation_id": obligation,
            "query_statuses": flags}


def audit_natural_inputs():
    batch_path = OWNER / "artifacts/public/multiscene-chain/uppaal-loop-batch-all-strict-1s.json"
    batch = json.loads(batch_path.read_text())
    metadata = ROOT / "data/baseline/nuscenes_metadata/interp_12Hz_trainval"
    required = ("condition_id", "subject_ref", "identity_witness", "applicability_witness", "release_truth")
    boundary_count = verified_count = 0
    missing_fields = Counter()
    inspected = []
    for row in batch["items"]:
        stem = row["scenes"][0] + "-to-" + row["scenes"][-1] + "-loop-result.json"
        path = batch_path.parent / stem
        record = json.loads(path.read_text())
        inspected.append({"path": str(path.relative_to(ROOT)), "sha256": digest(path)})
        for event in record["events"]:
            if event["channel"] != "scene_boundary":
                continue
            boundary_count += 1
            bindings = event["detail"].get("semantic_bindings", [])
            verified_count += sum(all(key in b for key in required) for b in bindings)
            for key in required:
                if not any(key in b for b in bindings):
                    missing_fields[key] += 1
    return {"status": "NOT_RUN_NATURAL_CROSS_SCENE_SEMANTICS",
            "saved_chain_count": batch["result_count"],
            "saved_scene_count": len({s for r in batch["items"] for s in r["scenes"]}),
            "official_metadata_present": metadata.is_dir(),
            "boundary_count": boundary_count,
            "verified_semantic_boundary_bindings": verified_count,
            "boundary_missing_fields": dict(missing_fields),
            "inspected_inputs": inspected,
            "reasons": ["OBJECT_AND_CONDITION_CONTINUITY_NOT_ESTABLISHED",
                        "SOURCE_PREDICATE_TRUTH_NOT_ANNOTATED"],
            "saved_input": str(batch_path.relative_to(ROOT)), "saved_input_sha256": digest(batch_path),
            "note": "Saved speed-request replay results do not supply pedestrian, signal, or obstacle identities and release truth."}


def prepare(output):
    output.mkdir(parents=True, exist_ok=False)
    cases = build_cases()
    save(output / "cases.json", cases)
    save(output / "protocol.json", {
        "project_id": "sequential-coc-verification", "domains": list(DOMAINS),
        "case_count": len(cases), "joint_vectors": 27, "scene_counts": [2, 3],
        "lifecycle_variants": VARIANTS, "queries": QUERIES,
        "expected_labels": "AUTHORED_BEFORE_SOLVER_NO_CASE_FILTERING",
        "human_gold": False, "independent_external_test": False,
        "scope": "Supplied stop-until predicates and GO; not arbitrary joint constraint satisfiability or physical safety.",
        "boundary_policy": "Carry only on supplied identity/applicability; uncertain links retain an unresolved obligation and reject guessed release evidence; ended scopes discard; point evidence expires.",
        "baseline": "Same model and inputs, discard active obligations at every scene boundary.",
    })
    save(output / "natural_input_audit.json", audit_natural_inputs())
    manifest = {"project_id": "sequential-coc-verification", "task_id": "cross-scene-constraints",
                "status": "PREPARED", "created_at": datetime.now(timezone.utc).isoformat(),
                "inputs": [str(Path(__file__).relative_to(ROOT)),
                           "projects/03-sequential-coc-verification/artifacts/public/multiscene-chain/uppaal-loop-batch-all-strict-1s.json"],
                "source_sha256": digest(Path(__file__)),
                "cases_sha256": digest(output / "cases.json"), "protocol_sha256": digest(output / "protocol.json"),
                "natural_input_audit_sha256": digest(output / "natural_input_audit.json"),
                "existing_condition_model_sha256": digest(OWNER / "experiments/kiee_review_revision/condition_model.py"),
                "source_kind": "AUTHORED_SYMBOLIC", "human_gold": False, "independent_external_test": False}
    save(output / "RUN_MANIFEST.json", manifest)
    for item in cases:
        for mode in ("carry", "reset"):
            folder = output / "models" / item["case_id"] / mode
            folder.mkdir(parents=True)
            (folder / "model.xml").write_bytes(model_bytes(encode(item["events"], mode == "reset")))
            (folder / "queries.q").write_text("\n".join(QUERIES) + "\n")
    manifest["model_input_sha256"] = {
        str(p.relative_to(output)): digest(p) for p in sorted((output / "models").rglob("*")) if p.is_file()
    }
    save(output / "RUN_MANIFEST.json", manifest)
    print(json.dumps({"status": "PREPARED", "case_count": len(cases), "output": str(output)}), flush=True)


def evaluate(output, verifyta):
    manifest = json.loads((output / "RUN_MANIFEST.json").read_text())
    if manifest["status"] != "PREPARED":
        raise ValueError("Evaluation requires a prepared, unused run")
    for filename, key in (("cases.json", "cases_sha256"), ("protocol.json", "protocol_sha256")):
        if digest(output / filename) != manifest[key]:
            raise ValueError("Frozen input changed: " + filename)
    if digest(Path(__file__)) != manifest["source_sha256"]:
        raise ValueError("Source changed after preparation")
    for name, expected_digest in manifest["model_input_sha256"].items():
        if digest(output / name) != expected_digest:
            raise ValueError("Frozen model input changed: " + name)
    cases = json.loads((output / "cases.json").read_text())
    rows = []
    for i, item in enumerate(cases):
        row = {"case_id": item["case_id"], "group": item["group"], "expected": item["expected"]}
        for mode in ("carry", "reset"):
            folder = output / "models" / item["case_id"] / mode
            command = [str(verifyta), "-q", "-t1", str(folder / "model.xml"), str(folder / "queries.q")]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
            (folder / "stdout.txt").write_text(completed.stdout)
            (folder / "stderr.txt").write_text(completed.stderr)
            if completed.returncode:
                raise RuntimeError(f"UPPAAL failed: {item['case_id']}/{mode}; see stderr.txt")
            row[mode] = parse_result(completed.stdout + completed.stderr, encode(item["events"], mode == "reset"))
            row[mode]["model_sha256"] = digest(folder / "model.xml")
            row[mode]["stdout_sha256"] = digest(folder / "stdout.txt")
            row[mode]["stderr_sha256"] = digest(folder / "stderr.txt")
        rows.append(row)
        if (i + 1) % 10 == 0:
            print(json.dumps({"completed_cases": i + 1, "total": len(cases)}), flush=True)
    save(output / "results.json", rows)
    result = {"status": "COMPLETED", "case_count": len(rows), "solver_model_runs": 2 * len(rows),
              "expected_counts": dict(Counter(r["expected"]["verdict"] for r in rows)),
              "carry_verdict_matches": sum(r["carry"]["verdict"] == r["expected"]["verdict"] for r in rows),
              "carry_issue_matches": sum(all(r["carry"][key] == r["expected"][key] for key in ("issue_event_id", "obligation_id")) for r in rows),
              "reset_verdict_matches": sum(r["reset"]["verdict"] == r["expected"]["verdict"] for r in rows),
              "reset_prediction_counts": dict(Counter(r["reset"]["verdict"] for r in rows)),
              "natural_scene_semantic_cases_verified": 0,
              "evidence_level": "AUTHORED_CROSS_SCENE_FEASIBILITY_NOT_INDEPENDENT_ACCURACY"}
    save(output / "RESULT.json", result)
    report = f"""# 장면 간 보행자·신호·장애물 제약 연결 시험

보행자 통과, 적용 신호의 진행 허용, 장애물 해소를 각각 독립적인 stop-until 의무로 표현했다. 장면 경계에서 대상 동일성·적용 범위·근거 유효성을 입력으로 제공하고, 남은 의무와 후속 GO의 충돌을 실제 UPPAAL로 검사했다. 영상·자연어에서 이 입력을 자동으로 확정한 실험은 아니다.

- 작성 사례: {len(rows)}건. 세 조건의 참/거짓/미상 27조합 × 2종의 장면 길이(2/3 scene) 54건, 종류별 경계·재활성화 9변형 × 3종 27건.
- 기대 판정: {result['expected_counts']}.
- 장면 간 유지 모델 판정 일치: {result['carry_verdict_matches']}/{len(rows)}.
- 최초 문제 사건·관련 의무 일치: {result['carry_issue_matches']}/{len(rows)} (정상 사례의 null 포함).
- 경계에서 의무를 버리는 비교 모델 판정 일치: {result['reset_verdict_matches']}/{len(rows)}.
- 비교 모델 판정 분포: {result['reset_prediction_counts']}.
- 실제 solver 실행: {result['solver_model_runs']}개 모델, 각 5개 query. XML/query/stdout/stderr 보존.

## 연결 정책

확인된 대상·적용 범위만 연결한다. 동일성이 미상이면 기존 의무는 미해결로 남기고 추정 대응에 의한 해제를 막는다. 명시적으로 적용 범위가 종료된 의무는 다음 장면에 강제하지 않는다. 순간 관측은 경계에서 만료하고, 경계를 포함하는 유효 구간을 명시한 증거만 유지한다. 재활성화 시 과거 해제 증거를 초기화한다.

## 실제 자료와 주장 범위

기존 multi-scene 13 chain/29 scene의 속도 요구·반응 결과는 존재하지만 세 의미 조건의 대상 동일성, 적용 범위 및 해제 참값 연결이 없다. 공식 trainval 전역 메타데이터도 현재 로컬에서 찾지 못했다. 자연 장면 간 의미 검증은 미실시(0건)이며 natural_input_audit.json에 근거를 기록했다.

이번 81건은 설계자가 입력과 기대 판정을 작성한 방법 실증이다. 새 모델과 같은 설계자가 관여했으므로 독립 시험이나 자연 오류 정확도가 아니다. 조건별 GO 금지를 검사하며 임의 제약 전체의 동시 만족 가능성, 정량 시간 제한, 객체 추적 정확도 또는 실제 안전을 검증하지 않는다. 기존 원고·모델·실험 결과는 수정하지 않았다.
"""
    (output / "REPORT_KO.md").write_text(report)
    version = subprocess.run([str(verifyta), "--version"], capture_output=True, text=True, timeout=15)
    manifest.update(status="COMPLETED", completed_at=datetime.now(timezone.utc).isoformat(),
                    verifyta=str(verifyta), verifyta_version=(version.stdout or version.stderr).splitlines()[0],
                    output_sha256={name: digest(output / name) for name in ("results.json", "RESULT.json", "REPORT_KO.md")})
    save(output / "RUN_MANIFEST.json", manifest)
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("prepare", "evaluate"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--verifyta", type=Path, default=ROOT / "runtime/solvers/uppaal-5.0.0-linux64/bin/verifyta")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-\d{3}", args.run_id):
        parser.error("run-id must be lowercase kebab-case with a three-digit suffix")
    destination = OWNER / "artifacts/public/cross-scene-constraints-001" / args.run_id
    if args.stage == "prepare":
        prepare(destination)
    else:
        evaluate(destination, args.verifyta.resolve())
