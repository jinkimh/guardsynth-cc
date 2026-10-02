# 1차 행동 제약 실행 계약

- project_id: `guardsynth-coc`
- 개발 계약: `GS-PAPER1-ENTRY-POLICY-v0.1`, 2026-09-08
- 작업: M12-R01-A 조건부 행동 계약 → M14-R01-A/B Core·SMT·CNL 실행
- 권위: [연구계획 v2.3](../plans/01_RESEARCH_PLAN_V02.md), [마일스톤](../plans/02_PROJECT_MILESTONES.md)
- 상태: **개발용 subset/policy 명세 확정; 실제 장면 source와 본 실험 action/gold 계약은 미확정**

## 1. 범위와 선택

선택 과제는 에고가 특정 충돌 영역에 진입할 것인지의 bounded qualitative decision이다.
행동은 `ENTER_ZONE` 또는 `DEFER_ENTRY`다. DEFER_ENTRY는 해당 진입 결정을 보류하는 것이며
즉시 정지/비상 제동/제어 가능성을 보증하는 명령이 아니다. 속도, 정지거리, 충돌 확률, metric
geometry를 이 subset에서 계산하지 않는다. 이 연구용 정책을 보편적 법규로 주장하지 않는다.

기존 `eblc-program-v0.1/v0.2`와 numeric stopping semantics는 그대로 유지한다.
별도 `eblc-action-contract-v0.1` JSON schema/parser가 명시한 subset만 받으며, 기존
`eblc-core-v0.1` type checker와 SMT compiler로 자동 lowering한다. 일반적인 제약 추출기나
범용 EBLC semantics 전체가 완성됐다는 뜻은 아니다.

정책 `CLEAR_REQUIRED_FOR_ENTRY`를 개발 버전의 고정 의미로 선택한다. 이전 수작업 예제의
두 UNKNOWN 반례를 막기 위한 명시적인 정책 변경이며 CNL에서 몰래 추가하는 것이 아니다.
추가 정책 variants를 이번 실험 코드에 추측해서 넣지 않는다. 보수성이 nominal 진행에
주는 영향은 실제 데이터 평가에서 따로 측정해야 한다.

## 2. 실행 의미

각 obligation j에 대해 truth는 TRUE/FALSE/UNKNOWN/CONFLICT, evidence_valid는 독립된
Boolean이다. TRUE는 해당 obligation을 활성화할 조건이 존재함, FALSE는 그 조건의 해소가
확인됨을 뜻한다. UNKNOWN/CONFLICT/invalid는 FALSE가 아니다.

```text
on[j,t]    := valid[j,t] AND truth[j,t]=TRUE
clear[j,t] := valid[j,t] AND truth[j,t]=FALSE
active[j,t] := if on[j,t] then TRUE
               else if clear[j,t] then FALSE
               else previous_active[j,t]

entry_permitted[t] := AND_j clear[j,t]
action[t]=ENTER_ZONE → entry_permitted[t]
active[j,t] → action[t] != ENTER_ZONE
review_required[t] := OR_j (invalid[j,t] OR truth[j,t] in {UNKNOWN,CONFLICT})
```

입력을 읽고 그 판단의 상태를 갱신한 후 행동을 제약한다. 첫 판단 이전 active는 명시적인
자유 입력이며 이후 이전 단계의 active를 사용한다. 동일 전이를 반복하므로 해제 후 충돌
재확인은 재활성화된다. 만료/우선순위 예외/수치 연속-clear threshold는 v0.1 범위에 없다.
현재의 valid FALSE를 충분한 clearance로 채택하는 것은 개발 정책이며 물리적 해소 검증을
생략해도 된다는 뜻은 아니다. 하나의 obligation 해제가 나머지를 해제하지 않는다.

모든 조건이 clear이면 두 행동 모두 허용된다. 이것은 진행 가능성이지 진행을 강제하는
liveness나 실제 성공률 보증이 아니다. UNKNOWN이면 명세상 ENTER_ZONE을 배제하지만,
그 출력을 실제 영상의 독립 행동 정답으로 복제해서는 안 된다.

## 3. Source/binder matrix

