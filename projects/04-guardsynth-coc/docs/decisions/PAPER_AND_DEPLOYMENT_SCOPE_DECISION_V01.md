# 1차 논문과 2차 자율주행 심화 개발의 범위 분리

- project_id: `guardsynth-coc`
- 결정 ID: `GS-PAPER-SCOPE-001`
- 결정일: 2026-09-06
- 상태: `APPROVED_SCOPE_NOT_EXECUTED`
- 승인 근거: 연구 책임자의 네 가지 핵심 주장 중심 범위 축소 및 단계 분리 요청
- 상위 문서: [연구계획 v2.3](../plans/01_RESEARCH_PLAN_V02.md)
- 실행 문서: [마일스톤](../plans/02_PROJECT_MILESTONES.md), [학습 요구사항](../requirements/M18_EBLC_LEARNING_EFFECT_REQUIREMENTS_V01.md)
- 2026-09-06 명확화: 1차는 실제 이미지/영상 기반 VLM의 가중치/내부 adapter 학습이 필수다.
  full fine-tuning은 선택이며, 고정 VLM+별도 scorer·text-only 학습·prompt/SAT만으로 대체 불가

## 1. 판단: 1차 논문보다 넓었던 연구프로그램

v2.2까지는 제약 추출·학습 효과와 함께 범용 EBLC 언어, 세 slice/six families, 14종 baseline,
다중 관할 source closure, 대규모 closed-loop, Alpamayo integration, 전문가 생산성 및 실차
준비를 하나의 critical path로 묶었다. 각 주제에는 별도의 정답·대조군·표본·한계가 필요하다.
앞선 일관성 감사는 누락된 검증을 복구했지만, 그것이 모두 한 논문의 필수 조건인지는 구분하지
못했다. 또한 E4-L은 EBLC 판정의 preference 학습이지 자연어 제약 삽입을 직접 검증하는 설계가
아니었다. 사용자가 명시한 전달 경로로 primary 실험을 바로잡는다.

범위를 줄이는 대상은 주장 수와 적용 범위다. source 정직성, 독립 test/gold, 동일 학습 예산,
실제 가중치 업데이트, 부정 결과 보고는 제거하지 않는다. 이전 artifact와 1/60 집계는
보존한다. scope 변경만으로 기존 실패를 통과시키거나 새 적격 장면을 만들어내지 않는다.

## 2. 1차 논문의 한 가지 중심 주장

> 선언된 주행 의사결정 과제에서, CoC·장면·외부 근거로 추출한 제약을 EBLC로 명세·검증하고
> 의미를 보존한 자연어 제약으로 되돌려 CoC 학습 supervision에 넣으면, 동일 예산의 원본
> CoC 학습보다 제약 위반이 줄고 정상 행동 수행이 유지되는가?

‘모든 CoC에 제약이 필수’라는 보편 명제나 실차 안전성은 주장하지 않는다. 강화된 학습은
제약 기반 supervision의 실효성을 뜻하며 reinforcement learning 알고리즘을 필수로 뜻하지 않는다.
여기서 1차/2차는 Project 04 안의 연구 단계다. 기존 `paper1`/`paper3`나 Project 01/05의
논문을 재명명하거나 동일 기여를 중복 출판한다는 뜻이 아니다.

| 핵심 주장 | 1차 논문에 필요한 증거 | 담당 |
|---|---|---|
| C1. 제약 추가의 필요성/효용 | 같은 task의 원본 CoC 대 제약 강화 학습 비교, 위반·정상 행동을 함께 측정 | M15/M18 |
| C2. 무엇을 어디서 어떻게 추출하는가 | CoC는 intent/target 후보, scene은 관측 조건, rule/system source는 규범, 물리식은 근거 있는 수치; field별 provenance와 abstention | M12/M14/M16 |
| C3. EBLC 검증과 자연어 전달 | 사용된 EBLC subset의 type/unit/일관성·bounded 검증, CNL의 조건·대상·부정/의무·해제·수치 보존, 검증 생략 대조 | M14/M17 |
| C4. 자연어 제약을 넣은 실제 학습 효과 | 실제 checkpoint·≥3 paired seeds·동일 데이터/학습 예산, no-shield 독립 held-out 평가 | M18/M20 |

