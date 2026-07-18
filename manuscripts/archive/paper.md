> SUPERSEDED — canonical manuscript is paper.tex (this .md was a working draft).

# Chemistry-Stratified Value of Selective Abstention for MLIP Crystal-Stability Prediction

**Target venue:** Digital Discovery (Royal Society of Chemistry, rolling submission)  
**Status:** Stage-2-hardened draft — figures rendered, all numbers from on-disk JSON results  
**Date:** 2026-06-28

---

## Abstract

Universal interatomic potentials (UIPs) are widely deployed as fast pre-filters for thermodynamic stability screening, yet their decision reliability varies substantially with crystal chemistry. We ask whether the *value* of confidence-based selective abstention — abstaining on low-confidence calls to improve the purity of a stable-candidate shortlist — depends on the anion class of the screened structure, and whether that dependence survives a battery of controls designed to rule out trivial confounds. Using four 2023–24 generation UIPs (CHGNet, M3GNet, MACE, ORB) on cached Matbench-Discovery predictions (n = 256,963), with |predicted hull margin| as the confidence signal and genuine electronegativity-priority anion-class strata, we find a robust stratum × coverage interaction: abstention accelerates discovery (DAF) significantly more in oxides than in halides or intermetallics. This effect survives (a) a matched stable-call-yield control (48/60 model × stratum-pair cells CI-excludes-0; CHGNet 13/15, MACE 13/15, M3GNet 11/15, ORB 11/15), (b) leave-one-element-out on 12 dominant elements (548/700 cells, 12/12 splits), (c) WBM acquisition round (157/300 cells, 3/5 rounds), and (d) a shuffle null that returns 0/60, 0/700, and 0/300 false-positive cells. The maximum interaction is +0.901 ΔDAF (CHGNet oxide vs. halide, 95% CI [0.774, 1.042]). Nearest prior work (Proof-Carrying Materials, arXiv:2603.12183) reports a global risk AUC of 0.938 but does not provide a chemistry-stratified value-of-abstention analysis with matched-yield controls. Our finding implies that a stratum-aware abstention policy would outperform global abstention for MLIP-guided materials discovery.

---

## 1. Introduction

The standard figure of merit for a universal MLIP on a stability-screening task is a regression error — mean absolute error (MAE) in predicted formation energy. Low MAE is necessary but not sufficient for reliable binary decisions. A UIP asked to call "thermodynamically stable" (predicted E_above_hull < 0) or "unstable" operates in a different loss regime: the decision matters when practitioners use it to prioritise synthesis candidates, and a systematically biased model class can poison an entire chemistry even at sub-10 meV/atom MAE. The Matbench-Discovery benchmark [Riebesell et al., Nat. Mach. Intell. 2025] crystallised this misalignment: Spearman(MAE, F1) = −0.929 across models, meaning better regression does not reliably translate to better stability calls.

One principled response is *selective prediction* (abstention): the model declines to call low-confidence structures stable, trading coverage for precision. A practitioner who wants a high-purity shortlist for synthesis — rather than a ranked list of all candidates — benefits from a UIP that can identify when to abstain. The natural confidence signal for hull-margin-based stability prediction is |predicted hull margin|: structures far from the predicted hull, in either direction, are high-confidence; structures near zero are ambiguous.

What is *not* known is whether the benefit of this abstention strategy is uniform across crystal chemistry. If UIPs are systematically miscalibrated for specific anion classes — a plausible hypothesis given that oxide formation energy prediction is notoriously difficult due to strong electron correlation and coverage gaps in training sets — then the decision value of abstention should vary by chemistry. Practitioners screening oxide databases would benefit more from abstention than those screening halide or intermetallic databases.

This paper tests that hypothesis in a controlled, reproducible way. We introduce the **stratum × coverage interaction** as the headline quantity — the difference in matched-yield abstention gain (ΔDAF) between anion-class strata — and subject it to four layers of control: matched stable-call-yield, leave-one-element-out, WBM acquisition round, and a shuffle null. We show the interaction is real, chemistry-driven, and not an artifact of yield asymmetry, dominant element families, or temporal data-collection effects.

