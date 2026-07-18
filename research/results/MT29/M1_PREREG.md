# MT29 · M1 pre-registration — committee-variance robustness of the stratified matched-yield abstention interaction

Date written: 2026-07-01 (BEFORE running E1/E3). Author: ZeyuFu.
Compute: CPU, on-disk cached Matbench-Discovery WBM preds (`~/mt_uip/{chgnet,m3gnet,mace,orb}_pred.csv`,
`~/mt_stage0/data/2023-12-13-wbm-summary.csv.gz`), `conda run -n dl python`. No GPU, no downloads.

## Background / what is already fixed (not being re-litigated here)

The single-model Stage-1 matched-yield control (`mt29_stage1_matched_yield_fix.py` →
`mt29_stage1_matched_yield_result.json`) already reports a **SUCCESS**: 48/60 (model,stratum-pair)
matched-yield DAF abstention-benefit interactions CI-exclude-0, shuffle-null 0/60. The abstention
signal there is a **single model's** predicted-hull margin `|hull_pred_m|`. The per-pair sign is
single-model-consistent (14/15 stratum-pairs have a unique agreed sign among the significant cells;
oxide-anchored pairs positive, `*-other` / halide/pnictide pairs negative). The single-model
reference sign map (from the existing JSON, pre-existing data) is:

```
oxide vs {chalcogenide,halide,intermetallic,other,pnictide} : +
intermetallic vs {chalcogenide?,halide}                     : +   (intermetallic-chalcogenide split)
chalcogenide vs halide                                       : +
chalcogenide vs {other,pnictide}                             : -
halide vs {other,pnictide}                                   : -
intermetallic vs {other,pnictide}                            : -
pnictide vs other                                            : -
```
Dominant single-model sign (median of the 48 significant interaction_med) = **+ (0.0663)**.

## M1 question

Is the stratum×coverage matched-yield abstention benefit a property of *committee disagreement*
(a model-agnostic reliability axis), or an artifact of one model's margin? E1 forks the abstention
signal from a single model's `|hull_pred_m|` to the **committee variance**: std across the 4 UIPs of
the reconstructed predicted hull. Low committee variance = high confidence (keep first); high variance
= abstain. Consensus stable call = mean predicted hull < 0. Everything else (common absolute matched
yield Y across strata, DAF = precision/base-rate, `Y_loose = min over strata of committee-called-stable`,
`Y_tight = Y_loose//2`, 1000-boot percentile CIs, seed 20260621, shuffle-null) is held identical to
`mt29_stage1_matched_yield_fix.py`.

## PRE-REGISTERED TWO-BRANCH GATE (both branches evaluated & reported; no HARKing)

Let the committee produce, per stratum-pair p (15 pairs over the 6 anion families), an interaction
median `I_c(p)`, a 95% bootstrap CI, `excl0_c(p)`, and `sign_c(p)=sign(I_c(p))`.
Let `S_single(p)` = the single-model reference sign for pair p (map above; defined when the significant
single-model cells agree on sign). Let the single-model **consensus** significance for pair p be
`excl0_single(p)` = (>=2 of 4 models CI-exclude-0 for p).

**Branch A — PASS-robustness** (committee reproduces the stratum×coverage interaction sign):
PASSes iff (i) the committee yields >=1 pair with `excl0_c(p)` true, AND (ii) among pairs with both
`excl0_c(p)` true and `S_single(p)` defined, `sign_c(p)==S_single(p)` for a **strict majority (>50%)**
of those pairs. (Secondary read-out, not gating: committee dominant sign = sign(median of significant
`I_c`) equals the single-model dominant sign `+`.)

**Branch B — PASS-contrast** (committee is not a trivial re-derivation of a single model):
PASSes iff there exists >=1 stratum-pair where the committee significance decision differs from the
single-model consensus, i.e. `excl0_c(p) != excl0_single(p)` for at least one p, OR `sign_c(p)`
disagrees with `S_single(p)` on at least one committee-significant pair. (The committee is a distinct
signal, so at least one such difference is expected; identical results on all 15 pairs would FAIL B.)

**Shuffle-null hygiene (must hold for either branch to count as evidence):** permuting the committee
variance within each stratum's called-stable set must collapse the interaction to <=5% CI-exclude-0
false positives (same rule as the single-model script).

Honest-negative is acceptable: if Branch A FAILs (committee does not reproduce the sign) that is a
reportable falsification of the "disagreement drives the interaction" reading, and if Branch B FAILs
the committee added nothing over a single model. No branch outcome is privileged in advance.

## E3 (defensive, no gate) — SSCS-style stratified conditional coverage

Reuse the native-Gaussian probability from `mt29_crossgen_reliability_exec_2026_06_29.py`
(`p_native = Phi(-hull_pred/sigma)`, `sigma = RMSE(err)` on the calibration half, scored on the test
half, seed 20260629). Per anion-family stratum on the test half, compute the conditional-coverage /
calibration-in-the-large gap `gap = mean(p_native) - empirical_stable_rate`, with a 1000-boot
percentile 95% CI (resample within stratum). Aggregate **SSCS = max_stratum |gap|** (worst-slab
deviation, size-stratified-coverage style) with its own bootstrap CI, per UIP. Descriptive only.

## median-vs-mean audit (manuscript mislabel check)

Record verbatim what statistic the ORIGINAL scripts report as the headline abstention number.
`mt29_stage1_matched_yield_fix.py` uses `np.median` of the within-stratum bootstrap gain/interaction
distribution (fields `gain_median`, `interaction_med`); the CI is the 2.5/97.5 percentile. It does
NOT report the bootstrap mean. Any manuscript sentence calling this the "mean" abstention benefit is
mislabeled.

## Outputs
- E1 → `research/results/MT29/mt29_committee_variance.json`
- E3 → `research/results/MT29/mt29_sscs_stratified.json`
- E2 (multi-seed) is DEFERRED — not run in M1.
