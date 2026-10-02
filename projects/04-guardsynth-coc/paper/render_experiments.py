"""Render the illustrated bilingual experiments. Owner: guardsynth-coc.

Run after render_experiments_figures.py. Generated TeX and PDF figures are
self-contained reproduction assets; completed snapshots cannot be overwritten.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'PROJECT_REGISTRY.json').exists())
OUT = ROOT/'artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/experiments-section-2026-09-30-002'
assert OUT.is_dir() and not (OUT/'RESULT.json').exists(), 'Run figures first; completed runs are immutable'
PREAMBLE = r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=20mm,headheight=16pt]{geometry}
\usepackage{fontspec,kotex,amsmath,booktabs,longtable,array,xcolor,hyperref,fancyhdr,graphicx}
\setmainfont{DejaVu Serif}
\setsansfont{DejaVu Sans}
\setmonofont{DejaVu Sans Mono}
\setmainhangulfont{Noto Sans CJK KR}
\setmonohangulfont{Noto Sans CJK KR}
\definecolor{navy}{HTML}{173E59}
\definecolor{codebg}{HTML}{F3F6F8}
\hypersetup{colorlinks=true,linkcolor=navy,urlcolor=navy,pdftitle={GuardSynth Experimental Evaluation}}
\urlstyle{same}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}
\setlength{\emergencystretch}{4em}
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.2}
\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{\small GuardSynth}
\fancyhead[R]{\small Experimental Evaluation}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.3pt}
\clubpenalty=10000\widowpenalty=10000
\raggedbottom
\begin{document}
'''

def esc(s):
    chars={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$',
           '#':r'\#','_':r'\_','{':r'\{','}':r'\}',
           '~':r'\textasciitilde{}','^':r'\textasciicircum{}',
           '→':r'\ensuremath{\rightarrow}','≥':r'\ensuremath{\geq}',
           '¬':r'\ensuremath{\neg}','∨':r'\ensuremath{\lor}',
           'Σ':r'\ensuremath{\Sigma}','τ':r'\ensuremath{\tau}',
           'Δ':r'\ensuremath{\Delta}','−':r'\ensuremath{-}'}
    return ''.join(chars.get(c,c) for c in s)

records=[]
for lang in ('ko','en'):
    source=ROOT/f'projects/04-guardsynth-coc/paper/IEEE_ACCESS_EXPERIMENTS_V01_{lang.upper()}.md'
    md=source.read_text(); lines=md.splitlines(); links=[]; boxes=0; figures=0; tables=0
    def inline(s):
        tick=chr(96)
        pattern=r'\[([^\]]+)\]\(([^)]+)\)|'+tick+'([^'+tick+']+)'+tick+r'|\*\*([^*]+)\*\*|\$([^$\n]+)\$'
        result=[];pos=0
        for m in re.finditer(pattern,s):
            result.append(esc(s[pos:m.start()]))
            if m.group(1):
                label,target=m.group(1,2)
                if not target.startswith(('https://','http://')):
                    actual=(source.parent/target).resolve()
                    assert actual.exists(),actual
                    target=os.path.relpath(actual,OUT)
                links.append({'label':label,'target':m.group(2)})
                result.append(r'\href{\detokenize{'+target+'}}{'+esc(label)+'}')
            elif m.group(3):
                result.append(r'{\ttfamily\small '+esc(m.group(3))+'}')
            elif m.group(4):
                result.append(r'\textbf{'+esc(m.group(4))+'}')
            else:
                result.append(r'\('+m.group(5)+r'\)')
            pos=m.end()
        result.append(esc(s[pos:]))
        return ''.join(result)

    parts=[PREAMBLE];i=0;box_group=False;evidence_group=False;table_group=False
    while i<len(lines):
        line=lines[i]
        if not line.strip(): parts.append('');i+=1;continue
        if line.startswith(('**표 E', '**Table E')):
            parts.append(r'\par\medskip\noindent\begin{minipage}{\linewidth}')
            table_group=True
        if line.startswith(('**코드 박스 ', '**Code Box ')):
            parts.append(r'\par\medskip\noindent\begin{minipage}{\linewidth}')
            box_group=True
        if line.startswith('!['):
            m=re.fullmatch(r'!\[([^]]+)\]\(([^)]+)\)',line);assert m
            image=(source.parent/m.group(2)).resolve();assert image.exists()
            vector=image.with_suffix('.pdf');assert vector.exists()
            target=os.path.relpath(vector,OUT)
            j=i+1
            while j<len(lines) and not lines[j].strip():j+=1
            caption=lines[j];assert caption.startswith(('그림 ','Figure '))
            parts.append(r'\par\medskip\noindent\begin{minipage}{\linewidth}\centering')
            parts.append(r'\includegraphics[width=\linewidth,height=.39\textheight,keepaspectratio]{'+target+'}')
            parts.append(r'\par\small\raggedright '+inline(caption))
            parts.append(r'\end{minipage}\par\medskip')
            figures+=1;i=j+1;continue
        if line.startswith(chr(96)*3):
            code=[];i+=1
            while i<len(lines) and not lines[i].startswith(chr(96)*3):
                code.append(lines[i]);i+=1
            boxes+=1
            title=('코드 박스 ' if lang=='ko' else 'Code Box ')+str(boxes)
            parts.append(r'\par\medskip\noindent\fcolorbox{navy}{codebg}{\begin{minipage}{\dimexpr\linewidth-2\fboxsep-2\fboxrule\relax}')
            parts.append(r'{\small\bfseries '+esc(title)+r'}\par\smallskip')
            for n,raw in enumerate(code,1):
                indent=len(raw)-len(raw.lstrip())
                parts.append(r'\noindent\makebox[1.8em][r]{\color{gray}\scriptsize '+str(n)+r'}\hspace{.8em}'+
                    r'\parbox[t]{\dimexpr\linewidth-2.8em\relax}{\raggedright\ttfamily\fontsize{8.2}{10.5}\selectfont '+
                    r'\hspace*{'+str(indent*.5)+r'em}'+esc(raw.lstrip())+r'\strut}\par\vspace{1pt}')
            parts.append(r'\end{minipage}}\par\medskip')
            if box_group:
                parts.append(r'\end{minipage}\par\medskip')
                box_group=False
            i+=1;continue
        if line.startswith('# '):
            parts.append(r'\section*{'+inline(line[2:])+'}');i+=1;continue
        if line.startswith('## '):
            if line in ('## 재현 근거','## Reproducibility Evidence'):
                parts.append(r'\begingroup\small\setlength{\parskip}{3pt}')
                parts.append(r'\subsection*{'+inline(line[3:])+'}')
                evidence_group=True;i+=1;continue
            parts.append(r'\section*{'+inline(line[3:])+'}');i+=1;continue
        if line.startswith('### '):
            parts.append(r'\subsection*{'+inline(line[4:])+'}');i+=1;continue
        if line==chr(96)+'enters → entry_ms ≥ clear_ms + release_clear_ms'+chr(96):
            parts.append(r'\[\mathit{enters}\ \Longrightarrow\ \mathit{entry\_ms}\geq\mathit{clear\_ms}+\mathit{release\_clear\_ms}.\]')
            i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                rows.append([c.strip() for c in lines[i].strip('|').split('|')]);i+=1
            n=len(rows[0]);assert all(len(r)==n for r in rows)
            widths={3:[.23,.38,.39],4:[.26,.16,.24,.34],5:[.18,.235,.195,.195,.195]}[n]
            if n==4 and rows[0][0] in ('조건','Condition'):
                widths=[.25,.25,.25,.25]
            spec='@{}'+''.join(r'>{\raggedright\arraybackslash}p{\dimexpr '+f'{w:.4f}'+r'\linewidth-'+f'{(n-1)*8*w:.3f}'+r'pt\relax}' for w in widths)+'@{}'
            header=' & '.join(r'\textbf{'+inline(c)+'}' for c in rows[0])+r' \\'
            parts += [r'\par\medskip\noindent\begin{minipage}{\linewidth}\small',
                      r'\begin{tabular}{'+spec+'}',r'\toprule',header,r'\midrule']
            for row in rows[2:]:parts.append(' & '.join(inline(c) for c in row)+r' \\')
            parts += [r'\bottomrule\end{tabular}\end{minipage}\par\medskip']
            if table_group:
                parts.append(r'\end{minipage}\par\medskip')
                table_group=False
            tables+=1;continue
        if line.startswith('> '):
            parts.append(r'\begin{quote}'+inline(line[2:])+r'\end{quote}');i+=1;continue
        if line.startswith('- '):
            parts.append(r'\begin{itemize}\setlength{\itemsep}{0pt}\setlength{\parsep}{0pt}\setlength{\topsep}{2pt}')
            while i<len(lines) and lines[i].startswith('- '):
                parts.append(r'\item '+inline(lines[i][2:]));i+=1
            parts.append(r'\end{itemize}');continue
        parts.append(inline(line)+r'\par');i+=1
    if evidence_group:parts.append(r'\endgroup')
    parts.append(r'\end{document}')
    stem=f'ieee-access-experiments-v01-{lang}'
    tex=OUT/(stem+'.tex');tex.write_text('\n'.join(parts))
    for run in (1,2):
        r=subprocess.run(['/home/jinhyun/.local/bin/xelatex','-interaction=nonstopmode','-halt-on-error',tex.name],
            cwd=OUT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (OUT/f'build-{lang}-{run}.log').write_text(r.stdout)
        if r.returncode:raise RuntimeError(r.stdout[-5000:])
    record={'language':lang,'source':str(source.relative_to(ROOT)),
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'pdf':stem+'.pdf','figures':figures,'code_boxes':boxes,'tables':tables,'links':links}
    assert (figures,boxes,tables)==(4,0,7)
    records.append(record)
    print(json.dumps({k:v for k,v in record.items() if k!='links'},ensure_ascii=False))
(OUT/'RUN_MANIFEST.json').write_text(json.dumps({
    'project_id':'guardsynth-coc','run_id':OUT.name,'sources':records,
    'purpose':'Bilingual experimental evaluation with original-prediction figures; no new training',
    'builders':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [Path(__file__),Path(__file__).with_name('render_experiments_figures.py'),
                          Path(__file__).with_name('verify_experiments_unsat.py')]},
    'reproduce':'Run render_experiments_figures.py, verify_experiments_unsat.py, then render_experiments.py before RESULT.json is finalized; generated TeX also compiles twice with XeLaTeX.',
    'prior_snapshot':'experiments-section-2026-09-30-001; UNSAT interpretation added without overwriting prior outputs'
},ensure_ascii=False,indent=2)+'\n')
