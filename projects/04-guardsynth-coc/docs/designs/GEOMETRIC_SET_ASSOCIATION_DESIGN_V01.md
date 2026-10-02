# GuardSynth geometric set association v0.1

## 목적

복수 보행자 후보가 있을 때 최근접 후보 하나를 임의로 고르지 않고, 실제 track box와 ego
corridor가 겹치는 후보 집합을 target으로 고정한다. 이 산출물은 M13의
`target_zone_or_lane_association`에 대한 source-linked 기하학 근거다.

## 입력과 판정

- 입력: 시간 정렬된 모든 actor track sample, oriented 2-D half extent, 차량 폭과 전방 extent
- 포함: `abs(center_y) <= ego_half_width + actor_half_extent_y`이고 actor box가 ego 전방에 있는
  sample이 하나 이상인 track
- 출력: SHA-256 actor ID의 `SET`, corridor/track overlap의 x·y·time interval, source pointer
- 다중 후보: 유효한 결과다. nearest-only 선택은 하지 않는다.
- 0개 후보: `REVIEW_REQUIRED / NO_GEOMETRIC_CORRIDOR_ASSOCIATION`

## 주장 경계

이 판정은 수치로 재검토 가능한 track–corridor association이다. CoC 문장의 의미적 지시 대상,
보행 의도, 횡단보도나 법적 zone, 충돌 확률 또는 차량 안전성을 뜻하지 않는다. raw track ID는
제한 입력에만 남기고 산출물에는 SHA-256 식별자만 기록한다.
