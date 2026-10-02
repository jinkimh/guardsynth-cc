# 논문 개선 계획

대상 문서: `paper/demestic-journal/main.tex` 및 `sections/*.tex`

본 문서는 현재 원고를 논문 형태로 더 설득력 있게 다듬기 위한 개선 계획이다. 핵심 방향은 논문의 주장을 과도하게 넓히지 않고, reasoning-augmented driving annotation을 학습 데이터로 사용하기 전에 수행해야 하는 **정형 일관성 감사(formal consistency audit)** 로 명확히 재정의하는 것이다.

## 1. 핵심 포지셔닝 재정의

현재 원고는 reasoning-augmented E2E driving, CoC annotation, UPPAAL model checking, 학습 데이터 선별, scene continuity를 모두 다루고 있어 초점이 넓어 보일 수 있다. 논문의 중심 주장은 다음과 같이 좁히는 것이 바람직하다.

> 본 논문은 reasoning-augmented driving annotation이 물리적으로 안전한 제어를 보장하는지 증명하지 않는다. 대신, 이러한 annotation을 E2E/VLA 주행 모델 학습 데이터로 사용하기 전에 판단-반응 시간 계약, 반복 판단 의미론, 출처 정합성, scene 경계 처리가 일관적인지 검사하는 정형 감사 절차를 제안한다.

이 포지셔닝을 초록, 서론, 문제 정의, 논의에서 일관되게 유지해야 한다.

## 2. 초록 및 서론 개선

### 2.1 초록

초록은 다음 순서로 다시 정리한다.

1. Reasoning-augmented driving annotation은 자연어 판단 근거와 제어 의도를 함께 제공하므로 E2E/VLA 주행 학습에 유용하다.
2. 그러나 자연어 reasoning event는 그 자체로 actuator command가 아니며, 반복 event, 반응 기한, scene boundary가 명확히 정의되지 않으면 학습 데이터와 검증 결과가 모순될 수 있다.
3. 본 논문은 CoC event를 timed obligation으로 변환하고, UPPAAL 네트워크를 사용해 판단-반응 계약을 검사한다.
4. CoC-Nusc 94개 scene 실험에서 반복 의미론에 따른 verdict flip, deadline boundary 사례, orphan response, scene boundary carry-over 방지 가능성을 확인하였다.
5. 본 결과는 물리 안전성 증명이 아니라 학습 데이터 선별과 검토 우선순위화를 위한 protocol-level consistency audit임을 명시한다.

### 2.2 서론

서론은 다음 흐름으로 구성한다.

1. E2E/VLA driving에서 reasoning augmentation이 왜 등장했는지 설명한다.
2. Reasoning text가 학습 가능한 의미 신호를 제공하지만, 시간적 제어 계약은 자동으로 닫히지 않는다는 문제를 제기한다.
3. `scene-0001`의 반복 감속 사례를 직관적 동기 사례로 제시한다.
4. 본 논문의 연구 질문을 다음과 같이 압축한다.
   - RQ1: trusted reasoning event는 실제 검사 가능한 timed obligation으로 변환되는가?
   - RQ2: 반복 reasoning event의 의미론에 따라 deadline 판정이 달라지는가?
   - RQ3: CoC-Nusc annotation에서 protocol-level inconsistency 또는 review candidate를 찾을 수 있는가?
   - RQ4: scene continuity 증거가 없을 때 obligation carry-over를 차단할 수 있는가?
5. 기여를 세 항목으로 제시한다.
   - CoC reasoning event의 timed obligation 변환 절차
   - UPPAAL 기반 trace-replay 및 timed-contract checking 네트워크
   - CoC-Nusc 실험을 통한 failure mode 식별과 학습 데이터 선별 정책

## 3. 문제 정의 개선

### 3.1 Obligation 정의 순서 정리

`Obligation`은 자연어 CoC 문장과 차량 제어 명령 사이의 중간 검사 단위로 먼저 정의해야 한다. 그 다음에 제약식을 제시한다.

권장 구조:

1. Obligation의 직관적 정의
2. 수식 표현
3. 각 구성요소 설명
4. bounded response constraint
5. 예시
6. actuator command와 response witness의 차이

권장 표현:

> 의무(obligation)는 trusted reasoning event가 발생했을 때, 제한 시간 안에 관측 가능한 ego-motion response가 존재해야 한다는 추상적인 판단-반응 요구사항이다.

이후 다음과 같은 튜플 표현을 사용한다.

