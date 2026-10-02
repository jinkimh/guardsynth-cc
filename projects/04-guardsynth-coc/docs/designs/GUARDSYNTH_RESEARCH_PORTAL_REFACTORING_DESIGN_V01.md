# GuardSynth-CC 차세대 연구 포털 감사 및 리팩터링 설계 v1

- 문서 상태: `APPROVED_FOR_IMPLEMENTATION`
- 기준일: 2026-08-14
- 소유 project_id: `guardsynth-coc`
- 대상 애플리케이션: [`apps/research_portal/`](../../../../apps/research_portal/)
- 기존 설계: [GUARDSYNTH_PROJECT_PORTAL_DESIGN_V01.md](GUARDSYNTH_PROJECT_PORTAL_DESIGN_V01.md)
- 검토 UI 설계: [GUARDSYNTH_SCENE_EVIDENCE_REVIEW_UI_DESIGN_V01.md](GUARDSYNTH_SCENE_EVIDENCE_REVIEW_UI_DESIGN_V01.md)
- M16 계약: [M16_EXPERT_PILOT_REQUIREMENTS.md](../requirements/M16_EXPERT_PILOT_REQUIREMENTS.md)
- 구현 승인 상태: `APPROVED_IMPLEMENTATION_STARTED`

## 0. 설계 결론

기존 포털은 폐기하지 않는다. 현재의 강점인 5개 프로젝트 독립 projection, canonical 문서
live reload, loopback-only serving, immutable build run과 output overwrite 거부를 유지한다.
그 위에 다음 두 경계를 분리해 단계적으로 리팩터링한다.

1. **read-only research projection:** 현재 Python 정적 builder를 분리·정돈하여 프로그램,
   프로젝트, 플랫폼, 결과, 논문, 회의·결정을 canonical Markdown/YAML/manifest에서 읽는다.
2. **restricted review operations:** 로그인, 역할, 여러 review round, assignment, 독립 판정,
   adjudication과 metric이 필요한 부분만 loopback 전용 동적 backend와 round별 SQLite로 둔다.

두 경계는 같은 UI shell을 사용할 수 있지만 권위와 저장소는 다르다. 연구 질문, 성공 기준,
claim boundary와 milestone 상태는 웹에서 수정하지 않는다. review backend는 운영 record만 쓰며,
canonical Markdown writeback은 이 버전의 구현 범위에서 제외한다.

현재 M16의 정확한 표시 계약은 다음과 같다.

```text
UI/package readiness        = READY
human source review         = 0/60
distinct eligible scenes    = 1/60
M16 milestone               = PARTIAL
empirical annotation allowed= false
```

`UI_READY`, software test 통과 또는 60개 입력 packet 존재를 `SOURCE_COMPLETE`, M16 시작 gate 통과,
human review 완료 또는 core research 완료로 변환하지 않는다.

## 1. 감사 범위와 확인한 권위

다음 항목을 감사 기준으로 사용했다.

- repository 구조·명명 권위: `AGENTS.md`, Structure Codex v3.6, File Naming Codex v1.4
- registry: `PROJECT_REGISTRY.json`, `PROJECTS.md`
- 5개 프로젝트: 각 `PROJECT.yaml`, `README.md`, `STATUS.md`, canonical 계획 통제 세트,
  survey index와 `results/RESULT_INDEX.md`
- 공용 플랫폼: `platforms/eblc-bcv/PLATFORM.yaml`, `README.md`, `STATUS.md`, result index
- 포털: README, 944-line builder/server, site assets, 207-line test suite와 현재 v9 run manifest
- GuardSynth 연구 권위: 연구계획 v2, milestone ledger, execution tracker, M16 requirements,
  기존 portal/review designs와 CURRENT related-work survey
- 프로젝트 3의 두 CURRENT survey와 프로젝트 5의 진행 중 CURRENT survey

새 문헌 조사는 수행하지 않았다. 포털이 “왜 중요한가”를 표시할 때 사용할 조사 기준일은
canonical survey에 기록된 값만 사용한다.

| 프로젝트 | survey 권위 | 조사 기준일 | 홈 표시 규칙 |
|---|---|---|---|
| safety-constrained-coc | `PLANNED` | 없음 | 중요성 요약을 최신 근거처럼 표시하지 않고 `canonical survey 미완료` 표시 |
| specification-alignment | `PLANNED` | 없음 | 동일 |
| sequential-coc-verification | `CURRENT` 2개 | 2026-08-01, 2026-08-02 | 해당 날짜와 원문 링크를 함께 표시 |
| guardsynth-coc | `CURRENT` | 2026-08-08 | scoping survey임을 밝히고 원문 링크 표시 |
| eblc-language-verification | `CURRENT`, `IN_PROGRESS` | 미고정 | prior-art 감사 진행 중이며 신규성 미확정으로 표시 |

“최신”, “현재 문헌 전체”와 같은 표현은 survey에 그 근거가 없으면 사용하지 않는다.

## 2. 기존 포털 기능 감사

### 2.1 현재 기능과 판정

