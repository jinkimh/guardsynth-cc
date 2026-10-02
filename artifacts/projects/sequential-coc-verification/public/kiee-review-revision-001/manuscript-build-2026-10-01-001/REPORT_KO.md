# E6 개정 논문 및 세 심사 답변서 제작 결과

- 소유 프로젝트: `sequential-coc-verification`
- 작업: 승인된 대응·리비전 설계 10–12절의 E6 문서 제작
- 상태: **COMPLETE — 문서 제작과 검증 완료** (2026-10-01)
- 비교 기준: 원 저장소의 `latex-kiee-review-2022-coc-audit-10pages` 제출본. worktree 서론 미리보기는 전체 개정본 비교 기준이 아니다.
- 완료된 실험은 다시 실행하지 않았다. 저장 JSON/CSV 재집계와 해시 비교만 수행했다.

## 완성 파일

| 파일 | 쪽수 | 내용 |
|---|---:|---|
| [main.pdf](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/main.pdf) | 8 | 이번 수정 파란색 |
| [main-clean.pdf](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/main-clean.pdf) | 8 | 동일 내용, 수정 표시 제거 |
| [response-to-reviewer-1.pdf](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/response-to-reviewer-1.pdf) | 10 | Major 6 + Minor 3 = 9항목 |
| [response-to-reviewer-2.pdf](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/response-to-reviewer-2.pdf) | 9 | 1.1/1.2 분리 포함 8항목 |
| [response-to-reviewer-3.pdf](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/response-to-reviewer-3.pdf) | 12 | 11항목 |

개정 소스와 빌드 방법은 [README](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/README.md)에 있다.

원본 자산을 상대 링크로 재사용했고 제출본과 고정 실험 구현을 변경하지 않았다. 답변서는 project01 샘플의 A4/24mm/11pt/NotoSerifCJKkr, 코멘트·저자 답변·논문 반영 결과 3블록, 표지·총평·맺음말 구조를 적용했다. 샘플 접수번호나 “2차 수정”은 복사하지 않았다.

## 본문과 답변의 정렬

제목·초록·문제 정의·방법·실험 표·관련 연구·한계·결론을 CoC 작성 오류 가능성, 시간·조건 관계 검사 및 최초 사건·의무·근거 추적의 적용 가능성으로 정렬했다. 보행자 통과 전 정지 후 녹색 신호로 출발하는 가상 예시에서 A 미해제 확인은 모순, 해제 정보 없음은 근거 부족, A 해제 확인은 해당 의무와 양립한다.

자동 텍스트 경로와 작성 프레임 경로, 고정 단일 의무 모델과 별도 조건별 모델을 구분했다. P4는 입력 모순과 다른 검사기 처리 오류로 분리했다. 중심 모델이 정량 시간 제한이나 차량 동역학을 구현했다고 하지 않는다.

- 최초144건: 모순72/정상36/근거부족36. 기존 구조화96/144, 최초 위반54/72. local72/144, 이전1/3/5사건84/90/90, 단순 FSM144/144. 자동 텍스트는 전부 UNKNOWN으로 기대 미상36건만 일치한다. 정상 오탐0/36 중30건은 UNKNOWN이다.
- 최초 실패48건은 복수 일부 해제18/복수 모두 해제18/중간 대기 후 정상 해제12로 보존한다. 이후 조건별 모델144/144, 최초 위반72/72, 문제 위치·의무·사유 각각108/108은 **개발 후 동일 사례 재시험**이다. R3의 개발 미사용 독립 시험 요구를 충족했다고 답하지 않는다.
- 기존 Python–UPPAAL 판정·오류 종류·최초 위치144건 일치. 미상 사유24차이는 최초 반례 접두 경로 문제였고 종료 질의로144/144 일치를 확인했다. 원 파서는 변경하지 않았으며48개 의미 실패의 해결과 구분한다.
- 텍스트 κ0.027301, 불일치23/27, 합의 사유 메모0/27을 유지한다. 전문성·교육·중재·합의 과정을 지어내지 않았다. 임계값130건은 항상72/설정 의존57/항상 미검출1이며58건 전체를 설정 의존으로 기술하지 않는다. 궤적2/7/18 및27건별 사유를 유지한다.
- R1의 feasibility 대안을 명시했다. FSM도 성공하므로 UPPAAL 정확도 우위는 주장하지 않는다. 자연 오류 성능·사람 신뢰도 개선·독립 시험을 실제 수행한 것처럼 서술하지 않는다.

## 검증 결과

[document_validation.json](document_validation.json)은 PASS이며 오류 목록은 비어 있다.

- marked/clean 각8쪽의 **페이지별 추출 텍스트가 완전히 동일**하다. marked 변경 내용·표·그림·추가 참고문헌은 파란색, clean은 무채색이다.
- 28항목 모두 코멘트·답변·반영 결과를 갖췄다. 모든 발췌가 원고와 답변 PDF에 존재하며 명시된 발췌 쪽과 일치한다. 생성된 절·표·식·그림·목록 위치 매크로는 최종 main.aux와 일치한다.
- 5개 PDF 모두 A4다. 최종 로그에 미해결 인용·참조, Missing character, Overfull box 또는 치명 오류가 없다. 상속된 글꼴 대체·Underfull 비치명 경고는 남는다. 대표 원고 페이지와 답변서 표지·본문·마지막 페이지를 렌더링하여 레이아웃과 색상을 확인했다.
- 원 제출본20개 파일과 평가 요약의 고정 실험 코드 해시가 일치한다. 원본 소스 비교는 [manuscript_diff.patch](manuscript_diff.patch), 원본 해시는 [baseline_hashes.json](baseline_hashes.json)에 있다.
- 기존166개·신규36개 시험 통과 및 원고24pass/1skip은 이전 저장 실행 근거이며 E6에서 재실행하지 않았다. 시험이나 코드리뷰를 독립 사람 gold로 간주하지 않는다.
- 빌드 드라이버는 기존 run 경로를 거부한다. [build_guard_validation.json](build_guard_validation.json)에서 거부와 PDF 해시 불변을 확인했다. 재빌드는 새 owner-scoped run 경로를 사용해야 한다.

