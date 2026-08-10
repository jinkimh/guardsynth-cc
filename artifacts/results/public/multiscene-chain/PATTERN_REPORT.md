# Multi-Scene UPPAAL Pattern Report

## 범위

- 대상: nuScenes metadata mirror에서 같은 `log_token`이며 scene 간 gap이 1초 이하인 chain
- 추가 조건: 로컬 `CoC-Nusc`에 reasoning annotation과 egomotion trace가 모두 존재
- 검사 chain 수: 13개
- 모델: loop-indexed UPPAAL replay model
- 주요 query:
  - `E<> Source.Done`
  - `E<> MonitorProc.Responded`
  - `A[] not deadline_miss`
  - `A[] not contradiction`
  - `A[] not boundary_violation`
  - `A[] not deadlock`

## 핵심 결과

- 전체 통과 chain: 4개
- 실패 chain: 9개
- deadline 실패: 8개
- response reachability 실패: 7개
- boundary 실패: 0개

따라서 이 strict subset에서는 scene 연결성 자체가 문제가 아니라, 연결된 장기 episode 안에서 trusted reasoning obligation이 3초 안에 ego-speed response witness로 닫히는지가 주요 구분점이다.

## 통과 사례

### `scene-0007 -> scene-0008 -> scene-0009`

- scene 수: 3개
- replay duration: 약 39.0초
- event 수: 14개
- boundary gap: 801ms, 900ms
- 결과: 모든 query 통과

이 chain은 감속, 가속, 반복 감속이 모두 response witness와 매칭된다. 따라서 현재 detector와 deadline 설정에서는 positive connected episode 후보로 볼 수 있다.

### `scene-0056 -> scene-0057`

- scene 수: 2개
- replay duration: 약 19.5초
- event 수: 5개
- 결과: 모든 query 통과

짧지만 논문에서 설명하기 좋은 connected PASS 사례다. boundary가 짧고, reasoning event 수가 너무 많지 않아 그림과 timeline으로 제시하기 쉽다.

## 실패 사례

### `scene-0130 -> scene-0131 -> scene-0132 -> scene-0133`

- scene 수: 4개
- replay duration: 약 72.3초
- event 수: 16개
- boundary gap: 650ms, 600ms, 650ms
- 실패 query: `E<> MonitorProc.Responded`, `A[] not deadline_miss`
- 첫 실패 후보: `scene-0130:0:slow`
- CoT: "Yield to pedestrians crossing the street at the crosswalk and then accelerate to proceed."

이 사례는 boundary는 모두 통과하지만, 첫 scene의 yield/slow obligation이 deadline 안에 response witness로 닫히지 않는다. 즉 연결성 audit만으로는 발견할 수 없는 시간 계약 실패다.

### `scene-0027 -> scene-0028`

- scene 수: 2개
- replay duration: 약 31.4초
- event 수: 16개
- 실패 query: `E<> MonitorProc.Responded`, `A[] not deadline_miss`
- 첫 실패 후보: `scene-0027:0:accel`
- CoT: "Maintain lane and accelerate through the intersection as the traffic light is green and the path is clear."

이 사례는 acceleration reasoning도 deadline 기반 response witness와 맞지 않을 수 있음을 보여준다. 감속 중심 checker만으로는 놓칠 수 있는 반대 방향 사례다.

### `scene-0150 -> scene-0151`

- scene 수: 2개
- replay duration: 약 32.6초
- event 수: 10개
- 실패 query: `E<> MonitorProc.Responded`, `A[] not deadline_miss`
- 첫 실패 후보: `scene-0150:0:slow`
- CoT: "Adapt speed for the upcoming speed bump while keeping lane and maintaining a safe distance from the lead vehicle."

speed-bump 관련 event는 현재 batch에서 모두 FAIL group에만 나타났다. 이는 실제 위험이라기보다, speed-bump 상황에서 CoT의 "adapt speed" 표현과 ego-speed detector의 witness 정의가 잘 맞지 않을 가능성을 시사한다.

## 반복 패턴

태그 기반으로 보면 다음 tag가 FAIL group에 집중된다.

- `speed_bump`: 7/7 event가 FAIL group
- `parked_vehicle`: 5/5 event가 FAIL group
- `construction`: 6/8 event가 FAIL group
- `lead_vehicle`: 11/17 event가 FAIL group

이 통계는 강한 결론이 아니라 탐색적 신호다. 같은 `lead_vehicle`, `intersection`, `decelerate` 표현은 PASS group에도 존재하므로, 단어 자체가 실패 원인은 아니다. 더 정확한 해석은 특정 상황 표현과 현재 response detector/deadline 조합 사이의 mismatch 후보가 있다는 것이다.

## 모델 간 추론

1. Continuity audit와 UPPAAL verification은 다른 정보를 준다.
   - 모든 chain이 `A[] not boundary_violation`을 만족했지만, 8개 chain은 `A[] not deadline_miss`를 만족하지 못했다.
   - 즉 "연속으로 연결 가능하다"와 "연결된 episode가 판단-반응 계약을 만족한다"는 별개의 주장이다.

2. PASS chain은 connected positive candidate로 사용할 수 있다.
   - `scene-0007 -> scene-0008 -> scene-0009`, `scene-0056 -> scene-0057` 등은 현재 deadline/detector 설정에서 sequence-level positive supervision 후보가 된다.

3. FAIL chain은 hard negative가 아니라 review candidate에 가깝다.
   - response witness가 없다는 것은 actuator failure 증거가 아니라 ego-speed detector와 reasoning obligation 사이의 mismatch다.
   - 따라서 nominal trajectory learning에는 바로 쓰지 말고, checker regression 또는 manual review 대상으로 두는 것이 안전하다.

4. 현재 monitor는 deadline miss 이후의 2차 모순을 약하게 본다.
   - deadline miss가 발생하면 monitor가 `Miss` 상태로 들어가므로, 그 이후의 contradiction을 적극적으로 누적 감시하지 않는다.
   - 다음 모델은 sticky violation flag를 유지하면서 replay를 끝까지 소비하는 형태로 개선할 수 있다.
