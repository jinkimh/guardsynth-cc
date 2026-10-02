from pathlib import Path
from pypdf import PdfReader
from pypdf.generic import ContentStream
import re,unicodedata,json,hashlib,csv,collections,sys
root=next(p for p in Path(__file__).resolve().parents if (p/'PROJECT_REGISTRY.json').is_file());src=root/'projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01';a=root/'artifacts/projects/sequential-coc-verification/public/kiee-review-revision-001/manuscript-build-2026-10-01-001'
def norm(t):
 t=unicodedata.normalize('NFKC',t).replace('ㆍ','').replace('ᆞ','').replace('−','-').replace('–','-').replace('—','-')
 t=t.replace('``','').replace("''",'').replace('“','').replace('”','').replace('’',"'").replace('‘',"'").replace('--','-')
 t=re.sub(r'\[\d+(?:,\s*\d+)*\]','',t)
 return re.sub(r'\s+','',t)
def plain(t):
 t=t.replace(r'\_', '_').replace(r'\%', '%');t=re.sub(r'\\(?:texttt|emph|textbf|rev)\{([^}]*)\}',r'\1',t);t=t.replace('~',' ');return t
results={};fail=[]
marked=PdfReader(src/'main.pdf');clean=PdfReader(src/'main-clean.pdf')
results['pages']={};results['marked_clean_identical_text']=len(marked.pages)==len(clean.pages) and all(x.extract_text()==y.extract_text() for x,y in zip(marked.pages,clean.pages))
if not results['marked_clean_identical_text']:fail.append('marked-clean content mismatch')
pages=[norm(x.extract_text()) for x in marked.pages]
aux=(a/'main/main.aux').read_text();labels={m.group(1):(m.group(2),m.group(3)) for m in re.finditer(r'\\newlabel\{([^}]+)\}\{\{([^}]+)\}\{([^}]+)\}',aux)}
locs=(src/'manuscript-locations.tex').read_text();results['responses']={}
for key,(num,page) in labels.items():
 if not key.startswith(('sec:','tab:','eq:','lst:','fig:')):continue
 kind='절' if key.startswith('sec:') else '표' if key.startswith('tab:') else '식' if key.startswith('eq:') else '그림' if key.startswith('fig:') else '목록'
 label=f'{num}{kind}({page}쪽)' if kind=='절' else f'{kind} {num}({page}쪽)'
 expected=r'\expandafter\def\csname mloc@'+key+r'\endcsname{'+label+'}'
 if expected not in locs:fail.append('stale location macro: '+key)
results['location_macros_match_final_aux']=not any('location macro' in x for x in fail)

for name in ['main','main-clean','response-to-reviewer-1','response-to-reviewer-2','response-to-reviewer-3']:
 r=PdfReader(src/(name+'.pdf'));results['pages'][name]=len(r.pages)
 if any(abs(float(x.mediabox.width)-595.276)>1 or abs(float(x.mediabox.height)-841.89)>1 for x in r.pages):fail.append(name+' not A4')
 log=(a/name/(name+'.log')).read_text()
 serious=re.findall(r'^.*(?:Undefined control sequence|undefined references|Citation.*undefined|Missing character|Overfull|Fatal error).*$' ,log,re.M)
 results.setdefault('build_warnings',{})[name]=serious
 if serious:fail.extend(serious)
 if name.startswith('response'):
  response_pdf_text=norm(' '.join(p.extract_text() for p in r.pages))
  text=(src/(name+'.tex')).read_text();count={1:9,2:8,3:11}[int(name[-1])];actual=text.count(r'\begin{reviewitem}');blocks={b:text.count(r'\begin{'+b+'}') for b in ['reviewercomment','authorresponse','manuscriptrevision']}
  if actual!=count or any(x!=count for x in blocks.values()):fail.append(name+' review blocks')
  refs=re.findall(r'\\mloc\{([^}]+)\}',text)
  if any(ref not in labels for ref in refs):fail.append(name+' undefined locations')
  quoted=[]
  for item in re.findall(r'\\begin\{manuscriptrevision\}.*?\\end\{manuscriptrevision\}',text,re.S):
   q=re.search(r'\\begin\{quote\}(.*?)\\end\{quote\}',item,re.S).group(1).strip();q=plain(q)
   # A quote can deliberately join two nonadjacent revised sentences.
   parts=re.split(r'(?<=\.)\s+',q);hits=[]
   for part in parts:
    match=[i+1 for i,p in enumerate(pages) if norm(part) in p]
    hits.append(match)
    if not match:fail.append(name+' quote absent from PDF: '+part[:100])
   declared=[int(x) for x in re.findall(r'\d+',re.search(r'아래 발췌: ([0-9, ]+)쪽',item).group(1))]
   if any(not set(h).intersection(declared) for h in hits):fail.append(name+' excerpt page mismatch')
   if norm(q) not in response_pdf_text:fail.append(name+' quote absent from response PDF')
   quoted.append({'quote':q,'sentence_pages':hits,'declared_excerpt_pages':declared,'location_labels':re.findall(r'\\mloc\{([^}]+)\}',item)})
  results['responses'][name]={'item_count':actual,'block_counts':blocks,'location_references':len(refs),'quotes':quoted}
