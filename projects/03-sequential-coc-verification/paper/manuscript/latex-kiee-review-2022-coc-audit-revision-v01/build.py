"""Build the E6 manuscript and responses; intermediate files stay in owner artifacts."""
from pathlib import Path
import subprocess,os,sys,re,shutil
root=next(p for p in Path(__file__).resolve().parents if (p/'PROJECT_REGISTRY.json').is_file())
src=root/'projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01'
artifact_parent=root/'artifacts/projects/sequential-coc-verification/public/kiee-review-revision-001'
a=Path(os.environ.get('COC_BUILD_DIR',str(artifact_parent/'manuscript-build-2026-10-01-001'))).resolve()
a.relative_to(artifact_parent.resolve())
if a==artifact_parent.resolve() or a.exists():
 raise SystemExit('Build output already exists or is not a run directory; set COC_BUILD_DIR to a new owner-scoped run directory.')
a.mkdir(parents=True)
env=os.environ.copy();env['TEXINPUTS']=str(src/'.texlive-local/tex')+'//:'+str(src)+'//:';env['BIBINPUTS']=str(src)+':';env['BSTINPUTS']=str(src)+':';env['TEXMFVAR']=str(a/'.texlive-cache')
for name in (sys.argv[1:] or ['main','main-clean','response-to-reviewer-1','response-to-reviewer-2','response-to-reviewer-3']):
 out=a/name;out.mkdir(exist_ok=True)
 commands=[['lualatex','-interaction=nonstopmode','-halt-on-error','-file-line-error','-output-directory='+str(out),name+'.tex']]
 if name.startswith('main'): commands.append(['bibtex',name])
 commands.extend([commands[0]]*2)
 for i,cmd in enumerate(commands):
  with (out/f'build-{i+1}.txt').open('w') as log:r=subprocess.run(cmd,cwd=out if cmd[0]=='bibtex' else src,env=env,stdout=log,stderr=subprocess.STDOUT)
  if r.returncode:
   print((out/f'build-{i+1}.txt').read_text()[-6500:]);sys.exit(r.returncode)
 shutil.copy2(out/(name+'.pdf'),src/(name+'.pdf'))
 print(name,'built',flush=True)
 if name=='main':
  aux=(out/'main.aux').read_text(); lines=['% Generated from the final manuscript auxiliary labels.']
  for m in re.finditer(r'\\newlabel\{([^}]+)\}\{\{([^}]+)\}\{([^}]+)\}',aux):
   key,num,page=m.groups()
   if key.startswith(('sec:','tab:','eq:','lst:','fig:')):
    kind='절' if key.startswith('sec:') else '표' if key.startswith('tab:') else '식' if key.startswith('eq:') else '그림' if key.startswith('fig:') else '목록'
    label=f'{num}{kind}({page}쪽)' if kind=='절' else f'{kind} {num}({page}쪽)'
    lines.append(r'\expandafter\def\csname mloc@'+key+r'\endcsname{'+label+'}')
  (src/'manuscript-locations.tex').write_text('\n'.join(lines)+'\n')
