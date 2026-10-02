# Specification Alignment 연구계획 v1

- 프로젝트: `specification-alignment`
- 문서 계층: `01` 최상위 연구계획
- 상태: `WRITING_PLAN`
- 하위 마일스톤: [02_PROJECT_MILESTONES.md](02_PROJECT_MILESTONES.md)
- 실행 관리: [03_PROJECT_EXECUTION_TRACKER.md](03_PROJECT_EXECUTION_TRACKER.md)
- 관련연구: [RELATED_WORK_SURVEY_V01.md](../surveys/RELATED_WORK_SURVEY_V01.md)
- 논문 작성계획: [WRITING_PLAN.md](../../paper/manuscript/WRITING_PLAN.md)

## 1. 연구 질문

자연어, 구조화 표현, raw logic, 실행 가능한 검증기 및 hybrid 명세 인터페이스는 AI 제어
모델의 해석과 결정론적 형식 실행에서 어떻게 다른가?

## 2. 범위

- 요구사항만 제공하는 조건부터 자연어, CNL, JSON, DSL, raw logic까지의 표현 비교
- 실행 가능한 verifier와 모델이 읽는 명세 텍스트의 역할 분리
- 데이터, 모델, 학습량과 필드 위치를 통제한 공정 비교
- 위반 회피와 목표 달성, 형식 실행 결과의 분리 보고

raw STL·논리 문자열을 모델에 제시했다는 이유만으로 형식 검증을 수행했다고 주장하지 않는다.
실행 가능한 검증 결과는 별도 deterministic component의 출력으로 관리한다.

## 3. 현재 근거와 간극

초기 3-seed 표현 비교 근거가 있으나, controlled learning curve와 executable-verifier 조건은
아직 완료되지 않았다. 현재 상태는 논문 작성 및 실험 protocol을 고정하는 단계다.

상세 연구 질문, 표현 조건과 완료 기준은
[논문 작성계획](../../paper/manuscript/WRITING_PLAN.md)에 기록되어 있다.

## 4. 성공 기준

1. 표현 조건 사이에서 정보량과 학습량을 통제한다.
2. raw logic text와 실제 verifier 실행을 별도 조건으로 평가한다.
3. 주요 지표와 해석 규칙을 main experiment 전에 동결한다.
4. learning curve, 일반화 및 executable-verifier 실험으로 초기 결과의 범위를 검증한다.
5. 증거가 없는 형식 보증이나 일반화 주장을 배제한다.

범위나 성공 기준을 바꿀 때는 이 문서를 먼저 개정하고 하위 관리 문서를 동기화한다.
