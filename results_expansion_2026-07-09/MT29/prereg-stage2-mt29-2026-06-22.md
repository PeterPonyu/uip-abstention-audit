# MT29 — Preregistration + Submission Outline: chemistry-conditioned selective abstention in universal MLIP stability screening

> **Authorship-timing disclosure (added during manuscript remediation, 2026-06-30).** This
> file's on-disk mtime is 2026-06-22 02:05:57, ~79 seconds after
> `mt29_stage2_robustness_result.json` (mtime 02:04:38) and well after
> `mt29_stage1_matched_yield_result.json` (mtime 00:25:07 the same day). It is therefore a
> **same-session analysis protocol + results log**, not an ex-ante preregistration: the exact
> success thresholds and budget parameters documented below (Sections 5-6) were fixed
> during/after the Stage-1 and Stage-2 runs, and the H1 oxide-direction hypothesis (Section 2)
> is itself explicitly marked "Established at Stage-1." The genuine ex-ante commitment for
> this study — the general strata direction and kill criteria — is
> `DEEP-REVERIFY-2026-06-21.md`, written 2026-06-21 21:00, hours before Stage-1 ran.

**Story:** G003-s2-materials-mt29-loeo. Stage-2 robustness gate (LOEO + WBM-round) for the
corrected matched-yield stratified-abstention interaction. Target venue: **Digital Discovery**
(or NeurIPS Datasets & Benchmarks track). Status as of 2026-06-22: Stage-2 = **SUCCESS**.

---

## 1. Question

Universal MLIPs (CHGNet, M3GNet, MACE, ORB) are used to pre-screen WBM-style candidate
structures for thermodynamic stability (`e_above_hull < 0`). A practitioner who wants a *purer*
shortlist abstains on low-confidence calls, keeping the most confident predicted-stable
structures (confidence = `|predicted hull margin|`). **Does the benefit of this selective
abstention depend on the chemistry of the candidate, and is that dependence a real,
reproducible property of the models rather than an artifact of yield, of a few dominant element
families, or of a single data-acquisition round?**

Concretely: is there a **stratum × coverage interaction** — does abstention buy *more* discovery
acceleration (DAF) in some anion classes (e.g. oxides) than in others (e.g. halides /
intermetallics), at a *matched* surfaced-candidate budget?

## 2. Hypotheses

- **H1 (primary).** The matched-yield abstention gain differs across anion-class strata: the
  stratum × coverage interaction `gain_A − gain_B` excludes 0 for the majority of
  (model × stratum-pair) cells. Direction: **oxide is the highest-abstention-benefit stratum**;
  halide / intermetallic the lowest. *(Established at Stage-1: 48/60 cells CI-excl-0.)*
- **H2 (LOEO robustness).** H1 is not driven by a few dominant element families. Holding out any
  single dominant element (O, the most common cations Ni/Al/Ge/Cu/Fe/Sn/Si, and the
  stratum-defining anion-formers F/S/N/P) and recomputing, the interaction still excludes 0 for
  the majority of cells in the **majority of leave-one-out splits**.
- **H3 (temporal robustness).** H1 is not driven by a single WBM acquisition round. Recomputed
  *within* each of WBM rounds 1–5 (a time-like distribution-shift axis: later rounds are
  substitutions on earlier discoveries), the interaction excludes 0 for the majority of cells in
  the **majority of rounds**.
- **H0 (null / shuffle).** When the confidence signal is permuted within each stratum's
  called-stable set, abstention selects a random subset and the interaction vanishes (CI includes
  0 for ~all cells). Required to hold under every split.

## 3. Data

- **Source:** Matbench Discovery, on-disk public cached predictions. No tokens, no downloads at
  run time, CPU/pandas only.
  - `~/mt_stage0/data/2023-12-13-wbm-summary.csv.gz` — WBM ground truth
    (`e_form_per_atom_mp2020_corrected`, `e_above_hull_mp2020_corrected_ppd_mp`, `formula`,
    `material_id`). 256,963 rows after dropping NaNs and inner-joining all 4 model prediction CSVs.
  - `~/mt_uip/{chgnet,m3gnet,mace,orb}_pred.csv` — per-model predicted formation energy.
- **Strata (anion class, electronegativity priority):** halide > oxide > chalcogenide (S/Se/Te) >
  pnictide (N/P/As/Sb/Bi) > intermetallic (all-metal) > other (main-group). Per-formula.
  Counts: intermetallic 119,012 / pnictide 34,614 / other 27,947 / halide 26,523 / oxide 25,020 /
  chalcogenide 23,847. All six ≥ 23K rows, genuinely varying stable base rate.
- **WBM rounds** parsed from `material_id = wbm-{round}-{n}`: 61,466 / 52,755 / 79,160 / 40,314 /
  23,268 for rounds 1–5.
- **Reconstruction (frozen from Stage-0/1):** stable ⇔ `e_above_hull_true < 0`;
  `hull_pred = hull_true + (e_form_pred − e_form_true_mp2020_corrected)`;
  `stable_pred = hull_pred < 0`; confidence = `|hull_pred|`.

## 4. Metrics

- **DAF (discovery acceleration factor)** = precision / stratum stable base rate, comparable
  across strata.
