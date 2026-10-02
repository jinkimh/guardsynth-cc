"""Exercise preparation in an isolated process with the pinned learning solver runtime."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").exists())
EXPERIMENT = ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning"


class SceneTrainingPreflightTest(unittest.TestCase):
    def test_saved_real_processor_evidence_has_no_training_promotion(self):
        source = ROOT / "artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-reviewed-contract-001/scene18-training-preflight-2026-09-08-001"
        result = json.loads((source / "RESULT.json").read_text())
        metrics = result["processor_metrics"]
        self.assertEqual(metrics[0]["prompt_tokens"], metrics[1]["prompt_tokens"])
        self.assertGreater(metrics[1]["supervised_tokens"], metrics[0]["supervised_tokens"])
        for item in metrics:
            self.assertGreater(item["pixel_values_shape"][0], 0)
            self.assertEqual(item["sequence_tokens"] - item["prompt_tokens"], item["supervised_tokens"])
            self.assertLessEqual(item["sequence_tokens"], 8192)
        self.assertFalse(result["learning_export_allowed"])
        self.assertFalse(result["four_arm_comparison_complete"])
        self.assertEqual(result["optimizer_steps"], 0)
        self.assertFalse(result["model_weights_loaded"])

    def test_real_previews_keep_gates_and_supervision_separate(self):
        script = '''
import prepare_scene_training as p
import json
feedback, examples, inputs, details = p.prepare('Jun Choi', 'SYNTHETIC_TEST_ONLY')
assert feedback['reviewed_at'] is None
assert not feedback['formal_per_clause_response']
assert feedback['independence_basis'].startswith('REUSED_PRIOR')
assert examples[0]['input'] == examples[1]['input']
assert examples[0]['common_example_sha256'] == examples[1]['common_example_sha256']
assert 'CONSTRAINTS:' not in examples[0]['target']
assert 'CONSTRAINTS:' in examples[1]['target']
assert 'ACTION: DEFER_ENTRY' not in examples[1]['input']['text']
assert all(e['target'].endswith('ACTION: DEFER_ENTRY') for e in examples)
assert all(e['split']=='dev' and e['preview_only'] and not e['learning_export_allowed'] for e in examples)
assert details['input_frame_offset_us'] <= 0
assert details['event_predicates']['road']['truth'] == 'UNKNOWN'
assert details['matches_expected'] == 12
document = p.r.load(p.linked.GENERATION / 'scene_cnl.json')
for name, statement in [('Jin Hyun Kim','test'), ('Jun Choi','')]:
    try: p.english_feedback(name, statement, document)
    except ValueError: pass
    else: raise AssertionError('missing statement or mismatched identity accepted')
print(json.dumps({'checks':'passed'}))
'''
        result = subprocess.run([sys.executable, "-c", script], cwd=EXPERIMENT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["checks"], "passed")


if __name__ == "__main__":
    unittest.main()
