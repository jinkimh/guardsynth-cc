# Sequential CoC Consistency Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 동일 주행 클립 안의 연속 CoC를 의무ㆍ해제 상태로 연결하고, 사건별 검사로 놓치는 시간적 모순을 상태형 Python과 UPPAAL로 검출ㆍ평가한 뒤 KIEE 원고를 실험 결과에 맞게 보완한다.

**Architecture:** 공통 `ContractEvent` 중간표현을 중심으로 자료 추출기, 계약 컴파일러, 사건별 기준선, 상태형 Python 검사기와 UPPAAL 생성기를 분리한다. 자연 자료와 통제된 변형 자료는 같은 검사 인터페이스를 사용하지만 결과와 정답은 분리 보관하며, 궤적 연결은 증거가 있는 사례에만 삼값 판정을 적용한다.

**Tech Stack:** Python 3.12, 표준 `unittest`, pandas/pyarrow, NumPy, UPPAAL `verifyta`, JSON/JSONL/CSV, LaTeX.

## Global Constraints

- 주 실험 단위는 서로 다른 장면이 아니라 동일 장면 내부의 시점 순 CoC 사건 창이다.
- 분석 대상은 우선 종방향 `STOP_OR_HOLD`, `YIELD_OR_DECELERATE`, `ACCELERATE_OR_PROCEED`, `MAINTAIN_SPEED`로 제한한다.
- 증거 부재를 거짓으로 바꾸지 말고 `UNKNOWN`으로 보류한다.
- 자연 관측과 인위적 변형을 같은 결과 표본으로 합치지 않는다.
- 동일 장면의 여러 창과 원본ㆍ변형 쌍을 독립 표본으로 세지 않는다.
- 기존 데이터, 기존 결과 및 현재 KIEE 원고를 실험 완료 전 수정하지 않는다.
- 새 결과는 `experiments/results/restricted/sequential-coc-consistency-v1/`에만 쓴다.
- 제한 자료의 원문 CoC와 영상은 공개 경로로 복사하지 않는다.
- 물리적 안전, 실제 교통법규 위반, 인과 관계 또는 학습 성능 향상을 주장하지 않는다.
- 현재 작업 루트는 Git 저장소가 아니다. Git을 새로 초기화하지 말고 각 작업의 체크포인트를 `RUN_LOG.md`와 SHA-256 manifest에 기록한다. 향후 Git 저장소에서 실행할 경우에만 작업별 커밋을 만든다.

---

## File Structure

```text
projects/sequential-coc-verification/experiments/sequential_coc/
  __init__.py                 # 공개 인터페이스와 버전
  contract_ir.py              # enum, dataclass, JSON 직렬화
  extract_windows.py          # 94장면 재고와 장면 내부 사건 창 추출
  contract_compiler.py        # CoC 문장/주석을 계약 중간표현으로 변환
  event_local_checker.py      # 이전 상태를 보지 않는 기준선
  stateful_checker.py         # 의무ㆍ해제 상태를 추적하는 기준 구현
  uppaal_generator.py         # 동일 의미론의 UPPAAL XML/query 생성
  run_uppaal.py               # verifyta 실행과 반례 요약
  mutation_generator.py       # 쌍대 통제 변형 생성
  build_review_app.py         # 자연 사건 창의 블라인드 검토 HTML/CSV
  trajectory_contracts.py     # 자차 궤적의 삼값 계약 판정
  cross_scene_boundary.py     # 13체인의 출처ㆍ경계 보조 분석
  evaluate.py                 # 일치도, 성능, 신뢰구간과 교차표
  run_experiment.py           # 단계별 오케스트레이션과 manifest
  tests/
    fixtures.py               # 작업 전체에서 공유하는 정상ㆍ모순 사건 생성기
    test_*.py                 # 위 모듈별 unittest

experiments/results/restricted/sequential-coc-consistency-v1/
  inventory.json
  natural-windows.jsonl
  mutations.jsonl
  checker-results.jsonl
  trajectory-results.jsonl
  cross-scene-secondary.json
  metrics.json
  review/
  uppaal-models/
  traces/
  figures/
  RUN_LOG.md
  MANIFEST.sha256
```

### Task 1: 실험 재고와 불변 기준선 고정

