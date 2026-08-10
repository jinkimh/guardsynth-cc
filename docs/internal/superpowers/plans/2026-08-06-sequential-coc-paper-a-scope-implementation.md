# Sequential CoC 논문 A안 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 동일 장면 내부의 연속 CoC 계약 검증에 논문 범위를 고정하고, 계약 구조 사람 검토ㆍ탐색적 궤적 정합성ㆍclaim gate를 완성한 뒤 허용된 주장만 KIEE 원고에 반영한다.

**Architecture:** 기존 공통 IR, 상태형 Python 검사기와 UPPAAL 관찰자를 유지한다. 실제 상태를 텍스트로 추측하던 검토는 계약 구조 라벨 검토로 교체하고, 자연 텍스트ㆍ통제 변형ㆍ사람 궤적 결과를 독립 집계한다. 여러 장면의 automata를 전역 행동 모델로 합성하지 않는다.

**Tech Stack:** Python 3.12, 표준 `unittest`, pandas/pyarrow, NumPy, UPPAAL 5.0.0 `verifyta`, JSON/JSONL/CSV, 독립형 HTML, LaTeX.

## Global Constraints

- 프로젝트 루트는 `/home/jinhyun/prj_ws/prj_jin/guardsynth-cc`이다.
- 새 Python 코드는 `experiments/sequential_coc/`에만 둔다.
- 새 실험 결과는 `artifacts/results/restricted/sequential-coc-consistency-v1/`에만 둔다.
- 원자료, 기존 결과와 KIEE 원고는 자동 실험ㆍ사람 검토ㆍclaim gate가 끝나기 전에 수정하지 않는다.
- 제한 CoC 원문과 영상은 공개 경로, SDD 스냅샷, 시험 fixture와 보고서에 복사하지 않는다.
- 해제ㆍ객체ㆍ실행 증거가 없으면 FALSE로 추정하지 않고 `UNKNOWN` 또는 `EVIDENCE_REQUIRED`로 판정한다.
- 자연 자료, 통제 변형 자료와 궤적 자료를 별도 최상위 결과로 보고한다.
- 동일 장면의 여러 창과 원본ㆍ변형 쌍을 독립 표본으로 세지 않는다.
- 서로 다른 장면ㆍ시나리오의 automata를 하나의 전역 행동ㆍ제어 모델로 합성하지 않는다.
- 실제 교통법규, 충돌 위험, 물리 안전, 사람 행동의 최적성 또는 강화학습 성능을 주장하지 않는다.
- 비-Git 작업공간이므로 Git을 초기화하지 않는다. 각 작업 끝에 `RUN_LOG.md`와 `MANIFEST.sha256`을 갱신한다.
- 실제 `verifyta` 시험은 활성화된 UPPAAL 5.0.0 rev. `714BA9DB36F49691`로 실행하며 키를 출력ㆍ저장하지 않는다.

---

### Task 1: 상태 설문을 계약 구조 검토 패킷으로 교체

**Files:**
- Modify: `experiments/sequential_coc/build_review_app.py`
- Modify: `experiments/sequential_coc/tests/test_review_app.py`
- Replace atomically: `artifacts/results/restricted/sequential-coc-consistency-v1/review/REVIEW_PROTOCOL.md`
- Replace atomically: `artifacts/results/restricted/sequential-coc-consistency-v1/review/REVIEW_A.html`
- Replace atomically: `artifacts/results/restricted/sequential-coc-consistency-v1/review/REVIEW_B.html`
- Replace atomically: `artifacts/results/restricted/sequential-coc-consistency-v1/review/adjudication-mapping.json`
- Replace atomically: `artifacts/results/restricted/sequential-coc-consistency-v1/review/packet-manifest.json`
- Modify: `experiments/sequential_coc/tests/test_extract_windows.py`
- Modify: `artifacts/results/restricted/sequential-coc-consistency-v1/RUN_LOG.md`
- Modify: `artifacts/results/restricted/sequential-coc-consistency-v1/MANIFEST.sha256`

**Interfaces:**
- Consumes: `select_review_items(...)`의 승인된 23쌍/15후보 장면, earliest 15후보 + strict 12대조군 정책
- Produces: `build_contract_review_page(reviewer: str, items: Sequence[ReviewItem]) -> str`
- Produces CSV header:
  `review_id,obligation_explicit,required_action,persistence_explicit,release_condition_explicit,ordered_steps_explicit,textual_relation,state_evidence_needed,evidence_sufficiency,confidence,notes`

