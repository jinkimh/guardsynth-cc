# GuardSynth 다중 관할 파일럿 범위 결정 v1

- 결정 ID: `GS-P4-SCOPE-002`
- 결정일: 2026-08-14
- 상태: `APPROVED`
- 적용 범위: M16 이후 GuardBench-CoC pilot과 후속 empirical study
- 승인 근거: 연구 scope owner의 “KR-only 해제, 어떤 국가 장면도 허용” 결정
- 주장 경계: 장면 적격성·표본 범위 결정이며 법률 자문이나 차량 안전 보장이 아님

## 0. 2026-09-06 재확인·구현 반영

연구 scope owner가 “KR 전용을 해제하고 특정 지역으로 한정하지 않는다”는 결정을 재확인했다.
이에 공용 source-catalog schema의 `country_code=KR` 제약과 generic CLI의 암묵적 KR catalog
기본값을 제거했다. catalog loader는 경로를 명시적으로 받아야 하며, 각 jurisdiction-specific
catalog는 ISO-style 국가 코드와 공식 source host allowlist를 선언한다.

이는 특정 국가 whitelist를 두지 않는다는 뜻이지, 서로 다른 국가의 국내법을 혼합하거나 관할을
생략한다는 뜻이 아니다. M16의 중립 authority 선택은
[국제 도로교통협약 연구 기준 결정](M16_INTERNATIONAL_TREATY_BASELINE_DECISION_V01.md)이 구체화한다.
국내법 준수 주장을 하는 경우에는 여전히 같은 관할의 versioned 공식 source가 필요하다.

## 1. 결정

M16 이후의 pilot은 대한민국 단일 관할 제한을 해제한다. 국가 whitelist와 국가별 최소
quota를 두지 않으며, 어느 국가의 장면도 아래 장면별 근거 gate를 만족하면 포함할 수 있다.
서로 다른 국가의 적격 장면을 동일한 60-scene pilot에 결합하는 것도 허용한다.

이 결정은 국가를 알 수 없는 장면이나 source가 없는 규칙을 허용한다는 뜻이 아니다. 각
장면은 촬영 관할과 적용 authority의 jurisdiction, version/validity, scope, precondition 및
exception을 명시적으로 연결해야 한다. legal authority는 같은 관할의 공식 source여야 한다.
승인된 verified system requirement는 source가 적용 범위를 명시한 경우
jurisdiction-independent authority로 사용할 수 있다.

## 2. 장면별 적격성 규칙

장면은 다음 조건을 모두 만족할 때만 M16 slot에 포함한다.

1. 관할 국가와 필요한 경우 주·도·지방 등 하위 관할이 source-linked evidence로 식별된다.
2. M16 연구 baseline은 해당 국가의 UN 협약 당사국 상태와 공식 협약문을 연결한다. 국내법
   준수 주장을 하는 경우에는 같은 관할의 공식 source 또는 승인된 versioned snapshot이 필요하다.
   verified system requirement는 승인·버전·적용 범위가 source-linked 상태여야 한다.
3. rule scope, ODD, maneuver, precondition과 exception이 해당 장면과 호환된다.
4. 기존 M16의 실제/파생 장면 근거 8종이 모두 source-linked 상태다.
5. CoC claim, 파일명, 단일 이미지 추정 또는 다른 국가 규칙으로 누락 근거를 채우지 않는다.
6. recorded-rig binding과 simulation vehicle binding을 계속 분리한다.

관할이 불명확하면 `UNSUPPORTED_JURISDICTION`, 동일 장면에서 관할 source가 충돌하면
`CONFLICT`, 사람이 확인해야 하면 `REVIEW_REQUIRED`로 처리한다. 해당 상태는 해소되기 전까지
eligible 수에 포함하지 않는다.

## 3. 유지되는 범위와 gate

- 도시·근교 structured-road ODD와 세 deep slice는 유지한다.
- 60개 distinct scene, slice 20개씩, outcome 10개씩 및 18개 joint-cell quota를 유지한다.
- synthetic required-field fill 0, unsourced normative/numeric value 0을 유지한다.
- 60/60과 모든 quota가 충족되기 전에는 reviewer calibration과 annotation을 시작하지 않는다.
- 실제 차량 assurance와 실차 검증은 M21로 이관된 상태를 유지한다.
- jurisdiction은 분석 시 source version과 함께 cluster/covariate로 기록한다.

## 4. 기존 대한민국 결정과 catalog의 지위

[대한민국 초기 범위 결정](GUARDSYNTH_KR_SCOPE_AND_SOURCE_POLICY_DECISION_V01.md)은 P0 catalog와
E-1 feasibility 결과의 역사적·기술적 근거로 유지한다. 다만 M16 이후 pilot 표본을 KR-only로
제한하는 효력은 이 결정이 대체한다. 기존 대한민국 catalog는 폐기하지 않고 첫 번째 역사적
jurisdiction-specific catalog로 사용한다. generic loader나 M16 표본의 기본 catalog로 사용하지 않는다.

## 5. 다음 실행

기존 23개 distinct candidate와 이후 후보를 이 정책으로 재평가한다. 기존 California-linked
장면도 자동 승격하지 않고 관할·compatible authority·ODD·8/8 field closure를 다시 검증한다.
첫 재평가에서는 23개 distinct candidate 중 1개만 eligible이었다. 부족한 slice×outcome cell을
우선으로 국가 제한 없이 source-complete 장면을 확보하고,
60/60과 모든 gate가 충족될 때만 reviewer calibration으로 이동한다.
