import importlib.util
from pathlib import Path
import unittest

MODULE=Path(__file__).resolve().parents[1]/'build_review_packet.py'
class ReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), 'Review packet implementation is not present yet')
        spec=importlib.util.spec_from_file_location('review_packet',MODULE)
        self.api=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.api)
    def test_excludes_known_scenes_and_single_events(self):
        scenes={'old':[{},{}],'one':[{}],'new':[{},{}]}
        self.assertEqual(self.api.select_scenes(scenes,{'old'},24,3),['new'])
    def test_deterministic_independent_of_mapping_order(self):
        scenes={str(i):[{},{}] for i in range(30)}
        a=self.api.select_scenes(scenes,set(),24,5)
        b=self.api.select_scenes(dict(reversed(list(scenes.items()))),set(),24,5)
        self.assertEqual(a,b);self.assertEqual(len(set(a)),24)
    def test_zero_or_negative_sample_rejected(self):
        with self.assertRaises(ValueError):self.api.select_scenes({},set(),0,1)
    def test_packet_does_not_contain_gold_or_source_scene_id(self):
        page=self.api.render_html([{'review_id':'REV-opaque','events':[{'event_index':0,'time_s':0,'text':'Stop <until> clear.'}]}])
        self.assertIn('Stop &lt;until&gt; clear.',page)
        self.assertNotIn('TEXTUAL_CONTRADICTION',page)
        self.assertNotIn('scene-',page)
    def test_repeated_source_event_not_silently_dropped(self):
        page=self.api.render_html([{'review_id':'REV-opaque','events':[{'event_index':0,'time_s':0,'text':'Hold.'},{'event_index':1,'time_s':1,'text':'Hold.'}]}])
        self.assertEqual(page.count('Hold.'),2)
    def test_canonical_event_indexes_displayed_not_row_numbers(self):
        page=self.api.render_html([{'review_id':'REV-opaque','events':[{'event_index':7,'time_s':0,'text':'First.'},{'event_index':2,'time_s':1,'text':'Second.'}]}])
        self.assertIn('<td>7</td>',page)
        self.assertIn('<td>2</td>',page)
    def test_exposure_validator_exists(self):
        self.assertTrue(callable(getattr(self.api,'validate_exposure',None)))
        with self.assertRaises(ValueError):self.api.validate_exposure([{'scene_id':'a'}],{'a':[], 'b':[]})
    def test_duplicate_exposure_rejected(self):
        self.assertTrue(callable(getattr(self.api,'validate_exposure',None)))
        row={'scene_id':'a','known_trajectory_analysis':'False','known_old_review':'False'}
        with self.assertRaises(ValueError):self.api.validate_exposure([row,row],{'a':[]})
    def test_invalid_exposure_boolean_rejected(self):
        self.assertTrue(callable(getattr(self.api,'validate_exposure',None)))
        with self.assertRaises(ValueError):self.api.validate_exposure([{'scene_id':'a','known_trajectory_analysis':'','known_old_review':'False'}],{'a':[]})
if __name__=='__main__':unittest.main()
