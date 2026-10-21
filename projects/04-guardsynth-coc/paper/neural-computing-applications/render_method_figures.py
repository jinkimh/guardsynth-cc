"""Method figures for the Neural Computing and Applications draft.

Owner: guardsynth-coc. Figure 1 is a process diagram; Figure 2 reproduces two
archived model inputs verbatim. No model outputs or measured results are plotted.
Run from any directory with a Python that has matplotlib and Pillow.
"""
from pathlib import Path
import json
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p/'PROJECT_REGISTRY.json').exists())
PUBLIC = ROOT/'projects/04-guardsynth-coc/artifacts/public'
TEMPORAL = PUBLIC/'paper1-method-preservation-001/temporal-training-data-2026-09-29-001'
HOLD = PUBLIC/'paper1-position-hold-training-001/position-hold-training-2026-10-08-001'
FIG = HERE/'figures'
FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'pdf.fonttype': 42})
INK, BLUE, GREEN, CNL = '#173E59', '#E7F0F7', '#E3F2EA', '#1F7A4D'


def save(fig, name):
    for ext in ('pdf', 'png'):
        fig.savefig(FIG/f'{name}.{ext}', dpi=200, bbox_inches='tight', pad_inches=.05)
    plt.close(fig)


def box(ax, x, y, w, h, s, color=BLUE, size=8.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=.06',
                                facecolor=color, edgecolor=INK, linewidth=.8))
    ax.text(x+w/2, y+h/2, s, ha='center', va='center', color=INK, fontsize=size)


def line(ax, points, dashed=False, tip=True):
    xs, ys = zip(*points)
    ax.plot(xs, ys, color=INK, lw=.85, ls='--' if dashed else '-')
    if tip:
        ax.add_patch(FancyArrowPatch(points[-2], points[-1], arrowstyle='-|>', mutation_scale=9,
                                     lw=.85, color=INK, shrinkA=0, shrinkB=0,
                                     linestyle='--' if dashed else '-'))


def method_flow():
    # Drawn at the journal text width (372 pt) so that it is included at 100 %.
    fig, ax = plt.subplots(figsize=(5.15, 2.55))
    ax.set(xlim=(0, 12), ylim=(0, 5.6)); ax.axis('off')
    inputs = ['Original CoC', 'Observations', 'Supplied rules', 'Modeling\nassumptions']
    stages = ['01 Construct\nconstraint,\nbind evidence', '02 Specify\nin EBLC',
              '03 Check:\nstructure, evidence\nconsistency\nlogic\u2013rule', '04 Generate\nCNL, parse-back\ncheck, append']
    xs = (.2, 3.2, 6.2, 9.2)
    for x, s in zip(xs, inputs):
        box(ax, x, 4.5, 2.6, .9, s, size=7)
        line(ax, [(x+1.3, 4.5), (x+1.3, 4.05)], tip=False)
    line(ax, [(1.5, 4.05), (10.5, 4.05)], tip=False)
    line(ax, [(1.5, 4.05), (1.5, 3.6)])
    for x, s in zip(xs, stages):
        box(ax, x, 2.1, 2.6, 1.5, s, GREEN if x == 9.2 else BLUE, size=6.5)
    for x in (2.8, 5.8, 8.8):
        line(ax, [(x, 2.85), (x+.4, 2.85)])
    line(ax, [(7.5, 2.1), (7.5, 1.55), (4.5, 1.55), (4.5, 2.1)], dashed=True)
    line(ax, [(10.5, 2.1), (10.5, 1.55), (7.5, 1.55)], dashed=True, tip=False)
    ax.text(7.5, 1.1, 'Unexpected verdict, UNKNOWN,\nor parse mismatch \u2192 review',
            ha='center', va='center', color=INK, fontsize=6.5)
    ax.text(1.5, 1.35, 'Synthetic: supplied inputs\nReal: human confirmation',
            ha='center', va='center', color=INK, fontsize=6.5)
    ax.text(6, .25, 'Solid: processing order   \u00b7   Dashed: return for review',
            ha='center', va='center', color=INK, fontsize=6.5)
    save(fig, 'method-flow')


def prompt_lines(prompt, cnl, width):
    """Wrap a verbatim prompt; the CNL clause starts its own colored line."""
    out = []
    for raw in prompt.split('\n'):
        parts = raw.split(cnl) if cnl in raw else [raw]
        for i, part in enumerate(parts):
            if part.strip():
                out += [(w, INK) for w in textwrap.wrap(part.strip(), width)]
            if i < len(parts)-1:
                out += [(w, CNL) for w in textwrap.wrap(cnl, width)]
    return out


def input_examples():
    temporal = next(json.loads(l) for l in open(TEMPORAL/'test_p2.jsonl')
                    if json.loads(l)['id'] == 'test-11000-500')
    hold = next(r for r in map(json.loads, open(HOLD/'test.jsonl'))
                if r['id'] == 'test-000-0-2000-interval_maxima')
    hold_cnl = hold['prompts']['p2'].split('Constraint: ')[1].split('\n')[0]
    temporal_cnl = temporal['prompt'].split('intersection. ')[1].split('\n')[0]
    panels = [('(a) Pedestrian clearance, 0.5 s rule', TEMPORAL/temporal['image'],
               temporal['prompt'], temporal_cnl, temporal['response']),
              ('(b) Position hold, 2.0 s rule, interval-maximum representation', HOLD/hold['image'],
               hold['prompts']['p2'], hold_cnl, hold['target'])]
    # Drawn at the journal text width (372 pt) so that text keeps its size.
    height = 4.4
    fig = plt.figure(figsize=(5.15, height))
    step = .1/height  # one 6.2 pt text line in figure fractions
    rows = ((.99, .352), (.59, .534))  # (top, height) of each panel in figure fractions
    for (top, height), (title, image, prompt, cnl, answer) in zip(rows, panels):
        fig.text(0, top, title, ha='left', va='top', fontsize=7.5, color=INK)
        img = fig.add_axes((0, top-.035-height*.55, .26, height*.55))
        img.imshow(Image.open(image)); img.axis('off'); img.set_anchor('NW')
        txt = fig.add_axes((.28, top-.035-height, .72, height)); txt.axis('off')
        lines = prompt_lines(prompt, cnl, 70) + [(f'Reference label: {answer}', INK)]
        for i, (s, color) in enumerate(lines):
            txt.text(0, 1-i*step/height, s, va='top', ha='left', fontsize=6.2, color=color,
                     family='DejaVu Sans Mono', fontweight='bold' if color == CNL else 'normal')
    save(fig, 'input-examples')


method_flow()
input_examples()
