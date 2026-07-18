# MT29 · roster-expansion pre-registration — the generational contrast of oxide-anchored value-of-abstention

**Date written:** 2026-07-13, BEFORE running any expanded audit (this document is committed first).
**Author:** t1-materials (local CPU Tier-1 execution).
**Compute:** CPU/pandas/NumPy only. On-disk cached WBM ground truth + **published** Matbench-Discovery
per-structure predictions (Figshare article 28187990 v25, credential-free). No GPU, no self-inference,
no model weights, no box, no spend.

## Disclosure (read first — provenance honesty)

This pre-registration is authored **after** the paper's red-team / honest-scope pass (the disclosed
limitation (ii): "the oxide benefit reproduces on three of four modern UIPs but sharply reverses in the
newest, Orb-v3") and **before** the expanded run whose result it governs. It is therefore a genuine
ex-ante plan for turning an *n = 1 dissenter* limitation into a *powered* generational statement, but it
is **pending user sign-off**. All results produced under it will be labelled
"**post-hoc-motivated, pre-registered, pending sign-off**" until the user confirms. No outcome is
privileged in advance; an honest null (the contrast does **not** hold) is a reportable, publishable result
and is defined as such below.

This plan **inherits** the frozen statistical machinery verbatim (same prototype-blocked cluster
bootstrap, same common-absolute matched-yield budget, same BH-FDR + Holm multiplicity, same seed
20260621, same n_boot 1000). It **invents no new estimator.** The only new objects are (a) the roster,
(b) the model→generation map, (c) the two-arm aggregation of the already-defined per-model interaction.

## 0. Regression guard (run and PASSED before this plan executes)

Before any expansion, the frozen legacy-4 pipeline was re-run on the untouched on-disk inputs
(`~/mt_uip/{chgnet,m3gnet,mace,orb}_pred.csv` + `2023-12-13-wbm-summary.csv.gz`) and reproduced
**byte-identical** output JSON:

| script | frozen `output_sha256` | reproduced |
|---|---|---|
| `mt29_stage1_chem_yield.py` | `e203e6e326d0ab6f…` | byte-exact |
| `mt29_stage1_matched_yield_fix.py` | `e85f6177ac8a26ed…` | byte-exact |
| `mt29_stage2_robustness.py` | `2275d6a2c10afcb4…` | byte-exact |

The frozen result/manifest files were backed up and restored bit-for-bit; nothing canonical was mutated.
The four **downloaded** anchor predictions (from Figshare v25) are asserted **byte-identical** to the
on-disk frozen anchor CSVs (verified for chgnet: max abs diff 0.0 over 256,963 rows), so the download
path is the same authoritative source that produced the manuscript headline — the expansion sits on
continuous ground truth, not a re-derivation.

## 1. The roster (frozen list)

Source: every credential-free WBM prediction file on Figshare **28187990 v25**, converted by taking the
MP2020-corrected `e_form_per_atom_<model>` column (never the `*_uncorrected` variant) → `e_form_pred`.
This is the **authoritative** convention that matches the ground-truth `e_form_per_atom_mp2020_corrected`
column and the four frozen anchors — it is **not** the self-inferred `mt29_uip_inference.py` output, whose
documented ~+0.11 to +0.59 eV/atom oxide bias (POST-ANALYSIS-2026-07-10 §4) made the on-box OAM arm
degenerate. The roster expansion explicitly **replaces** that flawed self-inference with published preds.

**Generation map (frozen).** Each model is tagged by its documented training corpus, auditable from the
leaderboard filename and the matbench-discovery registry:
- **MP generation** = trained on Materials Project / MPtrj / MP-relaxed **only** (the 2022–2024 pre-
  additional-materials era). Includes the 4 anchors, the 2020-era classical baselines, and modern MP/MPtrj
  UIPs.
- **OMat generation** = trained on OMat24 / Alexandria (sAlex) / OpenLAM / OAM / OMA (the 2024–2026
  additional-materials era). Filename tokens `oam|omat|openlam|oma|salex|mpa` ⇒ OMat.
- **special** = GNoME (proprietary training corpus; weights not public, predictions published) — reported
  as a labelled special case, **excluded** from the two-arm contrast counts.

The exact roster, file ids, md5s, and per-model generation tags are frozen in
`research/results/MT29/fetch_roster_preds.py::ROSTER` and mirrored to
`results_expansion_2026-07-13/ROSTER25_DATA_MANIFEST.json`. Target ≈ 26 MP-trained + 17 OMat-trained +
GNoME; the precise counts after the pre-registered inclusion rule (§3) are recorded in the manifest.

**Primary vs. secondary population.** The **primary** contrast is over **modern UIPs only**
(`klass == uip`, i.e. GNN/equivariant potentials) so the two arms compare like-for-like architectures
across training eras. The 2020-era **classical** baselines (`klass == classical`: CGCNN, CGCNN+P, MEGNet,
Wrenformer, Voronoi-RF, ALIGNN, BOWSR-MEGNet) are all MP-trained and are reported for the
**MAE-vs-decision-quality spread** and the distributional-anchoring count, but are **not** required for the
generational verdict.

## 2. Inherited estimand (unchanged from the frozen pipeline)

For model *m* and anion stratum *f*, the **matched-yield abstention gain** is exactly
`mt29_stage1_matched_yield_fix.py`'s quantity:
`gain_f(m) = DAF(top y_tight | f) − DAF(top y_loose | f)`, where DAF = precision / stratum-base-rate over
the top-Y most-confident **called-stable** structures, Y a **common absolute budget across strata**
(`y_loose = min_f total_called_stable`, `y_tight = y_loose // 2`), confidence = `|hull_pred_m|`,
`hull_pred_m = hull_true + (e_form_pred_m − e_form_true)`. CIs are the **prototype-blocked (cluster)
bootstrap** of `mt29_prototype_blocked_ci.py` (block = `protostructure_spglib`), n_boot 1000, seed
20260621. The per-model **oxide-anchored interaction** is
`I_m = gain_oxide(m) − gain_halide(m)` (oxide vs halide is the frozen headline pair; the full 15-pair set
is also computed). `excl0(m)` ≡ the 95% blocked-bootstrap CI of `I_m` excludes 0.

