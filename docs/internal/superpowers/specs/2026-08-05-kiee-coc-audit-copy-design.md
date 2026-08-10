# CoC 감사 논문 KIEE 2022 독립 복사본 설계

## 1. 목적

현재 원고
`papers/demestic-journal`을 한국전기학회 2022 익명 심사 LaTeX 형식으로
변환한 독립 복사본을 다음 위치에 만든다.

`papers/demestic-journal/latex-kiee-review-2022-coc-audit`

변환은 서식과 문서 구조만 바꾸며, 검토를 마친 연구 주장·수치·증거 범위는
변경하지 않는다. 현재 IEEEtran 원고와
`papers/paper1-safety-constrained-coc/latex-kiee-review-2022`의 기존 논문은
수정하지 않는다.

## 2. 독립성 원칙

새 복사본은 원본 절 파일을 상대경로로 불러오거나 심볼릭 링크하지 않는다.
다음 파일을 새 디렉터리 내부에 독립적으로 둔다.

- `main.tex`
- `kiee-review.sty`
- `references.bib`
- `sections/` 아래 변환된 열 개 절
- `figures/` 아래 다섯 TikZ 그림
- `fonts/` 아래 Noto Serif CJK KR 글꼴과 OFL 라이선스
- `tests/test_kiee_format.py`
- `Makefile`, `README.md`

원본 원고가 이후 변경되더라도 복사본은 자동으로 바뀌지 않는다.

## 3. 형식 기준

기준 양식은
`papers/paper1-safety-constrained-coc/latex-kiee-review-2022`의 현재
`kiee-review.sty`와 형식 시험이다.

적용할 기준은 다음과 같다.

- A4, 좌우 18.01 mm, 상하 18.99 mm
- 2단 본문, 단 사이 8 mm
- 본문 8.5 pt, 12.75 pt 행간
- 영문 제목 16 pt, 국문 제목 14 pt
- 익명 심사본으로 저자 정보 생략
- 50--200단어 영문 초록
- 영문 핵심어 정확히 6개
- 모든 표와 그림에 국문·영문 병기 캡션
- 참고문헌 8 pt
- 로컬 Noto Serif CJK KR 글꼴 사용

## 4. 전면부 변환

국문 제목은 현재 논문의 제목을 유지한다.

> 추론 보강형 E2E 자율주행 데이터의 시간·출처 계약 감사: CoC-Nusc와
> UPPAAL 기반 분석

영문 제목은 같은 의미로 다음과 같이 사용한다.

> Auditing Temporal and Provenance Contracts in Reasoning-Augmented E2E
> Autonomous Driving Data: An Analysis with CoC-Nusc and UPPAAL

영문 초록은 현재 국문 요약의 다음 요소를 50--200단어로 번역·압축한다.

1. 회고적으로 생성된 CoC의 시간·출처 의미론 문제
2. 후보 시간 계약과 UPPAAL 관찰자 방법
3. 134개 주석 사건별 후보 계약과 125+4+5 라우팅
4. 282모델·1,128질의가 직렬화/질의 회귀 검사라는 제한
5. 13체인 결과가 다른 parser/detector의 구현 연기 시험이라는 제한
6. 물리 안전성·일반 CoC 충실도 증명이 아니라는 결론

핵심어는 다음 여섯 개를 사용한다.

- Autonomous driving
- End-to-end learning
- Chain-of-Causation
- Timed automata
- Model checking
- Data provenance

## 5. 본문 구조와 내용 보존

원본의 열 개 절을 같은 논리 순서로 유지한다.

1. 서론
2. 관련 연구
3. 데이터와 증거 수준
4. 문제 정의
5. 제안 방법
6. 실험 설계
7. 실험 결과
8. 논의와 활용
9. 타당성 위협
10. 결론

절 파일 이름도 `01-introduction.tex`부터 `10-conclusion.tex`까지 유지한다.
원본의 RQ1--RQ4, 모든 수치, 표, 수식, 코드 식별자와 한계 문장은 내용상
동일하게 보존한다. 형식 변환을 이유로 결과를 생략하거나 새 주장을 추가하지
않는다.

