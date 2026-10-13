"""Behavioral checks: condition binding, forgotten history and abstention accounting."""
import importlib.util
from pathlib import Path
import unittest

MODULE=Path(__file__).resolve().parents[1]/'scenario_evaluation.py'

class ScenarioEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), 'scenario evaluation implementation absent')
        spec=importlib.util.spec_from_file_location('scenario_evaluation',MODULE)
        self.api=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.api)

    def case(self,variant,gap=0):
        return next(c for c in self.api.build_cases() if c['family']=='pedestrian' and c['variant']==variant and c['gap']==gap)

    def test_no_case_filtering_and_balanced_factorial(self):
        cases=self.api.build_cases()
        self.assertEqual(len(cases),144)
        self.assertEqual(len({c['case_id'] for c in cases}),144)
        self.assertTrue(all(len([x for x in cases if x['family']==family])==24 for family in {c['family'] for c in cases}))

    def test_foreign_release_never_becomes_active_release(self):
        events,links=self.api.project_frames(self.case('wrong_release'))
        self.assertFalse(events[-1].release_known)
        self.assertEqual(links[-1]['bound_release_evidence'],None)

    def test_explicit_normal_release_is_bound_to_original_condition(self):
        events,links=self.api.project_frames(self.case('released_normal'))
        self.assertTrue(events[-1].release_known)
        self.assertTrue(events[-1].release_value)
        self.assertEqual(links[-1]['bound_condition'],'A')

    def test_frames_have_exact_source_spans(self):
        for c in self.api.build_cases():
            for e in c['events']:
                for s in e['source_spans']:
                    self.assertEqual(e['text'][s['start']:s['end']],s['quote'])

    def test_fsm_missing_release_is_unknown_not_false(self):
        result=self.api.check_fsm(self.case('missing_release')['events'])
        self.assertEqual(result['verdict'],'UNKNOWN')
        self.assertIsNone(result['first_event_id'])
        self.assertEqual(result['issues'][0]['reason'],'RELEASE_EVIDENCE_MISSING')

    def test_fsm_multi_requirement_cannot_disappear(self):
        c=self.case('multi_partial')
        result=self.api.check_fsm(c['events'])
        self.assertEqual(result['verdict'],'CONTRADICTION')
        self.assertEqual(result['first_event_id'],c['events'][-1]['event_id'])
        self.assertEqual(result['issues'][0]['obligation_id'],'C')

    def test_fsm_all_releases_allow_proceed(self):
        self.assertEqual(self.api.check_fsm(self.case('multi_all_released')['events'])['verdict'],'CONSISTENT')

    def test_fsm_recent_context_loses_old_obligation(self):
        c=self.case('held_memory_conflict',6)
        self.assertEqual(self.api.check_fsm(c['events'])['verdict'],'CONTRADICTION')
        self.assertEqual(self.api.check_fsm(c['events'][-2:])['verdict'],'CONSISTENT')

    def test_projection_declares_multi_requirement_loss(self):
        events,links=self.api.project_frames(self.case('multi_partial'))
        self.assertTrue(any(x['unrepresentable_conditions'] for x in links))

    def test_unknown_positive_stays_in_recall_denominator(self):
        rows=[{'expected':'CONTRADICTION','predicted':'UNKNOWN'},{'expected':'CONTRADICTION','predicted':'CONTRADICTION'},{'expected':'CONSISTENT','predicted':'CONSISTENT'}]
        result=self.api.summarize(rows)
        self.assertEqual(result['recall_all_positive'],0.5)
        self.assertEqual(result['positive_abstentions'],1)
        self.assertEqual(result['three_class_correct'],2)

    def test_missing_class_metric_is_undefined(self):
        result=self.api.summarize([{'expected':'UNKNOWN','predicted':'UNKNOWN'}])
        self.assertIsNone(result['recall_all_positive'])
        self.assertIsNone(result['normal_false_alarm_rate'])

if __name__=='__main__':unittest.main()
