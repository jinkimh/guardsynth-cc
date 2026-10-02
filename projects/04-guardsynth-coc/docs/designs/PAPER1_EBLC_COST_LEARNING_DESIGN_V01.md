# EBLC 비용 기반 추가 학습 비교 설계

- project_id: `guardsynth-coc`
- 날짜: 2026-09-29
- 상태: `PROTOCOL_FROZEN_QUEUE_WAITING_FOR_UPSTREAM`
- 사용자 승인: SFT 비교 유지 후 같은 추가 학습 예산의 SFT 대 EBLC 비용 반영 비교 제안에 “네..그렇게 게속 진행”
- 상위: [연구계획](../plans/01_RESEARCH_PLAN_V02.md), [범위 결정](../decisions/PAPER1_METHOD_PRESERVATION_AND_LABELING_DECISION_V01.md)
- 선행: [추가 학습·평가 설계](PAPER1_TEMPORAL_DIVERSITY_DESIGN_V01.md)

## 1. 연구 질문과 실행 순서

동일한 P2 checkpoint에서 같은 양을 더 학습할 때, 정답 모방만 계속한 경우보다 EBLC 위반 비용을
직접 반영한 경우 미사용 조건의 위반이 줄고 정상 진행이 유지되는가?
이는 검증기의 존재가 CNL 학습 효과를 높인다는 주장이 아니라 명시적인 목적함수 변경의 효과다.
네 후보의 비용을 모두 구할 수 있는 supervised expected-cost regularization이며 정책경사 RL,
실차/시뮬레이터 closed-loop RL 또는 추론 시 행동 차단기로 표기하지 않는다.
비용 조건은 후보별 제약 판정을 추가 감독 신호로 사용한다. 따라서 결과가 좋아져도 정형 언어
표현 자체가 더 우수하다거나 검증만 실행해서 모델이 좋아졌다는 인과 주장으로 바꾸지 않는다.

진행 중인 `temporal-expansion-learning-2026-09-29-001`의18회 학습·평가는 수정/중단하지 않는다.
추가 비용 실험은 전체 run이 COMPLETE이고 manifest·세 P2 adapter를 검증한 뒤 실행한다.
FAILED이면 자동 재학습·다른 checkpoint 대체 없이 원인을 보고한다. GPU2/4가 유휴일 때만 사용한다.
미래 checkpoint 해시는 프로토콜에 꾸며 넣지 않는다. 부모 run/seed/최종 checkpoint 선택 규칙을
먼저 고정하고 실제 해시는 실행 전에 별도 입력 연결 기록으로 묶는다.

## 2. 두 조건과 고정 예산

| 항목 | Continued SFT | SFT + EBLC cost |
|---|---|---|
| 시작점 | 각 seed의 동일한 확장 실험 최종 P2 adapter | 왼쪽과 동일 |
| 입력 | 기존 학습960행, P2 CNL | 왼쪽과 동일 |
| 정답 모방 손실 | assistant token CE | 같은 CE |
| 추가 비용 계수 | 0 | 1 |
| 반복/갱신 | 1epoch,60 optimizer updates | 왼쪽과 동일 |
| batch/누적/lr | 2/8/0.0002 | 왼쪽과 동일 |
| seeds | 42,17,123 | 왼쪽과 같은 paired seed |

optimizer는 양쪽 모두 새로 시작한다. LoRA 구성·학습 가능한 파라미터·dropout·정밀도·셔플 순서를
동일하게 유지하고 학습 직전 RNG도 다시 맞춘다. 두 조건 모두 비용 진단을 계산하되 계수만 다르게
하여 데이터 접근과 연산 차이를 작게 한다. 동일 갱신 수는 정확히 같은 벽시계 비용을 의미하지
않으므로 실제 시간/토큰/학습량도 기록한다. 중간 평가에 따른 조기 종료나 추가 epoch는 없다.

## 3. 비용과 구현 검증

각 후보 a의 비용은 `1 × EBLC 위반 + 0.25 × 불필요 정지`로 고정한다.
EBLC 위반은 장면 clear 시각·후보 entry 시각·진입 여부를 Core/Z3에 연결한 UNSAT 판정이다.
SAT/UNSAT를 독립 환경 규칙과 대조하고 UNKNOWN/불일치는 안전으로 처리하지 않고 실패로 보고한다.
불필요 정지는 제약을 지키며 진행 가능한 후보가 있는데 horizon 내내 정지하는 후보를 뜻한다.
참조 정답이나 위치상 role 문자열에서 비용을 역생성하지 않는다.