SAT는 외부 근거의 진실성이나 안전 보증이 아니다. CNL의 결정론적 생성도 학습 모델의 이해나
행동 준수를 보증하지 않는다. C3의 의미보존 검사와 C4의 실제 행동 평가를 모두 수행한다.

## 3. 범위 재단

| 항목 | 1차 논문 | 2차 심화 개발/별도 연구 |
|---|---|---|
| 데이터·모델·행동 범위 | 주 데이터셋 1개, trainable VLM 1개, 주 행동군 1개와 대비 행동군 1개 이내; M12에서 source와 표본으로 사전 동결 | 세 slice 전체/six families, 추가 dataset/model, 광범위 OOD |
| source | 논문에서 실제 쓰는 clause의 근거만 감사; 국가 whitelist 없이 benchmark source scope 명시 | 전체 catalog/다중 관할 coverage, 국내법 적용·운영 assurance |
| 24/60/18-cell | 고정 24 dry-run·60 formal pilot·18 joint quota를 1차 선행조건에서 해제. 기존 60/98 검토는 후보/개발 자료로 재사용 | 기존 엄격한 M13/M16 확장 protocol은 별도 실행 전 갱신·동결 |
| 표본 수·검토 | 임의 소수로 완료하지 않음. pilot/dev 분산으로 학습 효과·정상 행동 유지의 N을 test 전 결정, 독립 gold와 표본 선정/제외 보고 | 대규모 source review·전문가 생산성 3-arm 연구 |
| geometry | 주장에 필요한 관측/단위/수치만 source-bound; 정량 claim에는 실제 metric 근거 필요 | 모든 장면의 metric rig geometry·장기 lifecycle·센서 통합 |
| EBLC/BCV | 사용 subset의 명세·검증·CNL 의미보존, 검증 생략 ablation | 일반 언어/모든 target 신규성은 Project 05; 광범위 stress/translation 경쟁은 별도 |
| 학습 비교 | L0–L3 네 arm, 공통 seed/budget와 제한된 독립 행동 평가 | B0–B13 전수·선행 시스템 완전 재현·다중 학습법 |
| 평가 환경 | 고정 후보 행동/궤적 과제; 안전하게 진행 가능한 후보를 독립 판정. offline이면 closed-loop/goal completion으로 부르지 않음 | ≥2,000 closed-loop rollout, simulator 다양화, long-horizon goal completion |
| 적용·효용 | 학습 신호 효과만 필수; reviewer 시간은 예산 관리용 | M19 Alpamayo·verifier/reranker/shield, M20-R01 전문가 생산성 연구 |
| 실차 | 제외 | M21 SIL/HIL/shadow·승인된 시험장·차량 assurance |

제약을 사전 정의한 가상 환경으로 보완할 경우 별도의 controlled-simulation cohort로 명시한다.
실제 장면의 누락 geometry·관할·track을 합성해 source-complete로 바꾸는 것은 계속 금지한다.
1차 결과는 선택된 benchmark/model에서만 주장하며 실제 차량 효과로 외삽하지 않는다.

## 4. 최소 비교 실험과 자연어 전달

| Arm | CoC 학습 supervision | 비교 목적 |
|---|---|---|
| L0 | 원본 CoC + 공통 action/trajectory target | 제약 없는 학습 기준 |
| L1 | 동일 근거에서 직접 생성한 자연어 제약 + 동일 공통 target | 아무 자연어 가드나 추가해도 되는지 |
| L2 | EBLC 후보 → 동일 CNL renderer, 검증/repair/선별 생략 | 검증 단계의 순효과 |
| L3 | source-bound EBLC → 검증 → CNL → CoC에 삽입 | 제안 방법 |

L2는 과거 flat/preference arm을 재정의한 v2.3 arm이며 versioned manifest에서 구분한다.
정상 텍스트로 표현할 수 없는 malformed EBLC는 공통 parse 경계에서 abstain하고 semantic
오류·미검증 제약은 기록한다. 두 arm의 repair/selection·coverage 차이를 숨기지 않는다.
L3은 CNL 자체를 실제 training example의 supervision으로 사용한다. EBLC로 preference label만
만들고 CNL을 학습에 넣지 않는 실행은 이 실험 완료가 아니다. 공통 action label을 arm마다
바꾸지 않아 학습 효과와 행동 정답 교체 효과를 혼동하지 않는다.

