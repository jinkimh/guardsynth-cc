# GuardSynth vehicle assurance source 감사 보고서 v0.1

## 목적

실제 장면 EBLC의 동적 제동 bound에는 “관측된 적이 있는 값”이 아니라 해당 vehicle/DBW 구성에서
정해진 운용조건 아래 보장되는 값이 필요하다. 이 감사는 사용할 수 있는 근거와 사용할 수 없는
근거를 fail-closed 방식으로 분리한다.

## 허용하지 않는 대체값

- `OBSERVED_EGOMOTION`: 녹화된 가속도는 그 장면의 관측값이며 미래의 최소 보장 감속도가 아니다.
- `DERIVED_COC_RESPONSE_LATENCY`: CoC event와 속도 변화의 간격은 actuator command latency가 아니다.
- `PLATFORM_INTERFACE_DOCUMENTATION`: API·compute·sensor rig 설명은 특정 차량의 제동 보장이 아니다.
- 일반적인 제동거리 공식, 임의 friction, 사람 반응시간 또는 synthetic default

[NVIDIA PhysicalAI 데이터셋](https://huggingface.co/datasets/nvidia/PhysicalAI-Autonomous-Vehicles)은
sensor, egomotion, calibration과 vehicle dimensions를 제공하지만 brake command/actuation feedback
또는 vehicle-specific 보장 profile을 제공하지 않는다. [DRIVE AGX](https://developer.nvidia.com/drive/agx)는
개발 compute/IO 플랫폼이다.

[VehicleIO workflow](https://developer.nvidia.com/docs/drive/drive-os/7.0.3/public/drive-os-linux-sdk/embedded-software-components/DRIVE_AGX_SoC/DriveWorks/DriveWorks_SDK/tutorials/intermediate_tutorials/vehicle_action/vehicleio/usecase1.html)는
DBW fault의 정확한 원인에 vendor 문서가 필요함을 설명하고,
[VehicleIO actuator API](https://developer.nvidia.com/docs/drive/drive-os/7.0.3/public/drive-os-linux-sdk-api-ref/group__VehicleIO__actuators__group.html)는
지원되는 limit가 actuation interface에 의존하며 runtime capability 조회가 필요하다고 명시한다.

## 통과 조건

`OEM_VALIDATED` 또는 `CONTROL_STACK_VALIDATED` source에 다음이 모두 있어야 한다.

1. 현재 scene bundle과 동일한 `vehicle_binding_key`
2. 원문 reference와 SHA-256
3. 검증 방법
4. 최소 보장 감속도
5. command-to-deceleration 최대 latency
6. 최대 절대 jerk
7. 노면·속도·적재·온도 등 operating conditions
8. uncertainty/confidence model
9. vehicle/DBW identity, runtime capabilities, OEM 문서 또는 통제된 제동시험

하나라도 없으면 `MISSING_SOURCE_BEARING_VEHICLE_ASSURANCE_PROFILE`로 중단한다.

## 현재 판정

첫 Alpamayo calibration 장면은 clip-specific Hyperion 8.1 rig binding까지 있으나 실제 차량/DBW
identity와 검증된 제동 profile은 없다. 따라서 8/9 상태를 유지하고 EBLC→Core/Z3 실제 장면
실행을 허용하지 않는다. source-bearing simulator profile을 사용하는 경우 실제 차량 결과와
분리된 별도 실험으로 보고한다.
