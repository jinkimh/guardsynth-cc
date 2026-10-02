"""Render detailed bilingual experiment supplements using the established renderer."""
from pathlib import Path
import re,json
ROOT=Path("/home/jinhyun/prj_ws/prj_jin/guardsynth-cc")
OUT=Path(__file__).resolve().parent
assert not (OUT/"RESULT.json").exists()
builder=ROOT/"projects/04-guardsynth-coc/paper/render_experiments.py"
s=builder.read_text();s=s[:s.index("(OUT/'RUN_MANIFEST.json')")]
s=re.sub(r"ROOT = next[^\n]+",f"ROOT = Path({str(ROOT)!r})",s,count=1)
s=re.sub(r"OUT = ROOT/[^\n]+",f"OUT = Path({str(OUT)!r})",s,count=1)
s=s.replace("IEEE_ACCESS_EXPERIMENTS_V01_", "IEEE_ACCESS_EXPERIMENTS_SUPPLEMENT_V01_")
s=s.replace("ieee-access-experiments-v01-", "ieee-access-experiments-supplement-v01-")
s=s.replace("build-{lang}-{run}.log", "supplement-build-{lang}-{run}.log")
s=s.replace("assert (figures,boxes,tables)==(4,0,7)", "assert figures==4 and boxes==0 and tables==11, (figures,boxes,tables)")
s=s.replace("4:[.26,.16,.24,.34]","4:[.28,.24,.24,.24]")
s=s.replace("if line.startswith('## '):","if line.startswith('## '):\n            if evidence_group:\n                parts.append(r'\\endgroup'); evidence_group=False")
scope={"__file__":str(builder)}
exec(compile(s,str(builder),"exec"),scope)
(OUT/"supplement_build.json").write_text(json.dumps(scope["records"],ensure_ascii=False,indent=2)+"\n")
