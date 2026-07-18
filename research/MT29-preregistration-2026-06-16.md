# MT29 — Leaderboard rank fragility under prototype/family/time split (Stage-1 preregistration)

Date: 2026-06-16 · Workspace: `materials-mlip-research` · Status: **spec only, not run**.
Target venue: **Digital Discovery (RSC)** / **NeurIPS-ICLR Datasets & Benchmarks** — both explicitly accept
benchmark *audits* / stress-tests of prior evaluations, no new model.

## Wedge (why this clears the novelty bar)
Matbench Discovery **already** removes prototype leakage (11,175 MP→WBM matches; a "unique-prototype"
leaderboard of 215,488 structures) and notes metrics shift full-vs-dedup — so "we found leakage" is **known
and INCREMENTAL**. But the benchmark does **NOT** quantify rank *reordering* and **explicitly declines**
family-clustered / retrospective splits. Wedge = (a) **rank-fragility quantification** (Kendall-τ, bootstrap
rank CIs, per-model rank displacement) across leakage-stringency regimes, AND (b) the **family /
leave-one-element-out / time-like splits the authors declined**. Contribution is the *reordering map +
recommended split protocol*, not the existence of leakage.

## Preregistered question + falsifiable KILL
Are Matbench-Discovery model rankings stable after prototype-match / family / time-like filters, or are some
apparent gains driven by near-neighbor test-set structure?
- **KILL:** rankings are stable across all splits — Kendall-τ(full, leakage-controlled) > ~0.9 **and** no model
  moves > 1 rank with CI excluding 0. (A clean null is a reassuring but lower-impact result — report it honestly.)
- **KILL (data):** published per-model predictions / prototype metadata cannot support a clean split.

## Method / MPU
- **12–15** leaderboard models with public predictions (the benchmark hosts them).
- Splits: full WBM; unique-prototype; stricter near-neighbor dedup; **leave-one-element / family heldout**;
  **time-like** via WBM's 5 substitution generations; sAlex-leakage stratification.
- Compute family/prototype similarity from MP + Alexandria prototype labels (CPU, pandas).
- Output: rank-stability table with bootstrap rank CIs + per-model displacement under each split.

## Metrics
Kendall-τ / Spearman between rankings; per-model rank displacement (with bootstrap CIs); metric-delta by split;
density-vs-error correlation (does training-neighbor density predict per-family error inflation?).

## Adversarial stress test
- **Top reviewer kill:** "leakage is already known and handled." → Mitigation: the deliverable is *rank
  reordering* + the *declined* family/time splits, explicitly positioned against Riebesell 2025's dedup.
- **Boundary discipline:** report "rank fragility under split choice"; do **NOT** accuse any model of leakage
  without exact prototype-match evidence (matches the workspace's own card boundary note + Kapoor-Narayanan
  *Patterns* 2023 leakage-taxonomy framing).
- **Concurrent threat:** OMat24 documents the Alexandria↔WBM prototype overlap but does no rank audit — cite,
  don't be scooped by.

## Go/no-go spike (cheap, CPU, run before Stage-0)
Pull the leaderboard predictions; compute Kendall-τ between the **full** and **unique-prototype** rankings (the
benchmark already provides both numbers). If τ already shows material reordering → green. If τ≈1 → the story
*requires* the harder family/time splits to survive; decide whether to invest in those before committing.

## Boundaries
Benchmark-audit only; no materials-discovery and no leakage *accusation* without exact evidence. CPU-light;
published predictions + metadata; no UIP training, no DFT, no GPU run.

## Publication readiness capsule (pre-experiment gate)

- **Primary target / fallback:** Digital Discovery (primary) / NeurIPS or ICLR Datasets & Benchmarks-style evaluation track (fallback if packaged as reusable benchmark audit).
- **Exact rescued title:** *Hull-boundary abstention and rank fragility in universal interatomic-potential discovery benchmarks* — MT29 slice: *Rank fragility under prototype, family, and time-like splits*.
- **Preregistered question:** Do model rankings remain stable when Matbench Discovery-style metrics are recomputed under stricter prototype/family/time-like filters?
- **Minimum Stage-0 evidence:** rank table for at least full vs unique-prototype split; Kendall/Spearman correlation; per-model displacement with bootstrap CI; one sanity plot/table showing whether a model moves more than one rank.
- **Trivial baseline / null controls:** published full leaderboard; published deduplicated leaderboard; random split resampling; metric-only rank recomputation without new filtering.
- **Kill thresholds:** kill the rank-fragility headline if Kendall-τ remains >0.9 across all honest filters and no model moves by >1 rank with CI excluding 0; downgrade to a reassuring null audit if metadata support is clean.
- **Leakage / circularity controls:** distinguish prototype overlap from accusation; predefine split order before inspecting rank changes; keep any family/time-like split construction separate from model choice.
- **Data / resource gates:** public prediction tables and prototype/family/time-like metadata must be small-table accessible; no model inference, DFT, or GPU; stop if only aggregate leaderboard scores are available.
- **Next files to update:** `materials-mlip-research/research/materials-mlip-direction-bank.md`; MT28 shared title/abstract stub; consolidated readiness summary.

