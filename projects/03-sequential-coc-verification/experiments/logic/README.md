# Bounded temporal logic feasibility

이 디렉터리는 실제 생성 CoC와 6.4초 predicted trajectory에 대해 다음 세
판정을 분리하는 예비 실험이다.

1. `SAT`: 추출된 동시 행동 명제의 Boolean 일관성
2. `SMT`: CoC 행동과 전체 trajectory의 실수값 제약 일관성
3. `bounded temporal SMT`: 시간별 ego/obstacle footprint 안전 계약

## 방법 선택

| 방법 | v0 역할 | 이유 |
|---|---|---|
| SAT | 이산 의미 모순 대조군 | 연속 속도ㆍ거리와 threshold sensitivity를 직접 표현하기 부족하다. |
| SMT (Z3) | **주 검증기** | Boolean 의미, 실수 속도ㆍ거리, 복수 threshold 및 unsat core를 한 bounded model에서 다룬다. |
| UPPAAL | protocol/deadline 대조군 | 기존 실험에서 의무 순서와 deadline mutation은 검증했지만 실제 거리ㆍ충돌은 `UNKNOWN`이었다. |
| STL | 다음 단계 monitor | 연속 trace robustness에 적합하지만 v0의 불확실한 이산 해석과 counterexample core에는 SMT가 더 간단하다. |

주 검증기는 Z3의 Boolean과 quantifier-free linear real arithmetic만 사용한다.
무한 시간 또는 신경망 전체를 검증하지 않는다.

## 실행

```bash
export PYTHONPATH="$PWD/third_party/physical_ai_av/src:$PWD/projects/03-sequential-coc-verification/experiments/feasibility:$PWD/projects/03-sequential-coc-verification/experiments/logic"

runtime/alpamayo/ar1_venv/bin/python \
  projects/03-sequential-coc-verification/experiments/logic/test_bounded_temporal_smt.py

runtime/alpamayo/ar1_venv/bin/python \
  projects/03-sequential-coc-verification/experiments/logic/build_logic_inputs.py

runtime/alpamayo/ar1_venv/bin/python \
  projects/03-sequential-coc-verification/experiments/logic/run_bounded_temporal_smt.py
```

기본 결과는 제한 결과 아래에 저장한다.

```text
artifacts/results/restricted/alp-exp-005/feasibility-batch-v0/
  bounded-temporal-smt-v0/verification-result.json
```

결과 파일에는 원문 CoC를 쓰지 않고 SHA-256과 추출된 action만 쓴다.

## 판정 의미

- `stable_action_trajectory_contradiction`: 평가 가능한 모든 threshold에서
  CoC action과 trajectory가 모순된다.
- `CONDITIONAL_UNSAFE_WITNESS_ROBUST_TO_TESTED_MARGINS`: coarse object
  association과 constant-motion, axis-aligned footprint 가정에서 0/0.25/0.5m
  margin 모두 predicted trajectory에는 overlap이 있고 같은 checker가 recorded
  future에는 overlap을 찾지 못했다.
- `MARGIN_SENSITIVE_CONDITIONAL_WITNESS`: 0m에서는 위 조건이 성립하지만 safety
  margin을 넓히면 recorded-future negative control도 실패한다.
- `strong_joint_candidate`: 위 두 조건이 동시에 성립한다.

어느 conditional witness도 실제 충돌 판정이 아니다. 객체 identity, 좌표 변환,
yaw를 포함한 footprint, road geometry와 동역학을 독립적으로 확인해야 한다.
recorded future에도 overlap을 찾으면 checker artifact일 가능성이 있으므로 후보를
자동 기각한다.

STOP history 실험도 포함한다. 과거 속도가 일정 시간 threshold 아래였는지만 SMT로
검사하며, stop line과 표지 적용 범위를 복원하지 못했으므로 legal stop 판정은 항상
`UNKNOWN`으로 유지한다.

## Phase-aware 재분석 v1

v0의 endpoint 중심 action 판정이 감속 후 재가속이나 작은 회피 후 복귀를 모순으로
과대 계수하는지 확인하려면 다음을 실행한다.

```bash
export PYTHONPATH="$PWD/projects/03-sequential-coc-verification/experiments/logic:$PWD/projects/03-sequential-coc-verification/experiments/feasibility"

runtime/alpamayo/ar1_venv/bin/python \
  projects/03-sequential-coc-verification/experiments/logic/test_phase_aware_alignment.py

runtime/alpamayo/ar1_venv/bin/python \
  projects/03-sequential-coc-verification/experiments/logic/analyze_phase_aware_alignment.py

runtime/alpamayo/ar1_venv/bin/python \
  projects/03-sequential-coc-verification/experiments/feasibility/build_phase_aware_alignment_review.py
```

재분석은 action을 `response → hold → release` 국면으로 나눈다. target identity,
간격 또는 hazard clearance가 필요한데 현재 trace에 없으면 `UNKNOWN`으로 abstain한다.
결과와 A/B 블라인드 검토 화면은 각각 아래에 저장된다.

```text
artifacts/results/restricted/alp-exp-005/feasibility-batch-v0/
  phase-aware-alignment-v1/
  phase-aware-review-v1/
```

검토 화면은 source episode, seed와 자동 판정을 숨긴다. 모델 입력 16프레임은 장면
문맥 보조 자료일 뿐 recorded future가 아니며, 이 검토로 물리 안전을 판정하지 않는다.

## STOP/YIELD 속도 증가 집중 후보

signed longitudinal speed를 기준으로 STOP/YIELD 계획 중 의미 있는 전진 재가속 또는
near-stop 이후 후진이 있는 후보만 모으려면 다음을 실행한다.

```bash
export PYTHONPATH="$PWD/projects/03-sequential-coc-verification/experiments/feasibility:$PWD/projects/03-sequential-coc-verification/experiments/logic"
runtime/alpamayo/ar1_venv/bin/python \
  projects/03-sequential-coc-verification/experiments/logic/collect_safety_acceleration_focus.py
```

기본 결과는 `safety-acceleration-focus-v1/`에 CSV, JSON과 독립형 증거 HTML로
저장된다. 후보는 one-shot plan 수준이며 실제 실행 위반이나 사고로 해석하지 않는다.