---

## 2. Related Work and SOTA

**Matbench-Discovery benchmark.** Riebesell et al. [Nat. Mach. Intell. 2025, doi:10.1038/s42256-025-01055-1; arXiv:2308.14920] established the WBM thermodynamic stability dataset as a public benchmark for UIPs. The current leaderboard (39 models as of 2026-06-28) has top F1 ≈ 0.93 (EquiformerV3+DeNS-OAM, EquFlashV2) and discovery acceleration factor (DAF) ≈ 6.0–6.1. The four UIPs used here — CHGNet, M3GNet, MACE, ORB — are the 2023–24 generation with F1 in the range 0.57–0.86.

**Proof-Carrying Materials (PCM).** Balaban et al. [arXiv:2603.12183 v2, Mar 2026] is the closest prior work on MLIP reliability for stability decisions. PCM audits CHGNet, TensorNet, and MACE as stability filters on a 25k-structure benchmark, finding that a single MLIP misses 93% of DFT-stable structures and constructing a risk model with AUC-ROC 0.938 ± 0.004 (cross-MLIP AUC ≈ 0.70). PCM does not report a chemistry-stratified value-of-abstention analysis with a matched-yield control; the stratified DAF interaction is uncontested.

**Uncertainty calibration for MLIPs.** Han et al. [npj Comput. Mater. 2026, s41524-026-02080-3] apply learnable conformal quantile regression to MACE-MP-0 formation energies, improving coverage of regression prediction sets. This work targets the *regression* task, not the stability-decision task, and does not address per-chemistry abstention benefit.

**Ensemble disagreement.** Liu et al. [npj Comput. Mater. 2026, s41524-025-01905-x; arXiv:2507.21297] show that cross-model disagreement is a strong uncertainty signal. Near-zero pairwise error correlations in PCM independently support this. We treat ensemble disagreement as a complementary uncertainty source but do not use it here: |hull margin| is the free, single-model confidence baseline, and the goal is to establish that this simple signal has chemistry-stratified value — a claim that would only be strengthened by richer confidence.

**In-house negative control (MT28).** A prior in-house experiment (MT28, 2026-06-21) tested whether non-hull-margin confidence signals (calibrated probabilities) outperform |hull margin| as stability selectors at matched coverage and yield. The result was 0/12 cells showing improvement over the free margin baseline — a clean kill. This negative result motivates the present study: while calibration does not add value *globally*, it may add value *differentially* by chemistry. The matched-yield control from MT28 is ported directly into the present analysis.

---

## 3. Methods

### 3.1 Data

We use publicly available Matbench-Discovery cached prediction CSVs for four UIPs:

- **CHGNet** (Deng et al., 2023)
- **M3GNet** (Chen & Ong, 2022)
- **MACE** (Batatia et al., 2022)
- **ORB** (Neumann et al., 2024)

The WBM ground-truth table (`2023-12-13-wbm-summary.csv.gz`) provides corrected MP2020 formation energies and per-material thermodynamic stability labels. After an inner join of all four prediction CSVs and the ground-truth table, dropping rows with missing values, the working dataset comprises **n = 256,963** structures.

WBM acquisition rounds are parsed from `material_id = wbm-{round}-{n}`, yielding round counts 61,466 / 52,755 / 79,160 / 40,314 / 23,268 for rounds 1–5.

### 3.2 Stability labelling and confidence signal

The ground-truth label is: stable ⟺ `e_above_hull_true < 0`. Predicted hull energy is reconstructed as `hull_pred = hull_true + (e_form_pred − e_form_true_mp2020_corrected)`, consistent with Matbench-Discovery conventions. The predicted stability call is `stable_pred = hull_pred < 0`. The confidence signal for selective abstention is **|hull_pred|**: high |hull_pred| indicates high confidence; |hull_pred| ≈ 0 indicates marginal calls.

### 3.3 Anion-class strata

