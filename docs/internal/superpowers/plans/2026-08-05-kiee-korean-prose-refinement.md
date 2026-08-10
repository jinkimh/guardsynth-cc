# KIEE Korean Prose Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** KIEE 심사용 복사본의 한국어 제목ㆍ본문ㆍ표ㆍ캡션을 정확하고 이해하기 쉬운 문장으로 고치되, 영어 요소와 연구 내용은 그대로 보존한다.

**Architecture:** 편집 전 상태에서 수치ㆍ수식ㆍ인용ㆍ레이블ㆍ영문 캡션과 비편집 파일의 기준값을 저장하고 자동 회귀 검사를 먼저 만든다. 이후 개념 설명, 데이터ㆍ방법, 실험ㆍ결과, 논의ㆍ결론의 네 묶음으로 한국어를 편집하며 각 묶음마다 언어 검토와 의미 보존 검토를 별도로 수행한다. 마지막에는 논문 전체의 용어를 통일하고 LaTeX 빌드 및 PDF 전 페이지를 확인한다.

**Tech Stack:** LuaLaTeX, BibTeX, Python 표준 라이브러리 `unittest`, KIEE LaTeX 양식, TikZ, Noto Serif CJK KR

## Global Constraints

- 수정 대상은 `papers/demestic-journal/latex-kiee-review-2022-coc-audit`뿐이다.
- 원본 `papers/demestic-journal`에서 대상 하위 디렉터리를 제외한 파일과 `papers/paper1-safety-constrained-coc/latex-kiee-review-2022`는 수정하지 않는다.
- 한국어 제목, 10개 절의 한국어 본문, 표 안의 한국어 문구, 한국어 캡션만 편집한다.
- 영문 제목, 154단어 영문 초록, 영문 핵심어 6개, 영문 캡션 23개, 참고문헌은 변경하지 않는다.
- 연구 질문 RQ1--RQ4의 의미, 모든 수치ㆍ단위ㆍ수식ㆍ임계값ㆍ집계 관계, 인용ㆍ레이블, 실험 조건ㆍ결과와 주장 범위를 보존한다.
- 134개 후보의 비독립성, `125+4+5`, `282/1,128` 시험의 직렬화 한계, 별도 구현 13개 체인의 기본 동작 확인 범위, 반개구 조건 `r<D`, 상류 버전 출처 한계를 삭제하거나 약화하지 않는다.
- `감사`를 일괄 치환하지 않는다. 계약 충족 여부에는 `검증`, 데이터 상태 확인에는 `점검`, 사람이 다시 볼 항목에는 `검토`를 사용한다.
- 독자가 처음 접하는 개념은 쉬운 문장으로 풀어 쓴 뒤 짧은 용어를 사용한다.
- 한 문장에는 핵심 주장 하나를 두고, 입력--검사--결과--의미의 관계를 분명히 쓴다.
- Git 메타데이터가 없으므로 저장소를 초기화하거나 커밋하지 않는다. 기준 해시, 작업 보고서와 독립 검토 결과로 변경 이력을 남긴다.

---

### Task 1: 편집 기준값과 회귀 검사 구축

