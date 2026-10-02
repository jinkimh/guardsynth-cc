# GuardSynth Studio 설계 검증 보고서 v0.1

- project_id: `guardsynth-coc`
- subproject_id: `guardsynth-studio`
- 대상: [설계 v0.1](../designs/GUARDSYNTH_STUDIO_DESIGN_V01.md)
- 기준: [승인된 요구사항 v0.1](../requirements/GUARDSYNTH_STUDIO_REQUIREMENTS_V01.md)
- 검증 방법: 저장소 코드 정적 대조, 요구사항 추적, 상태/경합/누출 시나리오의 문서상 검토.
- 판정: 요구 범위의 설계 대응 확인. 배포·구현 검증은 미수행이며 사용자 설계 승인은 미기록.
- 제한: 독립 검토자가 수행한 검증이나 실행된 AT 수용 시험 결과가 아니다. 아래 기대 결과는 구현 검증 의무다.
- 후속 이력: 2026-09-29 사용자 설계 승인 후 구현이 진행되었다. 위 미구현/미승인은 본 설계 검토 당시 상태이며, 현재 결과는 [구현 검증 보고서](GUARDSYNTH_STUDIO_IMPLEMENTATION_VERIFICATION_REPORT_V01.md)에 기록한다.

## 1. 검증 범위와 근거

GS-01~GS-06, AT-01~AT-15 및 공통 상태·보안 요구를 설계 D1~D10과 대조했다.
다음 코드의 실제 함수·스키마를 읽어 재사용 주장을 확인했다. 모델/API/GPU/솔버 호출,
영상 업로드, 서버 실행/재시작, 학습, 기존 검토 수정은 수행하지 않았다.

| 근거 | 정적 확인 결과와 설계 반영 |
|---|---|
| [review_store.py](../../../../apps/research_portal/review_store.py) | 회차/할당 중심, revision 불변 및 상한 존재. 범용 autosave DB로 재사용하지 않고 D1/D3의 별도 schema 선택 |
| [security.py](../../../../apps/research_portal/security.py) | scrypt, session/CSRF, loopback Host/Origin, 경로·CSP 도우미 존재. upload/provider 보호까지 구현된 것으로 주장하지 않음 |
| [proposal schema](../../src/guard_synth/schemas/constraint_proposal_bundle.schema.json) | proposal verdict에 APPROVED 없음, CLAIMED 및 text_included=false. D6의 승인 envelope와 원 CoC 저장 분리 |
| [action_contract.py](../../../../platforms/eblc-bcv/src/guard_synth_eblc/action_contract.py) | 두 행동, all-clear 진입, 미확인 이전 상태 유지, 기본 base_consistency 1개. D7의 바인딩·추가 질의 필요 |
| [action schema](../../../../platforms/eblc-bcv/src/guard_synth_eblc/schemas/eblc_action_contract.schema.json) | horizon 최소 2, obligations 1–16, null identity 가능; parser는 horizon 최대 32 검사. D7의 더 좁은 Studio profile과 D6의 binding 승인 적용 |
| [smt_compiler.py](../../../../platforms/eblc-bcv/src/guard_synth_eblc/smt_compiler.py) | check_queries는 질의별 SAT/UNSAT/UNKNOWN, witness·SMT2·버전 반환. timeout 설정 없음, witness는 model_completion=True. D7/D9 외부 시간 제한·관찰 재사용 금지 |
| [cnl_renderer.py](../../../../platforms/eblc-bcv/src/guard_synth_eblc/cnl_renderer.py) | action renderer는 구조 검증 후 영어 템플릿·field paths·hash 반환, SMT/source gate 없음. D7 서비스 전제 검사 |
| [scene_conditioned_cnl.py](../../src/guard_synth/scene_conditioned_cnl.py) | 두 술어, observed offsets=[0], 미래 source frame 거부, 한영 템플릿, 학습 export false. 신규 일반 영상 adapter 완료 근거가 아님 |
| [qualitative_scene_contract.py](../../src/guard_synth/qualitative_scene_contract.py), [reviewed_action_contract.py](../../src/guard_synth/reviewed_action_contract.py) | scene18 clip/시점/대상 pin 및 단일 검토 관찰. D10에서 고정 사례를 범용 extractor로 사용하지 않음 |

## 2. 기능 요구 추적표

각 행의 “대응”은 설계 조항이 있다는 뜻이다. 동작 통과라는 뜻이 아니다.

