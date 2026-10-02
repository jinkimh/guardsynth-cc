# EBLC 학습 효과 평가의 필수 마일스톤 반영 결정

- project_id: `guardsynth-coc`
- 결정 ID: `GS-P5-LEARNING-SCOPE-001`
- 결정일: 2026-09-06
- 상태: `APPROVED_SCOPE_NOT_EXECUTED`
- 승인 근거: 연구 책임자의 학습 효과 실험 누락 원인 분석 및 마일스톤 반영 요청
- 상위 문서: [연구계획 v2.1](../plans/01_RESEARCH_PLAN_V02.md)
- 실행 계약: [M18 학습 효과 요구사항](../requirements/M18_EBLC_LEARNING_EFFECT_REQUIREMENTS_V01.md)
- 후속 v2.3: [논문/개발 분리 결정](PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md)이 primary를
  preference-only에서 EBLC→CNL→CoC supervision SFT로 변경하고 runtime/Alpamayo를 2차로 이관함.
  실제 학습·보고 필수성과 부정 결과 정직성은 유지하며 아래는 최초 보완 결정의 이력

## 1. 누락 원인과 확인 범위

현행 문서 대조로 확인한 계획 분해의 누락이다. 현재 canonical 계획 파일은 작업트리의
untracked 경로이고 해당 경로의 Git log에서 변경 이력이 조회되지 않았다. 따라서 특정 작성자,
커밋 또는 변경일이 누락을 만들었다고 판정하지 않는다.

| 확인한 문서 근거 | 확인되는 사실 | 원인 해석 |
|---|---|---|
| 연구계획 §1.1 | 선행 Safety-Constrained CoC는 주어진 가드의 학습, 본 연구는 가드의 적용성·근거성·타당성으로 역할을 구분 | 자동 생성 가드를 실제 학습 효과로 연결하는 응용 검증이 선행 연구에 이미 포함된 것으로 취급되기 쉬운 경계 |
| 연구계획 §7, §10 | downstream에 CoC 학습을 명시하고 학습 실험 3-seed 원칙을 둠 | 학습 의도 자체가 없었던 것은 아님 |
| RQ5/H5, E4, P5 | 위반·진행성 endpoint와 독립 evaluator는 있지만 가중치 업데이트/학습 신호/대조군이 없음 | 추론 시 계약 적용과 모델 학습 효과가 분리된 실험으로 정의되지 않음 |
| RQ7/H7, E5, M19 | prompt, verifier, reranker, monitor/shield에 태스크가 집중됨 | 학습 효과를 맡는 작업 패키지가 생기지 않음 |
| M20 종료 gate | main evaluation·전문가 효용·논문 산출물을 요구하지만 학습 비교 보고서는 요구하지 않음 | 논문 주장과 실험 산출물 간 추적성 부족으로 누락을 검출하지 못함 |

위 해석은 문서 구조에서 도출한 분석이며 작성자의 내적 의도에 대한 주장이나 역사적 증명이
아니다. Project 01의 수작업/합성 가드 학습 결과는 Project 04에서 자동 생성한 가드의 학습
효과를 대신하지 않는다. 기존 모델에 외부 shield를 붙인 성능 향상 역시 가중치 학습의 효과와
구분해서 측정해야 한다. 앞선 설명에서 학습 의도가 전혀 없다고 단정한 것은 잘못이었다.

## 2. 결정과 배치

기존 번호를 유지하면서 M18을 **EBLC 기반 학습 효과 및 독립 closed-loop 평가**로 확장한다.
필수 하위 단계 `M18-S02`~`M18-S05`에 `GS-P5-LEARNING-001` / `E4-L`을 부여한다.
M17의 생성 품질 검증과 source gate를 통과한 제약으로 학습 신호를 만들고, 동일한 모델·장면·
후보·학습 예산에서 학습한 모델을 공통 locked test로 평가한다.

- M16: source/gold 및 검토 결과 확보. 학습 데이터 전체를 60 pilot 장면으로 제한하지 않는다.
- M17: 생성기 품질과 abstention 검증, 학습 label producer의 version 동결.
- M18: 예산 통제 학습 비교 및 외부 shield 없는 primary 평가, 별도 shield 평가.
- M19: Alpamayo 추론 적용/이식성 평가. Alpamayo 가중치를 실제 학습할지는 모델·자원·라이선스
  feasibility를 기록해 정한다. 소형 모델 결과를 Alpamayo 학습 효과로 주장하지 않는다.
- M20: E4-L 실제 실행 보고서와 효과/부정 결과를 논문에 통합하는 필수 종료 gate.

학습 비교 **수행과 보고는 필수**이고 긍정 결과는 미리 보장하지 않는다. 미실행은
`NOT_EVALUATED`이며 M20 완료 근거가 아니다. 적절히 수행한 부정/불확실 결과는 보고하고
학습 개선 주장을 축소한다. 기존 E4 runtime 위반 감소 목표를 학습 효과로 재표기하지 않는다.

## 3. 재발 방지

논문의 각 핵심 주장에 RQ/H → milestone/work package → 고정 대조군 → metric → 실제
artifact의 연결을 둔다. M20은 이 대응표에서 미실행 항목이 있는지를 확인한다. 구현/프로토콜
완료와 실제 실험 완료를 별도 상태로 보고하며, 인터페이스 테스트나 SAT 결과를 학습 성능
근거로 계산하지 않는다.
