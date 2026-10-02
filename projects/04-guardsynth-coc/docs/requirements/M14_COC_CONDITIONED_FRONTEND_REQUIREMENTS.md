# M14 1차 제약 추출·EBLC 검증·CNL 학습 데이터 요구사항

- 상태: `PARTIAL`
- work package: `GS-P2-FRONTEND-REQUAL-001`
- 권위: [1차/2차 분리 결정](../decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md)

M12가 선택한 task의 CoC·scene·source에서 제약을 추출·binding하고 EBLC의 type/unit·모순·
지원 bounded 조건을 검증한다. 검증된 EBLC를 deterministic CNL로 렌더링해 **실제 CoC 학습
supervision에 삽입**한다. source/EBLC/verdict/CNL/example hash와 renderer version을 연결한다.

조건·대상·의무/금지·부정·수치/unit/frame·사용한 해제 조건의 fidelity tests와 독립 semantic
audit가 필요하다. 임의 NL 재작성이나 SAT 결과로 외부 근거를 대체하지 않는다.
전체 세 slice operational mapping, 일반 dense/NLP·복합 exception 확장은 2차이며 사용 subset의
정확성/abstention은 1차에도 필수다. 상세 학습 형식은 [M18 계약](M18_EBLC_LEARNING_EFFECT_REQUIREMENTS_V01.md)을 따른다.

## 이전 상세 요구사항 (2차/구현 이력)

<details>
<summary>기존 완료 근거와 확장 protocol 보기</summary>

아래 현재/필수/선행조건 표현은 당시 범위다. 1차 적용은 위 v2.3 계약이 대체한다.

### 이전 M14 CoC-conditioned constraint front-end 요구사항

- work package: `GS-P2-FRONTEND-001`
- 상태: `PARTIAL` (재적격화); 역사적 `COMPLETE_SCOPED_SOFTWARE` 보존
- 선행조건: M12 source catalog, M13 source-closure/abstention failure taxonomy
- 비목표: free-form CoC를 법률·관측 authority로 승격하거나 실제 차량 안전성을 확정

#### 이전 목적

CoC 자연어 단서, 구조화된 장면 fact와 source-bearing catalog를 결합하여 실행 후보 규칙,
적용성, target/zone binding과 abstention 이유를 가진 proposal bundle을 결정론적으로 만든다.

#### 이전 입력

1. CoC text, language, content hash/evidence ref, `CLAIMED` epistemic kind
2. jurisdiction, ODD tag, maneuver/slice hint
3. 네 값 `TRUE/FALSE/UNKNOWN/CONFLICT` 장면 predicate fact
4. 각 fact의 epistemic kind, source ref, target/zone ID
5. versioned parser/retrieval policy evidence ref
6. M12 source catalog

#### 이전 출력

- 원문을 포함하지 않는 typed CoC parse: intent, cause, action, uncertainty
- CoC와 scene fact를 분리한 provenance
- deterministic retrieval query와 ordered candidate rules
- required predicate별 four-valued applicability
- unique/ambiguous/unsupported target-zone binding
- `PROPOSED | REVIEW_REQUIRED | UNSUPPORTED | CONFLICT | NOT_APPLICABLE`
- 기존 GuardSynth request로 전달 가능한 항목 또는 정확한 미지원 reason code

`PROPOSED`는 front-end 후보라는 뜻이며 `VALIDATED`, 법률 판단 또는 안전 보장이 아니다.

#### 이전 v0.1 구현 범위

- 한국어/영어의 세 deep slice 관련 제한 어휘를 사용하는 deterministic lexical parser
- slice와 jurisdiction hard filter
- required predicate coverage 기반 four-valued applicability
- unique target/zone binding과 ambiguity abstention
- catalog binder가 명시한 `UNSUPPORTED` 수치 결과 보존
- paraphrase, fact ordering, hazard removal metamorphic test

#### 이전 후속 범위

아래 지원 공백은 `M14-R01 / GS-P2-FRONTEND-REQUAL-001`에서 세 slice의 supported/
unsupported rule·exception·materialization matrix와 실제 CoC dev coverage로 재적격화한다.
선택 parser/retriever의 범위와 version을 동결하며 일반 NLP/dense 구현을 자동으로 요구하지는
않는다. 미지원 rule을 분모에서 숨기거나 1/3 mapping을 전체 학습 신호 준비 완료로 보지 않는다.

- production dense model/reranker와 일반 자연어 parser 정확도 평가
- 복합 exception algebra와 모든 catalog rule의 operational policy authoring
- 실제/파생 장면에서의 empirical applicability 정확도 평가

#### 이전 성공 gate

- schema-valid locked fixtures 100%
- CoC claim이 observed/legal authority가 된 사례 0건
- 입력 순서에 무관한 deterministic output 100%
- missing/CLAIMED-only predicate abstention 100%
- ambiguity와 `CONFLICT` 보존 100%
- source 없는 normative/numeric value 0건
- 기존 maintained/P0a/structure 회귀 통과

#### 이전 주장 경계

이 front-end는 검토 가능한 제약 후보를 생성한다. parser 정확도, 법적 적용성, sensor
accuracy, actual-vehicle assurance 또는 안전 효과는 후속 expert/empirical 평가 전까지
입증되지 않는다.

#### 이전 종료 근거

- proposal pilot: `artifacts/results/public/guardsynth-coc-frontend-001/crosswalk-synthetic-2026-08-12-v3/`
- source-separated materialization: `artifacts/results/public/guardsynth-coc-frontend-materialization-001/crosswalk-synthetic-2026-08-12-v1/`
- 24-case locked matrix: `artifacts/results/public/guardsynth-coc-frontend-matrix-001/locked-synthetic-2026-08-12-v1/`
- schema/expected verdict 24/24, CoC authority 승격 0건, 지원된 proposal compiler 2/2
- maintained 286/286, P0a 7/7, structure 10/10

`24-case`는 세 slice의 software boundary matrix이며 실제 24장면 정확도가 아니다. 실행
policy mapping은 횡단보도 primary rule 1/3만 지원한다. 나머지는 임의 수치 없이
`NO_OPERATIONAL_POLICY_BINDING_FOR_PROPOSAL`로 보존하며 M15 공통 baseline protocol과
후속 policy authoring의 명시적 limitation으로 넘긴다.

</details>
