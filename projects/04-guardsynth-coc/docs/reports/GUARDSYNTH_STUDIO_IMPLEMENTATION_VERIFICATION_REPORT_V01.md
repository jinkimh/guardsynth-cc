# GuardSynth Studio 구현 검증 보고서 v0.1

## 추가 실행: nuScenes 영상·CAN 예제 (2026-09-30)

사용자 요청 “그 데이터를 예제로 올려서 실제 생성해보고 coc를 만들어보자..”에 따라
공식 nuScenes mini `scene-0061`의 전방 영상과 원본 CAN vehicle_monitor로 실제 CoC 1건을 생성했다.
이는 앞서 영상만 사용하는 요구의 후속 예제 확장이며 기존 연구·논문·학습 범위는 변경하지 않는다.
[입력·출처·결과와 검토](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-studio-001/nuscenes-can-demo-2026-09-30-001/REPORT_KO.md)를 참조한다.

- 카메라 keyframe39개의 원본 시각을 MP4 PTS로 보존, 26번째 시점12.55초에서 과거/현재7장 사용.
- 속도·브레이크 압력·스로틀·조향의 원단위를 유지하고 영상 시각 이전 마지막 CAN만 선택.
  최대600ms를 넘으면 미확인, 미래 보간/기존 설명·행동 정답 입력 없음.
- 영상 SHA·CAN SHA·clock origin·전송 승인을 확인하는 불변 운영자 attachment를 추가.
  주석 작성 이후 추가/교체 거부, job snapshot과 provider 재검사, DRAFT 입력 provenance 보존.
- `studio-state-coc-v1`으로 실제 gpt-5.4 1회 성공. 공사로 좁아진 통로·선행차·측정 속도를
  저속 유지/조건부 감속 이유에 연결했다. 실제 운전자 원인·실측 거리·안전 보장으로 승인하지 않음.
- mock 기반 새3개와 기존36개, 총39개 통과. 실제 입력은 source manifest와 별도 보존.
- 기존 공유한도5/6→6/6, 자동 재시도/증액 없음. 새 초안은 미승인·학습 부적격
  `VEHICLE_STATE_DEMO_ONLY`; AT-11 전체 사람승인/EBLC/export 수용 완료가 아님.
- 기존 Studio만 재시작, localhost45453 HTTP200 및 재시작 전후 DB snapshot 보존 확인.
  재로그인 후 새 nuScenes 영상→26번째 시점 선택. 일반 CAN 업로드 UI는 아직 없음.
- naming 기존5건, 구조22건 중 기존3건 실패(`.aws` root, P003 프로젝트 등록, naming).
  신규 정책 위반 없음. 기존 frozen 실험·원답·포털8766·타 앱8877·논문은 변경하지 않음.

- project_id: `guardsynth-coc`
- subproject_id: `guardsynth-studio`
- 기준: [승인 요구사항](../requirements/GUARDSYNTH_STUDIO_REQUIREMENTS_V01.md), [승인 설계](../designs/GUARDSYNTH_STUDIO_DESIGN_V01.md)
- 승인: 사용자 원문 “설계 명세 대로 구축을 진행해...”, 2026-09-29, 정확 시각 미기록.
- provider 후속 승인 원문: “OpenAI API 방식을 사용하자.” 현재 대화의 사용자 승인, 정확 시각 미기록. 연결 구현을 승인한 것이며 모델·키·예산·실제 영상 전송 승인은 미설정이다.
- 현재 상태 (2026-09-30): 로컬 구현·회귀 시험 후 실제 API 연결 및 공개 영상 두 시점의 CoC 초안 생성까지 확인(7절). 실제 AT-11 전체 수용은 사람 검토 및 후속 단계 대기. 아래 초기/후속 기록은 당시 상태를 보존한다.
- 실행 안내: [앱 README](../../../../apps/guardsynth_studio/README.md)

## 1. 구현 범위

독립 앱 `apps/guardsynth_studio/`를 `guardsynth-coc` 소유로 등록했다. SQLite schema v1,
불변 revision/승인 이력, CAS·idempotency, 인증/CSRF, 로컬 MP4/H.264 업로드, PyAV CPU
PTS 추출, 시점별 최대 7 causal frame UI, 확대, 점/폴리곤·삭제, outbox 자동저장을 구현했다.
실제 포털 서비스/DB는 사용하지 않는다.

