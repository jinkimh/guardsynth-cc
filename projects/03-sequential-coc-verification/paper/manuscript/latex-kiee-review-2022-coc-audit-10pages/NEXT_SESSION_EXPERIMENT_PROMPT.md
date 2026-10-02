# 다음 세션 실행 프롬프트

아래 내용을 새 Codex 세션에 그대로 전달한다.

---

`/home/jinhyun/prj_ws/prj_jin/coc-modelchecking` 프로젝트에서 전기학회논문지 원고의
추가 실험을 설계·구현·검증하고, 실제 결과가 확보된 뒤 KIEE 복사본 원고를
보완해 주세요.

## 최종 목적

현재 논문은 개별 CoC 사건과 자차 속도 반응의 시간·출처 조건을 주로 검사합니다.
추가 실험의 목적은 같은 주행 클립 안에서 시간 순서대로 생성된 CoC를 지속되는
의무와 해제 조건으로 연결했을 때, 사건별 검사로 찾기 어려운 미해소 의무,
조기 해제 및 행동 충돌을 검출할 수 있는지 평가하는 것입니다.

주된 주장은 다음 범위로 제한합니다.

> 미리 선언한 CoC 계약 의미론 아래에서 상태 기반 검증은 사건별 검사로 찾기
> 어려운 연속 CoC의 시간적 모순을 검출하고 반례 경로를 제시할 수 있다.

보조적으로, 궤적으로 평가 가능한 사례에서 논리적 모순과 실행 조건 위반이 함께
나타나는지 탐색합니다. 자연어의 유일한 의미, 실제 교통법규 위반, 충돌 위험,
물리적 차량 안전 또는 학습 성능 향상을 주장하지 마세요.

## 반드시 먼저 읽을 파일

1. `docs/superpowers/specs/2026-08-06-sequential-coc-consistency-experiment-design.md`
2. `projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/main.tex`
3. `projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/01-introduction.tex`
4. `projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/06-experiments.tex`
5. `projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/07-results.tex`
6. `projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/sections/09-threats.tex`
7. `projects/03-sequential-coc-verification/experiments/logic/README.md`
8. `projects/03-sequential-coc-verification/experiments/logic/run_bounded_temporal_smt.py`
9. `artifacts/results/public/multiscene-chain/PATTERN_REPORT.md`
10. `artifacts/results/public/multiscene-chain/uppaal-loop-batch-all-strict-1s.json`
11. `artifacts/results/public/scene-continuity-audit.json`
12. `artifacts/results/public/nuscenes-official-mini-continuity-audit.json`

관련 `AGENTS.md`, 적용 가능한 skill 지침과 프로젝트 README도 먼저 확인하세요.

## 확인된 데이터 현황

- 전체 CoC: 743장면, 3,218사건
- CoC가 둘 이상인 장면: 677
- 전체 장면 내부 인접 사건 쌍: 2,475
- 로컬 자차 궤적과 겹치는 부분집합: 94장면, 403사건
- 이 부분집합에서 CoC가 둘 이상인 장면: 90
- 부분집합의 장면 내부 인접 사건 쌍: 309
- 자동 사전 선별상 정지·양보 뒤 가속·진행이 인접한 쌍: 21
- 이러한 전환을 가진 장면: 16
- 기존 장면 간 엄격 체인: 13체인, 29고유 장면, 16경계

이 값은 다시 계산하여 재현하고 `inventory.json`에 산출 근거와 함께 기록하세요.
정규식 후보 수를 사람 정답으로 취급하지 마세요.

## 핵심 범위 결정

- 주 실험 단위: 동일 장면 내부의 시간 순서가 있는 CoC 사건 창
- 주 자료: 자차 궤적이 있는 94장면
- 장면 간 13체인: 출처·경계 정책 보조 실험
- 초기 행동 범위: 정지, 양보·감속, 진행·가속, 속도 유지
- 차선 변경: 현재 표본이 적으므로 정량 주장 제외
- 필요한 증거가 없으면 `false`가 아니라 `UNKNOWN`

## 수행 단계

### 1단계: 재고·출처 게이트

