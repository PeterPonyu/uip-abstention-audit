# V6 (MT) — cross-model disagreement predicts MLIP error and gates stable-call precision (but is not a universal flip predictor)

Date: 2026-06-15 · `dl4080` `graph` conda env (pandas + scipy, CPU). Data: full Matbench Discovery WBM
(256,963 structures) truth + 4 modern UIP formation-energy predictions (MACE / CHGNet / M3GNet / ORB),
the same cached compact CSVs as V2. Script: `v6_disagreement_reliability.py` · Raw: `results/V6/v6_result.*`.

## Why
No single MLIP knows its own error. But four *independently trained* modern UIPs disagree more where they are
wrong, so their **disagreement** (std of e_form_pred across the 4 models) is a label-free, training-free
uncertainty signal — the materials analogue of V3's AD-predicts-error and V7's ensemble spread. V6 asks,
falsifiably, on the full leakage-removed WBM: (1) does disagreement predict the consensus regression error?
(2) does abstaining on the most-disagreeing structures raise *stability-classification* precision? (3) shuffle
control; (4) where do the wrong stability calls actually sit? Predicted hull = true_hull + (mean e_form_pred −
e_form_true); stable = e_above_hull < 0.

## Results

**Disagreement strongly predicts error:** Spearman(disagreement, |consensus error|) = **0.714**; against the
per-model-mean error it is **0.900**. Disagreement nearly determines how wrong the UIPs are on a structure.

| coverage (keep lowest-disagreement) | stability precision | F1 | n called stable |
|--:|--:|--:|--:|
| 1.0 (all) | 0.741 | 0.777 | 47,269 |
| 0.9 | 0.749 | 0.793 | 45,974 |
| 0.8 | 0.759 | 0.801 | 43,802 |
| 0.7 | 0.774 | 0.811 | 40,949 |
| 0.6 | 0.791 | 0.822 | 37,116 |
| 0.5 | **0.807** | **0.830** | 32,719 |

Precision gain abstaining on the top-30% most-disagreeing: **0.741 → 0.774** (bootstrap 95% CI on gain
**[0.031, 0.035]**, excludes 0); **shuffled-disagreement control 0.739 (≈ no gain ✓)**. At 50% coverage,
precision 0.807 / F1 0.830.

Error-type by disagreement quartile (Q1 low → Q4 high): total flip rate **[0.088, 0.081, 0.075, 0.069]**;
false-STABLE (FP) **[0.045, 0.053, 0.057, 0.036]**; false-UNSTABLE (FN) **[0.043, 0.027, 0.019, 0.033]**.

## Adjudication — SUPPORTED for what it actually does, with a precise honest scope

1. **Disagreement is a strong, label-free error predictor (SUPPORTED).** ρ(disagreement, |consensus error|) =
   0.714 on 256,963 structures — decisively non-trivial. Cross-model disagreement is a genuine uncertainty
   proxy, no labels required.
2. **It is a decision-grade *precision* gate for "is this stable?" (SUPPORTED, CI-clean).** Abstaining on the
   most-disagreeing structures monotonically raises stable-call precision (0.741→0.807 at 50% coverage) and F1
   (0.777→0.830); the 30%-abstain gain CI [0.031,0.035] excludes 0 and the shuffled-disagreement control shows
   no gain. For the decision that matters in screening — "trust this 'stable, worth synthesizing' call" —
   disagreement abstention works.
3. **HONEST SCOPE / companion negative: disagreement does NOT localize overall misclassification.** The total
   stability-flip rate is essentially flat-to-slightly-*decreasing* across disagreement quartiles (0.088→0.069),
   and the FP/FN split is non-monotonic (FP peaks in the middle quartiles ~0.053–0.057; FN is highest at the
   extremes). The precision gain comes specifically because the high-disagreement structures form a small,
   **FP-dominated, low-precision pocket of stable predictions** that abstention removes — not because high
   disagreement marks misclassifications in general. So the signal is a **precision/regression-error gate, not a
   universal error localizer.** Claiming the latter (as the script's first auto-template line did) would be an
   over-claim; it is corrected here.

## Honest caveats
- Same **fixed-hull each_pred approximation** as MT1/V2 (predicted hull = true_hull + form-energy error; hull
  not recomputed from predictions). Reproduces published F1; absolute numbers can shift with full hull recompute.
- Disagreement = std over **4** UIPs; a larger, more architecturally diverse ensemble would sharpen the estimate.
  The 0.900 correlation to per-model-mean error partly reflects that disagreement and mean-error share the same
  4 predictions.
- Precision is conditional on the (rare, ~16.7% base-rate) stable class; the quartile FP/n rates are not
  precision and must not be read as such (see adjudication point 3).

## Conclusion
**V6 is supported with a sharp scope.** Cross-model disagreement among modern UIPs is a strong label-free
predictor of regression error (ρ=0.714) and a CI-clean, shuffle-controlled **precision gate** for stability
decisions (precision 0.74→0.81, F1 →0.83 at 50% coverage) — the materials instance of "the model's own
uncertainty is a decision variable." The honest boundary: it gates the *precision of positive (stable) calls*
and tracks *regression-error magnitude*; it does **not** predict overall misclassification rate. This pairs with
V2 (low MAE *does* predict good decisions for modern UIPs) to complete the materials reliability card: trust the
consensus, abstain where the models disagree. Benchmark-only; no materials-discovery claim.

## Source
Matbench Discovery — Nature Machine Intelligence 2025, `10.1038/s42256-025-01055-1`; UIP predictions per V2
(MACE/CHGNet/M3GNet/ORB Figshare releases). Disagreement-as-uncertainty framing per the workspace methodology.
