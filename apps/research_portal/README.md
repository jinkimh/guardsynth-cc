# GuardSynth-CC 연구 포트폴리오

등록된 5개 연구영역과 EBLC 공용 플랫폼을 canonical 문서에서 검증해 투영하고, owner별 논문·
산출물·검토 워크스페이스를 제공하는 로컬 연구 운영 포털이다. 기본 빌드는 read-only이며,
명시적으로 configured review DB와 auth file을 제공할 때만 동적 검토 API가 열린다. 제한 이미지가
포함될 수 있으므로 새 출력은
`artifacts/projects/guardsynth-coc/restricted/`에만
생성하고 서버는 loopback(`127.0.0.1`)에만 bind한다.

```bash
python3 -m apps.research_portal.run \
  --output-dir artifacts/projects/guardsynth-coc/restricted/guardsynth-project-portal-001/<run-id>

python3 -m apps.research_portal.run \
  --output-dir artifacts/projects/guardsynth-coc/restricted/guardsynth-project-portal-001/<run-id> \
  --serve --port 8765
```

브라우저에서 `http://127.0.0.1:8765/`를 연다. `--serve`는 이미 생성된 포털도 그대로
제공한다. 서버 모드의 `portal-data.js`는 페이지를 열 때마다 각 연구영역의 다음 권위 원장을
다시 읽으므로 개요·목표·마일스톤·현재 태스크 갱신이 자동 반영된다.

`reviews.html`은 등록된 검토 패킷의 직접 링크를 빌드 시 HTML에 포함한다. 자바스크립트가
로딩되지 않아도 목록에서 검토 화면으로 들어갈 수 있고, iframe 없이 전체 폭으로 열린다.
검토 목록·패킷 변경은 새 포털 run을 빌드해 반영한다. 운영·관리 화면은 별도로 접어 둔다.

신규 review backend는 project/classification 하나에 귀속된 기존 SQLite operations DB와 scrypt
hash만 담은 restricted auth JSON을 함께 지정한다. 네 option 중 하나라도 빠지면 시작을 거부한다.

빈 operations DB는 서버가 암묵적으로 만들지 않는다. 새 run 아래에서 다음 명령으로 schema v2
DB를 먼저 만든다. 대상이 등록된 owner/classification artifact root 밖이면 초기화를 거부한다.

```bash
python3 -m apps.research_portal.run \
  --init-review-db artifacts/projects/guardsynth-coc/restricted/<operations-run>/round.sqlite3 \
  --review-owner guardsynth-coc --review-classification RESTRICTED
```

```bash
python3 -m apps.research_portal.run \
  --output-dir artifacts/projects/guardsynth-coc/restricted/guardsynth-project-portal-001/<run-id> \
  --serve --port 8765 \
  --review-db artifacts/projects/guardsynth-coc/restricted/<operations-run>/round.sqlite3 \
  --review-owner guardsynth-coc --review-classification RESTRICTED \
  --auth-file artifacts/projects/guardsynth-coc/restricted/<operations-run>/auth.json \
  --review-public-export-root artifacts/projects/guardsynth-coc/public/research-review-export-001
```

`--review-public-export-root`는 선택 항목이다. 설정한 경우에만 닫힌 회차에서 allowlisted aggregate
public export API가 열리며, 등록된 owner의 `public/` 밖 경로는 거부한다. restricted DB, sample ID,
raw path, 이미지 bytes와 원문 CoC는 public run에 복사하지 않는다.

auth file은 `{"users": [...]}` 구조이며 각 user는 opaque `actor_id`,
`apps.research_portal.security.hash_secret()`으로 만든 `secret_hash`, 그리고
`RESEARCH_LEAD` 또는 `REVIEWER` role 배열만 가진다. 평문 secret은 파일, 명령 기록과 log에
저장하지 않는다. 실제 사용자 생성과 secret 전달은 저장소 밖의 승인된 운영 절차에서 수행한다.

- `projects/<NN>-<project-id>/PROJECT.yaml`
- `projects/<NN>-<project-id>/README.md`
- `projects/<NN>-<project-id>/STATUS.md`
- `projects/<NN>-<project-id>/docs/plans/01_RESEARCH_PLAN_*.md`
- `projects/<NN>-<project-id>/docs/plans/02_PROJECT_MILESTONES.md`
- `projects/<NN>-<project-id>/docs/plans/03_PROJECT_EXECUTION_TRACKER.md`
- 프로젝트 목록과 순서를 정하는 `PROJECT_REGISTRY.json`

생성된 run 파일은 재현성을 위한 빌드 스냅샷으로 변경하지 않고, live 응답만
권위 문서에서 재계산한다. 연구영역의 활성 마일스톤이 원장에 없으면 stale 상태를 표시하지
않고 HTTP 503으로 중단한다. 저장소 전체가 아니라 선택해 복사한 포털 파일만 서비스한다.
