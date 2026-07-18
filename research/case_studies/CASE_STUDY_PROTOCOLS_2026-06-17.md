# Case-study protocols for scientific red-team closure — 2026-06-17

Purpose: turn the workspace's aggregate MLIP reliability results into concrete, falsifiable case studies while preserving the red-team verdict that the current manuscript is **not** publication-ready.

Scope: use cached Matbench Discovery / WBM predictions, existing local MD batch JSON, and lightweight CPU/GPU reruns only. No new DFT, no from-scratch UIP training, no discovery claims.

## CS1 — MT28 boundary false-positive rescue

- **Mechanism question:** Are there traceable WBM structures whose naive predicted-hull decision says “stable” but true hull says “unstable,” and does the calibration layer abstain exactly there?
- **Existing seed cases:** `research/redteam/decision_cases_mt28_2026-06-16.md` lists 8 cases: `wbm-1-28541`, `wbm-2-42208`, `wbm-4-2717`, `wbm-3-56893`, `wbm-1-8863`, `wbm-2-50987`, `wbm-4-30606`, `wbm-1-35204`.
- **Minimum table:** material_id, model, formula/chemsys if available, true hull, predicted hull, naive stable, true stable, calibrated P(stable), confidence, 4-UIP disagreement, boundary band.
- **Controls:** margin-only abstention; random abstention; no-abstention forced call; split seed sensitivity.
- **Kill threshold:** if selected cases are cherry-picked and population-level yield/recall accounting shows unacceptable true-stable loss, downgrade from “calibration helps decisions” to “calibration can reject selected boundary false positives.”
- **12GB feasibility:** CPU pandas/sklearn only; no model inference.
- **Deliverable:** `research/case_studies/MT28_boundary_false_positive_cases_YYYY-MM-DD.md` plus CSV/JSON and one compact boundary plot.

## CS2 — MT28 calibration-vs-margin protocol reconciliation

- **Mechanism question:** Is the precision lift due to real calibration information or a protocol artifact caused by inconsistent scripts/splits/calibrators?
- **Red-team trigger:** `research/results/MT28/mt28_calibration_result.json` and `research/results/mt_v28_calibration_results.json` disagree for M3GNet and MACE isotonic gains.
- **Minimum experiment:** one canonical script producing margin, logistic, isotonic, and optional conformal variants for the same calibration/eval split; report precision, recall, n_stable_called, coverage, CI, and seed distribution.
- **Controls:** shuffle labels; margin-only; random abstention; repeated seeds; fixed split manifest hash.
- **Kill threshold:** if reconciled canonical protocol does not beat margin with CI for any scientifically useful model/coverage, kill the MT28 calibration headline and preserve only boundary abstention/margin baseline.
- **12GB feasibility:** CPU pandas/sklearn; cached predictions only.
- **Deliverable:** canonical `research/results/MT28/mt28_canonical_calibration_YYYY-MM-DD.json` and a short case-study narrative explaining why previous files diverged.

## CS3 — Disagreement as abstention signal, not router

- **Mechanism question:** Does model disagreement mark where to abstain, while failing to identify which model to trust?
- **Existing evidence:** V6 disagreement/error correlation 0.7142; V6 70% precision gain CI [0.0312, 0.0349]; V6b routing MAE 0.0420 worse than ORB 0.0285.
- **Minimum table:** boundary band × disagreement quartile: precision, recall, false-stable rate, n called stable.
- **Controls:** shuffled disagreement; best-single ORB; ensemble mean; consensus-closest routing.
- **Kill threshold:** if disagreement adds no lift beyond margin at matched coverage, keep V6 only as regression-error diagnostic, not decision gate.
- **12GB feasibility:** CPU-only table analysis.
- **Deliverable:** `research/case_studies/V6_disagreement_abstain_not_route_YYYY-MM-DD.md`.

## CS4 — MT4 seeded MD energy-conservation offenders

- **Mechanism question:** Do direct-force predictions inject non-conservative work into NVE trajectories under controlled OOD perturbations compared with gradient-based controls?
- **Existing cases:** `Si_strain_0`, `Si_strain_1`, `Si_strain_2`, `Si_rattle_0`, `Fe_rattle_4` from `research/redteam/md_cases_from_batch_2026-06-16.md`.
- **Minimum rerun:** seed velocities; fixed ASE/timestep/thermostat-free NVE; rerun 3 high-ORB offenders and 2 conservative controls; record environment, model versions, GPU, seed, timestep, structure generation.
- **Controls:** MACE and CHGNet as gradient-based negative controls; timestep halving for integrator artifact check; one low-disagreement structure.
- **Kill threshold:** if ORB/MACE mean drift ratio drops below 5× under seeded/timestep-controlled rerun, kill the strong physical-consistency claim.
- **12GB feasibility:** existing 64-atom/100-structure data used <~0.7GB mean peak VRAM; selected rerun should fit 12GB.
- **Deliverable:** `research/case_studies/MT4_seeded_energy_conservation_cases_YYYY-MM-DD.md` and `research/figures/mt4_seeded_offenders_YYYY-MM-DD.png`.

## CS5 — MT29 leaderboard leakage: null result to escalation design

- **Mechanism question:** Do rankings change only under richer family/time/prototype controls, or is the leaderboard robust?
- **Existing result:** unique-prototype-only audit is a null: Kendall tau=1.0, Spearman=1.0, rank displacement 0.
- **Minimum escalation:** require metadata manifest with prototype/family/time split columns; rerun rank correlation and displacement CIs; explicitly report null if rankings remain stable.
- **Controls:** original full leaderboard; unique-prototype split; bootstrap metric noise; no-claim null.
- **Kill threshold:** kill MT29 positive headline if tau remains >0.9 and no model moves >1 rank with CI excluding 0 across richer splits.
- **12GB feasibility:** CPU-only once metadata exists.
- **Deliverable:** `research/case_studies/MT29_rank_fragility_escalation_YYYY-MM-DD.md`.

## CS6 — MT23 inverse-crime toy appendix

- **Mechanism question:** Can an optimizer exploit the same low-fidelity simulator used for evaluation?
- **Existing result:** low-res T=0.9994 at L=0.68 falls to high-res T=0.4528; gap 0.5466; high-res optimum shifts by 2 grid steps.
- **Controls:** high-res selection; optional second solver or second geometry; record resolution grid.
- **Kill threshold:** kill any broad photonics claim if the optimum is resolution-stable across higher-fidelity/cross-solver checks.
- **12GB feasibility:** CPU/small simulation; no MLIP resource issue.
- **Deliverable:** single-solver toy appendix only unless cross-solver validation is added.

## Required manuscript-safe case-study language

- “Benchmark case study,” not “new material discovery.”
- “Fixed-hull offline Matbench Discovery protocol,” not deployable screening unless a real predicted-hull workflow is added.
- “Split isotonic/logistic selective prediction,” not conformal, unless conformal scores and finite-sample coverage guarantees are implemented.
- “Selected MT4 offenders exceed 1000× drift; batch mean is ≈53× ORB/MACE,” not “mean 1000×.”
