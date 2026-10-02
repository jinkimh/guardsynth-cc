# GuardSynth-CoC 로컬 연구·검토 포털 v0.1

## 1. 목적

분산된 연구계획, 마일스톤/Todo, 현재 gate와 장면 검토 HTML을 한 웹 진입점에서 추적한다.
포털은 새 연구 판단을 만들지 않고 canonical 문서와 실행 artifact를 읽기 쉽게 투영한다.

## 2. 정보 권위와 갱신

- 마일스톤·Todo: `02_PROJECT_MILESTONES.md`의 요약 표와 체크박스를 build 시 파싱
- 활성 work package·전체 판단·회귀 수: `03_PROJECT_EXECUTION_TRACKER.md`에서 파싱
- M13/M16 수량: terminal `BATCH_RESULT.json`과 최신 `PILOT_PREFLIGHT.json`에서 로드
- 연구 목적·주장 경계: 연구계획과 tracker의 고정된 목적을 요약해 표시

따라서 HTML에서 상태를 직접 수정할 수 없다. 상태 변경은 권위 문서와 artifact를 먼저
갱신한 뒤 새 run ID로 포털을 다시 build한다.

## 3. 페이지 구조

1. `index.html`: 배경·목적·네 목표군·RQ1–RQ7·사전 성공 기준·범위, 현재 gate와 핵심 수량
2. `milestones.html`: M00–M21 상태, 검색/filter, 각 Todo와 진행 bar
3. `review.html`: 이미지, source closure, association, 전문가 훈련 화면을 동일 workspace에서 선택
4. `guide.html`: 주요 상황, 충돌 영역, 대상 위치, 가림, 프레임 변화와 판단 금지 필드 설명

검토 화면은 iframe 안에서 실행하며 새 창 전체 폭으로도 열 수 있다. 이미지 기반 판단과
source-complete audit를 분리해 이미지밖에 없는 검토자가 ID·geometry·frame을 추측하지 않게 한다.

## 4. 제한 자료 보안 경계

- 출력 class는 `LICENSE_RESTRICTED_LOCAL_ONLY`
- 결과는 `artifacts/results/restricted/guardsynth-project-portal-001/` 아래에만 생성
- 서버 주소는 코드에서 `127.0.0.1`로 고정하고 외부 host option을 제공하지 않음
- 저장소 root를 서비스하지 않고, build 시 선택해 복사한 HTML·CSS·JS·JSON만 서비스
- 기존 제한 HTML은 원문 이미지 파일을 새로 복사하지 않고 self-contained 결과를 복사
- 매 build는 기존 결과 덮어쓰기를 거부하고 source 문서 hash를 manifest에 기록

## 5. 비목표와 주장 경계

- 포털은 annotation database, multi-user 인증 시스템 또는 배포형 웹서비스가 아니다.
- tracker 표시가 milestone research gate 통과를 새로 증명하지 않는다.
- 제한 장면을 공개 인터넷에 게시하지 않는다.
- review UI 입력이 누락 source를 대신하거나 차량 안전성 증거가 되지 않는다.

## 6. 검증

- 22개 milestone과 M00–M21 순서 파싱
- M13 4/24, M16 4/60·shortfall 56·annotation false 반영
- 네 top-level 페이지 및 선택된 review HTML 존재
- 모든 top-level local href/src 해소
- HTML에 절대 저장소 경로 미노출
- 기존 output overwrite 거부
- 실제 loopback HTTP 핵심 페이지 200 응답

구현: [`project_portal`](../../../../apps/research_portal/README.md)