**Files:**
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_extract_windows.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/extract_windows.py`
- Create: `experiments/results/restricted/sequential-coc-consistency-v1/RUN_LOG.md`
- Create: `experiments/results/restricted/sequential-coc-consistency-v1/inventory.json`

**Interfaces:**
- Consumes: `data/baseline/coc_nusc/reasoning/ood_reasoning.parquet`, `data/baseline/coc_nusc/labels/egomotion/*.parquet`
- Produces: `load_reasoning_events(path: Path) -> dict[str, list[dict]]`, `build_inventory(events, ego_scene_ids) -> dict`

- [ ] **Step 1: 실패하는 재고 시험 작성**

```python
def test_inventory_preserves_known_chunk0_counts(self):
    events = load_reasoning_events(REASONING)
    inventory = build_inventory(events, local_egomotion_scene_ids(EGO_DIR))
    self.assertEqual(inventory["trajectory_subset"]["scene_count"], 94)
    self.assertEqual(inventory["trajectory_subset"]["event_count"], 403)
    self.assertEqual(inventory["trajectory_subset"]["scenes_with_two_or_more"], 90)
    self.assertEqual(inventory["trajectory_subset"]["adjacent_pair_count"], 309)
```

- [ ] **Step 2: 시험 실패 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_extract_windows -v`

Expected: `ModuleNotFoundError` 또는 구현 함수 부재로 FAIL.

- [ ] **Step 3: 최소 재고 구현**

JSON 문자열인 `events` 열을 시점순으로 읽고, 장면 수ㆍ사건 수ㆍ2개 이상 사건 장면ㆍ인접 쌍을 계산한다. 원문 CoC는 `inventory.json`에 쓰지 않는다.

- [ ] **Step 4: 시험과 실제 재고 실행**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_extract_windows -v`

Run: `runtime/alpamayo/ar1_venv/bin/python projects/sequential-coc-verification/experiments/sequential_coc/extract_windows.py --inventory-only`

Expected: 시험 PASS, `94/403/90/309`가 재현되고 전체 주석 재고도 `743/3218/677/2475`로 기록됨.

- [ ] **Step 5: 체크포인트 기록**

`RUN_LOG.md`에 명령, 종료 코드와 재고 SHA-256을 기록한다. Git이 있는 환경에서만 `git commit -m "test: lock sequential CoC inventory"`를 수행한다.

### Task 2: 계약 중간표현과 삼값 증거 의미론

**Files:**
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/__init__.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/contract_ir.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/fixtures.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_contract_ir.py`

**Interfaces:**
- Produces: `Action`, `EvidenceValue`, `ObligationState`, `ContradictionType`, `ContractEvent`, `EventWindow`, `CheckResult`
- Produces: `ContractEvent.to_dict() -> dict`, `ContractEvent.from_dict(value: dict) -> ContractEvent`
- `ContractEvent` 필드: `scene_id: str`, `event_id: str`, `timestamp_us: int`, `action: Action`, `trigger: str | None`, `target: str | None`, `satisfaction_known: bool`, `satisfaction_value: bool`, `release_known: bool`, `release_value: bool`, `permitted_next_action: Action | None`, `phase_index: int`, `provenance: str`, `parse_status: str`, `source_text: str | None`.
- `tests/fixtures.py`는 이후 시험에서 쓰는 `event`, `hold_event`, `proceed_event`, `clear_then_go_window`, `conflict_then_valid_release`, `known_hold`, `unknown_release`, `accelerating_trace`, `fixture_results`를 실제 `ContractEvent`/`EventWindow` 값으로 생성한다.

- [ ] **Step 1: 삼값과 직렬화 실패 시험 작성**

```python
def test_unknown_release_is_not_false(self):
    event = ContractEvent(
        scene_id="scene-x", event_id="e0", timestamp_us=0,
        action=Action.STOP_OR_HOLD,
        release_known=False, release_value=False,
    )
    restored = ContractEvent.from_dict(event.to_dict())
    self.assertEqual(restored.release_evidence, EvidenceValue.UNKNOWN)
```

- [ ] **Step 2: 시험 실패 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_contract_ir -v`

Expected: 타입과 직렬화 함수 부재로 FAIL.

- [ ] **Step 3: 불변 dataclass 구현**

`release_known`과 `release_value`를 별도 필드로 유지하고, `UNKNOWN/FALSE/TRUE`를 속성으로 계산한다. `source_text`는 제한 결과에만 둘 수 있도록 직렬화 시 `include_text=False`를 기본값으로 한다.

- [ ] **Step 4: round-trip 및 유효성 시험 통과**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_contract_ir -v`

Expected: 잘못된 타임스탬프 순서와 모순되는 known/value 조합도 명시적 예외로 검출하며 PASS.

- [ ] **Step 5: 체크포인트 기록**

인터페이스 서명을 `RUN_LOG.md`에 기록한다. Git이 있으면 `git commit -m "feat: define sequential CoC contract IR"`.

### Task 3: 장면 내부 사건 창 추출

**Files:**
- Modify: `projects/sequential-coc-verification/experiments/sequential_coc/extract_windows.py`
- Modify: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_extract_windows.py`
- Create: `experiments/results/restricted/sequential-coc-consistency-v1/natural-windows.jsonl`

**Interfaces:**
- Produces: `build_event_windows(scene_id: str, events: list[dict], max_followups: int = 3) -> list[EventWindow]`
- Produces: `screen_transition_candidates(windows) -> dict[str, list[str]]`

- [ ] **Step 1: 시간순ㆍ중복ㆍ군집 단위 시험 작성**

```python
def test_window_keeps_scene_cluster_and_up_to_three_followups(self):
    # event()는 tests/fixtures.py의 ContractEvent 생성기이다.
    events = [event(3_000_000), event(1_000_000), event(2_000_000), event(4_000_000)]
    windows = build_event_windows("scene-a", events, max_followups=3)
    self.assertEqual([e.timestamp_us for e in windows[0].events], [1_000_000, 2_000_000, 3_000_000, 4_000_000])
    self.assertEqual(windows[0].cluster_id, "scene-a")
```

- [ ] **Step 2: 시험 실패 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_extract_windows -v`

- [ ] **Step 3: 창 생성과 익명 ID 구현**

`window_id`는 `scene_id`, 사건 타임스탬프와 원문 해시로 결정적으로 만들고, 같은 장면의 창은 같은 `cluster_id`를 갖게 한다. 제한 JSONL에는 원문을 저장할 수 있지만 공개 집계에는 해시만 쓴다.

- [ ] **Step 4: 전체 94장면 추출 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python projects/sequential-coc-verification/experiments/sequential_coc/extract_windows.py --write-windows`

Expected: 90개 다중 사건 장면과 309개 인접 관계가 보존되고, 후보 수는 자동 선별값임을 메타데이터에 표시.

- [ ] **Step 5: 체크포인트 기록**

JSONL 행 수와 장면별 분포를 `RUN_LOG.md`에 기록한다. Git이 있으면 `git commit -m "feat: extract within-scene CoC windows"`.

### Task 4: 공통 계약 컴파일러

**Files:**
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/contract_compiler.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_contract_compiler.py`

**Interfaces:**
- Consumes: `EventWindow`
- Produces: `compile_text(text: str, event_id: str, scene_id: str, timestamp_us: int) -> list[ContractEvent]`
- Produces: `compile_window(window: EventWindow) -> list[ContractEvent]`

- [ ] **Step 1: 단계형 문장과 불명 해제 조건 시험 작성**

```python
def test_yield_then_accelerate_is_ordered_not_simultaneous(self):
    compiled = compile_text("Yield to the pedestrian and then accelerate to proceed.", "e0", "s", 0)
    self.assertEqual([x.action for x in compiled], [Action.YIELD_OR_DECELERATE, Action.ACCELERATE_OR_PROCEED])
    self.assertLess(compiled[0].phase_index, compiled[1].phase_index)

def test_missing_clearance_stays_unknown(self):
    compiled = compile_text("Yield to the pedestrian.", "e0", "s", 0)
    self.assertEqual(compiled[0].release_evidence, EvidenceValue.UNKNOWN)
```

- [ ] **Step 2: 시험 실패 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_contract_compiler -v`

- [ ] **Step 3: 보수적 규칙 컴파일러 구현**

명시된 `until/once/after/then`만 해제ㆍ다음 국면 단서로 사용한다. 여러 해석이 가능하거나 대상이 없으면 `parse_status="UNKNOWN"`으로 보류한다. 기존 느린 의도 우선 부분문자열 파서를 재사용하지 않는다.

- [ ] **Step 4: 고정 문장군 회귀시험**

정지, 양보, 감속, 가속, 단계형 `yield ... then accelerate`, `stop sign` 객체 언급, `stopped bus` 오탐 방지를 각각 검사한다.

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_contract_compiler -v`

- [ ] **Step 5: 체크포인트 기록**

파싱된 비율과 `UNKNOWN` 비율을 기록하되 정확도라고 부르지 않는다. Git이 있으면 `git commit -m "feat: compile CoC into explicit contracts"`.

### Task 5: 사건별 기준선과 상태형 Python 검사기

**Files:**
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/event_local_checker.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/stateful_checker.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_checkers.py`

**Interfaces:**
- Produces: `check_event_local(events: list[ContractEvent]) -> CheckResult`
- Produces: `check_stateful(events: list[ContractEvent]) -> CheckResult`
- `CheckResult`는 `verdict`, `contradiction_types`, `first_event_id`, `state_trace`, `unknown_reasons`를 포함한다.

- [ ] **Step 1: 상태 유지가 필요한 실패 시험 작성**

```python
def test_event_local_misses_hold_go_but_stateful_finds_it(self):
    # hold_event()/proceed_event()는 tests/fixtures.py에서 가져온다.
    events = [hold_event(release=EvidenceValue.FALSE), proceed_event()]
    self.assertEqual(check_event_local(events).verdict, "CONSISTENT")
    result = check_stateful(events)
    self.assertEqual(result.verdict, "CONTRADICTION")
    self.assertIn(ContradictionType.HOLD_GO_CONFLICT, result.contradiction_types)

def test_unknown_release_abstains(self):
    result = check_stateful([hold_event(release=EvidenceValue.UNKNOWN), proceed_event()])
    self.assertEqual(result.verdict, "UNKNOWN")
```

- [ ] **Step 2: 시험 실패 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_checkers -v`

- [ ] **Step 3: 네 주 모순의 최소 상태기계 구현**

`HOLD_GO_CONFLICT`, `PREMATURE_RELEASE`, `ORDER_VIOLATION`, `STALE_OBLIGATION`을 sticky 결과로 기록하고 첫 모순 뒤에도 사건열을 끝까지 소비한다.

- [ ] **Step 4: 정상ㆍ모순ㆍUNKNOWN 표 시험 통과**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_checkers -v`

Expected: 각 유형의 양성 1건, 대응 음성 1건, UNKNOWN 1건이 모두 PASS.

- [ ] **Step 5: 체크포인트 기록**

상태 전이표 해시를 기록한다. Git이 있으면 `git commit -m "feat: add event-local and stateful contract checkers"`.

### Task 6: UPPAAL 관찰자와 Python 동등성

**Files:**
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/uppaal_generator.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/run_uppaal.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_uppaal_generator.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_uppaal_equivalence.py`

**Interfaces:**
- Produces: `build_uppaal_model(events: list[ContractEvent]) -> tuple[ElementTree, list[str]]`
- Produces: `run_verifyta(model: Path, queries: Path, verifyta: Path) -> CheckResult`

- [ ] **Step 1: XML 구조와 sticky 위반 시험 작성**

```python
def test_model_continues_after_first_violation(self):
    # conflict_then_valid_release()는 tests/fixtures.py의 고정 사건열이다.
    tree, queries = build_uppaal_model(conflict_then_valid_release())
    xml = ET.tostring(tree.getroot(), encoding="unicode")
    self.assertIn("sticky_hold_go_conflict", xml)
    self.assertIn("idx++", xml)
    self.assertIn("A[] not sticky_hold_go_conflict", queries)
```

- [ ] **Step 2: 생성기 시험 실패 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_uppaal_generator -v`

- [ ] **Step 3: 공통 IR 기반 생성기 구현**

기존 `generate_multiscene_loop_model.py`의 XML 도우미는 재사용하되 기존 `slow_req/accel_req` 파서와 `Miss` 흡수 상태는 재사용하지 않는다. `known/value`와 네 sticky 모순 플래그를 명시한다.

- [ ] **Step 4: verifyta 동등성 시험**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_uppaal_equivalence -v`

Expected: 고정 정상ㆍ모순ㆍUNKNOWN 표에서 상태형 Python과 UPPAAL 판정 100% 일치. `verifyta`가 없으면 명시적으로 SKIP하며 가짜 PASS를 만들지 않음.

- [ ] **Step 5: 체크포인트 기록**

UPPAAL 버전, 실행 경로와 동등성 결과를 기록한다. Git이 있으면 `git commit -m "feat: generate sequential CoC UPPAAL observers"`.

### Task 7: 통제된 쌍대 모순 생성

**Files:**
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/mutation_generator.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_mutation_generator.py`
- Create: `experiments/results/restricted/sequential-coc-consistency-v1/mutations.jsonl`

**Interfaces:**
- Produces: `mutate_window(window: EventWindow, kind: ContradictionType) -> MutationPair`
- `MutationPair`는 `pair_id`, `cluster_id`, `original`, `mutated`, `changed_fields`, `oracle`을 포함한다.

- [ ] **Step 1: 단일 요인 변형 시험 작성**

```python
def test_mutation_changes_only_declared_contract_field(self):
    # clear_then_go_window()는 tests/fixtures.py의 일관된 원본 창이다.
    pair = mutate_window(clear_then_go_window(), ContradictionType.PREMATURE_RELEASE)
    self.assertEqual(pair.changed_fields, ["events[1].release_value"])
    self.assertEqual(pair.original.cluster_id, pair.mutated.cluster_id)
    self.assertNotEqual(pair.original.content_hash, pair.mutated.content_hash)
```

- [ ] **Step 2: 시험 실패 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_mutation_generator -v`

- [ ] **Step 3: 네 유형별 결정적 변형 구현**

각 유형은 하나의 계약 필드 또는 사건 순서만 바꾸고, `seed=20260806`과 변형 전후 diff를 저장한다. 원본이 이미 모순이거나 UNKNOWN이면 변형 모체에서 제외한다.

- [ ] **Step 4: 4유형×10쌍 생성 및 무결성 검사**

Run: `runtime/alpamayo/ar1_venv/bin/python projects/sequential-coc-verification/experiments/sequential_coc/mutation_generator.py --pairs-per-type 10 --seed 20260806`

Expected: 총 40쌍, 유형별 정확히 10쌍, 원본 40건은 상태형 검사에서 모순이 아니며 변형 40건은 해당 oracle 유형으로 검출됨. 목표를 채우지 못하면 수를 꾸며 쓰지 않고 `INSUFFICIENT_SOURCE_WINDOWS`로 중단.

- [ ] **Step 5: 체크포인트 기록**

쌍 수, 제외 사유와 JSONL 해시를 기록한다. Git이 있으면 `git commit -m "test: add controlled sequential CoC mutations"`.

### Task 8: 자연 연속열 블라인드 검토 도구

**Files:**
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/build_review_app.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_review_app.py`
- Create: `experiments/results/restricted/sequential-coc-consistency-v1/review/REVIEW_PROTOCOL.md`
- Create: `experiments/results/restricted/sequential-coc-consistency-v1/review/REVIEW_A.html`
- Create: `experiments/results/restricted/sequential-coc-consistency-v1/review/REVIEW_B.html`

**Interfaces:**
- Produces: standalone HTML with embedded available evidence and CSV export
- CSV fields: `review_id,obligation_started,satisfaction_state,release_state,next_action,sequence_verdict,contradiction_type,evidence_sufficiency,confidence,notes`

- [ ] **Step 1: 블라인드ㆍ내보내기 시험 작성**

```python
def test_reviewer_html_hides_checker_and_source_ids(self):
    page = build_review_page("A", [fixture_item()])
    self.assertNotIn("scene-", page)
    self.assertNotIn("UPPAAL", page)
    self.assertIn("CSV 저장", page)
    self.assertIn("UNKNOWN", page)
```

- [ ] **Step 2: 시험 실패 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_review_app -v`

- [ ] **Step 3: 기존 독립형 HTML 패턴으로 검토 앱 구현**

기존 `build_phase_aware_alignment_review.py`의 자동 저장과 CSV 코드를 재사용한다. 검토자는 원본/변형 여부, 검사기 판정, 실제 장면 ID를 보지 못한다. 미래 영상이 없으면 해제 상태에 `UNKNOWN`을 선택하도록 안내한다.

- [ ] **Step 4: 후보와 대응 대조군 구성**

정지ㆍ양보 후 진행 사전 후보 16장면과 가능한 대응 대조군을 넣되, 중복 장면 수와 실제 평가 창 수를 보고서에 별도로 기록한다. 두 검토 파일의 순서는 서로 다른 고정 seed로 섞는다.

Run: `runtime/alpamayo/ar1_venv/bin/python projects/sequential-coc-verification/experiments/sequential_coc/build_review_app.py`

- [ ] **Step 5: 체크포인트 기록**

HTML에서 제한 원문을 제외한 adjudication 매핑이 노출되지 않는지 검사하고 해시를 기록한다. Git이 있으면 `git commit -m "feat: build blinded sequential CoC review"`.

### Task 9: 궤적 계약 연결

**Files:**
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/trajectory_contracts.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_trajectory_contracts.py`
- Create: `experiments/results/restricted/sequential-coc-consistency-v1/trajectory-results.jsonl`

**Interfaces:**
- Produces: `evaluate_trajectory_contract(events, ego_trace, thresholds) -> TrajectoryResult`
- `TrajectoryResult.verdict`는 `COMPLIANT`, `VIOLATION`, `UNKNOWN` 중 하나이다.

- [ ] **Step 1: 삼값 궤적 판정 시험 작성**

```python
def test_hold_violation_requires_known_unreleased_state(self):
    # T와 사건/궤적 생성기는 tests/fixtures.py의 고정값이다.
    self.assertEqual(evaluate_trajectory_contract(known_hold(), accelerating_trace(), T).verdict, "VIOLATION")
    self.assertEqual(evaluate_trajectory_contract(unknown_release(), accelerating_trace(), T).verdict, "UNKNOWN")
```

- [ ] **Step 2: 시험 실패 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_trajectory_contracts -v`

- [ ] **Step 3: 종방향 술어 구현**

기존 `analyze_phase_aware_alignment.py`의 signed speed 계산을 작은 순수 함수로 재사용한다. 정지ㆍ양보 유지 속도, 가속 시작과 필수 감속 단계만 구현하며 객체 간격과 차선 변경은 근거 부재 시 UNKNOWN이다.

- [ ] **Step 4: 사전 선언 임계값과 민감도 실행**

기본 정지 임계값과 감속량은 기존 논문 설정을 그대로 기록하되 규범 값으로 부르지 않는다. 최소 3개 임계값에서 판정 변화를 저장한다.

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_trajectory_contracts -v`

- [ ] **Step 5: 체크포인트 기록**

COMPLIANT/VIOLATION/UNKNOWN 수와 임계값 민감도를 기록한다. Git이 있으면 `git commit -m "feat: link sequential contracts to ego trajectories"`.

### Task 10: 평가와 성공 기준 판정

**Files:**
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/evaluate.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_evaluate.py`
- Create: `experiments/results/restricted/sequential-coc-consistency-v1/metrics.json`

**Interfaces:**
- Produces: `wilson_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]`
- Produces: `cohens_kappa(labels_a, labels_b) -> float | None`
- Produces: `evaluate_all(...) -> dict`

- [ ] **Step 1: 알려진 표의 지표 시험 작성**

```python
def test_metrics_keep_pairs_and_unknown_separate(self):
    # fixture_results()는 2개 쌍과 UNKNOWN 자연 사례 1개를 반환한다.
    report = evaluate_all(fixture_results())
    self.assertEqual(report["mutation"]["pair_count"], 2)
    self.assertEqual(report["natural"]["unknown_count"], 1)
    self.assertNotIn("unknown", report["natural"]["confusion_matrix"])
```

- [ ] **Step 2: 시험 실패 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_evaluate -v`

- [ ] **Step 3: 군집ㆍ쌍 단위 집계 구현**

자연 자료, 변형 자료, 궤적 자료를 별도 최상위 키에 둔다. 정밀도ㆍ재현율ㆍF1, Wilson 구간, Cohen kappa, 사건별 대비 추가 검출, Python-UPPAAL 일치와 반례 위치 정확도를 계산한다.

- [ ] **Step 4: 성공ㆍ축소 기준 자동 판정**

`claim_gate`에 `MUTATION_EVALUABLE`, `NATURAL_DESCRIPTIVE_ONLY`, `NATURAL_QUANTITATIVE_READY`, `UPPAAL_EQUIVALENT`, `TRAJECTORY_EXPLORATORY`를 기록한다. 20개 평가 가능한 자연 창 또는 40개 변형 쌍을 채우지 못하면 해당 주장을 자동으로 낮춘다.

- [ ] **Step 5: 전체 평가 시험과 체크포인트**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/sequential-coc-verification/experiments/sequential_coc/tests -v`

Git이 있으면 `git commit -m "feat: evaluate sequential CoC consistency"`; 없으면 전체 시험 결과를 `RUN_LOG.md`에 기록한다.

### Task 11: 장면 경계ㆍ출처 보조 실험

**Files:**
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/cross_scene_boundary.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_cross_scene_boundary.py`
- Create: `experiments/results/restricted/sequential-coc-consistency-v1/cross-scene-secondary.json`

**Interfaces:**
- Consumes: `experiments/results/baseline/multiscene-chain/uppaal-loop-batch-all-strict-1s.json`
- Produces: `evaluate_boundary_policy(chain: dict, carryover: bool, provenance_supported: bool) -> CheckResult`

- [ ] **Step 1: 출처 없는 이월 시험 작성**

```python
def test_unproven_carryover_is_separate_from_semantic_conflict(self):
    result = evaluate_boundary_policy(fixture_chain(), carryover=True, provenance_supported=False)
    self.assertEqual(result.verdict, "CONTRADICTION")
    self.assertEqual(result.contradiction_types, [ContradictionType.UNSUPPORTED_CARRYOVER])
```

- [ ] **Step 2: 시험 실패 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_cross_scene_boundary -v`

- [ ] **Step 3: 폐기ㆍ이월 정책 비교 구현**

기존 13체인의 장면 경계에서 활성 의무를 폐기하는 정책과 이월하는 정책을 비교한다. 공식 출처가 확인되지 않은 이월만 `UNSUPPORTED_CARRYOVER`로 기록하고 자연어 의미 모순 수에 더하지 않는다.

- [ ] **Step 4: 13체인 보조 실행**

Run: `runtime/alpamayo/ar1_venv/bin/python projects/sequential-coc-verification/experiments/sequential_coc/cross_scene_boundary.py`

Expected: 입력 13체인, 29개 고유 장면, 16개 경계를 재확인하고 결과에 `evidence_level="PROVENANCE_POLICY_EXAMPLE"`을 기록한다.

- [ ] **Step 5: 체크포인트 기록**

이 결과가 검출 성능이 아니라 정책 사례임을 `RUN_LOG.md`에 적는다. Git이 있으면 `git commit -m "exp: add cross-scene provenance policy check"`.

### Task 12: 재현 실행기와 결과 manifest

**Files:**
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/run_experiment.py`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/tests/test_run_experiment.py`
- Create: `experiments/results/restricted/sequential-coc-consistency-v1/MANIFEST.sha256`
- Create: `projects/sequential-coc-verification/experiments/sequential_coc/README.md`

**Interfaces:**
- CLI: `run_experiment.py --stage inventory|extract|compile|mutate|check|trajectory|evaluate|all`
- `--stage all`은 사람 검토 CSV가 없으면 `WAITING_FOR_REVIEW`로 멈추고 성공으로 위장하지 않는다.

- [ ] **Step 1: 재시작 가능성 시험 작성**

```python
def test_all_stops_cleanly_when_review_is_missing(self):
    result = run_all(fixture_config(review_csvs=[]))
    self.assertEqual(result.status, "WAITING_FOR_REVIEW")
    self.assertFalse(result.paper_update_allowed)
```

- [ ] **Step 2: 시험 실패 확인**

Run: `runtime/alpamayo/ar1_venv/bin/python -m unittest experiments.sequential_coc.tests.test_run_experiment -v`

- [ ] **Step 3: 단계별 실행과 원자적 결과 쓰기 구현**

각 단계는 임시 파일에 쓴 뒤 성공 시 결과 파일로 바꾸고, 입력ㆍ코드ㆍ출력의 SHA-256을 manifest에 기록한다. 원문 제한 자료에는 파일 권한 `0600`, 디렉터리 `0700`을 적용한다.

- [ ] **Step 4: 검토 전 자동 단계 실행**

Run: `runtime/alpamayo/ar1_venv/bin/python projects/sequential-coc-verification/experiments/sequential_coc/run_experiment.py --stage all`

Expected: 자동 단계가 통과하고 검토 CSV가 없으면 `WAITING_FOR_REVIEW`; 논문 파일은 변경되지 않음.

- [ ] **Step 5: 체크포인트 기록**

README에 정확한 실행 순서와 기대 중단 상태를 쓴다. Git이 있으면 `git commit -m "chore: add reproducible sequential CoC runner"`.

### Task 13: 사람 검토 완료와 최종 실험 실행

**Files:**
- Consume: `review/reviewer_A.csv`, `review/reviewer_B.csv`
- Create: `review/adjudication.csv`
- Modify: `metrics.json`, `RUN_LOG.md`, `MANIFEST.sha256`

**Interfaces:**
- Consumes Task 8 CSV 스키마
- Produces 합의 정답과 최종 `claim_gate`

- [ ] **Step 1: 두 CSV의 완전성과 블라인드 ID 검사**

Run: `runtime/alpamayo/ar1_venv/bin/python projects/sequential-coc-verification/experiments/sequential_coc/run_experiment.py --stage evaluate`

Expected: 누락 행, 중복 ID, 허용되지 않은 레이블이 있으면 구체적 오류와 함께 중단.

- [ ] **Step 2: 불일치 사례만 합의 판정**

원판정 A/B를 덮어쓰지 않고 `adjudication.csv`에 최종 판정자, 사유와 시각을 추가한다.

- [ ] **Step 3: 전체 실험 재실행**

Run: `runtime/alpamayo/ar1_venv/bin/python projects/sequential-coc-verification/experiments/sequential_coc/run_experiment.py --stage all`

Expected: 모든 자동 시험, 검사기, UPPAAL, 궤적 연결과 평가가 완료되고 `claim_gate`가 생성됨.

- [ ] **Step 4: 숫자 교차검증**

`자연 창 수 = 합의 판정 수`, `변형 쌍 = 원본 수 = 변형 수`, 유형별 합 = 전체, Python-UPPAAL 불일치 목록 = 보고된 불일치 수를 확인한다.

- [ ] **Step 5: 최종 체크포인트 기록**

전체 명령 출력, 도구 버전, manifest와 제한 사항을 고정한다. Git이 있으면 `git commit -m "exp: complete sequential CoC consistency evaluation"`.

### Task 14: KIEE 논문 보완

**Files:**
- Modify only after Task 13: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/main.tex`
- Modify: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/01-introduction.tex`
- Modify: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/02-related-work.tex`
- Modify: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/04-problem.tex`
- Modify: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/05-method.tex`
- Modify: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/06-experiments.tex`
- Modify: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/07-results.tex`
- Modify: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/08-discussion.tex`
- Modify: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/09-threats.tex`
- Modify: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/10-conclusion.tex`
- Modify/Add: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/figures/`

**Interfaces:**
- Consumes: `metrics.json`, 검토 합의 CSV, 대표 UPPAAL 반례
- Produces: 결과와 주장 범위가 일치하는 KIEE PDF

- [ ] **Step 1: 편집 무결성 시험을 먼저 갱신**

제목, RQ1--RQ5, `134=125+4+5`의 보조 결과 위치, `282/1128`의 회귀시험 한계, 자연/변형 분리를 검사하는 실패 시험을 추가한다.

- [ ] **Step 2: 기존 KIEE 시험이 새 주장 전 실패하는지 확인**

Run: `cd projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit && python3 -m unittest discover -s tests -v`

- [ ] **Step 3: `claim_gate`에 맞춰 원고 수정**

자연 모순이 확인되지 않았으면 존재를 암시하지 않는다. 주입 검출률을 자연 발생률로 쓰지 않는다. 궤적 `VIOLATION`을 실제 위험으로 부르지 않는다. `134=125+4+5`는 단일 사건 민감도 보조 결과로, `282/1128`은 구현 회귀시험으로 이동한다.

- [ ] **Step 4: 표와 그림 재구성**

최소 그림은 계약 상태기계, 정상-변형 쌍, 대표 UPPAAL 반례 경로이다. 표는 자연 자료, 통제 변형, 기준선 비교와 궤적 교차표를 분리한다.

- [ ] **Step 5: 빌드와 주장 감사**

Run: `cd projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit && make clean && make`

Run: `cd projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit && python3 -m unittest discover -s tests -v`

Expected: PDF 빌드 성공, 모든 편집 시험 PASS, LaTeX 오류와 정의되지 않은 참조 없음.

- [ ] **Step 6: 최종 체크포인트**

PDF SHA-256과 페이지 수를 `RUN_LOG.md`에 기록한다. Git이 있으면 `git commit -m "paper: add sequential CoC consistency evaluation"`.

## Final Verification Gate

- [ ] `runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/sequential-coc-verification/experiments/sequential_coc/tests -v` 전체 PASS
- [ ] `verifyta` 실행 또는 명시적 `NOT_RUN` 사유 기록
- [ ] 자연 자료와 변형 자료 수치가 모든 표에서 분리됨
- [ ] 사람이 확인하지 않은 사례를 실제 모순으로 표현하지 않음
- [ ] `UNKNOWN`을 음성 사례로 계산하지 않음
- [ ] Python-UPPAAL 불일치가 남아 있지 않거나 모두 설명됨
- [ ] `MANIFEST.sha256`가 모든 최종 산출물과 일치
- [ ] KIEE 원고 시험 및 PDF 빌드 성공
- [ ] 기존 데이터와 기존 결과 파일의 해시가 보존됨
