"""Generate this Korean main/supplement snapshot from maintained Markdown and frozen results.
Owner: guardsynth-coc. No training, no changes to source experiments.
"""
from pathlib import Path
import csv, hashlib, json, os, re, shutil, statistics, subprocess, sys
ROOT = Path("/home/jinhyun/prj_ws/prj_jin/guardsynth-cc")
BASE = ROOT / "artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001"
OUT = Path(__file__).resolve().parent
assert not (OUT / "RESULT.json").exists(), "Completed snapshots are immutable"
ADDITIONAL = ROOT.parent / "guardsynth-cc-worktrees/guardsynth-additional-20260930/artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001"
MULTI = ADDITIONAL / "multitask-contract-analysis-2026-09-30-001/metrics.csv"
TEMP = BASE / "temporal-experiment-closure-2026-09-29-001/all_primary_metrics.csv"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)
multi = list(csv.DictReader(MULTI.open()))
temporal = list(csv.DictReader(TEMP.open()))
shutil.copyfile(MULTI, OUT / "multitask_metrics.csv")
shutil.copyfile(TEMP, OUT / "temporal_metrics.csv")
seeds = (42, 17, 123)
arms = ("P0", "P1", "P2")
def values(task, subtype, arm, metric, split="test"):
    if task == "temporal":
        key = {"violation_rate":"guard_violation_rate", "pair_accuracy":"contract_swap_pair_accuracy"}.get(metric, metric)
        if split == "unseen": split = "unseen_duration"
        row, = [r for r in temporal if r["experiment"]=="expansion" and r["split"]==split and r["arm"]==arm and r["metric"]==key]
        return [100*float(row[f"seed{s}"]) for s in seeds]
    rs = {int(r["seed"]):r for r in multi if r["task"]==task and r["subtype"]==subtype and r["split"]==split and r["arm"]==arm}
    assert set(rs)==set(seeds), (task,subtype,arm,metric,split)
    return [100*float(rs[s][metric]) for s in seeds]
def avg(*args): return statistics.mean(values(*args))
subtypes = sorted({r["subtype"] for r in multi})
print("subtypes", subtypes)
tasks = [("static","max_speed","최고속도"),("static","min_clearance","최소거리"),
         ("static","min_entry_delay","진입시간"),("temporal","all","시간 대기"),
         ("maneuver","cruise_stop","정지"),("maneuver","lane_change","차선 변경")]
# Source-backed check of every primary and unseen table cell before rendering.
source = ROOT / "projects/04-guardsynth-coc/paper/IEEE_ACCESS_EXPERIMENTS_V01_KO.md"
md = source.read_text()
checks = []
for task,subtype,label in tasks:
    line = "| " + {"최고속도":"최고속도 제한","최소거리":"최소거리 확보","진입시간":"최소 진입시간","시간 대기":"시간 대기 후 진입","정지":"정지 행동"}.get(label,label) + " | "
    line += " | ".join(f"{avg(task,subtype,a,'accuracy'):.2f} / {avg(task,subtype,a,'violation_rate'):.2f}" for a in arms)+" |"
    assert line in md, line
    checks.append(line)
for task,label in (("temporal","시간"),("static","정적"),("maneuver","기동")):
    line = "| "+label+" | "+" | ".join(f"{avg(task,'all',a,'accuracy','unseen'):.2f} / {avg(task,'all',a,'violation_rate','unseen'):.2f}" for a in arms)+" |"
    assert line in md,line
    checks.append(line)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
font=FontProperties(fname="/home/jinhyun/.local/share/fonts/NotoSansCJK-Regular.ttc")
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,"pdf.fonttype":3})
colors={"P0":"#64748B","P1":"#C57927","P2":"#167D8D","SHUFFLED_GUARD":"#AC5665"}
def save(fig,name):
    for ext in ("pdf","png"):
        fig.savefig(FIG / f"{name}-ko.{ext}",bbox_inches="tight",pad_inches=.08,dpi=170)
    plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(8.5,3.3))
