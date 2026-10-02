# 한글·영문 논문 구성안 산출물

project_id: `guardsynth-coc`

## 산출 범위

상세 근거 패키지를 바탕으로 본문 8개 장, 기여·연구 질문, 그림 2개·표 5개,
본문과 보충자료의 구분, 집필 순서를 한글·영문 Markdown과 PDF로 정리했다.
이는 저자 검토용 구성안이며 완성된 원고 또는 투고용 조판본이 아니다.

저자의 범위 수정에 따라 EBLC 테스트 생성·행동 테스트·실행 중 모니터링과
오류 주입 실험을 논문 구성에서 제외했다. EBLC 정형 명세·검증, CNL 생성,
CoC 보강과 VLM 학습·성능 평가는 유지했다. 기존 패키지, 실험 기록,
main.tex와 이전 PDF는 수정하지 않았다.

## 파일

- 한글 원본: `projects/04-guardsynth-coc/paper/IEEE_ACCESS_MANUSCRIPT_OUTLINE_V01_KO.md`
- 영문 원본: `projects/04-guardsynth-coc/paper/IEEE_ACCESS_MANUSCRIPT_OUTLINE_V01_EN.md`
- [한글 PDF](ieee-access-manuscript-outline-v01-ko.pdf): 7페이지.
- [영문 PDF](ieee-access-manuscript-outline-v01-en.pdf): 8페이지.

각 TeX 파일은 Markdown으로부터 생성한 조판 스냅샷이다. 원문 수정은 Markdown에서
수행하며, PDF의 상대 링크는 저장소 디렉터리 배치를 유지해야 열린다.

## 확인

두 문서의 본문 장 구성과 주요 결과 수치, PDF 텍스트 보존, 원문 해시,
로컬 링크 대상을 확인한다. 한글 3·5페이지와 영문 4·6페이지의 대표 조판을
시각적으로 확인했다. 상세 기계 확인 결과는 `RESULT.json`에 기록한다.
다음 단계는 이 구성에 대한 저자 검토 후 본문 III–IV장과 예제·그림을 작성하는 것이다.