- [ ] **Step 1: 실제 상태 질문이 존재하면 실패하는 시험 작성**

```python
def test_contract_review_never_asks_actual_satisfaction_or_release_state(self):
    page = build_contract_review_page("A", [fixture_item()])
    self.assertNotIn("satisfaction_state", page)
    self.assertNotIn("release_state", page)
    self.assertIn("obligation_explicit", page)
    self.assertIn("state_evidence_needed", page)
```

- [ ] **Step 2: 새 CSV 계약과 선택지 시험 작성**

```python
def test_contract_review_csv_contract_is_exact(self):
    self.assertEqual(CONTRACT_REVIEW_FIELDS, (
        "review_id", "obligation_explicit", "required_action",
        "persistence_explicit", "release_condition_explicit",
        "ordered_steps_explicit", "textual_relation",
        "state_evidence_needed", "evidence_sufficiency", "confidence", "notes",
    ))
    self.assertEqual(CONTRACT_CHOICES["textual_relation"],
                     ("SUPPORTS", "CONTRADICTS", "INDEPENDENT", "AMBIGUOUS", "EVIDENCE_REQUIRED"))
```

- [ ] **Step 3: RED 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_review_app -v`

Expected: 기존 `satisfaction_state/release_state` 필드와 누락된 새 API 때문에 FAIL.

- [ ] **Step 4: 계약 구조 선택지 구현**

```python
CONTRACT_CHOICES = {
    "obligation_explicit": ("YES", "NO", "AMBIGUOUS"),
    "required_action": (
        "STOP_OR_HOLD", "YIELD_OR_DECELERATE", "ACCELERATE_OR_PROCEED",
        "MAINTAIN_SPEED", "OTHER", "AMBIGUOUS",
    ),
    "persistence_explicit": ("YES", "NO", "AMBIGUOUS"),
    "release_condition_explicit": ("YES", "NO", "AMBIGUOUS"),
    "ordered_steps_explicit": ("YES", "NO", "AMBIGUOUS"),
    "textual_relation": (
        "SUPPORTS", "CONTRADICTS", "INDEPENDENT", "AMBIGUOUS", "EVIDENCE_REQUIRED",
    ),
    "state_evidence_needed": ("YES", "NO", "AMBIGUOUS"),
    "evidence_sufficiency": ("SUFFICIENT", "INSUFFICIENT"),
    "confidence": ("LOW", "MEDIUM", "HIGH"),
}
```

- [ ] **Step 5: 블라인드ㆍ이스케이프ㆍCSV 기능 유지**

검토 HTML에는 실제 장면/창 ID, 후보ㆍ대조군, 검사기ㆍUPPAAL 판정, 원본ㆍ변형 상태를 넣지 않는다. CoC는 escaped HTML에만 두고 JavaScript에는 넣지 않는다. A/B는 동일 27개 항목을 서로 다른 고정 순서로 제공한다.

- [ ] **Step 6: 기존 패킷 해시를 기록하고 제한 경로에서 원자 교체**

교체 전 다섯 패킷 파일의 SHA-256을 `RUN_LOG.md`에 `SUPERSEDED_BEFORE_REVIEW`로 기록한다. 새 파일은 mode-0600 임시 파일을 검증한 뒤 `os.replace`로 게시한다. 사람 답변 CSV가 없음을 먼저 확인하며, 존재하면 교체하지 않고 `REVIEW_ALREADY_STARTED`로 중단한다.

- [ ] **Step 7: 새 패킷 생성**

Run: `runtime/alpamayo/ar1_venv/bin/python experiments/sequential_coc/build_review_app.py`

Expected JSON counts: raw candidate `23/15`, selected candidate `15/15`, strict controls `12/12`, total `27` independent clusters, status `WAITING_FOR_CONTRACT_REVIEW`.

- [ ] **Step 8: GREEN과 누출 감사**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_review_app -v`

Expected: 실제 상태 질문 부재, 새 CSV 계약, 동일 membership/다른 order, 금지 메타데이터 0, 제한 원문은 두 HTML과 natural JSONL에만 존재.

- [ ] **Step 9: 비-Git 체크포인트**

새 코드ㆍ시험ㆍ패킷ㆍ프로토콜ㆍ매핑ㆍmanifest 해시와 mode를 `RUN_LOG.md`와 누적 `MANIFEST.sha256`에 기록한다.

---

