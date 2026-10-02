# M14 CoC-conditioned front-end locked matrix

- 상태: **EXECUTED**
- software gate: **PASS**
- locked synthetic cases: **24개 / 3 slices**
- schema parse: **100.0%**
- expected primary verdict: **100.0%**
- 지원된 proposal의 EBLC/Core/Z3 compile: **100.0%**
- CoC authority 승격: **0건**
- 공개 출력의 CoC 원문: **0건**
- 실행 policy가 연결된 primary rule: **1/3**

이 matrix는 세 slice의 정상·동의표현/순서변경·누락·UNKNOWN·CONFLICT·FALSE·CLAIMED·
모호 binding 경계를 검사한다. 실제 24장면 표본, 일반 NLP 정확도 또는 법률 판단을 평가한
것은 아니다. 현재 실행 policy materialization은 횡단보도 규칙 1개만 지원하며, 다른
proposal은 임의 수치 없이 `NO_OPERATIONAL_POLICY_BINDING_FOR_PROPOSAL`로 남는다.
