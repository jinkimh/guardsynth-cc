# GuardSynth 대한민국 source catalog v0.1 감사 보고서

- 상태: **EXECUTED**
- template: 15개
- slice 배분: pedestrian/cyclist 5, stop/signals 6, following/cut-in 4
- broad family: 6/6
- source record/claim: 6/16
- predicate failure-to-UNKNOWN: 11/11
- source 없는 규범·실행 수치: 0건
- 주장 범위: `P0_SOURCE_CATALOG_TRACEABILITY_NOT_LEGAL_ADVICE_SENSOR_ACCURACY_VEHICLE_ASSURANCE_OR_SAFETY`

## 결과

대한민국 도로교통법과 시행규칙의 현행 공식 원문을 기준으로 세 slice 15개 규칙을
source claim에 연결했다. 법이 숫자를 제공하지 않는 안전거리에는 값을 넣지 않고
`UNSUPPORTED_LEGAL_TEXT_HAS_NO_NUMERIC_BOUND`를 유지했다. sensor freshness, release
hysteresis와 fallback은 법률 원문이 아니라 별도 시스템 operationalization으로 구분했다.

## 테스트

- source catalog 집중: 10/10
- 전체 maintained: 202/202
- P0a 회귀: 7/7
- 구조/문서 링크: 10/10

## 제한

이 결과는 공식 source record, schema와 reference closure를 감사한 것이다. 법률 전문가의
적용 판단, 자연어 CoC parsing, 실제 장면 association, sensor 성능, 차량 assurance 및
차량 안전성을 입증하지 않는다. source record hash는 원문 파일 hash가 아니라 공개한
canonical record의 변경 검출용 hash다.
