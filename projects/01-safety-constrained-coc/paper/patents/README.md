# Safety-Constrained CoC 발명설명서

- project_id: `safety-constrained-coc`
- 문서: [coc_invention_disclosure.hwp](coc_invention_disclosure.hwp)
- 발명명: 실행 가드 통합형 인과 연쇄를 이용한 요구사항 부합 궤적 선택 모델의 학습 방법 및 장치
- 문서 성격: 발명내용설명서 및 예비 청구항 1–18. 실제 출원·등록 여부는 미확인.
- 기반 논문: [latex-kiee-review-2022/main.tex](../manuscript/latex-kiee-review-2022/main.tex)
- 분석: [COC_INVENTION_DISCLOSURE_ANALYSIS_REPORT_V01.md](../../docs/reports/COC_INVENTION_DISCLOSURE_ANALYSIS_REPORT_V01.md)

## V02 수정본

- 편집용: [coc_invention_disclosure_v02.docx](coc_invention_disclosure_v02.docx)
- 검토용: [coc_invention_disclosure_v02.pdf](coc_invention_disclosure_v02.pdf)
- 내용 원본: [COC_INVENTION_DISCLOSURE_V02.md](COC_INVENTION_DISCLOSURE_V02.md)
- 문서·도면 생성: [build_coc_disclosure.py](build_coc_disclosure.py)
- 도면: `figures/coc_disclosure_fig01_v02.png`부터 `figures/coc_disclosure_fig07_v02.png`까지 7개.

V02는 원래 HWP를 보존하면서 사용자의 수정 요청에 따라 작성한 기술 검토용 발명설명서다.
이 환경에 HWP 저장용 한글 편집기가 없어 DOCX와 PDF를 제공한다. 두 파일은 같은 Markdown
내용에서 생성되지만 조판 엔진은 다르며, DOCX를 여는 프로그램과 설치 글꼴에 따라 쪽 나눔은
달라질 수 있다. PDF는 XeLaTeX로 생성하고 페이지를 이미지로 렌더링하여 검수한다.

주요 변경은 다음과 같다.

- 중복 절·제목을 정리하고 본문과 도면의 완화 간격을 5.5 m로 통일했다.
- 목표·가드 공동 충족 정답의 일반 정의와, 교착 후보의 낮은 진행도를 이용하는 기존 합성 구현을 구분했다.
- 청구항 5는 필터 순서를 제한하지 않는 공동 판정으로 정리했다.
- 청구항 9는 전용 쌍대·대조 손실에서 실제 구현된 계약별 정답 응답 지도학습으로 변경했다.
- 청구항 10은 별도 교란 모델과의 비교 통제로 한정했다. hard-negative 개선 학습은 포함하지 않았다.
- 청구항 13·15·18은 다른 항을 참조하지 않아도 기술 구성이 드러나도록 재작성했다.
- 공동 충족 후보가 없거나 효용이 동률인 경우와 외부 재선택은 설계 실시예로 명시했다.
- 수치 실시예·판정표, 학습 입력·정답, 감독 손실 및 기능부 부호를 추가하고 도면 7개를 다시 작성했다.
- KEPT·CSN 등의 학습 구성을 반영하여 선행문헌 비교를 수정하고 권리화 강도의 단정을 제거했다.

재생성에는 Python 3, `python-docx`, `Pillow`, XeLaTeX가 필요하다. 그림은 로컬
`~/.local/share/fonts/NotoSansCJK-Regular.ttc`, PDF는 기존 논문에 포함된 Noto Serif CJK KR
글꼴을 사용한다. 필요한 패키지를 갖춘 Python으로 다음을 실행한다.

```bash
python projects/01-safety-constrained-coc/paper/patents/build_coc_disclosure.py
```

실험 코드와 기존 결과는 수정하지 않았다. 발명자·출원인·발명 완성일·공개일 등 확인되지 않은
사실도 새로 기입하지 않았다. 원본 분석 보고서는 원래 HWP에 대한 검토 이력으로 유지한다.

검수 결과: PDF 19쪽, 예비 청구항 18개, 표 5개, 도면 7개를 확인했다. DOCX의 모든 본문 문단과
표 셀이 Markdown 원본과 일치하며, 문서 ZIP 구조와 이미지 포함을 확인했다. PDF의 글자 누락·
페이지 경계 초과 및 XeLaTeX overfull 경고는 없었다. HWP 원본 해시와 로컬 링크도 확인했다.
DOCX는 Word·한글 GUI에서 직접 열어 검수한 것은 아니다.

`python3 cli/checks/file_naming.py`는 실행했으며 이번 작업 경로에는 위반이 없다.
전체 검사는 다른 프로젝트 산출물의 `(1)` 파일 3개와 루트 `portal_exec.md` 때문에 실패한다.
해당 기존 파일은 수정하지 않았다.

## 생성·활용 과정 보완자료 V01

