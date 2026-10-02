// DOM-stub event regression, not a browser layout/accessibility certification.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const template=fs.readFileSync(process.argv[2],'utf8');
const packet=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
packet.packet_sha256=process.argv[4];packet.frames=packet.frames.map(f=>({...f,data_url:'test:'+f.frame_index}));
const js=template.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const memory=new Map();
function boot(){
 const elements=new Map();
 function element(id){return {value:'',checked:true,textContent:'',children:[],classList:{toggle(){}},
  setAttribute(k,v){this[k]=v},appendChild(e){this.children.push(e)},replaceChildren(){this.children=[]},
  getBoundingClientRect(){return {left:0,top:0,width:1000,height:562.5}},showModal(){this.open=true},close(){this.open=false},click(){},id};}
 const get=id=>{if(!elements.has(id))elements.set(id,element(id));return elements.get(id)};
 get('packet').textContent=JSON.stringify(packet);
 const context=vm.createContext({document:{getElementById:get,createElement:element,createElementNS:(_ns,tag)=>element(tag)},
  localStorage:{getItem:k=>memory.get(k)||null,setItem:(k,v)=>memory.set(k,v)},structuredClone,confirm:()=>true,
  Blob,URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},setTimeout:fn=>fn(),console});
 vm.runInContext(js,context);
 return {get,eval:s=>vm.runInContext(s,context),record:()=>JSON.parse(vm.runInContext('JSON.stringify(record())',context))};
}
let ui=boot();
assert.equal(ui.record().target_identity,'');
ui.get('reviewer_id').value='SYNTHETIC_UI_TEST';ui.get('reviewer_id').oninput();
ui.get('targetMode').onclick();ui.get('marks').onclick({clientX:400,clientY:281.25});
assert.deepEqual(ui.record().target_point,[.4,.5]);
ui.get('zoneMode').onclick();
for(const [x,y] of [[200,200],[700,200],[700,500],[200,500]])ui.get('marks').onclick({clientX:x,clientY:y});
ui.get('undo').onclick();assert.equal(ui.record().zone_polygon.length,3);
ui.get('finish').onclick();const before=ui.record();
ui.get('zoom').onclick();assert.equal(ui.get('zoomDialog').open,true);ui.get('closeZoom').onclick();
assert.equal(ui.get('zoomDialog').open,false);assert.deepEqual(ui.record().zone_polygon,before.zone_polygon);
ui.get('prev').onclick();ui.get('next').onclick();assert.deepEqual(ui.record().target_point,[.4,.5]);
ui=boot();assert.deepEqual(ui.record().zone_polygon,before.zone_polygon);assert.equal(ui.record().reviewer_id,'SYNTHETIC_UI_TEST');
assert.throws(()=>ui.eval('applyRecord({...record(),packet_sha256:"wrong"})'));
assert.throws(()=>ui.eval('applyRecord({...record(),target_point:[NaN,1]})'));
assert.throws(()=>ui.eval('applyRecord({...record(),ped_truth:"AUTO_CONFIRMED"})'));
assert.equal(ui.eval('validPolygon([[0,0],[1,0],[1,1],[0,1]])'),true);
assert.equal(ui.eval('validPolygon([[0,0],[1,1],[1,0],[0,1]])'),false);
assert.equal(ui.eval('validPolygon([[0,0],[.5,.5],[1,1]])'),false);
ui.get('target_identity').value='CONFIRMED_AGENT3';ui.get('target_identity').oninput();
ui.get('targetMode').onclick();ui.get('marks').onclick({clientX:500,clientY:300});assert.equal(ui.record().target_identity,'');
ui.get('restore').onclick();assert.deepEqual(ui.record().zone_polygon,packet.machine_proposal.zone_polygon);assert.equal(ui.record().zone_status,'');
ui.get('export').onclick();assert.match(ui.get('status').textContent,/모든 질문/);
ui.get('exportDraft').onclick();assert.match(ui.get('status').textContent,/JSON 저장/);
console.log('UI state, separate point/zone edits, undo, zoom return, reload/import and packet isolation passed');