| 요구 | 세부 요구 전체의 설계 대응 | 검토 시나리오 | 결과 |
|---|---|---|---|
| GS-01 | D2 PTS/추출/전체 시점; D3 영상 해시·출처·권한·설정·frame 근거·이름·도형 수정/현재 삭제; D9 손상/형식/공개 한도; D3 픽셀의 거리/의도 과장 금지 | W01, W02, W15 | 대응 |
| GS-02 | D3 raw/edited/model/prompt/입력·이력 및 사실/가정/미확인 분리; D4 명시 batch diff 승인; D3/D6 복수 행동·4상태·선택 메모·의미 예제·역할/노출·별도 승인 | W04, W06, W12, W16 | 대응 |
| GS-03 | D3/D6 대상·영역·적용/해제/시간·규칙·가정·지원 profile; 출처 3종·실제 조항/버전 대조·국가/시간 추정 금지; 4값/미적용·binding 상태·기존 proposal 필드·별도 사람 승인 | W07, W08, W09, W17 | 대응 |
| GS-04 | D2 기본/고급 UI; D7 제한 행동·해제·horizon·초기 상태·미래 witness 금지·미지원·재파싱/타입·Q1–Q5 기대/실제·공허성·timeout/UNKNOWN/실제 안전 경계; D6 버전 전파 | W08, W09, W10, W11 | 대응 |
| GS-05 | D7 결정적 영어/한글 profile·조항/버전·원문 권위·수동 파생문; D3 원본 보존·autosave/복구·해시; D6 충돌/재승인; D8 완료/오류/실제 수 | W03, W04, W05, W12, W16 | 대응 |
| GS-06 | D8 JSONL provenance·mask·버전·baseline pair·draft/NOT_APPLICABLE·split 계보·causal 검사·입력/목표 분리·독립성·새 export·단일 snapshot·제외 수; D5 텍스트/캐시 누출 | W02, W07, W12, W13, W14, W17, W18 | 대응 |
| 공통 상태·보안·범위 | D1 로컬/독립 DB/소유, D3~D6 revision/job/승인, D9 인증·비밀·경로·HTML·자원·취소·중복, D10 미결정과 기존 실험 경계 | W03~W05, W14, W15, W18 | 대응 |

## 3. 수용 시험 추적표

| AT | 설계 위치 | 구체적 검토 | 설계 판정 / 실행 상태 |
|---|---|---|---|
| AT-01 | D2/D3 | W01의 1–7 → 2–8 → 1–7 및 moment 별 저장 | 대응 / 미실행 |
| AT-02 | D2/D5 | W02 실제 PTS 및 t0 필터 | 대응 / 미실행 |
| AT-03 | D3/D9 | W03 commit/outbox/restart 복원 | 대응 / 미실행 |
| AT-04 | D4/D6 | W04 늦은 작업, 실제 의존만 stale | 대응 / 미실행 |
| AT-05 | D3/D6/D8 | W06 복수 행동·mask·메모·완료 수 | 대응 / 미실행 |
| AT-06 | D7 | W09~W11 SAT/UNSAT·공허·3단계 경계·UNKNOWN/timeout | 대응 / 미실행 |
| AT-07 | D7/D8 | W08/W11 미지원/미승인/stale 차단 | 대응 / 미실행 |
| AT-08 | D8 | W12 pair 입력/목표 및 버전 | 대응 / 미실행 |
| AT-09 | D5/D8 | W02/W13 미래 관찰·split 겹침 | 대응 / 미실행 |
| AT-10 | D9 | W15 경로·HTML·auth·secret | 대응 / 미실행 |
| AT-11 | D4/D5/D8 | W18 실제 provider 두 시점 경로와 mock 구분 | 대응 / 실제 provider 선정 전 |
| AT-12 | D2/D5 | W01/W02 시작/끝/7미만·미래 방문 후 복귀 | 대응 / 미실행 |
| AT-13 | D6~D8 | W07/W08/W17 binding·빈 제안·renderer 단독 성공 | 대응 / 미실행 |
| AT-14 | D3/D4/D8 | W03/W05/W14 autosave·동시 수정·snapshot 경합 | 대응 / 미실행 |
| AT-15 | D3/D6/D7 | W06/W12/W16 결정적 CNL·파생문·별도 레이블 | 대응 / 미실행 |

## 4. 시나리오 검토