**Files:**
- Create: `.superpowers/sdd/2026-08-05-kiee-korean-refinement/pre-edit-target.sha256`
- Create: `.superpowers/sdd/2026-08-05-kiee-korean-refinement/source-before.sha256`
- Create: `.superpowers/sdd/2026-08-05-kiee-korean-refinement/template-before.sha256`
- Create: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/tests/editorial_baseline.json`
- Create: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/tests/test_korean_editorial_integrity.py`
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/Makefile`
- Create: `.superpowers/sdd/2026-08-05-kiee-korean-refinement/task-1-report.md`

**Interfaces:**
- Consumes: 현재 KIEE 복사본과 기존 `tests/test_kiee_format.py`.
- Produces: 이후 모든 편집 작업이 실행할 `test_korean_editorial_integrity.py`와 편집 전 기준 JSONㆍ해시.

- [ ] **Step 1: 편집 전 보존 해시를 기록한다**

대상 전체, 대상 하위 디렉터리를 제외한 원본, 참조 양식의 정렬된 SHA-256 목록을 만든다. 원본 목록을 만들 때 중첩된 KIEE 대상이 포함되지 않도록 명시적으로 제외한다.

Run:

```bash
mkdir -p .superpowers/sdd/2026-08-05-kiee-korean-refinement
find papers/demestic-journal/latex-kiee-review-2022-coc-audit -type f -print0 | sort -z | xargs -0 sha256sum > .superpowers/sdd/2026-08-05-kiee-korean-refinement/pre-edit-target.sha256
find papers/demestic-journal -maxdepth 2 -type f ! -path '*/latex-kiee-review-2022-coc-audit/*' -print0 | sort -z | xargs -0 sha256sum > .superpowers/sdd/2026-08-05-kiee-korean-refinement/source-before.sha256
find papers/paper1-safety-constrained-coc/latex-kiee-review-2022 -type f -print0 | sort -z | xargs -0 sha256sum > .superpowers/sdd/2026-08-05-kiee-korean-refinement/template-before.sha256
```

Expected: 세 목록이 생성되고 원본 목록에는 `latex-kiee-review-2022-coc-audit` 경로가 없다.

- [ ] **Step 2: 의미 보존 기준 JSON을 생성한다**

Python 표준 라이브러리만 사용하여 현재 `main.tex`과 10개 절에서 다음 항목을 추출해 `editorial_baseline.json`에 저장한다.

- 정확한 영문 제목, 초록, 핵심어 순서
- `\bifigcaption`과 `\bitablecaption`의 영문 두 번째 인자 23개
- 절별 `\cite{}`, `\label{}`, `\ref{}` 키의 정렬된 다중집합
- 절별 숫자 토큰과 단위 토큰의 정렬된 다중집합
- 절별 수식 환경과 인라인 수식 원문
- `references.bib`, 다섯 TikZ 그림, 스타일, 글꼴, 로컬 PGF 라이선스 파일의 SHA-256

JSON에는 추출 시각을 넣지 않는다. 기준 파일이 결정적으로 재생성되어야 한다.

- [ ] **Step 3: 보존 회귀 검사를 먼저 작성한다**

`test_korean_editorial_integrity.py`에 다음 검사를 구현한다.

```python
class KoreanEditorialIntegrityTests(unittest.TestCase):
    def test_english_front_matter_matches_baseline(self): ...
    def test_english_bilingual_captions_match_baseline(self): ...
    def test_citations_labels_refs_numbers_units_and_math_match_baseline(self): ...
    def test_non_prose_assets_match_baseline_hashes(self): ...
    def test_original_source_and_template_manifests_remain_unchanged(self): ...
    def test_compiled_korean_prose_has_no_disallowed_literal_terms(self): ...
```

마지막 검사는 컴파일되는 `main.tex`과 10개 절에서 다음 한국어 직역 표현을 찾으면 실패하도록 한다.

```python
DISALLOWED = {
    "시간·출처 계약 감사",
    "감사 계약",
    "응답 계보",
    "반복 주석",
    "후보 시간 의무",
    "자차 움직임 응답 증거",
    "음성 대조",
    "스모크 테스트",
    "스모크 출력",
}
```

`라우팅`, `코호트`, `감사` 단독 문자열은 문맥 판정이 필요하므로 자동 금지하지 않고 최종 수동 검사 목록으로 출력한다.

- [ ] **Step 4: 새 검사가 편집 필요성을 정확히 드러내는지 확인한다**

Run:

```bash
python3 -m unittest -v \
  papers/demestic-journal/latex-kiee-review-2022-coc-audit/tests/test_korean_editorial_integrity.py
