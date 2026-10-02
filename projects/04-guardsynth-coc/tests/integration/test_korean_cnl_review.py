"""Korean assistance keeps source identity, versions and human-answer provenance."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=next(p for p in Path(__file__).resolve().parents if (p/"PROJECT_REGISTRY.json").exists())
sys.path.insert(0,str(ROOT/"projects/04-guardsynth-coc/experiments/paper1_cnl_learning"))
import localize_cnl_review as localizer
r=localizer.runner


class KoreanReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.out=Path(cls.temp.name)/"ko-001"
        localizer.run(cls.out)
        cls.packet=r.load(cls.out/localizer.PACKET_NAME)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_original_fields_preserved_and_packet_version_changed(self):
        parent=r.load(localizer.PARENT/localizer.PACKET_NAME)
        for key,value in parent.items():self.assertEqual(self.packet[key],value,key)
        self.assertNotEqual(r.digest(self.out/localizer.PACKET_NAME),localizer.PARENT_SHA)
        self.assertEqual(r.digest(localizer.PARENT/localizer.PACKET_NAME),localizer.PARENT_SHA)

    def test_five_translations_and_provenance_aliases(self):
        k=self.packet['korean_review']
        self.assertEqual(set(k['clauses']),set(self.packet['clause_ids']))
        self.assertEqual(set(k['reference_aliases']),set(self.packet['contract']['source_refs']))
        self.assertEqual(len(set(k['reference_aliases'].values())),4)
        self.assertNotIn('sha256:',json.dumps(k['contract_ko']))
        for cid in ('ped','road'):
            text=k['clauses'][cid]['translation']
            for term in ('그 경우에만','이전 활성 상태','해제 이후','별도 입력','진입을 금지'):self.assertIn(term,text)
        self.assertIn('진입을 강제하지 않습니다',k['clauses']['action.composition']['translation'])
        self.assertEqual(len(k['core_ko']),len(self.packet['core_semantics']['clauses']))
        self.assertTrue(any('다음 시점' in c['논리식'] for c in k['core_ko']))

    def test_intake_records_assisted_basis_not_english_fidelity(self):
        packet_path=self.out/localizer.PACKET_NAME
        response={'review_version':r.VERSION,'packet_sha256':r.digest(packet_path),'kind':'CNL',
            'reviewer_id':'SYNTHETIC_TEST_ONLY','reviewed_at':'2026-09-08T00:00:00Z',
            'independence':'INDEPENDENT','reason':'SYNTHETIC_TEST_ONLY_NOT_HUMAN',
            'answers':{cid:'UNJUDGEABLE' for cid in self.packet['korean_review']['review_clause_ids']}}
        review=Path(self.temp.name)/'synthetic.json';r.write_json(review,response)
        result=r.intake(Path(self.temp.name)/'intake-001',review,packet_path)
        self.assertEqual(result['review_basis'],localizer.BASIS)
        self.assertFalse(result['english_only_fidelity_established'])
        self.assertFalse(result['judgement_available']);self.assertFalse(result['learning_export_allowed'])
        self.assertEqual(result['reviewed_clause_ids'],['ped','road','action.composition'])
        self.assertEqual(result['excluded_review_clause_ids'],['action.identity','action.sources'])
        response['answers']['action.identity']='MATCH';r.write_json(review,response)
        with self.assertRaises(ValueError):r.intake(Path(self.temp.name)/'extra-001',review,packet_path)
        del response['answers']['action.identity']
        response['packet_sha256']=localizer.PARENT_SHA;r.write_json(review,response)
        with self.assertRaises(ValueError):r.intake(Path(self.temp.name)/'bad-001',review,packet_path)

    def test_immutable_hashes_and_no_human_answers(self):
        m=r.revalidate_run(self.out)
        for rel,sha in m['code_hashes'].items():r.verified(ROOT/rel,sha)
        self.assertFalse(self.packet['gold_prefilled'])
        self.assertNotIn('answers',self.packet)
        with self.assertRaises(FileExistsError):localizer.run(self.out)

    def test_pairs_reference_exact_actual_output_and_core(self):
        k=self.packet['korean_review']
        self.assertEqual(k['review_clause_ids'],['ped','road','action.composition'])
        cnl={c['clause_id']:c['text'] for c in self.packet['cnl_mapping']['clauses']}
        core={c['id']:c for c in self.packet['core_semantics']['clauses']}
        for cid,pair in k['pairs'].items():
            start=pair['excerpt_start'];excerpt=pair['generated_excerpt']
            self.assertEqual(cnl[cid][start:start+len(excerpt)],excerpt)
            self.assertEqual(pair['source_core'],[core[key] for key in pair['core_clause_ids']])
            self.assertTrue(pair['source_explanation']);self.assertTrue(pair['translation_lines'])
            self.assertNotIn('조건부 명세',str(pair['translation_lines']))
        self.assertEqual(set(core),{c for pair in k['pairs'].values() for c in pair['core_clause_ids']})


if __name__=='__main__':unittest.main()
