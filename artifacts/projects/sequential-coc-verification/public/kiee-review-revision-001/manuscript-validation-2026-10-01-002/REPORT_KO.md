# 승인된 E6 후속 원고 보강 및 최종 검증

- 소유 프로젝트: `sequential-coc-verification`
- 상태: **FOLLOW-UP COMPLETE / 문서 검증 PASS** (2026-10-01)
- 이전 E6 완료는 유지한다. 초기 E6의8쪽 원고와 답변서 및 봉인 run001은 보존했다.
- 비교 기준은 원 저장소의10쪽 제출본이다. 핵심 설명을 강화했으며 특정 페이지 수를 목표로 하지 않았다. 원 제출본은 수정하지 않았다.
- 완료된 실험은 재실행하지 않았다. 저장 입력·결과·XML·로그와 구현을 읽어 설명을 정렬했다.

## 완성 산출물

| PDF | 쪽수 | 내용 |
|---|---:|---|
| [main.pdf](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/main.pdf) | 11 | 수정 파란색 |
| [main-clean.pdf](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/main-clean.pdf) | 11 | 동일 내용, 표시 제거 |
| [response-to-reviewer-1.pdf](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/response-to-reviewer-1.pdf) | 10 | 9항목 |
| [response-to-reviewer-2.pdf](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/response-to-reviewer-2.pdf) | 9 | 8항목 |
| [response-to-reviewer-3.pdf](../../../../../../projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/response-to-reviewer-3.pdf) | 13 | 11항목; R3-11 상세 사례 포함 |

## 이전보다 복원·강화한 내용

[절별 비교 보고서](SECTION_COMPARISON_REPORT.md)와 [비교 기록](section_comparison.json)은 각 절의 복원 대상과 복원하지 않은 부정확한 주장/모델 설명을 기록한다. [제출본 비교](submitted_source_diff.patch)와 [초기 E6 비교](e6_source_diff.patch)도 보존했다.

- **자료의 흐름**: 기록 영상/자차 궤적→계산 행동/대표 시점→사후 CoC 생성→저장 문장→검사의 출처 도식을 복원했다. 기록값·계산값·자동 주석·검사 정의와 사건/쌍/장면 단위를 설명했다.
- **방법의 네 단계**: 입력 순서/출처 정리→자동 문구 또는 작성 프레임→배열과 상태 갱신/질의→사건·의무 ID와 원문 회수를 상세 파이프라인 및 본문으로 복원했다. 서론은 가상 A/B 예시와 질문·기여 중심으로 간결하게 유지했다.
- **현재 구현의 구성**: 동결 기존6상태와 보완 모델의2위치를 구분했다. 실제 ScenarioObserver/Observer, committed Run의 idx<N 자기 전이, step(),idx++, idx==N의 Done 전이, N/K 배열, active/known, 누적 bad/missing과 최초 기록을 설명했다. 오래된 보조 시간 네트워크를 중심 모델로 복원하지 않고 실제 모델 도식으로 대체했다. idx++는 함수 내부가 아니라 XML 전이에 있다는 점을 의사코드에도 맞췄다.
- **끝까지 이어지는 사례**: 저장된 보행자 세 변형의 원문 구절·프레임·실제 배열·e0/e1 상태·다섯 질의 결과·문제 사건/의무/사유·원문 회수를 설명했다. A=F/미상/T에 따른 모순/근거 부족/양립을 읽을 수 있게 했다. 증거 기록은 [trace_evidence_check.json](trace_evidence_check.json)에 있다.
- **결과의 이유와 활용**: 기존40쌍의 기억 효과와 P4 처리 시험을 구분하고,144건의 간격/이력 창,단일 의무 투영 손실,복수 일부/모두 해제 및 대기 미상의48실패를 보완 모델 설계와 연결했다. 분류와 최초 위치/108건 추적의 서로 다른 분모,반례 접두 경로와 종료 누적 사유도 설명했다. 검토 기록을 문장 수정/프레임 연결 점검/근거 보충에 활용하는 절차를 복원했다.
- **기여와 한계의 배치**: 반복되던 서론 마지막 범위 문단과 논의의 한계 반복을 줄이고 상세 제한은9절에 유지했다. 자연 오류 정확도·독립 시험·사람 재평가·자동 NLP·정량 시계·차량 안전은 새로 주장하지 않았다. 보조 P5 수식은 중심 이산 모델과 분리했다.

초기 E6의8쪽에서 현재11쪽이 되었다. 글꼴·본문 크기·여백을 늘리거나 빈 내용을 넣어 분량을 맞추지 않았다. 주장의 유효 범위를 지키면서 설명과 해석을 보강한 결과이며, 학회 필수 분량은 여전히 미확인이다.

