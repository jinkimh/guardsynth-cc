# 국내 저널 논문 최신 관련 연구 및 차별성 개정 설계

## 목적

2025년 말부터 2026년 7월까지 공개된 CoC/VLA 연구를 반영하여
`projects/sequential-coc-verification/paper/manuscript` 논문의 관련 연구, 서론의 차별성, 기여 주장과 요약을
일관되게 개정한다. 기존 연구와 중복되는 넓은 주장을 제거하고, 본 논문의 실제
실험이 지지하는 범위인 **학습 전 시간·출처 계약 감사**를 중심 차별성으로
명확히 한다.

## 핵심 재정의

본 논문은 다음을 최초 또는 주된 기여로 주장하지 않는다.

- CoC가 장면과 일치하는지 측정하는 일반적 faithfulness 평가
- CoC와 trajectory의 행동 정합성 또는 인과적 영향 측정
- 센서 perturbation에 대한 CoC 안정성 평가
- 반사실적 추론을 이용한 unsafe action 교정
- perception grounding 또는 trajectory consistency reward를 통한 CoC 학습
- CBF, shield 또는 폐루프 제어를 통한 물리 안전 보장

본 논문이 다루는 좁은 문제는 다음과 같다.

> 이미 생성된 시점별 CoC 판단과 기록된 자차 움직임을 학습 데이터로 사용하기
> 전에, 판단 사건이 언제 의무를 열고, 반복 판단이 기한을 유지·재시작·병합하며,
> 어떤 자차 반응이 의무의 응답 증거가 되고, 장면 간 의무 이월에 필요한 출처가
> 입증되었는지를 상태를 가진 시간 관찰자로 검사한다.

이 위치는 기존 충실도·개입·학습 개선·실행 안전 연구를 대체하지 않는다. 그보다
앞선 데이터 준비 단계에서 시간 의미론과 출처 정합성을 검사하는 전처리 관문이다.

## 개정 범위

### 1. 요약

현재 요약을 약 25--35% 줄인다. 다음 네 요소만 남긴다.

1. CoC가 학습 가능한 의미 신호이지만 판단과 반응의 시간 의미론은 자동으로
   주어지지 않는다는 문제
2. CoC-Nusc 판단, 자차 움직임과 출처를 UPPAAL 시간 관찰자로 변환하는 방법
3. 94개 장면, 134개 계약, 282개 모델, 1,128개 질의의 핵심 결과
4. 물리 안전성 증명이 아니라 학습 전 프로토콜 감사라는 범위 제한

반복되는 배경 설명, 차량 동역학 한계의 세부 열거와 연결 체인 실험의 세부 수치는
본문으로 이동하거나 요약에서 생략한다.

### 2. 서론

추론 보강이 학습 가능한 중간 표현이라는 동기는 유지한다. 다만 최신 연구를 다음과
같이 명시한다.

- CoC 장면 충실도와 reasoning-action 불일치는 이미 직접 측정되었다.
- CoT 개입으로 trajectory에 대한 인과적 영향을 평가하는 벤치마크가 존재한다.
- 센서 perturbation과 객체 제거에 따른 추론·궤적 변화가 대규모로 분석되었다.
- 반사실적 추론과 perception-grounded CoC는 모델의 행동을 교정하거나 학습을
  개선한다.

따라서 서론의 문제 간극은 “CoC가 맞는가”가 아니라 “시점이 있는 CoC-trajectory
주석을 하나의 에피소드 의무로 해석할 때 필요한 반복·기한·응답 매칭·장면 출처
규칙이 명시되어 있는가”로 바꾼다.

연구 질문은 유지하되 RQ와 기여 앞에 최신 연구와의 관계를 한 문단으로 추가한다.
기여 문구에서는 `새로운 안전 검증기`, `CoC의 안전성을 검증`과 같은 넓은 표현을
사용하지 않고 `시간·출처 프로토콜 감사`, `학습 전 정합성 관문`을 사용한다.

### 3. 관련 연구

관련 연구를 네 묶음으로 재구성한다.

#### 3.1 CoC 충실도와 행동 인과성

- Is VLA Reasoning Faithful?: Alpamayo-R1 100개 장면, 300회 추론의 entity/action
  fidelity와 reasoning-action consistency
- VLADriveBench: 관측 지표와 CoT 개입을 결합한 CoT-action 관계 평가
- Lost in Fog: 약 2,000개 장면과 18,000회 추론에서 센서 perturbation에 따른
  CoC/trajectory 안정성
- Counter-nuScenes/CVAA: 객체 제거를 통한 trajectory causal influence

차이: 위 연구들은 장면 충실도, 입력 변화, 객체 또는 CoT 개입에 대한 출력 변화를
검사한다. 본 논문은 모델 추론을 다시 실행하거나 객체를 제거하지 않고, 기록된
시계열 주석에서 지속되는 의무의 상태와 기한 판정을 검사한다.