### W01. 모든 시점과 프레임 경계

10개 manifest에서 i=0은 1개, i=5는 6개, i=6은 1–7, i=7은 2–8,
이전은 1–7이다. i=9에서 다음은 비활성이다. N=3에서도 3개만 표시하며 복제하지 않는다.
각 i에 고유 moment가 있으므로 7개 묶음이 하나의 CoC가 되는 오류를 막는다. t0 변경과 확대를
분리하여 확대 복귀가 다른 저장 항목을 열지 않는다. 설계 식으로 요구 경계를 확인했다.

### W02. 미래 방문·캐시·PTS 누출

t=10을 본 뒤 t=4로 돌아와 CoC 생성한다. 서버는 t<=4 프레임만 재구성하고 t=10 job의
prompt/cache/관찰 요약을 재사용하지 않는다. source frame t=4.1을 넣으면 거부한다.
가변 FPS에도 decoder 실제 PTS를 기록하며 4번째 프레임을 4초로 취급하지 않는다.
원 CoC에 “뒤에서 곧 지나갔다” 같은 미래 관찰이 있으면 원본에 누출 표식을 남기고 승인본 수정
또는 표본 제외가 필요하다. 사람의 기억·텍스트 의미 누출 자동 검출에는 한계가 있어 D5 노출 이력과
causal-only 검토가 필요하다. 단순 timestamp 검사로 의미 누출까지 증명했다고 주장하지 않는다.

### W03. 저장 지연·탐색·재시작

A/r7 편집 후 B로 이동하고 A의 저장 ACK가 늦게 도착한다. 요청은 A와 mutation ID에 묶여
A/r8만 갱신하고 B에는 적용되지 않는다. ACK 전에 브라우저가 재로딩되면 outbox가 r7 기반
동일 key를 재전송한다. 서버는 이미 commit한 경우 동일 r8을 반환한다. 서버 재시작은 committed
DB refs를 복구한다. 저장 실패는 빨간 실패 상태이며 완료 수를 올리지 않는다. 브라우저 저장소
불가·디스크 부족은 성공으로 숨기지 않는다. 이 설계의 실제 crash 내구성은 구현 시험 대상이다.

### W04. 오래된 job·취소·정확한 무효화

CoC/r3를 입력으로 proposal job J를 시작한 뒤 CoC/r4를 사람이 저장한다. J 완료는 입력 digest
불일치로 STALE_RESULT이며 r4를 덮어쓰지 않는다. 계약 변경은 검사/CNL/결합을 stale로 만들지만
그 계약을 보지 않은 행동 레이블 내용을 자동 수정하지 않는다. 결합과의 일치 확인만 다시 한다.
취소 뒤 J의 이전 lease 결과도 채택되지 않는다. query 버전 변경은 CoC를 무효화하지 않는다.

### W05. 동시 편집·일괄 승인

두 창이 r8에서 편집하면 첫 PATCH가 r9, 두 번째는 409다. 두 번째 입력은 outbox/비교 화면에
보존하고 자동 덮어쓰기하지 않는다. A/B/C 일괄 승인의 검토 diff 이후 B가 수정되면 전체 batch를
409로 거부한다. 일부 시점만 조용히 승인하지 않는다. 승인은 서버 actor/time으로 기록하며
모델이 제시한 reviewer 이름·시각은 승인 신원이 아니다.

### W06. 행동 승인과 실제 완료 수

진입과 보류를 모두 APPROPRIATE로 사람이 승인할 수 있다. UNKNOWN은 mask, NOT_APPLICABLE은
선택 메모와 함께 별도 값이다. 계약이 둘을 허용해도 레이블은 미승인 상태를 유지한다.
한 시점 ENHANCED_READY, 한 시점 REVIEW_COMPLETE_HELD라면 검토 완료 2, 강화 적격 1이다.
단일 정답 강제나 초안 수를 완료 수로 세는 경로가 없다.

### W07. NOT_APPLICABLE의 오분류

모델이 빈 proposals를 반환한 경우 UNRESOLVED다. 출처 미확인·미지원·전부 거절도 동일하다.
사람이 규칙 후보와 근거를 보고 적용 제약 없음으로 승인해야 NOT_APPLICABLE이 된다.
이때 CoC/행동 승인·계보가 충족되면 baseline만 export한다. hazard=FALSE는 규칙 해제 상태일
수 있으므로 규칙 자체가 미적용이라는 뜻으로 바꾸지 않는다.

