# M15 1차 네 학습 arm·공정 비교 요구사항

- 상태: `PARTIAL`
- work package: `GS-P2-BASELINE-REQUAL-001`
- protocol version: `v2.3-cnl-supervision`
- 권위: [1차/2차 분리 결정](../decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md)

필수 비교는 L0 원본 CoC / L1 동일 source 직접 NL / L2 검증 생략 EBLC→CNL /
L3 검증 EBLC→CNL의 네 arm이다. 동일 base data·action labels·모델 초기값·예산으로
실제 SFT하고, oracle guard/shield 없는 공통 test에서 평가한다.
선별/repair·실패·coverage·문장 길이·compute 차이를 기록하고 placeholder를 실행으로 세지 않는다.
자세한 input/target·검증 ablation·통계는 [M18 계약](M18_EBLC_LEARNING_EFFECT_REQUIREMENTS_V01.md)을 따른다.

종전 B0–B13·E2-FF-MATCHED 전수 및 실제 providers 완비 요구는 2차다. 1차에도 네 arm의 실제
provider는 필요하지만 그 때문에 모든 외부 시스템을 재현하지 않는다. v2.3 L2와 기존 flat L2를 혼합하지 않는다.

## 이전 상세 요구사항 (2차/구현 이력)

<details>
<summary>기존 완료 근거와 확장 protocol 보기</summary>

아래 현재/필수/선행조건 표현은 당시 범위다. 1차 적용은 위 v2.3 계약이 대체한다.

### 이전 M15 비교 baseline과 평가 protocol 요구사항

- work package: `GS-P2-BASELINES-001`
- 상태: `PARTIAL` (재적격화); 역사적 `COMPLETE_PROTOCOL` 보존, `M15-R01 QUEUED`
- 선행조건: M14 scoped front-end input/output protocol

#### 이전 목적

B0–B8/B13을 같은 입력 envelope, source budget, abstention 규칙과 공통 결과 schema로 실행할
수 있게 동결한다. 이 단계는 정확도 우열을 주장하지 않고 M16 이후 평가가 비교 가능한지
확인한다.

#### 이전 baseline registry

| ID | 방법 | 허용 입력 | v0.1 실행 경계 |
|---|---|---|---|
| B0 | controlled template prior | catalog, slice | empirical frequency가 없는 controlled prior임을 명시 |
| B1 | CoC-only free-form model | CoC | provider/model 없으면 `UNSUPPORTED`, 수치 자유생성 금지 |
| B2 | scene-only model | scene | provider/model 없으면 `UNSUPPORTED` |
| B3 | template retrieval only | scene predicate, catalog | retrieval 후보만 반환, applicability 추론 금지 |
| B4 | CoC+scene template retrieval | CoC, scene, catalog | M14 proposal 경로, EBLC/BCV 제외 |
| B5 | DriveReg-style source RAG | CoC, scene, catalog | deterministic BM25 source-catalog adapter |
| B6 | RTCD-style tag filter | scene predicate/tag, catalog | neutral CoC로 scene-only applicability 실행 |
| B7 | physics-only envelope | ego state, geometry, assurance | 수치 입력 없으면 `UNSUPPORTED`, 법규 선택 금지 |
| B8 | SanDRA-like action filter | rule, temporal/reachability action set | reachability 입력 없으면 `UNSUPPORTED` |
| B13 | B5→B6→B8 naive composition | 위 세 adapter 입력 | downstream abstention을 숨기지 않음 |

`style`/`like` adapter는 원 논문의 재현 구현이나 동등 성능을 주장하지 않는다.

#### 이전 공통 출력

- baseline ID/version과 adapter class
- 허용/실제 사용 input channel
- ordered candidate rule IDs와 source refs
- `EXECUTED | REVIEW_REQUIRED | UNSUPPORTED | CONFLICT`
- abstention reason codes
- numeric value/source와 action set(해당하는 경우)
- claim scope와 oracle independence label

#### 이전 protocol gate

1. B0–B8/B13 manifest가 ID/version/input budget을 고정한다.
2. M14 locked 24-case 입력 모두에서 모든 adapter가 결과를 반환한다.
3. provider 또는 필수 입력이 없으면 명시적 abstention이며 fallback 값을 만들지 않는다.
4. 동일 입력과 seed에서 byte-equivalent semantic result를 반환한다.
5. CoC-only/scene-only adapter가 금지된 channel을 읽지 않는다.
6. 결과 schema parse 100%, 숨겨진 failure 0건.
7. generator와 향후 expert/evaluation oracle은 코드·기대 label을 공유하지 않는다.
8. maintained/P0a/structure 회귀를 통과한다.

#### 이전 비목표와 주장 경계

- M15 locked matrix 결과를 baseline 성능 순위 또는 통계적 효과로 해석하지 않는다.
- 외부 LLM/VLM, DriveReg, RTCD4ADS, SanDRA의 완전 재현을 주장하지 않는다.
- 실제 24장면 부족을 synthetic matrix로 해소했다고 주장하지 않는다.
- 실제 차량 assurance/실증은 M21까지 이관 상태를 유지한다.

#### 이전 후속 재적격화 M15-R01

`GS-P2-BASELINE-REQUAL-001`은 실제 B1/B2 provider/model smoke, B9 flat/B10 EBLC+BCV/
B12 always-stop 실행, B11 독립 gold 입력 계약과 B0–B13 version registry를 동결한다.
B11 값은 M16/M17 gold 이후 결합하며 계약 검증에 미래 gold를 요구하지 않는다.
추가 `E2-FF-MATCHED`에는 B10과 같은 scene·CoC·source·model/tuning budget을 준다.
B1의 CoC-only 입력 경계는 유지한다. free-form raw output 오류는 audit에 보존하되
근거 없는 수치를 실행값으로 승격하지 않는다. provider 미설정 abstention은 실행 완료가 아니다.
입력 ablation·정보량 효과·표현/BCV 효과 및 style adapter와 원 논문 재현을 분리 보고한다.

</details>