```

Expected: 영어ㆍ수치ㆍ수식ㆍ인용ㆍ비편집 자산 보존 검사는 통과하고, 금지된 직역 표현 검사는 현재 원고의 실제 경로와 표현을 보여 주며 실패한다.

- [ ] **Step 5: 기본 테스트 명령에 편집 회귀 검사를 연결한다**

`Makefile`의 `test` 대상이 기존 형식 검사와 새 편집 무결성 검사를 모두 실행하도록 수정한다. `make test`의 실패 원인은 금지된 한국어 표현 검사뿐이어야 한다.

- [ ] **Step 6: Task 1 보고서를 작성한다**

기준 파일 목록, 의도적으로 실패하는 표현 검사, 나머지 보존 검사의 통과 상태를 `task-1-report.md`에 기록한다. Git을 사용할 수 없었다는 사실도 적는다.

---

### Task 2: 제목ㆍ서론ㆍ문제 정의의 개념 설명 개선

**Files:**
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/main.tex`
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/01-introduction.tex`
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/04-problem.tex`
- Create: `.superpowers/sdd/2026-08-05-kiee-korean-refinement/task-2-report.md`

**Interfaces:**
- Consumes: Task 1의 기준 JSON과 회귀 검사, 승인된 용어표.
- Produces: 논문 전체가 따를 `검증 조건`, `반복 CoC 사건`, `차량 반응`, `연결 관계`의 쉬운 정의.

- [ ] **Step 1: 한국어 제목을 직접적인 표현으로 바꾼다**

한국어 제목에서 `감사`를 `검증`으로 바꾸고, 제목만 읽어도 저장된 CoC 데이터의 시간 조건과 출처 연결을 검사하는 연구임을 알 수 있게 한다. 영문 제목은 그대로 둔다.

Target:

```tex
\kieekoreantitle{추론 보강형 E2E 자율주행 데이터의 시간ㆍ출처 계약 검증: CoC-Nusc와 UPPAAL 기반 분석}
```

- [ ] **Step 2: 서론의 첫 설명을 쉬운 문제 제기로 다시 쓴다**

`01-introduction.tex`에서 다음 순서로 문단을 재구성한다.

1. CoC가 기록된 행동의 이유를 설명하지만 안전을 보장하지는 않는다는 점
2. 같은 의도의 CoC가 여러 번 나타날 때 어느 시점을 기준으로 반응 시간을 계산할지 정해야 한다는 점
3. 차량 반응이 어떤 CoC에 대응하는지와 서로 다른 장면을 연결해도 되는지 확인해야 한다는 점
4. 본 연구가 이 세 가지를 시간ㆍ출처 검증 조건으로 표현한다는 점

`응답 계보`는 `CoC 사건과 차량 반응의 연결 관계`, `후보 시간 의무`는 `연구자가 분석을 위해 임시로 설정한 시간 조건`으로 풀어 쓴다.

- [ ] **Step 3: 동기 사례를 단계별 설명으로 나눈다**

`scene-0001` 설명은 한 문장에 정책ㆍ시간ㆍ판정을 모두 넣지 않는다. 다음 네 문장 단위로 나눈다.

- CoC 발생 시점과 반복 시점
- 실제 감속 시작 시점
- 최초 사건을 유지하는 정책의 계산 결과
- 반복 사건부터 다시 계산하는 정책의 결과와 이 사례가 안전 판정이 아니라는 해석

- [ ] **Step 4: RQ와 기여 문장을 같은 용어로 정리한다**

RQ1--RQ4와 기여 목록에서 `감사 판정`, `응답 계보`, `음성 대조`, `라우팅`, `스모크`를 각각 `검증 결과`, `연결 관계`, `잘못된 장면 연결 차단 시험`, `처리 유형 분류`, `기본 동작 확인`으로 바꾼다. 각 RQ는 무엇을 입력하고 무엇을 확인하는지 한 문장 안에서 드러나게 쓴다.

