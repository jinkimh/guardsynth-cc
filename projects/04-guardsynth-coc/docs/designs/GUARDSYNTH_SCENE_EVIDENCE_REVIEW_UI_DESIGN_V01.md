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
- 실제 검토 form: 카드별 장면 이미지, 필드별 evidence ref, 자동 권고와 최종 판정
- batch import: 여러 이미지 또는 폴더를 한 번 선택하면 이미지별 검토 카드 자동 생성
- restricted embedded package: 지정한 이미지들을 data URL로 단일 HTML에 내장
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

이미지 내장 패키지는 별도 갤러리를 만들지 않고 각 장면을 해당 설문 카드 상단에 직접
연결한다. 카드별 파일 선택란은 없으며 공개 shell에서만 상단 batch/folder import를 제공한다.
HTML 자체에는 제한 image bytes가 포함되므로 builder와 산출물은
`artifacts/results/restricted/` 경계를 강제한다.

## 5. Image-only 검토 모드

이미지밖에 없는 검토자에게 source audit 필드를 요구하지 않는다. 별도
`image_only_scene_review.html`은 장면 태그의 복수 선택과 이미지로 관찰 가능한 위험,
관련 이동 영역 후보, 관련 대상과 영역의 관계, 대상 가림, 교통 통제, ego 움직임 인상,
프레임 변화를 기록한다. 여기서 `_VISIBLE`은 영역 종류가 화면에서 식별된다는 뜻이며
충돌 발생이나 미래 경로 교차를 확정한다는 뜻이 아니다. 검토자는 관련 대상 하나와 그
대상을 판단하는 데 가장 직접적인 대표 영역 하나를 선택한다. 대상 위치는 그 두 항목의
공간 관계이고, 가림은 영역이 아니라 관련 대상의 몸체·차체가 가려진 정도다.
프레임 간 변화는 contact sheet 또는 연속 이미지에서 동일한 관련 대상과 선택 영역의
관계가 시간순으로 접근·진입·이탈·유지되는지를 기록한다. ego나 화면 전체의 변화가
아니며, 프레임 순서나 동일 대상 여부가 불명확하면 `CANNOT_TELL`, 비교할 프레임이 하나면
`SINGLE_FRAME_ONLY`를 사용한다.
target/track ID, timestamp, geometry evidence, coordinate frame, transform과 vehicle
assurance는 입력란이 아니며 `NOT_AVAILABLE_FROM_IMAGE`로 출력한다.

Image-only 결과는 후보 선별과 사람 검토 evidence일 뿐 source closure가 아니다. 따라서
`contract_readiness=REVIEW_REQUIRED`와
`IMAGE_ONLY_CANNOT_ESTABLISH_SOURCE_CLOSURE`를 항상 보존하며 `SOURCE_COMPLETE` 선택을
제공하지 않는다.