### Task 2: 계약 구조 검토 CSV 검증과 합의 게이트

**Files:**
- Create: `experiments/sequential_coc/contract_review.py`
- Create: `experiments/sequential_coc/tests/test_contract_review.py`
- Create after human input: `artifacts/results/restricted/sequential-coc-consistency-v1/review/contract-review-disagreements.csv`
- Consume only after supplied: `artifacts/results/restricted/sequential-coc-consistency-v1/review/contract_review_A.csv`
- Consume only after supplied: `artifacts/results/restricted/sequential-coc-consistency-v1/review/contract_review_B.csv`
- Consume only after supplied: `artifacts/results/restricted/sequential-coc-consistency-v1/review/contract_review_consensus.csv`

**Interfaces:**
- Produces: `validate_contract_review_csv(path: Path, expected_ids: set[str]) -> tuple[ContractReviewRow, ...]`
- Produces: `compare_contract_reviews(a, b) -> ReviewAgreement`
- Produces: `validate_consensus(rows, disagreements, expected_ids) -> tuple[ContractReviewRow, ...]`

- [ ] **Step 1: strict CSV 실패 시험 작성**

```python
def test_review_csv_rejects_wrong_header_duplicate_id_and_invalid_choice(self):
    with self.assertRaisesRegex(ValueError, "CSV_HEADER_MISMATCH"):
        validate_contract_review_csv(wrong_header_csv(), EXPECTED_IDS)
    with self.assertRaisesRegex(ValueError, "DUPLICATE_REVIEW_ID"):
        validate_contract_review_csv(duplicate_id_csv(), EXPECTED_IDS)
    with self.assertRaisesRegex(ValueError, "INVALID_CATEGORICAL_VALUE"):
        validate_contract_review_csv(invalid_choice_csv(), EXPECTED_IDS)
```

- [ ] **Step 2: RED 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_contract_review -v`

Expected: module import failure.

- [ ] **Step 3: strict loader와 일치도 구현**

UTF-8 BOM을 허용하고 header 순서, 정확한 27개 review ID, 중복, 빈 범주형 값, 선택지, notes 길이를 검증한다. 필드별 raw agreement와 Cohen kappa를 계산하되 상수 라벨이면 kappa는 `None`으로 기록한다.

- [ ] **Step 4: 불일치 파일 생성 시험**

```python
def test_disagreements_preserve_both_first_passes(self):
    report = compare_contract_reviews(rows_a(), rows_b())
    self.assertEqual(report.disagreement_ids, ("REV-0000000000000002",))
    self.assertEqual(report.rows_a[1].textual_relation, "SUPPORTS")
    self.assertEqual(report.rows_b[1].textual_relation, "AMBIGUOUS")
```

- [ ] **Step 5: 사람 입력 게이트 실행**

Run: `runtime/alpamayo/ar1_venv/bin/python experiments/sequential_coc/contract_review.py --review-dir artifacts/results/restricted/sequential-coc-consistency-v1/review`

Expected before CSVs: exit `0`, JSON status `WAITING_FOR_CONTRACT_REVIEW`; 답변ㆍ일치도ㆍ합의를 생성하지 않음.

- [ ] **Step 6: 두 CSV 뒤 불일치 목록 생성**

두 first-pass CSV가 모두 있을 때만 mode-0600 `contract-review-disagreements.csv`를 생성한다. 합의 CSV가 없으면 status `WAITING_FOR_CONSENSUS`로 중단한다.

- [ ] **Step 7: 합의 CSV 검증**

합의 파일은 모든 27개 ID를 포함하며, 불일치 항목은 합의 라벨을 명시하고 first-pass 원본을 수정하지 않는다. 완료 status는 `CONTRACT_REVIEW_COMPLETE`다.

- [ ] **Step 8: 체크포인트**

검토자별 행 수, 독립 cluster 수, 필드별 agreement/kappa, `AMBIGUOUS`, `EVIDENCE_REQUIRED`, `INSUFFICIENT` 수를 기록한다. 실제 CSV가 없으면 모두 `NOT_RUN`으로 유지한다.

---

### Task 3: 궤적 부분집합의 탐색적 행동 정합성

**Files:**
- Create: `experiments/sequential_coc/trajectory_contracts.py`
- Create: `experiments/sequential_coc/tests/test_trajectory_contracts.py`
- Create: `artifacts/results/restricted/sequential-coc-consistency-v1/trajectory-results.jsonl`

**Interfaces:**
- Produces: `classify_observed_action(ego_trace, thresholds) -> ObservedAction`
- Produces: `evaluate_trajectory_contract(events, ego_trace, thresholds) -> TrajectoryResult`
- `TrajectoryResult.verdict`: `ALIGNED`, `NOT_ALIGNED`, `UNKNOWN`

- [ ] **Step 1: 삼값 행동 정합성 시험 작성**

```python
def test_unknown_release_never_turns_human_proceed_into_coc_error(self):
    result = evaluate_trajectory_contract(unknown_release_events(), accelerating_trace(), T)
    self.assertEqual(result.verdict, "UNKNOWN")
    self.assertEqual(result.reason, "RELEASE_EVIDENCE_REQUIRED")
