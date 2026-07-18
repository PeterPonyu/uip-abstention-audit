# MT29 — Findings: alternative-stratification robustness of the matched-yield abstention interaction

Date: 2026-07-02. Prereg: `PREREG-altstrat-2026-07-02.md`, committed **ex ante** at
**`66f078c78d1d27783383e7f3da104297a4099cad`** (`prereg: alt-stratification robustness ...`).
Every result JSON below carries `provenance.git_sha = 66f078c...` (the prereg commit), confirming
the runs post-date the preregistration. CPU only, seed 20260621, on-disk cached WBM + UIP preds,
no downloads. Statistics identical to `mt29_stage1_matched_yield_fix.py` (matched-yield DAF gain,
common absolute yield budget across strata); only the `family` column construction changed.

## Headline

The chemistry-dependence of the selective-abstention benefit **reproduces under both alternative
stratum definitions**, not just the single anion-priority rule. Overall verdict: **BOTH_ROBUST**
(both stratifiers SUCCESS per the preregistered rule). Shuffle-null was clean throughout
(0/40 CI-exclude-0 and 0 Holm rejections in each stratifier).

| Stratifier | strata (n) | cells | CI-excl-0 (heterogeneity) | CI-above-0 (anion-consistent dir.) | Holm survivors, correct dir. | shuffle CI-excl0 | Verdict |
|---|---|---|---|---|---|---|---|
| `electronegativity_q5` (mean-Pauling-EN quintiles) | 5 (q1-q5) | 40 | 31/40 | 6/40 | **5** | 0/40 | **SUCCESS** |
| `metal_fraction` (amount-weighted metal fraction) | 5 (mf1-mf5) | 40 | 24/40 | 14/40 | **13** | 0/40 | **SUCCESS** |

Preregistered SUCCESS = >=1 cell with interaction CI entirely above 0 (more-oxide-like stratum has
the higher matched-yield DAF abstention gain) **surviving Holm within-stratifier** (alpha=0.05,
m=40, hires p at N_BOOT=10000), shuffle-null clean. Both clear it with margin.

**Multiplicity:** Holm within each family used hires (B=10000) p-values so the m=40 rank-1
threshold 0.05/40 = 1.25e-3 is above the attainable p-floor (2/10001 = 2.0e-4) - Holm is not
resolution-limited. Secondary BH-FDR (q=0.05) across the pooled 80 cells: **18/80** rejections in
the anion-consistent direction (all shuffle families: 0 BH rejections).

## Definitions used

- `electronegativity_q5`: `mean_EN = sum n_i*X(el_i) / sum n_i`, amount-weighted, `X` = pymatgen
  `Element(sym).X` (Pauling; pymatgen 2026.5.4). Quintiles by `np.quantile`; realized edges
  ~ [0.798, 1.627, 1.759, 1.908, 2.213, 3.843]. **0** rows dropped for undefined EN (no noble-gas
  compounds). q5 = highest EN = most anion-like.
- `metal_fraction`: `metal_frac = sum_{metal} n_i / sum n_i`, metal iff pymatgen
  `Element(sym).is_metal` (metalloids B/Si/Ge/As/Sb/Te/Po/At -> non-metal - deliberately distinct
  from the anion rule's `METALS` set). Fixed bins mf1=[0,1/3) mf2=[1/3,1/2) mf3=[1/2,2/3)
  mf4=[2/3,1.0) mf5={1.0}. Bin sizes 17,753 / 42,835 / 43,612 / 45,306 / 107,457 - all >=
  MIN_STRATUM=500. mf1 = lowest metal fraction = most anion-like.

## metal_fraction - clean, monotonic, anion-consistent

mf1 (nonmetal-rich) is the clear high-abstention-benefit stratum: all 14 CI-above-0 cells and all
13 Holm survivors are mf1-anchored, with mf5 (96% intermetallic) the low-benefit end. Strongest
cells (MACE) reach interaction +0.51 to +0.59 (Holm-adj p = 8.0e-3). Composition check: mf1 is
32% oxide / 51% halide / 11% chalcogenide; mf5 is 96% intermetallic - i.e. lower metal fraction
maps onto the anion-rich, higher-benefit chemistry, the anion-family direction. 10/40 cells fire in
the opposite direction (mid-fraction pairs), none a top-vs-bottom contradiction.

## electronegativity_q5 - heterogeneity confirmed, direction non-monotonic at the extreme (honest wrinkle)

The EN quintiles strongly confirm **heterogeneity** (31/40 CI-exclude-0, shuffle 0/40) and the
anion-consistent direction survives Holm (5 cells: MACE/ORB/CHGNet q4-vs-q3/q2, MACE q5-vs-q3;
interaction up to +0.31, Holm-adj p 8.0e-3 to 4.2e-2). **But 25/40 cells fire in the opposite
(anti-anion) direction** - the EN ranking is not cleanly monotonic in abstention benefit. This is
explained, not contradicted, by chemistry: the top quintile q5 is **44% oxide + 40% halide**,
pooling the two anion classes the anion-family result identified as *opposite* extremes
(oxide = highest benefit, halide = lowest). q5's benefit is therefore diluted and the peak sits at
q4 (oxide-/chalcogenide-leaning) rather than q5. Mean electronegativity conflates "oxidizing anion
present" (oxide) with "most electronegative anion present" (fluoride/halide), so it is a **noisier**
proxy for the abstention-benefit axis than either the anion rule or metal fraction. We report the
25 anti-direction cells transparently; they do not overturn the preregistered SUCCESS (which
requires >=1 anion-consistent Holm survivor, met with 5), and the underlying heterogeneity is
unambiguous.

## Interpretation

Under two stratifiers that do **not** use the anion-priority ordering, the abstention-benefit
interaction is (i) strongly heterogeneous across strata and (ii) higher for the more anion-/oxide-
rich, less-metallic strata, surviving within-family Holm correction and a matched shuffle-null. The
metal-fraction stratifier is the cleaner corroboration (monotonic, 13 Holm survivors); the
electronegativity-quintile stratifier corroborates the heterogeneity and the anion-consistent
component but is non-monotonic at the extreme quintile for a chemically sensible reason (oxide/
halide pooling). Net: the chemistry-dependence is **not an artifact of the single anion-priority
classification rule**. This supports converting the manuscript's "planned extension" note in
Threats-to-validity into a reported robustness result.

## Files (provenance-stamped, none overwrites an existing JSON)

- `mt29_stage1_altstrat.py` - parameterized clone of `mt29_stage1_matched_yield_fix.py`.
- `mt29_stage1_altstrat_electronegativity_q5_result.json` (+ `_manifest.json`)
- `mt29_stage1_altstrat_metal_fraction_result.json` (+ `_manifest.json`)
- `mt29_altstrat_multiplicity.py` -> `mt29_altstrat_multiplicity_result.json` (+ `_manifest.json`)
- Prereg: `PREREG-altstrat-2026-07-02.md` (commit `66f078c`).
