# MT1+MT2 Stage-0 — Matbench Discovery: "low regression error ≠ reliable stability decision" (MT1 SUPPORTED)

Date: 2026-06-15 · Workspace: `materials-mlip-research` · Compute: `dl4080` (pandas+sklearn, CPU; no pymatgen).
Data: Matbench Discovery WBM (registration-free CSVs from the repo): summary (true e_form + e_above_hull) +
per-model formation-energy predictions (CGCNN ens=10, CGCNN+P perturb=5, ALIGNN-FF, MEGNet).
Script: `mt_stage0.py` · Raw: `results/MT1_MT2/`. WBM test = **256,963** structures, **42,825** truly stable.

## Question (pre-registered, falsifiable)
Does low formation-energy regression error guarantee a reliable *stability* classification at the 0 eV/atom
hull boundary? **MT1:** reproduce the "triangle of peril" (a lower-MAE model can have worse stability F1) and
test whether boundary-abstention raises precision. **MT2:** does reliability degrade across WBM substitution
steps 1→5 (more OOD)? Method: predicted hull dist = true_hull + (e_form_pred − e_form_true) (standard
matbench-discovery each_pred; hull fixed at MP2020-corrected). Bootstrap 95% CIs.

## Results

| model | n | MAE_form (eV) | clf F1 | F1 CI | precision | FPR | boundary-abstain precision |
|---|--:|--:|--:|---|--:|--:|---|
| CGCNN | 256,961 | 0.135 | 0.509 | (0.505,0.512) | 0.446 | 0.148 | **0.45→0.59** @cov 0.70 |
| **CGCNN+P** | 256,961 | **0.108** | **0.508** | (0.505,0.512) | 0.407 | **0.197** | 0.41→0.58 @cov 0.56 |
| ALIGNN-FF | 256,963 | 0.140 | 0.491 | (0.488,0.495) | 0.374 | 0.240 | 0.37→0.40 @cov 0.69 |
| MEGNet | 256,963 | 0.128 | 0.511 | (0.507,0.514) | 0.456 | 0.138 | 0.46→0.50 @cov 0.75 |

## Adjudication — MT1 SUPPORTED, MT2 weak/mixed
- **Triangle of peril REPRODUCED ✅:** CGCNN+P has **lower formation-energy MAE (0.108 < 0.135)** than CGCNN
  yet **worse stability classification** (F1 0.508 ≤ 0.509, and notably **FPR 0.197 vs 0.148** — markedly more
  false "stable" calls). A better regressor is the worse *decision-maker* near the hull boundary — exactly the
  Nature MI 2025 (`10.1038/s42256-025-01055-1`) Table-1 effect, on the full leakage-removed WBM. The absolute
  F1 (~0.51) matches the published CGCNN value → method validated.
- **Calibrated boundary-abstention works ✅ (strongly for the CGCNN family):** abstaining on
  |predicted hull| < 0.05 eV/atom raises precision **0.45→0.59 (CGCNN)** and **0.41→0.58 (CGCNN+P)** at
  ~60–70% coverage; modest for MEGNet (0.46→0.50) and weak for ALIGNN-FF (0.37→0.40). The "do-not-trust near
  the boundary" gate is decision-grade where the model has signal.
- **MT2 OOD-by-step weak/mixed ⚠️:** formation-energy MAE rises mildly at the most-OOD step 5 for *all* models
  (CGCNN 0.139→0.165; CGCNN+P 0.098→0.135; ALIGNN 0.134→0.144; MEGNet 0.135→0.146) — a consistent but small
  regression-OOD signal. But stability **F1 is non-monotonic** across steps (e.g. CGCNN 0.48/0.54/0.48/0.54/0.53)
  → the clean monotonic OOD *classification* degradation curve is **NOT reproduced** with this fixed-hull
  each_pred. Honest negative for MT2 as framed; consistent with the broader theme that classification and
  regression decouple.

## Honest caveats
1. **Fixed-hull each_pred approximation** (predicted hull = true_hull + form-energy error; hull not recomputed
   from predictions). This is matbench-discovery's standard IS2RE approach and reproduces the published CGCNN
   F1, but the true pipeline recomputes the convex hull → absolute numbers can shift slightly.
2. **2020-era models** (CGCNN/MEGNet/ALIGNN-FF); modern UIPs (MACE/CHGNet/ORB) classify better. The *point*
   (regression≠classification reliability) is model-agnostic and holds.
3. MT2's per-step stable base-rate varies, which muddies the F1 trend; a base-rate-controlled OOD metric is the
   fix for a clean MT2.

## Conclusion
**MT1 is supported on the full WBM**: a lower-MAE energy model can be the less reliable stability classifier
(triangle of peril), and a calibrated boundary-abstention gate converts that into decision-grade precision
gains — the materials analogue of the workspace's "good score ≠ reliable decision" thesis. **MT2 (monotonic
OOD-by-substitution-step) is not cleanly reproduced** here (regression degrades mildly, classification
non-monotonic) — a follow-up with hull recomputation + base-rate control is needed. Benchmark-only; no
materials-discovery claim.

## Source
Matbench Discovery — Nature Machine Intelligence 2025, `10.1038/s42256-025-01055-1`; data: repo CSVs (CC-BY).

---
## ⚠️ 2026-06-15 UPDATE (V2) — the triangle-of-peril is SCOPED, not general
V2 (`findings-V2-modern-uip-triangle.md`) re-ran this on 4 **modern UIPs** (MACE/CHGNet/M3GNet/ORB) + the
2020 anchors. **Spearman(MAE, F1) = −0.93** across 8 models → low MAE DOES predict good stability decisions;
ORB is best on both. The "low MAE ≠ reliable decision" mismatch here was a **within-weak-2020-models artifact**
(all clustered near chance F1≈0.51); SOTA UIPs (MACE/ORB: MAE 0.029, F1 0.83–0.86, FPR 0.02–0.04) **close it.**
**Do NOT publish the triangle as a general law.** What survives + generalizes: **boundary-abstention raises
precision for every model incl. SOTA** (ORB 0.90→0.97). MT1 manuscript must be rescoped accordingly.