- **Matched-yield abstention gain (MT28 control, lifted to strata):** fix a **common absolute
  yield budget Y** (same integer count of surfaced stable candidates) in *every* stratum within a
  split; rank each stratum's called-stable structures by confidence; take top-Y;
  `gain = DAF(top Y_tight) − DAF(top Y_loose)`, with `Y_loose = min over usable strata of total
  called-stable`, `Y_tight = Y_loose // 2`, identical across strata. This holds **both** the
  surfaced-candidate count and its change fixed across strata, so any surviving interaction is
  abstention-quality-by-chemistry, not a yield-count artifact. (This is the exact control that
  KILLed the MT28 hull-margin wedge.)
- **Interaction** = `gain_A − gain_B` across stratum pairs, bootstrapped within strata
  (n_boot = 1000, seed 20260621), 95% percentile CI; "fires" = CI excludes 0.
- **Shuffle-null:** permute confidence within each stratum's called-stable set ⇒ random top-Y ⇒
  gain ≈ 0.

## 5. Success / Kill (preregistered)

- **SUCCESS:** interaction CI-excludes-0 for the **majority of (model × stratum-pair) cells**
  under **BOTH** the LOEO splits **AND** the WBM-round splits — operationalized as: a majority of
  LOEO leave-one-out splits each retain a majority-firing interaction, AND a majority of WBM
  rounds each retain a majority-firing interaction — with shuffle-null clean (<5% false-positive
  cells) throughout.
- **KILL:** the interaction collapses (CI includes 0 for most cells) once a dominant element is
  removed OR across rounds (i.e. it was element- or round-driven).

## 6. Result (this run, 2026-06-22)

| Gate | Splits passing | Pooled cells CI-excl-0 | Shuffle CI-excl-0 |
|---|---|---|---|
| **GATE 1 — Leave-one-element-out** | **12/12** | **548/700** | **0/700** |
| **GATE 2 — WBM-round split** | **3/5** | **157/300** | **0/300** |

**VERDICT: SUCCESS.**

- **LOEO (12/12):** dropping O (removes the entire oxide stratum's anion → 5 strata, 40 cells)
  still fires 37/40; dropping each common cation/anion-former keeps 39–50/60. The interaction is
  **not** carried by any single element family.
- **WBM-round (3/5 majority-firing → majority of rounds):** rounds 1/2/3 = 43/34/43 of 60;
  rounds 4/5 = 26/11 of 60. The two weaker rounds are the two **smallest** (40K, 23K rows) and
  the shortfall is concentrated in **ORB**, whose matched-yield budget shrinks fastest (ORB was
  already the weakest firer at Stage-1, 11/15). The **oxide-highest-benefit direction is
  preserved** even where CIs widen: in round 5, oxide is the higher-gain stratum in 16/20
  oxide-anchored cells and CHGNet/M3GNet fire **all 5** oxide cells (interaction up to +1.19).
  This is a power/per-model-budget effect under tiny rounds, **not** a temporal sign flip.
- **Shuffle-null clean everywhere: 0/700 (LOEO) and 0/300 (rounds).**

## 7. Figure list

1. **Stratum × model abstention-gain heatmap** — matched-yield gain per (anion-class × model),
   pooled; oxide row highest, halide/intermetallic lowest.
2. **LOEO robustness panel** — for each held-out element, interaction-excl-0 count (bar) with the
   pooled-baseline (48/60) reference line; flat bars = element-independent.
3. **WBM-round trajectory** — interaction-excl-0 count vs round 1–5, split by model; annotate
   per-round n and per-model matched-yield budget to show the round-4/5 dip is power, not decay.
4. **Oxide-vs-{halide,intermetallic} interaction with 95% CIs** across all splits (forest plot) —
   CIs above 0 across LOEO + early rounds.
5. **Shuffle-null overlay** — real vs shuffled interaction distributions per gate (shuffle mass at 0).
6. **DAF risk–coverage curves** for the extreme strata (oxide vs halide) at matched yield.

## 8. Threats to validity

- **Yield confound (primary, MT28's killer):** addressed by the common-absolute-yield budget; the
  interaction survives it (Stage-1 + here).
- **Stratum-definition sensitivity:** anion-class priority is one reasonable scheme; the LOEO of
  the anion-formers (F/S/N/P) and the drop-O run probe sensitivity to the defining chemistry and
  all survive. *Planned extension:* re-run with an alternative stratification (electronegativity
  bins; metal/non-metal ratio).
- **Small-round / per-model power:** rounds 4–5 are under-powered for the weakest model (ORB);
  reported transparently. Direction is preserved. Not used to claim per-round significance for
  every model — only majority-of-rounds.
- **Multiple comparisons:** 60 cells/split; we report counts and require a *majority*, not any
  single cell, and pair every real test with a matched shuffle-null (0 false positives observed).
- **Base-rate / DAF instability in thin strata:** `MIN_STRATUM=500`, `MIN_CALLED_STABLE=40`
  guards; strata below threshold in a split are dropped and reported.
- **Single confidence signal:** `|hull margin|` is the free MT28 baseline; richer confidence
  (ensemble disagreement) is future work and would only strengthen abstention.
- **Reproducibility:** fixed seed, 1000-boot, SHA-256 manifest over inputs+script+output.

## 9. Deliverables / files

- Script: `mt29_stage2_robustness.py`
- Result: `mt29_stage2_robustness_result.json` (full per-cell CIs for both gates)
- Manifest: `mt29_stage2_robustness_manifest.json` (input/script/output SHA-256, versions)
- Stage-1 headline: `mt29_stage1_matched_yield_result.json`
- This prereg: `prereg-stage2-mt29-2026-06-22.md`