#### 3.2 추론을 이용한 행동 교정과 학습 개선

- Counterfactual VLA: self-reflective counterfactual reasoning으로 meta-action 교정
- C-CoT: 대안 행동 결과를 평가하는 구조화된 반사실적 추론
- WorkDrive: roadwork perception grounding, CoC supervision과 lateral
  meta-action/trajectory consistency reward

차이: 이 연구들은 더 나은 추론 또는 trajectory를 생성하도록 모델을 바꾼다. 본
논문은 생성 모델이나 정상 trajectory를 만들지 않고, 기존 학습 쌍의 시간·출처
정합성을 감사하여 유지·검토·제외 후보를 구분한다.

#### 3.3 실행 안전 계층과 정형 보증

- VLSA/AEGIS: 로봇 조작 VLA에 CBF 기반 plug-and-play safety constraint layer를
  결합하며, 자율주행 CoC 연구로 잘못 기술하지 않는다.
- UPPAAL, STL, RSS, reachability, Scenic/VerifAI: 명시적 환경·동역학·속성을
  이용하는 정형 또는 시나리오 기반 보증

차이: 본 논문은 액추에이터와 상대 객체 동역학이 없어 물리 안전성을 주장하지
않는다. UPPAAL은 차량 제어기를 검증하기보다 데이터의 판단-응답 프로토콜을
감사하는 관찰자로 사용한다.

#### 3.4 본 연구의 위치

마지막 문단은 다음 세 층을 분리한다.

1. 충실도·인과성 연구: CoC가 맞고 행동에 영향을 주는가
2. 학습·실행 안전 연구: 추론 또는 행동을 어떻게 고치거나 제한하는가
3. 본 연구: 저장된 CoC-trajectory 학습 쌍이 상태를 가진 시간·출처 계약으로
   해석될 수 있는가

이 세 층은 대체 관계가 아니라 순차적이고 상호 보완적인 보증 단계임을 밝힌다.

### 4. 관련 연구 비교표

기존 표를 최신 연구가 보이도록 확장한다. 열은 다음과 같다.

- 접근 또는 대표 연구
- 주된 검사/개입 단위
- 모델 재추론 또는 입력 개입 여부
- 상태를 가진 반복·기한 의무
- 장면 연결 출처 검사
- 결과 또는 주장 범위

표의 행은 최소한 다음 묶음을 포함한다.

- CoC faithfulness / VLADriveBench
- Lost in Fog / Counter-nuScenes
- Counterfactual VLA / C-CoT / WorkDrive
- VLSA/AEGIS 및 물리 안전 계층
- 본 연구

표가 2단 폭에서 과밀해지면 연구별 한 행이 아니라 목적이 같은 연구군별로 묶는다.

### 5. 참고문헌

`references.bib`에 다음 8개 arXiv 항목을 추가한다.

- arXiv:2605.17268
- arXiv:2606.12706
- arXiv:2512.24426
- arXiv:2605.10744
- arXiv:2607.14727
- arXiv:2512.11891
- arXiv:2605.21446
- arXiv:2607.16938

서지 정보는 arXiv의 현재 제목, 저자, 연도와 식별자를 사용한다. 학회 게재가
확인된 경우에도 원고가 직접 확인한 범위를 넘는 venue 주장은 피한다.

## 검증 기준

- 요약이 기존보다 25--35% 짧아야 한다.
- 새 논문 8개가 관련 연구 또는 서론에서 실제로 인용되어야 한다.
- VLSA/AEGIS를 자율주행 실험으로 잘못 소개하지 않아야 한다.
- `first`, `최초`, `유일` 같은 우선권 주장을 새로 넣지 않아야 한다.
- 본 연구의 결과를 collision 감소, physical safety 또는 closed-loop safety로
  확대하지 않아야 한다.
- 기존 연구와의 차이가 시간 의무의 lifecycle, 반복 의미론, 응답 증거 매칭과
  장면 출처로 구체화되어야 한다.
- BibTeX와 LaTeX 빌드에서 미정의 인용 및 치명적 오류가 없어야 한다.
- 기존 실험 수치, RQ, 모델 구조와 결론의 범위는 변경하지 않아야 한다.

## 산출물

- 수정된 `projects/sequential-coc-verification/paper/manuscript/main.tex`의 요약
- 수정된 `projects/sequential-coc-verification/paper/manuscript/sections/01-introduction.tex`
- 전면 개정된 `projects/sequential-coc-verification/paper/manuscript/sections/02-related-work.tex`
- 최신 논문 항목이 추가된 `projects/sequential-coc-verification/paper/manuscript/references.bib`
- 재빌드된 `projects/sequential-coc-verification/paper/manuscript/main.pdf`