- [ ] **Step 5: 문제 정의를 쉬운 한국어로 재구성한다**

`04-problem.tex`에서 수식은 그대로 두고 수식 전후 설명만 고친다.

- `audit contract`는 첫 등장에 `CoC와 차량 반응이 정해진 시간 안에서 연결되는지를 확인하기 위한 검증 조건`으로 설명한다.
- `candidate deadline`은 안전 규정이 아니라 분석용 임시 제한 시간임을 바로 밝힌다.
- `Pending/Responded/Failed`는 각각 `반응 대기`, `반응 확인`, `시간 안에 반응을 확인하지 못함`으로 설명한다.
- PASS/FAIL이 안전/위험을 뜻하지 않는다는 문장을 판정 정의 직후에 둔다.

- [ ] **Step 6: Task 2 의미 보존 검사를 실행한다**

Run:

```bash
python3 -m unittest -v \
  papers/demestic-journal/latex-kiee-review-2022-coc-audit/tests/test_kiee_format.py \
  papers/demestic-journal/latex-kiee-review-2022-coc-audit/tests/test_korean_editorial_integrity.py
```

Expected: 수치ㆍ수식ㆍ인용ㆍ영문 보존 검사는 통과한다. 아직 다른 절에 남은 금지 표현만 실패 목록에 나타난다.

- [ ] **Step 7: 한국어와 기술 내용의 독립 검토를 수행한다**

한 검토자는 문장 호응, 한 번에 읽히는지, 용어 자연스러움만 본다. 다른 검토자는 원문의 조건과 주장 범위가 보존되었는지 본다. 두 검토 결과와 수정 사항을 `task-2-report.md`에 기록한다.

---

### Task 3: 관련 연구ㆍ데이터ㆍ방법 절의 절차 설명 개선