| 필드 | source 역할 | 현재 #18 | export 전 필요한 확인 |
|---|---|---|---|
| CoC | intent/관련 obligation 후보 | 원본 exact event 연결 | CoC 자체를 gold로 사용하지 않음 |
| target entity | CASCADE source ID 후보 | Agent3 연결 | 영상 대상과 동일성 및 predicate argument 연결 |
| zone | 공통 진입 영역의 의미 binding | null | 과제상 영역 식별·ego/target 관계; metric claim 없으면 meter 수치 불필요 |
| pedestrian_conflict | 시점별 관측/검증된 도출 | UNKNOWN | 실제 판단 시점에 해당 관계를 확인 |
| main_road_yield_required | 별도 적용 조건/근거 | UNKNOWN | 주도로 의무의 적용 또는 해소 확인 |
| evidence_valid | identity·시점·source·관측량 계약 검사 | false | 수용할 epistemic source·시간 정렬·관측/도출 방법 명시 |
| rule_ref | 연구용 policy의 해시 참조 | 본 문서 | treaty 일반 의무와 운영 설계 구분 |
| action gold | 독립 검토 | null | 본 과제 후보와 독립 판단 확보 |

협약 제21조는 보행자 보호의 참조이지 main-road 우선권이나 UNKNOWN fallback의 직접 근거가
아니다. 따라서 두 obligation의 실행 `rule_ref`는 이 개발 정책이고, 실제 annotation/CoC
해시는 별도의 source_refs로 남긴다. 의미 영역/관측량 요구를 제거하는 scope 변경은 하지 않는다.

evidence_valid는 compiler에서 관측하지 않는 interface다. 현재 source adapter는 실제 #18의
미확정 근거를 UNKNOWN/false로 유지한다. 파서가 성공했거나 SHA가 일치한다고 true로 올리지
않는다. 합성 truth-table 입력은 테스트에만 사용하고 실제 장면 입력과 분리한다.

## 4. 구현 소유권과 CNL

- [플랫폼 schema](../../../../platforms/eblc-bcv/src/guard_synth_eblc/schemas/eblc_action_contract.schema.json),
  [parser/lowering](../../../../platforms/eblc-bcv/src/guard_synth_eblc/action_contract.py): reusable implementation.
- [공통 renderer](../../../../platforms/eblc-bcv/src/guard_synth_eblc/cnl_renderer.py)의
  `render_action_contract`: 구조화 입력에서 CNLDocument·field/source/hash mapping을 생성한다.
- [장면 adapter](../../src/guard_synth/qualitative_scene_contract.py): 현재 pinned #18 과제만 준비한다.
- L2와 L3는 같은 renderer를 쓴다. renderer 자체는 구조 검사만 하고 solver/source gate를
  호출하지 않는다. 검증된 L3 학습 export는 별도의 source/gold/CNL 검토 완료가 필요하다.

null target/zone도 조건부 명세로 parse/compile할 수 있지만 CNL에 UNBOUND로 표시한다.
실행 가능한 조건부 명세와 source-complete 장면을 구분한다. 새로운 parser/version을 기존
numeric 프로그램의 실패 우회로 쓰거나 unbound CNL을 검증된 학습 정답으로 배포하지 않는다.

## 5. 검증 기준과 완료 경계

1. strict schema, ID/source refs, 기존 Core type checker 통과.
2. 기본 SAT와 각 probe의 전제 SAT를 먼저 확인; UNKNOWN/invalid/CONFLICT에서 entry 반례 UNSAT.
3. clear에서 DEFER와 ENTER 모두 SAT; 기존 활성 유지/해제/재활성화 검사.
4. gate 제거 mutation에서 이전 UNKNOWN 반례가 다시 SAT인지 검사.
5. 두 obligation의 truth×valid×prior 256개 조합에서 독립 truth-table와 행동 허용 결과 비교.
6. CNL의 대상·조건·부정·UNKNOWN·조합·입력 해시 보존 및 solver-free renderer 회귀 검사.
7. 실제 #18 source→계약→Core→SMT→CNL 출력과 source 미완료 gate를 함께 기록.

위 조건을 통과하면 M12-R01-A 개발 계약과 M14-R01-A/B 소프트웨어 연결 subtask를 완료한다.
M12-R01 전체 source/action/gold/cohort, M14 실제 추출 품질·독립 CNL fidelity, M16 적격성,
M18 본 학습·효과는 완료 처리하지 않는다. 다음은 필요한 predicate/zone 근거를 실제로
연결하는 source adapter 확장과 독립 행동 정답 준비이며, 기존 설문 전량 반복은 아니다.