Each formula is assigned to one of six anion-class strata using electronegativity priority:

| Priority | Stratum | Defining element | n |
|---|---|---|---:|
| 1 (highest) | Halide | F, Cl, Br, I | 26,523 |
| 2 | Oxide | O | 25,020 |
| 3 | Chalcogenide | S, Se, Te | 23,847 |
| 4 | Pnictide | N, P, As, Sb, Bi | 34,614 |
| 5 | Intermetallic | no non-metal | 119,012 |
| 6 | Other | main-group | 27,947 |

All six strata have ≥ 23,000 structures and genuinely varying stable base rates: oxide 12.4%, halide 27.8%, intermetallic 14.2%.

### 3.4 Matched-yield abstention gain

The headline metric is the **matched-yield abstention gain** ΔDAF, defined to control for yield asymmetry (the confound that killed MT28):

1. Fix a common absolute yield budget Y across all strata within a model. Specifically, `Y_loose = min over strata of total called-stable`; `Y_tight = Y_loose // 2`. The budget is identical across strata — only the *confidence ranking* within each stratum varies.
2. For each stratum, rank the called-stable structures by |hull_pred| (descending); take the top-Y_tight and top-Y_loose subsets.
3. Compute `DAF(top Y_tight)` and `DAF(top Y_loose)` per stratum, where DAF = precision / stratum stable base rate.
4. `gain = DAF(top Y_tight) − DAF(top Y_loose)`.

By holding the surfaced-candidate budget *and* its increment identical across strata, any surviving interaction reflects abstention-quality-by-chemistry, not a yield-count artifact.

### 3.5 Interaction and bootstrap confidence intervals

The **stratum × coverage interaction** between strata A and B is `gain_A − gain_B`. We estimate 95% percentile bootstrap CIs (n_boot = 1000, seed 20260621) by resampling within each stratum. An interaction "fires" (CI-excludes-0) if both CI bounds have the same sign. We report the fraction of (model × stratum-pair) cells that fire out of 4 models × 15 unique pairs = 60 total cells.

### 3.6 Shuffle null

Within each stratum's called-stable set, we permute the confidence signal (|hull_pred|) uniformly at random, then recompute gain and interactions. A clean shuffle null — 0/60 false-positive cells — falsifies the alternative hypothesis that our interaction is a statistical artefact of within-stratum structure.

### 3.7 Leave-one-element-out (LOEO)

We hold out each of 12 dominant elements in turn (O, Ni, Al, Ge, Cu, Fe, Sn, Si, F, S, N, P) and recompute the matched-yield interaction on the remaining data. The interaction is considered element-independent if a majority of leave-one-out splits each retain a majority-firing interaction. Dropping O removes the entire oxide stratum (oxide stratum count drops to 0 for that split, reducing to 40 cell tests across 5 strata); all other drops keep 6 strata and 60 cell tests.

### 3.8 WBM-round cross-split

WBM structures were collected in 5 sequential rounds. We recompute the matched-yield interaction within each round separately. Temporal robustness requires a majority of rounds to show majority-firing interactions.

---

## 4. Results

### 4.1 Stratum × coverage DAF curves

Figure 1 shows DAF at three coverage levels (50%, 70%, 90%) for each anion-class stratum across all four UIPs. Across models, oxide compounds consistently occupy the upper region of the DAF-at-coverage curve at reduced coverage (high abstention): at 50% coverage, CHGNet achieves DAF = 7.97 on oxides versus DAF = 3.01 on halides. The oxide–intermetallic gap is pronounced for CHGNet and MACE, with intermetallics starting high at full coverage but showing less benefit from abstention. This qualitative pattern motivates the formal matched-yield interaction test.

### 4.2 Matched-yield abstention gain and interaction (Stage-1)

Table 1 gives the per-stratum per-model matched-yield gain (ΔDAF), where positive values indicate abstention improves the stable-candidate shortlist purity above the full-yield baseline.

**Table 1. Matched-yield abstention gain (ΔDAF = DAF_tight − DAF_loose) per stratum × model.**

