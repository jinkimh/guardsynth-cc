# CoC E2E Driving Formal Verification Project

Alpamayo의 Chain-of-Causation(CoC) reasoning trace와 trajectory를 분석하고, grounded STL 계약과 CBF 안전 필터를 학습 및 폐루프 평가에 연결하는 연구 프로젝트다.

## 빠른 진입점

- 현재 연구계획: [`RESEARCH_PLAN_V1.md`](docs/plans/alpamayo-coc-formal-verification/RESEARCH_PLAN_V1.md)
- 방법 선택 근거: [`METHOD_SELECTION_SURVEY.md`](docs/decisions/alpamayo-coc-formal-verification/METHOD_SELECTION_SURVEY.md)
- GPU reference inference: [`ALP-EXP-005-REMOTE-RUNBOOK.md`](experiments/alpamayo/ALP-EXP-005-REMOTE-RUNBOOK.md)
- 실제 생성 CoC 결과 인덱스: [`artifacts/results/restricted/README.md`](artifacts/results/restricted/README.md)
- 보존된 GPU 실행환경: [`runtime/README.md`](runtime/README.md)
- CPU feasibility: [`experiments/feasibility/README.md`](experiments/feasibility/README.md)
- bounded temporal SMT feasibility: [`experiments/logic/README.md`](experiments/logic/README.md)
- CASCADE–PhysicalAI sensor pairing smoke test: [`data/restricted/nvidia_cascade/internal-derived/smoke-test-1/README.md`](data/restricted/nvidia_cascade/internal-derived/smoke-test-1/README.md)
- UPPAAL baseline: [`experiments/uppaal/README.md`](experiments/uppaal/README.md)
- 프로젝트 구조와 배치 규칙: [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md)

## 디렉터리

```text
guardsynth-cc/
├── docs/                      # 요구사항, 계획, 설계, 서베이, 보고서
├── src/                       # 공개 가능한 최종 재사용 코드
├── cli/pipelines/<domain>/    # 목적별 실행 인터페이스
├── tests/                     # 유지보수되는 패키지 테스트
├── experiments/               # 실험 정의, 프로토콜, fixture, 로컬 분석
├── artifacts/
│   ├── intermediate/          # 재생성 가능한 중간 산출물
│   └── results/
│       ├── public/            # 공개 synthetic/baseline 결과
│       └── restricted/        # 접근 통제 결과
├── papers/                    # 논문 원고와 투고 준비 자료
├── data/
│   ├── baseline/              # 공개ㆍ재현용 최소 데이터
│   └── restricted/            # 접근 통제 데이터와 내부 파생물
├── third_party/               # pinned upstream source checkouts
├── runtime/                   # 실제 실행에 사용한 checkout과 Python 환경
├── archive/                   # 이전 계획, handoff manifest, 원본 설치 archive
├── requirements-local.txt
└── MANIFEST.sha256
```

## 가장 먼저 할 일

1. `data/restricted/nvidia_physicalai/LICENSE.pdf`를 확인한다.
2. Hugging Face에서 `nvidia/Alpamayo-R1-10B`와 `nvidia/PhysicalAI-Autonomous-Vehicles` 접근 권한을 확인한다.
3. GPU 환경은 `experiments/alpamayo/ALP-EXP-005-REMOTE-RUNBOOK.md`를 따라 구성한다.
4. 생성 결과는 `artifacts/results/restricted/` 아래에만 저장한다.
5. 토큰, 원본 제한 데이터 및 clip별 내부 측정치를 공개 저장소에 업로드하지 않는다.

## GPU 기준

- NVIDIA GPU VRAM 24GB 이상
- RAM 32GB 이상 권장
- 여유 디스크 60GB 이상
- Linux와 CUDA 호환 driver
- Python 3.12
- reference run은 BF16, non-quantized

24GB 미만 GPU, quantization 또는 CPU offload가 필요한 결과는 reference 결과와 분리한다.

## 설치

포함된 ALP-EXP-005 실행환경을 재사용할 때:

```bash
cd runtime/alpamayo
source ar1_venv/bin/activate
python --version
nvidia-smi
```

환경을 새로 만들 때:

```bash
cd third_party/alpamayo
git status --short
git rev-parse HEAD

curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12 ar1_venv
source ar1_venv/bin/activate
uv sync --active

hf auth whoami
nvidia-smi
```

CPU-side 최소 환경:

```bash
python3 -m venv .venv-local
source .venv-local/bin/activate
pip install -r requirements-local.txt
export PYTHONPATH="$PWD/third_party/physical_ai_av/src:$PWD/experiments/feasibility:$PWD/experiments/uppaal"
python3 -m unittest discover -s experiments/feasibility -p 'test_*.py'
python3 -m unittest discover -s experiments/uppaal -p 'test_*.py'
```

로컬 UPPAAL verifier는 `runtime/solvers/uppaal-5.0.0-linux64/bin/verifyta`에 격리되어
있다. 실행에는 유효한 UPPAAL license가 필요하며, 다른 설치를 쓰려면 해당 `verifyta`
경로를 runner에 명시한다.

## 무결성

현재 구조에서 제한 결과, 대형 가상환경 및 설치된 UPPAAL 배포본 등을 제외한 공개 파일
해시는 프로젝트 루트에서 확인한다. 정확한 제외 규칙은
`cli/checks/build_manifest.py`가 단일 기준이다.

```bash
sha256sum -c MANIFEST.sha256
```

handoff 당시의 원래 목록과 manifest는 `archive/handoff/`에 보존한다. 구조 변경 이후의 현재 기준은 루트 `MANIFEST.sha256`이다.
제한 결과는 `artifacts/results/restricted/MANIFEST.sha256`으로 별도 검증한다.

## 주장과 보안 경계

- `data/restricted/nvidia_physicalai/reasoning/`은 공식 annotation이며 새로 생성한 모델 CoC가 아니다.
- 실제 Alpamayo model-output 연구는 ALP-EXP-005 결과부터 시작한다.
- 포함된 ALP-EXP-005 seed 42ㆍ43ㆍ44 결과는 실제 생성 CoC와 trajectory지만 SDPA compatibility fallback 결과이며 FlashAttention 2 reference 결과가 아니다.
- STL 만족은 전체 물리 안전 증명이 아니다.
- CBF 보증은 명시한 동역학, 상태 추정, uncertainty 및 feasibility 가정에 한정된다.
- 단일 clip이나 소수 seed로 전체 모델 안전을 주장하지 않는다.