1. 743장면/3,218사건 및 94장면/403사건 집계를 재현하세요.
2. 94장면에서 사건 순서, 타임스탬프, 궤적 존재와 사용 가능한 영상·프레임을 조사하세요.
3. 동일 장면 안의 사건은 연속 창으로 사용할 수 있지만, 서로 다른 장면은 공식
   출처 근거 없이 연결하지 마세요.
4. 결과를 새 경로의 `inventory.json`에 저장하세요.
5. 원천 데이터는 수정하지 마세요.

### 2단계: 공통 계약 중간표현

다음 필드를 가진 공통 표현을 구현하세요.

```text
scene_id, event_id, timestamp, trigger, obligation,
satisfaction_condition, release_condition,
permitted_next_action, evidence_known, provenance
```

상태는 `INACTIVE`, `ACTIVE`, `SATISFIED_WAIT_RELEASE`, `RELEASED`,
`VIOLATED`, `UNKNOWN`을 사용하세요. `known`과 `value`를 분리하여 증거 부재와
조건 거짓을 구분하세요.

`yield ... then accelerate`처럼 한 문장 안에서 순서가 명시된 행동을 동시 충돌로
잘못 해석하지 않도록 국면을 분리하세요. 공통 표현은 사건별 검사기, 상태형
Python 검사기와 UPPAAL 생성기가 함께 사용해야 합니다.

### 3단계: 자연 사건 창 구성

1. 의무 시작 사건과 뒤의 1~3개 사건을 하나의 창으로 구성하세요.
2. 94장면 전체를 선별하고, 정지·양보 후 진행 후보 16장면을 우선 포함하세요.
3. 장면 유형과 사건 수가 비슷한 정상 대조 창을 가능한 범위에서 구성하세요.
4. 같은 장면에서 나온 창은 독립 표본으로 세지 마세요.
5. 영상이나 객체 근거가 부족한 해제 조건은 `UNKNOWN`으로 남기세요.
6. 두 사람이 독립적으로 판정할 수 있는 블라인드 검토 자료와 CSV 스키마를 만드세요.
7. 평가자는 의무 시작, 충족, 해제, 다음 행동, 모순 유형, 증거 충분성을 판정하게 하세요.

목표는 평가 가능한 자연 창 20개 이상입니다. 충족하지 못하면 자연 결과를 사례
분석으로만 사용한다고 명시하세요.

### 4단계: 통제된 쌍대 모순 주입

사람이 확인한 정상 또는 명확한 상태 전이 창에 조건 하나만 바꾸어 다음 네 유형을
만드세요.

1. `HOLD_GO_CONFLICT`
2. `PREMATURE_RELEASE`
3. `ORDER_VIOLATION`
4. `STALE_OBLIGATION`

유형별 10쌍, 총 40쌍을 목표로 하세요. 원본과 변형은 장면, 사건 수, 나머지 내용,
시간 구조를 가능한 한 유지하세요. 원본과 변형을 독립 표본으로 세지 마세요.
주입한 정답 플래그를 검사기 입력으로 전달하면 안 됩니다. 검사기는 사건과 조건만
읽고 모순을 발견해야 합니다.

장면 간 `UNSUPPORTED_CARRYOVER`는 별도 보조 변형으로만 처리하세요.

### 5단계: 세 검사기 비교

동일한 중간표현에 다음을 적용하세요.

1. 각 사건을 독립적으로 보는 사건별 규칙 검사기
2. 활성 의무와 해제를 추적하는 상태형 Python 검사기
3. 시간·상태·경계와 반례를 검사하는 UPPAAL 관찰자

상태형 Python과 UPPAAL의 판정이 다르면 우열 결과로 보고하지 말고 구현 결함으로
조사하세요. 두 방법은 같은 의미론에서 일치해야 합니다. UPPAAL의 부가가치는
명세 표현, 상태 도달성, 조합 질의와 반례 경로로 평가하세요.

### 6단계: 궤적 계약 연결

근거가 충분한 사례에만 정지·양보 유지 속도, 가속 시작 시점, 필요한 감속 단계
술어를 적용하세요. 결과는 `COMPLIANT`, `VIOLATION`, `UNKNOWN`으로 구분하세요.
임계값은 결과를 보기 전에 선언하고 민감도 분석을 함께 수행하세요. 결과를 실제
사고, 위험 또는 물리 안전으로 부르지 마세요.