### W08. 미지원 행동과 렌더링 성공

“2초 후 가속” 제안은 Studio 진입 profile의 행동/시간 범위를 벗어나 UNSUPPORTED 초안이다.
DEFER_ENTRY로 임의 축약하지 않는다. 공용 renderer가 구조상 유효한 계약의 영어를 출력해도
source binding·승인·Q1–Q5가 없으면 verified export는 거부한다. null zone을 플랫폼 parser가
허용하더라도 Studio의 장면 진입 계약 승인 조건을 충족하지 않는다.

### W09. SAT와 장면 사실성

사용자가 ped=FALSE/valid, road=FALSE/valid를 승인하면 Q1 SAT, ENTER SAT, DEFER SAT가
기대된다. 실제 장면에서 사람이 잘못 읽었을 가능성은 SMT로 제거되지 않는다. 관찰 근거·사람
승인·claim scope를 남긴다. ped=TRUE로 바꾸면 Q1 SAT를 유지하고 ENTER UNSAT가 기대되는
성공 검사다. 서로 모순된 INITIAL 가정을 넣어 Q1 UNSAT가 되면 뒤 ENTER UNSAT를 성공으로
세지 않는다. 기대값은 실행 결과에 맞춰 수정할 수 없다.

### W10. 경계·공허성·초기 상태

동일 계약의 별도 가상 harness에서 0의 TRUE/valid, 1의 FALSE/valid, 2의 TRUE/valid를 준다.
전이 전·해제 시점·재활성 시점의 active 기대값은 TRUE/FALSE/TRUE이며 각 전제 SAT와
반대 상태 UNSAT를 함께 요구한다. 한 의무만 해제되고 다른 의무가 남으면 ENTER UNSAT다.
UNKNOWN/CONFLICT/무효는 prior를 유지하고 clear가 아니다. 미관찰 prior는 양 값 가능성을
검사하며 witness를 초기 관찰로 채우지 않는다. 실제 초 단위 threshold는 현재 profile 밖이며
“시간 경계 검증 완료”로 보고하지 않는다.

### W11. 두 종류 UNKNOWN과 검사 실패

관찰 truth=UNKNOWN은 review_required와 DEFER 정책을 만들며 정책 질의 자체는 PASS일 수 있다.
그러나 해당 시점은 현재 강화 학습 export에서 HELD다. solver status=UNKNOWN은 질의 미판정으로
검사 실패다. 시간 상한 도달은 TIMED_OUT, 의존 모듈 부재는 ERROR, 취소는 CANCELLED이며
어느 것도 PASS나 NOT_APPLICABLE로 바꾸지 않는다. 필수 질의가 빈 목록이어도 통과할 수 없다.

### W12. CoC·정답 입력 누출과 pair

승인 CoC가 “진입 보류가 정답”을 포함할 때 단순히 action_label 필드만 inputs에서 빼는 것으로
충분하지 않다. ACTION_WITH_CONTEXT에는 검토된 context projection을 쓰고 의미 분리가
어렵다면 COC_TARGET을 사용한다. 두 모드의 baseline/강화 pair는 같은 frame/question/action
approval/split을 사용한다. provenance에는 원본·결합본·레이블이 있지만 학습 loader 입력은
allowlist로 분리한다. 자유 텍스트 누출 검토의 잔여 한계는 W02와 같다.

### W13. 원본 계보와 split 겹침

영상 A를 train에 배정하고 같은 해시 재업로드 A2와 A의 일부 클립 B를 test로 요청한다.
lineage 연결 그룹이 같아 거부한다. 재추출과 baseline/강화본도 같은 split이다. 재인코딩으로
해시가 달라진 C는 계보 확인 없이 독립 영상으로 처리하지 않는다. train/test 그룹이 뒤늦게
같은 주행으로 확인되면 새 export 차단 및 이전 export 철회 기록을 만들며 원 파일은 수정하지 않는다.

### W14. export snapshot 경합

r12의 완전한 승인 집합을 트랜잭션에서 고정한 뒤 사람이 r13을 편집한다. export는 r12의
CoC/검사/CNL/행동을 일관되게 사용하고 r13 일부를 읽지 않는다. snapshot 생성 전에 r13이
commit됐다면 예상 r12 요청을 409로 거부한다. 작업 중 source 권한 철회나 lineage 충돌이
발견되면 게시를 차단한다. 단순 수정과 안전/권한 무효화를 구분하여 “항상 최신 head” 요구와
불변 snapshot 재현성의 충돌을 제거했다.