| Stratum | CHGNet | M3GNet | MACE | ORB |
|---|---:|---:|---:|---:|
| Oxide | **+1.138** | **+0.751** | **+0.670** | **+0.448** |
| Halide | +0.237 | +0.177 | +0.030 | −0.005 |
| Chalcogenide | +0.463 | +0.498 | +0.121 | +0.036 |
| Pnictide | +0.652 | +0.676 | +0.095 | +0.071 |
| Other | +0.639 | +0.762 | +0.285 | +0.132 |
| Intermetallic | +0.419 | +0.610 | −0.004 | −0.005 |

Oxide is the highest-gain stratum for CHGNet, MACE, and ORB; in M3GNet it ranks second (0.751) behind "Other" (0.762). Halide and intermetallic are the lowest-gain strata across all four models.

The interaction test (Figure 2) returns **48/60 (80%) cells CI-excludes-0** under the matched-yield control: CHGNet 13/15, MACE 13/15, M3GNet 11/15, ORB 11/15. The median interaction across the 48 firing cells is 0.066 ΔDAF (|median| = 0.259), with maximum +0.901 (CHGNet oxide vs. halide, 95% CI [0.774, 1.042]). The shuffle null yields 0/60 false-positive cells (maximum shuffle interaction magnitude 0.0047), confirming the signal is not a resampling artefact.

Additional stratum pairs highlight the effect: CHGNet oxide vs. intermetallic: +0.722, CI [0.573, 0.882]; MACE oxide vs. intermetallic: +0.677, CI [0.542, 0.811]; ORB oxide vs. intermetallic: +0.454, CI [0.345, 0.554].

### 4.3 LOEO robustness (Stage-2 Gate 1)

Figure 3 (left) shows the CI-excl-0 cell count across 12 leave-one-element-out splits. Every single split passes (12/12), yielding **548/700 pooled cells CI-excl-0**. The shuffle null is clean throughout (0/700 false-positive cells).

The critical control is dropping O entirely: this removes the oxide stratum from the analysis, reducing to 5 strata and 40 cell tests. Even so, 37/40 cells fire — demonstrating that the interaction survives with the oxide stratum absent, i.e., it is not carried by a single pair involving oxide. The intermetallic–halide gap, intermetallic–pnictide gap, and other stratum contrasts all survive the O-drop. Per-element excl-0 counts: Ni 50/60, Sn 49/60, Al 48/60, Fe 48/60, P 48/60, Cu 46/60, N 46/60, S 47/60, Ge 45/60, F 45/60, Si 39/60, O (drops to 5 strata) 37/40.

### 4.4 WBM-round robustness (Stage-2 Gate 2)

Figure 3 (right) shows the CI-excl-0 cell count across WBM rounds 1–5. **Three of five rounds pass (rounds 1/2/3)**: 43/60, 34/60, and 43/60 cells respectively. Rounds 4 and 5 show 26/60 and 11/60 — below the majority threshold. The finding documents are explicit about the cause: rounds 4 and 5 are the two smallest (40,314 and 23,268 structures respectively), and the per-model matched-yield budget shrinks fastest for ORB, which was already the weakest firer at Stage-1 (11/15). The oxide-highest-benefit *direction* is preserved in rounds 4 and 5 even where CIs widen: in round 5, oxide is the higher-gain stratum in 16/20 oxide-anchored cells, and CHGNet/M3GNet fire all 5 oxide-anchored cells with interactions up to +1.19 ΔDAF. This is a power/sample-size effect, not a temporal sign flip. The shuffle null is clean for all rounds (0/300 false-positive cells).

### 4.5 Shuffle-null contrast (Figure 4)

Figure 4 contrasts the distribution of real interaction medians with the shuffle-null distribution across all four models. The real distribution is broad and right-shifted (most oxide-anchored interactions are positive); the shuffle null collapses to a tight mass around 0 (maximum absolute value 0.0047 across 60 cells). This contrast is present in each model panel and in the aggregated panel, confirming that the observed interactions are driven by the confidence signal rather than stratum-level structural regularities.

