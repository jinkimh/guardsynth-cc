# 국내 학술지 투고 보완 계획

작성일: 2026-08-01

## 목표

본 논문을 국내 학술지 투고 가능한 형태로 다듬기 위해, 주장의 범위를 과장하지 않으면서도 실험 결과와 방법론의 방어력을 높인다. 핵심 방향은 "자율주행 안전성 증명"이 아니라 "reasoning-augmented E2E 주행 데이터의 protocol-level consistency audit"로 논문 정체성을 고정하는 것이다.

## 보완 원칙

1. 안전성 주장은 좁게 유지한다.
   - 본 논문은 collision avoidance, TTC, safe distance, actuator-level control safety를 증명하지 않는다.
   - 검증 대상은 reasoning event, timed obligation, ego-motion response witness, provenance policy 사이의 정합성이다.

2. 실험 결과는 한눈에 읽히게 만든다.
   - 실험이 많으므로 각 실험의 목적, 입력, 핵심 결과, 주장 가능 범위를 표로 요약한다.
   - 134개 contract와 130개 detector-profile subset의 차이를 수식 형태로 명확히 설명한다.

3. UPPAAL 사용 이유를 방어적으로 설명한다.
   - 단일 deterministic deadline 검사는 script로도 가능함을 인정한다.
   - UPPAAL의 가치는 계산 자체가 아니라 obligation lifecycle, repeat semantics, provenance, mutation oracle, boundary policy를 하나의 formal artifact로 묶는 데 있음을 강조한다.

4. 5개 review candidate를 단순 실패가 아니라 유형화된 감사 결과로 제시한다.
   - 반복/stale reasoning, repeat-semantics flip, deadline boundary, visual grounding uncertainty, action-trajectory mismatch를 구분한다.

5. 관련 연구 차별점을 직접적으로 표현한다.
   - Reasoning/VLA 연구는 reasoning-action supervision을 만든다.
   - Closed-loop benchmark는 outcome을 평가한다.
   - STL/RSS/reachability는 물리 모델이 있을 때 안전 주장을 만든다.
   - 본 논문은 학습 데이터로 들어가기 전 reasoning-motion pair의 시간/출처 정합성을 검사한다.

6. 한계 절은 약점 나열이 아니라 범위 통제와 확장 조건으로 작성한다.
   - 각 한계 뒤에 본 논문에서 취한 대응 또는 향후 필요한 evidence를 명시한다.

## 수행 항목

| ID | 보완 항목 | 반영 위치 | 완료 기준 | 상태 |
| --- | --- | --- | --- | --- |
| P1 | 논문 정체성 문장 강화 | 서론, 결론 | protocol-level consistency audit라는 범위가 반복적으로 드러남 | 완료 |
| P2 | 관련 연구 차별점 강화 | 관련 연구 표 및 문단 | 기존 E2E/VLA, closed-loop, formal safety와 본 연구의 차이가 명확함 | 완료 |
| P3 | 실험 요약표 추가 | 실험 결과 | 8개 실험의 목적/입력/결과/주장 가능 범위가 한 표에 정리됨 | 완료 |
| P4 | 134/130/125/4/5 수치 구조 명시 | 실험 결과 | detector sensitivity subset이 왜 130개인지 즉시 이해 가능함 | 완료 |
| P5 | 5개 review candidate 유형화 | 실험 결과 | "실패 5개"가 아니라 "검토 유형 5개"로 읽힘 | 완료 |
| P6 | UPPAAL 필요성 방어 강화 | 방법, 논의 | script baseline과 model checking의 역할 분담이 명확함 | 완료 |
| P7 | 한계 절의 대응 문장 추가 | 한계와 향후 확장 | 각 한계가 논문 기여를 약화시키지 않고 해석 범위를 통제함 | 완료 |
| P8 | 용어 통일 | 본문, 표, 그림 | hard negative 등 과도한 표현 제거, review candidate 중심으로 통일 | 완료 |

## 반영 결과

- 서론에서 논문 범위를 `protocol-level consistency audit`로 고정하고, 물리 안전성 평가 전 단계의 데이터 정합성 gate임을 명시하였다.
- 관련 연구 절에 reasoning/VLA, closed-loop benchmark, formal safety analysis와 본 연구의 역할 차이를 직접적으로 추가하였다.
- 실험 결과 절에 8개 실험의 목적, 입력, 핵심 결과, 주장 가능 범위를 요약하는 표를 추가하였다.
- `134 = 125 + 4 + 5`, `130 = 125 + 5` 구조를 수식으로 명시하여 batch screening과 detector sensitivity의 모집단 차이를 설명하였다.
- 5개 review candidate를 반복/stale reasoning, repeat-semantics flip, deadline boundary, grounding/action mismatch 후보로 유형화하였다.
- UPPAAL 사용 이유를 deterministic 계산 대체가 아니라 synchronized monitor, mutation oracle, boundary policy를 포함한 formal artifact 구성으로 설명하였다.
- 한계 절의 각 항목에 본 논문에서 취한 대응 또는 해석 제한을 추가하였다.

## 기대 효과

- Reviewer가 "안전성을 증명하지 못한다"라고 지적하기 전에 논문 스스로 claim scope를 제한한다.
- Reviewer가 "script로도 되지 않나"라고 묻기 전에 UPPAAL의 역할을 formal artifact와 mutation oracle 측면에서 설명한다.
- 실험 결과가 산만한 나열이 아니라, 문제 정의에 대응하는 감사 결과로 읽힌다.
- 국내 학술지 기준에서 아이디어 중심의 주장보다 재현 가능한 데이터 감사 절차로 설득력이 높아진다.