| 영역 | 현재 구현 | 감사 판정 | 처리 |
|---|---|---|---|
| 프로젝트 목록 | registry 순서로 5개 project page 생성 | 소유권과 순서가 정확함 | 유지 |
| project live projection | server mode에서 6개 canonical 문서를 page load마다 재파싱 | 가장 중요한 강점 | 유지·parser 분리 |
| active milestone sync | tracker ID가 ledger에 없으면 503 | fail-closed 동작 | 유지·검사 강화 |
| 프로젝트별 review ownership | 현재 9개 package 모두 `guardsynth-coc`에만 표시 | 다른 프로젝트와 혼합하지 않음 | 유지 |
| immutable build | 기존 output directory overwrite 거부 | 재현성과 기존 run 보존 | 유지 |
| serving root | build output만 `SimpleHTTPRequestHandler`에 제공 | 저장소 전체 static root 노출을 피함 | 유지 |
| bind | `127.0.0.1` 고정, host option 없음 | 제한자료 기본 경계에 부합 | 유지 |
| build manifest | source hash, review asset hash, registry hash 기록 | snapshot provenance에 유용 | 확장 |
| home | project card와 합계 metric부터 시작 | 프로그램 질문·목표·pipeline·gate가 없음 | 재설계 |
| EBLC/BCV | manifest에 platform count만 있고 실제 UI에는 표시되지 않음 | project 05와 platform 구분이 보이지 않음 | 별도 platform 영역 추가 |
| results/evidence | 전용 page와 owner/class filter 없음 | artifact claim 경계 확인 불가 | 신규 projection |
| papers | Paper 1·3 path와 본문이 Python/HTML에 하드코딩 | owner registry가 아니며 2·4·5를 표현하지 못함 | paper manifest 기반 전환 |
| review packages | 고정 path 4개와 glob association 5개를 복사 | round·protocol·assignment·metric 개념이 없음 | registry/round 모델로 전환 |
| review persistence | self-contained HTML의 localStorage/export | 한 브라우저의 도구일 뿐 중앙 운영 record 아님 | legacy read-only 유지 |
| auth/RBAC | 없음 | 다중 reviewer 운영 불가 | 동적 backend에 추가 |
| meeting/decision | page 없음 | PI 의사결정 workflow 부재 | read-only projection 추가 |
| public export | 없음 | restricted/public 분리 검증 불가 | 명시적 deidentification export 추가 |
| CSP | review package 일부에는 있으나 portal shell response header는 없음 | shell·route 보안 불충분 | response CSP 추가 |
| iframe | `allow-scripts allow-downloads allow-forms allow-modals` 고정 | package별 최소권한이 아님 | manifest별 최소 sandbox |
| status mapping | 문자열 포함 검사로 ready/partial 등을 추정 | `UI_READY`가 연구 readiness처럼 보일 위험 | exact gate status 사용 |
| status parser | 동일 label의 첫 값만 보존 | 여러 Evidence/Next 항목 손실 | list-aware parser |
| artifact paths | 여러 legacy/restricted path가 상수로 하드코딩 | owner/class drift와 stale path 위험 | artifact registry로 교체 |
| local link test | top-level HTML의 local href/src 검사 | 생성 전체 route와 nested asset 검사가 부족 | 전체 route manifest 검사 |

### 2.2 현재 v9 run의 정확한 범위

현재 canonical portal run은
`artifacts/projects/guardsynth-coc/restricted/guardsynth-project-portal-001/portal-2026-08-14-v9/`
이다. 5개 프로젝트, 52개 milestone, 논문 PDF 2개와 restricted review HTML 9개를 포함한다.
이는 `BUILT` 상태의 local tracking/review package이며 연구 결과, 전문가 agreement, 법률 자문,
실제 차량 안전 증거가 아니다.

현재 test suite가 직접 보장하는 것은 다음 정도다.

- 5개 project 순서, project page/review page 생성
- project 04에만 9개 review package 연결
- 6개 project canonical document의 live reload 예시 1건
- output overwrite 거부
- top-level local link 해소
- loopback HTTP의 기존 핵심 page 제공
- repository 절대 root 문자열의 HTML 비노출

로그인, 역할별 비가시성, review round, assignment, adjudication, agreement, public export,
artifact classification과 M16 1/60 gate는 현재 portal test suite가 보장하지 않는다.

## 3. 유지·리팩터링·제거 후보

### 3.1 반드시 유지할 기능

1. `PROJECT_REGISTRY.json`이 5개 프로젝트의 순서와 stable ID를 결정한다.
2. 각 project page는 자신의 canonical 문서만 읽는다.
3. server mode에서 page load/API read마다 canonical source를 다시 읽는다.
4. tracker–ledger active milestone 불일치는 503 또는 동등한 fail-closed 응답으로 중단한다.
5. build snapshot은 immutable하고 같은 run ID를 덮어쓰지 않는다.
6. server는 `127.0.0.1`에만 bind하고 repository root를 서비스하지 않는다.
7. review ownership과 artifact ownership을 project/platform별로 분리한다.
8. 제한 self-contained HTML 원본과 복사본의 hash를 검증할 수 있게 한다.
9. skip link, keyboard focus, text label이 있는 status, mobile readable layout을 유지한다.

### 3.2 리팩터링할 기능

- 944-line `run.py`를 projection, artifact registry, builder, route/server, security, review store와
  metric 모듈로 나눈다.
- 단순 정규식 YAML reader는 현재 flat metadata만 다루는 제한을 명시하고, `PROJECT.yaml`의
  canonical path·dependency list를 검증할 수 있는 parser로 교체한다.
- `STATUS.md`의 Evidence/Boundary/Blocker/Next를 단일 문자열이 아니라 순서 보존 list로 읽는다.
- research plan, milestone, tracker, survey index와 result index의 link를 owner root 안에서 검증한다.
- status color는 문자열 heuristic이 아니라 ledger의 exact base state를 사용한다.
- project raw state와 active gate state를 동시에 보이며 둘을 합성한 가짜 완료 상태를 만들지 않는다.
- paper와 review asset은 hardcoded constant가 아니라 owner-aware manifest/registry에서 읽는다.
- restricted HTML은 새 portal build마다 무조건 복사하지 않고 allowlisted route로 원본을 제공한다.
  sealed offline snapshot을 명시적으로 만들 때만 hash-preserving copy를 허용한다.

### 3.3 승인 후 제거 후보

다음은 먼저 replacement test가 통과한 뒤에만 제거한다.

| 후보 | 근거 | 제거 조건 |
|---|---|---|
| GuardSynth 전용 `_milestone_data`, `_tracker_metadata`, `_current_work_data` 중 중복 path | 5-project generic parser와 별도 legacy parser가 공존 | generic projection이 M16 gate를 동일하게 fail-closed 검증 |
| `M13_RESULT`, 고정 M16 preflight/review path 상수 | owner/class registry와 충돌 | registry route와 compatibility test 통과 |
| `PAPER1_PDF`, `PAPER3_PDF` 및 정적 papers 본문 | paper 1·3만 하드코딩 | 모든 project paper manifest와 PDF hash test 통과 |
| 고정 review menu 번호 `1.`~`5.x` | round의 목적·상태·소유권을 표현하지 못함 | review round list가 같은 legacy assets를 read-only로 표시 |
| global `guide.html`의 project-specific protocol 역할 | round별 versioned guideline과 혼동 | 공통 도움말과 canonical round guideline link 분리 |
| package별 필요를 보지 않는 iframe sandbox 권한 | 최소권한 원칙 위반 | sandbox policy manifest test 통과 |

기존 portal run, legacy artifact, localStorage export 또는 review 원본은 제거 후보가 아니다.

## 4. 새 사이트맵

```text
홈 /
├── 연구 프로젝트 /projects
│   ├── /projects/<project-id>
│   └── 공용 연구 플랫폼 /platforms/eblc-bcv
├── 결과와 근거 /evidence
│   ├── project/platform filter
│   ├── classification filter
│   └── /artifacts/<opaque-artifact-id>
├── 외부검토 /reviews
│   ├── /reviews/<review-round-id>
│   ├── /reviews/<review-round-id>/samples/<opaque-sample-id>
│   └── /reviews/<review-round-id>/adjudication
├── 회의와 결정 /meetings
├── 논문 /papers
└── 사용자 메뉴
    ├── 내 배정 /me/assignments
    ├── 내 진행률 /me/progress
    ├── 세션 종료 /logout
    └── 연구책임자에게만 운영 /operations
```

