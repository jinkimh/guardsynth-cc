# Alpamayo 전용 실험

이 디렉터리는 논문 원고와 분리된 Alpamayo 생태계 전용 실험 인덱스다.

## 실험 목록

| ID | 실험 | 상태 | 상세 결과 |
|---|---|---|---|
| `ALP-EXP-001` | 공식 reasoning annotation 기반 연속 시간계약 및 UPPAAL feasibility | 완료 | [내부 보고서](../evidence/data/nvidia_physicalai/internal-derived/ALPAMAYO_EXPERIMENT_REPORT.md) |
| `ALP-EXP-002` | 병렬 obligation 및 braking-priority 의미론 비교 | 예정 | - |
| `ALP-EXP-003` | CoC hazard와 obstacle track의 semantic association | 예정 | - |
| `ALP-EXP-004` | 상태 의존 safe-distance 계약 | 예정 | - |
| `ALP-EXP-005` | 실제 Alpamayo 모델 출력의 reasoning-trajectory 검증 | 원격 실행 패키지 준비 | [Runbook](ALP-EXP-005-REMOTE-RUNBOOK.md), [Agent prompt](ALP-EXP-005-REMOTE-AGENT-PROMPT.md) |

## 범위

`ALP-EXP-001`은 NVIDIA PhysicalAI AV의 공식 reasoning annotation과 주행 데이터를 사용한다.
Alpamayo 모델 가중치를 직접 추론한 실험은 아직 수행하지 않았다. 따라서 현재 결과를
`Alpamayo model safety evaluation`으로 표현하지 않는다.

## 접근 통제

공식 데이터 기반 상세 결과는 NVIDIA Autonomous Vehicle Dataset License의 confidentiality와
redistribution 제한을 받는다. 원문, clip별 측정치, UPPAAL 모델과 trace는
`evidence/data/nvidia_physicalai/internal-derived/` 아래에만 저장한다.

사본과 해시는 [COPY_MANIFEST.md](../evidence/data/nvidia_physicalai/COPY_MANIFEST.md)에서 관리한다.

## 재현 진입점

```bash
python3 feasibility/analyze_nvidia_official_cohort.py
python3 feasibility/analyze_nvidia_obstacle_feasibility.py
python3 uppaal/run_nvidia_official_cohort.py
python3 -m unittest discover -s feasibility -p 'test_*.py'
```

구현과 비공식 CoC-Nusc 선행 실험을 포함한 전체 기술 문서는
[feasibility README](../feasibility/README.md)를 참고한다.
