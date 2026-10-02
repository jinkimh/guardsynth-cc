"""Build reviewed bilingual manuscripts without changing experiment results."""
from pathlib import Path
import re,json,hashlib,shutil,subprocess,zipfile
ROOT=Path("/home/jinhyun/prj_ws/prj_jin/guardsynth-cc")
P=ROOT/"projects/04-guardsynth-coc/paper";OUT=Path(__file__).resolve().parent
assert not (OUT/"RESULT.json").exists()
F=OUT/"figures";F.mkdir(exist_ok=True)
with zipfile.ZipFile("/tmp/guardsynth-ieee-access-template.zip") as z:
    for n in z.namelist():
        p=Path(n)
        if p.name=="IEEEtran.cls":continue
        if p.suffix in (".cls",".sty",".fd",".map",".tfm",".pfb") or p.name in ("logo.png","notaglinelogo.png","bullet.png"):(OUT/p.name).write_bytes(z.read(n))
old=ROOT/"artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/experiments-section-2026-09-30-003/build_snapshot.py"
recipe=old.read_text().split("# Reuse the established Markdown/TeX renderer")[0]
recipe=recipe.replace('OUT = Path(__file__).resolve().parent',f'OUT = Path({str(OUT)!r})')
a,b=recipe.split("import matplotlib",1)
for x,y in {"정확도 (%) ↑":"Accuracy (%)","위반율 (%) ↓":"Violation rate (%)","연결 교란":"Shuffled","계약쌍 정확도 (%)":"Contract-pair accuracy (%)","정상 연결 / 학습 연결 교란 정확도 (%)":"Correct / shuffled accuracy (%)","금지: 요구 대기 미완료":"Prohibited: wait incomplete","허용: 요구 대기 충족":"Admissible: wait completed","허용 경계 = 11.000 s + 0.500 s":"Boundary = 11.000 s + 0.500 s","시간":"Temporal","정적":"Static","기동":"Maneuver"}.items():b=b.replace(x,y)
b=b.replace('f"{name}-ko.{ext}"','f"{name}-en.{ext}"')
b=b.replace("정상 연결 / 학습 Shuffled 정확도 (%)","Correct / shuffled accuracy (%)")
b=b.replace('fontsize=9)', 'fontsize=8)')
b=b.replace('font=FontProperties','tasks=[(a,b,{"최고속도":"Max speed","최소거리":"Clearance","진입시간":"Entry delay","시간 대기":"Wait","정지":"Stop","차선 변경":"Lane change"}.get(c,c)) for a,b,c in tasks]\nfont=FontProperties')
b=b.replace('"Max speed"','"Speed"').replace('"Entry delay"','"Entry time"').replace('"Lane change"','"Lane change"')
exec(compile(a+"import matplotlib"+b,str(old),"exec"),{"__file__":str(old)})
# Build one reference registry from existing source-backed bibliography entries.
refs={};local={}
for sec in ("RELATED_WORK","BACKGROUND"):
    md=(P/f"IEEE_ACCESS_{sec}_V01_EN.md").read_text()
    local[sec]={}
    for n,desc,url in re.findall(r"^-? ?\[(\d+)\] (.*?) \[(?:Paper|Source)\]\((https?://[^)]+)\)\.?",md,re.M):
        refs.setdefault(url,desc);local[sec][int(n)]=url
prior="prior-manuscript"
refs[prior]="Research team's preceding manuscript, Guard-Aware Trajectory Candidate Selection for Vision-Language Autonomous Driving: Safety-Constrained Chain-of-Causation, supplied revision v01. Publication details pending author confirmation."
refs["https://openai.com/codex/"]="OpenAI, Codex. Software used for drafting, translation, editing, and formatting assistance."
T=chr(96);order=[]
def key(url):
    if url not in order:order.append(url)
    return "r"+str(order.index(url)+1)
def esc(s):
    chars={"\\":r"\textbackslash{}","&":r"\&","%":r"\%","$":r"\$","#":r"\#","_":r"\_","{":r"\{","}":r"\}","~":r"\textasciitilde{}","^":r"\textasciicircum{}"}
    symbols={"→":r"\rightarrow","≥":r"\geq","≤":r"\leq","¬":r"\neg","∨":r"\lor","∧":r"\land","⊨":r"\models","Φ":r"\Phi","Σ":r"\Sigma","τ":r"\tau","Δ":r"\Delta","α":r"\alpha","×":r"\times","₀":"_0","₁":"_1","₂":"_2","↑":r"\uparrow","↓":r"\downarrow"}
    chars.update({k:r"\ensuremath{"+v+"}" for k,v in symbols.items()})
    chars.update({"–":"--","—":"---","−":"-"," ":" "})
    return "".join(chars.get(c,c) for c in s)
