# Generational reliability drift on Matbench-Discovery WBM — cross-gen calibration table

**Date:** 2026-06-29 · **Status:** SHIPPABLE · **Directional hypothesis ("newer UIPs calibrate worse"): REFUTED**

## What was run
First cross-**generational** reliability table on Matbench-Discovery WBM (n=256,963; 256,961 for CGCNN variants), both MLIP generations on ONE protocol:
- **2020-era:** CGCNN (ens=10), CGCNN+P, MEGNet, ALIGNN-FF
- **2023-24:** CHGNet, M3GNet, MACE, ORB

Axes: MAE, F1 (full set, reproduces V2 exactly), AURC (margin, test half), and ECE/Brier/NLL via a **zero-free-parameter native Gaussian error model** `p_stable = Phi(-hull_pred/sigma)`, `sigma = RMSE(err)` fit on cal half, scored on test half; secondary Platt logistic. 1000-boot 95% CIs + 200× shuffle null.

**Validation:** MAE/F1 match V2 to 4dp (ORB 0.0285/0.8596, CHGNet 0.0611/0.6099); CHGNet margin-AURC 0.2023 vs prior 0.2019.

Script: `research/results/MT29/mt29_crossgen_reliability_exec_2026_06_29.py`
Result: `research/results/MT29/mt29_crossgen_reliability_result-exec-2026-06-29.json`
Manifest: `research/results/MT29/mt29_crossgen_reliability_manifest-exec-2026-06-29.json`
Run: `CUDA_VISIBLE_DEVICES='' conda run -n dl python3 ...` (CPU only, no GPU).

## Cross-gen table

| Model | Gen | MAE | F1 | AURC | ECE_nat | Brier_nat | NLL_nat |
|---|---|---|---|---|---|---|---|
| ORB | 2023-24 | 0.0285 | 0.8596 | 0.0283 | 0.1182 | 0.0681 | 0.2478 |
| MACE | 2023-24 | 0.0292 | 0.8339 | 0.0534 | 0.1320 | 0.0735 | 0.2599 |
| CHGNet | 2023-24 | 0.0611 | 0.6099 | 0.2023 | 0.1568 | 0.1238 | 0.4064 |
| M3GNet | 2023-24 | 0.0726 | 0.5734 | 0.3276 | 0.2022 | 0.1477 | 0.4654 |
| CGCNN+P | 2020 | 0.1083 | 0.5083 | 0.4548 | 0.2077 | 0.1665 | 0.5134 |
| MEGNet | 2020 | 0.1282 | 0.5105 | 0.4790 | 0.1576 | 0.1494 | 0.4781 |
| CGCNN | 2020 | 0.1350 | 0.5089 | 0.3817 | 0.1620 | 0.1480 | 0.4665 |
| ALIGNN-FF | 2020 | 0.1404 | 0.4914 | 0.5840 | 0.2678 | 0.2016 | 0.6379 |

**Gen means (2020 vs 2023-24):** MAE 0.1280 vs 0.0479; AURC 0.4749 vs 0.1529; ECE_nat 0.1988 vs 0.1523; Brier_nat 0.1664 vs 0.1033; NLL_nat 0.5240 vs 0.3449; ECE_platt 0.0528 vs 0.0402; Brier_platt 0.1193 vs 0.0693.

2023-24 is better on **every** axis. Reliability tracks accuracy (extends V2 Spearman(MAE,F1)=−0.93 to calibration). All 8 models' native Brier sits below the 5th pctile of the label-permuted null (confidence informative for both generations).

**Spearman over 8 models:** MAE-vs-Brier +0.905 (p=0.0020), MAE-vs-NLL +0.905 (p=0.0020), MAE-vs-AURC +0.929 (p=0.0009), F1-vs-Brier −0.976 (p=3e-5), F1-vs-AURC −0.929 (p=0.0009), MAE-vs-ECE +0.810 (p=0.0149).
**Example 95% boot CIs (CHGNet):** ECE_nat [0.1551,0.1586], Brier_nat [0.1230,0.1246], AURC [0.1972,0.2070]. Shuffle null e.g. CHGNet Brier 0.124 vs null-mean 0.223.

## Honest nuances
1. **ECE is the noisiest axis and partially DECOUPLES from accuracy** (MAE-vs-ECE rho=+0.81 is the weakest correlation; MEGNet/CGCNN 2020 ECE 0.158/0.162 rival CHGNet 2023 0.157) — a humble, inaccurate model with wide Gaussian sigma can be well-calibrated while a poor discriminator. Calibration ≠ accuracy.
2. **Lead with proper scoring rules Brier/NLL (and AURC)**, which separate the generations cleanly; do not headline ECE.
3. **Platt recalibration collapses ECE for both gens** (0.053 vs 0.040) → the story lives on the native axis; sharpness (Brier_platt 0.119 vs 0.069) stays gen-separated and is irreducible by post-hoc scaling.
4. **"Modern" isn't monolithic:** ~2× Brier spread inside the 2023-24 cohort (ORB/MACE vs CHGNet/M3GNet) = the V2 triangle.

## Defensible novelty
The **measurement**: ECE/Brier/NLL of the stability call is a distinct reliability axis nobody had measured cross-generationally on WBM. Frame as a confirm-or-refute measurement (it refuted "newer-worse"), positioned as a guardrail/supporting study to the MT29 flagship — not a second flagship.

## Optional next steps
(a) reliability + risk-coverage curve PNGs for the 8 models; (b) per-sample native ensemble sigma for CGCNN/CGCNN+P as a robustness check (won't change direction); (c) ECE bin-count sensitivity (10/15/20).