기본 방식은 CoC/CNL/action target의 supervised fine-tuning이다. 정확한 input/target 위치,
loss mask·weight, 추론 시 자기 생성 CoC 유무는 M18-S02에서 고정한다. 추론에서 gold CNL이나
정답 guard를 외부 제공하지 않고 verifier/shield를 붙이지 않는다. L0의 짧은 텍스트에 따른
token/update/compute 차이 및 L1–L3 텍스트 길이를 통제·보고한다. 필요하면 dev에서 동일
길이 무관 텍스트 대조를 점검하되 그것을 다섯 번째 필수 대규모 학습 arm으로 자동 확대하지 않는다.

L3−L0은 제약 추가, L3−L1은 전체 파이프라인, L3−L2는 검증 기여의 증거다. L0만 이기면
EBLC/검증 방식의 우월성을 주장하지 않는다. 모든 대조군을 이긴다고 사전 가정하지 않는다.
기존 flat representation·lifecycle-off·BCV-only preference·with-shield ablation은 후속으로 둔다.

## 5. 실행 경로와 원고 구성

1차: M12 제한 source/task 동결 → M14 EBLC/CNL 경로 + M15 네 arm 계약 → M16 필요한 source와
독립 gold 검토 → M17-S01 split/gold lock + M17-S02 생성·검증·CNL 품질 → M18 실제 학습/평가
→ M20 원고/재현 패키지. M13 24장면 전체와 M19는 이 경로의 선행조건이 아니다.
2차: M20 이후 별도 scope/resource 승인 → M13 확장/M16 formal60·M18 runtime 확장 → M19 → M21.
2차 task는 QUEUED(DEFERRED_PHASE2)이며 완료·취소로 표시하지 않는다.

원고 본문은 문제/가설, 단일 파이프라인, 데이터·최소 비교 설계, 학습 효과와 검증 ablation,
한계의 흐름으로 구성한다. 핵심 표는 source/제약 예시, 생성·CNL 품질, L0–L3 학습 효과 정도로
집중한다. schema 전체, solver query 예시, 상세 source 표·검토 지침·추가 실패 사례는 부록이나
재현 자료로 둔다. 결과의 반례·실패·coverage는 본문에서도 숨기지 않는다. 저널별 페이지 수는
투고처를 선택할 때 확인하며 현재 임의 page cap을 정하지 않는다.

## 6. supersession 및 종료 조건

이 결정과 v2.3 1차 계약이 v2.2 감사의 모든 보완을 1차 필수로 묶던 규칙을 대체한다.
R01(source)·R03(사용 subset)·R05(독립 검토)·R06(통계)·R07(split)은 축소 범위로 유지한다.
R02 전체24·R04 전체 baseline·R08 광범위 runtime·R09 Alpamayo·R10 효용은 2차로 이관한다.
그 사실상의 결함을 해결했다고 표시하지 않으며, 해당 후속 주장을 할 때 다시 요구한다.

M20은 C1–C4 증거와 E4-L 실제 학습·CNL 사용·예산·독립 평가 보고서를 필수로 요구한다.
여기서 실제 학습은 동일 초기 VLM의 L0–L3 fine-tuning이며, 독립 평가는 held-out 이미지/영상에서
그 VLM의 행동/궤적 선택을 평가하는 것이다. 설명 문장 품질이나 별도 scorer 성능은 대체물이 아니다.
긍정 결과는 완료의 전제가 아니며 NOT_SUPPORTED/INCONCLUSIVE도 그대로 보고한다.
미실행을 긍정 결과로 대체하거나 삭제하지 않는다. 기존 60-scene 1/60은 종전 cohort의
역사적 수치이고 1차 새 범위의 적격성/진행률은 `NOT_EVALUATED`다. validator/UI 변경과
새 cohort 산정은 다음 실행이며 이번 계획 변경만으로 구현이 바뀌지는 않는다.