추가 손실은 첫 assistant 행동 토큰 위치의 A/B/C/D logits를 네 후보 안에서 정규화한 확률과
위 비용의 내적이다. 전체 손실은 `CE + 계수 × 기대 비용`이다. 단일 문자 토큰의 실제 ID,
causal logits 위치(정답 토큰 바로 이전), assistant-only mask, batch 대응을 실제 processor로 점검한다.
네 문자에 조건부인 비용만으로 출력 형식을 보장하지 않으므로 CE를 유지하고 무효 응답도 분모에 남긴다.
추가 비용이 잘못된 후보의 확률을 내리는 방향으로 미분되는지, 계수0이 CE와 동일한지,
라벨 회전에 불변인지, 참조 정답을 바꿔도 비용이 변하지 않는지 회귀 검사한다.

위 계수는 결과 전 정한 탐색적 연구 설정이며 물리적 안전 비용이나 최적값이 아니다.
계수 탐색은 이번 run에 포함하지 않는다. 실패하면 새 프로토콜 없이 결과를 보며 바꾸지 않는다.

## 4. 새로운 평가와 분석

기존 학습6.0–9.9초·검증10.0–10.9초·시험11.0–11.9초와 별도로 clear 시각12.0–12.9초를 예약한다.
기존3개 후보 패턴×4라벨 회전×2계약으로 각240행을 구성한다. canonical, 같은 의미의 paraphrase,
미학습 대기시간0.8/1.8초(+0.3초 후보 offset 변환)의 세 묶음을 새 예측 전에 고정한다.
각 묶음의 입력 이미지·prompt·참조·계약·해시를 보존하고 기존 test를 학습 자료로 편입하지 않는다.
비용 학습에 앞서 시작 P2 adapter도 같은 fresh 묶음으로 평가하여 ceiling과 단순 추가 학습 효과를 구분한다.

새 비교는6개 추가 학습 checkpoint와4,320예측, 시작점은3개 기존 checkpoint와2,160예측이다.
10개 고유 이미지의 파생 묶음이며6,480개 독립 장면이 아니다. 예전 진단을 보고 설계한 후속 실험임을
공개하고 원 사전등록 확인 실험으로 재표기하지 않는다.

기존7지표와 coverage를 모두 보고한다. 주 비교는 비용 조건-continued SFT의 canonical 결과이며
다음을 탐색적 point criteria로 함께 확인한다.

- 평균 위반률 차이 ≤ -0.02.
- 제약 준수 목표 완료율 및 계약쌍 정확도 차이 각각 ≥ -0.02.
- deadlock 및 무효 응답률 차이 각각 ≤ +0.01.

세 seed별 수치, 평균/표준편차, 전체 계약쌍·패턴·회전을 함께 보존하는 clear 시각 그룹
paired bootstrap 2,000회(고정 seed20260929)의95% 구간을 제시한다. point criteria 통과를 정식
비열등성/동등성 증명으로 쓰지 않는다. 개선 여지가 없는 ceiling 또는 불확실한 결과는 별도
INCONCLUSIVE 설명을 유지한다. 일반화 묶음의 악화·희생된 정상 진행·무효 응답도 빠짐없이 보고한다.
보상 계산에 쓰인 명세의 정확성 한계는 남으며 실제 도로 안전을 보장하지 않는다.

## 5. 완료 기준

- [x] 새 비용·평가 입력·분석 프로토콜 동결: `temporal-cost-protocol-2026-09-29-001`
- [x] 비용/토큰 위치/미분/계수0/독립 정답/분할 회귀 검사 및 실제 processor 확인: 비용·queue 테스트16개 통과
- [ ] 부모18 fits COMPLETE 및3개 P2 checkpoint 해시 연결
- [ ] 두 조건×3seed의60 updates·추가 checkpoint·전 평가 원응답 확보
- [ ] paired 분석, 기준 미달 및 한계 포함 보고서·원고 반영

자동 실행: tmux `guardsynth-temporal-cost-20260929`,
`temporal-cost-queue-2026-09-29-001/RESULT.json`에서 부모18 fits 완료를 대기한다.
그 뒤 실제 checkpoint 해시를 연결하고 유휴 GPU2/4에서
`temporal-cost-learning-2026-09-29-001`을 실행한다. 대기 등록은 비용 학습 완료가 아니다.
실행기: `experiments/paper1_cnl_learning/train_temporal_cost.py`,
대기 실행기: `experiments/paper1_cnl_learning/run_temporal_cost_queue.py`.