fig.subplots_adjust(left=.07,right=.98,bottom=.24,top=.88,wspace=.27)
for ax,metric,title in zip(axes,("accuracy","violation_rate"),("정확도 (%) ↑","위반율 (%) ↓")):
    for idx,arm in enumerate(arms):
        for j,(task,subtype,label) in enumerate(tasks):
            x=j+(idx-1)*.23
            vs=values(task,subtype,arm,metric)
            ax.scatter([x-.045,x,x+.045],vs,s=15,facecolors="white",edgecolors=colors[arm],zorder=3)
            ax.scatter(x,statistics.mean(vs),s=35,marker="D",color=colors[arm],label=arm if j==0 else None,zorder=4)
    ax.set_xticks(range(6),[t[2] for t in tasks],fontproperties=font,fontsize=9)
    ax.set_title(title,fontproperties=font)
    ax.set_ylim((-3,105) if metric=="accuracy" else (-1,52))
    ax.grid(axis="y",alpha=.18)
fig.legend(*axes[0].get_legend_handles_labels(),loc="lower center",ncol=3,frameon=False)
save(fig,"task-performance")
fig,axes=plt.subplots(1,2,figsize=(8.5,2.6))
fig.subplots_adjust(left=.07,right=.98,bottom=.28,top=.85,wspace=.3)
families=("temporal","static","maneuver")
for ax,metric,title,conditions in [(axes[0],"pair_accuracy","契約",arms),(axes[1],"accuracy","교란",("P2","SHUFFLED_GUARD"))]:
    for idx,arm in enumerate(conditions):
        xs=[i+(idx-(len(conditions)-1)/2)*.21 for i in range(3)]
        ax.scatter(xs,[avg(t,"all",arm,metric) for t in families],s=42,color=colors[arm],marker="D",
                   label="연결 교란" if arm=="SHUFFLED_GUARD" else arm)
    ax.set_xticks(range(3),["시간","정적","기동"],fontproperties=font)
    ax.set_ylim(-4,105);ax.grid(axis="y",alpha=.18)
    ax.set_title("계약쌍 정확도 (%)" if metric=="pair_accuracy" else "정상 연결 / 학습 연결 교란 정확도 (%)",fontproperties=font,fontsize=10)
    ax.legend(loc="lower center",bbox_to_anchor=(.5,-.39),ncol=3,prop=font,frameon=False,fontsize=9)
save(fig,"contract-linkage")
fig,ax=plt.subplots(figsize=(8.5,1.55))
ax.set_xlim(-1.6,1.6);ax.set_ylim(-.6,1.4)
ax.axvspan(-1.6,0,color="#F8E5E1");ax.axvspan(0,1.6,color="#E3F2EA")
ax.axvline(0,color="#24754C",ls="--",lw=1)
ax.hlines(0,-1.4,1.4,color="#475569",lw=1)
for x,txt,color in [(-1,"11.499 s\nUNSAT","#B44C42"),(0,"11.500 s\nSAT","#24754C"),(1,"11.501 s\nSAT","#24754C")]:
    ax.scatter(x,0,s=48,color=color,zorder=3)
    ax.text(x,.25,txt,ha="center",va="bottom",fontsize=10,color=color)
