# GuardSynth-CoC P0b 종료 판정 v1

- 판정일: 2026-08-09
- software 실행 상태: `EXECUTED`
- 연구 단계 판단: `DATA_GAP_PIVOT`
- 현재 범위의 남은 software 작업: 없음
- 실제 24-scene 계약 실행: 미수행

## 1. 종료한 범위

P0b에서 다음 공개 경로를 구현하고 회귀 테스트로 고정했다.

1. EBLC v0.2 program, typed derivation, lifecycle, composition 및 indexed collection
2. 고수준 EBLC → Core → SMT-LIB/Z3 변환과 bounded agreement
3. RuleTemplate, PredicateSpec, structured ContextGraph 및 sourced vehicle profile을
   EBLC로 만드는 source-aware GuardSynth generator
4. source URI/version/hash/scope를 필수로 하는 exact vehicle assurance registry
5. association, geometry, 좌표 변환 및 assurance가 완전할 때만 요청을 만드는
   fail-closed source authoring interface
6. 실제 입력 부재를 synthetic scene으로 채우지 않는 24-slot readiness pipeline

구현은 [`src/guard_synth`](../../src/guard_synth/)에, 실행 인터페이스는
[`cli/pipelines/guardsynth`](../../cli/pipelines/guardsynth/)에 있다.

## 2. 24-slot 실행 결과

[공개 집계 결과](../../artifacts/results/public/guardsynth-real-scene-readiness-001/terminal-readiness-2026-08-09-v3/REPORT_KO.md)는
현재 로컬 restricted derived input의 식별자와 CoC 본문을 포함하지 않는다.

| 항목 | 결과 |
|---|---:|
| 목표 slot | 24 |
| 실제/파생 VRU 후보 event | 5 |
| partial ContextGraph | 4 |
| trajectory horizon 밖 event | 1 |
| 입력 자체가 없는 slot | 19 |
| source-complete scene | 0 |
| 실행 가능한 실제 EBLC request | 0 |
| synthetic fill | 0 |

부분 ContextGraph 네 개는 모두 target-zone association, 검증된 rig→ego-path
transform 및 source-bearing vehicle assurance가 완전하지 않았다. 따라서 이를
실행 가능한 계약으로 승격하지 않았다.

## 3. 테스트 결과

- source authoring/registry: 8/8
- source-boundary adversarial: 14/14
- 전체 maintained EBLC/GuardSynth: 172/172
- 프로젝트 구조 및 문서 링크: 9/9

완전한 synthetic sourced scene 두 개와 test-only assurance report를 사용한 양성
테스트는 GuardSynth→EBLC indexed collection 생성을 통과했다. transform 또는
assurance가 빠진 음성 테스트는 생성 전에 중단됐다. 이 양성 테스트의 수치는 실제
차량 보장값이 아니다.

적대적 입력, 24-contract Z3 종단 실행, 발견 결함과 표적 line coverage는
[철저 테스트 보고서](GUARDSYNTH_SOURCE_BOUNDARY_THOROUGH_TEST_V1.md)에 기록한다.

## 4. 판정의 의미

`DATA_GAP_PIVOT`은 EBLC 구현 실패가 아니다. 현재 software path는 필요한 입력이
완전하면 생성하고, 불완전하면 정확한 reason code로 abstain한다. 반면 실제 24장면의
계약 타당성이나 안전성은 아직 평가하지 않았다.

P0b를 재개하는 유일한 조건은 다음 네 외부 입력이 실제 24개 장면에 갖춰지는 것이다.

1. unambiguous target–conflict-zone association
2. scene별 timestamp/geometry/ego state
3. 검증된 rig→canonical ego-path transform
4. 차량 binding과 일치하는 validation/assurance source 및 수치

이 입력이 들어오기 전에는 EBLC 문법이나 compiler 기능을 반복 확장하지 않는다.
입력이 확보되면 같은 pipeline을 재실행해 `P0B_GO` 여부를 판단한다. 이 보고서는
법규 타당성, 실제 차량 성능 또는 차량 안전성을 입증하지 않는다.

## 5. 2026-08-10 후속 단계 주석

이 문서의 “현재 범위 남은 software 작업 없음”은 P0b source-boundary 종료 범위를 뜻한다.
후속 P1 입력 authoring 작업으로 [label-light grounding 계층](../designs/guard-synth-coc/GUARDSYNTH_LABEL_LIGHT_GROUNDING_V01.md)을
추가했다. 기존 perception/map/trajectory 후보를 자동 확인, 최소 검토, 지원 불가/충돌로
나누어 대량 완전 라벨 의존을 줄인다. 이는 P0b 종료 판정을 뒤집는 EBLC 기능 확장이 아니라
다음 데이터 연결 단계다. 전체 단계 위치는 [프로젝트 현황](GUARDSYNTH_PROJECT_STAGE_STATUS_V1.md)에 둔다.
현재 활성 작업과 이후 순서는 [프로젝트 실행 추적표](../plans/guard-synth-coc/PROJECT_EXECUTION_TRACKER.md)를
단일 실행 기준으로 사용한다.
