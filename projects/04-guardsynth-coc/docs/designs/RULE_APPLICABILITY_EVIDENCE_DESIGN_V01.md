# GuardSynth 규칙 적용성 근거 v0.1

## 목적

이 단계는 공식 규칙 원문을 관측된 장면 조건에 연결한다. CoC 문장을 규범적 authority나
관측 사실로 승격하지 않으며, 규칙 연결 결과를 법률 자문·수치 차량 한계·차량 안전 검증으로
해석하지 않는다.

## 입력과 판정

첫 calibration 장면에서는 다음 근거가 모두 있을 때만 `CONDITIONALLY_APPLICABLE`을 출력한다.

1. 사람이 높은 신뢰도로 `CROSSWALK_VISIBLE`, `ROAD_USER_IN_EGO_PATH`,
   `IN_CONFLICT_REGION`을 판정한 image evidence
2. 기하학적으로 연결된 source-linked actor `SET`
3. California Legislature의 [Vehicle Code §21950](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=VEH&sectionNum=21950.) 원문과 snapshot SHA-256
4. 횡단보도 밖 예외 문맥을 보존하기 위한 [Vehicle Code §21954](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=VEH&sectionNum=21954.)
5. [SFMTA Powell/Hyde 노선](https://www.sfmta.com/routes/powell-hyde-cable-car)과
   [SFCTA Lombard Street 보고서](https://www.sfcta.org/sites/default/files/content/Executive/Meetings/board/2017/03-Mar-14/lombard_final_report_021517.pdf)로 교차 확인한 위치 단서

데이터셋에는 이 장면의 GPS/map ground truth가 없으므로 위치는
`INFERRED_HIGH_CONFIDENCE_NOT_DATASET_GPS`로 고정한다. 독립 GPS 확인값은 `false`이며,
이미지 조건이나 관할이 부족하면 `REVIEW_REQUIRED`로 중단한다.

## 산출물과 주장 경계

- `RULE_APPLICABILITY_EVIDENCE.json`: 공식 URL, snapshot hash, 조건부 적용성과 위치 한계
- `RUN_MANIFEST.json`: 제한 장면 입력 hash와 공개 원문 snapshot hash
- `RESULT.json`, `REPORT_KO.md`: 실행 결과와 인간 친화적 요약

원문 전체와 제한 이미지는 산출물에 복사하지 않는다. 이 단계는 규칙의 조건부 scene binding만
닫으며 `source_bearing_vehicle_assurance_profile`을 대신하지 않는다.

## 테스트 불변식

- country-only 위치는 적용성을 닫지 않는다.
- 횡단보도가 관측되지 않으면 §21950을 활성화하지 않는다.
- scene/association mismatch는 예외로 거부한다.
- 공식 source host, authority, jurisdiction과 SHA-256을 검증한다.
- 입력 객체를 변경하지 않는다.
