# KIEE 심사 대응 수정본 V02

- 소유 프로젝트: `safety-constrained-coc`
- 기준 원고: `../latex-kiee-review-2022-revision-v01/`
- 수정 범위: 2차 심사의 세 추가 확인 사항만 반영

## 제출 파일

1. [main.pdf](main.pdf): 수정 표시 논문. 이번 수정만 파란색이며 1차 수정 내용은 검정색이다.
2. [response-to-reviewer-1.pdf](response-to-reviewer-1.pdf): 기존 리뷰어 1 답변서와 같은 코멘트ㆍ저자 답변ㆍ논문 반영 결과 양식의 답변서.

기존 실험 수치와 표ㆍ그림은 유지하였다. 표준편차 정의가 다른 이유와 해석 범위를 설명하고, 복합 표현 변화의 주된 원인을 특정하지 않도록 해석을 명확히 하며, 표준 평가의 천장 효과 가능성을 기존 hard-case 결과와 함께 설명한다.

## 소스 및 빌드

`main.tex`, `sections/`, `kiee-review.sty`, `references.bib`는 V02의 독립 소스다.
`response-to-reviewer-1.tex`는 독립 답변서 소스다. 글꼴과 그림은 원본
`../latex-kiee-review-2022/`의 자산을 참조하므로 해당 디렉터리를 함께 유지한다.

```bash
make manuscript
make rebuttal
```

LuaLaTeX 및 BibTeX가 필요하다. 중간 빌드 파일은
`artifacts/projects/safety-constrained-coc/public/kiee-review-002/revision-2026-09-30-001/`에
생성하고, 제출용 PDF만 이 디렉터리에 복사한다. 답변서 쪽 번호는 V02 원고 기준이다.
