'use strict';
// Exercise the real UI handlers against a minimal DOM and persistent draft store.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=path.resolve(__dirname,'../../experiments/paper1_cnl_learning/source_gap_review.js');
const packet={review_version:'paper1-source-gap-v0.1',packet_sha256:'synthetic-test-packet',submission_directory:'test-only',scenes:[1,2].map(i=>({candidate_digest:'synthetic-'+i,event_timestamp_us:i,frames:[{timestamp_us:i,data_url:'data:image/jpeg;base64,'}],machine_points:[],source_person_ids:[],control_count:0,label:'test '+i,original_coc:'synthetic',prior_observation:null}))};
const records=packet.scenes.map(s=>({candidate_digest:s.candidate_digest,event_timestamp_us:s.event_timestamp_us,target_point:[.4,.5],zone_polygon:[[.1,.1],[.8,.1],[.4,.8]],target_status:'CONFIRMED',zone_status:'CONFIRMED',target_description:'synthetic person',ped_truth:'TRUE',ped_reason:'synthetic reason',road_context:'UNKNOWN',road_truth:'UNKNOWN',road_reason:'unknown',control_context:'UNKNOWN',control_truth:'UNKNOWN',control_reason:'unknown',reviewed_at:'2026-09-09T00:00:00Z'}));
const key='guardsynth-source-gap:'+packet.packet_sha256;
const store=new Map([[key,JSON.stringify({kind:'DRAFT',review_version:packet.review_version,packet_sha256:packet.packet_sha256,reviewer_id:'SYNTHETIC TEST',records,completed:records.map(r=>r.candidate_digest)})]]);
function boot(failWrites=false){
 const nodes=new Map(),downloads=[];
 function element(){return {value:'',textContent:'',children:[],attrs:{},appendChild(e){this.children.push(e);},replaceChildren(){this.children=[];},setAttribute(k,v){this.attrs[k]=v;},getBoundingClientRect(){return {left:0,top:0,width:100,height:100};},classList:{toggle(){}},click(){},showModal(){},close(){}};}
 function get(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);}
 get('packet').textContent=JSON.stringify(packet);
 vm.runInNewContext(fs.readFileSync(source,'utf8'),{document:{getElementById:get,createElement:element,createElementNS:element},localStorage:{getItem:k=>store.get(k),setItem:(k,v)=>{if(failWrites)throw Error('storage unavailable');store.set(k,v);}},structuredClone,Blob,URL:{createObjectURL(blob){downloads.push(blob);return 'blob:test';},revokeObjectURL(){}},setTimeout:()=>0,confirm:()=>true});
 return {get,downloads};
}
async function main(){
 const ui=boot(),get=ui.get;
 assert.equal(typeof get('clearPoint').onclick,'function');
 get('pointMode').onclick();
 get('clearPoint').onclick();
 let saved=JSON.parse(store.get(key)),first=saved.records[0];
 assert.equal(first.target_point,null);
 assert.equal(first.target_status,'');
 assert.equal(first.reviewed_at,null);
 assert.deepEqual(saved.completed,['synthetic-2']);
 for(const field of Object.keys(records[0]).filter(f=>!['target_point','target_status','reviewed_at'].includes(f)))assert.deepEqual(first[field],records[0][field],field);
 assert.deepEqual(saved.records[1],records[1]);
 assert.equal(get('marks').children.some(n=>n.attrs.stroke==='#ff4242'),false);
 get('marks').onclick({clientX:30,clientY:40});
 assert.equal(JSON.parse(store.get(key)).records[0].target_point,null,'delete must exit drawing mode');
 const unchanged=store.get(key);get('clearPoint').onclick();assert.equal(store.get(key),unchanged,'repeat delete must be a no-op');
 get('nextScene').onclick();get('prevScene').onclick();
 assert.equal(get('target_status').value,'');
 const restored=boot();assert.equal(restored.get('target_status').value,'');
 assert.equal(restored.get('marks').children.some(n=>n.attrs.stroke==='#ff4242'),false,'reload must not restore deleted point');
 get('draft').onclick();
 const draft=JSON.parse(await ui.downloads.at(-1).text());assert.equal(draft.records[0].target_point,null);
 await get('import').onchange({target:{files:[{text:async()=>JSON.stringify(draft)}]}});
 assert.equal(get('target_status').value,'');
 get('target_status').value='UNKNOWN';get('target_status').oninput();
 get('ped_truth').value='UNKNOWN';get('ped_truth').oninput();
 get('complete').onclick();get('export').onclick();
 const exported=JSON.parse(await ui.downloads.at(-1).text());
 assert.equal(exported.records.length,2);
 assert.equal(exported.records[0].target_point,null);
 assert.equal(exported.records[0].target_status,'UNKNOWN');
 assert.deepEqual(exported.records[0].zone_polygon,records[0].zone_polygon);
 completionCases();
 console.log('PASS: delete, redraw, completion invalidation, other scene/answers preserved, no-op, draft reload/import and answer export');
}
function completionCases(){
 store.clear();
 for(let i=3;i<=30;i++)packet.scenes.push({...packet.scenes[0],candidate_digest:'synthetic-'+i,event_timestamp_us:i,label:'test '+i});
 const fields=require(source).FIELDS,notes=['target_description','ped_reason','road_reason','control_reason'];
 const fillNA=ui=>{for(const field of fields){ui.get(field).value=notes.includes(field)?'':'NOT_APPLICABLE';ui.get(field).oninput();}};
 const ui=boot();fillNA(ui);
 ui.get('viewMode').onclick();assert.equal(ui.get('progress').textContent,'완료 0 / 30','drawing end is not review completion');
 ui.get('complete').onclick();assert.equal(ui.get('progress').textContent,'완료 1 / 30');
 assert.match(ui.get('completionProgress').textContent,/완료 1 \/ 30/);
 ui.get('complete').onclick();assert.equal(ui.get('progress').textContent,'완료 1 / 30','no double count');
 ui.get('target_status').oninput();assert.equal(ui.get('progress').textContent,'완료 1 / 30','unchanged input must not invalidate completion');
 const reloaded=boot();assert.equal(reloaded.get('progress').textContent,'완료 1 / 30','persisted completion after reload');
 ui.get('nextScene').onclick();fillNA(ui);ui.get('target_status').value='';ui.get('target_status').oninput();
 ui.get('complete').onclick();assert.equal(ui.get('progress').textContent,'완료 1 / 30');
 assert.match(ui.get('validation').textContent,/대상 확인/);
 assert.equal(ui.get('target_status').attrs['aria-invalid'],'true');
 assert.equal(JSON.parse(store.get(key)).records[1].target_status,'','failed completion preserves draft without invented answers');
 ui.get('target_status').value='NOT_APPLICABLE';ui.get('target_status').oninput();ui.get('complete').onclick();
 assert.equal(ui.get('progress').textContent,'완료 2 / 30');
 ui.get('nextScene').onclick();fillNA(ui);ui.get('target_status').value='UNKNOWN';ui.get('target_status').oninput();
 ui.get('complete').onclick();assert.equal(ui.get('progress').textContent,'완료 2 / 30');assert.match(ui.get('validation').textContent,/특정 불가 이유/);
 const noStorage=boot(true);noStorage.get('nextScene').onclick();noStorage.get('nextScene').onclick();fillNA(noStorage);noStorage.get('complete').onclick();
 assert.equal(noStorage.get('progress').textContent,'완료 3 / 30');assert.match(noStorage.get('status').textContent,/자동 저장 실패/);
 assert.equal(JSON.parse(store.get(key)).completed.length,2,'do not claim failed persistence');
 console.log('PASS: completion 0/30 -> 1/30 -> 2/30, N/A without notes, blank/UNKNOWN rejected, duplicate input/reload, failed-storage warning');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
