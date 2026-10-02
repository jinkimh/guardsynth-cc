# EBLC Language Verification 프로젝트 마일스톤

- 프로젝트: `eblc-language-verification`
- 문서 계층: `02` 연구계획의 단계별 분해
- 기준 연구계획: [01_RESEARCH_PLAN_V01.md](01_RESEARCH_PLAN_V01.md)
- 실행 관리: [03_PROJECT_EXECUTION_TRACKER.md](03_PROJECT_EXECUTION_TRACKER.md)

## 1. 상태 규칙

`COMPLETE`는 근거 artifact와 종료 gate가 있는 단계, `READY_NEXT`는 바로 수행할 다음 단계,
`QUEUED`는 선행조건을 기다리는 단계다. 기존 플랫폼 구현 완료를 독립 논문 평가 완료로
간주하지 않는다.

## 2. 마일스톤 원장

| ID | 마일스톤 | 상태 | 종료 gate |
|---|---|---|---|
| EB-M00 | 연구 소유권·질문·주장 경계 분리 | `COMPLETE` | 헌장, 계획, 분리 결정 기록 |
| EB-M01 | systematic prior-art 및 명칭 감사 | `READY_NEXT` | 검색 protocol, 비교표, 신규성 판정 |
| EB-M02 | baseline·benchmark·oracle protocol 동결 | `QUEUED` | versioned evaluation protocol |
| EB-M03 | 표현력·추적성 비교 | `QUEUED` | locked representation benchmark |
| EB-M04 | multi-target 의미보존 평가 | `QUEUED` | independent-oracle agreement report |
| EB-M05 | BCV 양방향 mutation 평가 | `QUEUED` | under/over/translation class별 결과 |
| EB-M06 | ablation·비용·강건성·실패 분석 | `QUEUED` | 통계와 failure taxonomy |
| EB-M07 | 외적 application case study | `QUEUED` | GuardSynth와 분리된 사례 연구 |
| EB-M08 | 원고·재현 패키지·내부 주장 감사 | `QUEUED` | submission-ready package |

## 3. Critical path

```text
EB-M01 → EB-M02 → {EB-M03, EB-M04, EB-M05} → EB-M06 → EB-M08
                                           └──────────→ EB-M07 (optional external case)
```

EB-M07은 중심 언어 결과의 선행조건이 아니다. EB-M01에서 독립 신규성이 성립하지 않으면
대규모 benchmark를 시작하지 않고 연구 범위를 engineering report 또는 좁은 compiler/BCV
기여로 전환한다.

## 4. 변경 규칙

연구 질문이나 성공 기준은 [01_RESEARCH_PLAN_V01.md](01_RESEARCH_PLAN_V01.md)에 먼저 기록한다.
플랫폼 기능 변경이 필요하면 project requirement를 versioning한 뒤 플랫폼 소유 경로에서
구현하고, 이 원장에는 평가 의존성만 기록한다.
