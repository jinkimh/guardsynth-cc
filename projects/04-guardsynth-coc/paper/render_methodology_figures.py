"""Publication-vector diagrams for the approved GuardSynth methodology revision.

Owner: guardsynth-coc. No model outputs or measured performance are plotted.
Run with the paper environment's Python; PNG previews accompany PDF vectors.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.font_manager import FontProperties

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'PROJECT_REGISTRY.json').exists())
OUT = ROOT/'artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/methodology-2026-09-30-005'
assert not (OUT/'RESULT.json').exists(), 'Completed snapshots are immutable'
FIG = OUT/'figures'
FIG.mkdir(parents=True, exist_ok=True)
FONT = FontProperties(fname='/home/jinhyun/.local/share/fonts/NotoSansCJK-Regular.ttc')
# Noto CJK uses CFF outlines: Type 3 preserves vector glyphs without wrapping
# CFF data as a TrueType font, which some PDF readers cannot render.
plt.rcParams.update({'pdf.fonttype':3, 'ps.fonttype':3, 'font.size':10})
INK, BLUE, GREEN, RED = '#173E59', '#E7F0F7', '#E3F2EA', '#F8E5E1'

def canvas(height=4.4, ymax=8):
    f,a=plt.subplots(figsize=(8,height)); a.set(xlim=(0,12),ylim=(0,ymax)); a.axis('off')
    f.subplots_adjust(left=.015,right=.985,top=.98,bottom=.02)
    return f,a

def text(a,x,y,s,size=10,**kw):
    return a.text(x,y,s,fontproperties=FONT,fontsize=size,color=INK,
                  ha=kw.pop('ha','center'),va='center',**kw)

def box(a,x,y,w,h,s,color=BLUE,size=10):
    a.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=.06',
                             facecolor=color,edgecolor=INK,linewidth=.8))
    text(a,x+w/2,y+h/2,s,size)

def arrow(a,start,end,dashed=False,curve=0):
    a.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=10,
                               linewidth=1,color=INK,linestyle='--' if dashed else '-',
                               connectionstyle=f'arc3,rad={curve}',shrinkA=3,shrinkB=3))

def elbow(a, points, dashed=False, tip=True):
    """Exact edge anchors; only horizontal/vertical segments, no box overlap."""
    assert all(x1==x2 or y1==y2 for (x1,y1),(x2,y2) in zip(points,points[1:]))
    xs,ys=zip(*points)
    a.plot(xs,ys,color=INK,lw=.85,ls='--' if dashed else '-',solid_capstyle='butt')
    if tip:
        start,end=points[-2:]
        a.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=9,
                    linewidth=.85,color=INK,shrinkA=0,shrinkB=0,
                    linestyle='--' if dashed else '-'))

def save(f,name,lang):
    for ext in ('pdf','png'):
        f.savefig(FIG/f'{name}-{lang}.{ext}',dpi=170,bbox_inches='tight',pad_inches=.08)
    plt.close(f)

for lang in ('ko','en'):
    ko=lang=='ko'
    def tr(k,e): return k if ko else e
    f,a=canvas(2.75,5.1)
    inputs=[tr('원 CoC\n행동·판단 이유','Original CoC\nAction rationale'),
            tr('관측 사실\n대상·사건·시점','Observations\nEntities, events, time'),
            tr('규칙\n제한·해제 조건','Rules\nRestriction and release'),
            tr('모델링 가정\n해석·검증 범위','Assumptions\nInterpretation scope')]
    for x,s in zip((.2,3.2,6.2,9.2),inputs):
        box(a,x,3.8,2.6,.95,s,BLUE,9.5)
        elbow(a,[(x+1.3,3.8),(x+1.3,3.35)],tip=False)
    elbow(a,[(1.5,3.35),(10.5,3.35)],tip=False)
    elbow(a,[(1.5,3.35),(1.5,2.85)])
    stages=[tr('01  후보·근거 연결','01  Bind candidates'),
            tr('02  EBLC 명세\n필드·타입·범위 검사','02  Specify EBLC\nField, type, scope checks'),
            tr('03  Core → SMT\n기대 판정 확인','03  Core → SMT\nCheck expected verdicts'),
            tr('04  CNL 생성\n원 CoC와 결합','04  Generate CNL\nCombine with CoC')]
    for x,s in zip((.2,3.2,6.2,9.2),stages):
        box(a,x,1.75,2.6,1.1,s,GREEN if x==9.2 else BLUE,9.5)
    for x in (2.8,5.8,8.8):elbow(a,[(x,2.3),(x+.4,2.3)])
    elbow(a,[(7.5,1.75),(7.5,1.2),(4.5,1.2),(4.5,1.75)],True)
    text(a,6,.76,tr('예상 불일치 / UNKNOWN → 명세·질의 재검토',
                    'Mismatch / UNKNOWN → revise specification or query'),9)
    text(a,1.5,1.08,tr('실제: 사람 확인\n합성: 공급 조건','Real: human review\nSynthetic: supplied inputs'),8)
    text(a,10.5,1.08,tr('영상·후보와 함께\n학습 입력 구성','With images and\ncandidate actions'),8)
    text(a,6,.20,tr('실선: 처리 순서   ·   점선: 재검토   ·   미확정 후보는 보류',
                    'Solid: processing   ·   Dashed: revision   ·   Unresolved candidates are held'),8)
    save(f,'method-flow',lang)

    f,a=canvas(3.9,8.7)
    text(a,.25,8.40,tr('(a) 개별 의무 j의 상태 전이','(a) State transitions of obligation j'),10,ha='left')
    box(a,.55,6.40,3.4,.70,tr('비활성 · 초기 또는 해제','INACTIVE · initial / released'),BLUE,9)
    box(a,8.05,6.40,3.4,.70,tr('활성 · 해당 진입 금지','ACTIVE · entry restricted'),RED,9)
    arrow(a,(3.95,6.96),(8.05,6.96),curve=-.18)
    text(a,6,7.65,'on[j,t] = valid AND truth=TRUE',8.5)
    arrow(a,(8.05,6.52),(3.95,6.52),curve=-.18)
    text(a,6,5.72,'clear[j,t] = valid AND truth=FALSE',8.5)
    arrow(a,(1.40,7.10),(3.10,7.10),curve=-.45)
    arrow(a,(8.90,7.10),(10.60,7.10),curve=-.45)
    text(a,2.25,7.97,tr('그 외: 유지','Otherwise: retain'),8.5)
    text(a,9.75,7.97,tr('그 외: 유지','Otherwise: retain'),8.5)

    # Transfer the clearance predicate, never the INACTIVE state, to the gate.
    elbow(a,[(6,5.42),(6,3.80),(1.80,3.80),(1.80,3.40)],dashed=True)
    text(a,6.22,4.98,tr('동일 clear 조건값 전달',
                       'Same clear value (not a state)'),8.5,ha='left')
    text(a,.25,4.35,tr('(b) 전체 진입 허용 판단','(b) Combined entry permission'),10,ha='left')
    box(a,.30,2.70,3.0,.70,'clear[j,t]',BLUE,9)
    box(a,.30,1.40,3.0,.70,tr('다른 의무의 clear[k,t]\n(k ≠ j)',
                            'Other clear[k,t]\n(k ≠ j)'),BLUE,9)
    box(a,4.60,1.95,3.65,1.0,tr('모든 clear가 참인가?\nAND across all obligations',
                              'Are ALL clear values true?\nAND across all obligations'),GREEN,9)
    elbow(a,[(3.30,3.05),(3.85,3.05),(3.85,2.65),(4.60,2.65)],dashed=True)
    elbow(a,[(3.30,1.75),(3.85,1.75),(3.85,2.25),(4.60,2.25)],dashed=True)
    box(a,9.0,1.95,2.70,1.0,tr('진입 허용 여부\nentry_permitted[t]',
                             'Entry permission\nentry_permitted[t]'),GREEN,9)
    elbow(a,[(8.25,2.45),(9.0,2.45)],dashed=True)
    text(a,6,.95,tr('허용 ≠ 강제 · 비활성만으로는 허용되지 않음 · 불확실 근거 → 검토',
                    'Permission ≠ obligation · Inactivity alone is insufficient · Unresolved → review'),8.5)
    text(a,6,.30,tr('실선: 상태 전이   |   점선: 조건값 전달 (상태 전이·포함 관계 아님)',
                    'Solid: state transition   |   Dashed: value flow (not a transition or containment)'),8.5)
    save(f,'lifecycle',lang)

    f,a=canvas(2.15,3.8)
    rows=[(2.95,tr('CoC: 보행자에게 양보 후 진행','CoC: yield, then proceed'),
                 tr('주체 ego / 대상 conflict zone\n관련 제한 후보 식별','Actor ego / target conflict zone\nIdentify restriction candidate'),BLUE),
          (2.1,tr('환경 관측: 영역 해소 11.0초','Environment: clear at 11.0 s'),
                 'Query binding: clear_ms = 11000',GREEN),
          (1.25,tr('공급 규칙: 해소 후 최소 0.5초','Supplied rule: wait at least 0.5 s'),
                 'Contract: release_clear_ms = 500',BLUE),
          (.4,tr('모델 가정: 이후 재점유 없음','Model assumption: no reoccupation'),
                 tr('단일 해소 시점 + 경과 시간으로 해석','Interpret one clear time + elapsed time'),GREEN)]
    for y,l,r,c in rows:
        box(a,.2,y,4.7,.64,l,c,9.5); box(a,5.5,y,6.3,.64,r,c,9.2)
        elbow(a,[(4.9,y+.32),(5.5,y+.32)])
    save(f,'evidence-map',lang)

    f,a=plt.subplots(figsize=(8,3.35))
    f.subplots_adjust(left=.16,right=.98,bottom=.25,top=.80)
    for y,d in [(1,.5),(0,1.5)]:
        edge=11+d
        a.broken_barh([(10.15,edge-10.15)],(y-.16,.32),facecolors=RED,edgecolors=INK,linewidth=.6,hatch='///')
        a.broken_barh([(edge,13.05-edge)],(y-.16,.32),facecolors=GREEN,edgecolors=INK,linewidth=.6)
        a.plot(edge,y,'o',color='#24754C',markersize=7)
        for name,x in [('A',10.5),('B',11.5),('C',12.5)]:
            a.plot(x,y+.29,marker='v',color=INK,markersize=5)
            text(a,x,y+.48,name,10)
        text(a,(10.15+edge)/2,y,tr('진입 금지','Entry forbidden'),9)
        if d==.5: text(a,12.25,y,tr('진입 허용','Entry permitted'),9)
        else: text(a,12.78,y,tr('허용','Permitted'),8)
    a.axvline(11,ymax=.79,color=INK,linestyle='--',linewidth=1)
    a.set(xlim=(10.15,13.05),ylim=(-.48,1.92),xticks=[10.5,11,11.5,12,12.5,13],yticks=[0,1])
    a.set_yticklabels([tr('대기 1.5초','Wait 1.5 s'),tr('대기 0.5초','Wait 0.5 s')],fontproperties=FONT)
    a.set_xlabel(tr('후보 진입 시각 (초)','Candidate entry time (s)'),fontproperties=FONT)
    text(a,11,1.76,tr('영역 해소 11.0초','Clear at 11.0 s'),9)
    for side in ('top','right','left'): a.spines[side].set_visible(False)
    a.tick_params(axis='y',length=0)
    f.text(.52,.025,tr('구성된 계약 의미 예제 · D는 비진입 후보 · 성능 측정 그래프 아님',
                      'Constructed contract example · D does not enter · Not a performance plot'),
           fontproperties=FONT,fontsize=9,ha='center',color=INK)
    save(f,'temporal-boundary',lang)

    f,a=canvas(2.15,3.7)
    rows=[(2.85,'target + hold','Do not enter the pedestrian conflict\nzone while it is occupied.',BLUE),
          (1.97,'enters =>\nentry_ms >= clear_ms + duration','Enter only after ...',GREEN),
          (1.09,'release_clear_ms = 500','... clear for at least 0.5 s.',BLUE)]
    for y,l,r,c in rows:
        box(a,.2,y,4.8,.65,l,c,9); box(a,5.55,y,6.25,.65,r,c,9.5)
        elbow(a,[(5,y+.325),(5.55,y+.325)])
    text(a,6,.50,tr('모델 입력: CoC + CNL  |  별도 추적: 버전·출처\n해석 맥락: 단일 해소·재점유 없음',
                    'Model input: CoC + CNL  |  Metadata: version and sources\nContext: single clearance, no reoccupation'),8.5)
    save(f,'cnl-map',lang)

(OUT/'figure_data.json').write_text(json.dumps({
    'project_id':'guardsynth-coc', 'kind':'CONSTRUCTED_SEMANTIC_ILLUSTRATIONS',
    'clear_time_s':11.0,'duration_s':[.5,1.5],'release_time_s':[11.5,12.5],
    'candidates':{'A':10.5,'B':11.5,'C':12.5,'D':None},
    'lifecycle_truth':['TRUE','UNKNOWN','FALSE','TRUE'],
    'lifecycle_valid':[True]*4, 'prior_active':False,
    'expected_active':[True,True,False,True],
    'expected_entry_permitted':[False,False,True,False],
    'learning_performance_data':False},indent=2)+'\n')
print(FIG)
