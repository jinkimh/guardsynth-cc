# EBLC v0.2 사용자 가이드

## 1. 무엇을 입력하는가

EBLC program은 이미 구조화된 다음 입력을 받는다.

1. source가 붙은 규칙과 claim scope
2. target actor와 conflict zone binding
3. 관측 predicate와 freshness 계약
4. 차량 profile 또는 system requirement에서 공급된 수치
5. 수치가 어떻게 계산되는지 나타내는 typed derivation DAG
6. release/reactivation/UNKNOWN fallback과 priority

CoC는 `CLAIMED` retrieval 단서가 될 수 있지만 그 자체가 관측 사실이나 법적 권위는
아니다. 입력이 부족하면 값을 만들어 넣지 말고 binder/adapter의
`REVIEW_REQUIRED` 또는 `UNSUPPORTED`를 유지한다.

## 2. 가장 작은 실행 흐름

프로젝트 루트에서 공개 v0.2 fixture를 읽고 CNL로 투영한다.

```python
from pathlib import Path

from src.guard_synth_eblc.cnl_renderer import export_cnl, render_program
from src.guard_synth_eblc.examples import synthetic_program_v02

program = synthetic_program_v02()
document = render_program(program)
export_cnl(document, Path("/tmp/eblc-cnl"))
```

생성 파일은 `CONSTRAINTS.txt`와 `CNL_MAPPING.json`이다. 전자는 model prompt에 넣을 수
있는 controlled text이고 후자는 각 문장의 EBLC field/evidence 연결 및 input/output
hash다. 실행과 SMT 변환에는 text가 아니라 `program`을 사용한다.

## 3. 공개 pipeline

```bash
python3 -m cli.pipelines.eblc.program_conformance.run --run-id <new-id>
python3 -m cli.pipelines.eblc.composition_compile.run \
  --program-version eblc-program-v0.2 --run-id <new-id>
python3 -m cli.pipelines.eblc.indexed_collection_compile.run --run-id <new-id>
python3 -m cli.pipelines.eblc.release_candidate.run --run-id <new-id>
python3 -m cli.pipelines.guardsynth.source_aware_generate.run --run-id <new-id>
```

- `program_conformance`: 단일 program → Core → Z3와 canonical 결과 비교
- `composition_compile`: 여러 contract의 priority/action 합성
- `indexed_collection_compile`: actor-zone instance를 bundle로 확장
- `release_candidate`: CNL, 추적표, 전체 회귀와 RC gate 실행
- `source_aware_generate`: 구조화 rule/context/profile을 program/indexed collection으로 생성

기존 run ID는 덮어쓰지 않는다. 모든 공개 합성 결과는
`artifacts/results/public/` 아래에 생성한다.

## 4. 결과 읽기

- `VALIDATED`: 제공된 입력과 bounded semantics 안에서 계약 실행이 성립함
- `REVIEW_REQUIRED`: 모호한 association, 미승인 fallback 등 사람 판단 필요
- `UNSUPPORTED`: geometry/profile/source/unit/frame 등 필수 입력 부재 또는 오류
- `CONFLICT`: 근거 또는 hard contract들이 서로 양립하지 않음

`VALIDATED`는 법규의 진위, perception 정확성 또는 차량 안전 인증을 뜻하지 않는다.
SMT의 `SAT`는 조건을 만족하는 witness가 있다는 뜻이고, violation query의 `SAT`는
반례가 존재한다는 뜻일 수 있으므로 query 목적과 함께 읽어야 한다.

## 5. 새 입력을 추가할 때의 체크리스트

- 모든 수치에 unit, frame과 evidence ref가 있는가?
- target과 zone association이 하나로 확정되었는가?
- geometry와 canonical frame transform이 있는가?
- 차량 수치가 실제 profile/source에 의해 보장되는가?
- CoC claim을 `OBSERVED`로 바꾸지 않았는가?
- UNKNOWN, stale, conflict, 바로 전/경계/바로 후 case를 테스트했는가?
- canonical/runtime/Core-SMT agreement가 유지되는가?
- CNL mapping의 omitted field가 없는가?

문법의 권위 있는 범위는 [EBLC v0.2 명세](../../specifications/eblc/EBLC_LANGUAGE_SPEC_V02.md),
현재 완료/이관 상태는 [요구사항 추적표](../../reports/EBLC_REQUIREMENT_TRACEABILITY_V02.md)에 있다.
