"""Disjoint synthetic training expansion with executable EBLC action tests.

This expands numeric/candidate templates, not road-scene diversity. The frozen
original experiment and its generator are read-only inputs.
"""
import argparse
from collections import Counter
from dataclasses import asdict, replace
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

import temporal_preservation as t
from guard_synth_eblc.smt_compiler import solve_assignment

VERSION = 'temporal-training-expansion-v0.1'
SPLITS = {'train': (60, 100), 'validation': (100, 110), 'test': (110, 120)}
DURATIONS = (500, 1500)
PATTERNS = ((-500, 500, 1500), (400, 600, 1600), (500, 1400, 1500))
ORIGINAL = t.BASE / 'temporal-protocol-2026-09-29-001'


@lru_cache(maxsize=2)
def compiled(duration_ms):
    return t.compile_core_model(t.parse_core_model(t.lower(t.contract(duration_ms / 1000))))


@lru_cache(maxsize=None)
def action_test(duration_ms, clear_ms, entry_ms):
    """Bind a chosen action, not its reference label, to the executable gate."""
    result = solve_assignment(compiled(duration_ms), {
        ('clear_ms', None): clear_ms,
        ('entry_ms', None): entry_ms if entry_ms is not None else 0,
        ('enters', None): entry_ms is not None,
    })
    return result['status']