명세서 작성을 위해 실시예와 산출 방식을 구체화해 달라는 검토 의견을 반영한 자료다.
기존 발명설명서 V02에 첨부하는 문서이며, 원본 HWP와 V02 본문은 유지한다.

- 전달용 묶음: [coc_patent_supplement_v01.zip](coc_patent_supplement_v01.zip)
- 검토용: [coc_generation_usage_supplement_v01.pdf](coc_generation_usage_supplement_v01.pdf)
- 편집용: [coc_generation_usage_supplement_v01.docx](coc_generation_usage_supplement_v01.docx)
- 내용 원본: [COC_GENERATION_USAGE_SUPPLEMENT_V01.md](COC_GENERATION_USAGE_SUPPLEMENT_V01.md)
- 수치·전체 프롬프트·정답: [coc_generation_usage_examples_v01.json](coc_generation_usage_examples_v01.json)
- 회신 초안: [COC_SUPPLEMENT_REPLY_DRAFT_V01.md](COC_SUPPLEMENT_REPLY_DRAFT_V01.md)
- 생성 및 검증: [build_coc_supplement.py](build_coc_supplement.py)

기존 코드를 재실행하여 시간 계약의 B/C, 차선변경 계약의 A/B 정답과 후보별 판정을
확인했다. 네 표본은 합성 입력·정답 생성의 재현 예이며 새로운 모델 예측 결과가 아니다.
문장틀 대입, 기본 CoC와의 결합, 감독학습 입력·손실 및 외부 판정 절차를 설명하고,
구현한 범위와 구조화 인과 단계·실행 연결의 확장 설계를 구분한다. 보완자료 8.1절에는
명세서에 활용할 수 있는 실시 방법 문안을 제공한다.

ZIP은 수정 발명내용설명서 V02 PDF·DOCX, 보완자료 PDF·DOCX, 수치 JSON, 기반 논문 PDF, 회신 초안 및 파일 해시를 담은
README를 포함한다. 기반 논문은 지정된 `latex-kiee-review-2022/main.pdf`의 바이트를
그대로 포함하며 ZIP 안에서만 `safety_constrained_coc_paper.pdf`로 명명한다. 공개 참고
문헌은 보완자료 9절에 공식 링크로 안내한다. 외부 전송은 수행하지 않았다.

재생성에는 위 문서 생성 의존성에 NumPy를 추가하여 다음 명령을 실행한다.

```bash
python projects/01-safety-constrained-coc/paper/patents/build_coc_supplement.py
```

보완자료 검수: PDF 8쪽·표 6개, DOCX 본문과 표의 원문 일치, PDF 텍스트 포함 및 페이지
경계, 글자 누락·overfull 경고 없음, ZIP 무결성과 기반 논문 원본 일치를 확인했다.
DOCX의 GUI 조판 검수는 포함하지 않는다. 파일명 검사는 기존의 다른 경로 위반 4건만
보고하며, 이번 보완자료 경로에 대한 위반은 없다.

## 원본과 배치 이력

- 이동일: 2026-09-14
- 제공 경로: 저장소 루트의 `1. 발명내용설명서-CoC.hwp` (실제 파일명은 분해형 한글).
- 사람이 읽는 원래 이름: `1. 발명내용설명서-CoC.hwp`.
- 새 경로: `projects/01-safety-constrained-coc/paper/patents/coc_invention_disclosure.hwp`.
- 배치 이유: 등록된 소유 프로젝트의 출원 자료이므로 `paper/` 아래에 보관하고, 논문 원고와 구분하기 위해 `patents/`를 사용한다.
- 적용 규칙: [Project Structure Codex §3·§5](../../../../docs/architecture/PROJECT_STRUCTURE_CODEX.md), [File Naming Codex §4.5·§5·§7](../../../../docs/architecture/FILE_NAMING_CODEX.md).
- 이동 전 참조 조사: Git 추적 파일 및 비무시 미추적 텍스트 파일에서 원래 한글 제목·파일명을 검색했으며 기존 참조는 발견되지 않았다. 기존 `MANIFEST.sha256`에도 원래 경로가 없었다.
- 원본 크기: `1,107,456 bytes`.
- 원본 SHA-256: `42d0c3694293e0fc5de0e85f502f33dac4e792b4d0d2e44c3781f70f893fb290`.
- HWP 본문과 내장 도면은 수정하지 않고 파일 경로만 변경했다. 분석 보고서의 수정 제안은 원본에 적용하지 않았다.

## 분석 방법

HWP 5 계열 OLE 컨테이너의 `BodyText/Section0`을 압축 해제하여 문단 텍스트를 읽고,
내장 PNG 7개를 각각 확인했다. 문서 내 스크립트는 실행하지 않았다.
추출 텍스트와 이미지의 임시 작업 위치는 `/tmp/coc_invention_analysis/`이며,
보존 원본과 분석 보고서가 이 자료의 지속적인 참조점이다.
HWP 편집기로 렌더링한 전체 페이지의 줄바꿈·쪽 나눔 검수는 포함하지 않는다.
