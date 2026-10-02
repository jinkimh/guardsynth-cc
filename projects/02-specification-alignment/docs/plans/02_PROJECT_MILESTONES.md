# Specification Alignment 프로젝트 마일스톤

- 프로젝트: `specification-alignment`
- 문서 계층: `02` 연구계획의 단계별 분해
- 기준 연구계획: [01_RESEARCH_PLAN_V01.md](01_RESEARCH_PLAN_V01.md)
- 실행 관리: [03_PROJECT_EXECUTION_TRACKER.md](03_PROJECT_EXECUTION_TRACKER.md)

## 1. 상태 규칙

`COMPLETE`는 근거가 있는 종료 단계, `READY_NEXT`는 현재 수행 가능한 단계,
`QUEUED`는 선행조건을 기다리는 단계다. 초기 비교 결과는 main experiment 완료로 간주하지 않는다.

## 2. 마일스톤 원장

| ID | 마일스톤 | 상태 | 종료 근거 또는 gate |
|---|---|---|---|
| SA-M00 | 연구 간극과 주장 경계 정의 | `COMPLETE` | 연구계획과 논문 작성계획 |
| SA-M01 | 초기 표현 형식 3-seed 비교 | `COMPLETE` | 작성계획에 기록된 초기 증거 |
| SA-M02 | 비교 protocol·조건·지표 동결 | `READY_NEXT` | 사전 정의된 실험 protocol |
| SA-M03 | learning curve와 field-position 비교 | `QUEUED` | 통제된 학습량·위치 실험 |
| SA-M04 | raw logic와 executable verifier 분리 평가 | `QUEUED` | 결정론적 verifier 결과와 모델 결과 |
| SA-M05 | 일반화·모델 반복·통계 평가 | `QUEUED` | 사전 정의 지표와 반복 실험 |
| SA-M06 | 원고 및 재현 패키지 완료 | `QUEUED` | 주장 감사와 재현 가능한 산출물 |

## 3. 변경 규칙

표현 조건, 성공 기준 또는 주장 경계를 바꾸면
[01_RESEARCH_PLAN_V01.md](01_RESEARCH_PLAN_V01.md)을 먼저 개정한다. 실행 순서만 바꾸는
경우에는 이 원장과 실행 추적표를 함께 갱신한다.
