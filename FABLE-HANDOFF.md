# FABLE-HANDOFF.md — materials-mlip-research

Handoff dossier for a future model ("Fable") to resume this MLIP-reliability audit workspace cold and
build a new SOTA contribution. Evidence-backed, honest, uncertainty marked. Prepared 2026-06-28;
**corrected 2026-06-28 after reconciling against the on-disk Stage-1/Stage-2 evidence** (the first pass
read only `DEEP-REVERIFY-2026-06-21.md`, which predates the Stage-1/2 results, and wrongly elevated the
dead rank-reordering direction — see §1).

---

## 0. TL;DR (≤8 bullet lines)
- This repo is a **reliability/benchmark-audit workspace over cached Matbench-Discovery predictions** (no model training, no DFT): calibration, conformal, selective prediction, ensemble disagreement, leaderboard rank fragility, and **chemistry-stratified discovery-acceleration under abstention** for universal interatomic potentials (UIPs).
- **Honest overall status: CONFIRMED-publishable.** The Stage-2-hardened winner is **MT29 "chemistry-stratified value of selective abstention"** — the oxide-vs-intermetallic abstention-benefit gap survives every control thrown at it. It is "P2 — most robust" in the portfolio submission plan, figure-ready for Digital Discovery.
- **Single best direction (PRIMARY):** the **stratum × coverage selective-abstention interaction**: confidence-based abstention helps the WBM stability decision *unequally* across anion-class strata (oxide most, intermetallic least), and this is NOT explained by hull-margin, base rate, yield, dominant elements, or time.
- **Metric Fable must beat:** the stratum×coverage **DAF/precision interaction** must stay **CI-excl-0** under the matched-yield control + real chemistry strata (current: matched-yield **48/60** cells, all 4 UIPs fire; LOEO **12/12** splits = 548/700 cells; WBM-round **3/5**; shuffle-null **0/700 & 0/300** clean; interaction |median| 0.267, max +0.90, chgnet oxide-vs-halide CI [0.774, 1.042]). To claim a *method* SOTA: a stratum-aware abstention policy beating the global policy's DAF-at-coverage per stratum.
- **DEAD — do not revive:** the **MT29 rank-reordering** framing (Kendall-τ=1.0 null on the run split, Stage-0) and the **MT28 "beat |hull-margin|" wedge** (own gate, 0/12 cells, 2026-06-21). These are residual control figures only.
- Scooped: MT4 ORB non-conservation (ICML 2025); V6 disagreement-as-uncertainty *signal* (npj 2026). V2 demoted to framing.
- All flagship work is **CPU/pandas over ~73 MB on-disk cached predictions** (n=256,963). GPU not load-bearing.

## 1. 项目身份 / Project identity
- **Domain:** reliability methodology for universal/ML interatomic potentials (MLIP/UIP) on the Matbench-Discovery crystal-stability benchmark. Mother-motif: *low regression error ≠ reliable decision.*
- **Core scientific question:** when a UIP pre-filters the binary "is this crystal thermodynamically stable (E_above_hull < 0)?" decision, does the *value* of confidence-based abstention depend on **chemistry** (anion class), in a way not explained by the free hull margin or trivial confounds — and are leaderboard rankings stable under honest leakage-controlled splits?
- **Artifact type:** **real-data audit**, not toy/synthetic and not a foundation model. It consumes the published Matbench-Discovery prediction CSVs; no potential is trained, no DFT is run.
- **Overall verdict & WHY (reconciled with the FULL evidence chain, not just DEEP-REVERIFY):** **CONFIRMED-publishable.** `DEEP-REVERIFY-2026-06-21.md` is a Stage-0 snapshot: it correctly KILLED the MT28 |hull-margin| wedge and flagged MT29-rank-reordering as a likely null — but it predates the Stage-1 (2026-06-22) and Stage-2 (2026-06-22) work that **pivoted MT29 to the stratified-abstention interaction and hardened it to SUCCESS**:
  - **Stage-1** (`research/results/MT29/findings-stage1-mt29-2026-06-22.md`): interaction survives genuine anion-class strata (precision 47/60, DAF 47/60) AND the corrected matched-stable-call-yield control that killed MT28 (**48/60**, all 4 models fire), shuffle-null clean (0/60).
  - **Stage-2** (`findings-stage2-robustness-2026-06-22.md`): survives **leave-one-element-out 12/12** (548/700 cells CI-excl-0; dropping all O does not collapse it) and **WBM-round 3/5** (temporal), shuffle-null clean throughout (0/700, 0/300).
  - Portfolio submission plan (`~/Desktop/Orchestration-files/PORTFOLIO-SUBMISSION-PLAN-2026-06-22.md`) lists this as **"P2 — most robust, draft"** → Digital Discovery. The portfolio memory's "MT29 CONFIRMED" refers to THIS stratified-abstention result, not rank-reordering. **The earlier PARTIAL verdict in this file's first pass was an error** caused by reading only the dead Part A.

