# GuardSynth Studio

- owner_project: `guardsynth-coc`
- subproject: `guardsynth-studio`
- 상태 (2026-09-30): 기존 로컬·모의 검증 이후 실제 Responses 연결 확인 완료. 합성 영상 1회 및 CC0 공개 주행 영상 두 시점의 CoC 생성 성공. 독립 loopback 데모 서버의 HTTP·로그인·REAL provider 확인. 사람 승인·제약 생성·EBLC/CNL·export를 포함하는 실제 AT-11은 아직 미완료.
- [현재 데모 실행 결과](../../artifacts/projects/guardsynth-coc/restricted/guardsynth-studio-001/public-video-demo-2026-09-30-001/RESULT.json): 자동 할당 접속 주소, 검토 시점, 실행 상태. 데모 호출 한도 2회는 소진되어 추가 생성은 차단된다. 일반 신규 실행은 아래 명시 설정이 없으면 계속 DISABLED/503이다.
- [승인 설계](../../projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_STUDIO_DESIGN_V01.md)
- [구현 검증 보고서](../../projects/04-guardsynth-coc/docs/reports/GUARDSYNTH_STUDIO_IMPLEMENTATION_VERIFICATION_REPORT_V01.md)

## 실행

저장소 루트에서 기존 등록 runtime을 사용한다. 추가 패키지 설치나 GPU 사용은 필요하지 않다.
PyAV/Pillow/Z3는 이 runtime에 이미 있으며 decoder와 SMT는 CPU 하위 프로세스에서 실행한다.
기본 포트 0은 OS가 사용 가능한 loopback 포트를 할당하게 한다. 기존 포털 8766 및 다른 앱의
8877은 CLI에서 거부하며 해당 서비스를 조회·중단·재시작할 필요가 없다.

```bash
runtime/alpamayo/ar1_venv/bin/python -B -m apps.guardsynth_studio.run \
  --run-id studio-local-001 --init-auth --actor studio-reviewer

runtime/alpamayo/ar1_venv/bin/python -B -m apps.guardsynth_studio.run \
  --run-id studio-local-001 --port 0
```

첫 명령은 터미널에서 비밀번호를 두 번 입력받으며 출력하지 않는다. 기존 auth 파일을 덮어쓰지 않는다.
두 번째 명령이 성공한 뒤 출력하는 `http://127.0.0.1:<할당된 포트>/`에 접속한다.
현재 접속 가능한 운영 주소를 확인하거나 상시 서버를 시작한 것은 아니다.
DB·auth·영상·프레임·export는 모두 다음 독립 root에 저장한다.

```text
artifacts/projects/guardsynth-coc/restricted/guardsynth-studio-001/studio-local-001/
```

같은 run-id로 다시 실행하면 SQLite revision과 작업 상태를 복구한다. 단일 서버 lock을 사용한다.
포털 DB를 지정하는 옵션은 없으며 loopback 이외 바인딩도 없다. 세션은 재시작 시 재로그인한다.
처리 중 순수 작업은 INTERRUPTED, 모델 전송 결과 불명 작업은 OUTCOME_UNKNOWN으로 복구하며
자동 유료 재시도하지 않는다. 기본 설정은 `{"mode":"DISABLED","model":null}`이며,
테스트 MOCK은 운영 CLI에서 켤 수 없다. OpenAI 연결 설정과 AT-11은 아래처럼 별도로 준비한다.

## OpenAI Responses 설정과 전송 경계