```

- [ ] **Step 2: RED 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_trajectory_contracts -v`

Expected: module import failure.

- [ ] **Step 3: 관측 행동 추상화 구현**

signed longitudinal speed만 사용해 `STOP_OR_HOLD`, `YIELD_OR_DECELERATE`, `MAINTAIN_SPEED`, `ACCELERATE_OR_PROCEED`, `UNKNOWN`을 판정한다. 차선 변경, 객체 간격과 실제 제동 명령은 판정하지 않는다.

- [ ] **Step 4: 임계값 세트 고정**

기존 논문 기본값을 `baseline`으로 기록하고 `strict`, `lenient` 민감도 두 세트를 추가한다. 세 값은 규범 안전 기준이 아니라 행동 추상화 매개변수로 명시한다.

- [ ] **Step 5: 94장면 실행**

94장면/403사건의 로컬 egomotion에 연결 가능한 사건만 처리한다. 자연 창이 중복되면 scene/event identity로 deduplicate하고 결과의 `sample_unit`을 scene cluster와 event로 각각 기록한다.

- [ ] **Step 6: 출력 검증**

`ALIGNED/NOT_ALIGNED/UNKNOWN` 수, 연결 실패 이유, 세 임계값의 판정 변화만 저장한다. 사람 행동을 ground truth, 안전 또는 최적 행동으로 부르지 않는다.

- [ ] **Step 7: GREEN과 체크포인트**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_trajectory_contracts -v`

Expected: synthetic normal/mismatch/UNKNOWN와 threshold-boundary tests PASS. JSONL mode-0600, restricted parent mode-0700, SHA-256 기록.

---

### Task 4: 분리 평가와 claim gate

**Files:**
- Create: `experiments/sequential_coc/evaluate.py`
- Create: `experiments/sequential_coc/tests/test_evaluate.py`
- Create: `artifacts/results/restricted/sequential-coc-consistency-v1/metrics.json`

**Interfaces:**
- Produces: `wilson_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]`
- Produces: `cohens_kappa(labels_a, labels_b) -> float | None`
- Produces: `evaluate_all(inputs: EvaluationInputs) -> dict[str, object]`

- [ ] **Step 1: 결과 영역 분리 시험 작성**

```python
def test_natural_mutation_and_trajectory_results_never_share_denominators(self):
    result = evaluate_all(fixture_inputs())
    self.assertEqual(result["controlled_mutation"]["pair_count"], 40)
    self.assertEqual(result["natural_contract_review"]["cluster_count"], 27)
    self.assertIn("UNKNOWN", result["trajectory_exploratory"]["verdict_counts"])
```

- [ ] **Step 2: claim gate 실패 시험 작성**

```python
def test_claim_gate_never_promotes_text_review_to_actual_state_ground_truth(self):
    gate = evaluate_all(fixture_inputs())["claim_gate"]
    self.assertFalse(gate["NATURAL_ACTUAL_STATE_READY"])
    self.assertTrue(gate["MUTATION_EVALUABLE"])
```

- [ ] **Step 3: RED 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_evaluate -v`

Expected: module import failure.

- [ ] **Step 4: 지표 구현**

통제 쌍은 유형별 검출률, Wilson interval, 정상 원본 오탐률, 사건별 대비 상태형 추가 검출을 계산한다. 자연 계약 검토는 구조 라벨의 agreement/kappa와 consensus count만 계산한다. 궤적은 정합성 교차표와 임계값 민감도만 계산한다.

- [ ] **Step 5: claim gate 구현**

