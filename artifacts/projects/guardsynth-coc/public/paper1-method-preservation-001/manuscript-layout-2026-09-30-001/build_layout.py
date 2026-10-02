"""English layout and approved section overviews; existing results are preserved."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys

ROOT = Path('/home/jinhyun/prj_ws/prj_jin/guardsynth-cc')
OUT = Path(__file__).resolve().parent
OLD = OUT.parent / 'manuscript-revision-2026-09-30-001'
PAPER = ROOT / 'projects/04-guardsynth-coc/paper'
assert '--update-current' in sys.argv or not (OUT / 'RESULT.json').exists(), 'Use --update-current only for an explicitly authorized in-place manuscript revision'
OVERVIEWS = {"Related Work":"This section reviews research connecting driving observations, reasoning, and actions, followed by traffic-rule specification and regulation-aware decision making. It then examines natural-language formalization and controlled natural language to clarify how GuardSynth relates to existing approaches.","Background":"This section introduces the established concepts underlying the proposed method. It begins with vision-language models and CoC, then explains satisfiability-based verification, finite temporal bounds, and modeling assumptions, before outlining controlled natural language and low-rank adaptation.","Proposed Method":"This section presents the GuardSynth workflow and defines the elements and semantics of EBLC. It then explains how constraints are derived from CoC, observations, and rules, checked logically, and rendered as CNL for insertion into CoC. Executable examples connect each task to its constraint fields, logical formula, generated text, and evaluation verdict.","Experimental Setup":"This section defines the experimental basis for evaluating behavioral benefits and specification checkability. It introduces the comparison conditions, tasks, and data, then describes the model and training budgets, reference judgments, and evaluation metrics.","Results":"This section compares action-selection accuracy and constraint violations across tasks, then examines responses to changed contracts and the role of correct case-constraint association. It next reports specification and CNL checks, followed by performance under unseen conditions and the scope of the findings.","Discussion":"This section interprets the role of explicit constraints in CoC and the value of formal support for their development. It distinguishes evidence validity, specification and translation correctness, and behavioral compliance, then considers the study's limitations and directions for further development."}
OLD_BACKGROUND = 'This section introduces established concepts needed to understand visual action reasoning and logical specifications: vision--language models and Chain of Causation, satisfiability-based verification, controlled natural language, and low-rank adaptation.'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

protected = list(PAPER.glob('*_KO.md')) + list(OLD.glob('*ko.pdf'))
before = {str(p): sha(p) for p in protected}
for p in OLD.iterdir():
    if p.suffix in ('.cls', '.sty', '.fd', '.map', '.tfm', '.pfb') or p.name in ('logo.png', 'notaglinelogo.png', 'bullet.png'):
        shutil.copyfile(p, OUT / p.name)
source = (PAPER / 'main.tex').read_text()
original = (OLD / 'ieee-access-manuscript-en.tex').read_text()

def captions(text):
    return re.findall(r'\\caption\{([^\n]*)\}', text)

def substantive_lines(text):
    result = []
    for line in text.splitlines():
        if not line or line.startswith('%'):
            continue
        if line in {p + r'\par' for p in OVERVIEWS.values()} | {OLD_BACKGROUND + r'\par'}:
            continue
        if line.startswith(('\\begin{figure', '\\end{figure', '\\includegraphics', '\\centering', '\\begin{tabular', '\\clearpage', '\\newpage')):
            continue
        line = re.sub(r'\\begin\{table\*?\}\[[^]]+\]', '', line)
        if line.startswith(('\\end{table}', '\\end{table*}')):
            continue
        line = line.replace(r'\\[3pt]', r'\\').replace(r'\\[1pt]', r'\\')
        result.append(line)
    return result

assert captions(source) == captions(original), 'Captions changed'
for section, paragraph in OVERVIEWS.items():
    assert source.count(paragraph + r'\par') == 1, section
    assert source.index(paragraph) > source.index(r'\section{' + section + '}')
assert substantive_lines(source) == substantive_lines(original), 'Non-layout content changed'
assert len(captions(source)) == 19
# Preserve the three boundary points, but typeset labels at readable column size.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
figdir = OUT / 'figures'
figdir.mkdir(exist_ok=True)
fig, ax = plt.subplots(figsize=(3.35, 1.13))
fig.subplots_adjust(left=.015, right=.985, top=.98, bottom=.04)
ax.set(xlim=(-1.65, 1.65), ylim=(-.6, 1.05))
ax.axvspan(-1.65, 0, color='#f7e6e4')
ax.axvspan(0, 1.65, color='#e3f1e9')
ax.axvline(0, color='#24754C', ls='--', lw=.8)
ax.hlines(0, -1.45, 1.45, color='#475569', lw=.8)
for x, label, color in [(-1.1, '11.499 s\nUNSAT', '#9b342d'), (0, '11.500 s\nSAT', '#1b5d3b'), (1.1, '11.501 s\nSAT', '#1b5d3b')]:
    ax.scatter(x, 0, s=20, color=color, zorder=3)
    ax.text(x, .10, label, ha='center', va='bottom', fontsize=7.5, color=color)
ax.text(-.84, .96, 'Prohibited: wait incomplete', ha='center', va='top', fontsize=7)
ax.text(.84, .96, 'Admissible: wait completed', ha='center', va='top', fontsize=7)
ax.text(0, -.48, 'Boundary = 11.000 s + 0.500 s', ha='center', fontsize=7.5)
ax.axis('off')
fig.savefig(figdir / 'smt-boundary-en.pdf')
plt.close(fig)
tex = OUT / 'ieee-access-manuscript-en.tex'
tex.write_text(source)
for n in (1, 2):
    p = subprocess.run(['/usr/bin/pdflatex', '-interaction=nonstopmode', '-halt-on-error', tex.name], cwd=OUT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OUT / f'build-en-{n}.log').write_text(p.stdout)
    assert p.returncode == 0, p.stdout[-5000:]
assert before == {str(p): sha(p) for p in protected}, 'Korean files changed'
manifest = {'project_id': 'guardsynth-coc', 'run_id': OUT.name, 'parent_run': OLD.name, 'scope': 'English layout and six approved section overviews; user-requested in-place revision', 'main_tex_sha256': sha(PAPER / 'main.tex'), 'unchanged_korean_sha256': before, 'captions_preserved': 19, 'section_overviews': OVERVIEWS, 'substantive_tex_unchanged_except_overviews': True, 'experiment_results_modified': False}
(OUT / 'RUN_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'build': 'PASS', 'captions_preserved': 19, 'section_overviews': 6, 'other_substantive_content': 'UNCHANGED', 'korean_files': 'UNCHANGED'}))
