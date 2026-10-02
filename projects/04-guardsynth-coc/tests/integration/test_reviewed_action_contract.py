"""Real corrected source → conditioned Core; independent packet leakage guards."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT=next(p for p in Path(__file__).resolve().parents if (p/"PROJECT_REGISTRY.json").is_file())
ENTRY=ROOT/"projects/04-guardsynth-coc/experiments/paper1_cnl_learning/execute_reviewed_contract.py"
spec=importlib.util.spec_from_file_location("reviewed_contract_runner",ENTRY)
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


class ReviewedContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.out=Path(cls.temp.name)/"test-001";cls.result=runner.run(cls.out)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def read(self,name):return runner.load(self.out/name)

    def test_effective_review_bound_without_whole_source_promotion(self):
        b=self.read("event_binding.json");c=self.read("action_contract.json")
        self.assertEqual(b["event_predicates"],{"ped":{"truth":"TRUE","evidence_valid":True},"road":{"truth":"UNKNOWN","evidence_valid":False}})
        self.assertEqual(c["zone_id"],"scene18_reviewed_entry_zone")
        self.assertEqual(c["obligations"][0]["target_entity_id"],"Agent3")
        self.assertIsNone(c["obligations"][1]["target_entity_id"])
        self.assertFalse(b["source_accepted_for_development"]);self.assertFalse(b["learning_export_allowed"])
        self.assertEqual(b["observed_core_offsets"],[0]);self.assertEqual(b["unobserved_core_offsets"],[1,2])

    def test_solver_checks_and_smt_replay(self):
        import z3
        checks=self.read("observed_checks.json")
        self.assertEqual(checks["query_count"],10);self.assertEqual(checks["matches_expected"],10)
        for q in checks["results"]:
            s=z3.Solver();s.from_file(str(self.out/q["smt2_file"]));self.assertEqual(str(s.check()).upper(),q["expected"])
        self.assertEqual(self.result["enter_status"],"UNSAT");self.assertEqual(self.result["defer_status"],"SAT")
        self.assertEqual(self.result["training_exports"],0);self.assertIsNone(self.result["independent_action_gold"])

    def test_action_packet_blinded_allowlist_and_no_future_inputs(self):
        p=self.read("scene18_independent_action_review_packet.json")
        self.assertEqual(set(p),{"review_version","kind","sample_id","event_timestamp_us","zone_polygon","frames","choices","scope","gold_prefilled"})
        self.assertTrue(all(f["timestamp_us"]<=p["event_timestamp_us"] for f in p["frames"]))
        html=(self.out/"scene18_independent_action_review.html").read_text()
        for leak in ("Yield to the traffic on the main road", "CONFIRMED_AGENT3", "ped_reason", "observed_checks", "HUMAN_REVIEWED_DEVELOPMENT_SOURCE"):
            self.assertNotIn(leak,html)
        display=json.loads(re.search(r'<script id="packet" type="application/json">(.*?)</script>',html,re.S)[1])
        import base64,hashlib
        self.assertEqual(len(display["images"]),len(p["frames"]))
        for frame,image in zip(p["frames"],display["images"]):
            self.assertEqual(hashlib.sha256(base64.b64decode(image.split(',',1)[1])).hexdigest(),frame["sha256"])

    def test_cnl_packet_uses_common_renderer_without_verdict_hint(self):
        p=self.read("scene18_independent_cnl_review_packet.json")
        self.assertEqual(p["cnl_text"],(self.out/"constraints.txt").read_text())
        self.assertNotIn("reviewed_event_inputs",[c["id"] for c in p["core_semantics"]["clauses"]])
        self.assertEqual(p["core_semantics"]["queries"],[])
        self.assertEqual(len(p["clause_ids"]),5)

    def test_hashes_and_immutability(self):
        m=self.read("RUN_MANIFEST.json")
        for field,base in (("input_hashes",ROOT),("code_hashes",ROOT),("output_hashes",self.out)):
            for rel,sha in m[field].items():self.assertEqual(runner.digest(base/rel),sha,rel)
        with self.assertRaises(FileExistsError):runner.run(self.out)

    def test_independent_intake_known_exposure_and_no_export(self):
        packet_path=self.out/"scene18_independent_action_review_packet.json"
        r={"review_version":runner.VERSION,"packet_sha256":runner.digest(packet_path),"kind":"ACTION",
           "reviewer_id":"Jin Hyun Kim","reviewed_at":"2026-09-08T00:00:00Z","independence":"INDEPENDENT",
           "answers":{"action":"DEFER_ENTRY"},"reason":"SYNTHETIC_TEST_ONLY_NOT_ACTUAL_REVIEW"}
        path=Path(self.temp.name)/"synthetic_review.json";runner.write_json(path,r)
        result=runner.intake(Path(self.temp.name)/"synthetic-intake-001",path,packet_path)
        self.assertFalse(result["independence_eligible"]);self.assertFalse(result["learning_export_allowed"])

    def test_mismatched_source_scene_rejected(self):
        scene,packet,review,_=runner.reviewed_inputs();packet=deepcopy(packet);packet["event_timestamp_us"]=0
        with self.assertRaises(ValueError):runner.bind_reviewed_scene18(scene,packet,review,packet_sha256="a"*64,
            review_ref="r",policy_ref="p",source_refs=["p","r"])

    def test_javascript_parses(self):
        script=re.search(r'<script>\s*(.*?)</script>',runner.TEMPLATE.read_text(),re.S)[1]
        subprocess.run(["node","--check"],input=script,text=True,check=True,capture_output=True)

    def test_ui_drafts_zoom_and_packet_restore_with_dom_stub(self):
        script=re.search(r'<script>\s*(.*?)</script>',runner.TEMPLATE.read_text(),re.S)[1]
        harness=r'''
const vm=require('vm'),assert=require('assert');
const input=JSON.parse(require('fs').readFileSync(0,'utf8'));
for(const packet of input.packets){
 const nodes=new Map(),stored=new Map();let downloads=0;
 function node(){return {value:'',textContent:'',children:[],hidden:true,
  classList:{toggle(){}},setAttribute(){},append(...x){this.children.push(...x)},
  appendChild(x){this.children.push(x)},replaceChildren(){this.children=[]},
  showModal(){this.open=true},close(){this.open=false},click(){downloads++}}}
 function get(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)}
 packet.packet_sha256='test-packet-'+packet.kind;
 if(packet.kind==='ACTION')packet.images=packet.frames.map((_,i)=>'test-image-'+i);
 get('packet').textContent=JSON.stringify(packet);
 let context={document:{getElementById:get,createElement:node,createElementNS:node},
  localStorage:{setItem:(k,v)=>stored.set(k,v),getItem:k=>stored.get(k)},
  URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},Blob:class{},setTimeout(){},assert};
 const probe=`
 assert(Object.values(state.answers).every(v=>v===''));
 $('export').onclick();assert($('status').textContent.includes('입력'));
 for(const [id,value] of Object.entries({reviewer_id:'SYNTHETIC_TEST_ONLY',independence:'UNCERTAIN',reason:'TEMPORARY_UI_TEST'})){
  $(id).value=value;$(id).oninput();
 }
 for(const id of answerIds)$(isAction?id:'answer_'+id).onchange({target:{value:'UNJUDGEABLE'}});
 const before=JSON.stringify(state);
 if(isAction){$('zoom').onclick();assert($('zoomDialog').open);$('nativeZoom').onclick();$('closeZoom').onclick();assert(!$('zoomDialog').open);
  $('prev').onclick();$('atEvent').onclick();assert.equal(index,P.frames.length-1);
 }
 assert.equal(JSON.stringify(state),before);save();
 restore(JSON.parse(localStorage.getItem(key)));assert.equal(JSON.stringify(state),before);
 assert.throws(()=>restore({...record(),packet_sha256:'wrong'}));assert.equal(JSON.stringify(state),before);
 $('export').onclick();
 `;
 vm.runInNewContext(input.script+probe,context);assert.equal(downloads,1);
 if(packet.korean_review){
  function visible(n){return (n.textContent||'')+' '+n.children.map(visible).join(' ')}
  for(const id of ['contract','core','clauses'])assert(!/sha256:|[a-f0-9]{64}/.test(visible(get(id))));
  assert(visible(get('clauses')).includes('한글 번역'));
  assert(visible(get('clauses')).includes('영문 원문 확인'));
  if(packet.korean_review.pairs){
   assert.equal(get('clauses').children.length,3);
   assert(visible(get('clauses')).includes('A · 실제 명세 규칙의 해설'));
   assert(visible(get('clauses')).includes('B · 실제 생성 문장의 한글 번역'));
   assert(!visible(get('clauses')).includes('조건부 명세 ‘장면 18'));
   assert(!nodes.has('answer_action.identity'));assert(!nodes.has('answer_action.sources'));
  }
  get('downloadOriginal').onclick();assert.equal(downloads,2);
 }
 vm.runInNewContext(input.script+"assert.equal(state.reviewer_id,'SYNTHETIC_TEST_ONLY'); assert(Object.values(state.answers).every(v=>v==='UNJUDGEABLE'));",context={...context});
}
'''
        # Fresh contexts model page reload, not actual browser rendering or downloads.
        packets=[self.read("scene18_independent_"+kind+"_review_packet.json") for kind in ("action","cnl")]
        from localize_cnl_review import korean_view
        localized=deepcopy(packets[1]);localized["korean_review"]=korean_view(localized);packets.append(localized)
        subprocess.run(["node","-e",harness],input=json.dumps({"script":script,"packets":packets}),text=True,check=True,capture_output=True)


if __name__=="__main__":unittest.main()
