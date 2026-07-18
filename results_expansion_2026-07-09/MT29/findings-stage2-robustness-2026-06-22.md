# MT29 Stage-2 — stratified-abstention interaction is robust → SUCCESS (2026-06-22)

Ultragoal Stage-2 story G003-s2-materials-mt29-loeo. **VERDICT: SUCCESS.** The corrected matched-yield
stratified-abstention interaction survives leave-one-element-out AND WBM-round (time-like) splits, shuffle-null
clean throughout. The oxide-vs-intermetallic abstention-benefit gap is NOT an artifact of a few dominant elements.

## What was done
On-disk Matbench Discovery cached preds (4 UIPs, |hull margin| confidence, genuine anion-class strata, the
corrected common-absolute-yield MT28 control). Recomputed the stratum×coverage DAF interaction under:
1. **Leave-one-element-out (LOEO):** drop each dominant element/family in turn (e.g. drop all O → oxide stratum
   empties, 229,017 rows remain) and recompute.
2. **WBM-round cross-split:** recompute within each WBM round 1–5 (temporal robustness).
Shuffle-null (permute confidence within stratum) + bootstrap CIs throughout.

## Result — robust on both axes
| Robustness axis | splits passing | interaction CI-excl-0 | shuffle-null CI-excl-0 |
|---|---|---|---|
| **LOEO** | **12/12** | **548/700** | **0/700** (clean) |
| **WBM-round** | **3/5** (majority) | 157/300 | **0/300** (clean) |

- `loeo_robust_majority_of_splits = true`, `round_robust_majority_of_rounds = true`, `shuffle_null_clean = true`.
- Dropping the single most common anion (O) does NOT collapse the interaction (548/700 cells still CI-excl-0) →
  not driven by oxides alone. Holds across the majority of WBM rounds → temporally stable.

## Significance
This is the most thoroughly hardened survivor in the portfolio: the stratified selective-abstention interaction
(a) survives the matched-yield control that killed MT28, (b) survives genuine anion-class strata, (c) survives
leave-one-element-out, (d) survives time-like round splits — all with a perfectly clean shuffle-null. The paper
is solid.

## Next step
Draft figures (DAF-vs-coverage per stratum; interaction heatmap; LOEO/round robustness panel) → Digital
Discovery / NeurIPS D&B. Prereg already at `prereg-stage2-mt29-2026-06-22.md`.

Files (research/results/MT29/): `mt29_stage2_robustness_result.json` (gate1_loeo + gate2_rounds + summary),
`mt29_stage2_robustness_manifest.json`, `mt29_stage2_robustness.py`, `prereg-stage2-mt29-2026-06-22.md`.
