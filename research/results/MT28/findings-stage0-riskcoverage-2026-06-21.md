# MT28 risk-coverage Stage-0 gate — KILL (decisive negative) (2026-06-21)

Ultragoal story G003-t1-materials. **GATE VERDICT: KILL** of the "beat `|hull margin|`" wedge.
This is a clean, preregistered negative result, not a failure to run.

## What was tested
Risk-coverage / AURC selective-prediction audit of the WBM stability decision (`e_above_hull < 0`),
n=256,963, 4 UIPs (chgnet/m3gnet/mace/orb), seed 20260621, 1000 bootstrap. Candidate abstention signals:
`margin` (= |predicted hull margin|, the mandatory trivial baseline), `iso` (isotonic-calibrated p_stable),
`disagree` (ensemble disagreement). Two controls: **matched coverage** AND **matched stable-call yield**.

## Result — the matched-coverage gain is an artifact; matched-yield kills it
- At **matched coverage**, `iso` beats `margin` (AURC gains CI-excluding-0 for chgnet +0.094, m3gnet +0.145,
  mace +0.029). This looks like a win.
- But `iso` achieves it by calling **far fewer** structures stable (e.g. chgnet cov_50: 858 vs margin's 7,666).
  At **matched stable-call yield**, the precision gain flips negative (chgnet −0.145, m3gnet −0.236 at cov_50).
- Preregistered gate: PASS iff ≥1 (model,coverage,signal) beats `|hull margin|` at **both** matched coverage
  **and** matched yield with 95% CI excluding 0. **Passing cells: 0/12 → KILL.**
- `disagree` is worse than `margin` almost everywhere. Shuffle-null margin precision ≈ base rate (sanity OK).

## Interpretation
**`|predicted hull margin|` is sufficient** as the stability-decision abstention signal — "distance is all you
need" for this task. The aggressive MT28 wedge (a learned/calibrated signal beating hull-margin) is dead.
This is itself a citable result (pre-empts over-claims) but is NOT a standalone flagship.

## Pivot (per dossier §6 directions 2–3, which do NOT depend on beating hull-margin)
1. **MT29 rank-reordering map** — per-model rank displacement w/ bootstrap rank CIs across
   full / unique-prototype / chemistry-family / WBM-round splits (data-gate shown false; metadata present).
2. **Stratified discovery-acceleration under abstention** — DAF/precision-vs-coverage stratified by
   chemical family / `unique_prototype` / WBM round; report the stratum × coverage interaction.
Both reuse the same on-disk ~73 MB cached predictions. Materials continues on these, not on MT28's dead wedge.

Artifacts: `mt28_riskcov_result.json`, `mt28_riskcov_manifest.json`, `mt28_riskcov.py`.