`관리`라는 이름은 사용하지 않는다. 사용자 메뉴의 `운영`은 허용된 review round 운영만 뜻하며
canonical research gate를 바꾸는 기능을 포함하지 않는다.

## 5. 프로젝트·플랫폼 정보구조

### 5.1 프로그램 계층

```text
GuardSynth-CC 연구 프로그램
└── 5개 독립 연구 프로젝트
    └── phase/work package
        └── milestone
            └── task/experiment/run
                └── artifact/evidence
```

프로젝트 1–5는 card와 URL을 독립적으로 가진다. 한 프로젝트 page가 다른 프로젝트의 paper,
review package 또는 result를 자신의 결과처럼 렌더링하지 않는다. cross-project dependency는
관계 link로만 표시한다.

### 5.2 공용 플랫폼 계층

```text
공용 EBLC/BCV 플랫폼
├── language
├── Core IR/lowering
├── compiler/SMT
├── runtime monitor
├── BCV
├── release/conformance tests
└── consumers
    ├── specification-alignment
    ├── guardsynth-coc
    └── eblc-language-verification
```

platform page는 `PLATFORM.yaml`, platform README/STATUS, release/test manifest와 platform result
index만 읽는다. Project 05 page는 독립 research plan, prior-art audit, benchmark와 paper만 읽고
platform release 완료를 신규성 또는 우수성 결과로 계산하지 않는다.

### 5.3 상태의 두 축

한 badge로 완료 의미를 뭉치지 않는다.

| 축 | 값 | 예 |
|---|---|---|
| execution state | `COMPLETE`, `PARTIAL`, `BLOCKED`, `READY_NEXT`, `QUEUED` | M16=`PARTIAL` |
| outcome qualifier | `PASSED`, `TERMINAL_SHORTFALL`, `SCOPED_SOFTWARE`, `PROTOCOL_ONLY`, `NOT_EVALUATED` | M13=`COMPLETE` + `TERMINAL_SHORTFALL` |

raw canonical state도 별도 text로 보존한다. 색상, icon, label을 함께 사용한다. 빈 결과나 미통과
gate는 성공 card 대신 `근거 없음`, `미시작`, `shortfall` 또는 `blocked` panel로 표시한다.

## 6. 홈 화면 설계

홈은 다음 순서를 고정한다.

1. 연구 제목
2. 대표 연구 질문
3. 프로그램 목표와 claim boundary
4. 전체 research pipeline
5. 현재 program stage와 핵심 gate
6. 왜 중요한가
7. 5개 프로젝트
8. 공용 EBLC/BCV platform
9. 주요 결과와 현재 external review link

대표 pipeline은 다음과 같이 렌더링한다.

```text
CoC                  실제 장면·시간 상태       외부 규칙·시스템 근거
(상황 단서)          (source packet 필요)       (authority/version/scope)
          \                |                   /
           +--------- provenance -------------+
           +-- recorded-rig binding -----------+
           +-- simulated assurance ------------+  서로 다른 badge
                              |
                              v
                    GuardSynth 제약 합성
                              |
                              v
                       EBLC 구조화
                              |
                              v
                 BCV / Core / SMT / runtime
                              |
                              v
                 plan 또는 monitor/shield 적용
                              |
                              v
      위반 감소 | 과잉제약 억제 | 진행성 유지 | 전문가 효용
```

그림 아래에는 항상 다음 boundary를 표시한다.

- CoC는 법규 authority가 아니다.
- image observation은 source-complete evidence가 아니다.
- recorded-rig binding과 simulated vehicle assurance는 다르다.
- bounded verification은 실제 차량 안전 증명이 아니다.
- M16 human review는 0/60, eligible은 1/60이며 empirical annotation은 시작되지 않았다.

“왜 중요한가”는 survey index가 `CURRENT`로 지정한 문서만 읽는다. 조사일이 없거나
`IN_PROGRESS`이면 그대로 표시하고 원문 link를 제공한다. project 1·2에는 근거가 준비되지
않았음을 명시한다.

## 7. 화면별 wireframe

### 7.1 홈

```text
+-------------------------------------------------------------------+
| GS | 홈 프로젝트 결과와근거 외부검토 회의와결정 논문 | 사용자    |
+-------------------------------------------------------------------+
| GuardSynth-CC                                                     |
| 대표 연구 질문                                                    |
| [현재: M16 PARTIAL] [eligible 1/60] [human review 0/60]            |
+-------------------------------------------------------------------+
| research pipeline diagram + 5 claim-boundary callouts             |
+-------------------------------------------------------------------+
| 왜 중요한가: survey status/date/source links                      |
+-------------------------------------------------------------------+
| Project 01 | 02 | 03 | 04 | 05                                   |
| 별도 영역: 공용 EBLC/BCV platform                                 |
+-------------------------------------------------------------------+
| 주요 결과(실제 record만) | 현재 external review round             |
+-------------------------------------------------------------------+
```

### 7.2 프로젝트 상세

```text
홈 > 연구 프로젝트 > <project>
+-----------------------------+-------------------------------------+
| 연구 질문·목적·가설         | raw state + active gate             |
| claimable / not claimable   | current single task / blocker      |
+-----------------------------+-------------------------------------+
| milestone filter: completed | active | blocked | queued           |
| Mxx status + qualifier + result + lesson + evidence + next gate   |
+-------------------------------------------------------------------+
| own artifacts | own papers | own review rounds                    |
| canonical source links and last read hash                          |
+-------------------------------------------------------------------+
```

각 project page의 기본 source는 다음 8개다.

1. `PROJECT.yaml`
2. `README.md`
3. `STATUS.md`
4. canonical research plan
5. milestone ledger
6. execution tracker
7. `docs/surveys/README.md`
8. `results/RESULT_INDEX.md`

project page는 1–6을 live control set으로, 7–8을 live evidence index로 읽는다. milestone result와
lesson은 문서에 명시된 경우만 표시하고, 없으면 `canonical 문서에 기록되지 않음`으로 둔다.

### 7.3 결과와 근거

