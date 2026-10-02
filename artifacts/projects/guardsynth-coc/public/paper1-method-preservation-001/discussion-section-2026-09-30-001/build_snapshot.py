"""Rebuild this bilingual Discussion snapshot. Owner: guardsynth-coc."""
from pathlib import Path
import hashlib, json, re, shutil
ROOT=Path("/home/jinhyun/prj_ws/prj_jin/guardsynth-cc")
OUT=Path(__file__).resolve().parent
assert not (OUT/"RESULT.json").exists(), "Completed snapshots are immutable"
builder=ROOT/"projects/04-guardsynth-coc/paper/render_experiments.py"
text=builder.read_text()
text=text[:text.index("(OUT/'RUN_MANIFEST.json')")]
text=re.sub(r"ROOT = next[^\n]+",f"ROOT = Path({str(ROOT)!r})",text,count=1)
text=re.sub(r"OUT = ROOT/[^\n]+",f"OUT = Path({str(OUT)!r})",text,count=1)
text=text.replace("IEEE_ACCESS_EXPERIMENTS_V01_","IEEE_ACCESS_DISCUSSION_V01_")
text=text.replace("ieee-access-experiments-v01-","ieee-access-discussion-v01-")
text=text.replace("Experimental Evaluation","Discussion")
text=text.replace("parts=[PREAMBLE];", "parts=[PREAMBLE.replace('{6pt}','{4pt}')];")
text=text.replace("parts.append(r'\\section*{'+inline(line[3:])", "parts.append(r'\\subsection*{'+inline(line[3:])")
text=text.replace("if line.startswith('## '):", "if line.startswith('## '):\n            if (lang=='ko' and line.startswith('## D.')) or (lang=='en' and line.startswith('## C.')):\n                parts.append(r'\\newpage')")
text=text.replace("assert (figures,boxes,tables)==(4,0,7)","assert (figures,boxes,tables)==(0,0,0)")
scope={"__file__":str(builder)}
exec(compile(text,str(builder),"exec"),scope)
records=scope["records"]
for record in records:
    source=ROOT/record["source"]
    shutil.copyfile(source,OUT/source.name)
sources=[builder,Path(__file__),
 ROOT/"projects/04-guardsynth-coc/paper/IEEE_ACCESS_EXPERIMENTS_V01_KO.md",
 ROOT/"projects/04-guardsynth-coc/paper/IEEE_ACCESS_EXPERIMENTS_SUPPLEMENT_V01_KO.md",
 ROOT/"projects/04-guardsynth-coc/paper/IEEE_ACCESS_METHODOLOGY_V01_KO.md"]
manifest={"project_id":"guardsynth-coc","run_id":OUT.name,"documents":records,
 "purpose":"Approved four-part Discussion; no added experiment or performance claim",
 "source_sha256":{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
 "reproduce":"Run build_snapshot.py with Python before finalizing RESULT.json; each generated TeX independently compiles twice with XeLaTeX.",
 "scope":"Standalone Korean and English Discussion; main.tex and frozen experiments unchanged"}
(OUT/"RUN_MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
print("Bilingual Discussion PDFs built; verification pending.")
