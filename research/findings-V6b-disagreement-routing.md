# V6b (materials) — disagreement flags per-model error, but label-free model routing fails (and naive averaging hurts)

Date: 2026-06-15 · `dl4080` `graph` env (pandas + scipy, CPU). Data: full WBM (256,963), 4 modern UIPs
(MACE/CHGNet/M3GNet/ORB), same cached predictions as V6/V2. Script: `v6b_materials.py` · Raw: `results/V6b/`.

## Why
V6 showed cross-model disagreement gates *consensus* stable-call precision. V6b asks two sharper questions:
(1) does disagreement flag **each individual model's** error (not just the consensus's)? (2) can disagreement
drive **label-free model routing** — pick, per structure, the model closest to the 4-model consensus — to beat
the best single model? The second is the appealing "ensemble + route" idea that practitioners reach for.

## Results

| model | MAE (eV) | Spearman(disagreement, \|its own error\|) |
|---|--:|--:|
| MACE | 0.0292 | 0.384 |
| CHGNet | 0.0611 | 0.711 |
| M3GNet | 0.0726 | 0.787 |
| ORB | 0.0285 | 0.422 |

Best single model: **ORB 0.0285**. Ensemble-mean MAE: **0.0390**. Consensus-closest routing MAE: **0.0420**.
Routing beats best single: **NO**. Routing beats ensemble-mean: **NO**.

## Adjudication — one positive, two honest negatives
1. **Disagreement flags per-model error (all 4 Spearman > 0).** It is a genuine label-free reliability flag for
   every model — and **more predictive for the weaker models** (CHGNet 0.71, M3GNet 0.79) than the strong ones
   (MACE 0.38, ORB 0.42): the weak models are usually the ones that disagree with the consensus when wrong, so
   disagreement "explains" their error more.
2. **Label-free model ROUTING fails (negative).** Picking the consensus-closest model per structure gives MAE
   0.042 — **worse than the best single model ORB (0.029) and worse than the plain ensemble mean (0.039)**.
   Disagreement tells you *that* a prediction is unreliable (V6) but not *which* model to trust; the
   consensus-closest model is often one of the mediocre ones agreeing with each other.
3. **Naive ensembling also hurts here (bonus negative).** The 4-model mean (0.039) is **worse than just using
   ORB (0.029)** — because ORB and MACE are far better than CHGNet/M3GNet, averaging drags in the worse models.
   With heterogeneous-quality UIPs, "average them" is the wrong move.

## Adjudication of the decision rule
The clean materials decision rule that survives V2+V6+V6b: **use the single best-validated UIP (ORB/MACE),
abstain where the models disagree (V6 precision gate), and do NOT average or route** — averaging and
consensus-routing both lose to the best single model when model quality is heterogeneous.

## Honest caveats
- Routing oracle is *consensus-closeness* (label-free, realistic); an *oracle* router (pick the truly-closest to
  ground truth) would of course win — but that needs labels, so it is not a deployable signal. The negative is
  specifically about the *deployable* label-free router.
- Same fixed-hull each_pred / 4-model-shared-prediction caveats as V6. ORB's dominance is on this WBM benchmark.

## Conclusion
**V6b refines the materials reliability card:** cross-model disagreement is a per-model error flag (strongest for
weaker models) but is **not** a model-selection signal — label-free consensus routing loses to the best single
model, and naive 4-model averaging also loses. Trust the best validated UIP, abstain on disagreement, don't
average. Benchmark-only.

## Source
Matbench Discovery — `10.1038/s42256-025-01055-1`; UIP predictions per V2. Extends `findings-V6-disagreement-reliability.md`.
