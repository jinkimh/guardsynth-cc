# ALP-EXP-005 원격 실행 Runbook

## 1. 목적

공식 `nvidia/Alpamayo-R1-10B` 모델에 공식 PhysicalAI AV clip을 입력하여 다음 산출물을 직접 생성한다.

1. Alpamayo Chain-of-Causation reasoning trace
2. trace와 함께 생성된 6.4초 미래 trajectory
3. 동일 시점의 기록 ground-truth trajectory
4. 모델, 데이터, 입력, seed와 실행환경 provenance

이 실험부터는 annotation conformance가 아니라 **Alpamayo model-output consistency**를 다룬다.
그러나 단일 또는 소수 추론 결과로 모델의 물리적 안전성을 주장하지 않는다.

## 2. Reference configuration

| 항목 | 고정값 |
|---|---|
| Experiment ID | `ALP-EXP-005` |
| Model | `nvidia/Alpamayo-R1-10B` |
| Model revision | `da911c5319ea5fd5c3de77f430f755f34ffd836e` |
| Model execution | BF16, non-quantized |
| Alpamayo code revision | `7da704aaaa56b2a0bbce9b7c404ca40b16ed2c93` |
| PhysicalAI AV revision | `b719eea7f0a63619ef51ec7f54178af0937ef050` |
| Python | 3.12.x |
| PyTorch | 2.8.0 |
| Transformers | 4.57.1 |
| Cameras | cross-left, front-wide, cross-right, front-tele |
| Camera history | 4 frames/camera, 0.4초 |
| Egomotion history | 16 waypoints, 10 Hz |
| Future trajectory | 64 waypoints, 10 Hz, 6.4초 |
| `top_p` | 0.98 |
| `temperature` | 0.6 |
| `num_traj_samples` | 1 |
| `max_generation_length` | 256 |
| Reference seed | 42 |
| Replication seeds | 42, 43, 44 |

새 Alpamayo 1.5가 존재하더라도 이 실험에서는 모델을 바꾸지 않는다. 1.5 비교는 별도 experiment ID로
수행한다.

## 3. 필요한 장비

### Reference run

- Linux
- NVIDIA GPU VRAM 24GB 이상
- CUDA 호환 NVIDIA driver
- RAM 32GB 이상 권장
- 디스크 여유 60GB 이상
- 인터넷 연결

권장 GPU는 RTX 3090/4090, A5000, A6000, A100 또는 H100이다. 16GB GPU의 CPU offload와 8-bit
양자화는 탐색 실행에는 사용할 수 있지만 reference result로 분류하지 않는다.

## 4. 계정과 라이선스

실행자는 개인 Hugging Face 계정에서 다음 접근 조건을 충족해야 한다.

1. `nvidia/PhysicalAI-Autonomous-Vehicles` 접근 승인
2. NVIDIA Autonomous Vehicle Dataset License 직접 동의
3. `nvidia/Alpamayo-R1-10B` model license 확인
4. 로컬 `hf auth login`

토큰을 prompt, source code, shell history 공유본, 결과 JSON 또는 로그에 기록하지 않는다. 데이터,
영상, annotation과 생성 결과는 access-controlled storage에만 둔다.

## 5. 입력 clip 선택

두 실행 모드를 구분한다.

### Mode A: 공식 smoke test

공식 GitHub 예제의 clip과 시점을 사용한다.

```text
clip_id = 030c760c-ae38-49aa-9ad8-f5650a545d26
t0_us   = 5100000
```

이 mode는 model loading과 trace 생성 확인용이다. 이 clip은 `ood_reasoning.parquet` cohort에 속하지
않으므로 human-refined event annotation과 직접 비교하지 않는다.

### Mode B: annotation-aligned experiment

`ood_reasoning.parquet`에서 다음 조건으로 clip을 선택한다.

