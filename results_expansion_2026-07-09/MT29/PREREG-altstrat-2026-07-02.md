# MT29 — Preregistration: alternative-stratification robustness of the matched-yield abstention interaction

Date written: **2026-07-02, BEFORE running `mt29_stage1_altstrat.py`.** Author: ZeyuFu.
This file is committed to git **ex ante** (its introducing commit precedes any altstrat result
JSON); the introducing commit SHA is the proof-of-timing and is recorded in
`findings-altstrat-2026-07-02.md` after the runs.
Compute: CPU only (`CUDA_VISIBLE_DEVICES=""`), `/home/zeyufu/miniconda3/envs/dl/bin/python`,
on-disk cached Matbench-Discovery WBM preds
(`~/mt_uip/{chgnet,m3gnet,mace,orb}_pred.csv`, `~/mt_stage0/data/2023-12-13-wbm-summary.csv.gz`).
No GPU, no network downloads.

## Background / what is already fixed (not being re-litigated here)

The Stage-1 matched-yield control (`mt29_stage1_matched_yield_fix.py` →
`mt29_stage1_matched_yield_result.json`) reports **SUCCESS**: 48/60 (model × anion-stratum-pair)
matched-yield DAF abstention-benefit interactions CI-exclude-0, shuffle-null 0/60, **oxide the
highest-abstention-benefit stratum**, halide/intermetallic the lowest (Stage-2 LOEO + WBM-round
robustness in `prereg-stage2-mt29-2026-06-22.md`). That result uses **one** stratum definition:
the anion-class family by electronegativity priority (halide > oxide > chalcogenide > pnictide >
intermetallic > other), the `anion_family()` rule in `mt29_stage1_chem_yield.py`.

The manuscript's Threats-to-validity lists "re-run with an alternative stratification
(electronegativity bins; metal/non-metal ratio)" as a *planned extension*. This preregistration
converts that planned extension into two **new hypothesis families**, each with its own
success/kill rule and a multiplicity plan across the two families, per this repo's audit culture.
This is **reviewer insurance / robustness supplement**, not a headline change: the anion-family
result stands on its own; here we test whether the *chemistry-dependence of abstention benefit*
reproduces when the strata are drawn by two rules that do **not** use the anion-priority ordering.

## Question

Is the stratum × coverage matched-yield abstention-benefit interaction a property of the
**chemistry** of the candidate set, reproducible under alternative principled stratum definitions,
or an artifact of the single anion-priority classification rule?

## Two new hypothesis families (stratifiers)

Both stratifiers reuse the **identical** statistic, seed, and matched-yield discipline as
`mt29_stage1_matched_yield_fix.py` (see "Statistics" below); only the `family` column construction
changes. Composition is parsed from the WBM `formula` column (space-separated integer counts, e.g.
`"Ac6 U2"`) with the existing `TOKEN_RE = ([A-Z][a-z]?)(\d*)`; `n_i` = stoichiometric amount of
element `i` (missing count ⇒ 1).

### (a) `--stratifier electronegativity_q5` — mean Pauling electronegativity quintiles

- **Averaging rule (exact):** composition-weighted mean Pauling electronegativity
  `mean_EN = ( Σ_i n_i · X(el_i) ) / ( Σ_i n_i )`, the amount-weighted arithmetic mean over the
  elements present in the formula.
- **Electronegativity source (exact):** `pymatgen.core.Element(sym).X` — the Pauling-scale value
  shipped in pymatgen (installed version 2026.5.4). Values are cached per symbol.
- **Undefined-EN rule:** elements with no defined Pauling `X` (the noble gases He/Ne/Ar/Kr/Xe/Rn,
  for which pymatgen returns NaN) make `mean_EN` undefined; any row containing such an element is
  **dropped** and the dropped count reported. (Marginal check during design: **0** such rows in the
  256,963-row set, so no rows are expected to drop; the rule is fixed ex ante regardless.)
- **Strata (exact):** quintiles of `mean_EN` by `np.quantile` at `[0, .2, .4, .6, .8, 1.0]` over
  the retained rows, giving 5 strata `q1..q5`. **q5 = highest mean-EN = most anion-/oxide-like**;
  q1 = lowest = most metallic. (Realized edges are covariate quantiles, outcome-independent; the
  design-time marginal was ≈ [0.797, 1.627, 1.759, 1.907, 2.213, 3.843], each quintile ≈ 51k rows.
  The **rule** — equal-count quintiles — is fixed ex ante; realized edges are recorded in results.)

