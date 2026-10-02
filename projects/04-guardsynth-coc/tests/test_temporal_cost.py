from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest

import torch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import train_temporal_cost as c


class CostTest(unittest.TestCase):
    def test_cost_target_role_independence_and_rotation(self):
        e = c.fresh_examples('canonical')[0]
        costs = c.candidate_costs(e)
        altered = replace(e, target='NOT_A_TARGET', scene=replace(e.scene,
            candidates=tuple(replace(a, role='deliberately_wrong') for a in e.scene.candidates)))
        self.assertEqual(costs, c.candidate_costs(altered))
        rotated = replace(e, scene=replace(e.scene, candidates=tuple(replace(a,
            label=c.LABELS[(c.LABELS.index(a.label) + 1) % 4]) for a in e.scene.candidates)))
        self.assertEqual(c.candidate_costs(rotated), costs[-1:] + costs[:-1])
        self.assertEqual(sorted(costs), [0., 0., .25, 1.])

    def test_no_progress_no_stop_penalty(self):
        e = c.fresh_examples('canonical')[0]
        e = replace(e, scene=replace(e.scene, candidates=tuple(replace(a,
            entry_time=None if a.entry_time is None else 0.) for a in e.scene.candidates)))
        self.assertEqual(c.candidate_costs(e), [1., 1., 1., 0.])

    @staticmethod
    def batch():
        return {'input_ids': torch.tensor([[5, 6, 0, 7], [5, 6, 2, 7]]),
                'labels': torch.tensor([[-100, -100, 0, 7], [-100, -100, 2, 7]]),
                'attention_mask': torch.ones(2, 4, dtype=torch.long)}

    def test_gradient_causal_position_and_lambda_zero(self):
        logits = torch.zeros(2, 4, 8, requires_grad=True)
        ce = logits.square().sum() + 2
        costs = torch.tensor([[1., 0., .25, 0.], [1., 0., .25, 0.]])
        loss0, expected, mass = c.objective(ce, logits, self.batch(), costs, [0, 1, 2, 3], 0)
        self.assertIs(loss0, ce)
        grad0 = torch.autograd.grad(loss0, logits, retain_graph=True)[0]
        self.assertTrue(torch.equal(grad0, torch.autograd.grad(ce, logits, retain_graph=True)[0]))
        loss, _, _ = c.objective(ce, logits, self.batch(), costs, [0, 1, 2, 3], 1)
        grad = torch.autograd.grad(loss, logits)[0]
        self.assertTrue(torch.isfinite(grad).all())
        self.assertGreater(float(grad[0, 1, 0]), 0)  # descent lowers violating logit
        self.assertLess(float(grad[0, 1, 1]), 0)
        self.assertEqual(int(grad[:, 2:].count_nonzero()), 0)
        self.assertAlmostEqual(float(expected.detach()), .3125)
        self.assertAlmostEqual(float(mass.detach()), .5)

    def test_expected_cost_permutation_and_optimizer_equivalence(self):
        torch.manual_seed(42)
        a = torch.nn.Parameter(torch.randn(2, 4, 8))
        b = torch.nn.Parameter(a.detach().clone())
        oa = torch.optim.AdamW([a], lr=.0002)
        ob = torch.optim.AdamW([b], lr=.0002)
        costs = torch.tensor([[1., 0., .25, 0.]] * 2)
        expected = c.objective(a.square().mean(), a, self.batch(), costs, [0, 1, 2, 3], 0)[1]
        permutation = [2, 0, 3, 1]
        permuted = c.objective(a.square().mean(), a, self.batch(), costs[:, permutation], permutation, 0)[1]
        self.assertTrue(torch.allclose(expected, permuted))
        for _ in range(3):
            oa.zero_grad(); ob.zero_grad()
            loss = c.objective(a.square().mean(), a, self.batch(), costs, [0, 1, 2, 3], 0)[0]
            loss.backward(); b.square().mean().backward(); oa.step(); ob.step()
            self.assertTrue(torch.equal(a, b))

    def test_mask_failures(self):
        batch = self.batch(); batch['labels'][:] = -100
        with self.assertRaisesRegex(ValueError, 'missing assistant'):
            c.action_positions(batch, [0, 1, 2, 3])
        batch = self.batch(); batch['labels'][0, 2] = 7
        with self.assertRaisesRegex(ValueError, 'not an action'):
            c.action_positions(batch, [0, 1, 2, 3])

    def test_fresh_suite_and_frozen_modules(self):
        splits = dict(c.d.SPLITS)
        a = c.fresh_examples('canonical'); p = c.fresh_examples('paraphrase')
        u = c.fresh_examples('unseen_duration')
        self.assertEqual(c.d.SPLITS, splits)
        self.assertEqual([len(a), len(p), len(u)], [240] * 3)
        self.assertEqual({round(e.scene.clear_time * 10) for e in a}, set(range(120, 130)))
        self.assertNotEqual(a[0].rich_coc_text, p[0].rich_coc_text)
        for left, right in zip(a, u):
            self.assertAlmostEqual(right.required_clear_duration - left.required_clear_duration, .3)
            self.assertEqual(c.candidate_costs(left), c.candidate_costs(right))
        for e in a + p + u:
            self.assertTrue(c.x.score(e, e.target)['correct'])

    def test_upstream_incomplete_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for status in ('FAILED', 'RUNNING'):
                (path / 'RESULT.json').write_text(json.dumps({'status': status, 'fits': 18}))
                with self.assertRaisesRegex(ValueError, 'all 18'):
                    c.bind_upstream(path)

    def test_no_violation_candidates(self):
        e = c.fresh_examples('canonical')[0]
        e = replace(e, scene=replace(e.scene, candidates=tuple(replace(a,
            entry_time=None if a.entry_time is None else 20.) for a in e.scene.candidates)))
        self.assertEqual(c.candidate_costs(e), [0., 0., 0., .25])

    def test_incomplete_pairs_refused(self):
        with self.assertRaisesRegex(ValueError, 'incomplete contract pair'):
            c.x.pair_rows([{'scene_id': 1, 'contract_level': 'short', 'correct': True}])

    def test_analysis_positive_negative_ceiling(self):
        # Ten clear-time clusters, twelve pairs per cluster; no model predictions.
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            for scenario, expected in (('positive', 'SUPPORTED'), ('negative', 'NOT_SUPPORTED'),
                                       ('ceiling', 'INCONCLUSIVE'), ('ceiling_with_harm', 'NOT_SUPPORTED')):
                for arm in c.ARMS:
                    for seed in c.x.SEEDS:
                        folder = run / f'{arm.lower()}-seed{seed}'; folder.mkdir(exist_ok=True)
                        rows = []
                        for cluster in range(10):
                            for variant in range(24):
                                violation = (variant < 3 and scenario != 'ceiling' and
                                             (arm != 'CE_EBLC' or scenario == 'negative'))
                                if scenario == 'ceiling_with_harm':
                                    violation = arm == 'CE_EBLC' and variant < 12
                                rows.append({'scene_id': cluster * 12 + variant // 2,
                                    'contract_level': 'short' if variant % 2 == 0 else 'long',
                                    'semantic_cluster': f'clear-{12000 + cluster * 100}',
                                    'correct': not violation, 'guard_violation': violation,
                                    'hold_violation': False, 'deadlock': False, 'goal_complete': True,
                                    'safe_goal_complete': not violation, 'valid': True, 'invalid': False})
                        for split in c.SPLITS:
                            (folder / f'{split}.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
                result = c.analyze(run, {'bootstrap_seed': 20260929})
                self.assertEqual(result['verdict'], expected)
                self.assertEqual(result['results']['canonical']['arms']['CE_ONLY']['coverage']['std_population'], 0)
                if scenario == 'ceiling':
                    self.assertIn('NO_HEADROOM', result['reason'])
                if scenario == 'ceiling_with_harm':
                    self.assertEqual(result['reason'], 'REGRESSION_OR_PRESERVATION_LIMIT_BREACH')
                    self.assertIn('guard_violation_rate', result['regression_metrics'])
                    self.assertEqual(result['results']['canonical']['arms']['CE_ONLY']['guard_violation_rate']['mean'], 0)
                    self.assertEqual(result['results']['canonical']['arms']['CE_EBLC']['guard_violation_rate']['mean'], .5)

    def test_actual_tokenizer_and_multimodal_mask(self):
        from transformers import AutoProcessor
        from vlm_guard_learning.train_qwen_temporal_guard_lora import TemporalCollator
        processor = AutoProcessor.from_pretrained(c.model_path(), local_files_only=True)
        processor.tokenizer.padding_side = 'right'
        ids = c.action_token_ids(processor.tokenizer)
        collator = TemporalCollator(processor, 'RICH_COC')
        e = c.fresh_examples('canonical')[0]
        batch = collator([replace(e, target=label) for label in c.LABELS])
        positions = c.action_positions(batch, ids)
        self.assertEqual(len(set(positions.tolist())), 1)
        self.assertGreater(batch['pixel_values'].numel(), 0)
        for i, pos in enumerate(positions):
            self.assertEqual(int(batch['labels'][i, pos + 1]), ids[i])
            self.assertTrue((batch['labels'][i, :pos + 1] == -100).all())
        prompt = processor.apply_chat_template([collator.user_message(e, 'RICH_COC')],
            tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors='pt')
        self.assertEqual(prompt['input_ids'].shape[1], int(positions[0]) + 1)
        self.assertTrue(torch.equal(prompt['input_ids'][0], batch['input_ids'][0, :positions[0] + 1]))

    def test_actual_checkpoint_delta_not_nonzero(self):
        from safetensors.torch import save_file
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / 'a'; b = Path(tmp) / 'b'; a.mkdir(); b.mkdir()
            save_file({'lora': torch.ones(2, 2)}, str(a / 'adapter_model.safetensors'))
            save_file({'lora': torch.ones(2, 2)}, str(b / 'adapter_model.safetensors'))
            with self.assertRaisesRegex(ValueError, 'no actual'):
                c.adapter_change(a, b)
            save_file({'lora': torch.ones(2, 2) + .1}, str(b / 'adapter_model.safetensors'))
            change = c.adapter_change(a, b)
            self.assertEqual(change['changed_tensor_count'], 1)
            self.assertNotEqual(change['source_sha256'], change['output_sha256'])
            self.assertGreater(change['tensors']['lora']['delta_l2'], 0)


if __name__ == '__main__':
    unittest.main()