단일 영속 작업 큐, 취소 generation·stale 결과·재시도/재시작 상태, CoC/별도 행동/출처/binding/
제약/계약 승인, 의존 결과 무효화, 적용성 검토, 원자적 일괄 승인 및 검토완료를 연결했다.
Project 04의 `studio_contract.py`는 공용 EBLC 플랫폼을 호출하여 Q1–Q5 및 결정적 한글/영어
CNL을 제공한다. scene18 연결이나 기존 한글 연구 산출물을 범용 extractor로 바꾸지 않았다.

export는 불변 snapshot의 JSONL 및 RESULT/RUN_MANIFEST를 게시한다. baseline/강화 pair,
입력/목표/provenance 분리, 학습 부적격 제외 사유, 원본/주행 그룹 split, 출처·권한·계보
무효화 후 다운로드 차단을 구현했다. 미지원·UNKNOWN·빈 proposal을 학습 승인으로 승격하지 않는다.

생성 run/DB/영상은 Studio restricted namespace, 시험 자료는 TemporaryDirectory다.
CPU 하위 프로세스에서 decoder/SMT 시간·메모리를 제한하며 외부 API/GPU/학습을 호출하지 않았다.
운영 auth 비밀 생성이나 상시 서버 기동은 수행하지 않았다. 테스트 서버만 자동 할당 loopback
포트에서 실행·종료했고 기존 8766 서비스는 변경하지 않았다.

## 2. GS 요구 추적과 실제 검증

시험 구현: [workflow 시험](../../../../apps/guardsynth_studio/tests/test_workflows.py),
[HTTP/브라우저 시험](../../../../apps/guardsynth_studio/tests/test_http_browser.py).

| 요구 | 구현 | 실제 검증과 한계 |
|---|---|---|
| GS-01 | media/service, 프레임·도형 UI | 실제 합성 H.264 decode, 원 PTS, 시작/끝, 재업로드 계보, 손상 파일 실패, 미래 binding 차단, 도형 삭제. 최대 용량의 운영 부하 시험은 아님 |
| GS-02 | component/approval/audit 및 별도 action | 실제 사람 검토 UI 경로, 복수 레이블, 원자 batch/409, 모델 원출력·MOCK 표시. 실제 VLM 호출은 미실행 |
| GS-03 | proposal schema 및 source/binding 승인 | 출처 원문 hash, rule/predicate 매핑, null 대상 역할·영역, 빈 목록/미지원/미승인 차단 |
| GS-04 | Project 04 studio_contract + 기존 EBLC | 실제 Z3 Q1–Q5, 공허 전제·금지행동 UNSAT·UNKNOWN 유지·지원 범위, 실제 child deadline. solver UNKNOWN 분기는 주입 시험 |
| GS-05 | CNL/combined, SQLite/outbox/UI | 실제 결정적 렌더링, 수동 파생문 분리, 브라우저 저장/확대/재로딩, HTTP 서버 재시작, 하위 stale 전파 |
| GS-06 | snapshot export·lineage | 실제 JSONL 파일/행 검토, 공통 pair, 입력 정답 분리, context 미검토 제외, snapshot 경합·권한/계보 무효화, mock/수동자료 부적격 |

## 3. AT 실제 시험표

PASS는 아래 특정 합성/로컬 사례에서의 동작 결과다. 운영 규모·실제 영상 의미 정확성·실제 모델
수용까지 입증한다는 뜻이 아니다. 테스트에서 REAL provenance를 주입하는 export fixture는
조건 분기 검증용이며 실제 provider 수행으로 계산하지 않는다.