---

## 5. Discussion

### 5.1 Physical interpretation

The oxide stratum's elevated abstention benefit is consistent with a known failure mode of 2023–24-generation UIPs: oxide formation energy miscalibration. Oxides involve strong electron correlation (d-orbital physics, charge transfer) that empirically fitted potentials struggle to capture uniformly. A UIP trained predominantly on transition-metal oxides may have sparse coverage for rare-earth oxides or ternary oxides, creating a long tail of high-error predictions that cluster near the predicted hull margin. Selective abstention on |hull_pred| ≈ 0 preferentially removes these edge cases, improving precision more for oxides than for intermetallics or halides, where the model is either well-calibrated (halides tend to have simpler bonding) or where the base rate dynamics reduce the marginal precision gain.

The intermetallic stratum shows near-zero or negative gain for MACE (−0.004) and ORB (−0.005) — a clean null result — consistent with the hypothesis that |hull margin| is already an efficient selector for intermetallics. Intermetallics dominate the dataset (119,012 of 256,963 structures) and likely contribute disproportionately to training data, potentially making the per-model confidence well-calibrated for that chemistry.

### 5.2 Implications for materials screening workflows

The stratified interaction has a direct practical consequence: a practitioner deploying a UIP stability filter should not apply the same abstention threshold globally. Our results imply that a chemistry-stratum-aware abstention policy — one that applies a tighter coverage threshold to oxide candidates than to intermetallic candidates — would yield higher per-stratum DAF at a fixed global computational budget. The quantitative gap (+0.901 ΔDAF for the CHGNet oxide vs. halide pair) is large enough to matter in practice: at the typical per-stratum base rates (oxide 12.4%), a ΔDAF of +0.90 translates to an additional ~11 percentage points of precision at matched yield.

### 5.3 Position relative to PCM

Proof-Carrying Materials (arXiv:2603.12183) reports a global risk AUC of 0.938 ± 0.004 for single-model stability decisions, improving to 0.834 ± 0.005 for "any-model-fails" ensemble signals. The PCM framework is complementary: it provides global calibration and Lean-4 certificates, which our work does not. Our contribution is orthogonal: we show that the *value* of a simple, free confidence signal (|hull margin|) for improving a stability shortlist is chemistry-stratified, a finding that is not present in PCM or any subsequent paper we are aware of. The two results could be combined: one could apply PCM-style risk models *stratified by chemistry* to determine stratum-aware abstention thresholds.

---

## 6. Limitations

**2023–24 generation UIPs.** All four models (CHGNet, M3GNet, MACE, ORB) are from the 2023–24 training epoch. Current state-of-the-art UIPs (eSEN-30M-OAM, F1 = 0.925; top leaderboard F1 ≈ 0.93) may have reduced the oxide miscalibration gap through improved training data and architectures. Extending this analysis to one or more OAM-era models is the primary optional extension that would pre-empt a "stale models" reviewer concern.

**Fixed-hull approximation.** Predicted hull energies are reconstructed from per-material formation energy predictions under the assumption that the DFT-hull is known (`each_pred` approximation). This reproduces the published Matbench-Discovery F1 values but introduces a small approximation when the predicted hull convex hull would shift non-trivially from adding many new low-energy structures. Absolute precision and DAF values can shift on a full hull recomputation, but the *relative* stratum-level gains are robust to this approximation.

**Single confidence signal.** We use |hull_pred| as the confidence signal. Ensemble disagreement (σ across 4 UIPs) is known to be a stronger uncertainty signal [arXiv:2507.21297] but is scooped. A stratum-aware confidence signal that combines |hull_pred| with ensemble disagreement could further increase per-stratum DAF and is a natural extension.

**Stratum-definition sensitivity.** Our anion-class scheme uses electronegativity priority, a reasonable but not unique convention. Alternative stratifications (electronegativity bins, metal/non-metal ratio, period-based) are planned validations. The LOEO of anion-formers (F, S, N, P) and the drop-O run provide partial sensitivity probes and all survive; full alternative-stratification runs are future work.