```tex
O_i = \langle \tau_i, a_i, h_i, D_i, R_{a_i}, q_i, s_i \rangle .
```

여기서 `tau_i`는 trigger 시각, `a_i`는 intent, `h_i`는 hazard/context, `D_i`는 후보 deadline, `R_{a_i}`는 response witness predicate, `q_i`는 quality/trust state, `s_i`는 obligation state이다.

### 3.2 Claim scope 명시

문제 정의 끝에 다음 범위 선언을 넣는 것이 좋다.

> 본 논문에서 obligation 만족은 물리적 충돌 회피나 차량 동역학상 실행 가능성을 의미하지 않는다. 이는 annotation, ego trace, 후보 deadline 사이의 protocol-level consistency를 의미한다.

## 4. 방법론 개선

### 4.1 전체 절차

방법론은 다음 절차로 정리한다.

1. Video 및 CoC annotation 수집
2. CoC sentence에서 intent, hazard, quality score 추출
3. trusted event만 timed obligation으로 변환
4. ego speed/trajectory에서 response witness 도출
5. UPPAAL 네트워크로 trace replay 및 timed contract checking 수행
6. verdict를 학습 데이터 선별 정책으로 변환

그림 1과 방법론 그림은 위 절차와 일치해야 한다.

### 4.2 UPPAAL의 역할 정교화

UPPAAL 모델은 reactive controller의 전체 폐루프 동작을 재현하는 모델이 아니다. 관측된 CoC event와 ego trace를 시간 순서대로 재생하고, observer automata가 시간 계약을 검사하는 구조로 설명해야 한다.

강조할 점:

- `CoCSource`: trusted/untrusted reasoning event와 반복 event를 시간 순서대로 재생
- `EgoTrace`: ego speed/trajectory에서 도출한 response witness를 재생
- `ObligationManager`: obligation 생성, pending, completed, violated 상태 관리
- `ReactionObserver`: deadline 및 반복 clock 처리 검사
- `DecisionValidator`: 저품질 event가 기존 trusted obligation을 덮어쓰지 못하게 검사

중요한 문장:

> 이 네트워크는 새로운 주행 행동을 생성하지 않는다. 대신 이미 기록된 reasoning-event trace와 ego-response trace가 지정된 시간 계약을 만족하는지 검사한다.

### 4.3 UPPAAL 사용 이유

UPPAAL을 사용하는 이유는 단순 실행 때문이 아니라, 다음을 명시적으로 조합할 수 있기 때문이다.

- 여러 timed observer의 동기화
- 반복 event 의미론 변경
- deadline violation reachability
- orphan response 탐지
- scene boundary carry-over 금지
- mutation oracle를 통한 검사기 민감도 확인

따라서 “UPPAAL이 자율주행 안전성을 증명한다”가 아니라 “UPPAAL이 reasoning-action annotation의 시간 계약 위반 가능성을 검사한다”로 설명해야 한다.

## 5. 실험 장 개선

실험은 절차 나열보다 “무엇을 검증하고 무엇을 발견했는가” 중심으로 재구성한다.

### 5.1 실험 1: 단일 장면 feasibility

목적:

- `scene-0001`의 반복 감속 event를 사용해 obligation 기반 검사가 실제로 가능한지 확인
- 단일 이벤트 검사와 episode-level 검사 결과 비교
- response detector parameter 민감도 확인

강조할 결과:

- 최초 trusted `DECELERATE` trigger: 2.5초
- 반복 감속 event: 3.5초, 4.8초
- response onset: 4.6597초
- 최초 trigger 기준 latency: 약 2.1597초
- `D=2s`에서는 실패, `D=3s`에서는 통과
- 반복 event를 새 trigger로 보면 잘못된 통과 판정이 가능함

### 5.2 실험 2: 반복 의미론 비교

반복 event의 세 의미론을 명확히 비교한다.

- Preserve: 최초 pending obligation의 deadline 유지
- Reset: 반복 event가 deadline을 다시 시작
- Deduplicate: 짧은 시간 안의 동등 event 병합

논문에서 주장해야 할 점:

> 어느 의미론이 정답인지는 데이터만으로 결정되지 않는다. 이는 시스템 요구사항 또는 학습 데이터 정책으로 명시되어야 한다.

### 5.3 실험 3: 94개 장면 전체 선별

핵심 수치를 명확히 표로 제시한다.