```text
홈 > 결과와 근거
[owner: all/project/platform] [class] [type] [state] [search]
+-------------------------------------------------------------------+
| artifact title       PARTIAL / TERMINAL_SHORTFALL                 |
| owner | class | milestone/work package | run/date/revision        |
| inputs + hashes | summary | lesson | gate impact                 |
| can claim | cannot claim | canonical path label | [웹에서 열기]  |
+-------------------------------------------------------------------+
```

넓은 table에는 위쪽 보조 horizontal scrollbar와 아래 native scrollbar를 하나의 scroll state로
동기화한다. 중복 content layer를 만들지 않는다.

### 7.4 external review round 목록·상세

```text
홈 > 외부검토
[project] [round type] [state] [assigned to me]
+-------------------------------------------------------------------+
| review_round_id | purpose | protocol | class | progress           |
| source gate | calibration | empirical | agreement/time status     |
+-------------------------------------------------------------------+

round detail
+-------------------------------------------------------------------+
| purpose / protocol / guideline version / claim limits             |
| sample manifest hash / blinded seed hash / independent reviewers  |
| SOURCE GATE 1/60   CALIBRATION NOT_STARTED   EMPIRICAL LOCKED      |
+----------------------+--------------------------------------------+
| filter/search samples| contact sheet/source packet/review form    |
| previous/next        | confidence/reason/time/finalize            |
| progress             |                                            |
+----------------------+--------------------------------------------+
```

new native review form에는 iframe을 쓰지 않는다. legacy self-contained review HTML만 isolated
iframe으로 연다. frame 위 shell에 classification, source run hash와 `LEGACY_READ_ONLY`를 표시한다.

### 7.5 회의와 결정

```text
홈 > 회의와 결정
+-------------------------------------------------------------------+
| previous goal | execution result | artifact | shortfall/lesson    |
| blocker | decision item | owner | target date | canonical minutes |
+-------------------------------------------------------------------+
| decision type: SUBMIT / PROTOCOL_FREEZE / GO-NARROW-NO-GO /       |
| SOURCE_ACQUISITION / CALIBRATION / EMPIRICAL_START / SCOPE /       |
| ACTUAL_VEHICLE_TRANSFER                                            |
+-------------------------------------------------------------------+
```

page는 decision/minutes를 projection할 뿐 research gate를 수정하지 않는다. `GO`, protocol freeze,
empirical start는 canonical decision와 gate evidence가 이미 존재할 때만 표시된다.

### 7.6 논문·사용자 메뉴

```text
논문: [project] [status] [manuscript/PDF/supplement]
card: owner, paper question, evidence scope, claim limit, manifest hash, open

사용자: pseudonymous display name | role | current round grants
        내 배정 | 내 진행률 | logout
```

## 8. 사용자 역할과 권한

전역 role은 최소화하고 round별 capability를 결합한다.

| 동작 | 연구책임자 | 독립 검토자 | round adjudicator |
|---|:---:|:---:|:---:|
| project/result/paper projection 열람 | 허용 범위 내 | 허용 범위 내 | 허용 범위 내 |
| review round 생성·종료 | O | X | X |
| sample manifest 등록·freeze | O | X | X |
| reviewer/adjudicator 배정 | O | X | X |
| 자신의 assigned sample 열람 | 필요 시 | O | 불일치 단계에서만 |
| independent verdict 입력/finalize | reviewer로 별도 배정된 경우 | O | X |
| 다른 reviewer verdict 열람 | round 완료 후 aggregate만 | X | 두 독립 판정 완료 후 불일치만 |
| adjudication record 생성 | X | X | O |
| original verdict overwrite | X | X | X |
| progress/agreement/time aggregate | O | 자신의 progress만 | assigned round adjudication progress |
| deidentified public export | O | X | X |
| canonical Markdown 수정 | X | X | X |

### 8.1 adjudicator 모델 비교와 선택

| 대안 | 장점 | 위험 |
|---|---|---|
| 전역 `ADJUDICATOR` role | 단순한 운영 | 모든 round에 과도한 권한, reviewer conflict 통제가 어려움 |
| reviewer account의 round별 grant | 최소권한, 목적별 분리, audit 용이 | assignment table과 검증이 필요 |

**선택:** 기본 account role은 `RESEARCH_LEAD` 또는 `REVIEWER`로 두고,
`round_membership(capability=ADJUDICATE)`를 회차별로 부여한다. 같은 round에서 independent
reviewer로 배정된 account에는 adjudication grant를 줄 수 없다. 이것이 “별도 adjudicator” 계약을
가장 정확히 집행한다.

## 9. canonical 문서와 데이터 소유권

| 데이터 | 권위 | portal 동작 | write 허용 |
|---|---|---|---|
| 프로젝트 순서/경로 | `PROJECT_REGISTRY.json` | live read | 없음 |
| project owner/canonical paths | `PROJECT.yaml` | live read+path validation | 없음 |
| 현재 state/evidence/boundary/blocker/next | `STATUS.md` | live read | 없음 |
| RQ/가설/success/claim boundary | research plan | live read | 없음 |
| 전체 milestone/Todo | milestone ledger | live read | 없음 |
| current single work | execution tracker | live read+ledger cross-check | 없음 |
| related-work authority/date | survey index와 CURRENT survey | live read | 없음 |
| project result index | `RESULT_INDEX.md` | live read | 없음 |
| platform state | `PLATFORM.yaml`, README/STATUS | live read | 없음 |
| immutable run metadata | `RUN_MANIFEST.json`, `RESULT.json` | registered read | 없음 |
| review 운영 판정 | round별 restricted SQLite | authenticated API | 역할/상태 전이 범위 내 |
| adjudication | 별도 adjudication row | append only | adjudicator만 |
| public aggregate | closed round의 deidentified export run | 생성 후 immutable | lead가 명시적으로 export |

기본 동작은 read-only projection이다. Markdown writeback은 별도 decision 없이는 구현하지 않는다.
향후 검토하더라도 allowlist, original hash, optimistic locking, conflict detection, revision history,
actor/time audit와 field-level patch만 허용한다. 전체 Markdown rewrite, RQ, success criteria,
claim boundary 변경은 금지한다. scope 변경은 decision record와 새 research-plan version으로만 한다.

## 10. artifact registry와 route 설계

### 10.1 registry 구성

maintained hardcoded path 목록을 두지 않고 다음 권위에서 registry를 생성한다.

1. `PROJECT_REGISTRY.json`의 project/platform artifact root
2. 각 `PROJECT.yaml`/`PLATFORM.yaml`의 owner와 artifact root 일치
3. owner root 아래의 `RUN_MANIFEST.json`과 `RESULT.json`
4. 각 owner의 `RESULT_INDEX.md`
5. immutable legacy는 `artifacts/LEGACY_OWNERSHIP.json`
6. paper는 각 project의 `paper/PAPER_MANIFEST.json`

