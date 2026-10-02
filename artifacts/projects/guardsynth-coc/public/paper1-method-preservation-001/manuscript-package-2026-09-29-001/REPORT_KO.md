# IEEE Access 집필 기초 PDF

- project_id: `guardsynth-coc`
- 원본: [한글 패키지](../../../../../../projects/04-guardsynth-coc/paper/GUARDSYNTH_COC_METHODS_SETTINGS_PACKAGE_V01_KO.md)
- 출력: [PDF](guardsynth-coc-methods-settings-package-v01-ko.pdf)
- 편집 가능한 조판 스냅샷: [LaTeX](guardsynth-coc-methods-settings-package-v01-ko.tex)
- 역할: 집필 기초자료. IEEE Access 공식 양식의 제출용 영문 원고는 아님.

기존 22개 절의 연구 내용과 수치를 유지하고 23절에 IEEE Access 준비 항목을 추가했다.
표지·목차·북마크·페이지 번호·23개 표·검색 가능한 한글을 제공한다.
과거 일반화 실패 표는 추가하지 않았으며 원 실험·기존 main.tex·과거 PDF는 변경하지 않았다.
새로운 학습이나 평가를 수행하지 않았다.

공식 [작성 안내](https://ieeeaccess.ieee.org/authors/preparing-your-article/)와
[제출 안내](https://ieeeaccess.ieee.org/authors/submission-guidelines/)에 따라 영문 원고,
공식 템플릿, 편집 파일과 PDF, AI 사용 공개 등의 준비 항목을 분리했다.
저자·소속·지원·인용을 임의로 확정하지 않았다.

## 재조판

이 디렉터리의 완료된 결과를 덮어쓰지 말고 새 owner-scoped run에 LaTeX를 복사한 후,
그 디렉터리에서 아래 명령을 두 번 실행한다. 소스는 로컬 XeLaTeX, kotex,
DejaVu Serif/Sans Mono 및 Noto Sans CJK KR를 사용한다.

```bash
/home/jinhyun/.local/bin/xelatex -interaction=nonstopmode -halt-on-error guardsynth-coc-methods-settings-package-v01-ko.tex
```

원본의 로컬 상대 링크는 PDF 디렉터리 기준으로 조정했다. 같은 저장소 구조에서 사용하며,
PDF만 외부로 옮기면 로컬 근거 파일 링크는 동작하지 않을 수 있다.
PDF 뷰어가 로컬 파일 접근을 차단할 수도 있다. 외부 제출용 참고문헌은 별도로 정리한다.

최종 페이지 수·내용 보존 검사·컴파일 상태는 RESULT.json, 입출력 해시는
RUN_MANIFEST.json에 기록한다. 대표 페이지의 한글·표·코드 가독성을 시각적으로 확인했다.
전체 파일명 검사의 기존 5개 지적 사항은 이번 작업과 관계없으며 수정하지 않았다.
