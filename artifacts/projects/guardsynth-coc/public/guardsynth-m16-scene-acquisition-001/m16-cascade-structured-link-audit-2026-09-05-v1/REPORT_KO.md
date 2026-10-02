# M16 CASCADE structured-link source 감사

- 상태: **M16_SOURCE_CLOSURE_PARTIAL_STRUCTURED_RELATION_AUDITED**
- approved CASCADE annotation hash binding: **98/98**
- distinct annotation sources: **81**
- relevant actor/control source set 폐쇄: **70/98**
- target lane/zone containment 폐쇄: **1/98**
- 신규 8/8 / final outcome / eligible: **0 / 0 / 0**
- 전체 eligible: **1/60**, shortfall **59**
- 새 curator 설문 화면: **생성하지 않음**

CASCADE schema의 because_of/action_target과 시간 활성 상태를 사용해 근거가 있는 actor/control SET만 닫았다. optional containment에서 ego와 모든 active target이 같은 environment/lane으로 연결된 경우에만 lane relation을 닫았다. 나머지 영상 관찰을 geometry로 해석하지 않았다. 따라서 새 source 없이 사람이 답할 수 없는 빈 curator 설문은 만들지 않았고, 필요한 source 계약을 acquisition manifest에 기록했다.

Structured-link status counts: `{'AVAILABLE_SOURCE_LINKED_SET': 70, 'REVIEW_REQUIRED_CAUSAL_REFS_OUTSIDE_EVENT_WINDOW': 4, 'REVIEW_REQUIRED_NO_ACTIVE_EGO_RELATION_LINK': 24}`
