# 실제 차량 검증 후속 단계 이관 결정 v1

- 결정일: 2026-08-12
- 상태: `ACCEPTED`
- 적용 프로젝트: GuardSynth-CoC
- 관련 단계: P1, P4–P6, M13–M21

## 결정

현재 연구·개발 critical path에서는 실제 차량 assurance profile과 실제 차량 실증을 요구하지
않는다. 실제 차량 단계는 다음 조건이 모두 충족된 이후의 후속 실증으로 이관한다.

1. 현재 계획의 방법·소프트웨어·데이터·전문가 평가 마일스톤 완료
2. 논문 원고와 재현 패키지 완성
3. 특허 출원 필요성 검토 및 출원하기로 결정한 경우 출원 신청 완료

출원·공개 순서와 권리 범위는 이 기술 문서가 판단하지 않으며 별도 전문가 검토를 따른다.

## 현재 대체 경로

현재 24장면 dry run은 다음 입력 경계를 사용한다.

```text
source-linked 실제/파생 장면 근거 8종
                       +
별도 binding의 simulation assurance profile
                       ↓
        GuardSynth → EBLC → Core → Z3
```

실제/파생 장면의 timestamp, ego state, actor track, target–zone association, geometry,
coordinate transform, applicable rule source와 recorded-rig binding은 임의 합성하지 않는다.
제동·지연 값만 명시적인 `SIMULATION_MODEL_SPECIFICATION`에서 가져온다.

## 주장 경계

- 이 경로의 24장면 결과는 방법·소프트웨어의 scene-grounded simulation 평가다.
- 실제 차량 source-complete, 실제 제동 성능, 충돌 감소 또는 차량 안전성 검증으로 부르지 않는다.
- recorded vehicle binding과 simulation vehicle binding을 합치지 않는다.
- CoC는 `CLAIMED`로만 보존하고 관측 사실이나 규범 authority로 승격하지 않는다.
- bounded SMT 결과는 계약·변환·질의의 제한된 일관성 근거이지 차량 안전 증명이 아니다.

## 일정 영향

- `GS-P1-SIM24-001`을 현재 활성 작업으로 둔다.
- 기존 실제 차량 24장면 gate는 현재 critical path의 선행조건에서 제거한다.
- 실제 차량 assurance 취득과 실증은 `M21`에서 재개한다.
- M14–M20은 simulation/recorded-data 주장 경계 안에서 진행하며 실제 차량 효과를 주장하지 않는다.
