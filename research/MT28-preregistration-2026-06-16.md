# MT28 — Hull-boundary stability-decision calibration (Stage-1 preregistration)

Date: 2026-06-16 · Workspace: `materials-mlip-research` · Status: **spec only, not run**.
Target venue: **Digital Discovery (RSC)** (primary) / **MLST** (fallback) — both accept a calibration/UQ
*audit* of existing models with no new model. **NOT** npj Comput. Mater. (would read as incremental).

## Wedge (why this clears the novelty bar)
Matbench Discovery (Riebesell et al., *Nat. Mach. Intell.* 2025, arXiv 2308.14920) *names* the "triangle of
peril" — accurate energy regressors produce high false-positive-stable rates near the 0 eV/atom hull — but
offers **no calibration/abstention remedy**. Every published UQ-for-MLIP method (Hu 2022 arXiv 2208.08337;
Ho/Ortner/Wang 2025 arXiv 2510.00721; Bilbrey 2025 npj 10.1038/s41524-025-01572-y) is **regression-targeted**
(energy/force intervals); **none reframes onto the binary stability decision with selective classification.**
Wedge = post-hoc calibration (temperature / isotonic / split-conformal) + an **abstention band at the hull
boundary**, audited on published predictions, with **selective-classification curves** (false-positive-stable
rate & precision vs coverage) as the headline — not the calibration recipe.

## Preregistered question + falsifiable KILL
Can calibrated abstention near the 0 eV/atom hull boundary reduce false-positive "stable" calls beyond the
trivial signal already available?
- **KILL (the one that matters):** calibrated abstention does **not** beat the trivial `|predicted hull margin|`
  as the abstention signal — i.e. bootstrap-95%-CI of (precision@coverage_calibrated − precision@coverage_margin)
  includes 0 at fixed coverage. If raw margin distance is already optimal, there is no calibration story
  (still publishable as a clean negative: "hull-margin distance is the sufficient uncertainty signal").
- **KILL (scope):** if abstention adds nothing even for the weak 2020 models (where the triangle is real).

## Method / MPU
- Models: **6–8** spanning UIP generations — weak-2020 anchors (CGCNN, MEGNet, ALIGNN-FF) + modern
  (MACE, CHGNet, M3GNet, ORB). Reuse the cached WBM predictions already on disk (`results/MT1_MT2/`, V2).
- Calibration methods: temperature, isotonic, split-conformal; + Venn-ABERS for robustness.
- Baselines to beat: (a) `|predicted hull margin|` abstention; (b) random abstention; (c) no abstention.
- Ablations: calibration-set size; abstention threshold (0 vs 0.05 vs 0.1 eV/atom); per-chemistry breakdown;
  the **V2 MAE↔F1 Spearman = −0.93** result included to show abstention — not the MAE/decision mismatch — is
  the surviving lever (modern UIPs already classify well; abstention still raises ORB 0.90→0.97, per V2).

## Metrics
Precision/recall & FP-stable-rate vs coverage (selective-prediction curves); ECE/Brier; reliability diagrams;
discovery-acceleration-factor @ coverage; bootstrap 95% CIs throughout.

## Adversarial stress test
- **Top reviewer kill:** "temperature/isotonic/conformal are off-the-shelf → no contribution." → Mitigation:
  lead with the *selective-classification decision* result + the `|hull-margin|`-baseline comparison; the
  novelty is the hull-boundary decision reframing, not the wrapper.
- **Second:** "modern UIPs already classify well (V2), so why care?" → the boundary band still lifts SOTA
  (ORB 0.90→0.97); cite own V2; scope the claim to the boundary, not globally.
- **Concurrent threat:** none direct (all UQ-MLIP work is regression-only) — confirm at submission.

## Go/no-go spike (cheap, CPU, run before Stage-0)
On cached WBM preds for **one** model (e.g. ORB): does split-conformal abstention beat `|hull-margin|`
abstention at 70% coverage (precision gap CI excludes 0)? If **no** model beats the margin baseline → the
direction collapses to "margin distance is all you need" — reframe as that negative.

## Boundaries
Benchmark-only; no materials-discovery claim. Published predictions + existing DFT labels; no UIP training, no DFT.

## Publication readiness capsule (pre-experiment gate)

- **Primary target / fallback:** Digital Discovery (primary) / Machine Learning: Science and Technology (fallback). Use a benchmark-audit framing; do not claim new material discovery.
- **Exact rescued title:** *Hull-boundary abstention and rank fragility in universal interatomic-potential discovery benchmarks* — MT28 slice: *Hull-boundary abstention for stability-decision calibration*.
- **Preregistered question:** At fixed coverage, does a calibrated/selective abstention rule reduce false-positive-stable calls near the hull boundary beyond the trivial absolute predicted hull-margin rule?
- **Minimum Stage-0 evidence:** one cached WBM model, one held-out calibration split, precision/FP-stable-rate vs coverage at 70% and 90% coverage, bootstrap CI for calibrated abstention minus `|predicted hull margin|`.
- **Trivial baseline / null controls:** no-abstention; random abstention; absolute predicted hull-margin abstention; shuffled stability labels; chemistry-stratified margin-only check.
- **Kill thresholds:** kill the calibration headline if the 95% CI for precision gain over the margin baseline includes 0 at both 70% and 90% coverage, or if gains occur only after excluding the hull-boundary band.
- **Leakage / circularity controls:** use Matbench Discovery WBM labels and split metadata; keep calibration/test structures disjoint; report prototype/chemistry strata; do not tune thresholds on the test curve.
- **Data / resource gates:** cached published predictions must exist locally or be obtainable as small tables; no DFT, no UIP training, no GPU run; abort if a required pull would exceed lightweight metadata/prediction-table download.
- **Next files to update:** `materials-mlip-research/research/materials-mlip-direction-bank.md`; any MT1/V2 findings only as background/control appendices; consolidated readiness summary.