## 2. 方法学分类 / Methodology classification
- **Is this methodological research? YES → benchmark/audit methodology.** It introduces no new estimator or potential; it is a **rigorously-controlled audit of where post-hoc selective abstention adds decision value across chemistry**, applied to frozen predictions.
- **Method classes in play** (all post-hoc, all on frozen predictions):
  - **selective prediction / abstention**: risk–coverage, AURC, precision/DAF at fixed coverage, and the **stratum × coverage interaction** (the headline object);
  - post-hoc **calibration** (isotonic / logistic on signed hull-distance → p_stable) — sensitivity layer;
  - **conformal prediction** (the on-disk `mt_v28_conformal_calibration.py` is *mislabeled* — isotonic + |p−0.5|, no finite-sample coverage; a real split/Mondrian conformal *classifier* is the open methods slot, §6 tertiary);
  - **ensemble-disagreement uncertainty** (std across 4 UIPs) — scooped, framing only;
  - **ranking-stability analysis** (Kendall-τ) — DEAD (null), kept as a control.
- **Which "SOTA to beat" applies:** the surviving headline's yardstick is an **abstention/coverage interaction number** (per-stratum DAF/precision gain difference, CI-excl-0), **not an accuracy number**. The killed MT28 direction was the only one whose bar was a calibration/selective-risk delta.

## 3. 当前 SOTA / Current SOTA  ← FRESH web-verified 2026-06-28
**(A) Matbench-Discovery leaderboard — the benchmark these audits ride on.** Live-fetched
2026-06-28 from the official leaderboard (now **39 models ranked**; combined score CPS = 0.5·discovery +
0.4·thermal-conductivity + 0.1·geometry). Top cluster (live fetch — see caveat):

| Model (2025–26) | F1 ↑ | κSRME ↓ | RMSD ↓ | MAE (eV/atom) ↓ | DAF ↑ |
|---|---:|---:|---:|---:|---:|
| EquiformerV3+DeNS-OAM | 0.931 | 0.118 | 0.059 | 0.018 | 6.07 |
| EquFlashV2 | 0.929 | 0.094 | 0.058 | 0.018 | 6.07 |
| eSEN-30M-OAM | **0.925** | **0.170** | 0.061 | 0.018 | 6.07 |
| PET-OAM-XL | 0.924 | 0.119 | 0.060 | 0.019 | 6.08 |
| SevenNet-MF-ompa | 0.901 | 0.317 | — | — | — |
| MACE-MPA-0 | 0.852 | 0.412 | — | — | — |
| MatterSim-v1-5M | 0.862 | 0.574 | — | — | — |

