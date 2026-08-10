# Small-VLM guard learning pilot

- model: `Qwen/Qwen3-VL-2B-Instruct`
- train examples per condition: 576
- epochs: 2

| Metric | Correct guard training | Shuffled-guard training |
|---|---:|---:|
| Held-out accuracy | 0.990 | 0.719 |
| Counterfactual scene rate | 0.958 | 0.000 |
| Unseen-paraphrase accuracy | 0.740 | 0.745 |
| STOP prediction rate | 0.490 | 0.406 |

Correct-minus-shuffled held-out accuracy: +0.271

## Predeclared criteria

- PASS: `held_out_accuracy_at_least_0p80`
- PASS: `accuracy_gain_vs_shuffled_at_least_0p15`
- PASS: `counterfactual_scene_rate_at_least_0p60`
- PASS: `paraphrase_accuracy_at_least_0p70`
- PASS: `no_always_stop_collapse`

Overall: 5/5 criteria passed.

This synthetic result tests whether guard/trajectory alignment is learnable. It is not a real-road safety result.
