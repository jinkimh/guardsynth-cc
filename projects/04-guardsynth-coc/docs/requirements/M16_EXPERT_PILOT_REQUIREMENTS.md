# M16 1차 독립 검토 및 2차 formal60 요구사항

- work package: `GS-P4-PILOT-001`, M16-R01/R02
- 상태: `PARTIAL`
- 새 1차 cohort 적격성: `NOT_EVALUATED`; 종전 strict formal60: 1/60
- 권위: [1차/2차 분리 결정](../decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md)

## 1차 검토 계약

- M12에서 선언한 task/clause에 필요한 source와 gold만 수집한다. 고정60/18 joint quota 및
  모든 장면8-field 요구를 일괄 적용하지 않지만 정량 주장에는 실제 metric source가 필수다.
- 영상60/geometry98의 관찰·보정·노출 이력을 재사용한다. 기계 제안 확인과 독립 gold를 분리하고
  pixel polygon 제출을 metric geometry/source closure로 자동 승격하지 않는다.
- 두 reviewer가 중립 source packet에서 제안 guard·선행 답을 보지 않고 독립 gold를 작성하고,
  별도 adjudicator가 답변 lock 후 불일치를 판정한다. exposure가 있으면 해당 항목을 재배정한다.
- CNL의 조건·대상·수치·부정/의무·해제 의미를 source EBLC와 독립 비교한다.
- 사용 gold field의 agreement/CI/결측을 보고한다. applicability/guard type을 primary gold로
  사용하면 기존 α≥0.67 기준과 정의불가 처리 원칙을 유지한다.
- calibration/dev/test·clip/episode 파생 표본 누출을 막는다. N은 learning endpoint의 dev
  분산과 nominal 성공 정밀도로 test 전 결정하며 60 해제를 소수 표본 충분성으로 해석하지 않는다.
- 과도한 기계 보조 생산성 비교는 E6/2차다. 시간 기록은 검토 비용 관리용으로만 유지한다.

기존 UI/assignment/validator는 아래 strict60/혼합 mode 구현이므로 새 protocol에 맞춘
tests·export 계약 검증 전 formal 수집을 시작하지 않는다. 현재 source 화면은 gold가 아니다.

## 이전 상세 요구사항 (2차/구현 이력)

<details>
<summary>기존 완료 근거와 확장 protocol 보기</summary>

아래 현재/필수/선행조건 표현은 당시 범위다. 1차 적용은 위 v2.3 계약이 대체한다.

### 이전 M16 60-scene 전문가 formal pilot 요구사항

- work package: `GS-P4-PILOT-001`
- 상태: `PARTIAL` (마지막 집계 1/60 eligible; formal annotation 미실행)
- 준비 경계: 기존 SOFTWARE_PREFLIGHT_COMPLETE는 v0.1 interface 검증 이력이며 아래
  M16-R01/R02 독립 검토·metric 보완 구현은 미완료
- 선행조건: M12–M15 재적격화, M16-R01/R02, source-complete scene eligibility
- 현재 acquisition 하위 요구사항: [M16_SOURCE_COMPLETE_SCENE_ACQUISITION_REQUIREMENTS_V01.md](M16_SOURCE_COMPLETE_SCENE_ACQUISITION_REQUIREMENTS_V01.md)

#### 이전 사전 고정 설계

- 총 60장면, 세 slice 각 20장면
- 여섯 outcome strata 각 10장면: `NOMINAL`, `HAZARD_TRUE_ACTIVE`, `UNKNOWN`,
  `CONFLICT`, `RELEASE`, `REACTIVATION`
- source-complete 장면만 포함하며 synthetic field fill 금지
- 장면/방법 순서를 결정론적 seed로 무작위화하고 reviewer 간 균형 배정
- 최소 2인 독립 검토 후 별도 adjudicator가 불일치를 판정
- calibration 항목은 평가 항목과 분리하고 gold에 포함하지 않음
- calibration은 본 60개와 별도이며, 24-scene dry-run/pilot/dev는 main locked test에서 제외
- 18개 slice×outcome joint cell은 3~4개, slice 20개/outcome 10개 quota 유지

#### 이전 검토 목적 분리: M16-R01

1. source curation: 기계 overlay·선행 영상 관찰과 polygon 확인을 허용한다. 제출·확인 완료와
   metric geometry/lifecycle witness 검증·8/8 eligibility는 별도 집계한다.
2. formal gold: 동일 중립 source packet을 두 reviewer가 독립 작성한다. 제안 guard·선행 답변·
   방법 결과는 숨기고, 같은 항목의 기계 제안을 본 reviewer는 미노출 reviewer로 재배정하거나
   해당 결과를 assisted/development로 분리한다. adjudicator는 답변 lock 후 불일치를 판정한다.
3. assistance 효용: scratch/free-form/proposed 비교와 두 UI mode 비교는 E6용 별도 배정이다.
   서로 다른 mode의 두 답변으로 계산한 α를 독립 동일조건 gold 신뢰도로 보고하지 않는다.