## 표14와 R3-11 상세

- 본문 **표14(10쪽)**는 일치2/불일치7/미상18의3행 요약이다. 결과 설명은7.6절(9쪽)에 있다.
- 상세 **G01–G27의27행은 R3-11 답변서13쪽**의 사례표로 옮겼다. 입력된27행의 판정과 여섯 사유 건수는 초기 E6와 한 글자도 바꾸지 않았다. 소스는 `response-trajectory-details.tex`이다.
- 본문과 답변서가 서로 상세 위치/요약 위치를 명시한다. 사유는 사건 건수이며 한 장면에서 여러 열에 중복될 수 있다. 행동 일치가 있어도 다른 사건의 시점/해제 정보 부족으로 미상일 수 있다. 궤적 불일치7건은 문장 모순이나 안전 위반의 독립 정답이 아니다.
- [trajectory_relocation.json](trajectory_relocation.json)과 최종 검증은27행 동일,2/7/18분포 및 답변PDF의 G01/G27을 확인했다.

## 검증 결과

[document_validation.json](document_validation.json): **PASS, 오류0**.

- 11쪽 marked/clean의 페이지별 추출 텍스트 동일. 표시본의 변경 본문·표·그림은 파란색이고 clean은 무채색이다.
- 세 답변서9/8/11항목의 3블록과28개 발췌를 확인했다. 발췌가 원고/답변PDF에 존재하고 명시한 쪽과 일치한다. 생성된 절·표·식·그림·목록 매크로는 최종 aux와 같고 실제 답변PDF의 위치 표현도 일치한다. 리뷰어 원 코멘트는 초기 E6와 동일하다.
- 모든PDF A4. 최종 로그에 미해결 인용·참조, Missing character, Overfull box, 치명 오류가 없다. 상속된 글꼴 대체 및 Underfull 비치명 경고는 남는다.
- 대표 원고의 도식·수식·결과/요약 표와 보강된 답변 항목·R3 상세표를 렌더링하여 색상·표/본문 경계·가독성을 확인했다. R3 상세27행은13쪽에 들어간다.
- 원 제출본20파일 해시,고정 실험 코드 해시 및 **이전 봉인 산출물1,834파일** 해시가 일치한다. 이전 E6와 실험 근거를 덮어쓰지 않았다.
- [naming_validation.json](naming_validation.json): 새 범위 위반0,기존/희소 경고12유지. 요구된 직접 명령은 sparse worktree의 cli.project_paths 누락으로 실행 중단되어 승인된 원 저장소 검사기 import/ROOT=worktree 대안을 사용했다. 규칙 완화나 무관한 파일 수정은 없다.

현재 문서의 재검증:

```bash
/home/jinhyun/prj_ws/prj_jin/oculophenome-xai/.venv/bin/python artifacts/projects/sequential-coc-verification/public/kiee-review-revision-001/manuscript-validation-2026-10-01-002/verify_documents.py
```

검증기는 manifest 봉인 후 기존 결과와 비교하며 결과 파일을 덮어쓰지 않는다. 빌드 run002는 첫 본문 미리보기,run003은 레이아웃 경고 수정 전의 중간 기록으로 보존했다. 최종5PDF와 로그는 **build run004**다. 새 빌드는 기존run을 거부하므로 새 COC_BUILD_DIR이 필요하다.

## 유지한 수치와 남은 한계

최초144건의 모순72/양립36/근거부족36,기존96/144 및54/72,local72/144,prev1/3/5=84/90/90,FSM144/144,자동텍스트전부UNKNOWN과 기대미상36건만일치,정상36건 중30UNKNOWN을 유지했다.48실패=18/18/12,보완144/144·72/72·각108/108은 개발 후 동일 사례 재시험이다. 기존Python–UPPAAL144건 판정/종류/위치 일치,미상 사유120/144와 종료 질의144/144는 분리했다.

기존40쌍의 P1–P3주석/구조화 시험30쌍과P4처리10쌍,κ0.027301·불일치23/27·합의 메모0/27,탐지130건의72항상/57설정 의존/1항상 미검출,궤적2/7/18및보조134=125+4+5도 그대로다. 단순FSM이 성공하므로UPPAAL 정확도 우위는 주장하지 않는다.

접수번호와 실제 심사 수정 차수는 확인 필요다. 개발 미사용 독립 시험,독립 사람 재평가와 자연 오류 정확도,범용 자동 의미 추출,정량 중심 시계·차량 동역학·물리 안전은 미확립이다. 원 생성prompt/checkpoint/config 일부는 미복원이다. 다음은 저자 최종 검토와 메타데이터 확인이며, 외부 제출/게시/메시지·push/merge·git index/희소 상태 정리·무관한 삭제는 수행하지 않았다.