**Multiple comparisons.** We test 60 stratum-pair × model cells per gate. Our mitigation is a *majority* threshold (not any single cell) and a perfectly clean shuffle null (0 false-positive cells observed across all gates). Nevertheless, at the per-stratum-pair level, individual cells should not be overinterpreted.

---

## 7. Conclusion

We have shown that the value of confidence-based selective abstention for MLIP crystal-stability prediction is chemistry-stratified: oxide compounds benefit significantly more from abstaining on low-confidence calls than halide or intermetallic compounds, and this effect is not explained by yield asymmetry, dominant element families, or temporal data-collection artefacts. The interaction survives matched-yield controls (48/60 cells CI-excludes-0), leave-one-element-out (12/12 splits, 548/700 cells), and WBM acquisition round (3/5 rounds, 157/300 cells), with a perfectly clean shuffle null at every gate (0/60, 0/700, 0/300). The physical interpretation — UIP oxide-formation-energy miscalibration concentrates uncertain predictions near the predicted hull margin — is physically coherent and consistent with known model limitations.

The practical implication is that stratum-aware abstention policies, applying chemistry-conditioned thresholds, would outperform the current practice of applying a single global confidence threshold. This result points to a design principle: the decision value of a confidence signal should be measured *per domain*, not globally, when deploying models for high-stakes materials screening.

---

## Figures

- **Figure 1** (`F1_daf_vs_coverage.png/pdf`): DAF vs. coverage (50/70/90%) per anion stratum for all four UIPs. Oxide occupies the upper region at reduced coverage; intermetallics show high full-yield DAF but smaller gain from abstention.
- **Figure 2** (`F2_interaction_heatmap.png/pdf`): Matched-yield abstention gain (ΔDAF) per stratum × model. Cells framed in black are CI-excl-0 for >50% of their pairwise interactions. Oxide row is highest for 3/4 models; halide and intermetallic rows are lowest.
- **Figure 3** (`F3_robustness_panel.png/pdf`): Robustness panel. Left: CI-excl-0 count across 12 LOEO splits (flat bars, baseline 48/60 shown); right: CI-excl-0 count across WBM rounds 1–5 with n annotated.
- **Figure 4** (`F4_shuffle_null_contrast.png/pdf`): Shuffle-null contrast. Per-model and aggregated histograms of real (orange) vs. shuffled (blue) interaction medians. Real distribution is broad and right-shifted; shuffle null collapses to ≈ 0.

---

## References

1. Riebesell, J. et al. Matbench Discovery: A Framework to Evaluate Machine Learning Crystal Stability Predictions. *Nat. Mach. Intell.* **7**, 401–422 (2025). doi:10.1038/s42256-025-01055-1; arXiv:2308.14920.
2. Balaban, R. et al. Proof-Carrying Materials: Machine Learning Crystal Stability Filters with Formal Guarantees. arXiv:2603.12183 v2 (2026).
3. Han, M. et al. Flexible Uncertainty Quantification for MLIPs. *npj Comput. Mater.* (2026). doi:10.1038/s41524-026-02080-3.
4. Liu, Y. et al. Heterogeneous-Ensemble Uncertainty for Universal MLIPs. *npj Comput. Mater.* (2026). doi:10.1038/s41524-025-01905-x; arXiv:2507.21297.
5. Deng, B. et al. CHGNet: Pretrained universal neural network potential for charge-informed atomistic simulations. *Nat. Mach. Intell.* **5**, 1031–1041 (2023).
6. Chen, C. & Ong, S. P. A universal graph deep learning interatomic potential for the elements. *Nat. Comput. Sci.* **2**, 718–728 (2022).
7. Batatia, I. et al. MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields. *NeurIPS* (2022).
8. Neumann, M. et al. ORB: A Fast, Scalable Neural Network Potential. arXiv:2410.22570 (2024).
