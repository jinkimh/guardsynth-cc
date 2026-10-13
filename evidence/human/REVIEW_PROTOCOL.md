# 검토자용 연속 CoC 시간 일관성 설문 프로토콜 — 한국어판

패킷 상태: `WAITING_FOR_CONTRACT_REVIEW`

## 1. 설문의 목적

이 설문은 자동 파서의 성능을 평가하지 않습니다. 연속된 CoC 텍스트 자체에
시간적으로 이어지는 요구가 있는지, 그 행동열이 무엇인지, 텍스트만으로 모순을
확정할 수 있는지를 독립적으로 판정합니다.

화면에는 CoC 텍스트와 첫 사건 기준 상대 시간만 있습니다. 영상, 그림, 궤적,
객체ㆍ신호 상태, 검사기ㆍUPPAAL 결과는 없습니다. 실제 사실을 추측하지 마십시오.

## 2. 세 가지 판정

### 2.1 `temporal_requirement_explicit`

문장 사이 또는 한 문장 안에 유지, 해제, “먼저 A, 다음 B” 같은 시간적 요구가
명시됐는지 판정합니다.

- `YES`: 시간적 연결이 명시되어 있습니다.
- `NO`: 행동은 있어도 서로 이어지는 시간적 요구는 없습니다.
- `AMBIGUOUS`: 문장 자체가 모호하여 정하기 어렵습니다.

### 2.2 `required_action_sequence`

텍스트가 요구하는 행동의 **의미 단계**를 시간 순서대로 버튼으로 추가합니다.
한 행동만 고르는 항목이 아닙니다. 같은 행동이 연속 반복되면 한 단계로 합칩니다.

- `STOP, STOP, ACCELERATE, ACCELERATE`
- 저장: `STOP_OR_HOLD>ACCELERATE_OR_PROCEED`

한 문장에 “정지한 다음 출발한다”라고 적혀 있어도 두 단계를 모두 기록합니다.
행동이 없으면 `NO_EXPLICIT_ACTION`, 행동 순서를 읽을 수 없으면 `AMBIGUOUS`를
단독으로 선택합니다. 잘못 누르면 마지막 단계 취소 또는 전체 초기화를 사용합니다.

### 2.3 `textual_consistency`

- `TEXTUAL_CONTRADICTION`: 문장만으로 시간적 요구의 충돌이 확정됩니다.
- `TEXTUALLY_CONSISTENT`: 텍스트에 명시된 유지ㆍ해제ㆍ순서 관계가 서로 맞습니다.
- `UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED`: 문장은 이해되지만 실제 신호ㆍ객체ㆍ영상
  상태가 있어야 모순 여부를 정할 수 있습니다.
- `AMBIGUOUS_TEXT`: 문장 자체가 모호합니다.
- `NOT_APPLICABLE_NO_TEMPORAL_REQUIREMENT`: 서로 이어지는 시간적 요구가 없습니다.

## 3. 합성 예제

### 텍스트 모순

- 앞: “신호가 녹색이 될 때까지 정지한다.”
- 뒤: “신호가 아직 적색이므로 출발한다.”
- 행동열: `STOP_OR_HOLD>ACCELERATE_OR_PROCEED`
- 판정: `TEXTUAL_CONTRADICTION`

### 외부 증거 필요

- 앞: “보행자가 지나갈 때까지 정지한다.”
- 뒤: “이제 출발한다.”
- 행동열: `STOP_OR_HOLD>ACCELERATE_OR_PROCEED`
- 이유: 보행자가 실제로 지나갔는지 텍스트만으로 알 수 없습니다.
- 판정: `UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED`

### 텍스트상 일관됨

- 앞: “오토바이가 지나갈 때까지 정지한다.”
- 뒤: “오토바이가 통과했으므로 출발한다.”
- 행동열: `STOP_OR_HOLD>ACCELERATE_OR_PROCEED`
- 판정: `TEXTUALLY_CONSISTENT`

표현 자체가 불분명하면 `AMBIGUOUS_TEXT`이고, 표현은 명확하지만 실제 상태 증거가
필요하면 `UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED`입니다.

## 4. 세 문항 작성 예

다음 두 문장이 제시됐다고 가정합니다.

1. “보행자가 지나갈 때까지 정지한다.”
2. “이제 출발한다.”

작성 예는 다음과 같습니다.

- `시간적 요구=YES`: “~할 때까지”라는 유지ㆍ해제 조건이 있습니다.
- `행동열=STOP_OR_HOLD>ACCELERATE_OR_PROCEED`: 정지한 다음 진행합니다.
- `텍스트 관계=UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED`: 보행자가 실제로 지나갔는지는
  영상이나 상태 정보가 필요합니다.

반대로 뒤 문장이 “보행자가 아직 횡단 중이므로 출발한다.”라고 명시하면 외부
증거 없이도 두 요구가 충돌하므로 `TEXTUAL_CONTRADICTION`입니다.

## 5. 판단하지 않는 것

- 차량이 실제로 정지하거나 출발했는지
- 보행자나 장애물이 실제로 사라졌는지
- 행동이 안전하거나 교통법규에 맞는지
- 사람 운전자의 행동이 정답 또는 최적인지
- 자동 파서가 텍스트를 잘 읽었는지

## 6. 저장 방법

세 판정 항목을 모두 입력해야 한 사례가 완료됩니다. 메모는 선택 사항입니다.
검토자 A는 `contract_review_A.csv`, 검토자 B는 `contract_review_B.csv`로 저장하고
`review/` 디렉터리에 둡니다. review ID나 CSV 헤더를 바꾸지 마십시오.

두 독립 CSV가 모두 준비된 뒤에만 불일치를 계산합니다. 합의 과정에서도 두 원본
CSV는 수정하거나 덮어쓰지 않습니다.