### (b) `--stratifier metal_fraction` — metal-fraction bins

- **Metal fraction (exact):** `metal_frac = ( Σ_{i: metal} n_i ) / ( Σ_i n_i )`, the amount-weighted
  fraction of the formula that is metal.
- **Metal/nonmetal classification (exact):** an element is a **metal** iff
  `pymatgen.core.Element(sym).is_metal` is `True`. This treats the metalloids
  (B, Si, Ge, As, Sb, Te, Po, At) and all true nonmetals as **non-metal** — a standard
  periodic-table convention that is **deliberately distinct** from the anion-priority rule's
  hand-rolled `METALS` set (which lumps metalloids with metals). This independence from the
  anion rule is the whole point of the robustness test.
- **Bin edges (fixed, ex ante):** five bins on `metal_frac ∈ [0, 1]`:
  `mf1 = [0, 1/3)`, `mf2 = [1/3, 1/2)`, `mf3 = [1/2, 2/3)`, `mf4 = [2/3, 1.0)`, `mf5 = {1.0}`
  (exactly pure-metal). Breaks are the round a-priori fractions 1/3, 1/2, 2/3 plus a distinguished
  pure-metal bin; they are **not** tuned to any outcome. **mf1 = lowest metal fraction = most
  anion-/oxide-like**; mf5 = pure metal = intermetallic-like. (Design-time marginal bin sizes:
  33,832 / 26,756 / 65,644 / 23,274 / 107,457 — all ≥ `MIN_STRATUM`.)

## Statistics (identical to `mt29_stage1_matched_yield_fix.py`)

- STABLE ⇔ `e_above_hull_true < 0`; `hull_pred = hull_true + (e_form_pred − e_form_true_mp2020_corrected)`;
  `stable_pred = hull_pred < 0`; confidence = `|hull_pred|`.
- **DAF** = precision / stratum stable base-rate. **Matched-yield gain** per stratum =
  `DAF(top Y_tight) − DAF(top Y_loose)`, where the top-Y is the Y most-confident **called-stable**
  structures of the stratum, `Y_loose = min over usable strata of total called-stable (per model)`,
  `Y_tight = max(1, Y_loose // 2)` — a **common absolute yield budget across strata** (the exact
  MT28 control). Per model.
- **Interaction** for stratum-pair `(A, B)` = `gain_A − gain_B`, bootstrapped **within** each
  stratum's called-stable set, `N_BOOT = 1000`, seed `20260621`, 95% percentile CI. A cell =
  one (model × stratum-pair). Strata are ordered **most-oxide-like → least**
  (EN: `[q5,q4,q3,q2,q1]`; metal-frac: `[mf1,mf2,mf3,mf4,mf5]`) and the interaction of each pair
  `(A, B)`, i<j, is `gain_A − gain_B` with **A the more-oxide-like** stratum.
- **Same direction as the anion-family result** (oxide = highest abstention benefit) is
  operationalized as: the interaction CI lies **entirely above 0** (`ci95_low > 0`), i.e. the
  more-oxide-like / higher-EN / lower-metal-fraction stratum has the **higher** matched-yield DAF
  abstention gain.
- **Shuffle-null:** permute confidence within each stratum's called-stable set (random top-Y),
  recompute the interaction; expected to collapse to ~0 CI-exclude-0.
- **p-values (for multiplicity):** two-sided bootstrap sign p on the paired gain-difference `d`,
  `p = min(1, 2·min[(1+#{d≤0})/(L+1), (1+#{d≥0})/(L+1)])`, computed at `N_BOOT_HIRES = 10000`.
  **Reason it must be hires:** Holm within a ≤40-cell family needs `p < 0.05/40 = 1.25e-3`; the
  attainable two-sided p-floor is `2/(B+1)`, which at `B=1000` is `2.0e-3 > 1.25e-3` and would
  mechanically zero Holm regardless of effect size. At `B=10000` the floor is `2.0e-4 < 1.25e-3`,
  so Holm is not resolution-limited. (Same construction as `mt29_multiplicity_correction.py`.)

