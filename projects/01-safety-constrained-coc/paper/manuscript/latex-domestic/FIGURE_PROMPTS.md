# 국내 저널 LaTeX 원고 그림 프롬프트

그림 파일을 만들기 전까지 `main.tex`은 컴파일 가능한 placeholder를 표시한다. 완성된 그림은 `figures/`에 저장하고 해당 `\placeholder{...}`를 `\includegraphics`로 교체한다.

## Figure 1 — Requirement와 Safety-Constrained CoC

학술 논문용 흰 배경 벡터 다이어그램. 왼쪽에는 동일한 교차로 장면과 “Yield to the pedestrian, then proceed”라는 Requirement CoC를 배치한다. 중앙에는 세 개의 trajectory 후보를 그린다: 정지선을 넘는 빠른 trajectory는 빨간색, 정지선 전에 부드럽게 정지하는 trajectory는 녹색, 지나치게 일찍 정지하는 trajectory는 회색. 위쪽에는 Requirement-only CoC가 세 후보를 모두 목표 충족으로 보는 모습을 표시한다. 아래쪽에는 `stop_offset <= 0`, `peak_decel <= d_max`, `peak_jerk <= j_max` Safety Guard가 빨간 후보를 제거하고 녹색 후보를 선택하는 모습을 표시한다. 오른쪽에는 “goal preserved + guard compliant”를 강조한다. IEEE/Elsevier 스타일, 절제된 파랑ㆍ녹색ㆍ빨강 팔레트, 16:9 가로형, 선명한 벡터 텍스트.

## Figure 2 — 학습 및 검증 파이프라인

학술 논문용 파이프라인. 왼쪽의 scene image, Requirement CoC, Execution Guard 세 입력이 Qwen3-VL-2B-Instruct + LoRA 블록으로 들어간다. 모델은 A/B/C/D trajectory candidate를 선택한다. 아래의 독립 verifier가 stop offset, speed, deceleration, jerk, minimum gap, entry time을 검사한다. 오른쪽에는 Guard Violation, Safe Goal Completion, Deadlock, Contract-Swap Pair Accuracy를 출력한다. 학습 branch에는 correct contract-target pairing과 shuffled control을 나란히 표시한다. 자연어는 파랑, verifier는 짙은 회색, admissible은 녹색, violation은 빨강.

## Figure 3 — Paired-contract 예

두 행으로 구성된 논문용 비교 도식. 두 행은 완전히 동일한 차선 변경 장면과 동일한 네 후보를 가진다. 첫 행의 permissive contract는 minimum gap >= 5.5m이고 early-continue 후보가 선택된다. 둘째 행의 restrictive contract는 minimum gap >= 9.0m이고 abort-then-retry 후보가 선택된다. 바뀐 것은 contract threshold뿐임을 중앙 세로 점선과 “same scene / same candidates”로 강조한다. Requirement-only 모델은 두 행에 같은 답을 내고 Safety-Constrained CoC 모델은 답을 올바르게 전환한다.

## Figure 4 — 핵심 결과 패널

3개 패널의 저널용 결과 그림. 패널 A는 R1의 base CoC 대비 문장 추가 trajectory 변화 0.263m와 hold-versus-opposite 차이 0.008m를 비교한다. 패널 B는 시간적 3-seed 실험의 Requirement, Inline NL, Separate NL, Shuffled, Logic 조건별 Guard violation과 Safe Goal Completion을 error bar와 함께 표시한다. 패널 C는 다중 maneuver standard와 hard test에서 Requirement, Safety-Constrained, Shuffled의 contract-pair accuracy를 비교한다. 색맹 친화 팔레트, 3D 효과 없음, 벡터 출력.

## Figure 5 — 후속 typed-contract 아키텍처

자연어 Safety-Constrained CoC가 Guard compiler로 들어가 type, operator, value, unit, fallback 필드가 되고, unit normalization 뒤 deterministic trajectory verifier 또는 runtime shield로 전달되는 구조. VLM 학습 인터페이스와 제어/검증 계층 사이에 명확한 경계를 표시한다. 아래에는 cm 단위 변환 오류가 compiler/normalizer에서 차단되는 작은 예를 넣는다. 흰 배경, 논문용 블록 다이어그램.

## 선택 Figure 6 — Release reversal

시간축 기반 개념도. t0에서 conflict zone clear로 provisional release, t0+0.6s에 ego 진입 시작, t0+0.8s에 보행자 또는 교차 차량 재등장. 위쪽의 monotonic phase APPROACH→HOLD→RELEASED가 위험 재등장을 처리하지 못하는 모습을 빨간 경고로 표시한다. 아래에는 revocable contract가 RELEASED에서 HOLD로 되돌아가고 runtime shield가 제동하는 모습을 그린다. Current-state shield는 미래 재등장을 놓칠 수 있고 predictive occupancy가 필요하다는 inset을 추가한다.