## 3. Pre-registered inclusion rule (anti-degeneracy)

A model enters the **powered** matched-yield contrast iff it calls **≥ 50 structures stable in every anion
stratum** used (so the common-Y budget is non-degenerate) AND its converted CSV covers ≥ 99% of the
256,963 WBM rows. Models failing either test are **reported with the reason** (and their per-stratum
called-stable counts) but **excluded from the arm-fraction denominators**. This rule is fixed now to
prevent a repeat of the self-inference degeneracy (oxides-called-stable = 2–5) leaking into the counts.
The strata are the frozen six anion classes; the contrast headline uses **oxide vs halide**.

## 4. Multiplicity plan (frozen, scaled to the expanded family)

The interaction family scales from 4×15 = 60 cells to **N_incl × 15** cells (N_incl = models passing §3).
We inherit `mt29_multiplicity_correction.py` unchanged:
- **Primary:** Benjamini–Hochberg FDR at q = 0.05 over the full N_incl × 15 family (BH scales cleanly).
- **Reported alongside:** Holm–Bonferroni FWER at α = 0.05 (conservative; reported, not gating).
- Per-cell p-values are the blocked-bootstrap two-sided achieved-significance level (fraction of bootstrap
  interaction draws on the far side of 0), consistent with the frozen script.
The generational verdict (§5) is read on the **BH-surviving** cells; the raw-CI reading is reported too.

## 5. PRE-REGISTERED VERDICTS (ex-ante success / kill, both directions reportable)

Let the modern-UIP arms be **MP-gen** (n = N_MP) and **OMat-gen** (n = N_OMat), each a set of `I_m` with
blocked-bootstrap CIs, after §3 inclusion and §4 BH survival.

### V1 — Distributional oxide-anchoring in the MP generation (strengthens the headline)
- **CONFIRMED** iff `I_m` is **positive and CI-excludes-0** (oxide value-of-abstention > halide) in
  **≥ 60%** of MP-gen UIPs; secondary read: oxide is the **arg-max-gain stratum** in ≥ 60% of MP-gen UIPs.
- **WEAKENED** iff 30–60%. **FAILED** iff < 30% (would undercut the headline; reportable).

### V2 — Generational dissolution / reversal (the real win, retires limitation (ii))
Define per model: `positive-anchored(m)` = `I_m > 0 and excl0(m)`; `reversed(m)` = `I_m < 0 and excl0(m)`;
`null(m)` = not `excl0(m)`.
- **CONFIRMED-DISSOLUTION** iff oxide-anchoring holds (V1 CONFIRMED in MP-gen) **AND** in OMat-gen the
  anchoring **dissolves or reverses**: `positive-anchored` in **≤ 40%** of OMat-gen UIPs
  (equivalently, `null ∪ reversed` in ≥ 60%).
- **CONFIRMED-REVERSAL (stronger)** iff additionally `reversed(m)` in **≥ 40%** of OMat-gen UIPs (the
  Orb-v3 sign-flip is systematic, not idiosyncratic).
- **NO-GENERATIONAL-EFFECT (honest null)** iff oxide-anchoring holds at similar rates in both arms
  (|MP-frac − OMat-frac| < 20 pp). This **would falsify** the "generation changed the reliability
  structure" reading and is to be reported **first and plainly** if it obtains.
- **IDIOSYNCRATIC-DISSENTER** iff OMat-gen is mostly still positive-anchored (> 60%) with only 1–2
  reversers: limitation (ii) stays as-is (Orb-v3 is a one-off), reported honestly.

### V3 — Formal between-generation test (single number, no cherry-picking)
Model-level two-sided **permutation test** on the generation label: statistic = mean(`I_m`, MP-gen) −
mean(`I_m`, OMat-gen), null = 10,000 random relabelings of the generation tag across the included UIPs,
seed 20260713. Report the observed gap, permutation p, and a bootstrap CI of the gap. **Significant**
generational difference iff permutation p < 0.05. (This is the powered replacement for "3 of 4 vs 1 of 4".)

### Kill switch (whole lever)
If, after §3, **N_OMat < 5** included OMat-gen UIPs (insufficient power) the generational verdict is
declared **UNDERPOWERED** and only V1 (MP distributional) is reported. Given ≈ 17 OMat-gen files this is
not expected, but is fixed here to avoid a post-hoc power excuse.

## 6. Shuffle-null hygiene (must hold for any V-verdict to count)

Permuting `|hull_pred_m|` within each stratum's called-stable set must collapse the interaction to
**≤ 5%** CI-exclude-0 false positives across the whole N_incl × 15 family (same rule as the frozen
scripts). A dirty shuffle-null voids the run.

## 7. Outputs (frozen destinations)

- Converted roster preds → `~/mt_uip_roster25/{model}_pred.csv`; data manifest →
  `results_expansion_2026-07-13/ROSTER25_DATA_MANIFEST.json`.
- Expanded audit → `results_expansion_2026-07-13/` (matched-yield + prototype-blocked CIs +
  multiplicity + SSCS + the two-arm generational contrast) and `RESULTS-ROSTER-EXPANSION.md` with the
  V1/V2/V3 verdicts stated prominently and honestly (null stated first if it obtains).
- **No manuscript file is touched** — integration is a later, separate pass.
