# V6 (MT) — cross-model disagreement as a stability-decision uncertainty signal

4 modern UIPs (MACE/CHGNet/M3GNet/ORB) on full WBM (n=256963). Disagreement = std of e_form_pred across models.

**Disagreement predicts consensus error:** Spearman(disagree, |err|) = **0.714** (per-model-mean err 0.900).

| coverage (keep lowest-disagreement) | stability precision | F1 | n called stable |
|--:|--:|--:|--:|
| 1.0 | 0.7405 | 0.7771 | 47269 |
| 0.9 | 0.7485 | 0.7929 | 45974 |
| 0.8 | 0.7587 | 0.8013 | 43802 |
| 0.7 | 0.7737 | 0.8112 | 40949 |
| 0.6 | 0.7914 | 0.8217 | 37116 |
| 0.5 | 0.807 | 0.83 | 32719 |

Precision gain abstaining on top-30% disagreement: 0.7405 -> 0.7737 (bootstrap 95% CI on gain [0.0312, 0.0349]); shuffled-disagreement control: 0.7394 (≈no gain).

Decision-flip (mis-stable OR mis-unstable) rate by disagreement quartile (Q1 low -> Q4 high): [0.0875, 0.0808, 0.075, 0.0693]. NOTE: disagreement gates stable-call PRECISION (it filters false-positive 'stable' calls), but does NOT track overall misclassification rate -- see findings.
  false-STABLE (FP) by quartile: [0.045, 0.0534, 0.0565, 0.0361]  |  false-UNSTABLE (FN) by quartile: [0.0426, 0.0274, 0.0185, 0.0332]
