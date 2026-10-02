'use strict';
const CHOICES={target_status:['CONFIRMED','UNKNOWN','NOT_APPLICABLE'],zone_status:['CONFIRMED','UNKNOWN','NOT_APPLICABLE'],ped_truth:['TRUE','FALSE','UNKNOWN','CONFLICT','NOT_APPLICABLE'],road_context:['APPLICABLE','NOT_APPLICABLE','UNKNOWN'],road_truth:['TRUE','FALSE','UNKNOWN','CONFLICT','NOT_APPLICABLE'],control_context:['APPLICABLE','NOT_APPLICABLE','UNKNOWN'],control_truth:['TRUE','FALSE','UNKNOWN','CONFLICT','NOT_APPLICABLE']};
const TEXTS=['target_description','ped_reason','road_reason','control_reason'],FIELDS=[...Object.keys(CHOICES),...TEXTS];
const pointOK=p=>Array.isArray(p)&&p.length===2&&p.every(v=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1);
function polygonOK(p){
 if(!Array.isArray(p)||p.length<3||p.length>64||!p.every(pointOK)||new Set(p.map(v=>JSON.stringify(v))).size!==p.length)return false;
 const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
 const on=(a,b,c)=>Math.abs(cross(a,b,c))<1e-12&&Math.min(a[0],b[0])<=c[0]&&c[0]<=Math.max(a[0],b[0])&&Math.min(a[1],b[1])<=c[1]&&c[1]<=Math.max(a[1],b[1]);
 let area=0;for(let i=0;i<p.length;i++){const a=p[i],b=p[(i+1)%p.length];area+=a[0]*b[1]-b[0]*a[1];for(let j=i+2;j<p.length;j++){if(i===0&&j===p.length-1)continue;const c=p[j],d=p[(j+1)%p.length];if(cross(a,b,c)*cross(a,b,d)<0&&cross(c,d,a)*cross(c,d,b)<0||on(a,b,c)||on(a,b,d)||on(c,d,a)||on(c,d,b))return false;}}
 return Math.abs(area)>1e-8;
}
const FIELD_LABELS={target_status:'1. 대상 확인',zone_status:'1. 진입 영역 확인',target_description:'1. 대상 설명 또는 특정 불가 이유',ped_truth:'2. 보행자와 경로의 관계',ped_reason:'2. 보행자 판단 근거',road_context:'3. 다른 차량 양보 조건의 적용 여부',road_truth:'3. 다른 차량 양보 조건의 현재 상태',road_reason:'3. 다른 차량 판단 근거',control_context:'4. 다른 통제의 적용 여부',control_truth:'4. 다른 통제의 현재 상태',control_reason:'4. 다른 통제 판단 근거'};
function validationIssues(a,s){
 const issues=[],add=(field,message)=>issues.push({field,message});
 if(a.candidate_digest!==s.candidate_digest||a.event_timestamp_us!==s.event_timestamp_us)add('complete','다른 장면/시점의 답변입니다.');
 for(const [f,values] of Object.entries(CHOICES))if(!values.includes(a[f]))add(f,FIELD_LABELS[f]+'을 선택해 주세요.');
 const reasonChoice={target_description:'target_status',ped_reason:'ped_truth',road_reason:'road_context',control_reason:'control_context'};
 for(const f of TEXTS)if(typeof a[f]!=='string'||a[f].length>4000||(!a[f].trim()&&a[reasonChoice[f]]!=='NOT_APPLICABLE'))add(f,FIELD_LABELS[f]+'를 입력해 주세요. 해당 없음이면 생략할 수 있습니다.');
 if(a.target_point!==null&&!pointOK(a.target_point))add('pointMode','대상 점 좌표가 잘못되었습니다. 다시 찍거나 삭제해 주세요.');
 if(!Array.isArray(a.zone_polygon)||a.zone_polygon.length&&!polygonOK(a.zone_polygon))add('polygonMode','영역의 점 수·중복·선 교차를 확인해 주세요.');
 if(a.target_status==='CONFIRMED'&&a.target_point===null)add('pointMode','대상을 확인했다면 위치에 점을 찍어 주세요.');
 if(a.zone_status==='CONFIRMED'&&(!Array.isArray(a.zone_polygon)||!a.zone_polygon.length))add('polygonMode','영역을 확인했다면 꼭짓점 3개 이상으로 표시해 주세요.');
 for(const p of ['road','control'])if((a[p+'_context']==='NOT_APPLICABLE')!==(a[p+'_truth']==='NOT_APPLICABLE')||a[p+'_context']==='UNKNOWN'&&a[p+'_truth']!=='UNKNOWN')add(p+'_truth',FIELD_LABELS[p+'_truth']+': 적용 여부가 해당 없음이면 상태도 해당 없음, 판단 불가이면 상태도 판단 불가를 선택해 주세요.');
 if(['TRUE','FALSE'].includes(a.ped_truth)&&(a.target_status!=='CONFIRMED'||a.zone_status!=='CONFIRMED'))add('ped_truth','보행자 관계를 확인하려면 대상과 영역 확인이 필요합니다. 불명확하면 판단 불가를 선택하세요.');
 return issues;
}
function validate(a,s){const issues=validationIssues(a,s);if(issues.length){const error=Error(issues.map(i=>i.message).join('\n'));error.issues=issues;throw error;}return a;}
if(typeof module!=='undefined')module.exports={validate,polygonOK,pointOK,FIELDS};
if(typeof document!=='undefined'){
 const $=id=>document.getElementById(id),P=JSON.parse($('packet').textContent),key='guardsynth-source-gap:'+P.packet_sha256;
 const empty=s=>({...Object.fromEntries(FIELDS.map(f=>[f,''])),candidate_digest:s.candidate_digest,event_timestamp_us:s.event_timestamp_us,target_point:null,zone_polygon:[],reviewed_at:null});
 let answers=Object.fromEntries(P.scenes.map(s=>[s.candidate_digest,empty(s)])),completed=new Set(),index=0,frame=0,mode='view';
 const scene=()=>P.scenes[index],answer=()=>answers[scene().candidate_digest],status=t=>$('status').textContent=t;
 const labels={TRUE:'확인됨',FALSE:'해소 확인',UNKNOWN:'판단 불가',CONFLICT:'근거 충돌',NOT_APPLICABLE:'해당 없음',APPLICABLE:'해당함'};
 for(const f of ['ped_truth','road_context','road_truth','control_context','control_truth'])for(const v of ['',...CHOICES[f]]){const o=document.createElement('option');o.value=v;o.textContent=v?labels[v]:'선택';$(f).appendChild(o);}
 function capture(){let different=false;for(const f of FIELDS){if(answer()[f]!==$(f).value)different=true;answer()[f]=$(f).value;}return different;}
 function snapshot(){return {kind:'DRAFT',review_version:P.review_version,packet_sha256:P.packet_sha256,reviewer_id:$('reviewer').value,records:Object.values(answers),completed:[...completed]};}
 function save(){try{localStorage.setItem(key,JSON.stringify(snapshot()));return true;}catch{status('자동 저장하지 못했습니다. 전체 초안 JSON으로 보관해 주세요.');return false;}}
 function menu(){const selected=String(index);$('scene').replaceChildren();P.scenes.forEach((s,i)=>{const o=document.createElement('option');o.value=i;o.textContent=(completed.has(s.candidate_digest)?'완료 · ':'미완료 · ')+s.label;$('scene').appendChild(o);});$('scene').value=selected;const count='완료 '+completed.size+' / '+P.scenes.length;$('progress').textContent=count;$('completionProgress').textContent=count+' · 현재 장면 '+(completed.has(scene().candidate_digest)?'완료':'미완료');}
 function clearValidation(){$('validation').textContent='';for(const f of [...FIELDS,'pointMode','polygonMode'])$(f).setAttribute('aria-invalid','false');}
 function showValidation(error){const issues=error.issues||[{field:'complete',message:error.message}];$('validation').textContent='아직 완료되지 않았습니다. 아래 '+issues.length+'개 항목을 확인해 주세요.\n'+issues.map(i=>'• '+i.message).join('\n');status('답변과 도형은 초안으로 유지됩니다. 표시된 항목을 확인한 뒤 답변 완료를 다시 누르세요.');for(const i of issues)$(i.field).setAttribute('aria-invalid','true');const first=$(issues[0].field);first.focus?.();first.scrollIntoView?.({block:'center',behavior:'smooth'});}
 function changed(force=true){const different=capture();if(force||different){completed.delete(scene().candidate_digest);answer().reviewed_at=null;}clearValidation();menu();save();}
 function draw(){const s=scene(),f=s.frames[frame];$('image').src=f.data_url;$('frameIndex').value=frame;$('clock').textContent=(f.timestamp_us/1e6).toFixed(6)+'초'+(frame===s.frames.length-1?' · 판단 프레임':' · 과거');$('prevFrame').disabled=frame===0;$('nextFrame').disabled=frame===s.frames.length-1;
  const svg=$('marks');svg.replaceChildren();if(frame!==s.frames.length-1)return;
  function add(tag,attrs){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,v);svg.appendChild(e);}
  for(const m of s.machine_points)add('circle',{cx:m.point[0]*1000,cy:m.point[1]*1000,r:9,fill:'none',stroke:'#da6dff','stroke-width':3,'vector-effect':'non-scaling-stroke'});
  const a=answer();if(a.zone_polygon.length)add('polygon',{points:a.zone_polygon.map(p=>p.map(v=>v*1000).join(',')).join(' '),fill:'#ffcd0033',stroke:'#ffcd00','stroke-width':2,'vector-effect':'non-scaling-stroke'});
  for(const p of a.zone_polygon)add('circle',{cx:p[0]*1000,cy:p[1]*1000,r:4,fill:'#ffcd00'});
  if(a.target_point)add('circle',{cx:a.target_point[0]*1000,cy:a.target_point[1]*1000,r:7,fill:'none',stroke:'#ff4242','stroke-width':3,'vector-effect':'non-scaling-stroke'});
 }
 const priorLabels={HAZARD_VISIBLE:'위험이 보임',NO_HAZARD_VISIBLE:'위험이 보이지 않음',STATE_TRANSITION_VISIBLE:'상태 변화가 보임'};
 function loadScene(){const s=scene();frame=s.frames.length-1;mode='view';$('mode').textContent='보기 모드';for(const f of FIELDS)$(f).value=answer()[f];$('heading').textContent=s.label;$('coc').textContent=s.original_coc;$('prior').textContent='재사용한 기존 시간창 답변: '+(priorLabels[s.prior_observation]||'이전 영상 답변 없음')+' · geometry 검토 이력 유지. 현재 판단 시점의 답변으로 자동 복사하지 않았습니다.';$('machine').textContent='기계 연결 대상 ID: '+(s.source_person_ids.join(', ')||'없음')+' / 시점 내 통제 주석 '+s.control_count+'개. 주석 존재만으로 적용성이나 행동 정답이 확정되지는 않습니다.';$('frameIndex').max=s.frames.length-1;menu();draw();}
 function switchScene(i){changed(false);index=Math.max(0,Math.min(P.scenes.length-1,i));loadScene();}
 $('scene').onchange=e=>switchScene(Number(e.target.value));$('prevScene').onclick=()=>switchScene(index-1);$('nextScene').onclick=()=>switchScene(index+1);
 for(const f of FIELDS)$(f).oninput=()=>changed(false);$('reviewer').oninput=save;$('form').onsubmit=e=>e.preventDefault();
 function atEvent(){frame=scene().frames.length-1;draw();}
 function setMode(m){mode=m;atEvent();$('mode').textContent=m==='point'?'대상 중심을 클릭하세요':m==='polygon'?'진입 영역 꼭짓점을 순서대로 클릭하세요':'보기 모드';}
 $('pointMode').onclick=()=>setMode('point');$('polygonMode').onclick=()=>setMode('polygon');$('viewMode').onclick=()=>{setMode('view');status('그리기만 종료했습니다. 아래 질문에 답한 후 이 장면 답변 완료를 눌러 주세요.');};
 $('clearPoint').onclick=()=>{if(answer().target_point===null){setMode('view');status('삭제할 대상 점이 없습니다.');return;}answer().target_point=null;$('target_status').value='';changed();setMode('view');status('대상 점을 삭제했습니다. 영역과 다른 답변은 유지됩니다. 대상 확인을 다시 선택해 주세요.');};
 $('marks').onclick=e=>{if(mode==='view'||frame!==scene().frames.length-1)return;const rect=$('marks').getBoundingClientRect(),p=[(e.clientX-rect.left)/rect.width,(e.clientY-rect.top)/rect.height].map(v=>Math.max(0,Math.min(1,v)));if(mode==='point'){answer().target_point=p;$('target_status').value='';}else{if(answer().zone_polygon.length>=64)return;answer().zone_polygon.push(p);$('zone_status').value='';}changed();draw();};
 $('undo').onclick=()=>{answer().zone_polygon.pop();$('zone_status').value='';changed();draw();};$('clearZone').onclick=()=>{if(answer().zone_polygon.length&&!confirm('현재 장면의 영역을 지울까요?'))return;answer().zone_polygon=[];$('zone_status').value='';changed();draw();};
 $('prevFrame').onclick=()=>{frame=Math.max(0,frame-1);draw();};$('nextFrame').onclick=()=>{frame=Math.min(scene().frames.length-1,frame+1);draw();};$('frameIndex').oninput=e=>{frame=Number(e.target.value);draw();};$('eventFrame').onclick=atEvent;
 $('zoom').onclick=()=>{$('zoomImage').src=scene().frames[frame].data_url;$('dialog').showModal();};$('closeZoom').onclick=()=>$('dialog').close();$('native').onclick=()=>$('zoomImage').classList.toggle('native');
 function complete(){if(capture()){completed.delete(scene().candidate_digest);answer().reviewed_at=null;}try{validate(answer(),scene());}catch(error){menu();save();throw error;}clearValidation();answer().reviewed_at=new Date().toISOString();completed.add(scene().candidate_digest);menu();return save();}
 $('complete').onclick=()=>{try{const saved=complete();status('이 장면 완료 · '+completed.size+' / '+P.scenes.length+(saved?' · 초안 자동 저장됨. 완료한 장면의 답변 JSON도 저장해 주세요.':' · 브라우저 자동 저장 실패. 새로고침 전에 답변 JSON을 반드시 저장해 주세요.'));}catch(e){showValidation(e);}};
 function download(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 $('export').onclick=()=>{try{capture();if(!$('reviewer').value.trim())throw Error('검토자 이름/ID를 입력하세요.');if(!completed.has(scene().candidate_digest)){try{complete();}catch(e){if(!completed.size)throw e;}}const records=P.scenes.filter(s=>completed.has(s.candidate_digest)).map(s=>validate(answers[s.candidate_digest],s));if(!records.length)throw Error('완료한 장면이 없습니다.');download({review_version:P.review_version,packet_sha256:P.packet_sha256,reviewer_id:$('reviewer').value.trim(),records},'paper1_source_gap_review.json');status(records.length+'장면 답변 저장을 요청했습니다. 미완료 장면은 포함하지 않았습니다.');}catch(e){status(e.message);}};
 $('draft').onclick=()=>{capture();save();download(snapshot(),'paper1_source_gap_draft.json');};
 function restore(data){if(data.packet_sha256!==P.packet_sha256||data.review_version!==P.review_version||!Array.isArray(data.records)||typeof data.reviewer_id!=='string')throw Error('다른 검토 자료의 파일입니다.');const merged=structuredClone(answers),seen=new Set();for(const a of data.records){const s=P.scenes.find(s=>s.candidate_digest===a.candidate_digest);if(!s||seen.has(a.candidate_digest)||a.event_timestamp_us!==s.event_timestamp_us)throw Error('알 수 없거나 중복된 장면입니다.');seen.add(a.candidate_digest);if(!FIELDS.every(f=>typeof a[f]==='string')||a.target_point!==null&&!pointOK(a.target_point)||!Array.isArray(a.zone_polygon)||a.zone_polygon.length>64||!a.zone_polygon.every(pointOK)||Object.entries(CHOICES).some(([f,v])=>a[f]!==''&&!v.includes(a[f])))throw Error('잘못된 초안 필드입니다.');merged[a.candidate_digest]=a;}
  const done=new Set(data.kind==='DRAFT'?data.completed:data.records.map(a=>a.candidate_digest));for(const id of done){const s=P.scenes.find(s=>s.candidate_digest===id);if(!s||!seen.has(id))throw Error('잘못된 완료 목록입니다.');validate(merged[id],s);if(!merged[id].reviewed_at)throw Error('완료 시각이 없습니다.');}answers=merged;completed=done;$('reviewer').value=data.reviewer_id;loadScene();}
 $('import').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;restore(JSON.parse(await f.text()));save();status('답변과 도형을 복원했습니다.');}catch(e){status(e.message);}};
 $('folder').textContent=P.submission_directory;try{const data=localStorage.getItem(key);if(data)restore(JSON.parse(data));}catch(e){status('자동 복원 실패: '+e.message+' · 저장한 JSON으로 복원할 수 있습니다.');}loadScene();
}
