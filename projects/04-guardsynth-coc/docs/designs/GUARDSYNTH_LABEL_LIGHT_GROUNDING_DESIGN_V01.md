# GuardSynth label-light grounding v0.1 설계

## 1. 목적

GuardSynth의 실제 장면 연결이 모든 frame의 보행자 polygon, conflict-zone polygon과
trajectory를 사람이 처음부터 완전하게 그리는 방식에 의존하면 연구와 실용화 모두에서
병목이 된다. 이 계층의 목적은 **기존 perception·tracking·map·trajectory 출력으로 후보를
먼저 만들고, 사람은 모호한 경우만 최소 확인**하게 하는 것이다.

```text
기존 detector/tracker/map/ego-path 출력
                 │
                 v
      target–zone 후보와 근거 생성
                 │
       ┌─────────┼──────────┐
       v         v          v
   자동 확인   최소 검토   지원 불가/충돌
       │         │          │
       └──── grounded scene  └─ EBLC 생성 안 함
                 │
                 v
source authoring → GuardSynth → EBLC → Core → Z3/runtime
```

이 모듈은 detector를 새로 학습하지 않고 confidence를 사실로 승격하지 않는다. `0-label`
정확도를 주장하지도 않는다. 작은 calibration/audit 표본과 모호한 사례 검토는 필요하다.

## 2. 입력 계약

`guardsynth-label-light-grounding-v0.1` packet은 다음을 받는다.

- 장면 timestamp와 전체 evidence registry
- `TRUE/FALSE/UNKNOWN/CONFLICT` hazard fact와 epistemic kind
- tracker가 제안한 target과 track evidence
- 지도/파생 geometry가 제안한 conflict zone과 검증된 좌표 변환 evidence
- target–zone pair 후보, path-intersection 판정과 confidence interval
- confidence calibration source와 자동 확인 policy source
- 실제 registry lookup에 사용할 vehicle binding key와 assurance scope

입력 schema는 syntax만 검사한다. 자동화 허용 여부는 canonical triage 함수가 판단한다.

## 3. 세 단계 판정

### 3.1 자동 확인

다음 조건이 모두 만족될 때만 `AUTO_CONFIRMED`다.

1. path-intersection이 `TRUE`인 pair가 policy가 요구하는 방식으로 유일하다.
2. confidence **하한**이 policy threshold 이상이다.
3. confidence가 승인된 calibration evidence에 묶여 있다.
4. hazard가 `CLAIMED`가 아니고 fresh하다.
5. track, zone geometry, coordinate transform 및 association evidence가 모두 있다.

자동 확인은 “association proposal을 다음 구조화 단계로 전달해도 된다”는 뜻이지, 안전이나
법규 타당성을 검증했다는 뜻이 아니다.

### 3.2 최소 사람 확인

저신뢰, 복수 후보, 자동화 금지 policy 또는 CoC claim-only hazard는
`REVIEW_REQUIRED`다. review task는 다음 네 동작만 제공한다.

- 제안 pair 확인
- 다른 후보 pair 선택
- 모호함 표시
- 장면 거부

전체 geometry를 다시 그리도록 요구하지 않는다. 확인 근거와 수정 여부는 provenance와
workflow metric에 남는다. 사람의 확인도 누락된 geometry나 vehicle assurance를 대신하지
않는다.

### 3.3 지원 불가와 충돌

track/geometry/transform/calibration evidence가 없으면 `UNSUPPORTED`, 상충하는 hazard는
`CONFLICT`로 남기고 grounded scene과 EBLC를 생성하지 않는다. 값을 추측하거나 낮은
confidence를 임의로 `FALSE`로 닫지 않는다.

## 4. 라벨 비용을 줄이는 방법

전 장면 완전 라벨 대신 다음 순서로 운영한다.

1. 기존 model output을 proposal로 재사용한다.
2. 유일하고 calibrated된 고신뢰 건은 자동 처리한다.
3. uncertainty·불일치·경계 사례만 review queue로 보낸다.
4. review에서 발생한 correction을 calibration/audit 표본으로 축적한다.
5. 자동 처리 표본 일부를 무작위 audit해 silent error를 추정한다.

따라서 필요한 사람 작업은 “모든 것을 그리기”가 아니라 “선택·확인·감사”가 된다. 실제
절감률과 association accuracy는 아직 측정하지 않았으며 24-scene dry run에서 자동화율,
검토율, 수정률, 검토 시간과 unsupported coverage를 함께 보고해야 한다.

## 5. 근거 전달과 경계

자동/사람 확인 결과에는 association model evidence, calibration evidence, target track,
review evidence가 모두 포함된다. `source_authoring.py`가 이를 최종 ContextGraph association과
generation request의 `source_refs`까지 전달한다. RuleTemplate, 법규, 수치, vehicle assurance는
별도 source registry가 제공하며 label-light 결과가 이를 생성하지 않는다.

## 6. v0.1 검증 범위와 다음 단계

공개 synthetic scenario는 자동 확인, policy 금지, 저신뢰, 복수 후보, claim-only,
unverified transform, conflict와 한 번 확인을 고정한다. 자동 확인된 두 scene은
GuardSynth→EBLC→Core→Z3까지 전달한다. 기존 제한 파생 입력은 식별자 없는 집계만 수행한다.

다음 데이터 작업은 기존 Alpamayo/파생 detector output을 이 packet으로 변환하는 adapter와
작은 층화 calibration/audit set이다. 실제 vehicle assurance와 rig→ego-path transform은
별도 source authoring 작업이며 annotation으로 대체할 수 없다.
