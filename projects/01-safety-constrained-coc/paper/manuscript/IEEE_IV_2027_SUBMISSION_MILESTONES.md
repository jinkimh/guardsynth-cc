# Safety-Constrained CoC: IEEE IV 2027 제출 마일스톤과 Todo

- 문서 성격: 국제학회 확장을 위한 실행 마일스톤 원장(living document)
- 작성 기준일: 2026-08-10
- 기반 원고: [KIEE 심사용 원고](latex-kiee-review-2022/main.tex)
- 실험 감사: [EXPERIMENT_RESULT_AUDIT.md](latex-kiee-review-2022/EXPERIMENT_RESULT_AUDIT.md)
- 장기 확장안: [INTERNATIONAL_JOURNAL_EXPANSION_PLAN.md](INTERNATIONAL_JOURNAL_EXPANSION_PLAN.md)
- 1차 목표 학회: IEEE Intelligent Vehicles Symposium 2027 (IEEE IV 2027)
- 공식 학회 안내: [IEEE IV 2027](https://ieee-iv.org/2027/intelligent-vehicles-symposium-2027-perth-australia/)
- IEEE 출판 정책: [Submission and Peer Review Policies](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/)
- 내부 제출 마감: **2026-10-01**
- 공식 일정 주의: IV 2027 안내 페이지에는 2026-11-15가 표시되어 있으나, IV 2026 공지는
  IV 2027부터 고정 10월 1일 마감으로 복귀한다고 명시한다. 공식 CFP와 PaperPlaza가
  확정될 때까지 더 이른 10월 1일을 내부 마감으로 사용한다. 근거는
  [IV 2026 Contributions 공지](https://ieee-iv.org/2026/contributions/)에 보존한다.
- 현재 단계: `IV00 READY_NEXT`
- 최종 목적: 합성 후보 선택의 feasibility 원고를 실행 가능한 궤적, 동일 모델 폐루프,
  강한 기준선과 OOD 통계를 갖춘 국제학회 논문으로 확장

## 1. 이 문서의 범위

이 문서는 현재 Safety-Constrained CoC 논문을 IEEE IV 2027에 제출하기 위한 계획이다.
다음 두 연구를 혼합하지 않는다.

| 구분 | 이 문서의 범위 | GuardSynth-CoC 장기 연구의 범위 |
|---|---|---|
| 입력 가드 | 이미 주어진 실행 가드 | 장면·CoC·근거에서 가드 합성 |
| 중심 문제 | 가드에 따른 궤적 ranking과 실행 검사 | 근거 결합, EBLC 합성 및 양방향 검증 |
| 주요 증거 | 실행 가능한 후보와 동일 VLM 폐루프 | source-bearing 실제 장면과 전문가 평가 |
| 목표 산출물 | IEEE IV 2027 conference paper | T-IV/T-ITS급 후속 연구 |

따라서 이번 제출을 위해 실제 법규 가드 자동 생성, 전체 EBLC catalog 또는 Alpamayo 전체
미세조정을 선행조건으로 만들지 않는다. 반대로 합성 A/B/C/D 선택 결과만 영어로 옮긴 것을
국제학회 확장으로 간주하지 않는다.

## 2. 상태와 운영 규칙

| 상태 | 의미 |
|---|---|
| `COMPLETE` | Todo와 종료 gate를 모두 충족하고 근거 artifact가 있음 |
| `READY_NEXT` | 바로 시작할 수 있는 다음 마일스톤 |
| `ACTIVE` | 현재 구현·실험·작성 중 |
| `QUEUED` | 선행조건을 기다리는 작업 |
| `BLOCKED` | 외부 결정·입력·권한 없이는 진행할 수 없음 |
| `PARTIAL` | 일부 산출물은 있으나 종료 gate 미통과 |
| `NO_GO` | 사전 기준 미달로 현재 학회 제출을 중단하거나 범위를 전환함 |

운영 원칙은 다음과 같다.

1. 체크박스는 파일, 실행 로그 또는 검산 결과가 있을 때만 `[x]`로 바꾼다.
2. 데이터 분할, 기준선, 지표와 Go/No-Go 기준은 main 실험 전에 동결한다.
3. 위반률만 낮추고 항상 정지하는 방법을 성공으로 판정하지 않는다.
4. Qwen 후보 선택과 별도 2층 신경망의 결과를 같은 시스템의 증거로 합치지 않는다.
5. 합성·시뮬레이션 결과를 실제 차량 안전 보장으로 표현하지 않는다.
6. 국내 저널과 국제학회에 실질적으로 같은 원고를 동시에 제출하지 않는다.
7. 실험이 사전 gate를 통과하지 못하면 수치를 숨기지 않고 benchmark/failure-analysis
   논문으로 주장을 축소하거나 ITSC/저널 일정으로 이월한다.

## 3. 현재 출발점

### 3.1 확보된 증거

- [x] Qwen3-VL-2B-Instruct + LoRA 기반 정적·시간·다중 주행 후보 선택 구현
- [x] 같은 장면과 후보에서 가드만 교체하는 paired-contract 평가
- [x] 표준 시간 과제 3-seed 결과 재현: 제안 조건 위반률 0, 목표 완료율 1,
  paired accuracy 1
- [x] 정지·차선 변경 표준 평가 3-seed 재현
- [x] 표현 변화, 미관측 수치와 영상 절제 평가
- [x] 미관측 시간값의 약한 일반화 공개: 위반률 0.351, paired accuracy 0.306
- [x] 원시 예측 단위 재집계와 저장 adapter GPU 재평가
- [x] 위반률·목표 완료·교착·과도한 보수성의 분리 보고
- [x] 별도 소형 신경망 폐루프 결과를 보조 증거로 명확히 제한

### 3.2 국제학회 제출 전 핵심 간극

- [ ] 단순 guard text 추가와 구별되는 학습·추론 방법
- [ ] A/B/C/D 문자가 아닌 실행 가능한 궤적 후보
- [ ] Qwen/VLM 후보 선택기를 그대로 사용하는 폐루프 실행
- [ ] prompt-only, hard-negative, verifier-only 등 강한 기준선
- [ ] 수치·단위·비교 연산자 OOD에 대한 구조적 대응
- [ ] 고정 데이터에서의 학습 seed와 환경 seed 분리
- [ ] 독립 evaluator, 신뢰구간, 효과크기와 paired 통계
- [ ] 익명 IEEE 형식의 영어 원고와 공개 재현 패키지

## 4. 국제학회용 중심 주장과 최소 기여

### 4.1 목표 주장

> Paired counterfactual contracts와 guard-aware ranking을 사용하면, 비전-언어 주행 모델은
> 동일 목표를 달성하는 실행 가능한 궤적 중 현재 계약에 맞는 후보를 더 잘 선택하며,
> 독립 실행 검증기와 결합했을 때 폐루프 위반을 줄이면서 목표 진행성을 유지한다.

이 주장은 다음 세 부분이 모두 입증될 때만 사용한다.

1. **방법 기여:** 표준 SFT를 넘는 guard-aware pairwise/ranking 목적함수 또는 구조화 계약
   처리 방법이 명확해야 한다.
2. **평가 기여:** 가드만 바뀌면 정답 궤적도 바뀌는 paired-contract benchmark가 장면
   shortcut과 always-stop을 검출해야 한다.
3. **시스템 증거:** 동일 VLM ranker를 폐루프에서 사용하고 안전·진행성·승차감을 함께
   평가해야 한다.

### 4.2 주장하지 않을 것

- 실제 차량의 충돌 감소 또는 도로 안전성 보장
- 자연어 가드가 법적으로 완전하거나 실제 도로 규칙을 모두 포괄한다는 주장
- 보지 않은 모든 수치·단위 관계에 대한 일반화
- Alpamayo-R1을 학습하여 개선했다는 주장
- 별도 소형 신경망 폐루프 수치를 Qwen의 폐루프 성능으로 해석

## 5. 전체 마일스톤 요약

| ID | 마일스톤 | 목표 기간 | 상태 | 핵심 종료 gate |
|---|---|---|---|---|
| IV00 | 투고 경로·중복 출판·공식 일정 확인 | 08-10~08-12 | `READY_NEXT` | 합법적 단일 투고 경로와 실제 마감 확정 |
| IV01 | 국제학회 주장·방법·평가 protocol 동결 | 08-11~08-15 | `READY_NEXT` | claim card, baseline, split, Go/No-Go 고정 |
| IV02 | 실행 가능한 paired-contract benchmark | 08-13~08-23 | `QUEUED` | 3개 maneuver 폐루프 실행 가능 |
| IV03 | Guard-aware ranking과 hybrid method | 08-16~08-27 | `QUEUED` | 표준 SFT와 구별되는 방법 및 ablation |
| IV04 | 동일 VLM 폐루프 pilot와 중간 판단 | 08-24~08-30 | `QUEUED` | 효과·진행성 pilot gate 통과 |
| IV05 | Main multi-seed 폐루프 실험 | 08-29~09-10 | `QUEUED` | locked protocol의 main 결과 완성 |
| IV06 | OOD·ablation·통계·실패 분석 | 09-07~09-16 | `QUEUED` | 핵심 주장별 CI와 failure taxonomy |
| IV07 | 영어 원고·그림·표 작성 | 09-01~09-20 | `QUEUED` | 익명 IEEE 원고 완성 |
| IV08 | 재현성·주장·내부 심사 감사 | 09-18~09-25 | `QUEUED` | 모든 수치 재계산, blocker 0건 |
| IV09 | 최종 제출 패키지 | 09-25~10-01 | `QUEUED` | PaperPlaza 제출과 receipt 보존 |
| IV10 | 심사 대응과 저널 확장 | 제출 이후 | `QUEUED` | rebuttal/camera-ready 또는 후속 전환 |

## 6. 의존 관계와 critical path

```text
IV00 투고 가능성
 └─ IV01 주장·protocol 동결
     ├─ IV02 실행 benchmark
     └─ IV03 guard-aware method
          └─ IV04 동일 VLM 폐루프 pilot ── Go/No-Go
              ├─ IV05 main multi-seed
              └─ IV06 OOD·ablation·통계
                    └─ IV07 영어 원고
                        └─ IV08 독립 감사
                            └─ IV09 제출
                                └─ IV10 심사/저널 확장
```

IV02와 IV03, 그리고 IV05 이후의 결과 분석과 원고 작성은 일부 병행할 수 있다. 하지만
IV01의 분할·기준선 동결 전 main 결과를 만들거나, IV04 gate 미통과 상태에서 제출용 주장을
고정해서는 안 된다.

## 7. 상세 마일스톤과 Todo

### IV00. 투고 경로·중복 출판·공식 일정 확인

- 상태: `READY_NEXT`
- 우선순위: `P0`
- 선행조건: 없음

Todo:

- [ ] 국내 KIEE 원고의 현재 상태를 `미투고/심사 중/게재 확정/출판` 중 하나로 기록
- [ ] 심사 중이면 동시 제출 금지 여부와 철회 필요성을 저자 전원이 확인
- [ ] 이미 출판됐으면 국제학회 논문의 신규 실질 기여와 겹침을 표로 작성
- [ ] IEEE IV 2027 공식 CFP와 PaperPlaza 개설 여부 확인
- [ ] 공식 abstract/full-paper deadline과 시간대 기록
- [ ] page limit, 익명성, supplementary/video 및 AI 사용 공개 정책 확인
- [ ] 모든 저자의 참가 가능성과 현장 발표 가능성 확인
- [ ] 공식 마감이 11월이어도 내부 10월 1일 마감을 유지할지 결정
- [ ] 단일 투고 경로 결정 기록 작성

종료 gate:

- 국내 원고와 국제 원고의 동시·중복 제출 위험이 없음
- 제출일, 형식, 저자와 발표자가 확정됨
- 불확실한 일정은 공식 근거가 나올 때까지 더 이른 날짜로 관리됨

산출물:

- `SUBMISSION_PATH_DECISION.md`
- 공식 CFP 및 정책 URL 목록

### IV01. 국제학회 주장·방법·평가 protocol 동결

- 상태: `READY_NEXT`
- 우선순위: `P0`
- 선행조건: IV00의 투고 가능성 확인

Todo:

- [ ] 한 문장 문제 정의와 한 문장 중심 주장 확정
- [ ] 국내 원고 대비 신규 기여를 `기존/신규/재사용 금지`로 구분
- [ ] 제안 방법을 `guard-aware pairwise ranker`와 선택적 `runtime verifier`로 명세
- [ ] 입력·출력·가드 schema와 후보 궤적 표현 확정
- [ ] 행동군을 최소 STOP, RELEASE/GO, LANE CHANGE 세 family로 고정
- [ ] 가능하면 YIELD/GAP ACCEPTANCE를 확장 family로 지정
- [ ] B0~B7 기준선 정의와 공정한 정보 budget 고정
- [ ] train/validation/ID/OOD split을 scenario 단위로 고정
- [ ] 환경 seed와 고정 데이터의 optimization seed를 분리
- [ ] 주요·보조 지표와 분모 정의를 metric contract로 작성
- [ ] IV04 pilot과 IV05 main의 Go/No-Go 기준을 실행 전에 고정
- [ ] 원시 결과 schema, run manifest와 artifact 경로 고정

필수 기준선:

| ID | 조건 | 구분하려는 효과 |
|---|---|---|
| B0 | Trajectory/state only | CoC와 가드가 없는 하한 |
| B1 | Basic/requirement CoC | 행동 목표 설명의 효과 |
| B2 | Frozen VLM + guard prompt | 학습 없는 prompting 효과 |
| B3 | Guard text + standard SFT | 현재 국내 원고 방법 |
| B4 | Shuffled guard mapping | 의미 있는 가드 대응 여부 |
| B5 | Hard-negative SFT without guard semantics | 어려운 음성 후보 노출 효과 |
| B6 | Deterministic verifier-only reranking | 완전한 규칙 검사만의 효과 |
| B7 | Proposed guard-aware ranker + verifier | 학습과 runtime assurance의 결합 |

종료 gate:

- 연구 질문마다 이를 반증할 수 있는 비교 조건과 지표가 하나 이상 있음
- main 실험 후 정답이나 결과에 맞춰 split·metric을 바꿀 여지가 제거됨
- 방법 기여가 단순 문자열 삽입과 구별됨

산출물:

- `INTERNATIONAL_CLAIM_AND_PROTOCOL_V01.md`
- versioned split/baseline/metric manifest

### IV02. 실행 가능한 paired-contract benchmark

- 상태: `QUEUED`
- 우선순위: `P0`
- 선행조건: IV01

Todo:

- [ ] simulator를 MetaDrive 우선, CARLA 보조 중 하나로 확정
- [ ] 상태, 관측, route goal과 replanning 주기 정의
- [ ] 각 후보를 waypoint·속도·시간을 포함한 실행 가능한 trajectory로 표현
- [ ] 동일 장면·목표·후보에서 가드만 교체되는 paired contract 생성
- [ ] STOP/APPROACH scenario template 구현
- [ ] HOLD/RELEASE/REACTIVATION scenario template 구현
- [ ] LANE CHANGE COMPLETE/ABORT scenario template 구현
- [ ] 확장 시 YIELD/GAP ACCEPTANCE template 구현
- [ ] permissive/restrictive 계약에서 정답 후보가 실제로 전환되는지 검사
- [ ] 모든 후보에 dynamics feasibility check 적용
- [ ] independent guard monitor 또는 STL robustness evaluator 구현
- [ ] collision, minimum TTC, clearance, stop-line overshoot 계산
- [ ] route completion, progress, deadlock, unnecessary stop 계산
- [ ] acceleration, jerk와 steering-rate 계산
- [ ] 계약과 evaluator가 같은 label lookup을 공유하지 않는지 검사
- [ ] deterministic replay와 boundary equality 회귀 테스트 작성

종료 gate:

- 최소 3개 maneuver family에서 B0, B1, B6를 폐루프로 실행 가능
- paired contract의 두 문제에 같은 scene/candidate set이 사용됨
- 가드 위반 감소와 목표 포기·과도한 보수성을 동시에 측정 가능
- 원시 episode로 모든 집계 지표를 재계산 가능

산출물:

- 공개 가능한 simulator/scenario package
- benchmark schema와 locked pilot split
- evaluator independence note

### IV03. Guard-aware ranking과 hybrid method

- 상태: `QUEUED`
- 우선순위: `P0`
- 선행조건: IV01, IV02의 trajectory schema

Todo:

- [ ] Qwen VLM이 K개 실행 후보에 score 또는 ranking을 출력하도록 변경
- [ ] 동일 scene의 permissive/restrictive 계약 쌍을 한 학습 단위로 구성
- [ ] 계약 교체 시 올바른 후보 순서가 뒤집히도록 pairwise ranking loss 구현
- [ ] guard violation robustness를 이용한 보조 loss 구현 여부 결정
- [ ] 목표 미완료·always-stop에 대한 goal-preservation loss 구현
- [ ] 필요 시 comfort penalty를 보조 항으로 구현
- [ ] 자연어 가드에서 값·단위·연산자를 typed field로 추출하는 경량 parser 구현
- [ ] 원문 가드와 typed contract 중 어느 정보가 모델에 들어가는지 명시
- [ ] inference 시 invalid 후보 masking 또는 verifier reranking 구현
- [ ] no-admissible-candidate fallback과 abstention 동작 정의
- [ ] standard SFT, pairwise-only, violation-only, full objective ablation 작성
- [ ] B2~B7을 동일 backbone, 후보와 학습 budget으로 실행 가능하게 구성
- [ ] 학습·평가 설정, LoRA config와 seed manifest 저장

종료 gate:

- proposed method가 `guard text + standard SFT`와 알고리즘적으로 구별됨
- 모든 ablation이 같은 입력 정보와 계산 budget에서 실행됨
- 가드가 없거나 모순될 때 동작이 fail-closed 또는 명시적 fallback으로 정의됨

산출물:

- 방법 명세와 수식
- training/inference implementation
- ablation config set

### IV04. 동일 VLM 폐루프 pilot와 중간 Go/No-Go

- 상태: `QUEUED`
- 우선순위: `P0`
- 선행조건: IV02, IV03

Todo:

- [ ] 별도 2층 신경망 대신 Qwen 기반 ranker를 planning loop에 연결
- [ ] 매 replanning cycle에서 최신 관측과 현재 계약으로 후보를 다시 선택
- [ ] B1, B3, B4, B5, B6, B7 pilot 실행
- [ ] 최소 20개 parameter configuration × 3 maneuver × 3 seed 실행
- [ ] violation, collision proxy, completion, deadlock과 intervention 집계
- [ ] 정보 지연과 release 후 hazard reappearance stress 실행
- [ ] 선택 실패와 verifier 개입 사례를 trajectory plot으로 검사
- [ ] 학습 label 생성기와 독립 evaluator의 판정 불일치 감사
- [ ] 표준 SFT 대비 proposed method의 효과크기와 불확실성 계산
- [ ] 중간 Go/No-Go 회의 결과를 문서화

Go 기준:

- B3 대비 B7의 가드 위반률이 의미 있게 감소하는 방향
- B1 대비 목표 완료율 손실이 5%p 이내
- B5 hard-negative보다 paired/OOD 조건에서 일관된 이점의 징후
- 3개 maneuver 모두에서 같은 방향의 효과
- verifier 개입 증가만으로 모든 개선이 설명되지 않음

전환 기준:

- 위반은 줄지만 completion이 5%p 넘게 감소하면 progress-aware loss/fallback 수정
- B5와 차이가 없으면 새로운 학습법 주장을 축소하고 benchmark/verifier 논문으로 전환
- Qwen 폐루프 연결이 불가능하면 IV 2027 main-track 제출을 중단하고 ITSC/저널 일정으로 이월
- ID만 개선되고 OOD가 악화되면 구조화 수치 표현을 우선 수정

종료 gate:

- `GO_FULL`, `GO_BENCHMARK`, `REWORK`, `DEFER` 중 하나의 판단이 근거와 함께 기록됨

산출물:

- `IV2027_PILOT_DECISION_V01.md`
- pilot result bundle과 failure examples

### IV05. Main multi-seed 폐루프 실험

- 상태: `QUEUED`
- 우선순위: `P0`
- 선행조건: IV04의 `GO_FULL` 또는 `GO_BENCHMARK`

Todo:

- [ ] main split hash와 config를 잠금
- [ ] 최소 3개, 권장 5개 optimization seed 실행
- [ ] optimization seed마다 같은 test scenarios를 사용해 학습 분산 측정
- [ ] 별도 environment/scenario seed 집합에서 환경 분산 측정
- [ ] B0~B7 전체 조건 실행
- [ ] 최소 3개 maneuver family별 결과 저장
- [ ] standard/ID와 OOD 결과를 완전히 분리
- [ ] hybrid 조건의 verifier intervention 원인 분류
- [ ] always-stop, no-admissible-candidate와 false rejection 집계
- [ ] crash, timeout, parse failure와 OOM을 누락하지 않고 분모에 반영
- [ ] 원시 episode에서 summary를 독립 재계산
- [ ] 실패 run 재실행 정책과 제외 이유 기록

권장 규모:

```text
3 maneuver families
× 50~75 parameter configurations
× 3~5 environment seeds
× locked method conditions
```

규모는 compute pilot 결과에 따라 IV01에서 최종 고정한다. 시간 부족을 이유로 main 결과를 본
후 표본 수를 임의 조정하지 않는다.

종료 gate:

- 모든 primary condition에서 계획된 유효 run의 95% 이상 완료
- 원시 결과와 summary 수치 100% 일치
- main 결과에 사용된 model/config/split/evaluator hash 보존

산출물:

- immutable main result directory
- main metric tables와 run manifest

### IV06. OOD·ablation·통계·실패 분석

- 상태: `QUEUED`
- 우선순위: `P0`
- 선행조건: IV05, IV03 ablation

Todo:

- [ ] 미관측 threshold interpolation과 extrapolation 분리
- [ ] unseen unit, equality boundary와 비교 연산자 평가
- [ ] paraphrase를 수치 변화와 분리한 단일요인 실험
- [ ] unseen guard conjunction과 phase order 평가
- [ ] stale contract와 hazard reappearance 평가
- [ ] blank/conflicting image 절제를 자연 영상 의미 의존성 주장과 분리
- [ ] prompt-only, standard SFT, pairwise, verifier-only, hybrid ablation
- [ ] maneuver별·seed별 breakdown 작성
- [ ] paired bootstrap 95% confidence interval 계산
- [ ] paired test와 effect size 계산
- [ ] seed 수준과 episode 수준 불확실성을 구분
- [ ] multiple comparison이 있으면 보정 방법 명시
- [ ] parse/number/unit/vision/contract/fallback 실패 taxonomy 작성
- [ ] 예상과 다른 음성 결과를 표와 본문에 포함

종료 gate:

- 초록과 결론의 모든 정량 주장에 대응하는 표·CI·원시 근거가 있음
- 일반화되지 않은 요인을 일반화 성공으로 표현한 문장이 없음
- 통계적 유의성과 실제 효과크기를 구분함

산출물:

- statistical analysis notebook/script
- OOD/ablation tables
- failure taxonomy report

### IV07. 영어 원고·그림·표 작성

- 상태: `QUEUED`
- 우선순위: `P1`
- 선행조건: IV01, 주요 방법 확정; IV05 결과와 병행

Todo:

- [ ] 공식 IEEE IV 2027 template 적용
- [ ] 저자·소속·감사의 글을 제거한 익명 제출본 구성
- [ ] 제목을 방법과 증거 범위에 맞게 수정
- [ ] 초록을 문제–방법–평가–핵심 결과–한계 순으로 작성
- [ ] introduction에서 paired-contract와 goal preservation의 필요성 명확화
- [ ] related work를 CoC, VLM driving, constrained planning, runtime assurance로 재구성
- [ ] problem formulation에 objective, guard와 admissible set 정의
- [ ] method에서 pairwise loss, verifier와 fallback 명세
- [ ] experiment에서 simulator, split, baseline, seed와 metric 정의
- [ ] 별도 2층 신경망 결과는 제거하거나 historical motivation으로만 제한
- [ ] main 결과, OOD, ablation과 closed-loop 결과 순서로 구성
- [ ] limitation에 합성 환경, 가드 provenance와 real-road 미검증 명시
- [ ] 표와 그림 내부 텍스트를 영어로 통일
- [ ] Figure 6류 그래프의 oracle은 `Non-deployable oracle upper bound`로 명확히 표기
- [ ] proposed method와 hybrid extension을 범례에서 시각적으로 구분
- [ ] 표마다 지표 방향, 분모, seed와 불확실성 정의 포함
- [ ] conference page limit 안에서 본문·참고문헌·감사의 글 배치 확인
- [ ] AI 도구 사용 공개가 필요하면 학회 정책에 맞게 작성

권장 본문 구조:

1. Introduction
2. Related Work
3. Problem Formulation and Paired-Contract Benchmark
4. Guard-Aware Trajectory Ranking and Runtime Verification
5. Experimental Setup
6. Results and Failure Analysis
7. Limitations and Conclusion

종료 gate:

- 익명성과 page limit 위반 0건
- 국내 원고의 수치와 국제 원고의 재사용 수치가 감사 기록과 일치
- 새 실험이 중심 증거이며 기존 synthetic 결과는 motivation/diagnostic으로 배치

산출물:

- `latex-ieee-iv-2027/` 원고와 PDF
- figure/table source package

### IV08. 재현성·주장·내부 심사 감사

- 상태: `QUEUED`
- 우선순위: `P0`
- 선행조건: IV05~IV07

Todo:

- [ ] 모든 표 수치를 원시 episode에서 다시 계산
- [ ] main text의 숫자와 생성 표의 자동 일치 검사
- [ ] numerator/denominator, seed와 표준편차 정의 확인
- [ ] train/test scenario leakage 검사
- [ ] candidate label·순서 shortcut 검사
- [ ] visual/text shortcut과 정보 leakage 검사
- [ ] verifier와 정답 label 생성의 독립성 감사
- [ ] 주장–실험 traceability matrix 작성
- [ ] 모든 figure caption만 읽어도 비교 조건과 방향을 이해할 수 있는지 검사
- [ ] 영어 용어, 약어와 baseline 이름 일관성 검사
- [ ] 관련 연구 누락과 과도한 신규성 주장 검사
- [ ] 익명성, self-citation, acknowledgment와 PDF metadata 검사
- [ ] 공식 format/page/file-size 검사
- [ ] clean environment에서 주요 결과 재현
- [ ] 최소 2인의 reviewer-style 내부 검토와 답변표 작성
- [ ] 치명적·주요·경미 의견을 분류하고 치명적/주요 의견 모두 처리

필수 주장–증거 질문:

- 가드를 넣어서 좋아진 것인가, 단지 더 많은 정보를 준 것인가?
- 올바른 가드 의미를 학습했는가, 후보 문자를 외웠는가?
- 위반 감소가 항상 정지하거나 verifier가 모두 막은 결과인가?
- 새로운 수치·단위·phase에서도 작동하는가?
- 폐루프 결과가 실제로 같은 Qwen/VLM 시스템의 결과인가?
- evaluator가 학습 label 생성 규칙을 그대로 재사용하지 않았는가?
- 실험 범위를 넘어 실제 차량 안전을 암시하는 문장이 있는가?

종료 gate:

- 표·그림·본문 수치 불일치 0건
- 치명적 및 주요 내부 심사 blocker 0건
- 각 핵심 주장에 독립된 실험 근거와 제한 문장이 있음
- 공개 artifact만으로 핵심 표를 재현 가능

산출물:

- `IV2027_CLAIM_EVIDENCE_MATRIX.md`
- `IV2027_INTERNAL_REVIEW_AUDIT.md`
- reproducibility manifest

### IV09. 최종 제출 패키지

- 상태: `QUEUED`
- 우선순위: `P0`
- 선행조건: IV08

Todo:

- [ ] 최종 공식 마감과 제출 portal 재확인
- [ ] 모든 저자의 이름, 이메일, ORCID와 conflict 정보 확인
- [ ] title, abstract와 keyword를 제출 시스템에 등록
- [ ] genuine abstract 등록 마감이 별도이면 먼저 제출
- [ ] 최종 익명 PDF를 IEEE PDF 검사 도구로 확인
- [ ] supplementary/video 허용 범위와 익명성 확인
- [ ] 선택적으로 3분 이내 closed-loop video 준비
- [ ] 코드·데이터 링크의 익명 접근 여부 확인
- [ ] 모든 저자에게 최종 PDF 승인 받기
- [ ] 제출 후 시스템 PDF를 다시 내려받아 원본과 비교
- [ ] submission ID와 receipt 보존
- [ ] 국내 투고 시스템과 중복 active submission이 없는지 마지막 확인

종료 gate:

- 마감 전 정상 제출되고 모든 저자가 receipt를 확인함
- 제출된 PDF가 승인본과 동일함
- 익명성·중복 제출·필수 field 누락이 없음

산출물:

- 제출 PDF hash
- submission receipt와 checklist

### IV10. 심사 대응과 국제 저널 확장

- 상태: `QUEUED`
- 우선순위: `P1`
- 선행조건: IV09

Todo:

- [ ] 리뷰 수신 즉시 주장별 쟁점과 답변 근거 분류
- [ ] 허용된 rebuttal 범위 안에서만 추가 분석 수행
- [ ] 채택 시 camera-ready에서 저자·감사의 글·공개 링크 복원
- [ ] 채택 시 모든 reviewer response가 반영됐는지 감사
- [ ] 거절 시 리뷰를 method/data/evidence/writing 문제로 분류
- [ ] 결과에 따라 IEEE ITSC 또는 T-IV 확장 경로 결정
- [ ] conference 결과를 후속 저널에서 명시적으로 인용하고 신규 기여표 작성
- [ ] CARLA 자연 영상, 두 번째 VLM과 실제 장면 case study를 저널 확장으로 이월

종료 gate:

- 채택본 제출 또는 다음 venue를 위한 변경 근거와 신규 실험 계획 확정

## 8. 사전 성공 기준

아래 수치는 main 결과를 보기 전에 IV01에서 최종 승인한다. 변경이 필요하면 main split을
실행하기 전에 이유와 버전을 기록한다.

| 평가 영역 | 최소 Go 기준 |
|---|---:|
| 제안법의 B1 대비 가드 위반 상대 감소 | 30% 이상 |
| 제안법의 B3 대비 가드 위반 감소 | 방향 일관 + 95% CI 보고 |
| 목표 완료율의 B1 대비 절대 손실 | 5%p 이하 |
| 정상 admissible trajectory false rejection | 10% 이하 |
| paired-contract accuracy | B3 및 B5보다 개선 방향 |
| maneuver 재현 | 최소 3 family에서 같은 효과 방향 |
| optimization 반복 | 최소 3 seed, 권장 5 seed |
| 원시 결과 재계산 일치 | 100% |
| source 없는 실제 차량 안전 주장 | 0건 |

`B3` 또는 `B5` 대비 통계적으로 분명한 이득이 없어도 benchmark와 실패 분석이 충분히
새로우면 `GO_BENCHMARK`가 가능하다. 이 경우 제목, 초록과 결론에서 새로운 학습법의 우월성
주장을 제거한다.

## 9. 제출 범위 결정표

| IV04/IV06 결과 | 제출 판단 | 논문 중심 |
|---|---|---|
| B7이 B3/B5보다 OOD·폐루프에서 우수 | `GO_FULL` | guard-aware method + benchmark + hybrid |
| 학습법 차이는 약하지만 benchmark/verifier 분석이 강함 | `GO_BENCHMARK` | paired-contract benchmark와 failure analysis |
| 위반 감소가 큰 completion 손실을 동반 | `REWORK` | progress-aware 설계 수정 후 재평가 |
| 동일 VLM 폐루프 또는 독립 평가 실패 | `DEFER` | IEEE ITSC/국제 저널 일정으로 이월 |
| 국내 원고와 중복 투고 문제 미해결 | `NO_GO` | 투고 경로부터 재결정 |

## 10. 제출 전 최종 체크리스트

### 연구 기여

- [ ] 표준 SFT와 구별되는 방법 또는 명확히 새로운 benchmark 기여
- [ ] 실행 가능한 trajectory와 동일 VLM 폐루프
- [ ] 최소 3개 maneuver family
- [ ] paired-contract hard negative와 always-stop 진단
- [ ] verifier-only와 hybrid 비교
- [ ] OOD threshold, 표현, 단위와 lifecycle 평가

### 실험 신뢰성

- [ ] 3~5 optimization seed
- [ ] 고정 test set과 별도 environment seed
- [ ] paired confidence interval와 effect size
- [ ] 독립 evaluator
- [ ] 원시 결과 재집계
- [ ] 실패와 음성 결과 공개

### 논문·제출

- [ ] 공식 CFP·마감·형식 재확인
- [ ] 국내 원고와 중복 투고 문제 없음
- [ ] 익명 영어 원고와 영어 figure/table
- [ ] 모든 주장–증거 traceability 완료
- [ ] 공개 재현 패키지 또는 익명 artifact
- [ ] 저자 전원 최종 승인과 제출 receipt

## 11. 지금 바로 수행할 단일 작업

다음 작업은 **IV00 투고 경로 확인**이다. 특히 국내 KIEE 원고가 실제로 투고됐는지와
현재 심사 상태를 먼저 기록해야 한다. 이 문제가 해소되면 IV01에서 방법·기준선·split을
동결하고, 그 다음에만 simulator와 GPU main 실험을 시작한다.