- 94개 scene
- 403개 annotation
- quality-pass event 290개
- directional contract 적용 가능 event 134개
- pass 129개
- review candidate 5개
- 모델 282개
- query 1,128개

이 실험의 의미:

> 전체 선별 실험은 CoC-Nusc annotation 전체가 안전하거나 위험하다는 결론을 내기 위한 것이 아니라, protocol-level review candidate를 자동으로 좁히는 feasibility를 보이기 위한 것이다.

### 5.4 실험 4: 의심 후보 집중 분석

분석 대상:

- `scene-0019`
- `scene-0028`
- `scene-0042`
- `scene-0065`
- `scene-0074`

비교 축:

- deadline `D=1--5s`
- Preserve / Reset / Deduplicate
- 27개 response detector profile

강조할 failure mode:

| Failure mode | Meaning | Example |
|---|---|---|
| Repeat-semantics flip | 반복 event를 어떻게 해석하느냐에 따라 verdict가 바뀜 | `scene-0028`, `scene-0074` |
| Deadline boundary | `D=3s`에서는 실패하지만 `D=4s`에서는 통과 | `scene-0042`, `scene-0065` |
| Orphan response | 수락된 obligation 없이 response만 관측됨 | `scene-0028` Deduplicate-1s |

## 6. 결과 장 개선

결과 장은 “모델 수와 query 수”보다 “논문이 발견한 현상”을 앞세운다.

### 6.1 단일 장면 결과

`scene-0001`의 결과는 논문 전체의 직관적 사례이므로, 실험과 결과 양쪽에서 반복해서 연결해도 된다. 단, 수치와 해석은 동일해야 한다.

권장 해석:

> 이 사례는 reasoning text가 존재하더라도 반복 판단의 lifecycle을 정의하지 않으면 동일한 ego response가 늦은 반응인지, 빠른 반응인지 다르게 판정될 수 있음을 보인다.

### 6.2 94개 장면 결과

결과는 다음 구조가 좋다.

1. 전체 통계
2. quality filtering 후 남은 event
3. directional contract 적용 가능 event
4. pass/review candidate
5. failure mode별 후보 분류

### 6.3 Multi-scene pilot 결과

현재 CoC-Nusc 단독 공개 데이터만으로는 scene 간 연속성을 보장할 수 없으므로, 모든 scene을 불연속으로 보는 최악 가정을 먼저 둔다.

그 다음 nuScenes 호환 metadata mirror 기반 pilot 결과를 제한적으로 제시한다.

- strict chain 13개
- pass 4개
- fail 9개
- boundary violation 0개

해석:

> 이 결과는 장기 scene 연결 검증의 가능성을 보이는 pilot이며, 공식 trainval metadata 전체와 객체/hazard continuity로 재확인되어야 한다.

## 7. 논의 개선

### 7.1 안전성 의미

다음 구분을 명확히 한다.

- 모델 체킹 결과가 의미하는 것: reasoning-action annotation의 시간 계약 및 protocol consistency
- 의미하지 않는 것: 충돌 회피, TTC 안전성, 물리 제어 가능성

권장 문장:

> 본 논문의 실패 verdict는 곧 물리적 사고 위험을 의미하지 않는다. 그러나 학습 데이터로 사용할 reasoning-action pair가 시간 계약 관점에서 모호하거나 모순적일 수 있음을 나타낸다.

### 7.2 학습 데이터 활용 정책

학습 데이터 선별 정책을 표로 정리한다.

| Case | Training use |
|---|---|
| Provenance-supported and quality-pass sample | Weak positive sample |
| Contract violation under justified deadline | Conditional hard negative or review candidate |
| Semantics-sensitive sample | Human review |
| Synthetic mutation | Checker test only |
| No scene continuity evidence | Independent clip/window sample only |
| Verified scene continuity | Sequence-level sample with model-checking gate |

중요한 점:

> Counterexample 자체를 올바른 대안 trajectory로 사용해서는 안 된다.

### 7.3 Closed-loop 평가와의 관계

권장 순서:

1. Model checking으로 protocol-level inconsistency 후보 선별
2. Human review로 annotation 의미 확인
3. Closed-loop replay/simulation으로 상호작용 결과 평가
4. Physical safety analysis로 TTC, 안전거리, 제동 가능성 평가

## 8. 타당성 위협 개선

현재 타당성 위협은 내용은 적절하지만, 지나치게 방어적으로 보이지 않게 “본 논문의 범위”와 연결해야 한다.

필수 항목:

- ego speed 변화는 brake/throttle command와 동일하지 않다.
- 3초 deadline은 규정이나 차량 요구사항에서 직접 도출된 값이 아니다.
- annotation은 VLM이 생성한 회고적 약한 레이블이다.
- response detector parameter에 따라 verdict가 변할 수 있다.
- chunk 0의 94개 scene만 평가하였다.
- CoC-Nusc 단독 공개 데이터에서는 scene 간 연속성을 보장할 수 없으므로 scene 간 obligation carry-over를 금지해야 한다.
- multi-scene pilot은 가능성 제시이며 공식 metadata와 객체 continuity로 재확인해야 한다.
- 객체 상대 거리, 상대 속도, actuator state, vehicle dynamics가 없으므로 physical safety는 `UNKNOWN`이다.

권장 마무리:

> 따라서 본 논문의 결과는 물리적 안전성 판정이 아니라, reasoning-augmented driving annotation의 학습 전 감사 및 검토 우선순위화 결과로 해석되어야 한다.

## 9. 용어 통일 계획

원고 전체에서 다음 용어를 일관되게 사용한다.

| Preferred term | Meaning |
|---|---|
| reasoning event | CoC 자연어 판단 문장 단위 |
| trusted event | quality/causal consistency를 통과한 reasoning event |
| intent | DECELERATE, STOP, YIELD 등 추상 제어 의도 |
| obligation | trusted event에서 생성되는 timed 판단-반응 요구사항 |
| response witness | actuator command가 아니라 ego motion에서 도출한 반응 증거 |
| episode | 같은 물리 scene 안에서 연결된 event sequence |
| scene boundary | scene 간 연속성이 증명되지 않는 경계 |
| mutation oracle | 의도적으로 삽입한 오류를 checker가 탐지하는지 확인하는 시험 장치 |

피해야 할 표현:

- “안전성을 증명한다”
- “제어 명령을 생성한다”
- “정답 trajectory”
- “모델체킹으로 자율주행 전체를 검증한다”
- “scene을 임의로 연결한다”

권장 표현:

- “protocol-level consistency를 검사한다”
- “추상 제어 의도를 timed obligation으로 변환한다”
- “ego motion 기반 response witness와 매칭한다”
- “학습 데이터 선별 및 검토 우선순위화에 사용한다”
- “연속성 증거가 있는 경우에만 long episode로 구성한다”

## 10. 우선순위별 실행 계획

### Phase 1: 핵심 주장 정리

- [ ] 초록 재작성
- [ ] 서론 첫 2쪽 재구성
- [ ] 연구 질문과 기여 재정의
- [ ] 논문의 claim scope 명시

### Phase 2: 문제 정의 및 방법론 정리

- [ ] obligation 정의, 튜플, 제약식 정렬
- [ ] CoC-to-obligation 변환 절차 정리
- [ ] UPPAAL 네트워크 설명을 trace replay + observer checking 중심으로 수정
- [ ] mutation oracle의 목적과 한계 명시

### Phase 3: 실험과 결과 재구성

- [ ] 단일 scene feasibility 결과를 직관 사례로 정리
- [ ] 94개 scene 선별 결과를 표로 정리
- [ ] failure mode 표 추가
- [ ] multi-scene pilot 결과의 범위와 한계 명시

### Phase 4: 논의 및 타당성 위협 보강

- [ ] 학습 데이터 활용 정책 표 추가
- [ ] closed-loop simulation과의 관계 정리
- [ ] 타당성 위협을 범위 선언형으로 수정
- [ ] physical safety `UNKNOWN` 해석 명확화

### Phase 5: 문체 및 형식 점검

- [ ] 논문답지 않은 표현 제거
- [ ] 한국어/영어 용어 혼용 정리
- [ ] 표와 그림의 용어 통일
- [ ] 모든 cross-reference, citation, LaTeX warning 확인
- [ ] 최종 PDF 시각 점검

## 11. 최종 목표 문장

원고 전체는 다음 한 문장으로 요약될 수 있어야 한다.

> 본 논문은 reasoning-augmented driving annotation을 E2E/VLA 학습 데이터로 사용하기 전에, 자연어 판단과 관측된 자차 반응 사이의 시간 계약 및 출처 정합성을 UPPAAL 기반 timed observer network로 검사하는 절차를 제안하고, CoC-Nusc 사례를 통해 반복 의미론, 기한 경계, 고아 반응, scene boundary 처리의 중요성을 보인다.