def records(split):
    start, stop = SPLITS[split]
    for tick in range(start, stop):
        for pattern_id, offsets in enumerate(PATTERNS):
            for rotation in range(4):
                labels = t.world.LABELS[rotation:] + t.world.LABELS[:rotation]
                clear_ms = tick * 100
                candidates = tuple(t.world.TemporalCandidate(label, entry, progress, role)
                    for label, entry, progress, role in zip(labels,
                        [(clear_ms + offset) / 1000 for offset in offsets] + [None],
                        [110., 100., 85., 0.],
                        ['premature', 'short_wait', 'long_wait', 'deadlock']))
                scene = t.world.TemporalScene(tick * 100 + pattern_id * 4 + rotation,
                                             tick / 10, 0, candidates)
                for duration_ms, level in zip(DURATIONS, ('short', 'long')):
                    # Independent integer reference; no renderer or solver result used.
                    allowed = [c for c in candidates if c.entry_time is None or
                               round(c.entry_time * 1000) - clear_ms >= duration_ms]
                    target = max(allowed, key=lambda c: c.progress).label
                    raw = t.contract(duration_ms / 1000)
                    guard = t.world._guard(duration_ms / 1000, False)
                    example = t.world.TemporalExample(scene, duration_ms / 1000, level,
                        guard, t.world.COC_TEXT + ' ' + guard, '', target, split)
                    cnl = t.render(raw)
                    prompts = {
                        'P0': t.world.prompt_for(example, 'COC_ONLY'),
                        'P1': t.world.prompt_for(example, 'RICH_COC'),
                        'P2': t.world.prompt_for(replace(example,
                            rich_coc_text=t.world.COC_TEXT + ' ' + cnl), 'RICH_COC'),
                    }
                    tests = {}
                    for c in candidates:
                        entry_ms = None if c.entry_time is None else round(c.entry_time * 1000)
                        status = action_test(duration_ms, clear_ms, entry_ms)
                        expected = 'SAT' if c in allowed else 'UNSAT'
                        if status != expected:
                            raise ValueError('EBLC/environment disagreement or UNKNOWN')
                        tests[c.label] = {'entry_ms': entry_ms, 'enters': entry_ms is not None,
                                         'eblc_status': status, 'environment_expected': expected}
                    yield {'id': f'{split}-{scene.scene_id}-{duration_ms}', 'split': split,
                           'scene': asdict(scene), 'semantic_group': f'clear-{clear_ms}',
                           'pattern_id': pattern_id, 'rotation': rotation,
                           'required_clear_ms': duration_ms, 'contract_level': level,
                           'contract': raw, 'cnl': cnl, 'guard': guard, 'prompts': prompts,
                           'reference_action': target, 'action_tests': tests,
                           'reference_kind': 'INDEPENDENT_PROGRAM_ENVIRONMENT_RULE',
                           'source_kind': 'SUPPLIED_SYNTHETIC_NOT_ROAD_OBSERVATION'}


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def prepare(output):
    if output.exists():
        raise FileExistsError(output)
    original_manifest = json.loads((ORIGINAL / 'RUN_MANIFEST.json').read_text())
    for name, digest in original_manifest['output_hashes'].items():
        if t.sha(ORIGINAL / name) != digest:
            raise ValueError('original protocol output drift')
    old_images = {json.loads(line)['image_pixel_sha256'] for line in
                  (ORIGINAL / 'paired_dataset.jsonl').read_text().splitlines()}
    output.mkdir(parents=True)
    (output / 'images').mkdir()
    dump(output / 'protocol.json', {
        'version': VERSION, 'project_id': 'guardsynth-coc', 'split_clear_tenths': SPLITS,
        'durations_ms': DURATIONS, 'candidate_offsets_ms': PATTERNS, 'label_rotations': 4,
        'arms': ['P0', 'P1', 'P2'], 'source': 'DETERMINISTIC_SUPPLIED_SYNTHETIC_WORLD',
        'evaluation_use': 'FRESH_HELDOUT_FOR_NEW_TRAINING_NOT_PRIOR_CONFIRMATION',
        'training_updates': 0, 'prior_exposed_evaluation_used_for_training': False,
        'assumption': 'SINGLE_CLEAR_TRANSITION_NO_REOCCUPATION',
        'limitations': ['Numeric/template diversity, not new physical environments.',
                       'P0 lacks duration input; paired contracts can have conflicting P0 targets.',
                       'Progress and candidate times may permit text shortcuts.',
                       'Reference and EBLC share supplied world assumptions, not implementation.'],
    })
    dump(output / 'contracts.json', {str(d): {'eblc': t.contract(d / 1000),
        'core': t.lower(t.contract(d / 1000)), 'cnl': t.render(t.contract(d / 1000))} for d in DURATIONS})
    counts, image_sets, summaries = {}, {}, {}
    total_bindings = 0
    for split in SPLITS:
        rows = list(records(split))
        image_sets[split] = set()
        rendered = {}
        for row in rows:
            clear = round(row['scene']['clear_time'] * 1000)
            if clear not in rendered:
                scene = t.world.TemporalScene(**{**row['scene'], 'candidates': ()})
                image = t.world.render_storyboard(scene)
                pixel_hash = hashlib.sha256(image.tobytes()).hexdigest()
                path = f'images/clear_{clear}.png'
                image.save(output / path)
                rendered[clear] = (path, pixel_hash)
            row['image'], row['image_pixel_sha256'] = rendered[clear]
            image_sets[split].add(row['image_pixel_sha256'])
            total_bindings += len(row['action_tests'])
        if image_sets[split] & old_images:
            raise ValueError('overlap with prior training/evaluation pixels')
        for other in image_sets:
            if other != split and image_sets[split] & image_sets[other]:
                raise ValueError('cross-split pixel leakage')
        with (output / f'{split}_paired.jsonl').open('w') as stream:
            for row in rows:
                stream.write(json.dumps(row) + '\n')
        for arm in ('P0', 'P1', 'P2'):
            with (output / f'{split}_{arm.lower()}.jsonl').open('w') as stream:
                for row in rows:
                    # Reference and tests are metadata outside the model prompt.
                    exported = {k: row[k] for k in ('id', 'split', 'image', 'image_pixel_sha256',
                                                    'reference_kind', 'semantic_group')}
                    exported.update(arm=arm, prompt=row['prompts'][arm],
                                    response=row['reference_action'])
                    stream.write(json.dumps(exported) + '\n')
        counts[split] = len(rows)
        summaries[split] = {'paired_rows': len(rows), 'rows_per_arm': len(rows),
            'unique_images': len(image_sets[split]), 'scene_candidate_sets': len(rows) // 2,
            'label_counts': dict(Counter(r['reference_action'] for r in rows)),
            'unique_model_inputs': {arm: len({(r['image_pixel_sha256'], r['prompts'][arm])
                                           for r in rows}) for arm in ('P0', 'P1', 'P2')}}
    result = {'status': 'DATA_READY_NOT_TRAINED', 'version': VERSION, 'splits': summaries,
        'paired_rows': sum(counts.values()), 'arm_rows': sum(counts.values()) * 3,
        'unique_storyboards': len(set.union(*image_sets.values())),
        'prior_pixel_overlap': 0, 'cross_split_pixel_overlap': 0,
        'action_bindings_checked': total_bindings,
        'distinct_smt_assignments': action_test.cache_info().currsize,
        'eblc_environment_disagreements': 0, 'optimizer_updates': 0}
    dump(output / 'RESULT.json', result)
    (output / 'REPORT_KO.md').write_text(
        '# 추가 학습 실험 데이터\n\n'
        '- 상태: 데이터 생성·EBLC 행동 판정 대조 완료. 추가 학습은 아직 실행하지 않음.\n'
        f'- 학습 {counts["train"]} / 검증 {counts["validation"]} / 시험 {counts["test"]}건, '
        '각각 P0/P1/P2 대응.\n'
        f'- 실제 고유 합성 이미지 {result["unique_storyboards"]}장. 숫자·후보 변형이며 실제 도로 장면이 아님.\n'
        '- 학습 6.0–9.9초, 검증 10.0–10.9초, 시험 11.0–11.9초에 영역이 비워지는 설정.\n'
        '- 대기시간 0.5/1.5초, 진입 후보 3패턴, 라벨 회전 4개. 경계는 표시 가능한 0.1초 단위.\n'
        '- 원 실험 이미지 및 분할 간 이미지 중복 0. 같은 영상의 파생 계약·후보는 같은 분할 유지.\n'
        '- 각 후보를 EBLC→Core→Z3에 바인딩해 독립 정수 환경 판정과 대조. '
        'SAT는 주어진 조건의 제약 준수이며 사실성·실차 안전성 보증이 아님.\n'
        '- 최대 정상 진행 후보를 참조로 선택하므로 정지만 하는 답을 최적 답으로 처리하지 않음.\n'
        '- P0는 계약 대기시간을 제공받지 않아 동일 입력에 다른 정답이 있을 수 있음. '
        '영상 없이 후보·진행값만으로 풀 수 있는 단서와 단일 전환 가정도 한계로 유지.\n'
        '- 기존 9개 checkpoint 결과에 합산하지 않음. 새 학습은 동일 예산·seed를 별도 동결한 뒤 실행.\n')
    sources = [Path(__file__), Path(t.__file__), t.PRIOR / 'vlm_guard_learning/temporal_guard_world.py',
               Path(t.compile_core_model.__code__.co_filename), ORIGINAL / 'RUN_MANIFEST.json']
    dump(output / 'RUN_MANIFEST.json', {'project_id': 'guardsynth-coc', 'status': 'COMPLETE',
        'input_hashes': {str(p.relative_to(t.ROOT)): t.sha(p) for p in sources},
        'output_hashes': {str(p.relative_to(output)): t.sha(p) for p in output.rglob('*') if p.is_file()}})
    return result