### W15. 업로드·경로·HTML·자원

`../` filename, 임의 절대 경로 asset ref, encoded traversal, symlink escape는 ID/root
해석과 decode 후 검증에서 거부해야 한다. `<script>` CoC는 문자로 표시한다. 미인증 쓰기·CSRF
불일치·외부 Origin은 거부하며 비밀정보는 export allowlist에 없다. 1 GiB 초과는 413,
손상/미지원 codec은 422, decode/SMT/VLM 시간 초과는 실패 상태다. 이 항목은 보안 구현을
실행한 결과가 아니라 설계 경로 점검이며 공격 입력 회귀 시험이 필요하다.

### W16. 결정적 CNL과 수동 파생문

같은 contract/binding/renderer/language version으로 다시 생성하면 동일 text/hash여야 한다.
한글 수동 편집은 DERIVED_TEXT 새 버전이며 원 생성문을 덮어쓰지 않는다. 의미 승인만으로
기존 SMT 결과를 파생문 보증으로 옮기지 않고 verified export는 결정적 생성문을 요구한다.
검증 CNL을 바꾸려면 계약 수정→재검사→재생성→재승인한다. CoC/행동 충돌은 재검토한다.

### W17. source·target·zone 수정

출처 ID만 있고 원문 조항·버전이 없는 제안은 승인되지 않는다. 정책은 정책으로 승인하고
법규로 이름을 바꾸지 않는다. zone 삭제나 target 재식별은 새 binding revision이며 의존
proposal/contract/check/CNL/결합은 stale이다. 과거 좌표는 승인 이력에 남지만 현재 도형은
완전히 제거한다. null target은 명시적 문맥 의무와 식별 실패를 구분한다.

### W18. 실제 provider 경로와 재시도

권한 있는 영상의 두 시점을 선택하여 실제 provider CoC → 사람 승인 → 출처 기반 제안 →
binding/계약 승인 → 검사/CNL → 행동·결합 승인 → snapshot export가 AT-11의 경로다.
provider 미설정은 503, mock은 MOCK 표식과 학습 부적격이다. 모델 호출 중 재시작되어 전송
결과가 불명확하면 OUTCOME_UNKNOWN이며 자동 중복 호출하지 않는다. quota/auth 오류에도
모델·계정을 전환하지 않는다. 이 경로는 아직 실행하지 않았으며 실연동 완료를 주장하지 않는다.

## 5. 설계 검토에서 해결한 항목

아래 “해결”은 최종 설계 문구에 반영했다는 뜻이며 코드 수정·실행 검증을 뜻하지 않는다.

| ID | 확인한 결함/누락 가능성 | 반영한 해결 |
|---|---|---|
| F01 | timestamp만 검사하면 미래 대화/cache/요약이 역류 | D5 stateless 요청, dependency 최대 관찰시각, cache key, 사람 노출 기록 |
| F02 | action_label 필드 분리만으로 CoC 속 정답 누출을 막지 못함 | D8 context projection 검토 또는 COC_TARGET |
| F03 | 포털 revision 저장을 그대로 Studio autosave로 오인 | D1/D3 별도 DB·CAS·outbox·idempotency |
| F04 | parser/CNL 성공 또는 base SAT 하나를 검증 완료로 오인 | D7 승인 binding·Q1–Q5·전제 SAT 및 현재 digest 필수 |
| F05 | solver witness의 자유 미래/초기 값이 관찰로 승격 | D7 미관찰 표시·양 prior 검사·가상 harness 분리 |
| F06 | 관찰 UNKNOWN과 solver UNKNOWN을 같은 상태로 취급 | D7/D8 정책 PASS와 export HELD, solver UNKNOWN은 미통과 |
| F07 | 빈 제안·거절·미지원을 NOT_APPLICABLE로 export | D6 명시 적용성 승인과 UNRESOLVED 분리 |
| F08 | 늦은 autosave/job·batch 승인·export가 버전을 혼합 | D3/D4 CAS+lease+원자 batch, D8 고정 snapshot |
| F09 | 파일 해시만으로 재인코딩/파생 영상 split 독립성을 오판 | D8 계보 연결 그룹·불명 보류·병합 충돌/철회 |
| F10 | 공용 solver에 timeout이 이미 있다고 가정 | D7/D9 작업 프로세스 시간/메모리 제한을 신규 경계로 명시 |
| F11 | 기존 scene18/한글 renderer가 범용 학습 승인까지 지원한다고 오인 | D10 지원 술어·pin·export false와 신규 Studio 업무 분리 |
| F12 | 모든 head 변경을 export 취소하면 snapshot 의미가 불명확 | D8 일반 편집은 고정 버전 유지, 권한/계보 무효화는 게시 차단 |