**Files:**
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/02-related-work.tex`
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/03-data.tex`
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/05-method.tex`
- Create: `.superpowers/sdd/2026-08-05-kiee-korean-refinement/task-3-report.md`

**Interfaces:**
- Consumes: Task 2에서 정의한 쉬운 핵심 용어와 Task 1 회귀 검사.
- Produces: 데이터 출처, 선별 과정, UPPAAL 변환 절차를 입력--처리--출력 순서로 설명한 세 절.

- [ ] **Step 1: 관련 연구의 비교 기준을 먼저 설명한다**

각 연구를 나열하기 전에 `모델의 추론을 다시 평가하는 연구`, `행동을 교정하는 연구`, `실행 중 안전 제약을 적용하는 연구`, `저장된 CoC와 차량 반응의 시간 관계를 확인하는 본 연구`로 구분한다. `저장 주석 감사`는 `저장된 CoC 데이터 검증`으로 바꾸고, 본 연구가 기존 충실도ㆍ인과성ㆍ폐루프 평가를 대체하지 않는 이유를 짧은 문장으로 쓴다.

- [ ] **Step 2: 데이터 출처 계층을 쉬운 말로 정리한다**

`03-data.tex`에서 공식 nuScenes, CoC-Nusc 변환 자료, 파싱 결과, 연구자가 만든 시간 조건을 서로 다른 출처로 분리한다. `약한 주석`은 `사람이 확인한 정답이 아니라 모델이 자동 생성한 주석`이라고 첫 등장에 설명한다.

- [ ] **Step 3: 403→290→134+156→130+4 흐름을 문장으로 설명한다**

화살표 수식은 보존한다. 바로 다음 문단에서는 각 숫자가 무엇을 세는지 한 문장씩 설명한다. 134개가 서로 독립된 반응이나 에피소드가 아니라 `CoC 사건별 검증 후보`라는 점을 별도 문장으로 둔다.

- [ ] **Step 4: 8건에서 5건으로 바뀐 사후 규칙을 명료화한다**

`코호트 보정 탐색 논리`는 `현재 분석 대상에서 결과를 살펴본 뒤 추가한 임시 규칙`으로 풀어 쓴다. 이 규칙이 독립적인 안전 요구사항이 아니며 추가 검증이 필요하다는 제한을 유지한다.

- [ ] **Step 5: 방법 절을 실제 실행 순서로 재구성한다**

`05-method.tex`의 설명 순서를 다음과 같이 통일한다.

1. CoC에서 행동 의도와 발생 시점을 읽음
2. 차량 속도 기록에서 반응 시작을 찾음
3. 반복 CoC 처리 정책을 적용함
4. 제한 시간 안에 반응이 있었는지 확인함
5. 장면 출처와 연결 가능성을 확인함
6. UPPAAL이 상태와 반례 경로를 기록함

모델 템플릿 이름은 유지하되, 각 템플릿이 무엇을 확인하는지 먼저 한국어로 설명한다. `observer`, `router`, `oracle`은 처음 등장할 때 `관찰 모델`, `결과 분류기`, `예상 결과 기준`을 병기한다.

- [ ] **Step 6: 표와 한국어 캡션을 본문 용어에 맞춘다**

관련 연구표, 출처 계층표, 증거 수준표, 방법 구성표의 한국어 셀과 캡션을 쉬운 용어로 고친다. 영문 캡션의 두 번째 인자는 그대로 둔다.

- [ ] **Step 7: Task 3 검증과 이중 검토를 수행한다**

Task 2와 같은 두 unittest 파일을 실행한다. 수치ㆍ수식ㆍ인용ㆍ영문 보존 검사는 통과해야 하고, 남은 금지 표현은 편집하지 않은 6--10절에서만 나와야 한다. 언어 검토와 기술 검토 결과를 `task-3-report.md`에 기록한다.

---

### Task 4: 실험ㆍ결과 절의 비교 대상과 의미 개선

**Files:**
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/06-experiments.tex`
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/07-results.tex`
- Create: `.superpowers/sdd/2026-08-05-kiee-korean-refinement/task-4-report.md`

**Interfaces:**
- Consumes: 앞 절에서 정리한 `검증 조건`, `차량 반응`, `반복 CoC 처리 정책`, `처리 유형 분류`.
- Produces: 각 실험의 질문ㆍ입력ㆍ비교 조건ㆍ결과ㆍ해석이 분명한 실험 및 결과 절.

- [ ] **Step 1: 실험마다 확인하려는 질문을 첫 문장에 쓴다**

각 실험 설명을 다음 틀로 정리한다.

```text
이 실험은 [무엇이 결과에 영향을 주는지] 확인한다.
[동일하게 유지한 입력]은 그대로 두고 [변경한 조건]만 바꾼다.
결과는 [측정값]으로 비교한다.
이 결과는 [허용되는 해석]만 지지하며 [과도한 해석]은 지지하지 않는다.
```

위 문장을 그대로 반복하지 말고 각 실험의 실제 조건을 넣어 자연스럽게 쓴다.

- [ ] **Step 2: UPPAAL 시험과 직렬화 시험을 구분한다**

282개 모델과 1,128개 질의의 일치는 시간 검증 성능이 아니라 플래그와 질의 변환 과정이 예상대로 동작했는지 확인한 결과임을 먼저 쓴다. `직렬화 회귀`만 단독으로 쓰지 않는다.

- [ ] **Step 3: 134개 결과의 단위와 비독립성을 명확히 쓴다**

125개, 4개, 5개가 어떻게 나뉘었는지 설명한 뒤, 반복 CoC가 같은 차량 반응을 공유할 수 있어 134개가 독립 표본이 아니라는 점을 별도 문장으로 둔다. PASS/FAIL 대신 가능한 한 `설정한 조건 안에서 반응 확인`, `추가 검토 필요`를 사용한다.

- [ ] **Step 4: 반복 정책과 제한 시간 민감도를 예로 설명한다**

`preserve/reset`은 각각 `첫 CoC 발생 시점을 유지하는 방식`, `반복 CoC가 나타날 때 시간을 다시 재는 방식`으로 먼저 설명한다. `scene-0028`, `scene-0074`, `scene-0042`, `scene-0065`의 결과는 정책 또는 제한 시간을 바꾸면 분류가 달라진다는 의미까지만 서술한다.

- [ ] **Step 5: 인위적 오류 사례와 실제 데이터 결과를 분리한다**

`orphan_response`, 경계 오류, 다단계 오류는 실제 주행에서 발견한 결함이 아니라 검사기의 동작을 확인하기 위해 인위적으로 만든 오류라는 점을 각 결과 바로 앞에 명시한다. `합성 변이`는 첫 등장 이후 `인위적 오류 사례`로 표현한다.

- [ ] **Step 6: 13개 체인 결과의 지위를 쉬운 말로 제한한다**

`스모크 출력`을 `별도 구현이 실행되는지만 확인한 기본 동작 결과`로 바꾼다. 사용한 파서와 속도 탐지기가 공유 검증 조건과 다르므로 RQ3의 성능 수치로 사용할 수 없다는 점을 두 문장으로 나눈다.

- [ ] **Step 7: 결과 표와 캡션을 독립적으로 이해할 수 있게 고친다**

표 제목과 열 이름은 표만 읽어도 단위와 판정 의미를 알 수 있게 한다. `감사 판정`, `라우팅`, `코호트`, `계보`, `스모크`를 본문에서 정의한 쉬운 표현으로 바꾼다. 숫자와 영문 캡션은 보존한다.

- [ ] **Step 8: Task 4 검증과 이중 검토를 수행한다**

두 unittest 파일을 실행하고, 금지 표현이 남아 있다면 8--10절에만 있어야 한다. 언어 검토자는 각 결과 문단에서 `무엇을 비교했는가`와 `무엇을 의미하는가`에 답할 수 있는지 확인한다. 기술 검토자는 모든 숫자와 제한 사항을 기준 JSON과 대조한다. 결과를 `task-4-report.md`에 기록한다.

---

### Task 5: 논의ㆍ한계ㆍ결론과 전체 용어 통일

**Files:**
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/08-discussion.tex`
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/09-threats.tex`
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/10-conclusion.tex`
- Modify: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/01-introduction.tex` through `10-conclusion.tex` only for cross-section terminology corrections
- Create: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/KOREAN_EDIT_REPORT.md`
- Create: `.superpowers/sdd/2026-08-05-kiee-korean-refinement/task-5-report.md`