## Min-n rule (declared ex ante)

- `MIN_STRATUM = 500` rows per stratum; `MIN_CALLED_STABLE = 40` called-stable per model per
  stratum (matches `mt29_stage2_robustness.py`). For a given model, a stratum below either
  threshold is **dropped from that model's pairs** and reported; a model needs **≥ 2 usable
  strata** to contribute any pair. Stratum sizes and the usable set are **printed and stored**.
- A stratifier that ends with **< 1 usable (model × pair) cell** is declared **UNINFORMATIVE**
  (cannot be tested), not a pass and not a falsification.

## Success / Kill / Uninformative (per stratifier, preregistered)

For each stratifier family separately (m = its cell count, ≤ 40):

- **SUCCESS** iff **≥ 1 cell** has its interaction CI **entirely above 0** (same direction as the
  anion result) **AND** that cell **survives Holm-Bonferroni within this stratifier**
  (Holm-adjusted p < 0.05, FWER α = 0.05, over this family's m cells, hires p-values) **AND** the
  stratifier's shuffle-null is clean (≤ 5% of its shuffle cells CI-exclude-0).
- **KILL** iff **0 cells** have a CI entirely above 0 in the correct direction — the
  chemistry-dependence does **not** reproduce under this stratum definition (an honest
  falsification for this stratifier; reported as such).
- **UNINFORMATIVE** iff ≥ 1 cell fires in the correct direction but **none survives Holm**
  within-stratifier, OR the shuffle-null is dirty (> 5%), OR < 1 usable cell. Reported as
  inconclusive — neither a pass nor a falsification.

The two-sided Holm/BH tests are combined with the **directional** requirement (CI above 0): a cell
counts toward SUCCESS only if it is both Holm-significant and in the anion-consistent direction.

## Multiplicity plan (across the two stratifier families)

- **PRIMARY (gating):** **Holm-Bonferroni within each stratifier family separately**
  (`relmetrics.multiplicity.holm_bonferroni`, α = 0.05, m = that family's cell count), on the
  hires p-values. This is the family-wise error control that gates each stratifier's SUCCESS.
- **SECONDARY (reported alongside, non-gating):** **Benjamini-Hochberg FDR (q = 0.05)** across the
  **pooled** two families (`relmetrics.multiplicity.benjamini_hochberg`, m = 40 + 40 = 80 cells),
  controlling the false-discovery rate over the entire altstrat hypothesis set. Reported next to
  the Holm outcome for every cell.
- Shuffle-null families receive the identical Holm + BH treatment (expected: 0 rejections).

## Overall reading across the two stratifiers (honest, non-gating)

- Both SUCCEED ⇒ the chemistry-dependence of abstention benefit is **robust to the stratum
  definition** (not an anion-priority artifact) — the intended reviewer-insurance outcome.
- One SUCCEEDs, one KILL/UNINFORMATIVE ⇒ reported as **partial** robustness with the exact failing
  stratifier named; the anion-family headline is unchanged either way.
- Both KILL ⇒ reported honestly as evidence the effect is **specific to the anion-priority
  stratification**; the manuscript's Threats-to-validity is updated to say so.

No outcome is privileged in advance; a null under either stratifier is a reportable result, not a
reason to re-tune the stratifier.

## Deliverables / files

- Prereg (this file): `research/results/MT29/PREREG-altstrat-2026-07-02.md` (committed ex ante).
- Script: `research/results/MT29/mt29_stage1_altstrat.py` (`--stratifier {electronegativity_q5,metal_fraction}`).
- Per-stratifier results: `mt29_stage1_altstrat_<stratifier>_result.json` (+ `_manifest.json`),
  provenance-stamped via `relmetrics.provenance.stamp_result`. Existing result JSONs are **never**
  overwritten.
- Multiplicity: `research/results/MT29/mt29_altstrat_multiplicity.py` →
  `mt29_altstrat_multiplicity_result.json` (+ manifest) — Holm within each family, BH across both.
- Findings: `research/results/MT29/findings-altstrat-2026-07-02.md` (states only what the JSONs
  support, including honest reporting of any null stratifier; records the prereg commit SHA).
