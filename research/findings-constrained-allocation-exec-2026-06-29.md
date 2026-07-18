# Constrained optimal-allocation test (materials knapsack + climate hard-constrained equalizer)

**Date:** 2026-06-29 · **Combined verdict: FALSIFIED — no CI-excl-0 dominance over the equal-coverage/global baseline in either domain**

## Question
The "unified optimal allocation" seam claims a *resource-aware, stratified* selective-prediction allocator dominates naive equal-coverage/global abstention at matched budget. The naive spikes already failed (materials B5: 8/24 positive, intermetallics negative; climate B6: KILL, coverage constraint violated). This run tests whether a **properly constrained optimizer** rescues the claim. It does not.

## Materials — marginal-gain knapsack (B5b): FALSIFIED-NO-DOMINANCE
Script: `research/results/MT29/mt29_b5b_knapsack_constrained-exec-2026-06-29.py`
Result: `research/results/MT29/mt29_b5b_knapsack_constrained-exec-2026-06-29.json`
Data: n=256,963 cached WBM predictions; 6 strata (oxide 25020, intermetallic 119012, chalcogenide 23847, halide 26523, pnictide 34614, other 27947); keep-budget B at cov=0.7 = 179,874. 1000-boot + 1000 shuffle-null.

The knapsack allocates abstention budget only to strata with positive marginal DAF-gain — yet it is **worse than the global threshold** at matched coverage:

| UIP | mean-DAF global | knapsack | gain | weighted-mean gain |
|---|---|---|---|---|
| chgnet | 4.3709 | 3.9339 | **−0.4370** | −0.1155 |
| m3gnet | 3.4897 | 3.2136 | **−0.2761** | +0.1409 |
| mace | 5.5339 | 5.0959 | **−0.4379** | −0.2889 |
| orb | 5.6885 | 5.4879 | **−0.2006** | −0.1340 |

Cells: total=24, positive-excl0=**5**, negative-excl0=**14**, shuffle-excl0=0. Mean-DAF aggregate positive in **0/4** models. → A global threshold beats stratified allocation for MLIP stability prediction.

## Climate — coverage-hard-constrained equalizer (B6b): no significant dominance
Script: `research/b6b_hard_constrained_equalizer-exec-2026-06-29.py` (in climate-energy-research)
Result: `climate-energy-research/research/results/B6-GROUP-BALANCED/b6b_hard_constrained_equalizer-exec-2026-06-29.json`
IFS-ENS clean forward split (train 2018-2020 / test 2021-2022); coverage hard-pinned to exactly 0.80 (fixes the B6 violation); 500 event-blocked bootstrap reps.

| Threshold | SEDI forced→global→group | excess global | excess group | **group_adv (excl0?)** | verdict |
|---|---|---|---|---|---|
| p90 | 0.8681→0.9408→0.9403 | 0.0940 [0.0456,0.1483] | 0.0931 [0.0487,0.1409] | **+0.0009 [−0.0166,+0.0209] — NO** | (labeled GO, but adv CI⊃0) |
| p95 | 0.8598→0.9298→0.9318 | 0.0627 [0.0124,0.1406] | 0.0667 [0.0158,0.1486] | **−0.0040 [−0.0281,+0.0164] — NO** | KILL |

With coverage properly constrained, the equalizer **matches** the global allocator but its advantage CI **includes 0** at both thresholds. The script's "GO-DOMINANCE" label at p90 is driven by `group_wins` flag logic; the load-bearing `group_adv` is not CI-separated from zero.

## Conclusion & strategic implication
The central claim — a constrained stratified/equalized allocator CI-dominates equal-coverage/global at matched budget — is **falsified in both domains**:
- materials: constrained knapsack is strictly *worse* (negative gains, 14/24 cells negative);
- climate: hard-constrained equalizer is statistically *indistinguishable* from global (adv CI⊃0 at p90 and p95).

**Action (matches the scout's RISKY-fallback):** do NOT pursue the "unified optimal allocation" methodology paper. Ship the two **diagnostic** halves standalone instead — they are robust and essentially done:
- materials MT29 chemistry-stratified *value-of-abstention interaction* (the diagnostic, not the allocator);
- climate equity-of-abstention disparity (+ the SEDI-inflation note, see `climate-energy-research/research/findings-degradation-note-exec-2026-06-29.md`).

The negative allocation result is itself worth a sentence in each diagnostic paper: *stratified abstention reveals a reliability disparity, but reallocating the abstention budget along those strata does not improve aggregate decision value over a global threshold.*