- **Caveat / UNVERIFIED names:** the exact top-row *model names* came from a single dynamic-page fetch; some 2026 row names (EquFlashV2, EquiformerV3, PET/TACE/MatRIS-OAM variants) may be transcription-fuzzy. **Corroborated across two sources:** eSEN-30M-OAM F1=0.925/κSRME=0.170; SevenNet-MF-ompa F1=0.901; MACE-MPA-0 F1=0.852; MatterSim-v1-5M F1=0.862/κSRME=0.574; top F1 ≈ 0.92–0.93, top κSRME ≈ 0.09–0.17, DAF ≈ 6.0–6.1. The 4 UIPs in this repo (orb/mace/chgnet/m3gnet, F1 0.57–0.86) are the **2023–24 generation** — a refresh to ≥1 OAM-era model would strengthen (but is not required for) a chemistry-stratified *value-of-abstention* claim, which is about decision-layer behavior, not raw accuracy.

**(B) Per-direction SOTA & scoop status:**

- **MT29 stratified-abstention interaction (PRIMARY, CONFIRMED).** **OPEN SEAM.**
  Nearest comparator: **Proof-Carrying Materials (PCM), arXiv:2603.12183 v2 (Mar 2026)** — audits CHGNet/TensorNet/MACE as stability filters; single MLIP **misses 93% of DFT-stable** on a 25k benchmark; risk model **AUC-ROC 0.938 ± 0.004** (cross-MLIP ~0.70; any-fails 0.834 ± 0.005); near-zero pairwise error correlations; Lean-4 certs. **PCM gives a global risk AUC, NOT a chemistry-stratified value-of-abstention (DAF) interaction with a matched-yield control.** No 2025–26 paper reports the oxide-vs-intermetallic abstention-benefit gap with these controls → the stratified-DAF interaction is uncontested. Confirmed NOT scoops: MS25 (ACS JCIM 10.1021/acs.jcim.5c01262), MLIPAudit (arXiv:2511.20487), "Bias in Universal MLIPs & Fine-Tuning" (arXiv:2603.10159).
