# V2 — does MT1's "triangle of peril" hold for modern UIPs? NO — it was a weak-model artifact (MT1 REVISED)

Date: 2026-06-15 · Compute: `dl4080` graph env (pandas+sklearn, CPU). Data: Matbench Discovery WBM
(registration-free): true e_form + e_above_hull (summary) + 4 modern UIPs (MACE-mpa-0, CHGNet-0.3.0,
M3GNet, ORB-v2; geo-opt preds from Figshare, parsed to compact CSVs) + 4 2020 anchors (CGCNN, CGCNN+P,
MEGNet, ALIGNN-FF; repo CSVs). Script: `mt_v2_modern_uip.py` · Raw: `results/MT_V2/`.

## Why
MT1 (`findings-MT1-MT2-triangle-of-peril.md`) reported a "triangle of peril": CGCNN+P had **lower** formation
MAE than CGCNN yet **worse** stability classification (FPR 0.197 vs 0.148) — "low regression error ≠ reliable
stability decision." But MT1 used only **2020-era** models. The audit (and a reviewer) demands: **does this
hold for 2024 SOTA universal potentials, or do they close the gap?** V2 answers it.

## Result — full spectrum (sorted by formation-energy MAE)

| model (year) | MAE_form (eV) | stability F1 | FPR | abstain-prec@0.05 |
|---|--:|--:|--:|--:|
| ORB-v2 (2024) | **0.029** | **0.860** | 0.018 | 0.97 |
| MACE-mpa-0 (2024) | 0.029 | 0.834 | 0.035 | 0.95 |
| CHGNet 0.3 (2023) | 0.061 | 0.610 | 0.141 | 0.78 |
| M3GNet (2022) | 0.073 | 0.573 | 0.202 | 0.67 |
| CGCNN+P (2020) | 0.108 | 0.508 | 0.197 | 0.58 |
| MEGNet (2020) | 0.128 | 0.511 | 0.138 | 0.50 |
| CGCNN (2020) | 0.135 | 0.509 | 0.148 | 0.59 |
| ALIGNN-FF (2020) | 0.140 | 0.491 | 0.240 | 0.40 |

**Spearman(MAE, F1) = −0.93** (n=8) → strongly monotone: **lower MAE predicts better stability classification
across the spectrum.** Best-MAE model (ORB) is also best-F1. → `triangle_persists = False`.

## Adjudication — MT1's headline claim must be SCOPED (honest partial refutation)
1. **The "triangle of peril" does NOT hold across the model spectrum.** For 2024 SOTA UIPs (MACE/ORB),
   low MAE (~0.029) comes WITH excellent stability decisions (F1 0.83–0.86, FPR 0.018–0.035). Regression
   accuracy and decision reliability are **aligned** for modern models.
2. **The MT1 mismatch was a *within-weak-models* artifact.** The 2020 GNN energy models all cluster near
   chance (F1 ≈ 0.49–0.51, MAE 0.11–0.14) — in that regime, where prediction error ≈ the hull-margin scale,
   MAE-rank and F1-rank decouple (the CGCNN-vs-CGCNN+P inversion). That decoupling is real but **local to the
   weak/comparable-error regime**, NOT a general law. → MT1's claim must be restated as: *"when energy-error is
   comparable to the hull-decision margin (weak models), lower MAE need not improve the stability decision —
   but accurate modern UIPs have moved past that regime."*
3. **The other MT1 claim — boundary-abstention — SURVIVES and generalizes.** Abstaining on |predicted hull|
   < 0.05 eV/atom raises precision for **every** model (ORB 0.90→0.97, MACE 0.83→0.95, CHGNet 0.52→0.78,
   CGCNN 0.45→0.59 …). The "verify/abstain near the 0 eV/atom boundary" decision layer is model-agnostic.

## Implication for the MT1 manuscript (Bundle B)
- **Do NOT publish "low MAE ≠ reliable decision" as a general law** — V2 shows SOTA closes it (a reviewer
  would catch this immediately, as flagged in the strategy audit). 
- The defensible, sharper paper is: **"stability-decision reliability is a *separate* axis from regression MAE,
  it tracks MAE only once models exit the near-chance regime, and a boundary-abstention gate gives a
  model-agnostic precision lift (incl. for SOTA UIPs)."** That's a more nuanced and more correct contribution.
- This is a case of the workspace's own discipline working: the single-comparison MT1 effect did **not**
  generalize; V2 caught it before submission.

## Caveats
- Fixed-hull each_pred approximation (predicted hull = true_hull + form-error; hull not recomputed) — same as
  MT1; absolute F1 reproduces published CGCNN values. Recomputing the hull per model is the next rigor step.
- Single benchmark (Matbench Discovery WBM); the abstention-generalizes claim is the robust headline.

## Source
Matbench Discovery — Nature Machine Intelligence 2025 `10.1038/s42256-025-01055-1`; modern-UIP predictions
from the project's Figshare (CC-BY); MACE/CHGNet/M3GNet/ORB.
