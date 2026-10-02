# GuardSynth 대한민국 초기 범위와 근거 정책 결정 v1

- 결정 ID: `GS-P0-SCOPE-001`
- 결정일: 2026-08-10
- 상태: `APPROVED_FOR_P0_CATALOG_AUTHORING / SUPERSEDED_AS_M16_JURISDICTION_LIMIT`
- 적용 시점: 2026-08-10 현재 유효한 법령
- 주장 범위: catalog authoring boundary이며 법률 자문이나 차량 안전 보장이 아님

> 2026-08-14부터 M16 이후 pilot의 KR-only 표본 제한은
> [다중 관할 파일럿 범위 결정](GUARDSYNTH_MULTI_JURISDICTION_PILOT_SCOPE_DECISION_V01.md)이
> 대체한다. 이 문서는 대한민국 P0 catalog와 E-1 결과의 근거로 계속 유효하다.

## 1. 결정

최초 카탈로그 관할은 **대한민국**으로 고정한다. 초기 ODD는 일반 승용차가 통행하는
도시·근교의 구조화 도로이며, 차선·교차로·횡단보도·자전거횡단도·신호기 또는 정지 위치를
좌표계가 확인된 지도/인지 출력으로 식별할 수 있는 경우만 포함한다.

법령 기준 버전은 다음과 같다.

- 「도로교통법」: 2026-07-01 시행, 법률 제21246호
- 「도로교통법 시행규칙」: 2026-08-01 시행, 행정안전부령 제610호
- 법제처 법령해석은 예외·해석 보조자료이며 법원 확정판결과 같은 기속력을 주장하지 않는다.

## 2. 세 deep slice

| slice | 포함 | 필수 장면 입력 | 제외/중단 조건 |
|---|---|---|---|
| pedestrian/cyclist yield | 횡단보도 보행자, 비횡단보도 횡단자, 자전거횡단도 이용자, 회전 중 횡단자 | actor class/track, crossing 또는 zone geometry, actor-zone association, ego pose/trajectory, timestamp | association·geometry·frame 불명, 단순 CoC 주장만 존재 |
| stop/signals | 적·황·점멸 신호, 일반 신호 준수, 경찰 지시 우선 | 신호 상태/지시, 신호-차로 association, stop line 또는 교차로 경계, ego pose, timestamp | 신호-차로 연결 불명, 신호 freshness 불명, 표지의 법적 의미 불명 |
| following/cut-in | 앞차 추종, 자전거 추월, 진로 변경 방해, 불필요한 급제동 | lead/adjacent actor association, 상대 위치·속도, lane/path, ego motion, timestamp | 법의 비수치 표현을 임의 수치로 변환, 차량 braking assurance 부재 |

긴급차량 특례, 공사구간 수신호, 철길건널목, 고속도로 특칙, 비구조화 off-road, 악천후
센서성능 주장은 v1 ODD에서 제외한다. 해당 상황이 감지되면 다른 규칙으로 추정하지 않고
`UNSUPPORTED_OUTSIDE_ODD`를 낸다.

## 3. source hierarchy와 주장 경계

| 우선순위 | source class | 허용 주장 | 금지 주장 |
|---:|---|---|---|
| 1 | `LEGAL` | 확인된 관할·시행일·조항의 규범 내용과 적용 범위 | 조항에 없는 거리·시간·감속 수치, 다른 관할로 일반화 |
| 2 | `VERIFIED_SYSTEM_REQUIREMENT` | 버전·승인자·시험범위가 있는 시스템 요구 | 법적 의무로 승격 |
| 3 | `VEHICLE_ASSURANCE` | 식별된 차량/조건에서 시험·보증된 capability | 다른 차량·노면·속도 범위로 외삽 |
| 4 | `PHYSICS_DERIVED` | 단위·좌표계·입력 근거가 닫힌 결정론적 유도값 | 입력을 vehicle guarantee로 간주 |
| 5 | `OBSERVED/PREDICTED/DERIVED` | provenance와 freshness가 있는 장면 사실/추정 | 규범 authority로 승격 |
| 6 | `COC_CLAIMED` | 검색·후보 생성 단서 | 관측 사실, 법규, 안전 보장으로 승격 |

hard legal/safety tier는 service/preference 점수로 상쇄하지 않는다. 서로 다른 authority가
충돌하면 조용히 가중합하지 않고 `CONFLICT` 또는 검토 대상으로 보낸다.

## 4. partial binding과 수치 정책

- 법이 “필요한 거리”를 요구하지만 숫자를 제시하지 않으면 결과는
  `UNSUPPORTED_LEGAL_TEXT_HAS_NO_NUMERIC_BOUND`이다.
- stop line/교차로 경계는 실제 geometry에서 좌표를 유도할 수 있으나 고정 margin을 넣지 않는다.
- freshness threshold, 연속 clear frame 수, 제동능력과 response time은 근거가 있는 시스템/차량
  profile이 제공될 때만 실행값이 된다.
- 필수 actor-zone, signal-lane 또는 lead-ego association이 유일하지 않으면
  `AMBIGUOUS_BINDING`으로 중단한다.
- CoC 문장만으로 activation truth를 만들지 않는다.

## 5. lifecycle authority

법규가 activation/invariant의 규범 근거를 제공하더라도 release hysteresis, reactivation,
expiry와 sensor fallback은 대체로 **시스템 operationalization**이다. 카탈로그는 lifecycle의
각 edge마다 `LEGAL_SOURCE`, `SYSTEM_OPERATIONALIZATION`, `VEHICLE_ASSURANCE` 또는
`UNSUPPORTED` authority를 별도로 기록한다. 시스템 의미를 법률 원문이라고 주장하지 않는다.

## 6. 공개·제한 자료 정책

- 법령 URL, 조항 식별자, paraphrase와 source-record hash는 공개한다.
- 법령 전문을 저장소에 복제하지 않고 국가법령정보센터 원문을 참조한다.
- `record_hash`는 원문 파일 hash가 아니라 canonical source record의 hash임을 명시한다.
- restricted scene의 원본, 식별자, frame, CoC 전문과 license 제한 annotation은
  `artifacts/results/restricted/`에만 둔다.
- 공개 결과에는 비식별 집계와 missing-field reason code만 둔다.

## 7. M12 초기 배분

| slice | template 수 | 핵심 근거 |
|---|---:|---|
| pedestrian/cyclist yield | 5 | 도로교통법 제27조제1·2·3·5항, 제15조의2제3항 |
| stop/signals | 6 | 도로교통법 제5조제1·2항, 시행규칙 별표 2의 적·황·점멸 신호 |
| following/cut-in | 4 | 도로교통법 제19조제1·2·3·4항 |
| 합계 | 15 | 세 slice, 여섯 broad family |

관련 세부 요구사항은
[P0_SOURCE_CATALOG_REQUIREMENTS.md](../requirements/P0_SOURCE_CATALOG_REQUIREMENTS.md)를
따른다.