- **MT28 — beat |hull-margin| on the stability decision.** **KILLED in-house** (0/12 cells beat the free margin at matched coverage+yield, 2026-06-21). Also relevant: **Flexible Uncertainty Calibration for MLIPs, now npj Comput. Mater. 2026 (s41524-026-02080-3)** — learnable conformal *regression* quantiles on MACE-MP-0, not the stability decision. Residual = a citable negative result.
- **Proper conformal stability *classifier* (finite-sample coverage).** **OPEN SEAM (narrow, low-impact).** All MLIP conformal work is regression; PCM uses formal certs. Genuinely unoccupied, partly pre-empted by "distance is sufficient."
- **V6 — cross-model disagreement as uncertainty.** **SCOOPED** (Liu et al., arXiv:2507.21297 → npj Comput. Mater. 2026 s41524-025-01905-x; PCM's near-zero error correlations independently support it). Effectively closed.
- **MT4 — ORB non-conservative-force NVE drift.** **SCOOPED → DROP** (Bigi/Langer/Ceriotti, arXiv:2412.11569 → ICML 2025 PMLR 267; repo ρ_ORB≈0.33 weak).
- **MT29-rank-reordering — leaderboard rank fragility.** **DEAD (null).** τ=1.0, 0 rank moves on the run (unique-prototype) split. The *concept* is established generically (BenchBench/BAT for AI benchmarks; MLIP Arena arXiv:2509.20630 for physics/MD tasks). The quantified materials rank-reordering map remains *uncontested but unrun and at high null risk* — keep only as an optional control, not a paper.
- **V2 — "low MAE ≠ reliable decision."** **PARTIALLY SCOOPED → framing.** Matbench Discovery (Nat. Mach. Intell. 2025) names the misalignment; Spearman(MAE,F1)=−0.929 is a guardrail figure.

## 4. 评价指标 / Evaluation metrics
| Metric | Def (1-line) | Dir | Typical / baseline | Computed on |
|---|---|---|---|---|
| **Stratum×coverage abstention interaction** (+boot CI) | difference in DAF/precision *gain* from abstention across anion strata | n/a (CI excl. 0 = real) | **headline:** matched-yield 48/60, LOEO 12/12 (548/700), WBM-round 3/5; \|median\| 0.267, max +0.90 | WBM, 4 UIPs, 6 strata |
| **Shuffle-null (permute confidence within stratum)** | falsification control | n/a (0 = clean) | **0/60, 0/700, 0/300** (clean throughout) | WBM |
| **Matched stable-call yield** | # called stable, held equal across strata/signals | n/a (control) | **the control that killed MT28**, survived by MT29 | WBM |
| **DAF** (discovery acceleration factor) | enrichment of stable hits vs random | ↑ | leaderboard top ≈ 6.0–6.1; per-stratum gain is the object | WBM first-10k |
| **Precision @ coverage** (selective) | precision of "stable" calls at top-k confidence | ↑ | margin: ORB 0.966@70%, MACE 0.952@70%, CHGNet 0.704@70% | WBM, 4 UIPs |
| **AURC** (area under risk-coverage) | mean selective risk over coverages | ↓ | \|hull margin\| baseline already optimal (MT28 KILL) | WBM, n=256,963 |
| **Kendall-τ / rank displacement** | leaderboard rank stability | ↑ (1=stable) | **τ=1.0, 0 moves** (DEAD direction) | 8 models, WBM splits |
| **F1 / κSRME** | stability classification / phonon κ error | ↑ / ↓ | leaderboard top ≈0.93 / ≈0.09–0.17 | WBM / phonon |
| **ECE / Brier / NLL** | calibration error / proper scores | ↓ | not load-bearing here | calibration split |

- **Target number Fable must beat (best direction = MT29 stratified abstention):** keep the stratum×coverage interaction **CI-excl-0** under the matched-yield + real-strata + LOEO + WBM-round battery (current: 48/60 matched-yield, 12/12 LOEO, shuffle-null clean). Fable claims *new* SOTA by either (a) extending the confirmed interaction to ≥1 OAM-era UIP + finer strata with tighter CIs, or (b) building a **chemistry-stratum-aware abstention policy** that delivers higher DAF-at-fixed-coverage per stratum than the global policy. Source: `research/results/MT29/findings-stage1-mt29-2026-06-22.md`, `findings-stage2-robustness-2026-06-22.md`, `mt29_stage1_matched_yield_result.json`, `mt29_stage2_robustness_result.json`.
- **If Fable instead revives a global calibration/risk angle, the bar is PCM's AUC-ROC 0.938 ± 0.004** (arXiv:2603.12183) **and** beating |hull-margin| at matched coverage+yield — which the in-house gate showed is *not* currently achievable (hard wall).

## 5. 现有资产 / Existing assets (on disk)
**Datasets present (no download needed; free/no-auth Figshare-cached):**
| Asset | Path | Size | Rows |
|---|---|---:|---:|
| 4 modern UIP preds (chgnet/m3gnet/mace/orb) | `~/mt_uip/*_pred.csv` | ~5.3 MB ea | 256,963 ea |
| 4 stage-0 (2020-era) preds (CGCNN ens=10, CGCNN+P, MEGNet, ALIGNN-FF) | `~/mt_stage0/data/*.csv.gz` | 1.3–13 MB | — |
| WBM summary = ground truth (hull, prototype, formula, round-from-id, bandgap, symmetry) | `~/mt_stage0/data/2023-12-13-wbm-summary.csv.gz` + cache mirror | ~13 MB | 256,963 |

Disk: 593 GB free; working data < 0.1 GB. Anion-class strata + WBM-round + element metadata are **confirmed joinable** on disk (224,179 distinct prototypes; WBM round from `material_id`, counts 61,466/52,755/79,160/40,314/23,268).

**Code that runs + cached results — MT29 Stage-1/2 are DONE (this is the load-bearing correction):**
- `research/results/MT29/mt29_stage1_chem_yield.py`, `mt29_stage1_matched_yield_fix.py`, `mt29_stage2_robustness.py` — the **working** stratified-abstention pipeline (genuine anion strata + corrected common-absolute-yield control + LOEO + WBM-round + 1000-boot CIs + shuffle-null). Results: `mt29_stage1_result.json`, `mt29_stage1_matched_yield_result.json` (headline), `mt29_stage1_chem_yield_result.json`, `mt29_stage2_robustness_result.json` (+ manifests). Prereg: `prereg-stage2-mt29-2026-06-22.md`.
- `research/mt28_riskcov.py` — canonical Stage-0 risk-coverage with full reproducibility manifest (seed 20260621, 1000 boot, SHA-256, pinned numpy 2.3.5/pandas 2.3.3/sklearn 1.7.2/scipy 1.16.2, py 3.13.7). Result + the MT28 KILL finding.
- Other scripts (`mt29_rank_fragility_audit.py`, `mt28_calibration_audit.py`, `mt_v28_conformal_calibration.py`, `v6_disagreement_reliability.py`, `mt_v2_modern_uip.py`) `py_compile`-clean.
- Independent red-team audit: `research/audits/INDEPENDENT_RED_TEAM_AUDIT_2026-06-17.md`.

**THIN / MISSING / UNVERIFIED (load-bearing gaps):**
1. **Figures for the P2 paper are NOT yet rendered** — DAF-vs-coverage per stratum, stratum×model interaction heatmap, LOEO/round robustness panel, shuffle-null contrast. This is the #1 remaining step to draft-ready (Stage-2 findings "Next step"). *(Being executed this session.)*
2. **No manuscript yet** (no `manuscripts/` dir, unlike geospatial/structured). Draft + figures = the path to submission.
3. The old `scripts/supplement_strata_daf.py` had a `KeyError: 'orb'` — **superseded** by the working `mt29_stage1/stage2` scripts above; archive or ignore it.
4. The `mt_v28_conformal_calibration.py` "conformal" label is an overclaim (no nonconformity/quantile/finite-sample coverage).
5. **Fixed-hull `each_pred` approximation** (predicted hull = true hull + formation-energy error). Reproduces published F1; absolute numbers can shift on full recompute.
6. Refresh to ≥1 OAM-era UIP is optional but would pre-empt a "stale models" reviewer note.

## 6. 通往我们自己的 SOTA / Path to our own SOTA
**Ranked surviving directions:**

1. **MT29 chemistry-stratified value of selective abstention (PRIMARY, CONFIRMED — finish to submission).**
   - **Falsifiable claim:** the value of confidence-based abstention for the WBM stability decision is chemistry-stratified (oxide most, intermetallic least), NOT explained by hull-margin, base rate, yield, dominant elements, or time.
   - **Status:** Stage-2-hardened SUCCESS (48/60 matched-yield, 12/12 LOEO, 3/5 rounds, shuffle-null clean). **Remaining = figures + draft only.**
   - **Wedge vs SOTA:** PCM (2603.12183) gives a global risk AUC, not a stratified value-of-abstention with a matched-yield control; no paper reports the anion-class abstention-benefit gap.
   - **Kill criteria:** interaction CI includes 0 after controls (already passed).
   - **Venue:** Digital Discovery (RSC, rolling) — primary; NeurIPS D&B (next cycle) — alt.
   - **Next steps (this machine, CPU, hours):** (a) render the 4 figures from the cached result JSONs; (b) draft the manuscript; (c) optional OAM-era UIP refresh + finer strata for the camera-ready.

2. **Chemistry-stratum-aware abstention POLICY (method extension → our own SOTA).** Turn the diagnostic into an estimator: a per-stratum abstention threshold that maximizes DAF-at-fixed-global-coverage, vs the global-threshold baseline. Claim: stratum-aware abstention strictly dominates global abstention on DAF-at-coverage. Kill if no per-stratum gain over global at matched coverage. This is the genuinely *new-method* seam.

3. **Proper conformal stability classifier (TERTIARY, methods slot).** Real split/Mondrian conformal classifier (nonconformity = signed hull margin) with distribution-free coverage; cures the mislabeled-"conformal" overclaim. Low-impact. Venue: MLST.

**Residual salvage from KILLED/DEAD work:** the MT28 risk-coverage KILL ("|hull margin| is sufficient at matched coverage+yield, 0/12") is a citable negative control inside the P2 paper. MT29-rank-reordering (τ=1.0) and V2 Spearman(MAE,F1)=−0.929 and V6 disagreement ρ=0.714 are reusable framing/guardrail figures. Do not pitch any of these standalone.

## 7. 数据与算力 / Data & compute feasibility
- **Everything publishable here is CPU/pandas** over <0.1 GB of on-disk tables (n=256,963) — seconds-to-minutes on the 24-core CPU; 1000-bootstrap CIs included. The RTX 5090 (24 GB) is **not load-bearing** (MT4 MD is scooped/dropped; it peaked 154–534 MB VRAM).
- **Fits trivially:** all stratified-abstention / rank / calibration / conformal / DAF analyses; env `dl` (numpy/pandas/sklearn/scipy suffice; torch unused for the audits).
- **Optional GPU-bounded refresh:** one OAM-era UIP (eSEN-30M / SevenNet-ompa) frozen-inference over WBM fits 24 GB for ≤30M-param models; not required for the chemistry-stratified value-of-abstention claim.
- **Do NOT pull:** Figshare bulk structure bundles — the compact prediction CSVs + WBM summary already on disk suffice.

## 8. Sources
**Live-verified this session (2026-06-28):**
- Matbench-Discovery leaderboard (39 models; CPS weighting; top F1≈0.93, κSRME≈0.09–0.17, DAF≈6.0–6.1) — https://matbench-discovery.materialsproject.org/ (live fetch; top-row model *names* UNVERIFIED/fuzzy; eSEN/SevenNet-ompa/MACE-MPA/MatterSim numbers cross-confirmed).
- Matbench Discovery, Nat. Mach. Intell. 2025 — 10.1038/s42256-025-01055-1 ; arXiv:2308.14920.
- Proof-Carrying Materials — arXiv:2603.12183 v2 (Mar 2026): AUC-ROC 0.938±0.004; misses 93% DFT-stable on 25k; near-zero pairwise error correlations; cross-MLIP ~0.70; any-fails 0.834±0.005 — https://arxiv.org/abs/2603.12183
- Flexible Uncertainty Calibration for MLIPs — npj Comput. Mater. 2026, s41524-026-02080-3 (was arXiv:2510.00721) — https://www.nature.com/articles/s41524-026-02080-3
- Heterogeneous-ensemble universal uncertainty (V6 scoop) — npj Comput. Mater. 2026, s41524-025-01905-x (arXiv:2507.21297).
- "The dark side of the forces" (MT4 scoop) — arXiv:2412.11569 → ICML 2025, PMLR 267.
- MLIP Arena — arXiv:2509.20630 / OpenReview SAT0KPA5UO. Not scoops: MLIPAudit arXiv:2511.20487; MS25 ACS JCIM 10.1021/acs.jcim.5c01262; "Bias in Universal MLIPs" arXiv:2603.10159; Benchmark Agreement Testing/BenchBench (generic AI).

**From on-disk docs (this repo) — the authoritative Stage-1/2 evidence:** `research/results/MT29/findings-stage1-mt29-2026-06-22.md` + `findings-stage2-robustness-2026-06-22.md` + `mt29_stage1_matched_yield_result.json` + `mt29_stage2_robustness_result.json` + `prereg-stage2-mt29-2026-06-22.md`; `~/Desktop/Orchestration-files/PORTFOLIO-SUBMISSION-PLAN-2026-06-22.md` (P2); `DEEP-REVERIFY-2026-06-21.md` (Stage-0 snapshot); `research/results/MT28/findings-stage0-riskcoverage-2026-06-21.md` (the MT28 KILL) + manifest; `research/findings-MT29-rank-fragility.md` (the DEAD direction); `research/audits/INDEPENDENT_RED_TEAM_AUDIT_2026-06-17.md`; on-disk `~/mt_uip/*_pred.csv`, `~/mt_stage0/data/*.csv.gz` (git HEAD b70f1ab).

## Independent Re-Audit (2026-06-30)

**Verdict: CONFIRMED** (re-confirmed independently, no change). This is one of the more rigorously self-documented repos in the portfolio: raw per-cell arrays are preserved (not just summaries), manifests carry sha256 + git_head + versions, the honest 3/5 WBM-round partial-pass is disclosed inside the JSON's own summary field (not just prose), a self-caught-and-fixed "vacuous control" bug is on record, and the hypothesis pivot after the originally-preregistered rank-fragility claim returned a null is transparently disclosed.

**Independently re-verified and holding up:** the core stratum × coverage DAF interaction claim (max interaction +0.90, CI [0.77, 1.04]; matched-yield 48/60; LOEO 12/12 = 548/700; WBM-round 3/5 = 157/300; all shuffle-nulls clean) reproduces exactly from the raw per-cell JSON (`research/results/MT29/mt29_stage1_matched_yield_result.json` and `mt29_stage2_robustness_result.json`), cross-checked against sha256-verified raw input data. The LOEO element list was confirmed to be algorithmically frequency-derived, not hand-picked.

**Minor corrections worth fixing (none affect the core verdict):**
- The TL;DR above states "interaction |median| 0.267" — this is actually the **mean** of |interaction_med| over all 60 cells, not a median. The true median is 0.19 (over all 60 cells, matching `manuscripts/paper.tex`) or 0.259 (over the 48 firing cells, matching the superseded `manuscripts/paper.md`). "median" should be corrected to either the right number or the right word.
- The "halide DAF 4.42 → 3.01" correction referenced in the master portfolio index is confirmed: 3.01 is genuinely what's in `research/results/MT29/mt29_stage1_chem_yield_result.json` and the only number used consistently in the current manuscript. However, no historical trail (commit, transcript, or log) proving when/how this correction happened could be found anywhere on disk — a provenance gap worth noting, not a current error.
- `manuscripts/figures/render_figures.py` (Python/matplotlib) and `manuscripts/figures/F1-F4*.R` (R/ggplot2) are two non-deduplicated figure pipelines over the same source JSONs; F2/F3 use identical output filenames, and the later R run silently overwrote the earlier Python-rendered images. No numeric divergence was found (both pipelines read the same underlying JSON), but this is a real reproducibility hygiene gap worth cleaning up (pick one toolchain, or rename outputs so both survive).
- The "preregistration" framing is looser than it may appear: the actual 2026-06-16 preregistration document committed to a different hypothesis (leaderboard rank-fragility) that returned a null; the chemistry-stratified-abstention hypothesis was substituted in afterward, and its own Stage-1 success criteria live only inside the analysis script's docstring, written in the same session as the result. This is already transparently disclosed within the repo's own docs — flagged here only for anyone treating "preregistered" as carrying full ex-ante evidentiary weight.

STATUS: CONFIRMED — independently re-audited 2026-06-30 (no change to core claim; see "Independent Re-Audit (2026-06-30)" section for minor documentation fixes) — best direction = MT29 chemistry-stratified value of selective abstention (Stage-2-hardened: matched-yield 48/60, LOEO 12/12, WBM-round 3/5, shuffle-null clean; figures+draft remaining) — metric to beat: keep the stratum×coverage DAF interaction CI-excl-0 under matched-yield+LOEO+round, or build a stratum-aware abstention policy beating global DAF-at-coverage.