def inline(s,sec=""):
    if sec=="RELATED_WORK":
        s=re.sub(r"\[([\d, ]+)\](?!\()",lambda m:"@@"+",".join(key(local[sec][int(n)]) for n in m[1].split(","))+"@@",s)
    pat=r"@@([^@]+)@@|\[([^]]+)\]\(([^)]+)\)|"+T+"([^"+T+"]+)"+T+r"|\*\*([^*]+)\*\*|\$([^$\n]+)\$"
    result=[];pos=0
    for m in re.finditer(pat,s):
        result.append(esc(s[pos:m.start()]))
        if m[1]:result.append(r"\cite{"+m[1]+"}")
        elif m[2]:
            label,url=m[2],m[3]
            if "latex-kiee-review-2022-revision-v01" in url:url=prior
            if url in refs:result.append(r"\cite{"+key(url)+"}")
            elif url.startswith("http"):result.append(r"\href{"+url+"}{"+esc(label)+"}")
            else:
                target=(P/url).resolve()
                assert target.exists(),target
                result.append(r"\href{\detokenize{"+str(target)+"}}{"+esc(label)+"}")
        elif m[4]:result.append(r"{\ttfamily\fontseries{m}\selectfont\footnotesize "+esc(m[4]).replace(r"\_",r"\_\allowbreak ").replace("/",r"/\allowbreak ")+"}")
        elif m[5]:result.append(r"\textbf{"+inline(m[5],sec)+"}")
        else:result.append("$"+m[6]+"$")
        pos=m.end()
    result.append(esc(s[pos:]));return "".join(result)
def render(md,sec,lang):
    for cut in ("\n## References","\n## 참고문헌","\n## 구현 및 예제 근거","\n## Implementation and Example Evidence","\n부가자료:"):md=md.split(cut)[0]
    lines=md.splitlines();out=[];i=0;caption=None
    while i<len(lines):
        s=lines[i]
        if not s.strip():out.append("");i+=1;continue
        if s.startswith("# "):i+=1;continue
        if s.startswith(("## ","### ")):
            level="subsubsection" if s.startswith("###") else "subsection"
            title=re.sub(r"^(?:[A-Z]|\d+)\.\s*","",s.lstrip("# "))
            out.append("\\"+level+"{"+inline(title,sec)+"}");i+=1;continue
        if s.startswith("!["):
            m=re.fullmatch(r"!\[([^]]+)\]\(([^)]+)\)",s);src=(P/m[2]).resolve().with_suffix(".pdf");assert src.exists(),src
            dest=F/src.name
            if src!=dest:shutil.copyfile(src,dest)
            j=i+1
            while j<len(lines) and not lines[j].strip():j+=1
            cap=re.sub(r"^(Figure|그림)\s*\d+\.\s*","",lines[j])
            out += [r"\begin{figure*}[!t]\centering",r"\includegraphics[width=.94\textwidth,height=.30\textheight,keepaspectratio]{"+str(dest)+"}",r"\caption{"+inline(cap,sec)+"}",r"\end{figure*}"]
            i=j+1;continue
        if re.match(r"^\*\*(Table|표) [EM]\d+\.",s) or s.startswith(("Table 1.","표 1.")):
            caption=re.sub(r"^(?:\*\*)?(?:Table|표)\s+[EM]?\d+\.\s*","",s).removesuffix("**");i+=1;continue
        if s.startswith("|"):
            rows=[]
            while i<len(lines) and lines[i].startswith("|"):rows.append([x.strip() for x in lines[i].strip("|").split("|")]);i+=1
            n=len(rows[0]);assert all(len(x)==n for x in rows)
            cap=caption or ("Constraint representation and example mappings" if lang=="en" else "명세 구성과 예제 대응")
            label=r"\label{tab:taskmap}" if "task-to-verdict" in cap or "과제–판정" in cap else ""
            widths={3:[.24,.33,.43],4:[.24,.25,.25,.26],5:[.13,.19,.25,.25,.18]}[n]
            spec="@{}"+"".join(r">{\raggedright\arraybackslash}p{\dimexpr "+str(w)+r"\textwidth-"+str(2*(n-1)*3*w)+r"pt\relax}" for w in widths)+"@{}"
            out += [r"\begin{table*}[tp]\caption{"+inline(cap,sec)+"}"+label,r"\centering\fontsize{8}{10}\selectfont\setlength{\tabcolsep}{3pt}",r"\begin{tabular}{"+spec+"}",r"\toprule"," & ".join(r"\textbf{"+inline(x,sec)+"}" for x in rows[0])+r"\\",r"\midrule"]
            for row in rows[2:]:out.append(" & ".join(inline(x,sec) for x in row)+r"\\[3pt]")
            out += [r"\bottomrule\end{tabular}",r"\end{table*}"];caption=None;continue
        if s.startswith(T*3):
            code=[];i+=1
            while i<len(lines) and not lines[i].startswith(T*3):code.append(lines[i]);i+=1
            out.append(r"\par\smallskip\noindent\fcolorbox{black!30}{black!3}{\begin{minipage}{\dimexpr\linewidth-2\fboxsep-2\fboxrule\relax}")
            for n,row in enumerate(code,1):
                txt=esc(row.lstrip()).replace(r"\_",r"\_\allowbreak ").replace(",",r",\allowbreak ")
                out.append(r"\noindent\makebox[1.5em][r]{\scriptsize "+str(n)+r"}\hspace{.4em}\parbox[t]{\dimexpr\linewidth-2em\relax}{\raggedright\ttfamily\fontseries{m}\fontsize{7.2}{9}\selectfont "+r"\hspace*{"+str((len(row)-len(row.lstrip()))*.3)+r"em}"+txt+r"\strut}\par")
            out.append(r"\end{minipage}}\par\smallskip");i+=1;continue
        if s.startswith("> "):out.append(r"\begin{quote}\small "+inline(s[2:],sec)+r"\end{quote}");i+=1;continue
        if s.startswith("- ") or re.match(r"^\d+\. ",s):
            num=not s.startswith("- ");env="enumerate" if num else "itemize";out.append(r"\begin{"+env+"}")
            while i<len(lines) and (bool(re.match(r"^\d+\. ",lines[i])) if num else lines[i].startswith("- ")):
                text=re.sub(r"^\d+\. ","",lines[i]) if num else lines[i][2:];out.append(r"\item "+inline(text,sec));i+=1
            out.append(r"\end{"+env+"}");continue
        eq={"Φ ∧ ¬P":r"\[\Phi\land\neg P\]","W = W₀ + (α/r)BA":r"\[W=W_0+\frac{\alpha}{r}BA\]","enters → entry_ms ≥ clear_ms + release_clear_ms":r"\[e\Rightarrow u_{\mathrm{ms}}\geq\tau_{\mathrm{ms}}+\Delta_{\mathrm{ms}}.\]"}
        out.append(eq.get(s.strip(T),inline(s,sec)+r"\par"));i+=1
    return "\n".join(out).replace("Table M1",r"Table~\ref{tab:taskmap}").replace("표 M1",r"표~\ref{tab:taskmap}")
