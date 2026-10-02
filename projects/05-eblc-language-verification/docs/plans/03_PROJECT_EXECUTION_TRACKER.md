# EBLC Language Verification 프로젝트 실행 추적표

- 프로젝트: `eblc-language-verification`
- 문서 계층: `03` 현재 실행 관리
- 기준 연구계획: [01_RESEARCH_PLAN_V01.md](01_RESEARCH_PLAN_V01.md)
- 전체 마일스톤: [02_PROJECT_MILESTONES.md](02_PROJECT_MILESTONES.md)
- 현재 상태: `RESEARCH_PLANNING`

## 1. 현재 단일 작업

`EB-M01`: EBLC, evidence-bearing contract, lifecycle contract, provenance-preserving compilation,
bidirectional specification mutation과 인접 용어에 대한 systematic prior-art 및 명칭 감사를
수행한다.

## 2. 완료 조건

- [ ] 검색 시점, 데이터베이스, 검색식, 포함·제외 기준을 기록한다.
- [ ] 가장 가까운 언어·도구를 feature와 evaluation 기준으로 비교한다.
- [ ] EBLC와 BCV 명칭 충돌 및 기존 사용을 확인한다.
- [ ] 신규하지 않은 구성요소와 검증 가능한 결합 기여를 분리한다.
- [ ] `GO`, `NARROW` 또는 `NO-GO`를 근거와 함께 판정한다.
- [ ] GO일 때만 EB-M02를 `READY_NEXT`로 전환한다.

## 3. 현재 금지 작업

- prior-art 결과 전에 “최초” 또는 독립 신규성을 원고에 확정
- benchmark를 보며 baseline과 success threshold를 반복 수정
- 플랫폼 코드를 이 프로젝트의 `src/`로 복사
- GuardSynth application 결과를 언어 자체의 독립 검증으로 사용

## 4. 예상 산출물

첫 산출물은 `docs/surveys/`의 독립 선행연구 서베이다. 평가 protocol과 실험은 EB-M01 판정
이후 각각 `docs/requirements/`와 `experiments/`에서 관리한다.
