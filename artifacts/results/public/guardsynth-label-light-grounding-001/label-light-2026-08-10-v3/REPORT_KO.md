# GuardSynth label-light grounding v0.1 실행 보고서

- 상태: **EXECUTED**
- synthetic scenario: 8/8
- 자동 확인: 1
- 사람 확인 요청: 4
- 최소 확인 완료: 1
- 입력 부족 중단: 1
- 충돌 보존: 1
- Z3: 5.0.0, query agreement 100%
- 주장 범위: `LABEL_LIGHT_SYNTHETIC_GROUNDING_AND_BOUNDED_HANDOFF_NOT_ASSOCIATION_ACCURACY_OR_VEHICLE_SAFETY`

## 무엇을 구현했는가

대량의 새 polygon/trajectory 레이블을 전제로 하지 않는다. 기존 perception·tracking·map
출력으로 target–zone 후보를 만들고, 승인된 calibration의 하한과 유일성 조건이 만족되면
자동 확인한다. 저신뢰·다중 후보·CoC claim-only 입력은 한 번의 선택/확인 작업으로 보내며,
geometry·좌표 변환·근거가 없거나 evidence가 충돌하면 EBLC를 만들지 않는다.

자동 확인된 synthetic 장면 두 개는 source authoring → GuardSynth generator → EBLC indexed
collection → bundle → Core → 실제 Z3까지 전달됐다. 사람 확인 근거도 최종 generation request의
provenance에 보존된다.

## 현재 제한 파생 입력

- 후보 event: 5/24
- association review 필요: 4
- 자동 확인 가능: 0
- contract 입력 부족: 4

이는 기존 제한 입력을 재레이블링한 결과가 아니라 식별자 없는 준비도 집계다. 현재 데이터에는
calibrated association proposal, 검증된 좌표 변환 및 실제 vehicle assurance가 없으므로
`DATA_GAP_PIVOT`은 유지된다.

## 테스트

- label-light 집중 테스트: 15/15
- 전체 maintained 테스트: 187/187
- P0a 회귀: 7/7
- 구조/문서 링크: 9/9

confidence는 관측 사실이나 안전 보장이 아니다. 이 결과는 label 부담을 줄이는 software
workflow와 bounded handoff를 검증했을 뿐 association 정확도, 실제 법규 또는 차량 안전성을
입증하지 않는다.
