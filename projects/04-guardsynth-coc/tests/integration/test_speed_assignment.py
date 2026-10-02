"""Relayed self-report provenance and unassigned ACTION preparation boundaries."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
CODE = ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning/prepare_speed_assignment.py'
spec = importlib.util.spec_from_file_location('speed_assignment', CODE)
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)


class SpeedAssignmentTest(unittest.TestCase):
    def test_self_report_preserves_words_scope_and_no_invented_authentication(self):
        d = prep.declaration()
        self.assertEqual(d['relayed_answer_verbatim'], '아니요')
        self.assertEqual(d['relay_confirmation_answer_verbatim'], '네')
        self.assertIsNone(d['declared_at'])
        self.assertEqual(d['recorded_date'], '2026-09-29')
        self.assertFalse(prep.accept_declaration(d)['dispatch_allowed'])
        for k, v in (('relay_confirmed_by_user', False), ('relayed_answer_verbatim', '네'),
                     ('declared_at', 'invented'), ('identity_authenticated', True),
                     ('assignment_authorized', True), ('webform_submission', True)):
            with self.subTest(k=k), self.assertRaises(ValueError):
                prep.accept_declaration({**d, k: v})

    def test_packet_rejects_answer_cues_and_future(self):
        p = json.loads((prep.SOURCE / 'action_input_pool.json').read_text())
        p['scenes'][0]['original_coc'] = 'cue'
        with self.assertRaises(ValueError):
            prep.make_packet(p)
        del p['scenes'][0]['original_coc']
        p['scenes'][0]['frames'][0]['timestamp_us'] = p['scenes'][0]['event_timestamp_us'] + 1
        with self.assertRaises(ValueError):
            prep.make_packet(p)

    def test_end_to_end_proposal_hashes_and_ui_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'assignment-001'
            result = prep.execute(out)
            self.assertEqual(result['proposed_scene_count'], 19)
            self.assertEqual(result['proposed_action_slots'], 76)
            self.assertIsNone(result['actual_assignment_count'])
            for k in ('reviewer_dispatched', 'action_responses_received', 'independent_speed_action_gold', 'new_training_scenes'):
                self.assertEqual(result[k], 0)
            proposal = json.loads((out / 'assignment_proposal.json').read_text())
            self.assertEqual(proposal['candidate_indices'], prep.INDICES)
            self.assertEqual(proposal['held_candidate_indices'], [79, 81])
            packet = json.loads((out / 'action_review_packet.json').read_text())
            self.assertEqual(len(packet['scenes']), 19)
            for s in packet['scenes']:
                self.assertEqual(set(s), {'sample_id', 'event_timestamp_us', 'frames'})
            html = (out / 'action_review_preview.html').read_text()
            self.assertNotIn('__PACKET__', html)
            self.assertNotIn('fetch(', html)
            self.assertNotIn('XMLHttpRequest', html)
            display = json.loads(re.search(r'<script id="packet" type="application/json">(.*?)</script>', html, re.S).group(1))
            self.assertEqual(display.pop('packet_sha256'), proposal['packet_sha256'])
            self.assertEqual(display, packet)
            script = re.findall(r'<script>(.*?)</script>', html, re.S)[0]
            # Execute UI logic with minimal DOM/storage doubles; no browser exposure or responses.
            harness = '''const assert=require('node:assert/strict');
const elements={};function element(){return {textContent:'',value:'',disabled:false,children:[],append(x){this.children.push(x)},replaceChildren(){this.children=[]},add(x){this.children.push(x)}};}
global.document={getElementById(id){return elements[id]||(elements[id]=element())},createElement:element};
global.Option=function(t,v){this.text=t;this.value=v};
global.localStorage={getItem(){return null},setItem(){}};
document.getElementById('packet').textContent=JSON.stringify(PACKET);
'''.replace('PACKET', json.dumps({**packet, 'packet_sha256': proposal['packet_sha256']}))
            checks = '''
assert.equal(draft.records.length,19);assert.equal(completed(draft),0);
assert(draft.records.every(r=>Object.values(r.action_assessments).every(v=>v===null)));
const changed=structuredClone(draft);changed.records[0].reason='test-only';
Object.keys(changed.records[0].action_assessments).forEach(k=>changed.records[0].action_assessments[k]='UNDETERMINED');
assert.equal(completed(validateDraft(changed)),1);
changed.packet_sha256='wrong';assert.throws(()=>validateDraft(changed));
const bad=structuredClone(draft);bad.reviewer_id='Jonh';assert.throws(()=>validateDraft(bad));
el('next').onclick();assert.equal(index,1);el('previous').onclick();assert.equal(index,0);
assert(el('frame').src.startsWith('data:image/jpeg;base64,'));
console.log('UI draft/render/navigation checks passed');
'''
            js = Path(tmp) / 'ui_test.js'
            js.write_text(harness + script + checks)
            checked = subprocess.run(['node', str(js)], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            manifest = json.loads((out / 'RUN_MANIFEST.json').read_text())
            for group in ('input_hashes', 'code_hashes', 'output_hashes'):
                for p, h in manifest[group].items():
                    self.assertEqual(prep.sha(((out if group == 'output_hashes' else ROOT) / p).read_bytes()), h)
            with self.assertRaises(FileExistsError):
                prep.execute(out)


if __name__ == '__main__':
    unittest.main()
