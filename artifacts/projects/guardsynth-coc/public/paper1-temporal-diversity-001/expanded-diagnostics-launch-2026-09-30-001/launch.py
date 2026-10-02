"""Frozen invocation of existing evaluators; no new model or scoring algorithm."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').exists())
sys.path.insert(0, str(ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import run_temporal_diversity as runner
import analyze_temporal_diversity as analysis

launch = Path(__file__).parent
cfg = json.loads((launch / 'protocol.json').read_text())
d = runner.d
d.LEARNING = ROOT / cfg['adapter_run']
protocol = d.BASE / cfg['evaluation_protocol']
output = d.BASE / cfg['inference_run']
report_dir = d.BASE / cfg['analysis_run']
assert not output.exists() and not report_dir.exists()
d.verify_manifest(protocol, inputs=True)
d.verify_manifest(d.LEARNING)
paths = [Path(__file__), launch / 'protocol.json', Path(runner.__file__), Path(analysis.__file__),
         Path(d.__file__), protocol / 'RUN_MANIFEST.json', d.LEARNING / 'RUN_MANIFEST.json']
for seed in cfg['seeds']:
    for arm in cfg['arms']:
        paths.extend(p for p in (d.LEARNING / f'{arm.lower()}-seed{seed}' / 'adapter').glob('*') if p.is_file())
manifest = {'project_id': 'guardsynth-coc', 'status': 'RUNNING',
            'started_at_utc': datetime.now(timezone.utc).isoformat(),
            'input_hashes': {str(p.relative_to(ROOT)): d.primary.sha(p) for p in paths},
            'configuration': cfg}
d.dump(launch / 'RUN_MANIFEST.json', manifest)
d.dump(launch / 'RESULT.json', {'status': 'RUNNING', 'inference_run': cfg['inference_run'], 'optimizer_updates': 0})
try:
    runner.execute(output, protocol, cfg['gpu'])
    result = analysis.analyze(protocol, output)
    assert result['prediction_rows'] == cfg['expected_prediction_rows']
    assert result['core_oracle_disagreements'] == 0
    result['adapter_run'] = cfg['adapter_run']
    result['D4_evidence_reused_not_new'] = True
    report_dir.mkdir()
    d.dump(report_dir / 'RESULT.json', result)
    report = '# 현재 확장 모델의 추가 진단\n\n'
    report += '2026-09-29 확장 학습의 P0/P1/P2, 세 시드 총 아홉 adapter를 재평가했다. 신규 학습은 없다.\n\n'
    report += '기존 동결 진단의 모든 조건을 다시 실행했으며 주 시험 분포와는 별도이다. '
    report += 'D4 표는 기존 오류 주입 기록의 재사용이며 새 검증 성과로 합산하지 않는다.\n\n'
    report += analysis.report(result)
    (report_dir / 'REPORT_KO.md').write_text(report)
    d.dump(report_dir / 'RUN_MANIFEST.json', {
        'project_id': 'guardsynth-coc', 'status': 'COMPLETE',
        'input_hashes': {str(p.relative_to(ROOT)): d.primary.sha(p) for p in
                         (launch / 'protocol.json', output / 'RUN_MANIFEST.json', protocol / 'RUN_MANIFEST.json')},
        'adapter_source_hashes': manifest['input_hashes'],
        'output_hashes': {p.name: d.primary.sha(p) for p in report_dir.iterdir() if p.is_file()}})
    manifest['status'] = 'COMPLETE'
    d.dump(launch / 'RESULT.json', {'status': 'COMPLETE', 'prediction_rows': result['prediction_rows'],
                                 'analysis_run': cfg['analysis_run'], 'optimizer_updates': 0})
except Exception as exc:
    manifest['status'] = 'FAILED'
    d.dump(launch / 'RESULT.json', {'status': 'FAILED', 'error': str(exc), 'optimizer_updates': 0})
    raise
finally:
    manifest['ended_at_utc'] = datetime.now(timezone.utc).isoformat()
    d.dump(launch / 'RUN_MANIFEST.json', manifest)
