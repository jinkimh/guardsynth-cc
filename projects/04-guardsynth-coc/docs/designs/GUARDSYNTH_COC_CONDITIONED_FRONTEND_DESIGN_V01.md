# GuardSynth CoC-conditioned front-end v0.1 설계

## 1. 경계

```text
CoC text (CLAIMED) ──> lexical semantic hints ─┐
                                               ├─> retrieval query ─> catalog candidates
Scene facts (4-value + provenance) ────────────┘                         │
                                                                        v
                                                applicability + partial binding
                                                                        │
                                                                        v
                                                      constraint proposal bundle
```

CoC 경로와 scene fact 경로는 합류하기 전까지 분리한다. CoC text는 hash/evidence ref와 typed
hint만 출력하며 원문, `OBSERVED`, `LEGAL` 또는 predicate truth를 만들지 않는다.

## 2. 결정론적 parser

v0.1은 일반 자연어 이해기가 아니다. versioned parsing policy에 고정된 한국어/영어 lexical
concept를 `intent/cause/action/uncertainty`로 투영한다. 인식하지 못한 표현은 `UNKNOWN`이며
추측하지 않는다. synonym과 word order 변화는 같은 concept set을 생성해야 한다.

## 3. retrieval과 hard filter

1. 요청 jurisdiction과 catalog jurisdiction이 다르면 `UNSUPPORTED_JURISDICTION`.
2. 명시된 slice hint와 parser cause가 일치하는 catalog slice만 후보로 둔다.
3. candidate ordering은 `(predicate overlap 내림차순, rule_id 오름차순)`이다.
4. lexical score는 proposal ordering일 뿐 applicability 또는 authority가 아니다.

## 4. four-valued applicability

각 required predicate의 source-bearing scene fact만 사용한다.

- 하나라도 `CONFLICT` → `CONFLICT`
- predicate가 없거나 `UNKNOWN`, 또는 `CLAIMED`만 있음 → `UNKNOWN`
- 모두 존재하며 하나라도 `FALSE` → `FALSE`
- 모두 fresh/source-linked `TRUE` → `TRUE`

v0.1은 freshness 수치가 catalog에서 `SOURCE_REQUIRED`인 경우 입력이 별도 freshness 판정을
제공하지 않으면 `UNKNOWN`으로 남긴다. 향후 scene adapter가 평가한 freshness status를 입력한다.

## 5. binding과 verdict

required fact들의 non-empty target/zone 집합이 각각 하나이면 `BOUND`, 둘 이상이면
`AMBIGUOUS`, 없으면 `UNSUPPORTED`다. 최종 proposal verdict는 다음 우선순위를 따른다.

`CONFLICT > UNSUPPORTED > REVIEW_REQUIRED > NOT_APPLICABLE > PROPOSED`

catalog binder output이 `UNSUPPORTED`이면 적용성이 TRUE여도 수치 계약을 만들지 않고 해당
reason code를 보존한다.

## 6. Materialization 경계

`frontend_materialization.py`는 source-bearing proposal을 기존 GuardSynth request로 넘긴다.
법규 source/claim과 CoC는 proposal provenance에만 남고, stop margin은 별도 simulation system
requirement, response/deceleration은 별도 simulated assurance model에서만 가져온다. 단일
proposal도 composition identity case로 EBLC bundle/Core/SMT까지 전달할 수 있도록 indexed
collection과 bundle schema는 최소 계약 수 1을 허용한다. 다중 계약 충돌 의미론은 변경하지
않는다.

v0.1 operational policy mapping은 `KR-RTA-27-1-CROSSWALK-STOP →
GS-SIM-PED-CORRIDOR-001` 하나다. 다른 proposal은 법규 문장으로부터 수치를 만들지 않는다.

## 7. v0.1 제한

- 일반 한국어/영어 의미 파싱이 아님
- 법률 exception의 완전한 논리식 평가가 아님
- production dense model 및 LLM reranker 미포함
- 세 slice 중 실행 policy materialization은 횡단보도 primary rule 하나만 지원
- `PROPOSED`는 전문가 검토 전 후보이며 safety validation이 아님
