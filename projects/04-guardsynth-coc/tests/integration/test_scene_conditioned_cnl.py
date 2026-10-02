"""Actual scene input → claim-checked CNL; observations and human gold stay separate."""

from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=next(p for p in Path(__file__).resolve().parents if (p/"PROJECT_REGISTRY.json").exists())
sys.path.insert(0,str(ROOT/"projects/04-guardsynth-coc/experiments/paper1_cnl_learning"))
import generate_scene_cnl as entry
import guard_synth.scene_conditioned_cnl as generator
r=entry.r


class SceneCNLTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.out=Path(cls.temp.name)/"scene-001";cls.result=entry.run(cls.out)
        cls.raw=r.load(entry.PARENT/"action_contract.json");cls.binding=r.load(cls.out/"event_binding.json")
        cls.packet=r.load(cls.out/"scene18_scene_cnl_review_packet.json")
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_real_scene_text_reflects_observation_and_unknown(self):
        doc=r.load(self.out/"scene_cnl.json")
        self.assertIn("보행자 관련 위험이 있다고 확인",doc["text_ko"])
        self.assertIn("양보할 필요가 있는지는 현재 유효한 근거로 확인되지 않았습니다",doc["text_ko"])
        self.assertIn("지금 지정된 영역으로 진입하지 말고",doc["text_ko"])
        self.assertEqual(len(doc["clauses"]),4)
        self.assertNotIn("sha256:",doc["text_ko"]);self.assertNotIn("추상",doc["text_ko"])
        self.assertFalse(doc["independent_semantic_review_complete"])
        self.assertFalse(doc["learning_export_allowed"])
        self.assertEqual(doc["binding_sha256"],generator.object_sha(self.binding))

    def test_checks_replay_and_all_sentences_have_support(self):
        import z3
        checks=r.load(self.out/"claim_checks.json");self.assertEqual(checks["matches_expected"],12)
        ids=set()
        for q in checks["results"]:
            ids.add(q["query_id"]);s=z3.Solver();s.from_file(str(self.out/q["smt2_file"]))
            self.assertEqual(str(s.check()).upper(),q["expected"])
        core=r.load(self.out/"core_model.json");core_ids={c["id"] for c in core["clauses"]}
        for c in r.load(self.out/"scene_cnl.json")["clauses"]:
            self.assertTrue(set(c["support_query_ids"])<=ids)
            self.assertTrue(set(c["core_clause_ids"])<=core_ids)

    def test_observation_changes_change_language_not_fixed_scene_script(self):
        for truth,valid,phrase in (("FALSE",True,"위험이 없다고 확인"),("FALSE",False,"현재 유효한 근거로 확인되지"),
                                   ("TRUE",False,"현재 유효한 근거로 확인되지"),("CONFLICT",True,"근거가 서로 충돌")):
            b=deepcopy(self.binding);b["event_predicates"]["ped"]={"truth":truth,"evidence_valid":valid}
            doc,_,_=generator.generate_scene_cnl(self.raw,b)
            self.assertIn(phrase,doc["clauses"][0]["text_ko"])
        b=deepcopy(self.binding)
        b["event_predicates"]={oid:{"truth":"FALSE","evidence_valid":True} for oid in ("ped","road")}
        doc,_,_=generator.generate_scene_cnl(self.raw,b)
        self.assertEqual(doc["clauses"][2]["semantics"]["allowed_actions"],["DEFER_ENTRY","ENTER_ZONE"])
        self.assertIn("계속 보류해도 됩니다",doc["clauses"][2]["text_ko"])

    def test_bad_binding_and_gate_mutation_fail_before_text(self):
        other=deepcopy(self.raw);other["subject_id"]="other_vehicle"
        with self.assertRaises(ValueError):generator.generate_scene_cnl(other,self.binding)
        for key,value in (("zone_id","wrong"),("observed_core_offsets",[0,1]),("review_ref","unknown"),("source_frame_timestamp_us",99999999)):
            b=deepcopy(self.binding);b[key]=value
            with self.assertRaises(ValueError):generator.generate_scene_cnl(self.raw,b)
        b=deepcopy(self.binding);b["event_predicates"]["road"]["evidence_valid"]="false"
        with self.assertRaises(ValueError):generator.generate_scene_cnl(self.raw,b)
        lower=generator.lower_action_contract
        def broken(c):
            core=lower(c);core["clauses"]=[x for x in core["clauses"] if x["id"]!="action_gate"];return core
        with patch.object(generator,"lower_action_contract",broken):
            with self.assertRaises(ValueError):generator.generate_scene_cnl(self.raw,self.binding)

    def test_actual_text_and_images_used_in_review_no_gold_leak(self):
        p=self.packet;doc=r.load(self.out/"scene_cnl.json")
        self.assertEqual(p["generated_text_ko"],doc["text_ko"])
        self.assertEqual([i["text"] for i in p["items"]],[c["text_ko"] for c in doc["clauses"]])
        html=(self.out/"scene18_scene_cnl_review.html").read_text()
        display=json.loads(re.search(r'<script id="packet" type="application/json">(.*?)</script>',html,re.S)[1])
        for f,img in zip(p["frames"],display["images"]):
            self.assertLessEqual(f["timestamp_us"],p["event_timestamp_us"])
            self.assertEqual(hashlib.sha256(base64.b64decode(img.split(',',1)[1])).hexdigest(),f["sha256"])
        self.assertNotIn("Jun Choi",html)
        self.assertNotIn("scene18-action-intake",str(self.result["input_hashes"]))

    def test_preview_is_blocked_not_training_record(self):
        p=r.load(self.out/"coc_cnl_preview.json")
        self.assertFalse(p["learning_export_allowed"]);self.assertIsNone(p["independent_action_gold"])
        self.assertIn(p["original_coc"],p["assistant_target_preview"])
        self.assertIn(p["constraint_supervision_candidate_en"],p["assistant_target_preview"])
        self.assertIn("FULL_SOURCE_ACCEPTANCE",p["blocked_by"])

    def test_new_review_kind_records_actual_scope_and_known_involvement(self):
        packet=self.out/"scene18_scene_cnl_review_packet.json"
        response={"review_version":entry.SCENE_VERSION,"kind":"SCENE_CNL","packet_sha256":r.digest(packet),
            "reviewer_id":"Jin Hyun Kim","reviewed_at":"2026-09-08T00:00:00Z","independence":"INDEPENDENT",
            "reason":"SYNTHETIC_TEST_ONLY_NOT_HUMAN","answers":{c:"UNJUDGEABLE" for c in self.packet["clause_ids"]}}
        review=Path(self.temp.name)/"synthetic.json";r.write_json(review,response)
        result=r.intake(Path(self.temp.name)/"intake-001",review,packet)
        self.assertFalse(result["independence_eligible"]);self.assertFalse(result["learning_export_allowed"])
        self.assertEqual(result["review_basis"],"SCENE_CONDITIONED_CNL_CLAIM_REVIEW")
        self.assertFalse(result["english_only_fidelity_established"])
        response["kind"]="CNL";r.write_json(review,response)
        with self.assertRaises(ValueError):r.intake(Path(self.temp.name)/"bad-001",review,packet)

    def test_manifest_and_immutable_output(self):
        m=r.revalidate_run(self.out)
        for p,sha in m["code_hashes"].items():r.verified(ROOT/p,sha)
        with self.assertRaises(FileExistsError):entry.run(self.out)

    def test_javascript_syntax(self):
        script=re.search(r'<script>\s*(.*?)</script>',entry.TEMPLATE.read_text(),re.S)[1]
        subprocess.run(["node","--check"],input=script,text=True,capture_output=True,check=True)

    def test_ui_refresh_preserves_packet_and_source(self):
        output=Path(self.temp.name)/"ui-refresh-001"
        before={p.name:r.digest(p) for p in self.out.iterdir()}
        result=entry.refresh_review(output,self.out)
        self.assertTrue(result["draft_compatible"])
        self.assertEqual(r.digest(output/"scene18_scene_cnl_review_packet.json"),before["scene18_scene_cnl_review_packet.json"])
        self.assertEqual({p.name:r.digest(p) for p in self.out.iterdir()},before)
        r.revalidate_run(output)
        self.assertIn("function collect()",(output/"scene18_scene_cnl_review.html").read_text())
        with self.assertRaises(FileExistsError):entry.refresh_review(output,self.out)

    def test_ui_text_choices_zoom_restore_and_export(self):
        script=re.search(r'<script>\s*(.*?)</script>',entry.TEMPLATE.read_text(),re.S)[1]
        harness=r'''
const vm=require('vm'),assert=require('assert'),input=JSON.parse(require('fs').readFileSync(0,'utf8'));
const nodes=new Map(),stored=new Map();let downloads=0,downloadText='';
function node(){return {value:'',textContent:'',children:[],classList:{toggle(){}},set id(v){nodes.set(v,this)},focus(){this.focused=true},
 setAttribute(k,v){this[k]=v},append(...x){this.children.push(...x)},appendChild(x){this.children.push(x)},
 replaceChildren(){this.children=[]},showModal(){this.open=true},close(){this.open=false},click(){downloads++}}}
function get(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)}
const p=input.packet;p.packet_sha256=input.sha;p.images=p.frames.map((_,i)=>'test-image-'+i);
get('packet').textContent=JSON.stringify(p);
const context={document:{getElementById:get,createElement:node,createElementNS:node},
 localStorage:{getItem:k=>stored.get(k),setItem:(k,v)=>stored.set(k,v)},
 Blob:class{constructor(parts){downloadText=parts.join('')}},URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},setTimeout(){},assert};
const probe=`
assert.equal($('generatedText').textContent,P.generated_text_ko);
assert.equal($('items').children.length,4);assert(Object.values(state.answers).every(v=>v===''));
$('export').onclick();assert($('status').textContent.includes('입력'));
for(const [id,value]of Object.entries({reviewer_id:'SYNTHETIC_TEST_ONLY',independence:'UNCERTAIN',reason:'TEMPORARY_UI_TEST'})){$(id).value=value;$(id).oninput()}
for(const id of P.clause_ids){$('answer_'+id).value='UNJUDGEABLE';$('answer_'+id).onchange({target:$('answer_'+id)})}
const before=JSON.stringify(state);$('frame').onclick();assert($('zoomDialog').open);$('nativeZoom').onclick();$('closeZoom').onclick();assert(!$('zoomDialog').open);
assert.equal($('zone').children.length,2);$('prev').onclick();assert.equal($('zone').children.length,0);$('atEvent').onclick();assert.equal($('zone').children.length,2);
assert.equal(JSON.stringify(state),before);restore(JSON.parse(localStorage.getItem(key)));assert.equal(JSON.stringify(state),before);
assert.throws(()=>restore({...record(),kind:'CNL'}));assert.throws(()=>restore({...record(),packet_sha256:'old'}));
assert.equal(JSON.stringify(state),before);
// DOM-only edits model autofill, restored select values and input events not delivered.
$('reason').value='';$('export').onclick();
assert($('status').textContent.includes('판단 근거'));assert(!$('status').textContent.includes('참여 여부'));
assert($('reason').focused);assert(Object.values(state.answers).every(v=>v==='UNJUDGEABLE'));
$('reason').value='DOM_ONLY_TEST_REASON';$('reviewer_id').value='DOM_ONLY_TEST_REVIEWER';
$('answer_'+P.clause_ids[0]).value='UNSUPPORTED';$('export').onclick();
assert.equal(state.reason,'DOM_ONLY_TEST_REASON');assert.equal(state.reviewer_id,'DOM_ONLY_TEST_REVIEWER');
assert.equal(state.answers[P.clause_ids[0]],'UNSUPPORTED');`;
vm.runInNewContext(input.script+probe,context);assert.equal(downloads,1);
function visible(n){return n.textContent+' '+n.children.map(visible).join(' ')}
assert(!/sha256:|[a-f0-9]{64}/.test(visible(get('items'))));
vm.runInNewContext(input.script+"assert.equal(state.reviewer_id,'DOM_ONLY_TEST_REVIEWER');assert.equal(state.answers[P.clause_ids[0]],'UNSUPPORTED');",{...context});
process.stdout.write(downloadText);
'''
        result=subprocess.run(["node","-e",harness],input=json.dumps({"script":script,"packet":self.packet,
            "sha":r.digest(self.out/"scene18_scene_cnl_review_packet.json")}),text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        response=json.loads(result.stdout)
        from guard_synth.independent_development_review import validate_independent_review
        verdict=validate_independent_review(response,self.packet,r.digest(self.out/"scene18_scene_cnl_review_packet.json"))
        self.assertFalse(verdict["judgement_available"])


if __name__=="__main__":unittest.main()
