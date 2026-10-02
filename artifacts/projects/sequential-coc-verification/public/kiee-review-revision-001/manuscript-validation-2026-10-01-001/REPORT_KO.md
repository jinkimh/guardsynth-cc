# E6 최종 문서 재검증

- 소유 프로젝트: `sequential-coc-verification`
- 상태: **PASS / E6 문서 제작 완료** (2026-10-01)
- [전체 제작 보고서](../manuscript-build-2026-10-01-001/REPORT_KO.md) 및 원 빌드 manifest와 로그는 보존했다.
- 완료된 실험이나 PDF 빌드는 재실행하지 않았다.

## 완성 파일

| 결과 | 쪽수 | 항목 |
|---|---:|---|
| [파란색 개정 논문](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/main.pdf) | 8 | — |
| [표시 제거 논문](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/main-clean.pdf) | 8 | — |
| [심사위원1 답변서](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/response-to-reviewer-1.pdf) | 10 | 9 |
| [심사위원2 답변서](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/response-to-reviewer-2.pdf) | 9 | 8 |
| [심사위원3 답변서](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/response-to-reviewer-3.pdf) | 12 | 11 |

## 재검증 원인과 결과

원 빌드의 최초 document_validation.json은 PASS였다. 봉인 이후 원 검증기를 재실행할 때 색상 값의 Python tuple과 JSON list를 그대로 비교하여 동일 결과를 변경으로 오판했다. 이는 검증 스크립트의 저장 형식 비교 오류다. 기존 빌드 기록은 수정하지 않고, 이 run의 검증기에 JSON 표현을 정규화한 비교를 적용했다. 기존 전체 보고서의 검증 명령 대신 아래 명령을 사용한다.

```bash
/home/jinhyun/prj_ws/prj_jin/oculophenome-xai/.venv/bin/python artifacts/projects/sequential-coc-verification/public/kiee-review-revision-001/manuscript-validation-2026-10-01-001/verify_documents.py
```

[document_validation.json](document_validation.json)은 오류0/PASS다. marked/clean의 페이지별 텍스트 동일,28개 답변 발췌와 명시 쪽수,최종 절·표·식·그림·목록 위치,색상,A4 및 미해결 인용·참조/글자 누락/넘치는 박스 부재를 다시 확인했다.

[hash_validation.json](hash_validation.json)의 모든 검사는 true다. 기존 봉인 파일51개,개정 소스26개,사용 근거 입력,5개 PDF와 링크된 글꼴·TeX 자산의 해시가 원 manifest와 일치한다. 문서 오류 수정이나 PDF 재생성 없이 검증기 비교 오류만 별도 기록으로 바로잡았다.

[naming_validation.json](naming_validation.json)은 새 범위 위반0,동일한 기존·희소 경고12개다. 직접 검사 명령은 sparse worktree의 cli.project_paths 누락으로 실행이 불가하여 승인된 원 저장소 검사기 import/ROOT 변경 대안을 사용했다. 일반 규칙 완화,기존 Reviewer 파일명 변경,무관한 프로젝트 수정은 없다.

## 남은 한계

144/144는 개발 후 동일 사례 재시험이다. 독립 자연 오류 성능,사람 재평가,개발 미사용 독립 시험,자동 의미 추출,정량 시간 제약,차량 동역학·물리 안전은 확립하지 않았다. 단순 FSM도 성공하여 UPPAAL 정확도 우위를 주장하지 않는다. 원 생성 prompt/checkpoint/config 일부는 미복원이다.

접수번호·실제 심사 수정 차수와 공식 필수 분량은 미확인이다. 원고8쪽을 완성했으며 baseline10쪽을 필수 제한으로 간주하지 않았다. 다음 작업은 저자 최종 검토와 메타데이터 확인이다. 외부 제출·게시·메시지,merge/push·무관한 정리/삭제는 하지 않았다.
