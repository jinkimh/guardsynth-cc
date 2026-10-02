"use strict";
const API = "/api/studio/v1";
const $ = id => document.getElementById(id);
const state = {csrf:null, moment:null, moments:[], extraction:null, videos:[], lineages:[], drawing:{}, busy:false};
const kinds = ["coc","action","source","binding","proposal","contract","cnl","combined","applicability","context","derived"];
const editable = kinds.filter(k => !["cnl","combined"].includes(k));
const texts = {coc:"CoC",action:"행동",source:"출처",binding:"관찰 결합",proposal:"제약 제안",contract:"계약",cnl:"CNL",combined:"결합 CoC",applicability:"적용성",context:"입력 context",derived:"수동 파생문"};
const cocFields = ["observations","relations","assumptions","unknowns","action_rationale","edited_text"];
const cocLabels = ["관찰 사실","관계","가정","미확인","행동 근거","승인할 CoC 본문"];
const actionIds = ["ENTER_ZONE","DEFER_ENTRY","MAINTAIN_SPEED","HOLD_STOP"];
const predicateIds = {ped:"pedestrian_conflict",road:"main_road_yield_required"};
const clone = value => JSON.parse(JSON.stringify(value));
const key = () => crypto.randomUUID();
function error(e){$("error").textContent=e.message || String(e);}
function button(text, fn){const b=document.createElement("button");b.textContent=text;b.onclick=()=>Promise.resolve().then(fn).catch(error);return b;}
function bind(id, fn){$(id).onclick=()=>Promise.resolve().then(fn).catch(error);}
async function api(path, method="GET", body, idempotency=key()){
  const headers={};
  if(method!=="GET"){headers["X-CSRF-Token"]=state.csrf;headers["Idempotency-Key"]=idempotency;}
  if(body && !(body instanceof FormData)){headers["Content-Type"]="application/json";if(method==="PATCH")headers["If-Match"]=String(body.revision);body=JSON.stringify(body);}
  const r=await fetch(API+path,{method,headers,body,credentials:"same-origin"});
  const value=await r.json();if(!r.ok){const e=new Error(`${r.status}: ${value.message}`);e.status=r.status;throw e;}return value;
}
let outbox;
const dbReady = new Promise((resolve,reject)=>{const r=indexedDB.open("guardsynth-studio-outbox",1);r.onupgradeneeded=()=>r.result.createObjectStore("edits",{keyPath:"id"});r.onsuccess=()=>{outbox=r.result;resolve();};r.onerror=()=>reject(r.error);});
async function dbOp(method,value){await dbReady;return new Promise((resolve,reject)=>{const tx=outbox.transaction("edits",method==="getAll"?"readonly":"readwrite");const s=tx.objectStore("edits");const r=method==="getAll"?s.getAll():s[method](value);tx.oncomplete=()=>resolve(r.result);tx.onerror=()=>reject(tx.error);});}
let timer, flushing=null;
async function queue(kind,payload){
  if(!state.moment)return;
  await dbOp("put",{id:key(),moment_id:state.moment.id,revision:state.moment.revision,kind,payload,created:Date.now(),sent:false});
  $("save_state").textContent="임시 저장 중";
  clearTimeout(timer);timer=setTimeout(()=>flush().catch(error),500);
}
async function flush(){
  if(flushing)return flushing;
  flushing=(async()=>{
    while(true){
    const rows=(await dbOp("getAll")).sort((a,b)=>a.created-b.created);
    if(!rows.length)break;
    for(const row of rows){
      row.sent=true;await dbOp("put",row);
      let result;
      try{result=await api(`/moments/${row.moment_id}`,"PATCH",{revision:row.revision,kind:row.kind,payload:row.payload},row.id);}
      catch(e){if(e.status===409){const current=await api(`/moments/${row.moment_id}`);state.conflict={row,current};$("conflict_diff").textContent=JSON.stringify({moment:row.moment_id,local:row.payload,current:current.components[row.kind]?.payload},null,2);if(!$("conflict").open)$("conflict").showModal();}throw e;}
      await dbOp("delete",row.id);
      // Only advance unsent edits after an acknowledged write from this outbox.
      for(const next of await dbOp("getAll"))if(next.moment_id===row.moment_id && !next.sent){next.revision=result.revision;await dbOp("put",next);const local=rows.find(r=>r.id===next.id);if(local)local.revision=result.revision;}
      if(state.moment?.id===row.moment_id){state.moment=result;renderControls();}
    }
    }
    $("save_state").textContent="저장됨";
  })().catch(e=>{$("save_state").textContent="저장 실패 · 초안 유지 (409는 최신본과 비교 필요)";throw e;}).finally(()=>{flushing=null;});
  return flushing;
}
function data(kind){return state.moment?.components[kind]?.payload || {};}
async function edit(kind,payload){await queue(kind,payload);await flush();await loadMoment(state.moment.id);}
async function approve(kind,decision){await flush();const m=await api(`/moments/${state.moment.id}`),c=m.components[kind];if(!c)throw Error("먼저 초안을 저장하세요");await api("/approvals","POST",{items:[{moment_id:m.id,revision:m.revision,stage:kind,component_id:c.id,dependency_digest:c.dependency_digest,decision}]});await loadMoment(m.id);}
function renderControls(){for(const kind of kinds){const host=$(kind+"_controls");if(!host)continue;host.replaceChildren();const c=state.moment?.components[kind],a=state.moment?.approvals[kind];const status=document.createElement("span");status.textContent=c?.stale?"STALE · 재검토":a?.decision || "미승인";status.className=c?.stale?"stale":"";host.append(status);for(const [text,d] of [["승인","APPROVE"],["보류","HOLD"],["거절","REJECT"]])host.append(button(text,()=>approve(kind,d)));}}
async function loadMoment(id){await flush();state.moment=await api(`/moments/${id}`);const m=state.moment;$("timestamp").textContent=`시점 ${m.ordinal+1} · t0 ${(m.t0_us/1e6).toFixed(6)}s · revision ${m.revision}`;
  $("strip").replaceChildren();for(const f of m.frames){const b=button(`${(f.timestamp_us/1e6).toFixed(3)}s`,()=>selectOrdinal(f.ordinal));const img=document.createElement("img");img.src=API+"/assets/"+f.asset_id;img.alt=`frame ${f.ordinal+1}`;b.prepend(img);$("strip").append(b);}
  $("current_frame").src=API+"/assets/"+m.frame.asset_id;$("previous").disabled=m.ordinal===0;$("next").disabled=m.ordinal===state.moments.length-1;
  for(const f of cocFields)$("coc_"+f).value=data("coc")[f] || "";$("causal").checked=!!data("coc").causal_confirmed;$("leakage").checked=!!data("coc").leakage;
  for(const a of actionIds)$("action_"+a).value=data("action").labels?.[a] || "";$("action_reason").value=data("action").reason || "";
  const source=data("source").records?.[0] || {};for(const f of ["id","kind","version","locator","quote"])$("source_"+f).value=source[f] || (f==="kind"?"POLICY":f==="id"?"policy_entry":"");$("source_reviewed").checked=!!source.reviewed;
  state.drawing=clone(data("binding"));$("zone_name").value=state.drawing.zone_name || "검토 진입 영역";$("target_name").value=state.drawing.target_name || "검토 대상";$("binding_confirmed").checked=state.drawing.binding_status==="BOUND";
  for(const oid of Object.keys(predicateIds)){const v=state.drawing.event_predicates?.[oid] || {};$(oid+"_truth").value=v.truth || "UNKNOWN";$(oid+"_valid").checked=!!v.evidence_valid;$(oid+"_context").checked=!!v.contextual_target_confirmed;}
  draw();renderControls();$("check_summary").textContent=data("check").status?`${data("check").status} · 질의 ${data("check").results?.reduce((n,r)=>n+r.query_count,0)}개 · 장면 사실 인증 아님`:"검사 미실행";
  $("cnl_text").textContent=data("cnl").text_ko || "";$("combined_text").textContent=data("combined").text || "";$("eligibility").textContent=JSON.stringify(m.eligibility,null,2);
  $("applicability").value=data("applicability").status || "UNREVIEWED";$("applicability_reason").value=data("applicability").reason || "";$("candidate_reviewed").checked=!!data("applicability").candidate_reviewed;
  $("raw_output").textContent=JSON.stringify(data("coc").raw_output || {},null,2);loadJson();
  await api(`/moments/${m.id}/exposure`,"POST",{revision:m.revision,panel:"moment_view"});
}
async function selectOrdinal(i){if(i>=0 && i<state.moments.length)await loadMoment(state.moments[i].id);}
async function openExtraction(id){await flush();state.extraction=id;await refreshMoments();if(state.moments.length)await selectOrdinal(0);}
async function refreshMoments(){if(!state.extraction)return;const result=await api(`/extractions/${state.extraction}/moments`);state.moments=result.moments;$("counts").textContent=`검토완료 ${result.review_complete} / ${result.moments.length} · 학습적격 ${result.training_eligible}`;$("moments").replaceChildren();for(const m of state.moments)$("moments").append(button(`${m.ordinal+1}: ${(m.t0_us/1e6).toFixed(3)}s · ${m.completion?.state || "초안"}`,()=>loadMoment(m.id)));}
async function refresh(){const r=await api("/videos");state.videos=r.videos;state.lineages=r.lineages;$("videos").replaceChildren();for(const v of r.videos){const div=document.createElement("div");div.textContent=`${v.name} · ${v.status}`;const details=document.createElement("details"),summary=document.createElement("summary"),identity=document.createElement("p");summary.textContent="원본 계보 식별자";identity.textContent=`video: ${v.id} · group: ${v.lineage_group_id}`;details.append(summary,identity);div.append(details);const interval=document.createElement("input");interval.type="number";interval.value="1";interval.min="0.1";interval.max="60";interval.step="0.1";div.append(interval,button("초 간격 추출",()=>api(`/videos/${v.id}/extractions`,"POST",{interval_s:Number(interval.value)})));for(const ex of r.extractions.filter(e=>e.video_id===v.id))div.append(button(`추출 ${ex.status}`,()=>openExtraction(ex.id)));$("videos").append(div);}await refreshMoments();}
async function job(type){
  if(state.busy)return;
  state.busy=true;
  const controls=["generate_coc","generate_proposal","check","render","combine","range_generate"].map($);
  controls.forEach(b=>b.disabled=true);
  $("error").textContent="작업 중입니다. 결과를 기다려 주세요. 같은 요청을 다시 누르지 않아도 됩니다.";
  try{await flush();const r=await api(`/moments/${state.moment.id}/jobs`,"POST",{revision:state.moment.revision,type});await pollJob(r.job_id);$("error").textContent="작업 완료 · 저장된 결과를 불러왔습니다.";}
  finally{state.busy=false;controls.forEach(b=>b.disabled=false);}
}
async function pollJob(id){for(let i=0;i<650;i++){const j=await api(`/jobs/${id}`);if(!["QUEUED","RUNNING"].includes(j.status)){if(j.status!=="SUCCEEDED"){if(j.error?.code==="PROVIDER_STALE" || j.status==="STALE_RESULT"){if(state.moment?.id===j.moment_id)await loadMoment(j.moment_id);throw Error("다른 저장 또는 생성으로 입력 버전이 바뀌었습니다. 현재 시점의 최신 저장 결과를 확인하세요. 자동 재시도하지 않았습니다.");}throw Error(`${j.status}: ${j.error?.message || "결과 미적용"}`);}if(state.moment)await loadMoment(state.moment.id);await refresh();return j;}await new Promise(r=>setTimeout(r,500));}throw Error("작업 상태에서 결과를 확인하세요");}
function draw(){const svg=$("overlay");svg.replaceChildren();const ns="http://www.w3.org/2000/svg";const points=state.drawing.zone_polygon || state.drawing.draft_zone_points;if(points?.length){const p=document.createElementNS(ns,"polygon");p.setAttribute("points",points.map(p=>p.join(",")).join(" "));p.setAttribute("fill","#2175c544");p.setAttribute("stroke","#146bb5");p.setAttribute("stroke-width",".004");svg.append(p);}if(state.drawing.target_point){const p=document.createElementNS(ns,"circle");p.setAttribute("cx",state.drawing.target_point[0]);p.setAttribute("cy",state.drawing.target_point[1]);p.setAttribute("r",".012");p.setAttribute("fill","#dc431b");svg.append(p);}}
async function saveBinding(temporary=false){const m=state.moment,b=clone(state.drawing);if(!m)return;if(b.zone_polygon?.length<3){b.draft_zone_points=b.zone_polygon;delete b.zone_polygon;}else if(b.zone_polygon)delete b.draft_zone_points;b.zone_id="entry_zone";b.target_id=b.target_point?"reviewed_target":null;b.zone_name=$("zone_name").value;b.target_name=$("target_name").value;b.frame_id=m.frame.frame_id;b.evidence_refs=[m.frame.frame_id];b.max_observed_timestamp_us=m.t0_us;b.binding_status=$("binding_confirmed").checked?"BOUND":"AMBIGUOUS";b.event_predicates={};for(const oid of Object.keys(predicateIds))b.event_predicates[oid]={truth:$(oid+"_truth").value,evidence_valid:$(oid+"_valid").checked,prior_active:null,contextual_target_confirmed:$(oid+"_context").checked};if(temporary)await queue("binding",b);else await edit("binding",b);}
async function sha(text){return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(text)))).map(x=>x.toString(16).padStart(2,"0")).join("");}
function loadJson(){$("json_editor").value=JSON.stringify(data($("edit_kind").value),null,2);}
for(let i=0;i<cocFields.length;i++){const label=document.createElement("label");label.textContent=cocLabels[i];const area=document.createElement("textarea");area.id="coc_"+cocFields[i];label.append(area);$("coc_fields").append(label);area.oninput=saveCoc;}
async function saveCoc(){try{const value={};for(const f of cocFields)value[f]=$("coc_"+f).value;value.causal_confirmed=$("causal").checked;value.leakage=$("leakage").checked;await queue("coc",value);}catch(e){error(e);}}
$("causal").onchange=saveCoc;$("leakage").onchange=saveCoc;
for(const a of actionIds){const label=document.createElement("label");label.textContent=a;const select=document.createElement("select");select.id="action_"+a;for(const v of ["","APPROPRIATE","INAPPROPRIATE","UNKNOWN","NOT_APPLICABLE"]){const o=document.createElement("option");o.value=v;o.textContent=v || "선택 안 함";select.append(o);}label.append(select);$("action_fields").append(label);select.onchange=saveAction;}
async function saveAction(){try{const labels={};for(const a of actionIds)if($("action_"+a).value)labels[a]=$("action_"+a).value;if(Object.keys(labels).length)await queue("action",{vocabulary_version:"studio-entry-v1",labels,reason:$("action_reason").value});}catch(e){error(e);}}
$("action_reason").oninput=saveAction;
for(const oid of Object.keys(predicateIds)){const div=document.createElement("div");const label=document.createElement("label");label.textContent=oid==="ped"?"보행자 관련 위험":"주도로 양보 필요";const select=document.createElement("select");select.id=oid+"_truth";for(const v of ["UNKNOWN","TRUE","FALSE","CONFLICT"]){const o=document.createElement("option");o.textContent=v;select.append(o);}label.append(select);div.append(label);for(const [suffix,text] of [["valid","근거 유효"],["context","개별 대상 없는 문맥 의무 확인"]]){const l=document.createElement("label"),c=document.createElement("input");c.type="checkbox";c.id=oid+"_"+suffix;l.append(c,document.createTextNode(text));div.append(l);}$("predicate_fields").append(div);}
for(const k of editable){const o=document.createElement("option");o.value=k;o.textContent=texts[k];$("edit_kind").append(o);}
for(const k of ["context","derived"]){const div=document.createElement("div");div.id=k+"_controls";$("extra_controls").append(div);}
$("edit_kind").onchange=loadJson;
$("login_form").onsubmit=async e=>{e.preventDefault();try{const r=await api("/login","POST",{actor_id:$("actor").value,secret:$("secret").value});$("secret").value="";state.csrf=r.csrf_token;await activate();}catch(e){error(e);}};
async function activate(){await dbReady;$("login").hidden=true;$("workspace").hidden=false;$("batch_tools").hidden=false;$("lineage_tools").hidden=false;const c=await api("/capabilities");$("provider").textContent=`VLM: ${c.provider_mode} · ${c.model||"모델·키·전송 승인·한도 설정 대기"} · 생성 결과는 사람 승인 필요`;await flush();await refresh();}
$("upload_form").onsubmit=async e=>{e.preventDefault();try{const f=$("video_file").files[0],form=new FormData();form.append("file",f);form.append("metadata",JSON.stringify({name:f.name,source:$("video_source").value,license:$("video_license").value,permission:$("permission").checked,drive_id:$("drive").value || null,parent_video_id:$("parent_video").value || null,parent_interval_us:$("parent_video").value?[Number($("parent_start").value),Number($("parent_end").value)]:null}));const r=await api("/videos","POST",form);await pollJob(r.job_id);}catch(e){error(e);}};
bind("refresh",refresh);bind("previous",()=>selectOrdinal(state.moment.ordinal-1));bind("next",()=>selectOrdinal(state.moment.ordinal+1));bind("next_error",()=>{const next=state.moments.find(m=>m.ordinal>state.moment.ordinal && m.eligibility.state==="HELD") || state.moments.find(m=>m.eligibility.state==="HELD");if(next)return loadMoment(next.id);});
bind("enlarge",()=>{$("zoom_image").src=$("current_frame").src;$("zoom").showModal();});bind("close_zoom",()=>$("zoom").close());
$("overlay").onclick=e=>{const r=$("overlay").getBoundingClientRect(),p=[(e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height];if($("draw_mode").value==="target")state.drawing.target_point=p;else if($("draw_mode").value==="zone"){state.drawing.zone_polygon ||= state.drawing.draft_zone_points || [];state.drawing.zone_polygon.push(p);}else return;draw();saveBinding(true).catch(error);};
bind("clear_target",async()=>{delete state.drawing.target_point;draw();await saveBinding();});bind("clear_zone",async()=>{delete state.drawing.zone_polygon;delete state.drawing.draft_zone_points;draw();await saveBinding();});bind("save_geometry",()=>saveBinding());bind("save_binding",()=>saveBinding());
bind("save_source",async()=>{const quote=$("source_quote").value;await edit("source",{records:[{id:$("source_id").value,kind:$("source_kind").value,version:$("source_version").value,locator:$("source_locator").value,quote,sha256:await sha(quote),reviewed:$("source_reviewed").checked}]});});
bind("prepare_proposal",async()=>{const source=data("source").records?.[0];if(!source)throw Error("출처부터 기록하세요");const b=data("binding");const proposals=Object.entries(predicateIds).map(([oid,predicate])=>({obligation_id:oid,rule_id:source.id,slice:"studio-entry-v0.1",source_claim_refs:[source.id],source_record_refs:[source.id],required_predicate_refs:[predicate],applicability:"TRUE",binding_status:b.binding_status || "AMBIGUOUS",target_id:oid==="ped"?b.target_id:null,zone_id:b.zone_id,binder_ref:"studio-human-v1",verdict:"PROPOSED",reason_codes:[],claim_boundary:"CONDITIONAL_NOT_SCENE_TRUTH"}));await edit("proposal",{frontend_version:"guardsynth-coc-conditioned-frontend-v0.1",request_id:key(),status:"PROPOSED",reason_codes:[],coc_parse:{parser_version:"guardsynth-coc-conditioned-frontend-v0.1",language:"ko",epistemic_kind:"CLAIMED",evidence_ref:state.moment.id,text_included:false,concepts:{},unknown_groups:[]},claim_promoted_to_scene_or_legal_authority:false,proposals,claim_scope:"HUMAN_PROPOSED_CONDITIONAL_ENTRY"});});
bind("prepare_contract",async()=>{const p=data("proposal").proposals;if(!p?.length)throw Error("제약 제안부터 기록하세요");await edit("contract",{contract_version:"eblc-action-contract-v0.1",contract_id:"studio_entry_contract",horizon:3,claim_scope:"CONDITIONAL_ACTION_SELECTION_NOT_VEHICLE_SAFETY",subject_id:"ego",zone_id:data("binding").zone_id,policy:"CLEAR_REQUIRED_FOR_ENTRY",source_refs:[...new Set(p.flatMap(x=>x.source_record_refs))],obligations:p.map(x=>({obligation_id:x.obligation_id,predicate_id:x.required_predicate_refs[0],target_entity_id:x.target_id,rule_ref:x.rule_id,source_refs:x.source_record_refs}))});});
for(const [id,type] of [["generate_coc","COC"],["generate_proposal","PROPOSAL"],["check","CHECK"],["render","CNL"],["combine","COMBINE"]])bind(id,()=>job(type));
bind("save_applicability",()=>edit("applicability",{status:$("applicability").value,reason:$("applicability_reason").value,candidate_reviewed:$("candidate_reviewed").checked}));
bind("complete",async()=>{await flush();await api(`/moments/${state.moment.id}/complete`,"POST",{revision:state.moment.revision});await loadMoment(state.moment.id);await refreshMoments();});
bind("save_json",()=>edit($("edit_kind").value,JSON.parse($("json_editor").value)));
bind("save_split",async()=>{const all=await api("/videos"),ex=all.extractions.find(x=>x.id===state.extraction),v=all.videos.find(x=>x.id===ex.video_id),g=all.lineages.find(x=>x.id===v.lineage_group_id);await api(`/lineages/${g.id}`,"POST",{revision:g.revision,split:$("split").value || null,confirmed:$("lineage_confirmed").checked});await refresh();});
bind("export",async()=>{await flush();await refreshMoments();const r=await api("/exports","POST",{moments:state.moments.map(m=>({id:m.id,revision:m.revision})),mode:$("export_mode").value,purpose:$("export_purpose").value});await pollJob(r.job_id);const result=await api(`/exports/${r.export_id}`);const p=document.createElement("p");p.textContent=`${result.status} · ${result.row_count}행 · 제외 ${result.excluded.length}시점`;for(const file of result.files){const a=document.createElement("a");a.textContent=file.relative_path.split("/").pop()+" ";a.href=API+"/assets/"+file.asset_id;a.download=a.textContent.trim();p.append(a);}$("exports").append(p);});
$("advanced").ontoggle=async()=>{if($("advanced").open && state.moment){try{await flush();state.moment=await api(`/moments/${state.moment.id}/exposure`,"POST",{revision:state.moment.revision,panel:"constraints_and_advanced"});}catch(e){error(e);}}};
setInterval(async()=>{if(!state.csrf)return;try{const r=await api("/jobs");$("jobs").replaceChildren();for(const j of r.jobs.slice(-15)){const d=document.createElement("div");d.textContent=`${j.kind} · ${j.status} ${j.error?.message || ""}`;d.append(button("취소",()=>api(`/jobs/${j.id}/cancel`,"POST",{})),button("재시도",()=>api(`/jobs/${j.id}/retry`,"POST",{})));$("jobs").append(d);}}catch(e){error(e);}},2000);
window.addEventListener("beforeunload",e=>{if(flushing){e.preventDefault();e.returnValue="";}});
api("/session").then(async r=>{state.csrf=r.csrf_token;await activate();}).catch(()=>{});
for(const k of kinds){const o=document.createElement("option");o.value=k;o.textContent=texts[k];$("batch_stage").append(o);}
function range(){const start=Number($("range_start").value)-1,end=Number($("range_end").value);if(!Number.isInteger(start)||!Number.isInteger(end)||start<0||end<=start||end>state.moments.length||end-start>100)throw Error("현재 추출에서 1–100개의 유효한 시점을 선택하세요");return state.moments.slice(start,end);}
bind("range_generate",async()=>{await flush();for(const selected of range()){const m=await api(`/moments/${selected.id}`);await api(`/moments/${m.id}/jobs`,"POST",{revision:m.revision,type:"COC"});}});
bind("batch_preview",async()=>{await flush();const kind=$("batch_stage").value;const moments=[];for(const selected of range())moments.push(await api(`/moments/${selected.id}`));state.batch=moments.map(m=>{const c=m.components[kind];if(!c)throw Error(`시점 ${m.ordinal+1}의 초안 없음`);return {moment_id:m.id,revision:m.revision,stage:kind,component_id:c.id,dependency_digest:c.dependency_digest,decision:"APPROVE"};});$("batch_confirm").checked=false;$("batch_diff").textContent=JSON.stringify(moments.map(m=>({timestamp:m.t0_us,revision:m.revision,previous_approval:m.approvals[kind]||null,current:m.components[kind]})),null,2);});
bind("batch_approve",async()=>{if(!$("batch_confirm").checked||!state.batch)throw Error("먼저 시점·변경 내용을 검토하세요");await api("/approvals/batch","POST",{items:state.batch});state.batch=null;await loadMoment(state.moment.id);await refreshMoments();});
bind("conflict_close",()=>$("conflict").close());
bind("conflict_apply",async()=>{const {row,current}=state.conflict;await dbOp("delete",row.id);const replacement={...row,id:key(),revision:current.revision,sent:false};await dbOp("put",replacement);for(const next of await dbOp("getAll"))if(next.moment_id===row.moment_id&&!next.sent){next.revision=current.revision;await dbOp("put",next);}$("conflict").close();await flush();await loadMoment(row.moment_id);});
bind("merge_lineages",async()=>{const all=await api("/videos"),ids=$("merge_groups").value.split(",").map(x=>x.trim());const groups=ids.map(id=>{const g=all.lineages.find(x=>x.id===id);if(!g)throw Error("그룹 ID를 확인하세요");return{id,revision:g.revision};});await api("/lineages/merge","POST",{groups,reason:$("merge_reason").value});await refresh();});
bind("revoke_video",async()=>{const all=await api("/videos"),ex=all.extractions.find(e=>e.id===state.extraction),v=all.videos.find(v=>v.id===ex?.video_id);if(!v)throw Error("영상을 선택하세요");await api(`/videos/${v.id}/permission`,"POST",{revision:v.revision,permission:false});await refresh();});
bind("logout",async()=>{await flush();await api("/logout","POST",{});for(const row of await dbOp("getAll"))await dbOp("delete",row.id);location.reload();});
let sourceEpoch=0;
async function autosaveSource(){const epoch=++sourceEpoch;const record={id:$("source_id").value,kind:$("source_kind").value,version:$("source_version").value,locator:$("source_locator").value,quote:$("source_quote").value,reviewed:$("source_reviewed").checked};record.sha256=await sha(record.quote);if(epoch===sourceEpoch)await queue("source",{records:[record]});}
for(const f of ["id","kind","version","locator","quote","reviewed"])$("source_"+f).addEventListener("input",()=>autosaveSource().catch(error));
for(const id of ["zone_name","target_name","binding_confirmed",...Object.keys(predicateIds).flatMap(k=>[k+"_truth",k+"_valid",k+"_context"])])$(id).addEventListener("input",()=>saveBinding(true).catch(error));
for(const id of ["applicability","applicability_reason","candidate_reviewed"])$(id).addEventListener("input",()=>queue("applicability",{status:$("applicability").value,reason:$("applicability_reason").value,candidate_reviewed:$("candidate_reviewed").checked}).catch(error));

// Help is presentation only: no writes, prefilled answers, approvals or generation.
function helpLink(anchor){const a=document.createElement("a");a.href="/manual.html#"+anchor;a.target="_blank";a.rel="noopener";a.textContent="자세한 설명 (새 탭)";return a;}
function fieldHelp(id,text){const control=$(id),hint=document.createElement("p");hint.id=id+"_help";hint.className="field_help";hint.textContent=text;control.setAttribute("aria-describedby",hint.id);control.closest("label")?.classList.add("explained_field");control.insertAdjacentElement("afterend",hint);}
function sectionHelp(id,anchor,summary,example){const host=$(id).closest("section,details"),box=document.createElement("div");box.className="section_help";const p=document.createElement("p");p.textContent=summary+" ";p.append(helpLink(anchor));const details=document.createElement("details"),title=document.createElement("summary"),body=document.createElement("p");title.textContent="참고 예시와 주의점";body.textContent=example;details.append(title,body);box.append(p,details);host.insertBefore(box,host.children[1]||null);}
const cocHelp=[
  "직접 보이는 사실만 씁니다. 예: 선택 영역 가장자리에 사람이 보인다. 추측은 가정 칸으로 분리하세요.",
  "대상과 영역의 관계를 적습니다. 예: 사람의 위치가 제안 진입 영역과 겹친다.",
  "미확인 전제임을 밝힙니다. 예: 표시 영역으로 진입하려는 상황이라고 가정하나 경로 확인이 필요하다.",
  "모르는 내용을 남깁니다. 예: 가림 때문에 영역 뒤쪽의 보행자 유무는 알 수 없다.",
  "관찰이 행동 판단으로 이어지는 이유입니다. 예: 겹침의 해소를 확인하기 전에는 진입을 보류한다.",
  "승인할 문장을 직접 정리하세요. 다른 다섯 칸에서 자동 합성되지 않습니다. 예: 관찰한 겹침과 남은 가림을 구분하여 진입 보류 이유를 기술한다."
];
cocFields.forEach((f,i)=>fieldHelp("coc_"+f,cocHelp[i]));
const actionHelp={ENTER_ZONE:"지정한 영역으로 들어가기. 근거에 비추어 적절한지 판단합니다.",DEFER_ENTRY:"진입 결정을 미루기. 급제동이나 정지 명령이 아닙니다.",MAINTAIN_SPEED:"이미 주행 중인 속도 유지. 현재 학습 profile 미지원이며 해당 없음도 보류됩니다. 진입 전용 작업에서 쓰지 않으면 비워 두세요.",HOLD_STOP:"이미 멈춘 상태 유지. 현재 학습 profile 미지원이며 해당 없음도 보류됩니다. 정지 상태를 모르면 단정하지 마세요."};
const actionNames={ENTER_ZONE:"영역 진입",DEFER_ENTRY:"진입 보류",MAINTAIN_SPEED:"주행 속도 유지",HOLD_STOP:"정지 유지"};
const choiceNames={APPROPRIATE:"적절",INAPPROPRIATE:"부적절",UNKNOWN:"판단 불가",NOT_APPLICABLE:"해당 없음"};
for(const a of actionIds){const el=$("action_"+a);el.parentNode.firstChild.textContent=actionNames[a]+" ("+a+")";for(const option of el.options)if(option.value)option.textContent=choiceNames[option.value]+" · "+option.value;fieldHelp(el.id,actionHelp[a]+" 복수 적절 선택 가능. 빈칸은 미기록, UNKNOWN은 근거 부족, NOT_APPLICABLE은 행동 상황 밖입니다.");}
for(const oid of Object.keys(predicateIds)){
  const el=$(oid+"_truth");for(const o of el.options){const v=o.value;o.value=v;o.textContent=({TRUE:"참",FALSE:"거짓",UNKNOWN:"미확인",CONFLICT:"근거 충돌"})[v]+" · "+v;}
  fieldHelp(el.id,(oid==="ped"?"선택 영역의 보행자 충돌 조건":"선택 진입 맥락에서 주도로 양보가 필요한 조건")+"을 판단하세요. 충분히 보이는 범위의 해소는 FALSE, 가림은 UNKNOWN입니다. CONFLICT는 같은 조건·같은 시점의 유효 근거가 양립하지 않는 경우입니다.");
  fieldHelp(oid+"_valid","이 관찰 근거가 해당 조건에 관련되고 현재 시점에 유효한지 확인합니다. CoC 문장만으로 보이지 않는 신호를 증명하지 않습니다.");
  fieldHelp(oid+"_context","특정 객체 없이 성립하는 문맥 의무임을 확인할 때만 선택합니다. 대상을 찾지 못했다는 뜻이 아닙니다.");
}
for(const [id,text] of Object.entries({
  causal:"t0와 그 이전의 근거만 썼는지 직접 검토한 뒤 확인합니다. 자동 승인되지 않습니다.",
  leakage:"미래 관찰 또는 정답 누출을 실제 발견했을 때 표시합니다. 형식적으로 선택하지 마세요.",
  action_reason:"레이블의 관찰 근거를 기록합니다. 솔버가 허용했다고 정답으로 복사하지 않습니다. 입력은 자동저장되며 별도 행동 승인이 필요합니다.",
  source_id:"규칙을 연결할 식별자입니다. 예시 ID 자체는 근거가 아닙니다.",
  source_kind:"POLICY는 연구 정책, EXTERNAL은 외부 권위 근거, UNVERIFIED_MODEL은 미검증 제안(승인 불가)입니다.",
  source_version:"검토한 실제 문서판을 적습니다. 버전을 모르면 확인부터 하세요.",
  source_locator:"원문을 다시 찾을 수 있는 조항·절·페이지 위치입니다.",
  source_quote:"정확한 인용문을 기록하세요. 해시는 자동 계산됩니다. 영상으로 국가·법규를 만들지 않습니다.",
  source_reviewed:"원문과 적용 근거를 직접 확인한 경우 선택합니다. 외부 권위의 관할·효력 범위는 고급 source에서 별도로 기록해야 합니다.",
  zone_name:"예: 검토 중인 합류 진입 구역. 실제 경로가 불명확하면 영역을 지어내지 마세요.",
  target_name:"대상 = 지금 검토하는 진입 조건의 근거로 지정할, 현재 프레임의 특정 객체 하나입니다. 예: ‘횡단보도 오른쪽 끝의 파란 옷 보행자’. ‘위험 요소’처럼 모호하게 쓰지 말고 위치·종류·구별 특징을 적으세요. 단순히 전방에 보이는 차량이라는 이유로 선택하지 않습니다. CoC만 생성할 때는 지정하지 않아도 됩니다.",
  binding_confirmed:"대상·영역·현재 causal 프레임 근거의 대응을 확인합니다. 기록과 별개로 승인해야 합니다.",
  applicability:"미검토 / 적용됨 / 명시 검토한 적용 제약 없음 / 미해결을 구별합니다. 빈 후보나 실패는 미적용이 아닙니다.",
  applicability_reason:"예: 후보 규칙을 검토했으나 현재 영역과 대응을 확인하지 못함. 이 경우 미해결로 남깁니다.",
  candidate_reviewed:"실제 규칙 후보와 근거를 검토했을 때만 선택합니다. 적용성 저장 뒤 별도 승인이 필요합니다.",
  split:"같은 원본·주행과 파생 클립은 하나의 train/validation/test에 둡니다. 불명확하면 분리 보류입니다.",
  export_mode:"COC_TARGET: CoC를 출력 목표에 둡니다. ACTION_WITH_CONTEXT: 정답 누출 없음을 별도 승인한 context를 입력에 둡니다.",
  export_purpose:"DRAFT는 보류 초안도 포함하나 학습 적격이 아닙니다. DEVELOPMENT_TRAINING은 보류 항목을 제외합니다.",
  json_editor:"허용 필드만 수정한 뒤 구조 초안 저장을 누르세요. origin·hash·승인·검사 상태를 조작하지 마세요. 항목 전환 전 저장합니다."
}))fieldHelp(id,text);
sectionHelp("login_form","quick-start","로그인 후 기존 영상의 추출 READY를 선택하세요. 준비된 영상은 다시 올리지 않아도 됩니다.","공개 데모는 화면 7번·13번에 초안이 있습니다. 호출 한도는 소진되었으므로 추가 생성 없이 검토하세요.");
sectionHelp("upload_form","quick-start","파일 선택은 내 PC의 파일을 업로드합니다. 출처·라이선스·주행 정보를 확인하세요.","영상 사용권한 확인은 외부 전송 승인이 아닙니다. 파생 클립이면 먼저 부모 영상·구간을 기록하세요.");
sectionHelp("viewer","frames","오른쪽 끝이 t0입니다. 썸네일 클릭은 판단 시점도 바꾸며 확대와 다릅니다.","1–7 → 다음 → 2–8 → 이전 → 1–7. 미래를 본 뒤 돌아와도 앞선 답변에 미래 지식을 넣지 마세요.");
sectionHelp("draw_mode","geometry","CoC 생성에는 도형 편집이 필요 없습니다. 대상은 ‘현재 검토하는 진입 조건의 근거로 지정할 객체 하나’입니다. 예: 횡단보도 진입을 검토할 때 오른쪽 끝의 보행자. 모든 차량을 표시하는 작업이 아닙니다. 영역은 자차의 진입 여부를 판단할 도로 공간이며 대상의 테두리가 아닙니다.","① 보행자 충돌 검토: 횡단보도 오른쪽 끝의 보행자 몸체 안을 클릭하고 ‘오른쪽 끝 파란 옷 보행자’처럼 이름을 적습니다. 영역은 검토할 횡단보도 진입 공간입니다. ② 주도로 양보 검토: 현재 기본 템플릿은 특정 차량 하나가 아닌 진입 문맥을 사용합니다. 임의 차량을 찍지 말고 주도로 관계·규칙 근거를 검토하세요. 개별 대상 없는 문맥 확인은 대상이 안 보인다는 뜻이 아닙니다. ③ 선행차 때문에 감속하는 현재 nuScenes 예제: 선행차를 CoC 관찰·이유에 기술하되 도형은 비워 두어도 됩니다. 현재 추종·감속 계약은 지원하지 않습니다. 무엇을 검토할지 불명확하면 ‘선택 안 함’을 유지하세요. 시점당 대상 점 하나·영역 하나를 지원하며 대상은 한 번 클릭, 영역은 꼭짓점 3개 이상을 클릭합니다. 클릭은 자동저장되며 도형 반영으로 확인합니다.");
sectionHelp("coc_fields","coc","관찰·관계·가정·미확인·행동 근거를 구분하고 CoC 본문을 직접 맞춰 쓰세요. 자동저장 뒤 별도 승인합니다.","본문은 자동 조립되지 않습니다. 모델 원출력은 보존되며 아래 예시는 답변에 자동 입력되지 않습니다.");
sectionHelp("action_fields","actions","행동을 별도로 검토·승인합니다. 복수 행동이 적절할 수 있으며 현재 지원은 진입·보류뿐입니다.","속도 유지·정지 유지는 현재 학습 미지원입니다. 쓰지 않는 칸은 비워 두되 적격을 위해 거짓 레이블을 만들지 마세요.");
sectionHelp("source_id","sources","실제 출처를 기록하고 관찰과 결합합니다. 입력은 자동저장되며 기록 버튼과 항목별 승인도 있습니다.","POLICY는 연구 정책이지 법규가 아닙니다. EXTERNAL의 관할·효력·적용 범위는 고급 source JSON에서 확인하세요.");
const predicateGuide=document.createElement("p");predicateGuide.className="section_help";predicateGuide.textContent="관찰 조건과 결합 체크의 의미를 확인하세요. ";predicateGuide.append(helpLink("predicates"));$("predicate_fields").before(predicateGuide);
sectionHelp("generate_proposal","constraints","승인 CoC·출처·관찰 결합 뒤 제안을 검토합니다. 모델 버튼은 호출을 사용하고 수동 템플릿은 초안만 만듭니다.","수동 템플릿은 ped·road 둘 다 제안합니다. 인용문이 두 규칙 모두를 뒷받침하는지 확인하세요. horizon 3은 3초나 3프레임이 아닙니다.");
sectionHelp("check","verification","계약 승인 → 검사 → CNL 검토·승인 → 원 CoC와 결합·승인 순서입니다. 행동 승인도 별도로 필요합니다.","금지 행동의 UNSAT는 기대 성공일 수 있습니다. 전체 PASS도 장면 사실·차량 안전 인증은 아닙니다. 가상 미래를 관찰로 사용하지 마세요.");
sectionHelp("applicability","applicability","적용성과 완료를 구분하세요. 적용성 입력 저장 후 승인은 별도이며 완료해도 학습 보류일 수 있습니다.","빈 제안·미지원·오류는 NOT_APPLICABLE이 아닙니다. 후보와 근거를 검토하지 못했다면 UNRESOLVED로 남기세요.");
const exportGuide=document.createElement("p");exportGuide.className="section_help";exportGuide.textContent="원본·주행 split 확인 후 저장 snapshot을 내보냅니다. 검토완료 수와 학습적격 수는 다릅니다. ";exportGuide.append(helpLink("export"));$("export_mode").closest("label").before(exportGuide);
sectionHelp("json_editor","advanced","단순 폼에 없는 출처 범위·제약·계약·context·수동 파생문을 검토할 때 사용합니다.","수동 CNL은 derived, 정답 누출 없는 입력 문장은 context로 따로 기록·승인합니다. 생성 원문이나 검사 보증을 덮어쓰지 않습니다.");
sectionHelp("jobs","jobs","작업 성공은 사람 승인이 아닙니다. 오류 이유를 확인하고 명시 재시도 여부를 판단하세요.","BUDGET은 한도 소진, STALE_RESULT는 오래된 결과 미적용입니다. 취소가 원격 비용 취소를 보장하지 않습니다.");
sectionHelp("batch_tools","batch","구간 생성은 시점별 호출을 소비합니다. 일괄 승인은 미리보기의 모든 시점·차이를 확인한 뒤 실행하세요.","최대 100시점이며 하나라도 버전이 바뀌면 전체 승인을 거부합니다. 현재 공개 데모의 호출 한도는 이미 소진되었습니다.");
sectionHelp("lineage_tools","lineage","파생 구간은 μs 단위입니다. 계보 병합·권한 철회는 기존 export에 영향을 줍니다.","2초~5초는 2000000~5000000 μs입니다. 계보가 불명확하면 split을 확정하지 마세요. 로그아웃 전 저장 실패·충돌을 해결하세요.");
const savingGuide=document.createElement("p");savingGuide.textContent="저장 ≠ 승인 ≠ 검토 완료 ≠ 학습 적격. 상위 수정은 의존 결과의 재검토를 요구합니다. ";savingGuide.append(helpLink("saving"));document.querySelector("header").append(savingGuide);