path classification과 manifest classification이 다르거나 owner root 밖으로 resolve되면 registry
build를 중단한다. symlink target, `..`, absolute user input과 unknown classification은 거부한다.

### 10.2 ArtifactRecord

```text
artifact_id                 opaque stable portal ID
owner_kind                  PROJECT | PLATFORM
owner_id                    project_id | platform_id
classification              PUBLIC | RESTRICTED | INTERMEDIATE | LEGACY_IMMUTABLE
artifact_type               report/result/manifest/review_ui/paper/package/failure/platform_release
experiment_id, run_id, created_at, code_revision
milestone_id, work_package_id
source_inputs[]              logical source IDs + hashes; no client absolute path
summary, lessons, gate_impact
claim_scope, claim_limitations
canonical_path              server-side only
web_assets[]                allowlisted relative assets + hashes + MIME
manifest_hash
```

`canonical_path`는 client JSON이나 URL에 보내지 않는다. UI에는 owner-relative display label만
제공한다. raw scene ID, raw path, CoC full text와 image bytes는 public record에 넣지 않는다.

### 10.3 routes

```text
GET /api/artifacts?<filters>                 metadata filtered by role/class
GET /artifacts/<opaque-artifact-id>          detail shell
GET /assets/<opaque-artifact-id>/<asset-id>  exact allowlisted asset only
```

route resolver는 registry record가 가진 exact resolved path만 연다. directory listing, arbitrary
filename parameter와 repository-relative route는 제공하지 않는다. response에는 `nosniff`, CSP,
classification header와 cache policy를 붙인다.

### 10.4 public export

public export는 restricted DB/file의 복사가 아니다. allowlisted aggregate field만 새 object로
직렬화한다. export 전 leakage test는 raw identifier, path separator pattern, CoC full-text hash,
image magic bytes, restricted artifact ID와 forbidden key를 검사한다. 결과는 해당 review owner의
`artifacts/projects/<project-id>/public/`에 새 immutable run으로 쓴다.

## 11. external review 데이터 모델

review 목적이 다른 회차는 다른 `review_round_id`를 사용한다. 허용 type은 다음과 같다.

- `M16_SOURCE_REVIEW`
- `M16_EXPERT_PILOT`
- `IMAGE_ONLY_SCENE_REVIEW`
- `ASSOCIATION_LIFECYCLE_REVIEW`
- `SPECIFICATION_INTERFACE_REVIEW`
- `EBLC_LANGUAGE_EVALUATION`
- `PAPER_INTERNAL_CLAIM_REVIEW`

### 11.1 entity 관계

```text
ReviewRound 1---1 SampleManifest 1---N Sample
ReviewRound 1---N RoundMembership N---1 User
Sample     1---N Assignment N---1 User
Assignment 1---N ReviewRevision
Sample     0---1 AdjudicationRecord
ReviewRound 1---N GuidelineRevision
ReviewRound 1---N AuditEvent
ReviewRound 1---N ExportRecord
```

### 11.2 ReviewRound 필수 필드

```text
project_id, review_round_id, review_type, purpose
protocol_uri, requirements_uri, classification
target_type, sample_manifest_hash
independent_review_required, reviewers_per_sample
assignment_algorithm_version, blinded_seed_ciphertext, blinded_seed_hash
adjudicator_membership_id, guideline_version, guideline_revision_count, max_revisions=2
round_state, ui_status, source_gate_status, calibration_status, empirical_status
progress_contract_version, agreement_contract_version
export_root, claim_limitations, created_by, created_at, closed_at
```

### 11.3 Sample과 source 판정

sample은 portal용 opaque ID와 owner 내부 source reference를 분리한다. source closure 결과는
다음 네 값만 사용한다.

```text
SOURCE_COMPLETE | REVIEW_REQUIRED | UNSUPPORTED | CONFLICT
```

reviewer 선택은 source record를 만들지 않는다. `SOURCE_COMPLETE`는 required source field가
모두 manifest reference/hash를 가지고 validator를 통과했을 때만 계산된다. image-only round는
항상 `contract_readiness=REVIEW_REQUIRED`와
`IMAGE_ONLY_CANNOT_ESTABLISH_SOURCE_CLOSURE`를 보존한다.

track ID, timestamp, transform, jurisdiction, rule, missing source 또는 recorded vehicle assurance를
image response에서 추정해 채우는 API field는 만들지 않는다. `UNKNOWN` fact와 source packet
누락은 별도 reason code다. simulation binding은 recorded-rig/vehicle assurance와 다른 field다.

### 11.4 round 상태

```text
DRAFT
ELIGIBILITY_BLOCKED
READY_CALIBRATION
CALIBRATION_ACTIVE
READY_EMPIRICAL
EMPIRICAL_ACTIVE
ADJUDICATION_ACTIVE
COMPLETE
TERMINAL_SHORTFALL
```

상태 전이는 server가 prerequisites에서 계산한다. UI button이 research gate를 직접 바꾸지 않는다.

## 12. reviewer assignment와 adjudication workflow

### 12.1 deterministic assignment

1. lead가 sample manifest를 등록한다.
2. validator가 distinct sample, slice/outcome quota와 classification을 검증한다.
3. manifest hash를 freeze한다.
4. restricted seed와 algorithm version을 고정한다.
5. 각 `(sample, reviewer, slot)`에 대해 HMAC-SHA256 score를 계산하고 balanced assignment를 만든다.
6. sample마다 서로 다른 reviewer 최소 2인, reviewer별 배정 수 차이 최대 1을 검증한다.
7. reviewer별 blinded order도 별도 HMAC score로 정렬한다.
8. assignment manifest를 hash하고 이후 수정 대신 새 round/revision을 만든다.

seed 원문은 restricted DB에 암호화 또는 host secret으로 보호하고, public export에는 seed hash와
algorithm version만 포함한다. Python runtime의 암묵적 iteration order에 의존하지 않는다.

### 12.2 독립 review

- reviewer는 자신의 assignment와 protocol/guideline만 본다.
- 다른 reviewer verdict, aggregate agreement와 adjudication은 독립 finalize 전 보이지 않는다.
- finalize 후 원 verdict는 immutable하다. 허용 revision은 explicit revision record로 추가한다.
- start/end, active duration, confidence, reason code와 correction action을 server event로 기록한다.
- sample previous/next와 개인 progress를 제공한다.

### 12.3 adjudication

