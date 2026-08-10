# Package Contents and Exclusions

## 포함

- 실제 Alpamayo 추론을 위한 runbook과 coding-agent prompt
- STL+CBF 중심의 최신 연구계획과 방법 선택 서베이
- 기존 논문ㆍ설계ㆍ관련 연구 문서
- 기존 feasibility/UPPAAL baseline 코드, tests와 XML models
- NVIDIA PhysicalAI AV의 clip index, metadata, reasoning annotation
- 해당 데이터의 라이선스 PDF와 copy manifest
- 기존 모델체킹ㆍ물리 feasibility 파생 결과
- 기존 CPU baseline test 재현용 CoC-NuScenes reasoning과 egomotion labels
- Alpamayo, PhysicalAI AV, CoC autolabeler의 pinned source checkout

## 의도적으로 제외

- Alpamayo-R1-10B 모델 가중치
- Hugging Face token과 기타 credential
- 4GB `v1.0-mini.tgz`와 전체 nuScenes camera 원본
- 약 237MB의 CoC-NuScenes camera MP4
- Hugging Face cache와 다운로드 cache
- UPPAAL 설치 zip, binary와 academic key
- Python virtual environment, `__pycache__`, pytest cache
- LaTeX 중간 build 파일

## 제외 사유

모델 가중치와 공식 영상 데이터는 실행자의 승인된 계정으로 원격 시스템에서 직접 받아야 revision과 라이선스 계보를 보존할 수 있다. 원본 nuScenes 데이터는 현재 ALP-EXP-005 reference inference에 필요하지 않고 패키지 크기의 대부분을 차지하므로 제외했다.

## 보안 분류

`data/nvidia_physicalai/`와 향후 `restricted-results/`는 라이선스 제한 내부 자료로 취급한다. public Git 저장소, 외부 LLM prompt, 공개 artifact storage에 업로드하지 않는다.
