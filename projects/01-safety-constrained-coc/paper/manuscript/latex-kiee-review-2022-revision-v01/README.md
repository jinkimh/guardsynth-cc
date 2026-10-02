# KIEE 심사 대응 수정본 V01

이 디렉터리는 `../latex-kiee-review-2022/` 원문을 보존하면서 심사 의견을 반영하기
위한 독립 수정본이다. `main.tex`, `sections/`, `references.bib`, `kiee-review.sty`는
수정본 안에서만 편집한다.

용량이 큰 글꼴과 그림은 원문 디렉터리의 `fonts/`와 `figures/`를 읽기 전용 자산으로
참조한다. 따라서 이 수정본에서 논문 내용을 고쳐도 원문은 바뀌지 않지만, 원문
디렉터리를 함께 유지해야 빌드할 수 있다.

## 심사 대응 파일

- `response-to-reviewers.tex`: 리뷰어별 답변서 양식
- [response-to-reviewer-1.pdf](response-to-reviewer-1.pdf): 리뷰어 1 답변, 통합 PDF의 1–7쪽
- [response-to-reviewer-2.pdf](response-to-reviewer-2.pdf): 논문 정보·답변에 앞서·리뷰어 2 답변·맺음말을 포함한 독립 답변서
- [response-to-reviewer-2.tex](response-to-reviewer-2.tex): 리뷰어 2 독립 답변서 소스
- `main.tex`: 수정 논문의 진입 파일
- `sections/`: 수정 논문에서만 사용하는 독립 절 파일

각 코멘트는 다음 세 항목을 반드시 포함한다.

1. 리뷰어 코멘트 원문
2. 리뷰어에 대한 저자 답변
3. 논문 반영 결과와 수정 위치

새 코멘트는 `response-to-reviewers.tex`의 `reviewitem` 블록을 복제하여 작성한다.
답변서의 논문 반영 결과와 실제 `main.tex` 또는 `sections/*.tex` 변경이 일치하는지
항상 함께 확인한다.

리뷰어 1 PDF는 통합 PDF의 1–7쪽을 원래 내용·쪽 번호·조판 그대로 분리한 파일이다.
리뷰어 2 답변서는 통합 LaTeX 소스의 공통 앞부분(논문 정보와 답변에 앞서)에 리뷰어 2
답변과 맺음말을 이어 붙여 독립적으로 조판했다. 답변 내용과 논문 정보는 유지하고
답변서 자체의 쪽 번호는 1부터 시작한다. 통합 답변서를 수정하면 리뷰어 1 분리본과
리뷰어 2 소스에도 해당 변경을 반영해야 한다. 아래 `make rebuttal`은 통합 답변서만
빌드한다.

## 빌드

```bash
make                 # 수정 논문과 답변서 모두 빌드
make manuscript      # main.pdf만 빌드
make rebuttal        # response-to-reviewers.pdf만 빌드
make rebuttal-reviewer-2  # response-to-reviewer-2.pdf만 빌드
```

LuaLaTeX 캐시는 이 디렉터리의 `.texlive-cache/`에 생성된다.
