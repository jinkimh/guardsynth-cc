# GuardSynth source boundary 철저 테스트 보고서 v1

- 실행일: 2026-08-09
- 대상: vehicle assurance registry, source authoring, 24-slot readiness,
  GuardSynth→EBLC→Core→Z3 종단 경로
- 최종 상태: `PASS_WITH_RESIDUAL_DATA_GAPS`
- 실제 장면 판단: `DATA_GAP_PIVOT`

## 1. 테스트 전략

기존 정상 경로를 반복하는 대신 다음 trust boundary를 적대적으로 검사했다.

1. 차량 profile 수치, source URI/hash/scope 및 세 종류 uniqueness
2. hazard, association, geometry, transform, assurance의 개별 누락
3. `CLAIMED`, 미래 timestamp, 잘못된 frame 및 중복 contract
4. 이전 synthetic context/profile provenance의 잔류 여부와 결정성
5. adapter event 수와 candidate/gap 목록의 회계 일치
6. schema-valid flag 위조와 raw identifier 비노출
7. readiness gate와 실제 24-scene 실행 완료 주장의 분리
8. 서로 다른 24개 synthetic contract의 EBLC bundle→Core→project-local Z3 실행

테스트 구현은
[`test_source_authoring_adversarial.py`](../../tests/unit/test_source_authoring_adversarial.py)에
고정했다. 실제/파생 데이터는 식별자나 CoC 본문을 출력하지 않았다.

## 2. RED 단계에서 발견한 결함

최초 14-test 설계 전 단계의 12개 test method에서 15 failure와 1 error가 발생했다.
이를 기대값 수정 없이 다음 여섯 결함군으로 정리하고 구현을 보강했다.

| ID | 결함 | 영향 | 수정 |
|---|---|---|---|
| T-01 | whitespace source field와 비-URI 문자열 수용 | provenance가 형식만 갖춘 것처럼 보일 수 있음 | nonblank 및 `urn/file/https` scheme 강제 |
| T-02 | assurance `scope`를 scene binding에 사용하지 않음 | test-only profile의 범위 밖 오결합 가능 | scene–profile scope exact match 강제 |
| T-03 | adapter declared event count와 목록 수 불일치 미검출 | 24-slot 누락 수가 잘못 계산될 수 있음 | exact accounting invariant 추가 |
| T-04 | `context_schema_valid`와 status flag를 과신 | 얕은 record가 source-complete로 오판될 수 있음 | ContextGraph schema 재검증 및 독립 필드 검사 |
| T-05 | authoring이 generator의 REVIEW/UNSUPPORTED 요청을 반환 | API boundary가 executable input처럼 오해될 수 있음 | 반환 전 canonical generator verdict 재검증 |
| T-06 | 24개 ready 입력과 실제 실행 완료를 같은 Boolean으로 표현 | readiness를 실제 검증으로 오독할 수 있음 | readiness gate와 execution-completed 필드 분리 |

## 3. 최종 결과

[최신 terminal run](../../../../artifacts/results/public/guardsynth-real-scene-readiness-001/terminal-readiness-2026-08-09-v3/RESULT.json)의 결과는 다음과 같다.

| 테스트 | 결과 |
|---|---:|
| 기존 시작 기준선 | 158/158 |
| source authoring 기본 | 8/8 |
| source-boundary adversarial | 14/14 |
| 전체 maintained EBLC/GuardSynth | 172/172 |
| P0a regression | 7/7 |
| 구조 및 문서 링크 | 9/9 |

24-contract 종단 테스트는 각 actor–zone binding을 별도 contract로 확장하고 실제
project-local Z3 5.0.0에서 `SAT`를 확인했다. 24번째 contract의 exact
`stop_position` witness는 `457/2`였다. 이는 test-only sourced value를 사용한
compiler/scaling 증거이며 실제 차량 제동 성능이 아니다.

표준 라이브러리 `trace`로 외부 dependency를 제외하고 표적 line coverage도 측정했다.

| 모듈 | line coverage |
|---|---:|
| `guard_synth.assurance_registry` | 98% |
| `guard_synth.source_authoring` | 92% |
| `guard_synth.source_aware_generator` | 86% |
| `guard_synth_eblc.bundle_elaborator` | 98% |
| `guard_synth_eblc.indexed_collection` | 81% |
| `guard_synth_eblc.smt_compiler` | 67% |

이는 표적 suite의 line coverage이며 branch coverage나 전체 프로젝트 coverage가 아니다.
`coverage.py`는 로컬에 설치되어 있지 않아 새 dependency나 network download 없이
Python 표준 `trace`를 사용했다.

## 4. 실제 입력 재평가

강화된 checker로 기존 restricted-derived 결과를 다시 평가해도 다음 판단은 변하지 않았다.

- 후보 event: 5/24
- partial ContextGraph: 4
- source-complete scene: 0/24
- readiness gate: false
- 실제 24-scene 실행 완료: false
- synthetic fill: 0
- 최종 판단: `DATA_GAP_PIVOT`

## 5. 잔여 위험과 주장 경계

이번 감사로 source boundary의 알려진 여섯 software 결함은 고정 테스트 범위에서
재현되지 않는다. 그러나 다음은 여전히 입증하지 못했다.

- 실제 차량 validation report에 기반한 assurance profile
- 24개의 실제 source-complete 장면
- association annotation의 전문가 정답성
- 실제 법규 source의 적합성
- 독립 safety oracle 또는 closed-loop 차량 안전성
- coverage 밖 경로와 미지의 결함 부재

따라서 software 결과는 통과했지만 실제 연구 판단은 계속 `DATA_GAP_PIVOT`이다.