### 7단계: 평가

최소한 다음을 계산하세요.

- 자연 사례 판정 분포와 `UNKNOWN` 비율
- 두 검토자의 원판정 일치도와 Cohen's kappa
- 합의 정답 대비 정밀도, 재현율, F1과 신뢰구간
- 주입 유형별 검출률과 정상 원본 오탐률
- 사건별 검사 대비 상태형 검사의 추가 검출 수
- 상태형 Python과 UPPAAL 일치율
- 반례가 올바른 사건과 상태를 지목하는 비율
- 논리 판정과 궤적 계약 판정의 교차표
- 반복 정책, 제한 시간, 속도 임계값 민감도

작은 표본에서 p-value를 과장하지 말고 장면 단위 결과와 개별 반례를 함께 보고하세요.

### 8단계: 결과 고정과 논문 보완

먼저 별도 결과 보고서를 작성하여 실제 수치와 한계를 고정하세요. 그 후에만 다음
KIEE 복사본을 수정하세요.

```text
projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit
```

수정 원칙은 다음과 같습니다.

- 논문의 중심을 단일 사건 반응 검사에서 연속 의무의 시간적 일관성 검증으로 이동
- 기존 `134=125+4+5`는 단일 사건 민감도 보조 결과로 유지
- `282 모델/1,128 질의`는 변환 회귀시험으로 명확히 축소
- 13체인은 장면 경계·출처 보조 실험으로 유지
- 자연 사례와 인위적 모순 결과를 분리
- 실제로 발견되지 않은 자연 모순을 발견했다고 쓰지 않음
- 사람이 확인하지 않은 판정을 gold라고 부르지 않음
- 물리적 안전성과 학습 효과를 주장하지 않음

실험 결과에 따라 제목, 초록, 서론, 연구 질문, 방법, 실험, 결과, 논의, 한계와 결론을
일관되게 수정하세요. 기존 KIEE 스타일과 한국어 문체를 유지하고, 영어 용어는 꼭
필요한 경우에만 사용하세요.

## 새 구현과 결과 경로

```text
projects/03-sequential-coc-verification/experiments/sequential_coc/
artifacts/results/restricted/sequential-coc-consistency-v1/
```

기존 실험과 결과를 덮어쓰지 마세요. 제한 자료의 원문 CoC, 이미지, 비디오 또는
접근 토큰을 공개 결과에 복사하지 마세요. 새로운 토큰이나 자격 증명을 문서·로그·
명령줄에 노출하지 마세요.

## 검증과 작업 방식

- 구현 전 관련 테스트와 기존 데이터 형식을 읽으세요.
- 기능별 단위시험을 먼저 작성하고 실패를 확인한 뒤 구현하세요.
- 모든 집계는 재실행 가능한 스크립트에서 생성하세요.
- 기존 원고의 편집 무결성 시험을 유지하세요.
- 논문 빌드 후 경고, 참조, 그림·표 배치와 페이지 공백을 확인하세요.
- 완료를 주장하기 전에 전체 테스트, 실험 재실행, 결과 매니페스트와 PDF 빌드를
  검증하세요.
- 데이터나 영상이 부족하면 임의로 채우지 말고 `UNKNOWN`, `NOT_RUN` 또는 명확한
  차단 사유로 기록하세요.
- 진행 중에는 각 단계의 실제 수치와 해석 범위를 한국어로 짧게 보고하세요.

## 최종 산출물

1. 데이터 재고와 출처 보고서
2. 공통 계약 중간표현과 검사기
3. 자연 사건 창 및 블라인드 검토 자료
4. 통제된 원본·모순 쌍
5. 세 검사기 비교 결과와 UPPAAL 반례
6. 궤적 계약 탐색 결과
7. 재현 가능한 집계·그림·표와 SHA-256 매니페스트
8. 전체 실험 보고서
9. 실제 결과를 반영한 KIEE LaTeX 원고와 PDF
10. 수행하지 못한 항목과 남은 한계 목록

작업을 시작하기 전에 현재 파일과 데이터 상태를 조사하고, 구체적인 구현 계획을
제시한 뒤 진행하세요.

---