| AT | 실행 근거 | 결과 |
|---|---|---|
| AT-01 | `test_navigation_cas_idempotency_restart`, 브라우저 `test_browser_navigation_zoom_outbox_reload_and_xss` | PASS: 1–7→2–8→1–7, 답변 유지 |
| AT-02 | `test_real_cpu_decode_pts_and_duplicate_lineage`, `test_future_binding_and_generated_provenance_rejected`, `test_model_input_separation_and_invalid_output_preserved` | PASS: 실제 PTS·causal 입력/근거 |
| AT-03 | 브라우저 outbox 재로딩, `test_http_server_restart_preserves_committed_edit` | PASS: 확대 복귀·미확인 저장 재전송·서버 재시작 복원 |
| AT-04 | `test_stale_job_cancel_recovery_and_timeout`, `test_geometry_delete_and_dependency_invalidation` | PASS: 오래된 결과 미적용, 관련 결과만 stale |
| AT-05 | `test_context_manual_cnl_and_completed_counts`, `test_empty_not_applicable_and_separate_action` | PASS: 복수/미확인/미적용·독립 레이블·완료/적격 수 분리 |
| AT-06 | `test_q1_q5_cnl_determinism_and_unknown`, `test_nonvacuity_unsupported_and_solver_unknown`, `test_simultaneous_cas_and_actual_child_timeout` | PASS: 추상 3단계 경계·공허성·SMT; 실제 시간 임계 profile은 미지원 |
| AT-07 | eligibility/export 및 수동/mock 경로 시험 | PASS: 미지원·미승인·stale·수동/mock 자료 학습 부적격 |
| AT-08 | `test_export_snapshot_pair_and_split` | PASS: 공통 frame/question/action/split, 원본·강화본 보존 |
| AT-09 | 미래 binding/provider 입력, 계보 재업로드/병합 시험 | PASS: 구조적 누출 차단. 자유 문장·사람 기억의 누출은 사람 검토 경계 |
| AT-10 | `test_auth_csrf_path_disabled_provider_and_if_match`, 브라우저 XSS, secret payload 차단 | PASS: 인증·CSRF·Origin·경로·HTML·비밀 필드 |
| AT-11 | `test_browser_human_review_to_smt_cnl_draft_export`는 로컬 사람 작성 경로만 실행; Responses 전송은 모의 시험 | 미실행: OpenAI 방식 선택됨, 실제 모델·키·영상 전송/비용 설정 및 두 시점 수용 필요 |
| AT-12 | 실제 브라우저/manifest 경계 및 stateless provider 입력 시험 | PASS: 모든 시점·7미만·끝·미래 프레임 배제 |
| AT-13 | 빈 proposal/출처 hash/binding/SMT gate 시험 | PASS: NOT_APPLICABLE 자동 승격 및 renderer 단독 검증 승격 없음 |
| AT-14 | 동시 thread CAS, 늦은 결과, 브라우저 outbox 및 snapshot 경합 | PASS: 시점/버전 혼합·조용한 덮어쓰기 방지 |
| AT-15 | 결정적 CNL·derived·별도 action 및 브라우저 승인 경로 | PASS: 재현성·승인 분리·원문 보존 |

## 4. 초기 로컬 구현 실행 결과

기존 등록 `runtime/alpamayo/ar1_venv/bin/python`의 PyAV/Pillow/Z3를 사용했다. 패키지 설치나
환경 변경은 없었다. Chromium은 기존 캐시 binary를 사용했으며 Playwright 설치 없이 로컬 CDP로
시험했다. 소켓 제한 sandbox 밖 실행 권한으로 임시 loopback HTTP/브라우저 시험을 수행했다.

- 전체 앱 시험: `PYTHONDONTWRITEBYTECODE=1 runtime/alpamayo/ar1_venv/bin/python -B -m unittest discover -s apps/guardsynth_studio/tests -t . -v` — 20개 통과, skip 없음.
- JavaScript 구문: `node --check apps/guardsynth_studio/static/app.js` 통과. Python AST 파싱 통과.
- 링크/추적: Studio·프로젝트 진입 문서 로컬 링크 56개 정상, canonical 진입 링크 오류 0개,
  GS 6행/AT 15행 누락·중복 없음, registry owner 정상.
- 명명 검사: 기존 5건만 실패. `projects/P003_ophthalmic_foundation_model_validation`,
  `m16_geometry_candidate_review (1).csv/.json`, `scene18_scene_cnl_review (1).json`, `portal_exec.md`.
- 관련 구조 unittest: 22개 중 20개 통과. 기존 naming assertion 및 미등록 P003 프로젝트 assertion
  2건만 실패; 신규 Studio 소유 검사는 통과했다.

초기 구조 검사에서 앱을 연구포털 하나로 고정한 assertion이 신규 등록과 충돌하여, 해당
소유 검사에 Studio 등록·경로·owner·README 확인을 추가했다. 이외 기존 구조 문제는 수정하지 않았다.
최종 브라우저 회귀 중 초기 `about:blank` 준비 상태를 Studio 준비로 오인한 시험 도구 경합을
수정했다. 실제 Studio URL과 문서 준비를 함께 기다리도록 변경한 뒤 전체 20개 시험을 재통과했다.

