# Sequential CoC Verification 프로젝트 마일스톤

- 프로젝트: `sequential-coc-verification`
- 문서 계층: `02` 연구계획의 단계별 분해
- 기준 연구계획: [01_RESEARCH_PLAN_V01.md](01_RESEARCH_PLAN_V01.md)
- 실행 관리: [03_PROJECT_EXECUTION_TRACKER.md](03_PROJECT_EXECUTION_TRACKER.md)

## 1. 상태 규칙

`COMPLETE`는 근거 산출물이 있는 종료 단계, `READY_NEXT`는 현재 수행 가능한 단계,
`QUEUED`는 선행조건을 기다리는 단계다. mutation 검출률은 자연 오류 검출 정확도로
해석하지 않는다.

## 2. 마일스톤 원장

| ID | 마일스톤 | 상태 | 종료 근거 또는 gate |
|---|---|---|---|
| SQ-M00 | sequential obligation과 주장 경계 정의 | `COMPLETE` | 연구계획과 방법 선택 기록 |
| SQ-M01 | stateful checker와 timed contract pipeline | `COMPLETE` | 실험 코드와 재현 결과 |
| SQ-M02 | controlled mutation 및 경계 사례 평가 | `COMPLETE` | mutation·boundary 결과 |
| SQ-M03 | 제한된 Python–UPPAAL agreement 확인 | `COMPLETE` | 모델·query 재현 산출물 |
| SQ-M04 | protocol-level consistency 원고 완료 | `COMPLETE` | `MANUSCRIPT_READY` 상태 |
| SQ-M05 | KIEE 심사 대응 재분석·오류 주입 평가와 원고 보완 | `READY_NEXT` | 실험·11쪽 원고·세 답변서 검증 완료, 본 저장소 통합; 저자 검토와 투고 메타데이터 확인 대기 |
| SQ-M06 | 별도 E2E 학습·폐루프 확장 | `QUEUED` | 명시적 신규 범위 승인과 데이터 |

SQ-M06은 현재 원고의 완료 조건이 아니다. GuardSynth의 합성·grounding 작업을 이 프로젝트에
혼합하지 않는다.

## 3. 변경 규칙

연구 질문이나 성공 기준을 바꾸면 [01_RESEARCH_PLAN_V01.md](01_RESEARCH_PLAN_V01.md)을
먼저 개정한다. 원고 보완 계획은 해당 paper 디렉터리에서 관리하되 프로젝트 상태는 이
마일스톤 원장과 실행 추적표에 요약한다.