저장 검증 재확인 명령(기존 환경 읽기만):

```bash
/home/jinhyun/prj_ws/prj_jin/oculophenome-xai/.venv/bin/python artifacts/projects/sequential-coc-verification/public/kiee-review-revision-001/manuscript-build-2026-10-01-001/verify_documents.py
```

완료 manifest가 있으면 검증기는 기존 결과와 비교하며 기록을 덮어쓰지 않는다.

## 28항목 위치 대응

아래 쪽수는 해당 답변서 PDF의 항목 위치다. 세부 원고 절·표·쪽과 발췌 쪽은 각 “논문 반영 결과”와 document_validation.json에 기록되어 있다.

| 심사 항목 | 답변서 쪽 |
|---|---:|
| R1 Major 1. 자연 오류 검증과 주장 범위 | 2 |
| R1 Major 2. 원문에서 검사 입력으로의 변환 | 3 |
| R1 Major 3. 검토자 일치도와 합의 기록 | 4 |
| R1 Major 4. 비교 방법의 확장 | 5 |
| R1 Major 5. 반응 시간 설정과 탐색 규칙 | 6 |
| R1 Major 6. 재현성과 자료 출처 | 7 |
| R1 Minor 1. 자연 후보 15장면의 선정 | 8 |
| R1 Minor 2. 초록의 검토 분모 | 9 |
| R1 Minor 3. 결론의 필요성과 효과 표현 | 10 |
| R2-1.1. CoC 간 양립 문장 | 2 |
| R2-1.2. 불일치의 영향 문장 | 3 |
| R2-2. 논문 전반의 국문 표현 | 4 |
| R2-3. UPPAAL 명칭 | 5 |
| R2-4. 연구 질문과 기여의 연결 | 6 |
| R2-5. 서론 구조와 간결성 | 7 |
| R2-6. 관련 연구의 기술 비교 | 8 |
| R2-7. 기존 연구 대비 기여 범위 | 9 |
| R3-1. 시간 논리와 실행 중 검증 연구 | 2 |
| R3-2. 자료 버전·생성과 선정 절차 | 3 |
| R3-3. P4 검사기 처리 오류 분리 | 4 |
| R3-4. 미상·장면 종료·복수 의무 | 5 |
| R3-5. 추출 주체와 전체 변환 사례 | 6 |
| R3-6. Python–UPPAAL 상태·속성과 일치성 | 7 |
| R3-7. 순환 검증과 독립 시험 요구 | 8 |
| R3-8. 이력을 보는 비교기 | 9 |
| R3-9. 선정·교육·합의와 낮은 κ | 10 |
| R3-10. 40/40 결과와 자연 성능 지표 | 11 |
| R3-11. 궤적 일치2·불일치7·미상18 | 12 |

## 근거와 인용

원 실험 근거는 같은 artifact parent의 evaluation-summary-2026-10-01-001, controlled-scenarios-2026-10-01-001, terminal-evidence-2026-10-01-001, condition-model-2026-10-01-001 및 restricted 재분석에 있다. RUN_MANIFEST.json은 사용 근거 문서의 해시를 기록한다. restricted 원자료를 이 public 빌드 폴더로 복사하지 않았다. public은 로컬 보관 분류이며 외부 공개 완료를 뜻하지 않는다.

UPPAAL 명칭·질의는 공식 자료, 관련 연구는 1차 문헌을 확인했다. 확인 URL과 구분은 [reference_verification.json](reference_verification.json)에 있다. 신규·최초·최고 또는 기존 시간 논리의 발명 주장은 추가하지 않았다.

## 파일명 검사와 남은 한계

요구된 `python3 cli/checks/file_naming.py`는 sparse worktree의 `cli.project_paths` 누락으로 직접 실행이 중단되었다. 승인된 대안으로 원 저장소 검사기를 import하고 ROOT만 worktree로 지정했다. 상세 결과는 naming_validation.json에 기록한다. 새 개정본·빌드 범위 위반0이며 기존·희소 경고12개는 유지한다. 일반 규칙 완화나 무관한 프로젝트 수정은 하지 않았다. 전체 저장소 naming 통과를 주장하지 않는다.

접수번호와 실제 심사 수정 차수는 “확인 필요”다. 이전10쪽은 baseline 분량이며 필수 제한으로 간주하지 않았다. 공식 투고요령 첨부 PDF를 확보하지 못해 분량 제한은 미확인이다. 핵심 한계를 삭제하여 분량을 맞추지 않았다.

자연 오류 정확도, 독립 사람 재평가, 개발 미사용 독립 시험, 자동 의미 추출, 정량 시간 제약, 차량 동역학·물리 안전은 남은 한계다. 원 생성 prompt/checkpoint/config 일부도 미복원이다. 이를 E6 파일 제작의 중단 사유로 삼지 않고 본문·답변에 명시했다. 외부 제출·게시·메시지 전송·merge/push·무관한 정리/삭제는 수행하지 않았다.