# Numbers are recounted from immutable inputs, never by running a detector.
croot=root/'artifacts/projects/sequential-coc-verification/public/kiee-review-revision-001';c=croot/'controlled-scenarios-2026-10-01-001'
cases=json.loads((c/'cases.json').read_text());scores=json.loads((c/'scores.json').read_text());retest=json.loads((croot/'condition-model-2026-10-01-001/RESULT.json').read_text())
results['expected_classes']=dict(collections.Counter(x['expected']['verdict'] for x in cases));results['first_results']={k:{'correct':v['three_class_correct'],'first_violation':v['first_violation_exact'],'gaps':{g:d['three_class_correct'] for g,d in v['by_gap'].items()}} for k,v in scores.items()};results['retest']=retest
assert results['expected_classes']=={'CONTRADICTION':72,'CONSISTENT':36,'UNKNOWN':36}
assert scores['legacy_full']['three_class_correct']==96 and scores['fsm']['three_class_correct']==144
assert retest['verdict_matches']==144 and retest['first_violation_matches']==72
assert all(retest[k]==108 for k in ['issue_location_matches','issue_obligation_matches','issue_reason_matches'])
# Preserve baseline and frozen experiment implementation identity.
baseline=Path('/home/jinhyun/prj_ws/prj_jin/guardsynth-cc/projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-10pages')
before=json.loads((a/'baseline_hashes.json').read_text());results['original_submission_unchanged']=all(hashlib.sha256((baseline/k).read_bytes()).hexdigest()==v for k,v in before.items())
if not results['original_submission_unchanged']:fail.append('original submission modified')
summary=json.loads((croot/'evaluation-summary-2026-10-01-001/RUN_MANIFEST.json').read_text());results['frozen_code_hashes_match']=all(hashlib.sha256((root/k).read_bytes()).hexdigest()==v for k,v in summary['source_hashes'].items())
if not results['frozen_code_hashes_match']:fail.append('frozen implementation modified')
# Check blue content in marked PDF and absence of chromatic content in clean.
colors={}
for name,reader in [('main',marked),('main-clean',clean)]:
 rgb=set()
 for p in reader.pages:
  for operands,op in ContentStream(p.get_contents(),reader).operations:
   if op in (b'rg',b'RG'):rgb.add(tuple(round(float(v),5) for v in operands))
 colors[name]=sorted(rgb)
results['rgb_colors']=colors
if not any(x[2]>x[0] and x[2]>x[1] for x in colors['main']):fail.append('no revision blue')
if any(max(x)-min(x)>0.001 for x in colors['main-clean']):fail.append('chromatic clean content')
results['errors']=fail;results['status']='PASS' if not fail else 'FAIL'
if (a/'RUN_MANIFEST.json').is_file():
 saved=json.loads((a/'document_validation.json').read_text())
 if results!=saved:fail.append('sealed validation result changed');results['status']='FAIL'
else:
 (a/'document_validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':results['status'],'pages':results['pages'],'marked_clean_identical_text':results['marked_clean_identical_text'],'errors':fail},ensure_ascii=False,indent=2))
sys.exit(bool(fail))