def load_examples(output, split, arm):
    """Use the existing visual collator without regenerating rows from old seeds."""
    if split not in SPLITS or arm not in ('P0', 'P1', 'P2'):
        raise ValueError('unknown split/arm')
    manifest = json.loads((output / 'RUN_MANIFEST.json').read_text())
    path = output / f'{split}_paired.jsonl'
    if t.sha(path) != manifest['output_hashes'][path.name]:
        raise ValueError('dataset drift')
    examples = []
    for line in path.read_text().splitlines():
        row = json.loads(line)
        scene = t.world.TemporalScene(**{**row['scene'], 'candidates': tuple(
            t.world.TemporalCandidate(**c) for c in row['scene']['candidates'])})
        text = row['cnl'] if arm == 'P2' else row['guard']
        example = t.world.TemporalExample(scene, row['required_clear_ms'] / 1000,
            row['contract_level'], row['guard'], t.world.COC_TEXT + ' ' + text, '',
            row['reference_action'], split)
        mode = 'COC_ONLY' if arm == 'P0' else 'RICH_COC'
        if t.world.prompt_for(example, mode) != row['prompts'][arm]:
            raise ValueError('loader prompt drift')
        digest = hashlib.sha256(t.world.render_storyboard(scene).tobytes()).hexdigest()
        if digest != row['image_pixel_sha256']:
            raise ValueError('loader image drift')
        examples.append(example)
    return examples


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'temporal-training-data-\d{4}-\d{2}-\d{2}-\d{3}', args.run_id):
        parser.error('use temporal-training-data-YYYY-MM-DD-NNN')
    print(json.dumps(prepare(t.BASE / args.run_id), indent=2))