## 6. 미해결·후속 구현 검증

| ID | 열린 항목 | 영향 / 닫을 조건 |
|---|---|---|
| O01 | 실제 provider/model·라이선스·전송 권한·예산/자원 미선정 | 실제 생성·AT-11 보류. 배포 설정 승인과 두 시점 실제 연동 시험 필요 |
| O02 | 한글 Studio 템플릿 및 일반 영상 binding UI 미구현 | 지원 두 술어의 mapping·질의 conformance·사람 검토 흐름 시험 필요 |
| O03 | DB/CAS/outbox/job/파일 commit 경계 미구현 | 재시작·취소·중복·동시 승인·export 경합 AT 실행 필요 |
| O04 | decoder 환경·자원 기본값의 실측 적합성 미확인 | 허용 형식·PTS·손상/크기·timeout 시험 및 자원 한도 확정 필요 |
| O05 | 자유 문장과 사람 기억의 미래/정답 누출 자동 증명 불가 | 노출 기록·causal/context 사람 검토, 불명 표본 보류 유지 |
| O06 | 백업·보존/이력 파기 운영 정책 미확정 | DB/파일 동시 복원 검증 및 restricted 운영 정책 필요 |
| O07 | 사용자 설계 승인 미기록 | 본 보고서는 요구사항 승인이나 구현 권한을 확장하지 않음 |

O01~O06은 해당 기능의 구현·배포 확인 사항이다. 새 조사나 기존 논문 gate로 추가하지 않는다.
설계 검토상 알려진 미반영 요구는 없지만 모든 AT는 구현 이후 실제 시험해야 한다.

## 7. 저장소 검사

수정 전 baseline에서 명명 위반 5건, 관련 구조 unittest 22개 중 20개 통과/2개 실패를 확인했다.
실패는 이번 Studio 설계 파일과 무관하며 수정하지 않는다.

| 기존 실패 | 내용 |
|---|---|
| 명명 1 | `projects/P003_ophthalmic_foundation_model_validation` 디렉터리 이름 |
| 명명 2–3 | `guardsynth-m16-scene-acquisition-001/m16-geometry-curator-submission-2026-09-06-v1/`의 `m16_geometry_candidate_review (1).csv` 및 `.json` |
| 명명 4 | `guardsynth-paper1-reviewed-contract-001/scene18-independent-submission-2026-09-08-001/scene18_scene_cnl_review (1).json` |
| 명명 5 | 미등록 root 파일 `portal_exec.md` |
| 구조 1 | `test_maintained_files_follow_naming_codex`: 위 5건 |
| 구조 2 | `test_registry_exactly_matches_project_directories`: 미등록 `P003_ophthalmic_foundation_model_validation` |

최종 문서에 대해 다음 검사를 실행했다. 새 명명/구조 실패는 확인되지 않았다.

- `python3 -B cli/checks/file_naming.py`: 종료 코드 1, baseline과 동일한 기존 5건.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.structure.test_project_layout tests.structure.test_checkpoint_naming_exception`:
  22개 중 20개 통과, baseline과 동일한 2개 실패.
- 쓰기 없는 Python 링크 검사: Studio 문서 3개와 README의 로컬 링크 45개 정상,
  `broken_markdown_links`의 저장소 canonical entry 링크 오류 0개. PROJECT.yaml의 세 문서 연결 정상.
- 추적표 검사: GS 행 6/6, AT 행 15/15, 시나리오 18/18 존재, 중복 행 없음.
  승인 원문·승인 시각 미기록 메타데이터 및 공백 검사 통과.
- 요구사항 수정 범위 수동 검토: 승인/후속 문서 메타데이터만 변경했고 본문 기능·AT·단계 의미는 보존했다.
  README/PROJECT.yaml은 Studio 항목만 갱신했다. 부모 상태/계획/논문·코드·학습 산출물은 편집하지 않았다.
