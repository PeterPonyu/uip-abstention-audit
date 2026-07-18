# V6b (materials) — disagreement as a per-model error flag + model routing (WBM, 4 UIPs)

n=256963. Disagreement = std of e_form_pred across MACE/CHGNet/M3GNet/ORB.

| model | MAE (eV) | Spearman(disagreement, |error|) |
|---|--:|--:|
| mace | 0.0292 | 0.3839 |
| chgnet | 0.0611 | 0.7105 |
| m3gnet | 0.0726 | 0.7874 |
| orb | 0.0285 | 0.4221 |

Best single model MAE: orb 0.0285. Ensemble-mean MAE: 0.0390.
Consensus-closest routing MAE: 0.0420 (beats best single: False; beats ensemble-mean: False).

Per-model Spearman>0 = disagreement flags each per-model error; routing tests if disagreement enables label-free model selection.
