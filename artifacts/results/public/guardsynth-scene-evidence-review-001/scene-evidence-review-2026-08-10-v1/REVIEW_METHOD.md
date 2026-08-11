# GuardSynth 실제 장면 근거 검토 UI v0.1 설계

- work package: `GS-P1-DRYRUN-001`
- 목적: M13의 부분 후보를 `SOURCE_COMPLETE`, `REVIEW_REQUIRED`, `UNSUPPORTED`,
  `CONFLICT`로 일관되게 분류
- 입력 보안: 사용자가 선택한 이미지는 브라우저 메모리에서만 표시하며 저장소·서버·export에 포함하지 않음
- 주장 경계: 검토 UI는 누락된 법규·좌표 변환·차량 assurance를 생성하거나 대체하지 않음

## 1. 검토 단위

한 review record는 한 장면/이벤트를 대상으로 다음 여섯 묶음을 확인한다.

1. hazard fact와 epistemic/freshness
2. target–zone/lane association
3. geometry, unit, coordinate transform와 timestamp alignment
4. 관할·규칙·precondition·exception applicability
5. numeric constraint 사용 여부와 vehicle assurance
6. lifecycle activation/release/reactivation/fallback 관측 가능성

이미지는 판단 보조 자료이고 evidence reference 자체가 아니다. 검토자는 이미지에서 보이는
내용과 추적기·지도·calibration·법규·차량 시험 record를 구분해 기록해야 한다.

## 2. 자동 권고 판정

우선순위는 다음과 같다.

```text
evidence conflict
    -> CONFLICT
필수 장면/geometry/transform 또는 필요한 assurance 누락
    -> UNSUPPORTED
CLAIMED/UNKNOWN hazard, stale fact, association ambiguity, rule applicability 미확정
    -> REVIEW_REQUIRED
필수 reference와 applicability가 모두 닫힘
    -> SOURCE_COMPLETE
```

사람이 radio button을 선택했다는 사실은 source가 아니다. `SOURCE_COMPLETE` 권고에는
track, geometry, association, transform, rule source가 모두 필요하다. numeric bound를
실행할 때만 exact vehicle binding과 assurance evidence를 추가로 요구한다.

## 3. HTML 구성

- 검토 방법: 권한 분리, 단계별 checklist, 판정 흐름
- 합성 도식: association, coordinate transform, evidence pipeline
- 예제: source-complete symbolic signal, ambiguous association, missing transform,
  missing numeric assurance
- 실제 검토 form: 로컬 이미지 선택, 필드별 evidence ref, 자동 권고와 최종 판정
- 진행률/localStorage: 텍스트 응답만 브라우저에 자동 저장
- export: CSV와 JSON; 이미지 bytes는 내보내지 않음

Content Security Policy는 network를 차단하고 `data:`/`blob:` 이미지와 inline CSS/JS만
허용한다. 따라서 restricted scene 이미지는 검토자가 로컬에서 선택할 수 있지만 공개
artifact에는 들어가지 않는다.

## 4. 운영 절차

1. 공개 HTML을 로컬 브라우저에서 연다.
2. reviewer ID와 restricted 내부 scene ID를 입력한다.
3. 필요한 경우 로컬 frame/contact sheet를 선택한다.
4. 각 단계의 실제 evidence ref를 입력한다.
5. 자동 권고와 reason code를 확인하고 최종 판정을 선택한다.
6. JSON과 CSV를 모두 저장한다.
7. restricted scene ID가 포함된 결과는 `artifacts/results/restricted/`에서만 관리한다.

공개 연구 결과에는 raw ID와 이미지 대신 판정별 count, reason-code count, review time만
집계한다.
