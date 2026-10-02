# M16 국제 도로교통협약 연구 기준 결정 v1

- 결정 ID: `GS-P4-M16-AUTHORITY-001`
- 결정일: 2026-09-06
- 상태: `APPROVED`
- 적용 범위: M16 98-event source frontier의 normative baseline
- 주장 경계: 국내법 준수 판정, 법률 자문 또는 차량 안전 보장이 아님

## 1. 결정

특정 한 국가의 법률을 다른 국가 장면에 적용하지 않는다. M16에서는 장면 국가가 당사국인
UN 도로교통협약의 공통 규범을 `INTERNATIONAL_TREATY_NORMATIVE_BASELINE`으로 선택한다.

- 현재 유럽권 35건은 1968년 비엔나 도로교통협약을 사용한다.
- 미국 63건은 미국이 비준한 1949년 제네바 도로교통협약을 사용한다.
- 적용 강도는 `DIRECT_TREATY_RULE`과 `GENERAL_DUE_CARE_FALLBACK`으로 분리한다.
- 국내 세부법이 없으면 `domestic_detail_required=true`로 기록하되 M16 연구 기준의 결측으로
  계산하지 않는다.
- 모든 결과에서 `legal_compliance_claim=NOT_PERMITTED`를 강제한다.

## 2. slice별 기준

| 협약 체계 | slice | 근거 | 강도 |
|---|---|---|---|
| Vienna 1968 | pedestrian/cyclist yield | Road Traffic Article 21 | 직접 규칙 |
| Vienna 1968 | stop/signals | Road Signs and Signals Article 23 | 직접 규칙 |
| Vienna 1968 | following/cut-in | Road Traffic Article 13(5) | 직접 규칙 |
| Geneva 1949 | 세 slice | Road Traffic Articles 8(5), 10 | 일반 주의의무 fallback |

미국 장면의 보행자 양보, 신호 의미, 추종·차선변경 세부사항은 국내법 없이 법적 준수 여부를
판정하지 않는다. 이 fallback은 장면별 규칙 합성의 중립적인 최소 연구 기준일 뿐이다.

## 3. 공식 근거

- [1968 Road Traffic 협약 상태](https://treaties.un.org/Pages/showDetails.aspx?clang=_en&objid=080000028003745e)
- [1968 Road Traffic 협약문](https://unece.org/DAM/trans/conventn/Conv_road_traffic_EN.pdf)
- [1968 Road Signs and Signals 상태](https://treaties.un.org/Pages/ViewDetailsIII.aspx?Temp=mtdsg3&chapter=11&lang=en&mtdsg_no=XI-B-20&src=TREATY)
- [1968 Road Signs and Signals 협약문](https://unece.org/DAM/trans/conventn/Conv_road_signs_2006v_EN.pdf)
- [1949 Road Traffic 협약 상태](https://treaties.un.org/Pages/showDetails.aspx?objid=080000028005793f)
- [1949 Road Traffic 협약문](https://treaties.un.org/doc/Publication/UNTS/Volume%20125/v125.pdf)

당사국 상태는 2026-09-06에 위 UN Treaty Collection에서 확인했다. catalog는 이 공식 host 외
URI를 거부하고, 현재 cohort의 12개 국가와 세 slice가 모두 매핑되지 않으면 fail closed한다.

## 4. M16 gate 영향

`applicable_rule_scope`는 해당 국가의 협약 당사국 상태, slice mapping, 공식 협약문과
`NOT_PERMITTED` 주장 경계가 모두 있을 때 국제협약 연구 기준으로 닫을 수 있다. 이는 종전의
“모든 장면에 국내법 catalog가 있어야 한다”는 M16 연구 gate를 대체한다. 국내법 준수 연구를
후속 수행할 경우 별도 국내 authority가 필요하다.

현재 98건 모두 baseline이 결합되어 authority 획득 task는 해소됐지만, semantic geometry,
lane/zone association과 outcome lifecycle witness가 남아 있어 eligible은 1/60이다.