```python
claim_gate = {
    "MUTATION_EVALUABLE": mutation_pair_count == 40,
    "UPPAAL_EQUIVALENT": uppaal_mismatch_count == 0 and actual_verifyta_ran,
    "NATURAL_CONTRACT_DESCRIPTIVE": contract_consensus_available,
    "NATURAL_QUANTITATIVE_READY": evaluable_textual_clusters >= 20,
    "NATURAL_ACTUAL_STATE_READY": False,
    "TRAJECTORY_EXPLORATORY": linked_trajectory_count > 0,
    "GLOBAL_COC_MODEL_CLAIM": False,
    "PHYSICAL_SAFETY_CLAIM": False,
    "LEARNING_PERFORMANCE_CLAIM": False,
}
```

- [ ] **Step 6: 전체 평가 실행**

사람 CSV/합의가 없으면 exit `0`, status `WAITING_FOR_CONTRACT_REVIEW`, 자연 agreement와 KIEE 수정은 `NOT_RUN`. 존재하면 모든 단위를 교차검증하고 `metrics.json`을 mode-0600으로 원자 게시한다.

- [ ] **Step 7: 전체 시험**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s experiments/sequential_coc/tests -v`

Expected: 실제 licensed verifyta 포함 no skip, manifest regression 포함 PASS.

---

### Task 5: 장면 경계 출처 정책 보조 실험

**Files:**
- Create: `experiments/sequential_coc/cross_scene_boundary.py`
- Create: `experiments/sequential_coc/tests/test_cross_scene_boundary.py`
- Create: `artifacts/results/restricted/sequential-coc-consistency-v1/cross-scene-secondary.json`

**Interfaces:**
- Produces: `evaluate_boundary_policy(chain: dict, carryover: bool, provenance_supported: bool) -> CheckResult`

- [ ] **Step 1: 출처 없는 이월 시험 작성**

```python
def test_unproven_carryover_is_policy_error_not_natural_semantic_conflict(self):
    result = evaluate_boundary_policy(fixture_chain(), True, False)
    self.assertEqual(result.contradiction_types,
                     (ContradictionType.UNSUPPORTED_CARRYOVER,))
```

- [ ] **Step 2: RED 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_cross_scene_boundary -v`

Expected: module import failure.

- [ ] **Step 3: discard/carryover 정책 구현**

기존 13체인, 29고유 장면, 16경계를 재확인한다. provenance가 확인되지 않은 carryover만 `UNSUPPORTED_CARRYOVER`로 기록하고 네 자연 의미 모순 수에 합치지 않는다.

- [ ] **Step 4: 실행과 체크포인트**

Run: `runtime/alpamayo/ar1_venv/bin/python experiments/sequential_coc/cross_scene_boundary.py`

Expected: `evidence_level="PROVENANCE_POLICY_EXAMPLE"`, `global_model_claim=false`, exact input counts or explicit `INPUT_INVENTORY_MISMATCH`.

---

### Task 6: 재현 실행기와 최종 manifest

**Files:**
- Create: `experiments/sequential_coc/run_experiment.py`
- Create: `experiments/sequential_coc/tests/test_run_experiment.py`
- Modify: `artifacts/results/restricted/sequential-coc-consistency-v1/RUN_LOG.md`
- Modify: `artifacts/results/restricted/sequential-coc-consistency-v1/MANIFEST.sha256`

**Interfaces:**
- Produces CLI: `run_experiment.py --stage inventory|extract|compile|check|uppaal|mutate|review|trajectory|evaluate|secondary|all`

- [ ] **Step 1: 사람 검토 게이트 시험 작성**

```python
def test_all_stops_without_contract_review_csvs_and_never_touches_paper(self):
    result = run_all(fixture_config(contract_review_csvs=[]))
    self.assertEqual(result.status, "WAITING_FOR_CONTRACT_REVIEW")
    self.assertFalse(result.paper_modified)
```

- [ ] **Step 2: RED 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_run_experiment -v`

Expected: module import failure.

- [ ] **Step 3: 단계 실행기 구현**

각 stage는 기존 공개 함수만 호출하고 subprocess 실패, missing artifact, hash mismatch를 유한 상태로 기록한다. `all`은 새 검토 CSV가 없으면 성공으로 위장하지 않고 정상적인 wait status로 종료한다.

- [ ] **Step 4: 보호 체크포인트 검증**

Task 1의 reasoning parquet, 98 egomotion parquet, 1,610 기존 결과 파일과 541 KIEE 파일 해시를 재계산한다. 불일치 시 `PROTECTED_INPUT_CHANGED`로 중단한다.

- [ ] **Step 5: 실제 verifyta 포함 전체 실행**

Run: `runtime/alpamayo/ar1_venv/bin/python experiments/sequential_coc/run_experiment.py --stage all`

Expected before review: 자동 단계 PASS, status `WAITING_FOR_CONTRACT_REVIEW`, KIEE 해시 불변.

- [ ] **Step 6: 최종 자동 시험과 manifest**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s experiments/sequential_coc/tests -v`