현재 source-review 화면은 1번이며 2번의 완료 근거가 아니다. 기존 제출은 재사용하고 새
formal 검토를 요청하기 전에 역할·노출·source packet·export round-trip을 검증한다. pixel
polygon 확인만으로 depth·metric frame·temporal track·규범 근거를 닫지 않는다. reviewer에게
자신의 역할과 제공된 자료로 알 수 없는 값을 추정하게 하지 않는다.

#### 이전 annotation 단위

- applicability와 abstention
- guard type, target/zone, operator와 range/unit/frame
- source sufficiency와 source refs
- activation, maintain, release, reactivation, expiry, fallback
- reviewer confidence, correction action, 시작/종료 시간

#### 이전 start gate

1. eligibility 60/60, slice quota와 outcome quota 충족
2. raw/restricted 입력과 공개 결과 경계 확인
3. reviewer training/calibration 완료
4. annotation schema/UI export 검증
5. baseline/model version과 split manifest 동결
6. M13-R01/M14-R01/M15-R01 및 M16-R01/R02 구현·test 완료
7. 독립 gold 배정과 source curation/assistance 노출 분리, 별도 calibration 확인

하나라도 미충족이면 annotation을 시작하지 않고 정확한 shortfall을 출력한다.

#### 이전 성공 gate

- adjudication 전 applicability와 guard type Krippendorff α 각각 ≥0.67
- CI·결측·상수 label 등 α 정의 불가 처리 명시; 정의 불가는 통과가 아님
- field agreement, correction rate와 장면당 시간 보고
- 최대 두 번의 guideline revision만 허용하고 이력 보존
- annotation cluster/variance 기반 main N과 비용 산정. E2/E4/E4-L/E6은 각각 실제 endpoint
  dev/pilot 분산을 사용하고 없으면 POWER_INPUT_PENDING으로 해당 lock 전 확보
- 균형 60장면의 비율을 자연분포 prevalence로 보고하지 않음; sampling frame·선정/제외 수 보고

#### 이전 보완 구현 수락 기준: M16-R01/R02

- 노출된 reviewer를 독립 gold로 집계하지 않는 배정·import negative tests
- 중립 source packet/hash와 독립 답변 lock, 별도 adjudication·노출 manifest
- polygon 종류별 autosave/zoom 복귀/export/import 보존 및 기존 제출 중복 반영 방지
- pixel correction 완료와 metric source 검증, source eligibility와 execution readiness 분리 tests
- 두 field α·불일치/상수/결측·calibration 제외 및 balanced sampling 경고 tests
- outcome UNKNOWN/CONFLICT는 source 부족을 합성해 채우지 않고 근거 있는 상태만 인정

기존 구현은 두 UI mode를 섞어 배정하고 applicability α만 산출하므로 이 수락 기준을 아직
통과한 것으로 보지 않는다. 상세 근거는 [일관성 감사 R05/R06](../reports/MILESTONE_CONSISTENCY_AUDIT_REPORT_V01.md)에 있다.

#### 이전 v0.1 software 준비 이력 (새 독립 gold protocol 완료 아님)

- deterministic seed를 사용하는 2인 독립 blinded assignment와 별도 adjudicator 지정
- slice×outcome joint cell당 3~4개인 locked 60-slot manifest(행 20, 열 10)
- `MINIMAL_CONFIRMATION`/`COMPLETE_AUTHORING` 두 mode의 self-contained training UI와 timing export
- annotation·assignment·agreement/timing metrics JSON 계약과 semantic validator
- nominal Krippendorff α의 유한표본 기대 불일치 보정
- 최대 guideline revision 2회 enforcement
- 관측 paired effect/variance source ref가 없으면 생성되지 않는 power-planning 계약

최종 preflight package:
`artifacts/results/restricted/guardsynth-expert-pilot-preflight-001/m16-preflight-2026-08-12-v4/`

software 검증(2026-08-12):

- `python3 -m unittest tests.guard_synth_eblc.test_expert_pilot_protocol -v`: 10/10
- maintained GuardSynth/EBLC suite: 303/303
- P0a compatibility: 7/7
- project structure/link suite: 10/10

#### 이전 역사적 입력 경계와 현재 계승

M13 terminal batch의 source-complete scene은 4개이며 모두
`PEDESTRIAN_CYCLIST_YIELD/HAZARD_TRUE_ACTIVE`다. 따라서 60-scene empirical annotation은
시작할 수 없다. M16 software 준비와 preflight를 완료하되 부족한 56장면을 합성하지 않는다.
training fixture와 UI는 interface 검증용 synthetic 자산이며 empirical pilot 표본이 아니다.
위 4/60·shortfall 56은 M13 terminal 당시의 역사적 집계다. 현재 scope 재감사값은 1/60이며
최신 단일 작업은 [실행 추적표](../plans/03_PROJECT_EXECUTION_TRACKER.md)의 M12-R01이다.

</details>