**Interfaces:**
- Consumes: Tasks 2--4의 용어와 모든 편집 결과.
- Produces: 전체 원고에서 통일된 한국어와 편집 전후 사례를 담은 보고서.

- [ ] **Step 1: 논의 절을 결과의 활용과 한계로 나눈다**

`감사는 학습 데이터 준비를 무엇을 바꾸는가?`와 같이 호응이 틀린 제목을 `이 검증 결과를 학습 데이터 준비에 어떻게 활용할 수 있는가?`처럼 고친다. 각 처리 유형을 다음처럼 설명한다.

- 설정한 조건 안에서 반응이 확인된 항목: 학습 자료로 바로 확정하지 않고 유지 여부를 검토할 수 있음
- 정책이나 탐지기에 따라 결과가 달라지는 항목: 사람이 추가로 확인해야 함
- CoC와 반응의 연결 근거나 장면 출처가 부족한 항목: 긴 학습 시퀀스로 연결하지 않음
- 인위적 오류 사례: 검사기 회귀 시험에만 사용

`약한 유지 후보`처럼 뜻을 바로 알기 어려운 표현은 위 설명 뒤에 필요한 경우에만 짧은 이름으로 사용한다.

- [ ] **Step 2: 연구 한계를 원인과 영향으로 설명한다**