## 6. 그림과 표

원본의 다섯 TikZ 그림을 새 복사본으로 복사하고, KIEE 스타일에서 요구하는
색상·TikZ 패키지와 라이브러리를 제공한다.

- `overview-pipeline.tex`
- `annotation-flow.tex`
- `method-pipeline.tex`
- `uppaal-network.tex`
- `training-routing.tex`

모든 `\caption`은 다음 인터페이스 중 하나로 바꾼다.

- `\bifigcaption{국문 캡션}{English caption}`
- `\bitablecaption{국문 캡션}{English caption}`

영문 캡션은 국문 캡션의 의미와 주장 범위를 그대로 번역한다. KIEE의 좁은
2단 폭에서 읽기 어려운 전폭 표·그림은 `figure*`/`table*`을 유지하고,
필요한 경우 열 너비와 글꼴 크기만 조정한다. 표의 행·수치·의미는 바꾸지 않는다.

## 7. 참고문헌

현재 `references.bib` 전체를 복사한다. 본문의 인용 키는 변경하지 않는다.
KIEE 복사본은 기존 양식과 같은 `unsrt` BibTeX 스타일과 8 pt 참고문헌을
사용한다. 미정의 인용과 중복 키가 없어야 한다.

## 8. 자동 검사

`tests/test_kiee_format.py`는 다음을 검사한다.

- KIEE 용지·여백·단 간격
- 익명 전면부와 로컬 글꼴/OFL 존재
- 영문 초록 50--200단어
- 영문 핵심어 6개
- 열 개 절이 모두 컴파일 대상인지 여부
- 원본과 복사본의 핵심 수치·연구 질문·증거 제한 문구 일치
- 모든 컴파일 대상 그림·표가 병기 캡션을 사용하는지 여부
- 원본 디렉터리로 향하는 상대 `\input` 또는 심볼릭 링크가 없는지 여부

시험은 특정 그림·표 개수에 불필요하게 고정하지 않고, 실제 컴파일 대상 전체를
탐색하여 검사한다.

## 9. 빌드와 시각 검증

`Makefile`은 먼저 형식 시험을 실행하고, 이후 LuaLaTeX--BibTeX--LuaLaTeX--
LuaLaTeX 순서로 빌드한다. `latexmk`가 있으면 같은 LuaLaTeX 흐름을 사용한다.

완료 기준은 다음과 같다.

- 형식 시험 전부 통과
- LaTeX와 BibTeX 종료 코드 0
- 미정의 명령·인용·참조 0
- overfull hbox/vbox 0
- 유효한 PDF 생성
- 모든 PDF 페이지 렌더링 및 시각 검사
- 한글 글꼴 깨짐, 그림·표 잘림, 레이블 겹침, 빈 컬럼, 고립 제목 없음

underfull 또는 글꼴 대체 경고는 실제 가독성 문제가 없을 때만 비차단 진단으로
기록한다.

## 10. 오류 처리와 보존

- 대상 폴더가 이미 존재하면 내용을 임의로 삭제하지 않고 충돌 파일을 먼저
  확인한다.
- 원본 `papers/demestic-journal`의 파일은 읽기 전용 입력으로 취급한다.
- 기존 Safety-Constrained CoC KIEE 원고도 읽기 전용 양식 기준으로만 사용한다.
- 빌드 실패 시 생성된 부분 PDF를 완료 산출물로 보고하지 않는다.
- 유효한 Git 메타데이터가 없으므로 커밋을 전제로 하지 않고, 변환 보고서와
  파일 비교를 작업 기록으로 남긴다.

## 11. 산출물

- 독립 KIEE LaTeX 원고 디렉터리
- 빌드된 `main.pdf`
- 형식 회귀 시험
- `README.md`의 빌드·출처·독립성 설명
- 변환 및 검증 보고서