## 5. 남은 선택과 운영 확인

- OpenAI Responses adapter는 후속 구현·모의 검증했다(6절). 실제 모델/키·전송 승인·예산은
  미설정이므로 기본 DISABLED/503이다. 테스트 MOCK은 운영 CLI에서 켤 수 없다.
  설정 후에도 AT-11 두 시점 실제 수용은 별도로 수행해야 한다.
- 운영 auth는 실행자가 `--init-auth`로 직접 설정한다. 기본 포트 0으로 사용 가능한 loopback
  포트를 할당하며 시작 성공 후 출력 주소를 사용한다. 8766/8877은 CLI에서 거부한다.
  상시 서비스를 시작하거나 현재 접속 주소를 확인한 것은 아니다.
- 테스트는 작은 합성 영상과 명시적 failure 주입을 포함한다. 1 GiB/30분 영상, 실제 저장장치
  고장, 백업 복구의 운영 부하/재해복구 시험은 별도 운영 환경 확인 대상이다.
- 업로드 파서는 제한된 단일 동시 요청을 메모리에서 처리한다. 최대 크기의 실제 메모리 사용은
  운영 자원 선택 시 확인해야 한다. 취소는 결과 채택을 막고 CPU task는 제한시간 내 종료한다.
- 화면상 도형 삭제는 현재 좌표 제거다. 승인된 과거 revision/완료 export를 물리적으로 파기하지
  않는다. restricted 보존/백업/파기 정책은 운영자가 확정해야 한다.
- 자유 문장·사람이 이미 본 미래 정보의 의미 누출은 완전 자동 검증할 수 없다. causal-only 확인,
  검토 노출 이력, context 별도 승인과 보류 정책을 유지한다. 독립 평가 정답 export는 지원하지 않는다.

학습/실험/논문/부모 STATUS·milestone·secondary metric 작업은 편집하지 않았다. 커밋·푸시,
기존 파일 삭제, 계정/모델 변경, subagent 생성은 수행하지 않았다.

## 6. OpenAI Responses 연결 후속 검증 (2026-09-29)