chapters=[("INTRODUCTION","Introduction","서론"),("RELATED_WORK","Related Work","관련 연구"),("BACKGROUND","Background","배경"),("METHODOLOGY","Proposed Method","제안 방법"),("EXPERIMENTS","Experimental Setup","실험 설정"),("RESULTS","Results","결과"),("DISCUSSION","Discussion","논의"),("CONCLUSION","Conclusion","결론")]
common=r"""
\usepackage{amsmath,amssymb,booktabs,array,xcolor,graphicx,hyperref}
\setlength{\emergencystretch}{3em}\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.12}\hypersetup{hidelinks}\raggedbottom
\setcounter{dbltopnumber}{2}
"""
records=[]
for lang in ("en","ko"):
    order.clear();front=(P/f"IEEE_ACCESS_TITLE_ABSTRACT_V01_{lang.upper()}.md").read_text()
    title=front.splitlines()[0][2:];abstract=front.split("\n\n",2)[2].strip()
    if lang=="en":
        start=r"\makeatletter\def\input@path{{"+str(P/"ieee-access-template")+r"/}}\makeatother"+"\n"+r"\documentclass[nolineno]{ieeeaccess}"+common+r"""
\usepackage[T1]{fontenc}
\usepackage{etoolbox}
\definecolor{accessblue}{cmyk}{1,.35,0,.3}
\makeatletter
\def\reviewfooter{\hbox to\textwidth{\scriptsize Author-review draft\hfill\thepage}}
\apptocmd{\ps@titlepage}{\let\@oddfoot\reviewfooter\let\@evenfoot\reviewfooter}{}{}
\apptocmd{\ps@headings}{\let\@oddfoot\reviewfooter\let\@evenfoot\reviewfooter}{}{}
\makeatother
\begin{document}\pagestyle{headings}
\history{Author-review draft; publication metadata pending.}\doi{}
\title{"""+esc(title)+r"""}
\author{Author information pending confirmation}
\address{Affiliations and corresponding author to be confirmed}
\markboth{GuardSynth: Formal Specification and Verification}{GuardSynth: Formal Specification and Verification}
\begin{abstract}"""+inline(abstract)+r"""\end{abstract}
\begin{keywords}Behavioral constraints, Chain of Causation, controlled natural language, formal verification, vision-language models.\end{keywords}
\maketitle
"""
    else:
        start=r"\documentclass[10pt,a4paper,twocolumn]{article}\usepackage[margin=18mm]{geometry}\usepackage{fontspec,kotex}"+common+r"""
\setmainfont{DejaVu Serif}\setmonofont{DejaVu Sans Mono}
\setmainhangulfont{Noto Sans CJK KR}\setmonohangulfont{Noto Sans CJK KR}
\renewcommand{\figurename}{그림}\renewcommand{\tablename}{표}
\renewcommand{\thesection}{\Roman{section}}\renewcommand{\thesubsection}{\Alph{subsection}}
\title{"""+esc(title)+r"""}\author{저자 검토용 원고}\date{}
\begin{document}\twocolumn[\maketitle\begin{minipage}{\textwidth}\small\textbf{초록}\quad """+inline(abstract)+r"""\par\medskip\textbf{주요어}\quad 행동 제약, CoC, EBLC, CNL, 정형 검증, VLM.\end{minipage}\vspace{1em}]
"""
    parts=[start]
    for name,en,ko in chapters:
        src="EXPERIMENTS" if name=="RESULTS" else name;md=(P/f"IEEE_ACCESS_{src}_V01_{lang.upper()}.md").read_text()
        if name in ("EXPERIMENTS","RESULTS"):
            before,after=md.split("\n## B.",1);md=before if name=="EXPERIMENTS" else "# Results\n\n## B."+after
        if name=="DISCUSSION":parts.append(r"\clearpage")
        parts += [r"\section{"+(en if lang=="en" else ko)+"}",render(md,src,lang)]
    parts.append(r"\section*{"+("Acknowledgment" if lang=="en" else "집필 지원 고지")+"}")
    parts.append(("OpenAI Codex assisted drafting, translation, editing, and formatting of Sections I--VIII. The authors remain responsible for checking claims and references. Author, affiliation, funding, and prior-publication metadata require final confirmation." if lang=="en" else "I--VIII장의 초안 작성·번역·편집·형식 정리에 OpenAI Codex를 사용하였다. 주장·인용의 최종 확인과 책임은 저자에게 있으며, 저자·소속·연구비·선행 원고 출판 정보는 최종 확인이 필요하다.")+r"\cite{"+key("https://openai.com/codex/")+"}")
    parts.append(r"\begin{thebibliography}{99}")
    for url in order:parts.append(r"\bibitem{"+key(url)+"} "+esc(refs[url])+(r" \url{"+url+"}" if url.startswith("http") else ""))
    parts.append(r"\end{thebibliography}")
    if lang=="en":parts.append(r"\EOD")
    parts.append(r"\end{document}")
    stem="ieee-access-manuscript-"+lang;tex=OUT/(stem+".tex");tex.write_text("\n".join(parts))
    engine="/usr/bin/pdflatex" if lang=="en" else "/home/jinhyun/.local/bin/xelatex"
    for run in (1,2):
        r=subprocess.run([engine,"-interaction=nonstopmode","-halt-on-error",tex.name],cwd=OUT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (OUT/f"build-{lang}-{run}.log").write_text(r.stdout)
        if r.returncode:raise RuntimeError(r.stdout[-5000:])
    records.append({"language":lang,"pdf":stem+".pdf","tex":stem+".tex","references":list(order)})
for f in P.glob("IEEE_ACCESS_*_V01_*.md"):shutil.copyfile(f,OUT/f.name)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/"RUN_MANIFEST.json").write_text(json.dumps({"project_id":"guardsynth-coc","run_id":OUT.name,"documents":records,"source_sha256":{str(f.relative_to(ROOT)):sha(f) for f in P.glob("IEEE_ACCESS_*_V01_*.md")},"purpose":"Integrated manuscript revision; no new experiments","prior_manuscript":"projects/01-safety-constrained-coc/paper/manuscript/latex-kiee-review-2022-revision-v01","template_url":"https://ieeeaccess.ieee.org/wp-content/uploads/2026/05/ACCESS_latex_template_20260513-1-1.zip","template_sha256":sha(Path("/tmp/guardsynth-ieee-access-template.zip")),"experiment_results_modified":False},ensure_ascii=False,indent=2)+"\n")
print(json.dumps(records,ensure_ascii=False))