1. 필요한 독립 판정 수가 모두 finalized되기 전에는 sample을 adjudication queue에 넣지 않는다.
2. exact agreement sample은 기본 queue에서 제외한다.
3. 별도 round adjudicator는 disagreement sample과 두 original verdict를 읽는다.
4. final verdict와 rationale/source reference를 새 `AdjudicationRecord`로 기록한다.
5. original verdict를 update/delete하지 않는다.
6. adjudicator가 해당 round reviewer였거나 assignment가 불완전하면 fail closed한다.

## 13. agreement·progress 계산 계약

### 13.1 progress

```text
reviewer_progress = finalized_assigned / assigned
independent_scene_progress = samples_with_required_finalized_reviews / total_samples
adjudication_progress = adjudicated_disagreements / disagreement_samples_ready
round_progress는 세 분수를 따로 표시하며 하나의 평균으로 숨기지 않음
```

미배정 sample, withdrawn assignment와 invalidated revision은 별도 count로 보고한다. denominator를
사후 변경하려면 새 manifest version과 audit event가 필요하다.

### 13.2 applicability Krippendorff alpha

nominal alpha를 사용한다.

```text
delta(c, k) = 0 if c == k else 1
alpha = 1 - Do / De
```

- item당 유효 독립 판정 2개 이상만 포함한다.
- missing response는 category가 아니며 제외 count를 보고한다.
- protocol이 정한 abstention은 explicit category로 포함한다.
- `De=0`이면 alpha를 1로 꾸미지 않고 `NOT_ESTIMABLE_NO_CATEGORY_VARIANCE`로 보고한다.
- included scene 수, category counts, missing counts, formula version과 confidence interval을 함께 낸다.
- M16 gate는 applicability alpha `>=0.67`이다.

### 13.3 기타 metric

- categorical field agreement: exact agreement와 confusion matrix
- numeric interval agreement: overlap 여부와 intersection-over-union; unit/frame 일치 sample만 계산
- source agreement: normalized source record ID 집합의 exact/Jaccard, raw path 비교 금지
- scene correction rate: adjudicated scene 중 final record가 적어도 한 original field와 다른 비율
- field correction rate: adjudicated comparable field 중 final이 적어도 한 original과 다른 비율
- reviewer time: server event 기반 active seconds의 median, IQR, p90; idle timeout 제외 규칙 version 고정
- agreement, correction, time은 calibration과 empirical set을 섞지 않고 별도 보고

guideline revision은 최대 2회다. revision 3 요청은 API에서 거부한다. revision 전·후 sample과
metric을 섞지 않고 version별로 보고한다.

### 13.4 M16 start gate

```text
source_cohort_ready =
  distinct_eligible == 60
  AND each_slice == 20
  AND each_outcome == 10
  AND all_joint_cells_meet_locked_manifest
  AND source_complete == 60

calibration_start_allowed =
  source_cohort_ready
  AND schema_ui_export_validated
  AND assignments_valid

empirical_annotation_start_allowed =
  calibration_start_allowed
  AND calibration_complete
  AND reviewer_training_complete
  AND baseline_model_split_manifest_frozen
  AND guideline_revision_count <= 2
```

현재 입력에서는 `distinct_eligible=1`, `human_source_review=0`이므로 둘 다 `false`다. UI는
부족한 59개와 빈 slice/outcome/joint cell을 보여주고 annotation endpoint를 403으로 거부한다.

## 14. 보안과 restricted/public 경계

### 14.1 server·session

- bind address는 코드 상수 `127.0.0.1`; `--host` option을 만들지 않는다.
- Host/Origin은 `127.0.0.1:<port>`와 `localhost:<port>`만 허용한다.
- password/access code는 random salt의 `hashlib.scrypt`로 hash하고 평문 저장·log를 금지한다.
- session ID는 `secrets.token_urlsafe`, server-side session table, idle/absolute timeout을 사용한다.
- cookie는 `HttpOnly; SameSite=Strict; Path=/`; TLS mode일 때 `Secure`를 추가한다.
- state-changing request는 CSRF token과 `application/json` content type을 요구한다.
- login rate limit, constant-time hash comparison과 generic failure message를 사용한다.

새 framework는 필요하지 않다. 범위가 loopback-only JSON API와 정적 asset route로 제한되어
현재 Python server를 작은 명시적 router로 확장할 수 있다. route·auth 복잡도가 이 설계 범위를
넘는다고 RED test가 보일 때만 별도 framework decision을 작성한다.

### 14.2 request/route

- JSON body, string length, enum, list count와 export size 상한
- URL percent-decoding 후 `..`, separator, NUL, absolute path 거부
- resolved path의 owner root containment와 no-symlink 검사
- MIME allowlist와 `X-Content-Type-Options: nosniff`
- directory listing 없음
- audit event에 actor, action, round, object opaque ID, timestamp, result를 기록하되 secret/raw path 금지

### 14.3 CSP와 iframe

outer portal 기본 CSP:

```text
default-src 'self'; connect-src 'self'; img-src 'self' data: blob:;
style-src 'self'; script-src 'self'; frame-src 'self'; object-src 'none';
base-uri 'none'; form-action 'self'; frame-ancestors 'self'
```

new native page는 inline script를 사용하지 않는다. legacy self-contained HTML은 별도 isolated
response policy를 사용하며 `allow-same-origin`을 절대 부여하지 않는다. manifest가 요구할 때만
`allow-scripts`, export가 있을 때만 `allow-downloads`를 부여한다. `allow-forms`, `allow-modals`는
실제 package test가 요구하지 않으면 제거한다. 외부 network는 CSP `connect-src 'none'`로 막는다.

### 14.4 SQLite lifecycle, backup, export

- portal **build run**은 생성 즉시 immutable하다.
- review **operations run**은 `OPEN` 동안 round DB만 append/update할 수 있고 `CLOSED` 후 immutable하다.
- round 하나가 owner와 classification 하나만 가진다. 서로 다른 project 또는 public/restricted를
  한 DB에 넣지 않는다.
- SQLite는 WAL, foreign key, transaction, busy timeout과 schema version을 사용한다.
- backup은 SQLite backup API로 restricted sibling `backups/`에 만들고 hash/audit를 기록한다.
- close 시 checkpoint, integrity check, final export/hash 후 DB를 freeze한다.
- public export는 별도 public run이며 restricted backup의 복제가 아니다.
- existing localStorage JSON/CSV는 자동 import하지 않는다. lead가 provenance를 검토해 새 round의
  명시적 import를 승인할 때만 import preview와 hash를 남긴다.

## 15. SSH 접근과 서비스 운영

remote host에서 portal은 계속 loopback에만 열린다.