범위는 앱 provider/service/job/task 연결, 실행 포트 안내, 해당 시험/README와 본 보고서다.
승인 요구·EBLC·행동 레이블·학습 적격 기준을 축소하지 않았다. 외부 API·실제 키·사용자 영상은
사용하지 않았으며 모의 전송에만 합성 프레임과 시험용 비밀 문자열을 사용했다.
공식 [이미지 입력](https://developers.openai.com/api/docs/guides/images-vision)과
[구조화 출력](https://developers.openai.com/api/docs/guides/structured-outputs)을 대조했다.

- 고정 Responses endpoint, base64 causal 이미지 1–7개, `text.format` strict schema,
  `store=false`, tools 없음, 대화 이력 없음, retry/fallback 0을 구현했다. 무보존 보장은 하지 않는다.
- 영상 원본 해시별 전송 허용 목록·영상 권한·명시 모델·호출/토큰/deadline 설정을 요구한다.
  호출 전 SQLite 예산 예약, 설정 signature/영상 revision 바인딩, 전송 직전 권한/현재 revision
  재검사, 이미지 무결성·크기 검사를 추가했다. 실패/결과 불명도 예산을 소비하며 재시작으로 초기화되지 않는다.
- CoC와 제약의 task/data를 분리하고 제약만 승인 CoC·출처를 받는다. 행동 레이블/미래/세션 이력은 제외한다.
  기존 proposal 스키마의 닫힌 출력 부분집합과 기존 로컬 검증을 함께 사용한다. 모델은 사람 승인 상태를 쓸 수 없다.
- auth/429/timeout/refusal/incomplete/JSON/schema 실패를 보존한다. HTTP 원문과 비밀 반향은
  저장하지 않는다. 수동 재시도 뒤 이전 오류 감사 기록도 남으며 늦은/취소된 응답은 head에 적용되지 않는다.
- 주입 전송은 MOCK으로 고정하여 실제 생성/학습 적격으로 위장하지 않는다. 실제 모델의 정확성,
  schema 수용 여부·지연·비용은 이번 모의 검증으로 입증하지 않는다.

추가 시험: [test_openai_provider.py](../../../../apps/guardsynth_studio/tests/test_openai_provider.py).
요청 형식·모델 고정·stateless·출처/정답 분리, 미래 방문 후 과거 입력, 비활성 설정, HTTP 상태/오류,
한도/재시작·설정 변경, stale/cancel, 비밀값 및 JSON escape 반향의 DB/export 차단, 수동 재시도
오류 이력을 시험했다. 연결 전 실패하는 시험을 확인한 뒤 구현했다. 자체 검토에서 발견한
인코딩 비밀 반향과 재시도 시 오류 이력 소실은 회귀 시험과 함께 수정했다. 독립 코드 검토를 수행한 것은 아니다.

실제 AT-11은 **미실행**이다. 사용자가 모델·서버 키·호출/비용 한도·영상별 전송 범위를 확정해야
실제 두 시점 수용을 진행할 수 있다. 인증 초기화/자동 할당 loopback 주소/비활성 설정 예제는
[README](../../../../apps/guardsynth_studio/README.md)에 있다. 기존 8877 서비스는 건드리지 않았다.

최종 후속 검사 결과:

- 전체 앱 unittest **33개 통과, skip 0**: 기존 20개 + OpenAI 모의/경계 13개, 16.377초.
  명령은 4절과 동일하며 외부 API 호출은 없다.
- JavaScript 구문 검사 통과, 앱 Python AST 16파일 통과, 수정 문서 2개의 로컬 링크 9개 정상.
- `python3 cli/checks/file_naming.py`: 종료 코드 1, 기존 명명 위반 5건 동일. 수정하지 않음.
- 관련 구조 unittest: 22개 중 19개 통과/3개 실패. 알려진 naming/P003 두 assertion 외에
  `test_every_root_namespace_is_registered_or_tool_owned`가 기존 환경의 `.aws` 디렉터리
  미등록을 추가 보고했다. 이 작업에서 `.aws`를 생성·열람·수정하지 않았으며 범위 밖 실패로 남겼다.
  초기 기록의 구조 2실패를 현재 결과로 재사용하지 않는다.
- 제한 경로 `git diff --check` 통과. Studio 파일들이 기존부터 untracked이므로 이 명령만으로
  변경 비교가 충분하다고 간주하지 않고 연결부와 테스트를 직접 재검토했다.

서버 키를 확인하거나 출력하지 않았고 운영 비밀/설정/run을 만들지 않았다. 임시 시험 서버 외에
상시 실행 서버는 없다. 인증 오류는 이번 작업 도구 실행에서 재발하지 않았다.

## 7. 실제 API 연결 및 공개 영상 데모 (2026-09-30)

사용자가 저장된 키 확인·사용을 승인하고, 첫 시험 영상은 프로젝트 자료 또는 공개 데이터에서
선택하도록 요청했다. 현재 실행 환경의 `OPENAI_API_KEY`로 공식 모델 목록 조회 HTTP 200을
확인했다. Codex 표준 로그인 파일에는 ChatGPT 인증만 있었으며, 거기서 API 키를 추출하거나
로그인 토큰을 대체 키로 쓰지 않았다. 키 값·일부 문자열·해시는 출력하지 않았다.

- [합성 영상 연결 시험](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-studio-001/api-smoke-2026-09-30-001/RESULT.json): 기존 합성 영상 도우미와 실제 업로드·추출·작업자·Responses 경로 사용. `gpt-5.4`, 7프레임, 실제 1회 호출, CoC 구조화 응답 성공. 입력 873/출력 534토큰. 실제 주행 의미 정확성 검증은 아니다.
- [공개 주행 영상 데모](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-studio-001/public-video-demo-2026-09-30-001/REPORT_KO.md): CC0 영상 첫 12초, 13개 시점 추출. 0-based ordinal 6·12(화면 7·13번), 각각 최대 7개 causal frame으로 실제 CoC 초안 생성 성공. 두 호출 합계 입력 8,484/출력 1,317토큰.
- 공개 영상 출처는 L. Shyamal의 [Bangalore 20220814 154815](https://commons.wikimedia.org/wiki/File:Bangalore_20220814_154815.webm), CC0-1.0이다. 내려받은 버전·해시·변환·구간은 RUN_MANIFEST에 기록했다. 프로젝트 내 NVIDIA 제한 영상은 외부 전송하지 않았다.
- 별도 Studio 서버를 loopback 자동 할당 포트에서 시작했다. 실제 `/` HTTP 200, 로그인 HTTP 200, 인증 후 REAL provider·모델·영상 1건 조회를 확인했다. 기존 8766/8877 서비스는 변경하지 않았다.
- API 키는 상속 환경변수에만 유지한다. 생성한 두 run의 파일/DB에서 실제 키의 바이트 일치가 없음을 검사했다. 별도 Studio 로그인은 무작위 비밀번호의 hash로 구성하고, 사용자 전달용 비밀번호 파일은 `/tmp`에 0600 권한으로 두었다. 비밀번호/API 키는 이 보고서에 기록하지 않는다.
- 실제 주행 영상 호출 상한 2회는 소진되었다. 무인 추가 호출은 없으며, 모델 생성 성공을 사람 승인으로 승격하지 않았다. 승인 0, 학습 적격 0. 이 데모를 논문 성능 근거로 사용하지 않는다.

따라서 **API·이미지 입력·스키마 응답·서버 접근은 실제 확인**했지만, 승인 CoC/출처/대상 연결을
전제로 하는 제약 생성과 사람 승인 → EBLC → CNL → export의 실제 AT-11은 아직 미완료다.
다음 단계는 화면 7·13번 CoC 초안의 사람 검토이며, 이후 별도 호출 한도 내 후속 생성이 필요하다.
본 절은 기존 33개 시험을 다시 실행했다는 기록이 아니다. 이번에는 운영 경로의 실제 smoke와
HTTP 인증 확인을 추가했다. 명명 검사 결과는 기존 5건만 남았다.

## 8. 사용 매뉴얼·편집 안내 구현 및 반영 (2026-09-30)

인계된 bounded 설계의 사용자 승인 “네” 및 “tmux 내에서 진행하고..다시 논문에 대해 논의하자”를
근거로 구현했다. 재승인·중복 설계 문서를 만들지 않았다. 앱의 정적 화면·GET 매뉴얼 경로·시험과
README/본 절만 수정했으며 7절의 실제 API 증거와 원 run 기록은 변경하지 않았다.

- 상단 작업 화면/사용 매뉴얼 메뉴, 한국어 전용 매뉴얼 16개 항목, 편집 영역별 요약·펼침 예시·
  대응 anchor 링크를 추가했다. 매뉴얼은 새 탭/noopener로 열리고 입력·선택 시점을 유지한다.
  CoC/행동/관찰의 동적 입력에 보이는 설명과 aria-describedby를 연결했다.
- 실제 저장 동작을 대조하여 출처·관찰 결합·적용성도 자동저장됨을 설명했다. 기록 버튼과 승인,
  검토완료와 학습적격, 미지원 행동 키(해당 없음 포함), 인과성·가정·정답 누출, 대상/진입 영역,
  외부 출처 추가 필드, 수동 두-조건 템플릿, Q1–Q5, CNL·context·split·계보·작업 오류를 구분했다.
  예시는 입력값으로 채우지 않으며 저장·승인·schema·eligibility·호출 정책을 변경하지 않았다.
- 일반 안내만 `/manual.html`의 좁은 GET 경로로 공개했다. 데이터/API 인증과 CSP는 유지한다.
  새 라이브러리·폰트·인라인 스크립트는 없다. 이미지 공간을 유지하고 매뉴얼은 반응형 본문과 표를 사용한다.

검증: 인계 시험의 401 및 누락 링크 RED를 재확인한 뒤 구현했다. 새 탭 시험은 Chromium에서
스크립트 click()이 사용자 동작으로 인정되지 않아 차단되는 것을 재현했다. 실제 CDP 마우스 클릭과
새 탭 탐색 완료 대기로 수정했고 새 탭·기존 입력·시점·저장·무승인·job 미생성 assertions는 유지했다.

- 전체 앱 unittest **35개 통과, skip 0**, 18.506초: 기존 33개 및 새 매뉴얼 HTTP/브라우저 2개.
- JavaScript 구문 검사 통과. 매뉴얼 16개 고유 anchor 및 UI 안내 anchor 링크 17개 정상.
- `python3 cli/checks/file_naming.py`: 기존 5개 위반 동일. 관련 구조 22개 중 19개 통과/3개 실패:
  기존 naming, P003 미등록, `.aws` root 미등록. 이 작업의 신규 실패는 없으며 범위 밖 항목은 수정하지 않았다.

운영 반영: 권한 있는 실행 환경에서 기존 PID 1107616의 실행 파일·cwd·Studio 모듈·지정 run과
상속 API 키의 존재만 확인했다. 키 값이나 타 프로세스 환경, 사용자 비밀번호 전달 파일은 읽지 않았다.
QUEUED/RUNNING job이 없고 REAL 설정·한도 2회임을 확인한 후 해당 서버만 재시작했다.
새 PID는 **1217816**, 주소는 동일한 **http://127.0.0.1:45453/** 이다.
작업 화면/매뉴얼 HTTP 200 및 서버 파일과 응답 일치, CSP, 미인증 영상 API 401을 확인했다.
시작 시 REAL 표시를 확인했으며 운영 비밀번호를 사용한 재로그인 시험은 수행하지 않았다.

재시작 전후 DB 전체 논리 snapshot(수정/답변/승인/job/호출 metadata 포함), auth/provider 설정 및
기존 RESULT/RUN_MANIFEST/REPORT가 동일함을 확인했다. 호출 수는 2→2이며 새 API 호출은 없다.
로그인 세션은 초기화되어 사용자 재로그인이 필요하다. 8766/8877·논문·학습·다른 프로젝트는
수정하거나 중단하지 않았다. 실제 AT-11의 나머지 사람 승인·제약·검증 수용 상태는 7절 그대로다.

## 9. CoC 프롬프트 역할 분리 (2026-09-30)

사용자가 CoC 본문이 관찰 설명 대신 `pedestrian_conflict`/`main_road_yield_required`와
`ENTER_ZONE`/`DEFER_ENTRY`의 미해결 판정만 제시한다고 보고했다. 코드 대조 결과 CoC와
제약 작업이 동일한 지시문을 사용하여 CoC에도 EBLC 진입 profile 판정 지시가 포함되어 있었다.
해당 생성 job의 입력은 첫 시점 t0=0, 실제 1프레임임을 읽기 전용으로 확인했다.
따라서 단일 이미지라는 설명 자체는 맞으며, 형식 제약 판정이 장면 본문을 대체하도록
유도할 수 있는 과제 혼합이 수정 대상이다. 차량 제어 정보 부재만으로 원인을 단정하지 않는다.

CoC `studio-scene-coc-v2`는 구체적 관찰·객체/도로 관계·확인 가능한 변화·불확실성·짧은 조건부
행동 근거와 독립 본문을 요청한다. 단일 프레임에서 시간 변화나 실제 운전자 제어 원인을
단정하지 않되 관찰 가능한 설명을 생략하지 않도록 했다. 제안 근거가 없으면 추가 확인 사항과
빈 행동 목록을 허용한다. 후속 제약 `studio-source-proposal-v1`에만 지원 술어/행동 판정을 둔다.
요청에 실제 frame_count와 single_frame/past_to_current_sequence를 명시하고 각 CoC 필드에
역할 설명을 추가했다. provider signature도 갱신하여 이전 대기 작업을 새 지시로 재해석하지 않는다.
사람 승인·학습 적격·출처·미래 누출·비밀·비용 한도 정책은 유지했다.

실패하는 모의 요청 회귀 시험을 먼저 추가했고, 수정 후 전체 **36개 통과/skip 0**(18.437초)를
확인했다. 단일/7프레임 입력, CoC 지시의 계약 코드 제외, task 버전과 필드 설명을 검사했다.
실제 VLM을 재호출하지 않았으므로 새 프롬프트의 생성 품질 개선을 실증했다고 주장하지 않는다.
명명 검사에는 기존 5건만 남았고 범위 밖 파일은 수정하지 않았다.

첫 반영 시도는 사용자의 실행 job을 발견하여 중단 없이 보류했다. 작업 종료와 사용자의
“서버 재시작” 지시 후 지정 Studio만 같은 45453 포트로 재시작했다. 새 PID **1283303**,
REAL 시작 표시, 작업/매뉴얼 HTTP 200 및 미인증 영상 API 401을 확인했다.
재시작 전후 DB 전체 논리 snapshot·auth·provider 설정·기존 run 증거 파일이 동일하다.
사용자 승인으로 앞서 늘린 총 한도 4회는 유지했으며 당시 사용량 **4→4**였다.
추가 API 호출·예산 확대·기존 CoC 덮어쓰기는 하지 않았다. 로그인은 다시 필요하고 수정 지시는
새 생성 요청부터 적용된다. 새 유료 생성에는 남은 한도가 없으므로 별도 한도 승인이 필요하다.
