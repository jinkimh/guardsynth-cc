# M16 review-event anchor 결정

- 결정일: 2026-09-05
- 적용 범위: `GS-P4-PILOT-001`의 M16 source curation scene
- 결정: 각 review item의 source-linked `event_timestamp_us`를 해당 장면의 `model-t0`로 사용
- 상태: `ACCEPTED`

## 배경

M16의 60-scene formal pilot은 기존 Alpamayo inference run을 재현하는 실험이 아니다. 각 후보는
CASCADE annotation에서 결정적으로 분류된 event에 고정되며, 사람의 영상 관찰 packet도 그 event
전후의 frame을 제시한다. 따라서 다른 clip 또는 과거 inference manifest의 t0를 가져오면 장면의
실제 검토 기준시각과 어긋날 수 있다.

## 결정과 검증 규칙

1. M16 curation scene의 `model-t0`는 그 record의 `event_timestamp_us`와 같아야 한다.
2. event timestamp는 선택된 offline egomotion 범위 안에 있어야 하며, 인접 pose 사이에서
   quaternion Slerp와 translation 선형보간으로 event pose를 계산한다.
3. `dataset_rig_at_event → ego_at_model_t0`는 같은 시각·같은 ego frame이므로 identity가 정상이다.
   행렬과 역행렬의 수치 closure를 검증하지 못하면 field를 닫지 않는다.
4. NVIDIA NCore가 선택한 offline egomotion과 offline sensor extrinsics의 materialized hash와
   수치 유효성을 함께 확인한다.
5. 이 결정은 과거 Alpamayo inference 결과를 재감사할 때의 t0를 변경하지 않는다.

## 주장 경계

이 결정은 coordinate-transform field만 닫는다. lane/zone geometry, actor/control association,
관할 authority, rule applicability, outcome lifecycle 또는 차량 안전성을 판정하지 않는다. 해당
근거가 없는 record는 계속 `source_complete=false`, `eligible=false`로 유지한다.