사용자 승인 방식은 “OpenAI API 방식을 사용하자.”이다. 이는 어댑터 구현 선택이며 실제 영상
전송·유료 호출 승인으로 해석하지 않았다. Responses의 이미지와 구조화 출력 문법은
[Images and vision](https://developers.openai.com/api/docs/guides/images-vision),
[Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)를 확인했다.

`--provider-config`는 비밀값 없는 JSON 파일을 읽는다. 다음은 **비활성 준비 예제**로, 값을
사용자/운영자가 확정하기 전에는 생성할 수 없다. 설정 파일 자체는 이번 작업에서 만들지 않았다.

```json
{
  "mode": "OPENAI",
  "model": null,
  "transmission_approved": false,
  "video_sha256_allowlist": [],
  "max_calls": 0,
  "max_output_tokens": 0,
  "timeout_s": 120
}
```

- `model`: 이미지 입력과 Structured Outputs를 지원하는 명시적 모델명. 기본 모델·fallback 없음.
- `transmission_approved`: 선택 영상의 OpenAI 외부 전송을 승인한 뒤에만 `true`.
  `video_sha256_allowlist`에는 승인된 원본 영상 SHA-256만 넣는다. 로컬 업로드 권한과 별개다.
- `max_calls`: 해당 Studio run의 누적 호출 시도 상한(1–10000). SQLite에 전송 전 예약하며 실패·
  timeout·결과 불명도 소비한다. 서버 재시작/설정 변경으로 초기화되지 않는다. 수동 재시도도 소비한다.
- `max_output_tokens`: 요청별 1–8192, `timeout_s`: 1–120초. 금액을 추정하거나 통화 예산을
  자동 보증하지 않으므로 모델 가격과 입력 비용을 고려한 사용자 한도·계정 예산 설정이 필요하다.
- API 키는 서버 프로세스의 `OPENAI_API_KEY` 환경변수에 비밀관리 도구로 주입한다. 설정 JSON,
  명령 인자, 브라우저 입력, DB, 로그, export에 키를 넣지 않는다. 키를 확인·출력하는 명령은 제공하지 않는다.
  ChatGPT/Codex 로그인 복구는 Studio API 키 설정을 대신하지 않는다.

키·모델·영상 전송 승인·호출 한도 중 하나라도 없거나 설정이 유효하지 않으면 DISABLED/503이다.
준비가 끝난 후에만 실행 명령에 `--provider-config <비밀값 없는 설정 경로>`를 추가한다.
생성 버튼은 명시한 시점만 요청하며, 전체 영상 자동 전송은 하지 않는다.

서버는 같은 추출의 시간순 1–7개 프레임을 t0까지 다시 확인하고 PNG 해시/긴 변 1280px,
이미지당 8 MiB, 요청 전체 32 MiB, 텍스트 32 KiB, 반환 결과 16 KiB를 제한한다.
이미지는 base64 `input_image`, 초기 detail은 `low`이며 실제 장면 세부 판독 적합성은 AT-11 대상이다.
CoC 작업에는 프레임만, 제약 작업에는 프레임과 승인된 CoC·출처만 입력한다. 행동 정답,
다른 시점 결과, 세션 이력, 전체 영상, 솔버 미래 witness는 보내지 않는다. 출처 URL도 fetch하지 않는다.

매 요청 `store=false`, 대화/previous_response_id 없음, `tools=[]`, 자동 재시도 0, 모델 fallback 0이다.
`store=false`는 무보존 보장이 아니다. 실제 전송 전 계정의 데이터 보존 조건을 확인해야 한다.
고정 HTTPS endpoint만 사용하는 CPU 하위 프로세스가 전체 호출 deadline을 제한한다.
HTTP 오류 본문/헤더/예외 원문은 저장하지 않으며 auth/429/timeout/refusal/incomplete/JSON/schema를
분리된 오류 코드로 남긴다. timeout은 결과·비용이 불명일 수 있으며 취소로 원격 비용 취소를 보장하지 않는다.
수동 재시도 후에도 `provider_error` 감사 기록을 보존한다. 키 반향은 JSON 해석 전후 검사하여 차단한다.

제약 출력은 기존 proposal 스키마의 닫힌 부분집합이다. `concepts={}`, `executable_parameters=null`로
두며 모델 생성 실행 코드/계약을 사용하지 않는다. 출처 refs·대상/영역·적용성·사유는 사람이 수정·승인하고
기존 EBLC 경로로 계약을 작성·검사한다. 모델 응답/스키마 성공은 승인·법규/장면 사실 인증이 아니다.
테스트용 전송 함수를 주입하면 반드시 MOCK이며 학습 부적격이다. 실제 AT-11은 권한 있는 영상의
두 시점에서 실제 모델 → 사람 승인 → EBLC/CNL → export까지 별도로 수행해야 한다.

## 검토 흐름

CoC 프롬프트 `studio-scene-coc-v3`는 사건→자차와의 관계/위험→행동→목적을 설명하고,
EBLC 술어/행동 코드의 적용 판정은 후속 제약 요청으로 분리한다. 첫 시점은 실제로 이미지가
한 장이므로 시간 변화·실제 제어 원인을 단정하지 않는다. 여러 프레임이면 제공된 시간순
근거만 사용한다. 본문은 3~5문장으로 행동 이유→제공된 실측 근거→확인 한계를 정리한다.
운전자의 실제 행동 원인이 미확인이라는 이유로 근거 있는 권고 이유를 생략하지 않는다.
이미 제동했다는 기록만으로 추가 제동을 정당화하지 않으며, 객체 동일성과 조향 부호도 추정하지 않는다.
이 변경은 기존 생성문·사람 답변을 자동 수정하지 않으며 새 요청부터 적용한다.
모의 시험은 요청 분리를 확인한 것이고 새 프롬프트의 실제 생성 품질 수용 시험은 아니다.
동일 scene-0103 입력으로 실제 생성 1회를 수행한
[행동 이유 우선 프롬프트 비교](../../artifacts/projects/guardsynth-coc/restricted/guardsynth-studio-001/coc-reason-prompt-2026-09-30-001/REPORT_KO.md)에
변경 전후 원문과 남은 한계를 기록했다. 41개 회귀 시험은 통과했으며 사람 승인과 일반적 품질 수용은 별도다.

상단 **작업 화면 | 사용 매뉴얼**에서 매뉴얼을 새 탭으로 열 수 있다. 각 편집 영역의
**자세한 설명**은 해당 항목으로 바로 이동하며 작업 탭의 선택 시점·입력을 바꾸지 않는다.
화면의 짧은 안내와 펼칠 수 있는 참고 예시, CoC·행동·관찰별 설명을 함께 제공한다.
예시는 답변을 자동 입력하거나 승인하지 않는다. 실제 내용은 직접 검토·저장·승인해야 한다.
매뉴얼 원본: [manual.html](static/manual.html).

2026-09-30 매뉴얼 반영 후 지정 데모의 [작업 화면](http://127.0.0.1:45453/)과
[사용 매뉴얼](http://127.0.0.1:45453/manual.html)의 HTTP 200을 확인했다.
서버의 loopback 주소이므로 원격 사용자는 기존 SSH 터널을 이용한다. 이 확인은 당시 상태이며
영구 가용성을 보장하지 않는다. 이 배포에서 로그인 세션은 초기화되었으므로 재로그인이 필요하다.
사용자 답변·기존 실행 기록·인증/provider 설정·소진된 호출 한도(2/2)는 보존했다.
준비된 공개 데모의 화면 7번·13번 초안을 추가 생성 없이 검토할 수 있다.

1. 사용권한을 확인한 MP4/H.264 영상을 로컬 업로드한다. probe 작업 성공 후 간격을 지정해 추출한다.
   처음/끝과 실제 PTS를 보존하며 모든 추출 시점을 열 수 있다. 모델 생성은 자동 실행하지 않는다.
2. 시점별 CoC와 별도 행동 레이블을 작성·승인한다. 일반 텍스트 입력은 IndexedDB outbox와
   CAS 자동저장에 묶인다. 저장 실패/409에서는 내 초안과 최신본을 비교한 뒤 명시적으로 새 버전을 만든다.
3. 출처 원문·버전·위치를 입력하고 검토한다. EXTERNAL 출처의 관할/효력 범위는 고급 JSON에서
   `jurisdiction`, `applicable_scope`, `effective_period`를 기록한다. POLICY를 법규로 표시하지 않는다.
4. 현재 프레임에서 대상 점·영역을 그리고 관찰 TRUE/FALSE/UNKNOWN/CONFLICT 및 근거 유효성을
   기록한다. 문맥 의무의 null 대상은 별도 확인이 필요하다. 도형 삭제는 현재 버전의 좌표를 제거한다.
5. 제약 초안→사람 승인→계약 초안→사람 승인 후 Q1–Q5, CNL, 결합 작업을 각각 실행한다.
   제약/행동/CNL 승인은 별개다. SAT는 장면 사실이나 안전의 인증이 아니다.
6. 원본/주행 계보 그룹의 split을 확정하고 저장 snapshot을 export한다. 미승인·수동/mock CoC·
   UNKNOWN·미지원은 학습 적격이 아니다. DRAFT export는 이 상태를 보존한다.

지원 profile은 두 술어의 진입/보류, horizon=3이다. 가속·시간 임계 등은 임의 근사하지 않는다.
한글 CNL 수동 편집은 고급 `derived`에 보관하며 결정적 생성문을 덮어쓰지 않는다.
입력 context를 쓰려면 고급 `context`에 `text`와 `no_label_leakage: true`를 저장하고 별도 승인한다.
기본 `COC_TARGET`은 CoC/CNL을 출력 목표에만 둔다. raw provenance를 모델 입력에 펼치지 않는다.

구간 생성/일괄 승인은 최대 100시점이다. 일괄 승인은 표시한 시점·component·의존 버전 그대로
원자 처리하며 하나라도 바뀌면 409다. 학습 적격 수와 검토완료 수를 따로 표시한다.

## 재현 검사

생성 버튼은 작업이 끝날 때까지 비활성화해 같은 화면의 중복 요청을 막는다.
생성 중 다른 저장으로 버전이 바뀐 경우 자동 재시도하지 않고, 현재 보고 있는 동일 시점의
최신 저장본을 다시 표시한다. `PROVIDER_STALE`은 예산 초과가 아니며 먼저 저장된 CoC를 확인한다.

```bash
PYTHONDONTWRITEBYTECODE=1 runtime/alpamayo/ar1_venv/bin/python -B -m unittest \
  discover -s apps/guardsynth_studio/tests -t . -v

node --check apps/guardsynth_studio/static/app.js
python3 -B cli/checks/file_naming.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.structure.test_project_layout tests.structure.test_checkpoint_naming_exception
```

테스트는 TemporaryDirectory, 합성 영상, CPU solver와 자동 할당 loopback 포트만 사용한다.
브라우저 시험은 기존 `~/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome`을 사용하며
네트워크 설치를 하지 않는다. Chromium이 없으면 해당 시험을 skip하므로 통과로 해석하지 않는다.
소켓 제한 sandbox에서는 로컬 HTTP/Chromium 시험에 loopback 실행 권한이 필요하다.
테스트용 비밀번호와 가상 REAL provenance fixture는 운영 인증·실제 VLM 호출이 아니다.

## 운영 경계

### 차량 상태가 포함된 nuScenes 예제 (2026-09-30)

사용자 요청 “그 데이터를 예제로 올려서 실제 생성해보고 coc를 만들어보자..”에 따라
공식 nuScenes mini의 `scene-0061` CAM_FRONT와 동일 장면 CAN `vehicle_monitor`를 연결했다.
기존 로컬 데모 화면에서 **nuScenes scene-0061 · 영상 + CAN 상태/제어 예제**를 선택하고,
추출 목록을 연 뒤 **26번째 시점, 12.55초**에서 실제 생성된 CoC를 검토한다.
이번 재시작 후 재로그인이 필요하다. 기존 Bangalore 영상·답변·승인 이력은 보존했다.

원본 취득/변환/입력 근거와 결과는
[예제 보고서](../../artifacts/projects/guardsynth-coc/restricted/guardsynth-studio-001/nuscenes-can-demo-2026-09-30-001/REPORT_KO.md),
[manifest](../../artifacts/projects/guardsynth-coc/restricted/guardsynth-studio-001/nuscenes-can-demo-2026-09-30-001/RUN_MANIFEST.json),
[실제 결과](../../artifacts/projects/guardsynth-coc/restricted/guardsynth-studio-001/nuscenes-can-demo-2026-09-30-001/RESULT.json)에 있다.
39개 원본 카메라 시각을 MP4 PTS로 정확히 보존했으며, 실제 요청은 9.55–12.55초의 7프레임이다.
CAN은 각 이미지 시각 이전의 마지막 표본만 사용한다. 600ms보다 오래되면 null이며 미래 보간은 없다.
속도 km/h, 브레이크 압력 bar, 스로틀 0–1000, 조향각 degree를 분리한다.
측정 시각 정렬은 실시간 전달 지연 검증이 아니다. CAN 기록은 운전자 의도나 안전 제동 보장이 아니다.

연결은 운영자 Python API `Service.attach_vehicle_state(video_id, revision, data, actor, key)`로
새 영상의 주석 작성 전에만 가능하다. [닫힌 스키마](vehicle_state.py)를 검증하고 영상 SHA·원본 CAN SHA·
clock origin·별도 전송 승인을 보존한다. 기존 연결 수정/교체와 기존 주석 뒤 연결은 거부한다.
일반 사용자용 CAN 업로드 UI는 아직 없다. CoC 작업이 시간 필터된 입력 snapshot을 저장하며,
`studio-state-coc-v2`는 행동 이유를 먼저 설명하고 실측 제어와 운전자 의도·원인 증명을 구분한다.
프롬프트 버전은 작업 입력과 provider 서명에 함께 연결되며 변경 전 대기 작업은 전송을 거부한다.
DRAFT export에는 실제 사용한 차량 상태가 입력으로 보존된다. 현재 이 연결은
`VEHICLE_STATE_DEMO_ONLY`로 학습 적격을 차단한다. 기존 사람 승인/EBLC 절차를 대체하지 않는다.

실제 요청 1회 성공, 기존 공유 한도 총6회 중6회 사용. 자동 재시도·한도 증액은 하지 않았다.
실제 CoC 생성 성공은 AT-11 전체 완료가 아니다. 재현 검사는 위 unittest 명령을 사용하며
이번 차량 상태·출처·미래 표본·변조·export 검사를 포함해 39개가 통과했다.

upload 1 GiB/30분, decode 300초, SMT 30초, 단일 작업자/대기 100개, 여유 디스크 2 GiB를
기본 제한으로 사용한다. 취소는 결과 게시를 막으며 이미 실행 중인 CPU 작업은 timeout 안에 종료한다.
출처/권한/계보가 무효화된 export는 다운로드를 거부하고 원 파일은 감사 이력으로 보존한다.
대형 영상·디스크 장애·브라우저 캐시 제한의 운영 적합성 및 백업/보존 정책은 운영자 확인 대상이다.
소규모 로컬 도구이며 인터넷 서비스로 공개하지 않는다.
