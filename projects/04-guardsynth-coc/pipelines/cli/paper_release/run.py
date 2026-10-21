"""Export an allowlisted, frozen public NCA reproducibility distribution.

Owner: guardsynth-coc. Never follows symlinks or exports the working tree wholesale.
Only exported copies are sanitized; original experiment records are preserved.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[5]
PUBLIC = 'projects/04-guardsynth-coc/artifacts/public/'
EXPERIMENTS = 'projects/04-guardsynth-coc/experiments/'
RUNS = [
    'paper1-vlm-constraint-baselines-001/vlm-constraint-baselines-2026-10-12-001',
    'paper1-vlm-constraint-baselines-001/vlm-constraint-baseline-analysis-2026-10-12-001',
    'paper1-learning-specification-faults-001/learning-specification-faults-2026-10-12-001',
    'paper1-constraint-composition-001/document-grounded-composition-2026-10-17-002',
    'paper1-constraint-composition-001/constraint-composition-2026-10-17-001',
    'paper1-position-hold-training-001/position-hold-training-2026-10-08-001',
    'paper1-position-hold-selection-001/position-hold-selection-2026-10-08-002',
]
RUNS += ['paper1-method-preservation-001/' + n for n in (
    'temporal-protocol-2026-09-29-001', 'temporal-training-data-2026-09-29-001',
    'temporal-expansion-protocol-2026-09-29-001', 'temporal-expansion-learning-2026-09-29-001',
    'static-contract-protocol-2026-09-30-003', 'static-contract-learning-2026-09-30-001',
    'maneuver-contract-protocol-2026-09-30-003', 'maneuver-contract-learning-2026-09-30-001',
    'multitask-contract-analysis-2026-09-30-001', 'temporal-secondary-metrics-2026-09-29-001')]
RUNS += ['paper1-temporal-diversity-001/' + n for n in (
    'diversity-protocol-2026-09-29-001', 'diversity-analysis-2026-09-29-001',
    'diversity-inference-2026-09-29-001', 'expanded-diagnostics-analysis-2026-09-30-001',
    'expanded-diagnostics-inference-2026-09-30-001')]
RUNS += ['paper1-reasoning-comparison-001/' + n for n in (
    'reasoning-comparison-2026-10-07-001', 'seven-condition-reasoning-2026-10-07-001')]
SOURCE_GROUPS = {
    EXPERIMENTS + 'paper1_cnl_learning/': (
        'temporal_preservation.py', 'temporal_preservation_config.json',
        'temporal_training_data.py', 'temporal_diversity.py',
        'learning_specification_faults.py', 'learning_specification_faults_protocol_v0_1.json',
        'constraint_composition.py', 'constraint_composition_protocol_v0_1.json',
        'document_grounded_composition.py', 'document_grounded_composition_protocol_v0_1.json'),
    EXPERIMENTS + 'paper1_external_methods/': (
        'run_vlm_constraint_baselines.py', 'vlm_constraint_baselines_protocol_v0_1.json',
        'run_vlm_generation_budget.py', 'run_vlm_batched_diagnostic.py', 'resume_vlm_constraint_baselines.py',
        'run_reasoning_comparison.py', 'reasoning_comparison_protocol_v0_1.json',
        'run_position_hold_selection.py', 'train_position_hold_selection.py',
        'position_hold_training_profile.py', 'build_vlm_constraint_baselines_report.py'),
    'projects/01-safety-constrained-coc/experiments/vlm_guard_learning/': (
        '__init__.py', 'guard_world.py', 'temporal_guard_world.py', 'candidate_guard_world.py',
        'maneuver_guard_world.py', 'train_qwen_guard_lora.py', 'train_qwen_temporal_guard_lora.py'),
    'platforms/eblc-bcv/src/guard_synth_eblc/': (
        '__init__.py', 'core_ir.py', 'schema_validation.py', 'smt_compiler.py',
        'schemas/eblc_core_ir.schema.json'),
    'cli/': ('__init__.py', 'solver_runtime.py', 'project_paths.py'),
    'projects/04-guardsynth-coc/tests/': ('test_learning_specification_faults.py',),
    'projects/04-guardsynth-coc/tests/unit/': (
        'test_constraint_composition.py', 'test_document_grounded_composition.py'),
    'projects/04-guardsynth-coc/pipelines/cli/paper_release/': ('run.py', 'verify.py'),
    'runtime/solvers/': ('z3-5.0.0-x86_64-glibc-2.36/INSTALL_MANIFEST.json',
                        'compat/z3-5.0.0-gcc12/format'),
}
MIT = '''MIT License

Copyright (c) 2026 GuardSynth contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''
DATA_LICENSE = '''Synthetic data and generated experiment records in this distribution
are licensed under Creative Commons Attribution 4.0 International (CC BY 4.0).
Copyright (c) 2026 GuardSynth contributors.

License: https://creativecommons.org/licenses/by/4.0/
Legal code: https://creativecommons.org/licenses/by/4.0/legalcode.en

Attribute the GuardSynth contributors and this release, link to the license,
and indicate modifications. This license does not cover third-party traffic
rules, policy documents, model weights, or source imagery. Source catalogs
provide references and authored abstractions; linked documents keep their
original rights. No restricted PhysicalAI/nuScenes imagery is redistributed.
'''
GUIDE = '''# GuardSynth NCA reproducibility distribution

Owner: `guardsynth-coc`. This frozen source/data distribution accompanies the
NCA manuscript on checked behavioral constraints for CoC-augmented candidate
selection. It preserves project-relative paths and removes host-specific metadata
from exported copies. Original experiment records in the working repository are unchanged.

## Quick verification (Python 3.11, standard library only)

Extract the archive into an empty directory and run from its root:

```sh
python3 projects/04-guardsynth-coc/pipelines/cli/paper_release/verify.py --root .
```

This verifies every manifest SHA-256 and independently recomputes admissibility,
preferred candidates, preferred-selection scores, violation rates and rule-pair
scores from the fresh-adapter and pretrained 2B/8B prediction records. The
historical field `accuracy` means preferred-selection score. Invalid responses
are incorrect and count as neither violations nor admissible choices.
The main 12-token pretrained runs and post-hoc generation-budget records are
kept separate. For example, 2B's 0% violation rate with all invalid answers is
not evidence of compliance.

## Included evidence

- Frozen train/test JSONL, synthetic images, protocols, per-seed predictions,
  and records for the four fresh-adapter conditions and pretrained VLM controls.
- Six-task and position-hold continuation datasets and prediction records,
  paraphrase/unseen-value diagnostics, and the earlier expression-diversity checks.
- Learning-specification fault injection: 384 cases, including 288 supported
  faults, 48 valid controls and 48 jointly wrong source/specification cases.
- Document-grounded authored composition: 176 cases (58 UNSAT, 118 SAT),
  including 12 three-way conflicts with satisfiable pairs. These are authored
  restricted models, not reconstructions or safety certifications of vehicles.
- Selected maintained source dependencies, unchanged Core/SMT implementation,
  schema, solver build provenance, and unit tests.

`SOURCE_MANIFEST.json` is the authority for exactly which files are included,
their public hashes, original-file hashes, relative paths and licenses. Exported
run manifests may reference omitted weights, logs and earlier code versions.
Historical embedded digests remain provenance records; the source manifest is
the authority for hashes of the sanitized distribution. The exported source is the release-time
snapshot, not a claim that every historical source hash matches today's source.
Historical shuffled-rule controls are retained only where embedded in original
aggregate records; they are not a current manuscript claim.

## Rerun the formal checks

The recorded solver is Z3 **5.0.0**, not a generic pip 4.x solver. Build the
upstream `z3-5.0.0` release with Python bindings into the prefix recorded in
`runtime/solvers/z3-5.0.0-x86_64-glibc-2.36/INSTALL_MANIFEST.json`, or set
`GUARDSYNTH_Z3_PREFIX` to an equivalent installation. Its archive hash and GCC12
compatibility-header provenance are included. Solver binaries are excluded.
Install the lightweight dependencies with `python3 -m pip install -r requirements-checks.txt`.
The release's formal rerun was tested with Python 3.12.13, NumPy 2.2.6,
Pillow 12.1.1 and the recorded Z3 build. Then run:

```sh
python3 -m unittest discover -s projects/04-guardsynth-coc/tests -p test_learning_specification_faults.py
python3 -m unittest discover -s projects/04-guardsynth-coc/tests/unit -p 'test_*composition.py'
python3 projects/04-guardsynth-coc/experiments/paper1_cnl_learning/learning_specification_faults.py --run-id learning-specification-faults-reproduction-001
python3 projects/04-guardsynth-coc/experiments/paper1_cnl_learning/document_grounded_composition.py --run-id document-grounded-composition-reproduction-001
```

The runners refuse to overwrite existing runs. Compare the new `RESULT.json`
aggregates to the archived ones. Unit tests are controls; the full runners
exercise all archived-profile cases. The standard-library verifier reads
checker aggregate records; it does not itself execute SMT.

## GPU learning and inference

`run_vlm_constraint_baselines.py --help` documents prepare, fit, pretrained,
and aggregate actions. A new run ID is required. There are 2 tasks × 4 arms ×
3 seeds = 24 fits, with identical initial LoRA tensors per task/seed.
The code expects local model snapshots; download official Hugging Face models:

- `Qwen/Qwen3-VL-2B-Instruct`, revision
  `89644892e4d85e24eaac8bacfd4f463576704203`, at the normal HF cache path.
- `Qwen/Qwen3-VL-8B-Instruct`, revision
  `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`, under the recorded
  `runtime/alpamayo/hf_cache/` snapshot path (or adjust the local model constant).

The available local GPU environment at release time has PyTorch 2.8.0,
Transformers 4.57.1, PEFT 0.20.0 and Matplotlib 3.10.8. These are recorded
for setup guidance, not a new GPU training validation or a complete historical lockfile.
Training scripts preserve their recorded path assumptions.
They are provided for inspection and reproduction; the release validation
does not rerun 24 GPU fits or assert bitwise GPU determinism. Per-run training
metadata records budgets and initialization hashes. Adapter/model weights are excluded.
The selected source supports the fresh-adapter experiments and formal checks;
older six-task/continuation predictions and datasets are included as evidence,
not a promise that every historical launch/scheduler workflow is exported.

## License and boundaries

Original code: **MIT**, `license-code.txt`. Synthetic data and generated
experiment records: **CC BY 4.0**, `license-data.txt`. Third-party references
and dependencies retain their own licenses; the accompanying solver build
manifest and compatibility shim are build provenance, not a Z3 redistribution.
Minimal registry markers and only migration hashes for the exported files are
included for path resolution; the full repository governance catalog is excluded.
These markers are not relicensed as synthetic data. This release grants no blanket license to other
files in the parent monorepo.

Excluded: licensed road imagery/raw Alpamayo inputs, model/adapter weights,
private expert-review submissions, credentials, API-server state and logs,
and unrelated projects/apps. Obtaining original restricted road inputs requires
the original providers' access terms; the Alpamayo diagnostics cannot be
reproduced from this synthetic-data distribution alone.
'''


def selected_files():
    selected = {ROOT / (folder + name) for folder, names in SOURCE_GROUPS.items() for name in names}
    for run in RUNS:
        directory = ROOT / PUBLIC / run
        assert directory.is_dir(), directory
        for path in directory.rglob('*'):
            rel = path.relative_to(directory)
            if path.is_file() and not any(p in ('adapter', '__pycache__') or 'shuffled' in p.lower() for p in rel.parts):
                if path.suffix in ('.json', '.jsonl', '.csv', '.png'):
                    if path.name not in ('scheduling.json', 'execution_recovery.json', 'hold_worker.json',
                                         'temporal_worker.json', 'progress.json', 'training_progress.json'):
                        selected.add(path)
    for path in selected:
        assert path.is_file() and not path.is_symlink(), path
        assert path.stat().st_size < 100 * 1024 * 1024, path
    return sorted(selected)


def scan(path, content):
    if path.suffix not in ('.py', '.json', '.jsonl', '.csv', '.md'):
        return
    for pattern in (rb'gh[pousr]_[A-Za-z0-9]{30,}', rb'github_pat_[A-Za-z0-9_]{40,}',
                    rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----', rb'sk-[A-Za-z0-9]{40,}'):
        if re.search(pattern, content):
            raise ValueError(f'Potential credential in {path}; export stopped')


def sanitize(content):
    """Remove concrete host locations/identifiers without changing measurements."""
    text = content.decode()
    text = text.replace(str(ROOT) + '/', '')
    text = text.replace(str(ROOT), 'REPOSITORY_ROOT')
    # JSON strings, quoted shell snippets and plain metadata may contain home paths.
    text = re.sub(r'/home/[A-Za-z0-9_.-]+(?:/[^\s"\x27<>),;\]}]+)?', 'LOCAL_PATH_REMOVED', text)
    text = re.sub(r'GPU-[0-9a-fA-F-]{20,}', 'GPU_ID_REMOVED', text)
    return text.encode()


def run(run_id):
    target = ROOT / PUBLIC / 'paper1-reproducibility-release-001' / run_id
    target.mkdir(parents=True, exist_ok=False)
    payload, items = {}, []
    for path in selected_files():
        name = path.relative_to(ROOT).as_posix()
        original = path.read_bytes()
        data = sanitize(original) if path.suffix in ('.json', '.jsonl', '.csv', '.py', '.md') else original
        scan(path, data)
        payload[name] = data
        license_name = 'MIT' if path.suffix == '.py' or name.endswith('/format') or '/schemas/' in name or '/experiments/' in name else 'CC-BY-4.0'
        if name in ('PROJECT_REGISTRY.json', 'PROJECT_STRUCTURE.md', 'docs/architecture/ARTIFACT_MIGRATION.json') or name.endswith('INSTALL_MANIFEST.json'):
            license_name = 'provenance-reference-not-relicensed'
        items.append(dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                          source_sha256=hashlib.sha256(original).hexdigest(),
                          sanitized=data != original, license=license_name))
    registry = json.loads((ROOT / 'PROJECT_REGISTRY.json').read_text())
    selected_projects = [p for p in registry['projects'] if p['id'] in ('guardsynth-coc', 'safety-constrained-coc')]
    minimal = {'projects': [{k: p[k] for k in ('id', 'path', 'artifact_root')} for p in selected_projects],
               'platforms': [{'id': 'eblc-bcv', 'path': 'platforms/eblc-bcv', 'artifact_root': 'platforms/eblc-bcv/artifacts'}]}
    migration = json.loads((ROOT / 'docs/architecture/ARTIFACT_MIGRATION.json').read_text())
    rewritten = [{k: row[k] for k in ('path', 'before_sha256', 'after_sha256')}
                 for row in migration['rewritten_files'] if row['path'] in payload]
    generated = {'PROJECT_REGISTRY.json': json.dumps(minimal, indent=2) + '\n',
                 'PROJECT_STRUCTURE.md': '# Frozen GuardSynth NCA distribution\n\nOwner: guardsynth-coc. Retains original project/platform paths. See README.md.\n',
                 'docs/architecture/ARTIFACT_MIGRATION.json': json.dumps({'rewritten_files': rewritten}, indent=2) + '\n'}
    for name, text in generated.items():
        data = text.encode()
        payload[name] = data
        items.append(dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                          license='provenance-reference-not-relicensed', origin='minimal-public-path-metadata'))
    manifest = dict(project_id='guardsynth-coc', task_id='nca-public-reproducibility',
                    source_policy='explicit allowlist; sanitized release-time snapshot; original records unchanged', files=items)
    payload['SOURCE_MANIFEST.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    payload['README.md'] = GUIDE.encode()
    payload['license-code.txt'] = MIT.encode()
    payload['license-data.txt'] = DATA_LICENSE.encode()
    payload['requirements-checks.txt'] = b'numpy==2.2.6\nPillow==12.1.1\n'
    # Marker required by cli.project_paths; no maintained implementation copied here.
    payload['src/.release-marker'] = b'Compatibility-root marker for frozen scripts.\n'
    archive = target / ('guardsynth-nca-reproducibility-' + run_id.removeprefix('github-release-') + '.tar.gz')
    with archive.open('wb') as stream, gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as tar:
            for name, data in sorted(payload.items()):
                info = tarfile.TarInfo('guardsynth-nca/' + name)
                info.size, info.mode, info.mtime = len(data), 0o644, 0
                tar.addfile(info, io.BytesIO(data))
    (target / 'SOURCE_MANIFEST.json').write_bytes(payload['SOURCE_MANIFEST.json'])
    (target / 'license-code.txt').write_text(MIT)
    (target / 'license-data.txt').write_text(DATA_LICENSE)
    (target / 'README.md').write_text('''# GuardSynth NCA public release

Owner: `guardsynth-coc`. Status: packaged locally; validation and PR status are in `RESULT.json`.

Download and extract [the reproducibility archive](ARCHIVE_FILENAME).
The included README explains metric recomputation, formal-check reruns, model prerequisites,
excluded restricted inputs and license boundaries. [File manifest](SOURCE_MANIFEST.json).
Code: [MIT](license-code.txt). Synthetic data/records: [CC BY 4.0](license-data.txt).

This is a frozen distribution, not a second maintained source tree. Source paths inside
the archive retain the project's original layout. The archive contains no model weights,
licensed road imagery, API credentials or server state. A GitHub PR must be merged before
this release is available on the original repository's default branch.
Host-specific home paths and GPU identifiers have been removed from exported copies.
The file manifest records both original and public hashes; original experiment records remain unchanged.
'''.replace('ARCHIVE_FILENAME', archive.name))
    metadata = dict(project_id='guardsynth-coc', task_id='nca-public-reproducibility',
                    run_id=run_id, status='PACKAGED', created_at=datetime.now(timezone.utc).isoformat(),
                    inputs=[str(p.relative_to(ROOT)) for p in selected_files()],
                    archive=archive.name, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                    source_files=len(items), uncompressed_bytes=sum(i['bytes'] for i in items),
                    compressed_bytes=archive.stat().st_size,
                    code_license='MIT', synthetic_data_license='CC-BY-4.0')
    for name in ('RUN_MANIFEST.json', 'RESULT.json'):
        (target / name).write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({k: v for k, v in metadata.items() if k != 'inputs'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    run(parser.parse_args().run_id)
