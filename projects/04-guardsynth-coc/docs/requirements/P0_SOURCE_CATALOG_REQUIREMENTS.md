# M12 1차 논문의 task·제약·source 요구사항

- work package: `GS-P0-SOURCE-REQUAL-001` / M12-R01
- 상태: `READY_NEXT`
- 권위: [1차/2차 분리 결정](../decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md)

1차는 주 dataset 1개·trainable VLM 1개·주 행동군과 대비군 1개 이내를 source/관측성과
충분한 표본으로 사전 선정한다. 사용 clause의 조건·target·수치/unit·해제와 source/binder를
연결한다. CoC claim은 관측/규범 authority가 아니다. 국가 whitelist 없이 선택한 benchmark
규칙의 범위를 명시하며 실제 법적 준수나 차량 안전으로 확대하지 않는다.

출력은 선택 task/model/data, source-to-clause matrix, 필요한 관측량, 새 cohort eligibility와
split/power 입력이다. 기존 15-template/3-slice/6-family 전체 재검증은 2차이며 1차 선행조건이 아니다.
VLM 선정 시 실제 image/video 입력, fine-tuning 가능한 module·processor, license·가용 자원과
내부 adapter/full fine-tuning 경로를 확인한다. 별도 scorer만 학습하는 모델 구성은 선택하지 않는다.
관측되지 않은 수치/geometry를 채워넣지는 않는다. 기존 1/60을 새 범위에서 통과로 재표기하지 않는다.

## 이전 상세 요구사항 (2차/구현 이력)

<details>
<summary>기존 완료 근거와 확장 protocol 보기</summary>

아래 현재/필수/선행조건 표현은 당시 범위다. 1차 적용은 위 v2.3 계약이 대체한다.

### 이전 GuardSynth 대한민국 P0 source catalog 요구사항

- work package: `GS-P0-CATALOG-001`
- milestone: M12
- 선행 결정: [대한민국 범위 결정](../decisions/GUARDSYNTH_KR_SCOPE_AND_SOURCE_POLICY_DECISION_V01.md)
- locked 범위: 15개 template, 세 deep slice, 여섯 broad family
- 이 범위는 최초 KR catalog의 완료 이력이며 현재 전체 장면의 국가 제한이 아니다.
- 후속 `M12-R01 / GS-P0-SOURCE-REQUAL-001 READY_NEXT`는 현 multi-jurisdiction/treaty scope의
  clause별 source·precondition/exception·binder와 직접 규칙/일반 fallback/system/physical
  구분을 재감사한다. 기준은 [일관성 감사 R01](../reports/MILESTONE_CONSISTENCY_AUDIT_REPORT_V01.md)이며
  기존 artifact를 바꾸지 않고 새 current-scope 실행 matrix와 gate 결과를 남긴다.

#### 이전 1. 산출물

1. `projects/04-guardsynth-coc/src/guard_synth/schemas/source_catalog.schema.json`
2. `projects/04-guardsynth-coc/src/guard_synth/fixtures/source_catalog_kr_v0_1.json`
3. `projects/04-guardsynth-coc/src/guard_synth/source_catalog.py`
4. catalog audit 단위 테스트와 공개 실행 artifact

기존 단일 synthetic P0b catalog와 generator fixture는 회귀 호환성을 위해 유지한다. 새 catalog는
실제 source authoring을 위한 별도 버전 경계이며, 곧바로 기존 pedestrian program으로
컴파일된다고 주장하지 않는다.

#### 이전 2. 필수 내용

- 관할·시행일·ODD와 공식 source record
- source claim 단위의 rule trace
- rule의 scope/precondition/exception/roles
- target/zone binding, ambiguity reason과 partial binder
- PredicateSpec의 observability/freshness/failure-to-UNKNOWN
- activation/invariant/bound/release/reactivation/expiry/fallback 및 edge별 authority
- hard legal/system과 service/preference를 분리한 priority tier
- 여섯 family coverage와 세 slice별 rule 수

#### 이전 3. fail-closed 규칙

- 법령에 없는 numeric literal을 rule/binder/lifecycle에 삽입하지 않는다.
- 수치 근거가 없으면 `UNSUPPORTED`와 reason code를 기록한다.
- source·predicate·binder·lifecycle reference가 닫히지 않으면 catalog load를 거부한다.
- official source record가 아닌 항목을 `LEGAL`로 표기하면 거부한다.
- CoC를 source claim 또는 observed predicate로 등록하면 거부한다.
- freshness threshold가 근거 없이 없을 때는 `REVIEW_REQUIRED` policy로 보존한다.

#### 이전 4. locked gate

| gate | 기대값 |
|---|---:|
| schema-valid fixture | 100% |
| template 수 | 12–20 (locked 15) |
| slice coverage | 각 slice 4개 이상 |
| broad family coverage | 6/6 |
| source/predicate/binder/lifecycle reference closure | 100% |
| source 없는 normative/numeric value | 0 |
| failure-to-UNKNOWN contract | 100% predicates |
| catalog focused tests | 100% pass |

이 gate는 source catalog의 구조와 추적성을 검증한다. 규칙 해석의 법률 자문 적합성, sensor
accuracy, 차량 capability 또는 실제 장면 안전성을 입증하지 않는다.

</details>
