# ALP-EXP-005 원격 Coding Agent Prompt

아래 `Prompt` 블록을 24GB 이상 NVIDIA GPU가 연결된 원격 coding agent에게 그대로 전달한다.
`TARGET_CLIP_ID`와 `TARGET_T0_US`는 공개 prompt에 넣지 말고 원격 보안환경의 환경변수로 설정한다.

## Prompt

```text
당신은 NVIDIA Alpamayo 공식 모델의 재현 가능한 추론 실험을 수행하는 senior ML systems engineer다.
계획만 제안하지 말고 설치, 구현, 단일 추론, 검증과 결과 저장까지 완료하라.

실험 ID: ALP-EXP-005

목표:
공식 nvidia/Alpamayo-R1-10B 모델에 NVIDIA PhysicalAI AV의 공식 clip을 입력하여 새
Chain-of-Causation reasoning trace와 대응 6.4초 trajectory를 생성한다. 생성 CoC, predicted
trajectory, ground-truth trajectory와 완전한 provenance를 제한 디렉터리에 저장한다.

중요한 범위:
- 이것은 Alpamayo model-output 생성 및 consistency feasibility 실험이다.
- 단일 결과로 모델 안전성, 충돌 부재 또는 D=1s의 정당성을 주장하지 않는다.
- NVIDIA 데이터와 파생 결과는 라이선스 제한 내부 자료다.
- 데이터, 영상, CoC, trajectory를 public repository나 외부 서비스에 업로드하지 않는다.
- Hugging Face token을 코드, 로그, prompt, 결과 파일 또는 답변에 노출하지 않는다.

Reference pins:
- model: nvidia/Alpamayo-R1-10B
- model revision: da911c5319ea5fd5c3de77f430f755f34ffd836e
- Alpamayo Git revision: 7da704aaaa56b2a0bbce9b7c404ca40b16ed2c93
- dataset: nvidia/PhysicalAI-Autonomous-Vehicles
- dataset revision: b719eea7f0a63619ef51ec7f54178af0937ef050
- Python: 3.12.x
- torch: 2.8.0
- transformers: 4.57.1
- dtype: bfloat16
- quantization: none
- top_p: 0.98
- temperature: 0.6
- num_traj_samples: 1
- max_generation_length: 256
- seed: 42
- attention: flash_attention_2; 호환 실패 때만 sdpa fallback

하드웨어 gate:
1. 시작하자마자 nvidia-smi, VRAM, RAM, disk를 확인하라.
2. GPU VRAM이 24GB 미만이면 reference run을 수행하지 말고 BLOCKED_INSUFFICIENT_VRAM으로 종료하라.
3. CPU offload 또는 8-bit/4-bit 결과를 reference 결과로 위장하지 마라.
4. disk 여유가 60GB 미만이면 중단하라.

인증 gate:
1. hf auth whoami로 인증 여부만 확인하라. token 값은 출력하지 마라.
2. nvidia/PhysicalAI-Autonomous-Vehicles 접근을 작은 metadata 파일로 확인하라.
3. 401/GatedRepo이면 사용자가 브라우저에서 접근 동의하고 로컬 hf auth login을 마칠 때까지 중단하라.

입력:
- 환경변수 TARGET_CLIP_ID와 TARGET_T0_US가 있으면 annotation-aligned mode로 사용하라.
- 없으면 공식 smoke-test clip 030c760c-ae38-49aa-9ad8-f5650a545d26, t0_us=5100000을 사용하라.
- smoke-test clip 결과를 human-refined annotation 비교로 표현하지 마라.

실행 단계:
1. NVlabs/alpamayo를 clone하고 Git revision을 정확히 checkout하라.
2. uv로 Python 3.12 virtual environment를 만들고 공식 dependency를 설치하라.
3. 설치 버전, Git revision, GPU와 driver 정보를 기록하라.
4. 공식 src/alpamayo_r1/test_inference.py를 읽고 그 API를 그대로 사용하라.
5. run_alp_exp_005.py를 구현하라. 다음 CLI를 지원해야 한다:
   --clip-id, --t0-us, --seed, --output-dir, --model-revision,
   --attn-implementation.
6. load_physical_aiavdataset으로 4 cameras x 4 frames, 16 ego-history points와 64 future GT points를 로드하라.
7. from_pretrained에 model revision을 명시하고 BF16 non-quantized 모델을 CUDA에 로드하라.
8. 공식 processor, create_message와 sample_trajectories_from_data_with_vlm_rollout을 사용하라.
9. CPU/CUDA seed를 모두 설정하고 num_traj_samples=1로 추론하라.
10. extra["cot"][0], pred_xyz, pred_rot와 GT trajectory를 추출하라.
11. CoC는 console에 전문을 출력하지 말고 restricted output 파일에만 기록하라.
12. trajectory shape, 64-waypoint horizon, NaN/Inf와 빈 CoC를 검증하라.
13. minADE를 계산하되 safety metric이라고 부르지 마라.
14. 아래 산출물을 모두 저장하라.

필수 산출물:
restricted-results/alp-exp-005/reference-seed-42/
  manifest.json
  generated_coc.txt
  generated.json
  predicted_trajectory.npz
  ground_truth_trajectory.npz
  metrics.json
  inference.log

manifest 필수 필드:
experiment_id, model_id, model_revision, code_revision, dataset_id,
dataset_revision, clip_id, t0_us, seed, dtype, quantized,
attention_implementation, num_traj_samples, top_p, temperature,
max_generation_length, GPU name/VRAM, torch/transformers versions,
provenance_class=MODEL_GENERATED,
publication_control=LICENSE_RESTRICTED_INTERNAL_RESULT.

성공 기준:
- CoC가 비어 있지 않다.
- predicted trajectory는 64 future waypoint를 가진다.
- 모든 trajectory/rotation 값이 finite다.
- model/data/code revision이 manifest에 고정된다.
- BF16이며 quantization을 사용하지 않는다.
- token 또는 credential이 어떤 산출물에도 없다.
- 실행 command와 종료 상태가 기록된다.

실패 처리:
- CUDA OOM이면 입력 camera 수, 해상도, history, trajectory horizon을 몰래 줄이지 마라.
- GPU process 정리와 num_traj_samples=1을 확인한 후에도 OOM이면 reference run을 실패로 기록하라.
- FlashAttention만 실패하면 sdpa로 한 번 재시도하고 reference_class를
  COMPATIBILITY_FALLBACK_SDPA로 기록하라.
- <traj_future_start>가 생성되지 않거나 CoC가 비면 seed와 실패 출력을 보존하라.
- 성공한 결과만 골라 실패를 삭제하지 마라.

Reference run 성공 후:
- 동일 입력, 동일 설정에서 seed 42, 43, 44 replication run을 각각 독립 디렉터리에 저장하라.
- seed 간 CoC 동일/상이 여부, trajectory pairwise ADE를 summary.json에 기록하라.
- CoC 전문은 summary나 최종 답변에 복사하지 마라.

최종 답변 형식:
1. EXECUTED / BLOCKED / FAILED 상태
2. 사용한 GPU 및 pinned revisions
3. 입력 mode와 shape
4. CoC nonempty 여부와 문자 수만 보고
5. predicted trajectory shape와 finite 여부
6. minADE 및 seed 간 차이. safety metric이 아님을 명시
7. 결과 디렉터리와 생성 파일 목록
8. fallback, 경고와 남은 제한

원본 CoC, clip 영상, trajectory 배열, token은 최종 답변에 직접 노출하지 마라.
```

## 원격 결과를 받은 뒤

결과 디렉터리를 access-controlled 경로로 가져온 후 `ALP-EXP-005` provenance validator와
reasoning-trajectory contract extractor를 현재 프로젝트에서 실행한다. 원격 agent의 요약만 받고 원본
산출물을 확보하지 못한 경우 실험 상태를 `UNVERIFIED_REMOTE_CLAIM`으로 기록한다.