ax.text(-.8,1.05,"금지: 요구 대기 미완료",fontproperties=font,ha="center",fontsize=10)
ax.text(.8,1.05,"허용: 요구 대기 충족",fontproperties=font,ha="center",fontsize=10)
ax.text(0,-.4,"허용 경계 = 11.000 s + 0.500 s",fontproperties=font,ha="center",fontsize=10)
ax.axis("off");save(fig,"smt-boundary")
# Reuse the established Markdown/TeX renderer, adapting only source/output selection,
# counts and numeric table widths. Generated TeX is independently rebuildable.
builder = ROOT / "projects/04-guardsynth-coc/paper/render_experiments.py"
text=builder.read_text()
text=text[:text.index("(OUT/'RUN_MANIFEST.json')")]
text=re.sub(r"ROOT = next[^\n]+",f"ROOT = Path({str(ROOT)!r})",text,count=1)
text=re.sub(r"OUT = ROOT/[^\n]+",f"OUT = Path({str(OUT)!r})",text,count=1)
text=text.replace("for lang in ('ko','en'):","for document in ('supplement', 'main'):\n    lang = 'ko'")
text=text.replace("source=ROOT/f'projects/04-guardsynth-coc/paper/IEEE_ACCESS_EXPERIMENTS_V01_{lang.upper()}.md'",
"""source=ROOT/('projects/04-guardsynth-coc/paper/IEEE_ACCESS_EXPERIMENTS_SUPPLEMENT_V01_KO.md' if document=='supplement' else 'projects/04-guardsynth-coc/paper/IEEE_ACCESS_EXPERIMENTS_V01_KO.md')""")
text=text.replace("stem=f'ieee-access-experiments-v01-{lang}'","stem='ieee-access-experiments-supplement-v01-ko' if document=='supplement' else 'ieee-access-experiments-v01-ko'")
text=text.replace("assert (figures,boxes,tables)==(4,0,7)","assert (figures,boxes,tables)==((4,0,11) if document=='supplement' else (3,0,4)), (document,figures,boxes,tables)")
text=text.replace("4:[.26,.16,.24,.34]","4:[.28,.24,.24,.24]")
text=text.replace("3:[.23,.38,.39]","3:[.23,.30,.47]")
text=text.replace("parts=[PREAMBLE];", "parts=[PREAMBLE.replace('{6pt}','{4pt}') if document=='main' else PREAMBLE];")
text=text.replace("tex.write_text('\\n'.join(parts))", "tex.write_text('\\n'.join(parts).replace(r'\\medskip',r'\\smallskip') if document=='main' else '\\n'.join(parts))")
text=text.replace("if line.startswith('## '):","if line.startswith('## '):\n            if evidence_group:\n                parts.append(r'\\endgroup'); evidence_group=False")
text=text.replace("if line.startswith('## '):", "if line.startswith('## '):\n            if document=='main' and line.startswith('## D.'):\n                parts.append(r'\\newpage')")
scope={"__file__":str(builder)}
exec(compile(text,str(builder),"exec"),scope)
records=scope["records"]
for name in ("IEEE_ACCESS_EXPERIMENTS_V01_KO.md","IEEE_ACCESS_EXPERIMENTS_SUPPLEMENT_V01_KO.md"):
    shutil.copyfile(ROOT/"projects/04-guardsynth-coc/paper"/name,OUT/name)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
sources=[MULTI,TEMP,builder,Path(__file__),source,
 ROOT/"projects/04-guardsynth-coc/paper/IEEE_ACCESS_EXPERIMENTS_SUPPLEMENT_V01_KO.md",
 BASE/"experiments-section-2026-09-30-002/unsat_review.json",
 ROOT/"artifacts/projects/guardsynth-coc/public/paper1-temporal-diversity-001/expanded-diagnostics-analysis-2026-09-30-001/RESULT.json"]
manifest={"project_id":"guardsynth-coc","run_id":OUT.name,"prior_snapshot":"experiments-section-2026-09-30-002",
 "purpose":"Compact Korean experiment section and separate comprehensive supplement; no new training",
 "source_sha256":{str(p):sha(p) for p in sources},"documents":records,
 "main_tex_modified":False,"english_revision":"unchanged; this run updates Korean only",
 "reproduce":"Run this build_snapshot.py with runtime/alpamayo/ar1_venv/bin/python before RESULT.json; each generated .tex compiles independently twice with XeLaTeX."}
(OUT/"RUN_MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
(OUT/"content_checks.json").write_text(json.dumps({"primary_and_unseen_rows_checked":checks,"original_runs_modified":False},ensure_ascii=False,indent=2)+"\n")
print("PDF builds complete; layout inspection and finalization pending")