Run from restricted result root: `sha256sum -c MANIFEST.sha256`

Expected: no skipped actual-UPPAAL test, 모든 manifest entry `OK`, 허용 경로 밖 제한 원문 복사 0.

---

### Task 7: claim gate 기반 KIEE 원고 보완

**Files:**
- Modify only after completed consensus and metrics gate: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/main.tex`
- Modify only after gate: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/01-introduction.tex`
- Modify only after gate: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/02-related-work.tex`
- Modify only after gate: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/04-problem.tex`
- Modify only after gate: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/05-method.tex`
- Modify only after gate: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/06-experiments.tex`
- Modify only after gate: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/07-results.tex`
- Modify only after gate: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/08-discussion.tex`
- Modify only after gate: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/09-threats.tex`
- Modify only after gate: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/10-conclusion.tex`
- Modify/Add only after gate: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/figures/`

**Interfaces:**
- Consumes: completed `metrics.json`, contract-review agreement/consensus, trajectory results, actual UPPAAL witness and `claim_gate`
- Produces: KIEE PDF whose claims are mechanically audited against the gate

- [ ] **Step 1: 논문 수정 게이트 시험 작성**

```python
def test_paper_update_rejects_waiting_or_forbidden_claims(self):
    with self.assertRaisesRegex(RuntimeError, "CLAIM_GATE_CLOSED"):
        prepare_paper_update(waiting_metrics())
    self.assertFalse(approved_metrics()["claim_gate"]["GLOBAL_COC_MODEL_CLAIM"])
```

- [ ] **Step 2: 게이트 전 시험 실패 확인**

Run from paper root: `python3 -m unittest discover -s tests -v`

Expected: 새 A안 주장ㆍ금지어 감사가 원고 수정 전 FAIL.

- [ ] **Step 3: 허용된 주장만 반영**

주 결과는 통제 변형과 사건별 대비 상태형 추가 검출, 실제 Python–UPPAAL 동등성 및 대표 반례다. 자연 결과는 계약 구조 명시성, 궤적은 탐색적 정합성으로 분리한다. 통합 CoC 모델, 환경 강건성, 물리 안전과 학습 성능 표현을 넣지 않는다.

- [ ] **Step 4: 최소 그림ㆍ표 생성**

그림: 장면 내부 계약 상태기계, 정상–변형 쌍, 대표 UPPAAL 반례. 표: 자연 계약 구조, 통제 변형, 사건별/상태형 비교, 궤적 탐색 결과를 각각 분리한다. 전역 Environment–Controller–Plant 모델은 결과 그림으로 넣지 않는다.

- [ ] **Step 5: LaTeX와 주장 감사**

Run from paper root: `make clean && make`

Run: `python3 -m unittest discover -s tests -v`

Expected: PDF build PASS, 금지 주장 0, 수치가 `metrics.json`과 일치.

- [ ] **Step 6: 최종 manifest와 완료 보고**

PDF 경로, 페이지 수, 논문 시험 수, PDF SHA-256, 전체 실험 manifest 결과를 기록한다. 자연 검토가 완료되지 않았거나 claim gate가 닫혀 있으면 Task 7은 `NOT_RUN`이며 원고 해시를 보존한다.

---

## 실행 중단 규칙

- 새 계약 구조 검토 CSV가 없으면 Task 2 Step 5에서 `WAITING_FOR_CONTRACT_REVIEW`로 멈춘다.
- 두 검토자의 불일치가 있고 합의 CSV가 없으면 `WAITING_FOR_CONSENSUS`로 멈춘다.
- 보호 입력 해시가 바뀌면 `PROTECTED_INPUT_CHANGED`로 멈춘다.
- 실제 verifyta가 실행되지 않으면 `UPPAAL_EQUIVALENT=false`이며 논문 결과 수정은 금지한다.
- 자연 텍스트 판정 가능 cluster가 20개 미만이면 자연 정량 주장을 하지 않는다.
- 어떤 중단도 임의 라벨, 합의, 수치 또는 사람 답변을 생성하는 이유가 될 수 없다.
