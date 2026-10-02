# EBLC 플랫폼과 독립 연구 프로젝트 분리 결정 v1

- 상태: `ACCEPTED`
- 결정일: 2026-08-13
- 적용 대상: `eblc-bcv`, `eblc-language-verification`, `guardsynth-coc`

## 결정

재사용 EBLC/BCV 구현은 `platforms/eblc-bcv/`에 유지한다. 독립 연구 질문, comparative
evaluation, paper-specific experiments, analysis와 manuscript는
`projects/05-eblc-language-verification/`가 소유한다. GuardSynth는 플랫폼을 직접 소비하며,
Project 05를 관련 독립 연구로 참조한다.

## 이유

- EBLC 구현은 GuardSynth와 Specification Alignment 등 둘 이상의 실제 소비자가 있다.
- 독립 논문은 플랫폼 release와 구분되는 baseline, locked evaluation 및 artifact 소유권이 필요하다.
- 구현과 논문 평가를 분리하면 application 성능을 언어 자체의 증거로 순환 사용하는 위험을 줄인다.

## 결과

- 플랫폼 source, schema, conformance test와 release report는 이동하지 않는다.
- Project 05는 플랫폼 version을 dependency로 고정해 평가한다.
- Project 05의 실험 run은 `artifacts/projects/eblc-language-verification/`에 기록한다.
- 플랫폼 자체 release/conformance run은 `artifacts/platforms/eblc-bcv/`에 남는다.
