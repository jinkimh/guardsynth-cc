# Safety-Constrained CoC 국내 저널 LaTeX 원고

## 구조

- `main.tex`: IEEEtran/kotex 기반 메인 원고. 패키지가 없는 현재 서버에서는 2단 fallback 사용
- `sections/`: 절별 LaTeX 파일
- `figures/generate_figures.py`: 결과 JSON에서 CSV와 그림을 재생성
- `figures/data/`: 그림에 사용한 추적 가능한 CSV
- `figures/*.pdf`: 편집ㆍ제출용 벡터 그림
- `figures/*.png`: 현재 LaTeX 원고에 연결한 220 dpi 호환 그림
- `FIGURE_PROMPTS.md`: 그림을 다시 디자인할 때 사용할 상세 프롬프트

## 빌드

```bash
make figures
make
```

현재 서버에는 `IEEEtran.cls`, `kotex.sty`, `latexmk`가 없으므로 `main.tex`의 fallback과 직접 XeLaTeX/BibTeX 빌드를 사용한다. 정식 제출 환경에서 해당 패키지가 존재하면 IEEEtran 템플릿을 자동으로 선택한다.

## 수치 출처

- 시간 계약: `artifacts/results/public/small-vlm-guard-v0/temporal-guard-multiseed-v0/summary.json`
- 다중 maneuver/hard: `artifacts/results/public/small-vlm-guard-v0/maneuver-guard-multiseed-v0/summary.json`
- R1 진단: `docs/reports/SAFETY_CONSTRAINED_COC_PROGRESS_REPORT_V01.md`
- Release reversal: `artifacts/results/public/contract-microworld-v2/pilot-release-reversal-2026-08-04-v1/DEEP_STRESS_ASSESSMENT_KO.md`
