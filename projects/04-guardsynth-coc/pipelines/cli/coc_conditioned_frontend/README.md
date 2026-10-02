# CoC-conditioned constraint front-end

공개 synthetic 또는 허가된 구조화 입력을 `CoC(CLAIMED) + scene facts + source catalog`에서
검토 가능한 constraint proposal bundle로 변환한다.

```bash
python3 -m cli.pipelines.guardsynth.coc_conditioned_frontend.run \
  --input projects/04-guardsynth-coc/src/guard_synth/fixtures/coc_frontend_request_crosswalk_v0_1.json \
  --output-dir artifacts/results/public/guardsynth-coc-frontend-001/<run-id>
```

출력은 CoC 원문을 포함하지 않으며 `PROPOSED`는 법적 판단·차량 안전 검증이 아니다.

지원되는 횡단보도 제안 하나를 별도 simulation policy와 결합해 EBLC→Core→SMT까지
실행하려면 다음 명령을 사용한다.

```bash
python3 -m cli.pipelines.guardsynth.coc_conditioned_frontend.materialize \
  --output-dir artifacts/results/public/guardsynth-coc-frontend-materialization-001/<run-id>
```

세 slice의 24개 locked synthetic 경계조건은 다음과 같이 실행한다.

```bash
python3 -m cli.pipelines.guardsynth.coc_conditioned_frontend.evaluate_matrix \
  --output-dir artifacts/results/public/guardsynth-coc-frontend-matrix-001/<run-id>
```

현재 실행 policy 연결은 횡단보도 규칙 하나뿐이다. 그 밖의 규칙은 source 없는 수치를
만들지 않고 `NO_OPERATIONAL_POLICY_BINDING_FOR_PROPOSAL`로 남긴다.
