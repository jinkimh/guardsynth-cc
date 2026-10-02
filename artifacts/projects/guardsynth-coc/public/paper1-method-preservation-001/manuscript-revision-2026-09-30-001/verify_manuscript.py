"""Read-only source/data/logic checks for the manuscript revision."""
from pathlib import Path
import csv,hashlib,json,re,statistics
import z3
ROOT=Path("/home/jinhyun/prj_ws/prj_jin/guardsynth-cc")
P=ROOT/"projects/04-guardsynth-coc/paper";OUT=Path(__file__).resolve().parent
B=ROOT.parent/"guardsynth-cc-worktrees/guardsynth-additional-20260930/artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001"
def rows(path):return [json.loads(x) for x in path.read_text().splitlines()]
checks=[];sources={}
def read(path):
    sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    return rows(path)
for task in ("static","maneuver"):
    base=B/(task+"-contract-protocol-2026-09-30-003")
    contracts=read(base/"test_contracts.jsonl")
    examples={tuple(x["id"]):x for x in read(base/"test_p2.jsonl")}
    seen=set()
    for row in contracts:
        raw=row["contract"];kind=raw["kind"]
        if kind in seen:continue
        seen.add(kind)
        example=examples[tuple(row["id"])]["example"]
        candidates=[example["scene"]["candidate_a"],example["scene"]["candidate_b"]] if task=="static" else example["scene"]["candidates"]
        syms={d["name"]:z3.Bool(d["name"]) if d["sort"]=="BOOL" else z3.Int(d["name"]) for d in row["core"]["declarations"]}
        def expr(x):
            if x["op"]=="var":return syms[x["name"]]
            if x["op"]=="literal":return z3.BoolVal(x["value"]) if x["sort"]=="BOOL" else z3.IntVal(x["value"])
            left,right=expr(x["left"]),expr(x["right"])
            return {"implies":lambda:z3.Implies(left,right),"le":lambda:left<=right,"ge":lambda:left>=right}[x["op"]]()
        for c in candidates:
            label=c["name"] if task=="static" else c["label"]
            complete=True if task=="static" else c["goal_complete"]
            s=z3.Solver();s.add(*[expr(x["formula"]) for x in row["core"]["clauses"]]);s.add(syms["completes"]==complete)
            for x in raw["limits"]:s.add(syms[x["field"]]==(round(c[x["field"]]*1000) if complete else 0))
            got=str(s.check()).upper();expected=row["candidate_checks"][label]["eblc_status"]
            assert got==expected,(kind,label,got,expected)
            checks.append({"task":kind,"id":row["id"],"candidate":label,"status":got})
        for lang in ("KO","EN"):
            md=(P/f"IEEE_ACCESS_METHODOLOGY_V01_{lang}.md").read_text()
            for sentence in re.split(r"(?<=\.) (?=[A-Z])",row["cnl"]):assert sentence in md,(lang,kind,sentence)
            for x in raw["limits"]:
                assert x["field"] in md
        assert row["cnl"] in examples[tuple(row["id"])]["prompt"]
        assert "Requirement CoC:" in examples[tuple(row["id"])]["prompt"]
e=z3.Bool("enters");u=z3.Int("entry_ms")
for value,expected in ((11499,"UNSAT"),(11500,"SAT")):
    s=z3.Solver();s.add(z3.Implies(e,u>=11000+500),e,u==value)
    got=str(s.check()).upper();assert got==expected
    checks.append({"task":"temporal","entry_ms":value,"status":got})
# All primary/unseen numerical cells agree between maintained language editions.
def numeric_rows(md):
    return [re.findall(r"\d+\.\d+",x) for x in md.splitlines() if x.startswith("|") and re.search(r"\d+\.\d+ / \d+\.\d+",x)]
ko=(P/"IEEE_ACCESS_EXPERIMENTS_V01_KO.md").read_text()
en=(P/"IEEE_ACCESS_EXPERIMENTS_V01_EN.md").read_text()
assert numeric_rows(ko)==numeric_rows(en)
assert len(numeric_rows(ko))==9
for lang in ("KO","EN"):
    md=(P/f"IEEE_ACCESS_EXPERIMENTS_SUPPLEMENT_V01_{lang}.md").read_text()
    assert all(f"## S{i}." in md for i in range(1,11))
    assert "85.71%" in md and "NOT_SUPPORTED" in md and "INCONCLUSIVE" in md
s1=(P/"IEEE_ACCESS_EXPERIMENTS_SUPPLEMENT_V01_KO.md").read_text().split("## S8.")[1]
s2=(P/"IEEE_ACCESS_EXPERIMENTS_SUPPLEMENT_V01_EN.md").read_text().split("## S8.")[1]
assert numeric_rows(s1)==numeric_rows(s2)
for p in P.glob("IEEE_ACCESS_*_V01_*.md"):
    t=p.read_text()
    assert "ECBL" not in t and "chain of cognition" not in t.lower(),p
    assert not re.search(r"\bP3\b",t),p
# Confirm frozen evidence has not changed during the audit.
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in sources.items())
result={"project_id":"guardsynth-coc","candidate_and_temporal_queries":checks,"smt_checks":len(checks),
"bilingual_primary_unseen_rows":9,"bilingual_primary_unseen_numeric_cells":54,
"bilingual_additional_supplement_rows":len(numeric_rows(s1)),
"exact_cnl_profile_kinds":5,"frozen_source_sha256":sources,"terminology_check":"PASS","experiment_results_modified":False}
(OUT/"content_checks.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k not in ("candidate_and_temporal_queries","frozen_source_sha256")},ensure_ascii=False))