```bash
# remote host
python3 -m apps.research_portal.run \
  --output-dir artifacts/projects/guardsynth-coc/restricted/guardsynth-project-portal-001/<new-run-id> \
  --serve --port 8765

# reviewer workstation
ssh -N -L 8765:127.0.0.1:8765 <user>@<remote-host>
```

reviewer는 `http://127.0.0.1:8765/`에 접속한다. reverse proxy, public ingress, `0.0.0.0` bind와
cloud object public URL은 기본 운영에 포함하지 않는다. 여러 reviewer가 필요한 경우 각각 SSH
account/tunnel을 사용하고 portal authentication을 추가 방어선으로 유지한다.

운영 시작 전 check:

1. output run과 review operations run ID가 새 값인지 확인
2. loopback socket 확인
3. classification/route manifest 검증
4. login bootstrap secret을 out-of-band 전달하고 최초 로그인 후 회전
5. backup target과 free space 확인
6. audit log와 DB integrity smoke test

## 16. TDD 계획

모든 구현 단계는 먼저 실패하는 test를 추가한 뒤 최소 구현을 한다.

### Phase A — projection과 정보구조

1. registry 순서의 project 5개와 platform 1개가 별도 model인지 RED test
2. 6개 control document live reload와 survey/result live index test
3. exactly-one research plan, canonical path containment와 tracker–ledger sync fail-closed test
4. list-aware STATUS, exact status+qualifier test
5. 새 home/project/platform sitemap과 모든 home/up links test

### Phase B — artifact와 paper registry

1. project/platform owner와 classification mismatch RED test
2. legacy immutable read-only, public/restricted separation test
3. opaque route, traversal, symlink, absolute path leakage test
4. paper manifest 5개와 project ownership test
5. no-result/shortfall 렌더링 test

### Phase C — review backend

1. round create/freeze/close state machine test
2. deterministic balanced assignment와 reviewer isolation test
3. original verdict immutability와 separate adjudication test
4. progress/alpha/correction/time golden fixture test
5. guideline revision 3 거부 test
6. M16 1/60 `annotation_start_allowed=false` test

### Phase D — auth/security/export

1. password hash/session/CSRF/RBAC test
2. reviewer가 다른 reviewer verdict를 읽을 수 없는 route test
3. Host/Origin, body size, enum, traversal, MIME test
4. CSP와 package별 iframe sandbox test
5. public export forbidden-key/identifier/image-byte leakage 0 test

### Phase E — build/compatibility

1. existing v9 run read-only compatibility fixture
2. new run overwrite refusal와 manifest hash test
3. 모든 generated href/src/route resolve test
4. loopback-only integration test
5. file naming, project structure/link, build manifest와 root integrity checks

## 17. 단계별 migration 계획

### M0. 승인과 freeze

- 이 문서 승인 전 code, service, DB와 artifact를 변경하지 않는다.
- v9 portal과 9개 review package hash를 compatibility baseline으로 고정한다.

### M1. read-only projection refactor

- `run.py`의 동작을 test로 고정하고 module만 분리한다.
- 새 home, project, platform, results, meeting, paper read-only page를 추가한다.
- 기존 CLI와 existing build mode를 유지한다.

### M2. owner-aware registries

- hardcoded review/paper/artifact path를 registry projection으로 교체한다.
- legacy assets는 원래 owner/classification과 hash를 가진 read-only record로 등록한다.
- static offline snapshot compatibility option은 유지한다.

### M3. dynamic review backend

- feature flag/explicit CLI option이 있을 때만 auth와 round API를 시작한다.
- 새 review round만 DB에 기록한다. existing localStorage output은 자동 import하지 않는다.
- M16 gate와 reviewer isolation을 먼저 구현하고 실제 reviewer 운영은 별도 승인 후 시작한다.

### M4. hardening과 public export

- CSP, Host/Origin, CSRF, rate limit, backup/close/export와 leakage test를 통과한다.
- public export는 deidentified aggregate용 새 immutable run만 만든다.

### M5. cutover

- new portal run을 새 ID로 build한다.
- v9와 모든 legacy run은 그대로 둔다.
- replacement acceptance가 모두 통과한 뒤에만 dead code를 제거한다.

## 18. 승인 후 변경할 정확한 경로

이번 설계 단계에서는 아래 파일을 만들거나 수정하지 않는다. 승인 후 예상 change set이다.

### 18.1 application source

```text
apps/research_portal/README.md                         modify
apps/research_portal/run.py                            modify; CLI compatibility shell
apps/research_portal/projection.py                     new
apps/research_portal/artifact_registry.py              new
apps/research_portal/paper_registry.py                 new
apps/research_portal/review_store.py                   new
apps/research_portal/review_backend.py                 new
apps/research_portal/review_metrics.py                 new
apps/research_portal/security.py                       new
apps/research_portal/schemas/artifact_registry.schema.json new
apps/research_portal/schemas/paper_manifest.schema.json    new
apps/research_portal/schemas/review_round.schema.json      new
apps/research_portal/schemas/sample_manifest.schema.json   new
apps/research_portal/schemas/review_export.schema.json     new
```

### 18.2 site assets

```text
apps/research_portal/site/index.html                   modify
apps/research_portal/site/projects.html                new
apps/research_portal/site/project.html                 modify
apps/research_portal/site/platform.html                new
apps/research_portal/site/evidence.html                new
apps/research_portal/site/artifact.html                new
apps/research_portal/site/reviews.html                 new
apps/research_portal/site/review_round.html            new
apps/research_portal/site/review_sample.html           new
apps/research_portal/site/review_adjudication.html     new
apps/research_portal/site/meetings.html                new
apps/research_portal/site/papers.html                  modify
apps/research_portal/site/login.html                   new
apps/research_portal/site/portal.css                   modify
apps/research_portal/site/portal.js                    modify
```

기존 `milestones.html`, `review.html`, `project_review.html`, `guide.html`은 compatibility route로
먼저 유지한다. replacement와 redirect/link test가 통과한 뒤 삭제 여부를 별도 diff에서 결정한다.

### 18.3 tests

```text
apps/research_portal/tests/test_portal.py               modify; compatibility coverage 유지
apps/research_portal/tests/test_projection.py           new
apps/research_portal/tests/test_artifact_registry.py    new
apps/research_portal/tests/test_paper_registry.py       new
apps/research_portal/tests/test_review_store.py         new
apps/research_portal/tests/test_review_workflow.py      new
apps/research_portal/tests/test_review_metrics.py       new
apps/research_portal/tests/test_security.py             new
apps/research_portal/tests/test_site_integrity.py       new
tests/structure/test_project_layout.py                  modify; portal ownership/path contract만
```