`09-threats.tex`의 각 한계를 다음 구조로 쓴다.

1. 어떤 정보 또는 검증이 부족한가
2. 그 때문에 어떤 결론을 내릴 수 없는가
3. 후속 연구에 무엇이 필요한가

한 문장에 세 내용을 모두 넣지 않는다. `코호트 보정`, `출처 플래그`, `직렬화 회귀`, `스모크`는 쉬운 설명으로 바꾼다.

- [ ] **Step 3: 결론을 목적--방법--핵심 결과--한계 순으로 다시 쓴다**

첫 문단은 연구가 해결한 문제와 방법, 둘째 문단은 134 및 125+4+5 결과와 정책 민감도, 셋째 문단은 안전성을 입증하지 않는다는 한계와 후속 검증을 다룬다. 서로 다른 구현의 13개 체인 결과는 기본 동작 확인에만 사용했다는 제한을 유지한다.

- [ ] **Step 4: 전체 원고의 잔여 직역 표현을 문맥별로 검토한다**

Run:

```bash
grep -RInE '감사|응답 계보|반복 주석|후보 시간 의무|자차 움직임 응답 증거|라우팅|코호트|스모크|음성 대조|출처 플래그|직렬화 회귀' \
  papers/demestic-journal/latex-kiee-review-2022-coc-audit/main.tex \
  papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections
```

각 결과를 문맥별로 검토한다. 구현 변수, 인용된 영문 용어 또는 `audit`의 영문 캡션을 제외한 한국어 직역 표현은 자연스러운 문장으로 바꾼다. 검색 결과가 남으면 `task-5-report.md`에 남긴 이유를 한 줄씩 기록한다.

- [ ] **Step 5: 편집 보고서를 작성한다**

`KOREAN_EDIT_REPORT.md`에 다음을 기록한다.

- 수정 범위와 보존 범위
- 핵심 용어의 변경 전ㆍ후와 선택 이유
- 대표 문장 10개의 편집 전ㆍ후 비교
- 수치ㆍ수식ㆍ인용ㆍ영문 요소 보존 검사 결과
- 연구 주장이나 결과를 바꾸지 않았다는 경계

- [ ] **Step 6: 전체 편집 검사를 통과시킨다**

Run:

```bash
make -C papers/demestic-journal/latex-kiee-review-2022-coc-audit test
```

Expected: 기존 형식 검사와 새 편집 무결성 검사가 모두 통과하고 금지 표현 실패가 0개다.

- [ ] **Step 7: 한국어 원고 전체를 독립 검토한다**

언어 검토자는 제목부터 결론까지 순서대로 읽으며 다음을 판정한다.

- 문장을 한 번 읽고 뜻을 이해할 수 있는가
- 주어와 서술어가 맞는가
- 같은 개념에 같은 용어를 쓰는가
- 앞 문장과 뒤 문장의 논리 관계가 자연스러운가
- 표와 캡션이 본문 없이도 이해되는가

기술 검토자는 기준 JSON과 설계 문서의 주장 경계를 대조한다. 발견 사항을 수정하고 범위를 좁힌 재검토를 받는다.

---

### Task 6: 전체 빌드ㆍ시각 검사ㆍ원본 보존 감사

