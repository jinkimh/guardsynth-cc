# KIEE 2022 HWP 기반 익명 심사본

한국전기학회 2022 HWP 양식의 실측 규격을 재현한 독립 LaTeX 복사본이다. 기존
`latex-domestic/main.tex`과 절 파일은 수정하지 않는다.

## 적용한 형식

- A4, 좌우 여백 18.01 mm, 상하 여백 18.99 mm
- 2단 본문, 단 사이 8 mm
- 본문 8.5 pt, 줄 간격 150% 상당
- 영문 제목 16 pt, 국문 제목 14 pt
- 익명 심사용 저자 정보 생략
- 영문 Abstract 50-200단어와 영문 Key Words 6개
- 모든 그림과 표의 한글-영문 병기 캡션
- 로컬 `fonts/`의 Noto Serif CJK KR과 OFL 라이선스 사용

## 구조

- `main.tex`: 익명 심사본의 제목, 영문 초록, 절 구성
- `kiee-review.sty`: 용지, 글꼴, 단, 제목, 캡션 형식
- `sections/`: 이 복사본에서만 수정되는 독립 절 파일. `06-results.tex`는 이전 결과 절을 보존한 비컴파일 자료이며, 현재 결과는 `05-experiments.tex`에 통합되어 있다.
- `figures/`: 원고 그림과 재생성 스크립트
- `tests/test_kiee_format.py`: 형식 회귀 검사
- `tests/test_experimental_evidence.py`: 원시 예측ㆍepisode에서 논문 지표를 독립 재계산하는 검사
- `EXPERIMENT_RESULT_AUDIT.md`: 수치 재검산, 해석 수정 및 재실험 우선순위

## 빌드

```bash
make
```

LuaLaTeX 글꼴 캐시는 이 폴더의 `.texlive-cache/`에 저장된다. 그림을 원자료에서
다시 생성하려면 `make figures`를 먼저 실행한다.

## 수치 출처

- 정적 후보(seed 42): `artifacts/results/public/small-vlm-guard-v0/candidate-guard-summary-seed42-v0/summary.json`
- 시간 계약: `artifacts/results/public/small-vlm-guard-v0/temporal-guard-multiseed-v0/summary.json`
- 시간 계약 해석 보고서: `docs/reports/TEMPORAL_GUARD_MULTISEED_EXPERIMENT_REPORT_V01.md`
- 다중 maneuver/hard: `artifacts/results/public/small-vlm-guard-v0/maneuver-guard-multiseed-v0/summary.json`
- R1 진단(단일 장면): `artifacts/results/restricted/alp-exp-006/guard-semantic-summary-v2/summary.json`
- 폐루프 단계 완비: `artifacts/results/public/contract-microworld-v1/pilot-phase-complete-isolated-2026-08-04-v2/PHASE_COMPLETE_ASSESSMENT_KO.md`
- Release reversal: `artifacts/results/public/contract-microworld-v2/pilot-release-reversal-2026-08-04-v1/DEEP_STRESS_ASSESSMENT_KO.md`

주 증거는 Qwen3-VL-2B-Instruct의 합성 후보 선택 실험이다. Alpamayo-R1 단일 장면 진단과 별도 두 층 신경망의 폐루프 미시 환경은 서로 다른 모델ㆍ과제에서 얻은 보조 증거이므로 교차 모델 재현이나 실제 차량 안전성의 증거로 합치지 않는다.
