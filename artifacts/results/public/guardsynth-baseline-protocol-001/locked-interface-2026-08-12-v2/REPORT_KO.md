# M15 GuardSynth baseline protocol smoke run

- 상태: **EXECUTED**
- software protocol gate: **PASS**
- baseline: **10개 (B0–B8/B13)**
- locked cases: **24개**
- 공통 schema 결과: **240/240**
- channel firewall 위반: **0건**
- 숨긴 failure: **0건**
- 품질 점수 계산: **아니오**

외부 free-form/scene model provider, matrix의 physics/assurance와 reachability 입력은 제공되지
않았으므로 관련 adapter는 명시적으로 abstain했다. B5/B6는 각각 deterministic BM25
source retrieval과 scene-only semantic filter의 `style adapter`이며 원 시스템 재현이 아니다.
이 run은 비교 인터페이스·입력 channel·abstention protocol을 동결할 뿐 성능 우열이나 실제
안전 효과를 보여주지 않는다.