**Files:**
- Modify only if required for layout: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/sections/*.tex`
- Update: `papers/demestic-journal/latex-kiee-review-2022-coc-audit/KOREAN_EDIT_REPORT.md`
- Create: `.superpowers/sdd/2026-08-05-kiee-korean-prose-refinement/task-6-report.md`

**Interfaces:**
- Consumes: 완성된 한국어 편집본, 모든 테스트와 기준 해시.
- Produces: 빌드된 최종 PDF, 원본 보존 및 전 페이지 시각 검사 증거.

- [ ] **Step 1: 전체 테스트와 빌드를 새로 실행한다**

Run:

```bash
make -C papers/demestic-journal/latex-kiee-review-2022-coc-audit all
```

Expected: 모든 unittest가 통과하고 LuaLaTeX--BibTeX--LuaLaTeX--LuaLaTeX 빌드가 종료 코드 0으로 끝난다.

- [ ] **Step 2: 로그 차단 오류를 확인한다**

Run:

```bash
(grep -E 'Undefined control sequence|LaTeX Warning: (Citation|Reference).*undefined|There were undefined references|Fatal error|Emergency stop|Overfull \\[hv]box|Missing character' \
  papers/demestic-journal/latex-kiee-review-2022-coc-audit/main.log || true)
```

Expected: 출력 0줄. Underfull 경고는 페이지를 확인한 뒤 실제 가독성 문제가 없는 경우에만 허용한다.

- [ ] **Step 3: 모든 PDF 페이지를 렌더링해 확인한다**

`mutool draw`로 모든 페이지를 PNG로 렌더링한다. 제목, 한국어 줄바꿈, 표 셀, 이중언어 캡션, TikZ 그림, 참고문헌을 페이지별로 확인한다. 글자 겹침, 잘림, 빈 열, 고립된 절 제목 또는 지나치게 큰 공백이 있으면 한국어 문장 의미를 바꾸지 않는 범위에서 줄바꿈과 표 너비만 조정한다.

- [ ] **Step 4: 원본과 참조 양식 보존을 다시 확인한다**

Run:

```bash
sha256sum -c .superpowers/sdd/2026-08-05-kiee-korean-prose-refinement/source-before.sha256
sha256sum -c .superpowers/sdd/2026-08-05-kiee-korean-prose-refinement/template-before.sha256
```

Expected: 원본과 참조 양식의 모든 항목이 `OK`다.

- [ ] **Step 5: 독립성과 최종 패키지를 확인한다**

대상에 심볼릭 링크, 원본을 가리키는 상대 입력, 테스트 캐시, TeX 캐시, 압축 아카이브가 없는지 확인한다. 테스트ㆍ빌드 과정에서 생성된 `tests/__pycache__`와 `.texlive-cache`는 최종 확인 후 제거한다. PDF, LaTeX 소스, 글꼴, PGF와 라이선스는 보존한다.

- [ ] **Step 6: 최종 보고서와 전체 검토를 완료한다**

`KOREAN_EDIT_REPORT.md`에 최종 페이지 수, 테스트 수, 로그 검사, 시각 검토, 원본 보존 결과를 추가한다. 새 검토자가 설계 문서의 모든 요구사항을 읽고 전체 복사본을 다시 검토한다. 차단 또는 중요 발견이 있으면 한 차례 수정하고 해당 범위를 재검토한다. 최종 결과를 `task-6-report.md`에 기록한다.

---

## Final Acceptance Checklist

- [ ] KIEE 복사본만 수정되었다.
- [ ] 한국어 제목ㆍ본문ㆍ표ㆍ캡션이 자연스럽고 쉽게 읽힌다.
- [ ] 영문 제목ㆍ초록ㆍ핵심어ㆍ영문 캡션ㆍ참고문헌이 보존되었다.
- [ ] 수치ㆍ수식ㆍ인용ㆍ레이블ㆍ실험 결과와 주장 범위가 보존되었다.
- [ ] 금지한 직역 표현이 한국어 원고에 남지 않았다.
- [ ] 기존 형식 검사와 새 편집 무결성 검사가 모두 통과한다.
- [ ] 전체 LaTeX 빌드와 로그 검사가 통과한다.
- [ ] PDF의 모든 페이지가 시각 검토를 통과한다.
- [ ] 원본과 참조 양식 해시가 편집 전과 같다.
- [ ] 편집 보고서가 대표 변경 사례와 검증 결과를 정확히 기록한다.