- `split == val`
- event 수 2개 이상
- egomotion과 4개 필수 camera feature 존재
- 선택 event의 `t0_us > 1,600,000`
- `t0_us + 6,400,000`이 egomotion 범위 안에 존재

선택한 `clip_id`와 `t0_us`는 외부 prompt에 직접 넣지 않고 원격 보안 환경의 실행 변수로 전달한다.

## 6. 설치

```bash
git clone https://github.com/NVlabs/alpamayo.git
cd alpamayo
git checkout 7da704aaaa56b2a0bbce9b7c404ca40b16ed2c93

curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

uv venv --python 3.12 ar1_venv
source ar1_venv/bin/activate
uv sync --active

hf auth whoami
nvidia-smi
```

설치 후 다음을 기록한다.

```bash
python --version
python -c 'import torch, transformers; print(torch.__version__, transformers.__version__)'
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
git rev-parse HEAD
```

## 7. 실행기 요구사항

공식 `src/alpamayo_r1/test_inference.py`를 기반으로 `run_alp_exp_005.py`를 만든다. 다음 argument를
지원해야 한다.

```text
--clip-id
--t0-us
--seed
--output-dir
--model-revision
--attn-implementation flash_attention_2|sdpa
```

실행기는 다음을 수행한다.

1. `load_physical_aiavdataset()`으로 4-camera/egomotion 입력을 로드한다.
2. 모델 revision을 명시하여 BF16 가중치를 로드한다.
3. 공식 processor와 message template을 사용한다.
4. seed를 CPU 및 CUDA에 모두 설정한다.
5. `sample_trajectories_from_data_with_vlm_rollout()`을 호출한다.
6. `extra["cot"][0]`을 추출한다.
7. predicted/ground-truth trajectory를 원본 정밀도로 저장한다.
8. minADE를 계산하되 안전 metric으로 해석하지 않는다.
9. 입력과 출력 shape, NaN/Inf, special-token 종료 여부를 검증한다.
10. provenance manifest를 저장한다.

## 8. Reference run

```bash
python run_alp_exp_005.py \
  --clip-id "$TARGET_CLIP_ID" \
  --t0-us "$TARGET_T0_US" \
  --seed 42 \
  --model-revision da911c5319ea5fd5c3de77f430f755f34ffd836e \
  --attn-implementation flash_attention_2 \
  --output-dir restricted-results/alp-exp-005/reference-seed-42
```

FlashAttention 설치 또는 GPU 호환 문제가 있을 때만 `sdpa`로 다시 실행한다. 이 경우 manifest의
`reference_class`를 `COMPATIBILITY_FALLBACK_SDPA`로 기록한다.

## 9. Replication run

reference run 성공 후 동일 입력으로 seed만 변경한다.

```bash
for seed in 42 43 44; do
  python run_alp_exp_005.py \
    --clip-id "$TARGET_CLIP_ID" \
    --t0-us "$TARGET_T0_US" \
    --seed "$seed" \
    --model-revision da911c5319ea5fd5c3de77f430f755f34ffd836e \
    --attn-implementation flash_attention_2 \
    --output-dir "restricted-results/alp-exp-005/seed-$seed"
done
```

seed별 CoC 문장과 trajectory를 덮어쓰지 않는다.

## 10. 필수 출력

```text
restricted-results/alp-exp-005/<run-id>/
├── manifest.json
├── generated_coc.txt
├── generated.json
├── predicted_trajectory.npz
├── ground_truth_trajectory.npz
├── metrics.json
└── inference.log
```

### `manifest.json`