### 18.4 project-owned metadata와 decisions

```text
projects/01-safety-constrained-coc/paper/PAPER_MANIFEST.json          new
projects/02-specification-alignment/paper/PAPER_MANIFEST.json         new
projects/03-sequential-coc-verification/paper/PAPER_MANIFEST.json     new
projects/04-guardsynth-coc/paper/PAPER_MANIFEST.json                  new
projects/05-eblc-language-verification/paper/PAPER_MANIFEST.json      new
projects/04-guardsynth-coc/docs/requirements/GUARDSYNTH_RESEARCH_PORTAL_REQUIREMENTS_V01.md new
projects/04-guardsynth-coc/docs/decisions/GUARDSYNTH_PORTAL_WRITEBACK_SCOPE_DECISION_V01.md new
projects/04-guardsynth-coc/docs/decisions/GUARDSYNTH_PORTAL_REVIEW_STORAGE_DECISION_V01.md  new
```

### 18.5 generated paths

```text
artifacts/projects/guardsynth-coc/restricted/guardsynth-project-portal-001/<new-run-id>/
artifacts/projects/<project-id>/restricted/research-review-round-001/<review-round-id>/
artifacts/projects/<project-id>/public/research-review-export-001/<export-run-id>/
```

review operations directory는 `OPEN` 동안 운영 state이고 close/final integrity 후 immutable이다.
기존 `artifacts/results/`, `artifacts/intermediate/`와 portal v1–v9는 수정하지 않는다.

## 19. acceptance criteria

### Registry/projection

- [ ] 5개 project가 registry 순서로 독립 표시된다.
- [ ] EBLC/BCV가 project card가 아닌 platform으로 표시된다.
- [ ] project 05 결과와 platform implementation 상태가 분리된다.
- [ ] canonical control 문서 6개가 page load/API read마다 reload된다.
- [ ] survey index와 result index도 owner page에서 live read된다.
- [ ] stale/missing/duplicate research plan 또는 active milestone mismatch가 fail closed한다.
- [ ] project raw state와 active gate/status qualifier가 구분된다.

### Artifacts/UI

- [ ] artifact owner, class, milestone/work package, run/date/revision, input hash, result, lesson,
  gate impact, claim scope/limit과 web route가 표시된다.
- [ ] `PUBLIC/RESTRICTED/INTERMEDIATE/LEGACY_IMMUTABLE`가 섞이지 않는다.
- [ ] `PARTIAL/BLOCKED/TERMINAL_SHORTFALL/COMPLETE`가 text와 icon으로 구분된다.
- [ ] 결과 없는 gate가 success card로 보이지 않는다.
- [ ] 모든 page에 home과 상위 project/platform link가 있다.
- [ ] mobile reading, keyboard focus, previous/next, search/filter와 table dual-scroll이 동작한다.
- [ ] relation map은 zoom, fit, legend와 keyboard-accessible alternative table을 제공한다.

### Review

- [ ] 여러 목적의 review round를 만들 수 있고 목적을 한 round에 혼합할 수 없다.
- [ ] sample manifest hash와 deterministic balanced assignment가 재현된다.
- [ ] sample마다 최소 2인 독립 review와 별도 adjudicator가 강제된다.
- [ ] reviewer는 다른 reviewer verdict를 독립 finalize 전에 볼 수 없다.
- [ ] original verdict는 immutable하고 adjudication은 별도 record다.
- [ ] progress, nominal Krippendorff alpha, correction과 time golden test가 통과한다.
- [ ] guideline revision 3회째가 거부된다.
- [ ] M16 1/60에서 empirical annotation endpoint와 UI가 잠긴다.
- [ ] image-only response가 source closure로 승격되지 않는다.

### Security/operations

- [ ] output overwrite를 거부한다.
- [ ] bind는 loopback only이고 Host/Origin allowlist를 적용한다.
- [ ] login, scrypt hash, HttpOnly/SameSite cookie, CSRF와 role/round authorization이 동작한다.
- [ ] path traversal, symlink escape, unknown asset과 oversized input을 거부한다.
- [ ] restricted identifier와 absolute path가 HTML/URL/client JSON에 노출되지 않는다.
- [ ] public export의 forbidden restricted identifier/image byte leakage가 0이다.
- [ ] iframe sandbox와 CSP가 package별 최소권한이다.
- [ ] audit, backup, DB integrity, close/freeze와 deidentified export가 재현된다.

### Required closeout checks

- [ ] portal test suite
- [ ] project structure/link tests
- [ ] `python3 cli/checks/file_naming.py`
- [ ] `python3 -m cli.checks.build_manifest`
- [ ] `MANIFEST.sha256` check
- [ ] `git diff --check`

## 20. 기존 portal run 호환성

1. 기존 run directory와 파일을 수정·삭제·rename하지 않는다.
2. 기존 `python3 -m apps.research_portal.run --output-dir ... [--serve]` CLI는 유지한다.
3. 기존 static snapshot의 `index.html`, `project_01.html`~`project_05.html`, `review_01.html`~
   `review_05.html`, `PORTAL_DATA.json`과 review asset은 그대로 열 수 있다.
4. new server가 old snapshot을 열 때는 missing new registry를 오류로 만들지 않고
   `LEGACY_READ_ONLY` mode로 제공한다.
5. old review localStorage/JSON/CSV를 자동으로 DB에 import하지 않는다.
6. legacy `artifacts/results/` link는 `LEGACY_IMMUTABLE` badge와 read-only route로만 제공한다.
7. new portal run은 새 run ID를 사용하고 source/build/route manifest hash를 기록한다.
8. compatibility test는 v9 manifest의 project 5, milestone 52, review 9, paper 2와 asset hash를
   baseline으로 사용하되 이 숫자를 future canonical truth로 하드코딩하지 않는다.

## 21. 구현 승인 시 고정할 결정

이 설계는 다음 선택을 권고한다.

1. static builder를 유지하고 dynamic review backend만 같은 application 안의 명시적 option으로 추가한다.
2. adjudicator는 전역 role이 아니라 round별 capability로 부여한다.
3. review DB는 round별 restricted operations run에 두고 close 후 immutable하게 만든다.
4. canonical Markdown writeback은 구현하지 않는다.
5. restricted legacy HTML은 read-only isolated iframe으로 유지하고 새 review는 native UI/API로 만든다.
6. paper, artifact와 review route는 owner/classification-aware manifest/registry에서 만든다.

승인 전에는 위 예정 경로의 code, schema, DB, service와 artifact를 만들지 않는다.
