// DOM-state tests without a browser; all answers here are synthetic test data.
'use strict';
const vm=require('node:vm'),assert=require('node:assert/strict');
let input='';process.stdin.on('data',s=>input+=s);process.stdin.on('end',()=>{
 const data=JSON.parse(input),stored=new Map();let lastBlob=null,downloadName=null,storageFails=false;
 function setup(){const nodes={};function element(){return {children:[],textContent:'',value:'',handlers:{},appendChild(x){this.children.push(x)},replaceChildren(){this.children=[]},setAttribute(k,v){this[k]=v},addEventListener(k,f){this.handlers[k]=f},showModal(){this.open=true},close(){this.open=false},click(){downloadName=this.download}}}
  const document={getElementById(id){return nodes[id]??(nodes[id]=element())},createElement:element,createElementNS:element};
  document.getElementById('packets').textContent=JSON.stringify(data.packets);
  const c=vm.createContext({document,Blob,console,confirm:()=>true,setTimeout:f=>f(),URL:{createObjectURL(b){lastBlob=b;return 'blob:test'},revokeObjectURL(){}},localStorage:{getItem:k=>stored.get(k)??null,setItem(k,v){if(storageFails)throw Error('storage unavailable');stored.set(k,v)}},assert});
  for(const script of data.scripts)vm.runInContext(script,c);
  return c;
 }
 let c=setup();const run=s=>vm.runInContext(s,c);
 run(`assert.equal(progress(),0);assert.equal($('reviewer_id').value,'Jonh');assert.equal($('independence').value,'');$('complete').onclick();assert.match($('reviewStatus').textContent,/행동 선택/);$('exportAll').onclick();assert.equal(progress(),0);`);
 assert.equal(lastBlob,null);
 run(`$('independence').value='INDEPENDENT';$('independence').handlers.change();$('action').value='UNJUDGEABLE';$('action').handlers.change();$('reason').value='Synthetic test: unclear direction';$('reason').handlers.input();$('complete').onclick();assert.equal(progress(),1);assert.equal($('completionTop').textContent,'완료 1/16');$('zoom').onclick();$('closeZoom').onclick();assert.equal($('zoomDialog').open,false);scene(1);scene(0);assert.equal($('action').value,'UNJUDGEABLE');assert.equal(progress(),1);`);
 c=setup();run(`assert.equal(progress(),1);assert.equal($('reason').value,'Synthetic test: unclear direction');$('reason').value='Synthetic revised reason';$('reason').handlers.input();assert.equal(progress(),0);$('complete').onclick();assert.equal(progress(),1);const good=batch('DRAFT');const bad=JSON.parse(JSON.stringify(good));bad.reviews[1]=bad.reviews[0];assert.throws(()=>restoreBatch(bad));assert.equal(progress(),1);const wrong=JSON.parse(JSON.stringify(good));wrong.bundle_sha256='wrong';assert.throws(()=>restoreBatch(wrong));restoreBatch(good);assert.equal(progress(),1);$('reviewer_id').value='Test reviewer';$('reviewer_id').handlers.input();assert.equal(progress(),0);assert.equal($('action').value,'UNJUDGEABLE');$('reviewer_id').value='Jonh';$('reviewer_id').handlers.input();`);
 storageFails=true;run(`$('complete').onclick();assert.match($('reviewStatus').textContent,/브라우저 저장 실패/);`);storageFails=false;
 run(`for(let i=0;i<P.length;i++){scene(i);$('action').value=i===0?'UNJUDGEABLE':'DEFER_ENTRY';$('action').handlers.change();$('reason').value='Synthetic test reason '+i;$('reason').handlers.input();$('complete').onclick()}assert.equal(progress(),16);$('exportAll').onclick();`);
 assert.equal(downloadName,'paper1_action_review.json');assert.ok(lastBlob);
 lastBlob.text().then(text=>{const result=JSON.parse(text);assert.equal(result.reviews.length,16);assert.equal(result.submission_kind,'FINAL');c=setup();run(`assert.equal(progress(),16);const value=batch('FINAL');restoreBatch(value);assert.equal(progress(),16);`);process.stdout.write(JSON.stringify(result));});
});
