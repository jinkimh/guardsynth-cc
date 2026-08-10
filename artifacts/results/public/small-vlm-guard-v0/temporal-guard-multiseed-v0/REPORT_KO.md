# STOP–HOLD–RELEASE–GO 다중 seed 재현 결과

- seeds: `[42, 17, 123]`
- 모든 seed에서 동일 데이터 규모, epoch, optimizer 설정 사용

## Held-out 평균 ± population standard deviation

| 조건 | 정확도 | Guard 위반 ↓ | Deadlock ↓ | 안전+목표완료 ↑ | 계약전환 pair ↑ |
|---|---:|---:|---:|---:|---:|
| Requirement CoC | 0.500 ± 0.000 | 0.319 ± 0.052 | 0.000 ± 0.000 | 0.681 ± 0.052 | 0.000 ± 0.000 |
| Inline NL constraint | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| Separate NL guard | 0.698 ± 0.094 | 0.191 ± 0.136 | 0.000 ± 0.000 | 0.809 ± 0.136 | 0.396 ± 0.187 |
| Shuffled guard | 0.510 ± 0.015 | 0.333 ± 0.023 | 0.000 ± 0.000 | 0.667 ± 0.023 | 0.021 ± 0.029 |
| Logic guard | 0.538 ± 0.027 | 0.274 ± 0.108 | 0.000 ± 0.000 | 0.726 ± 0.108 | 0.076 ± 0.055 |

## Seed별 핵심 값

- Requirement CoC: pair `[0.0, 0.0, 0.0]`, safe-goal `[0.625, 0.75, 0.6666666666666666]`
- Inline NL constraint: pair `[1.0, 1.0, 1.0]`, safe-goal `[1.0, 1.0, 1.0]`
- Separate NL guard: pair `[0.3958333333333333, 0.625, 0.16666666666666666]`, safe-goal `[0.6979166666666666, 1.0, 0.7291666666666666]`
- Shuffled guard: pair `[0.0625, 0.0, 0.0]`, safe-goal `[0.65625, 0.6979166666666666, 0.6458333333333334]`
- Logic guard: pair `[0.10416666666666667, 0.125, 0.0]`, safe-goal `[0.6770833333333334, 0.875, 0.625]`

## 추가 seed 실행 전 선언한 진단 기준

- PASS: `inline_mean_violation_at_most_0p10`
- PASS: `inline_mean_safe_goal_at_least_0p90`
- PASS: `separate_mean_pair_beats_shuffled_by_0p20`
- PASS: `separate_mean_safe_goal_beats_coc_only`
- FAIL: `separate_unseen_mean_safe_goal_at_least_0p70`

## 해석

- Inline과 separate 조건은 동일한 자연어 제약 정보를 받으며, 차이는 정보 위치와 구획 형식이다.
- 단일 seed 우위가 반복되지 않으면 표현의 본질적 우위가 아니라 optimization variance로 해석한다.
- Logic guard는 별도 parser 없이 VLM 텍스트 입력으로만 사용했으므로 실행 가능한 정형 검증기 성능을 뜻하지 않는다.
- 본 결과는 합성 후보 선택 재현성 진단이며 실제 도로 안전 증거가 아니다.