```json
{
  "experiment_id": "ALP-EXP-005",
  "model_id": "nvidia/Alpamayo-R1-10B",
  "model_revision": "da911c5319ea5fd5c3de77f430f755f34ffd836e",
  "code_revision": "7da704aaaa56b2a0bbce9b7c404ca40b16ed2c93",
  "dataset_id": "nvidia/PhysicalAI-Autonomous-Vehicles",
  "dataset_revision": "b719eea7f0a63619ef51ec7f54178af0937ef050",
  "clip_id": "<restricted>",
  "t0_us": 0,
  "seed": 42,
  "dtype": "bfloat16",
  "quantized": false,
  "attention_implementation": "flash_attention_2",
  "num_traj_samples": 1,
  "top_p": 0.98,
  "temperature": 0.6,
  "max_generation_length": 256,
  "provenance_class": "MODEL_GENERATED",
  "publication_control": "LICENSE_RESTRICTED_INTERNAL_RESULT"
}
```

### `generated.json`

```json
{
  "coc_nonempty": true,
  "coc_character_count": 0,
  "trajectory_shape": [1, 1, 1, 64, 3],
  "rotation_shape": [1, 1, 1, 64, 3, 3],
  "contains_nan_or_inf": false,
  "generated_coc_path": "generated_coc.txt",
  "predicted_trajectory_path": "predicted_trajectory.npz"
}
```

CoC 원문은 console에 길게 출력하지 않고 제한 파일에만 저장한다.

## 11. 성공 조건

reference run은 다음을 모두 만족해야 성공이다.

- model 및 dataset revision이 manifest와 일치
- 4개 camera x 4 frames 입력 확보
- 16개 ego-history waypoint 확보
- CoC trace가 비어 있지 않음
- predicted trajectory가 64 future waypoint를 포함
- trajectory와 rotation에 NaN/Inf가 없음
- `num_traj_samples == 1`
- BF16, non-quantized 실행
- 결과와 로그에 access token이 없음
- 모든 결과가 restricted output directory에 존재

## 12. 실패 처리

### CUDA OOM

1. 다른 GPU process를 종료한다.
2. `num_traj_samples=1`인지 확인한다.
3. 공식 입력 해상도, camera 수, history와 horizon을 임의 축소하지 않는다.
4. 24GB 이상 GPU로 이동한다.
5. CPU offload는 `EXPLORATORY_CPU_OFFLOAD` 별도 run으로만 수행한다.
6. 8-bit/4-bit는 reference run으로 사용하지 않는다.

### FlashAttention 오류

`sdpa`로 재실행하고 compatibility fallback임을 manifest에 기록한다. 두 결과를 동일 reference class로
합치지 않는다.

### GatedRepo / 401

브라우저에서 dataset access 상태를 확인한 뒤 실행 머신에서 다시 `hf auth login`한다. 토큰을 command
argument로 직접 전달하지 않는다.

### `<traj_future_start>` 미생성

실패 결과와 seed를 보존하고 재시도 횟수를 기록한다. 성공한 trace로 조용히 대체하지 않는다.

## 13. 후속 검증

생성 결과를 기존 timed-contract pipeline에 연결할 때 세 계층을 분리한다.

```text
human-refined event annotation    OBSERVED_ANNOTATION
Alpamayo generated CoC            MODEL_GENERATED_REASONING
Alpamayo generated trajectory     MODEL_GENERATED_ACTION
recorded future trajectory        OBSERVED_EGOMOTION
```

다음 비교를 수행한다.

1. 생성 CoC의 행동과 생성 trajectory의 방향 일치
2. 생성 trajectory와 기록 trajectory의 open-loop 차이
3. 생성 CoC와 human-refined annotation의 의미 차이
4. seed에 따른 reasoning 및 trajectory 변동
5. 후보 timed contract와 mutation에 대한 UPPAAL 판정

minADE 또는 한 trace의 conformance를 충돌 안전성 증거로 사용하지 않는다.

## 14. 원격 실행 후 가져올 것

라이선스상 허용되는 보안 경로를 통해 다음 제한 산출물만 현재 연구환경으로 이동한다.

- run directory 전체
- 설치 및 GPU 환경 요약
- 성공/실패 상태
- 변경된 실행 코드의 patch

공개 issue, public repository, paste service 또는 일반 메신저에 CoC 원문, 영상, trajectory와 token을
올리지 않는다.
