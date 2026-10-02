# M16 post-review source closure 재감사

- 상태: **M16_SOURCE_CLOSURE_PARTIAL_CALIBRATION_VARIANT_RESOLVED**
- human video observation: **60/60 완료·무결성 검증**
- classified events / materialized unique clips: **98 / 81**
- temporal / calibration 5-of-5 / recorded rig: **98 / 98 / 98**
- NVIDIA 공식 offline variant 선택 근거: **98/98 연결**
- verified coordinate transform: **0/98** (장면별 model-t0와 수치 폐쇄 필요)
- 신규 8/8 / final outcome / eligible: **0 / 0 / 0**
- 전체 eligible: **1/60**, shortfall **59**
- formal expert annotation 시작: **금지**

NVIDIA NCore의 고정 커밋은 PhysicalAI 변환에서 offline egomotion과 offline sensor extrinsics를 요구하며 non-offline 변형은 지원하지 않는다고 명시한다. 이에 따라 이전의 variant-selection 미결정은 해소했다. 다만 이를 장면별 좌표변환 완료로 과대 해석하지 않았다. model-t0 binding과 역행렬 수치 폐쇄, source-linked lane/zone geometry, 관할에 맞는 versioned authority, lifecycle witness가 각각 98건 남아 있다. 사람의 영상 답변은 관찰 근거로 연결했지만 이 source 필드들을 대신하지 않는다.
