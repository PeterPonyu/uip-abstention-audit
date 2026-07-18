# MT29 Stage-0 — PASS via stratified-abstention interaction; rank-reordering is NULL (2026-06-21)

Ultragoal story G013-t1-materials-pivot-mt29 (the materials pivot after MT28's hull-margin wedge was KILLed).
**VERDICT: PASS** — entirely from Part B (stratified abstention interaction). Part A (rank reordering) is a
clean, decisive NULL. The surviving paper is the **chemistry/prototype-stratified abstention interaction**,
NOT the rank-reordering map.

## Data confirmed
WBM summary (256,963 rows, 0 hull nulls): `unique_prototype` (215,488 T / 41,475 F), `protostructure_spglib`,
`formula`, round-from-`material_id` (61,466 / 52,755 / 79,160 / 40,314 / 23,268). Predicted hull via MBD recipe
`e_above_hull_pred = e_above_hull_true + (e_form_pred − e_form_true_mp2020)`. Sanity: MACE F1 0.834 matches the
published leaderboard. Only the 4 modern UIPs (chgnet/m3gnet/mace/orb) have pred CSVs → rank map over n=4.

## Part A — rank-reordering map: NULL
- Leaderboard RIGID: orb(1) > mace(2) > chgnet(3) > m3gnet(4) in EVERY split (FULL / unique_prototype /
  rounds 1-5 / family binary/ternary/quaternary+), both F1 and DAF.
- **Kendall-τ full-vs-every-split = 1.0** (all 10 splits, both metrics); **zero CI-supported rank changes**
  (bootstrap rank CIs degenerate width-0). Meets the preregistered Part-A KILL exactly. With only 4
  well-separated UIPs there is no fragility to find → the rank-reordering deliverable is dead.

## Part B — stratified DAF under abstention: PASS
Confidence = `|predicted hull margin|` (the free MT28 baseline). Interaction = (precision/DAF gain from
tightening coverage 0.9→0.5) differenced BETWEEN strata, bootstrapped within strata (n_boot=1000).
- **Precision-gain interaction: 41/56 stratum-pair tests have 95% CI excluding 0.**
- **DAF-gain interaction: 13/16 tests exclude 0.** e.g. chgnet binary-vs-quaternary+ DAF-int +1.57 [1.37,1.79];
  m3gnet ternary-vs-quaternary+ +0.88 [0.81,0.95]; mace ternary-vs-quaternary+ +0.32 [0.24,0.39].
- unique_prototype axis interacts: mace T-vs-F precision-int −0.084 [−0.094,−0.073]; chgnet +0.068 [0.056,0.080].
- **Shuffle null is CLEAN** (kills the base-rate/ceiling-artifact objection): permuted-|margin| interaction ≈ 0
  (chgnet ternary-vs-quat+ REAL +0.093 [0.076,0.110] vs SHUFFLE +0.000 [−0.012,0.012]).
- Best-coverage policy differs by stratum for some cells (DAF-optimal coverage flips 0.5→0.7 for MACE on
  quaternary+ and ORB on rounds 2-3).

## Caveats / next step
- Interaction shown with the COARSE family proxy (# distinct elements). For a paper, re-run with genuine
  chemical-family / anion-class strata, AND fold MT28's matched-stable-call-yield control into the per-stratum
  DAF (else the yield confound returns) before any utility claim → Digital Discovery / NeurIPS D&B.

Files (research/results/MT29/): `mt29_stage0_result.json`, `mt29_partA_rank_reordering.json`,
`mt29_partB_strata_precision.json`, `mt29_partB_strata_daf.json`, plus reproduction scripts.
