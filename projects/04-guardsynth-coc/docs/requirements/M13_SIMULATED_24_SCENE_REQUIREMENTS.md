# M13 전체 24-scene 재검증 요구사항 (2차)

- 상태: `QUEUED` (DEFERRED_PHASE2)
- work package: `GS-P1-SIM24-REQUAL-001`
- 권위: [1차/2차 분리 결정](../decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md)

전체 세 slice 24장면 확보는 1차 논문 선행조건에서 해제한다. 사용하는 subset의 source·binder·
compiler/CNL smoke는 M14/M17에서 수행한다. 4/24 terminal 이력은 보존한다. 아래 전체24 요구는
M20 이후 2차 scope/resource를 재승인한 뒤 적용하며 이번 변경으로 empirical gate를 통과한 것이 아니다.

## 이전 상세 요구사항 (2차/구현 이력)

<details>
<summary>기존 완료 근거와 확장 protocol 보기</summary>

아래 현재/필수/선행조건 표현은 당시 범위다. 1차 적용은 위 v2.3 계약이 대체한다.

### 이전 M13 실제 장면 근거 × 가상 차량 24장면 요구사항

- work package: `GS-P1-SIM24-001`
- 상태: `PARTIAL` (재적격화); 역사적 `COMPLETE / M13_TERMINAL_DATA_SHORTFALL_FRONTEND_CAN_PROCEED` 보존
- 종료 결과: 실제/파생 4/24장면·17계약 실행, 부족 20장면과 slice/strata 공백을
  synthetic fill 없이 terminal decision으로 기록
- 결과: `artifacts/results/restricted/guardsynth-sim24-batch-001/alpamayo-terminal-batch-2026-08-12-v1/`
- 결정 근거: [실제 차량 검증 후속 단계 이관](../decisions/ACTUAL_VEHICLE_VALIDATION_DEFERRAL_DECISION_V01.md)
- 입력 등급: 실제/파생 장면은 source-linked, 차량 assurance는 simulation-only
- 후속 보완: `M13-R01 / GS-P1-SIM24-REQUAL-001 QUEUED`; terminal 완료는 보존하며
  current-scope 세 slice 24-scene 재검증이 formal annotation의 선행 gate

#### 이전 목적

24개 실제/파생 장면 근거를 하나 이상의 명시적 가상 차량 assurance profile에 투영하여
`GuardSynth → EBLC → Core → Z3` 배치 실행 가능성, abstention, 변환 일치와 실패 유형을
평가한다.

#### 이전 장면별 필수 실제/파생 근거

1. timestamp
2. ego pose와 speed
3. 관련 actor의 시간 연속 track
4. target–zone/lane association
5. conflict 또는 stop geometry
6. 검증된 coordinate transform
7. 적용 가능한 규칙 source와 조건부 applicability
8. recorded-rig binding

위 8개 중 하나라도 없으면 해당 장면은 실행하지 않고 정확한 reason code를 기록한다.

#### 이전 시뮬레이션 전용 입력

- simulation vehicle binding
- response time
- service deceleration
- position uncertainty
- 모델 범위·제외 조건·source hash

시뮬레이션 binding은 recorded-rig binding과 반드시 달라야 한다.

#### 이전 24장면 구성

- 세 deep slice별 8장면
- 각 slice에서 nominal/hazard, clear/occluded, release/reactivation strata 보존
- 동일 장면 또는 동일 이벤트를 이름만 바꾸어 중복 계산하지 않음
- 부족한 slice는 미달 수와 missing-field manifest를 그대로 보고

#### 이전 실행 산출물

- `SCENE_CANDIDATE_INVENTORY.json`
- `SCENE_SOURCE_CLOSURE.json`
- `BATCH_RESULT.json`
- `TRANSLATION_RESULTS.json`
- `ABSTENTION_RESULTS.json`
- `RUN_MANIFEST.json`
- `REPORT_KO.md`

새 제한 원문·식별자는 `artifacts/projects/guardsynth-coc/restricted/` 아래에서만 처리한다.
위 `artifacts/results/`는 기존 immutable run 참조다. 공개 결과에는 집계와
비식별 reason code만 둔다.

#### 이전 성공 gate

- 실제/파생 장면 근거 8/8: 24/24 또는 미달 terminal decision
- synthetic scene-field fill: 0건
- recorded/simulation binding 분리: 실행 장면 100%
- schema와 source closure validation: 실행 장면 100%
- canonical/Core/Z3 판정 agreement: locked 실행 trace 100%
- Z3 SMT-LIB 직접 replay: 생성 파일 100%
- missing input의 `UNSUPPORTED` 또는 `REVIEW_REQUIRED` 보존: 100%
- source 없는 규범·수치값: 0건
- 정상·위험·UNKNOWN·CONFLICT·release/reactivation 결과를 분리 보고

#### 이전 비목표

- 실제 차량 assurance 또는 안전성 검증
- 법률 적용의 최종 판단
- 센서 인식 정확도 검증
- 실제 충돌 감소 효과 주장

#### 이전 첫 작업

최초 작업 이력이며 현재 재적격화는 M12-R01 source 감사 후 실행한다. 부족 slot을 기록하는
것과 새 empirical gate 통과를 구분하며, 부족 상태를 다시 terminal로 면제하지 않는다.
24개는 적절한 source/development 표본을 재사용할 수 있으나 main locked test와 분리한다.
source-eligible이지만 생성/compile 실패한 장면도 분모에 남긴다.

로컬 실제/파생 자료를 read-only로 감사하여 24개 slot 후보별 8개 근거 상태와 재사용 가능한
artifact를 `SCENE_CANDIDATE_INVENTORY.json`으로 작성한다. 아직 준비되지 않은 후보를 가상
장면으로 채우지 않는다.

</details>
