# M16 source geometry 후보 생성 결과

- 상태: `M16_SOURCE_GEOMETRY_CANDIDATES_GENERATED_CURATOR_REVIEW_REQUIRED`
- 대상 이벤트: 98
- source-bound 기계 후보: 98
- curator 확인 대기: 98
- 신규 source-complete/eligible: 0/0
- 기존 pilot eligible: 1/60

TwinLiteNet+ large의 차선 및 주행 가능 영역 출력을 98개 이벤트의 다섯 시점에 생성했다. 각 출력은 원본 영상 해시, 실제 frame index와 timestamp, 원본 pixel hash, 모델 source revision과 weight hash에 연결했다.

이 결과는 지도 ground truth가 아니라 curator용 machine candidate이다. curator 확인 전에는 lane/zone·conflict geometry field를 닫지 않으며, source-complete·pilot eligibility·차량 안전성 주장을 새로 생성하지 않는다.

검토 화면은 기계 표시 품질 확인과 영상 위 normalized pixel polygon 보정만 받는다. 국가·관할, 법규 적용, calibration, evidence reference와 source-complete 판정은 묻지 않는다.
