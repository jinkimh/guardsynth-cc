# GuardSynth 포털 review 저장소 결정 v1

- 결정 ID: `GS-PORTAL-STORAGE-001`
- 결정일: 2026-08-14
- 상태: `APPROVED`
- 적용 범위: 신규 review round

## 결정

review round 하나는 project owner와 classification 하나에 귀속된 SQLite DB 하나를 사용한다.
DB는 `artifacts/projects/<project-id>/restricted/` 아래의 새 operations run이 소유하며 WAL,
foreign key, transaction, busy timeout과 schema version을 사용한다.

독립 판정은 revision row로 append하고 finalize된 원 판정은 수정·삭제하지 않는다. adjudication은
별도 row다. round close 시 integrity check와 final export/hash를 수행하고 DB를 동결한다. public
aggregate는 allowlisted deidentified field만 새 public run으로 생성하며 restricted DB나 backup을
복사하지 않는다. 기존 localStorage JSON/CSV는 자동 import하지 않는다.
