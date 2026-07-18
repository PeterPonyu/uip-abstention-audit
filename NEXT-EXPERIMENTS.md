# NEXT-EXPERIMENTS — deferred items too expensive/blocked for the 2026-07-02 depth pass

Each item below was selected from the 2026-07-02 portfolio review
(`portfolio-review-2026-07-02.json`, materials-mlip entry: `depth_expansion`,
`gap_to_submission`, `risks`) but exceeds the depth-pass budget (>~20 min CPU, GPU,
network bulk transfer, or external credentials). Completed depth items (budget-ratio
sweep, BH/Holm multiplicity correction, B5b policy reconciliation, figure-pipeline
dedup) are NOT listed here — see `research/results/MT29/` and git log for those.

---

## 1. Add >=1 OAM-era 2025-26 UIP via frozen inference (eSEN-30M-OAM or SevenNet-MF-ompa)

**What:** Run frozen (no-training) inference of one modern UIP over the 256,963 WBM
structures, write `~/mt_uip/<model>_pred.csv` in the same schema as the existing four
(`material_id, e_form_pred`), then re-run `mt29_stage1_matched_yield_fix.py` and
`mt29_stage2_robustness.py` with the model added to `MODELS`.

**Why (review):** "The audited UIPs are the 2023-24 generation (F1 0.57-0.86) while the
live leaderboard tops F1~0.93; a 'results may not hold for modern models' objection is
likely." Listed as insurance for the JCIM submission ("item 7" in gap_to_submission).

**Estimated cost:** GPU (RTX 5090 per FABLE-HANDOFF §7), several hours of inference over
257k structures + model checkpoint download (~1-30 GB). Blocked here: no GPU budget in the
depth pass and network bulk download.

**Command sketch (when unblocked):**
```bash
# adapt ~/mt_uip/mt_v2_modern_uip.py (existing frozen-inference harness for the 4 cached UIPs)
python ~/mt_uip/mt_v2_modern_uip.py --model esen-30m-oam \
    --wbm ~/mt_stage0/data/2023-12-13-wbm-summary.csv.gz --out ~/mt_uip/esen_pred.csv
# then add 'esen' to MODELS in research/results/MT29/mt29_stage1_chem_yield.py and re-run:
python3 research/results/MT29/mt29_stage1_matched_yield_fix.py
python3 research/results/MT29/mt29_stage2_robustness.py
python3 research/results/MT29/mt29_multiplicity_correction.py stage1
```

## 2. Convex-hull recompute to bound the fixed-hull approximation (validation subset)

**What:** For a stratified random subset (e.g. 5k structures, all six anion families),
rebuild the MP patched phase diagram with pymatgen and recompute e_above_hull_pred from
each model's predicted formation energies, instead of the fixed-hull shortcut
`hull_pred = hull_true + (e_form_pred - e_form_true)`. Report the distribution of
(fixed-hull minus true-hull) prediction differences per stratum and whether any Stage-1
cell flips excl-0 status.

**Why (review):** "Predicted hull distance is a fixed-hull approximation ... absolute
numbers could shift on full recompute (acknowledged in FABLE-HANDOFF §5)"; gap item 9
calls a validation-subset recompute "cheap insurance" for review.

**Estimated cost:** Network download of the MP2020-compatible entries (matbench-discovery
`mp_computed_structure_entries` ~1-2 GB) + ~1-3 h CPU for PatchedPhaseDiagram construction
and 5k x 4 model hull queries. Blocked here: bulk network read + over CPU timebox.

**Command sketch:** new script `research/results/MT29/mt29_hull_recompute_validation.py`
using `matbench_discovery.data.DataFiles.mp_patched_phase_diagram` (cache dir
`~/.cache/matbench-discovery`), seed 20260621, stratified sample, SHA-256 manifest.

## 3. Push the git baseline off-disk (remote + Zenodo DOI)

**What:** Create a private remote (GitHub/GitLab), `git push --tags origin master`, and
archive a release tarball to Zenodo/Figshare for a DOI to cite in the JCIM data-availability
statement.

**Why (review):** "No remote exists — pushing the baseline somewhere off-disk is the single
highest-value follow-up for durability"; "a disk mishap loses the byte-reproducibility
evidence." (Also gap item 2: external reproducibility + DOI.)

**Estimated cost:** minutes, but blocked here: requires network + account credentials the
depth pass does not have.

**Command sketch:**
```bash
cd /home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research
git remote add origin <URL> && git push -u origin master --tags
```

## 4. Alternative stratifications (electronegativity bins, metal/nonmetal ratio, prototypes)

**What:** Re-run the Stage-1 matched-yield interaction under 2-3 alternative stratum
definitions to show the chemistry-dependence is not an artifact of the single
anion-priority rule. Each run is ~1-2 min CPU on the cached CSVs; the blocking cost is
design + prereg hygiene (each new stratifier is a new hypothesis family and should be
committed ex ante with its own success/kill rule, per this repo's audit culture), plus a
multiplicity plan across stratifiers.

**Why (review):** depth_expansion: "Test alternative stratifications ... beyond the single
anion-priority rule — listed as planned in Threats to validity." The paper still says
"planned extension."

**Estimated cost:** ~0.5 day including prereg + analysis + write-up (not a <20-min fix).

**Command sketch:** clone `mt29_stage1_matched_yield_fix.py` -> parameterize the
`family` column construction (e.g. mean-Pauling-electronegativity quintiles from the
formula; metal fraction bins); write prereg md first; then
`python3 mt29_stage1_altstrat.py --stratifier electronegativity_q5`.

## 5. Mondrian/split conformal stability classifier (per-stratum finite-sample coverage)

**What:** Implement the real split/Mondrian conformal classifier for the stable/unstable
decision (calibration half / test half, per-anion-family Mondrian groups), reporting
per-stratum empirical coverage vs the SSCS miscalibration table already in the paper.
`relmetrics.conformal.MondrianConformal` (reliability-commons) provides the machinery.

**Why (review):** depth_expansion: "Implement the real split/Mondrian conformal stability
classifier ... the SSCS table already shows per-chemistry miscalibration and
mt_v28_conformal_calibration.py is acknowledged as mislabeled." Also flagged in
DEEP-REVERIFY §2 as an open, uncontested seam (possible standalone MLST paper).

**Estimated cost:** CPU-cheap to run (~minutes) but a new contribution requiring its own
prereg, calibration-split design, and a manuscript section (or separate paper) — beyond a
depth-pass fix. ~1-2 days honest work.

## 6. Venue packaging for JCIM (achemso template, BibTeX, ToC graphic, SI, cover letter)

**What:** Convert `manuscripts/paper.tex` from generic article class + inline
thebibliography to ACS `achemso`, move LOEO/round detail to Supporting Information, add ToC
graphic and a cover letter positioning against Proof-Carrying Materials (arXiv:2603.12183,
global non-stratified AUC only), and a provenance note for the halide DAF 4.42->3.01
correction.

**Why (review):** gap_to_submission item 8; journal recommendation replaces Digital
Discovery (ESCI, APC) with JCIM (SCIE Q1, hybrid, no APC).

**Estimated cost:** mechanical, ~1 day of writing/formatting; not an analysis fix, so out
of scope for the depth pass.

---

## Implementation status (2026-07-08 pass — harnesses only, not yet run)

Items **1** and **2** now have fully implemented, pytest-covered code
(`python -m pytest` green, 51 tests) that was NOT runnable in that pass's CPU-only,
network-free sandbox. Nothing below has produced a real result JSON yet — every test
uses synthetic/toy fixtures or hand-checkable systems, never real WBM/MP data or a real
checkpoint. See `RUNME_CONTAINER.md` for the exact AutoDL 4090D run sequence still
needed to turn these into real results.

- **Item 1 (OAM-era UIP):** `research/results/MT29/mt29_uip_inference.py` (Arm 1a —
  frozen-inference harness; model registry for `esen-30m-oam` [gated,
  `REQUIRES_USER_CHECKPOINT` guard] / `sevennet-mf-ompa` [un-gated fallback]) and
  `research/results/MT29/mt29_stage1_oam_arm.py` (Arm 1b — hooks any discovered
  OAM-era `*_pred.csv` into the existing corrected matched-yield pipeline, writing a
  NEW `mt29_stage1_oam_arm_result.json`; never touches the frozen canonical
  `mt29_stage1_chem_yield.py`/`mt29_stage1_matched_yield_fix.py` or their results).
  Still needed: GPU + the gated checkpoint (or the un-gated SevenNet fallback) +
  reference-energy table, all on the container.
- **Item 2 (hull recompute):** `research/results/MT29/mt29_hull_math.py` (Arm 2a —
  pure numpy/scipy convex-hull-recompute math, no pymatgen dependency, unit-tested on
  hand-checkable binary/ternary toy systems) and
  `research/results/MT29/mt29_hull_recompute_validation.py` (Arm 2b — stratified
  5k-structure validation-subset recompute against MP reference entries, reporting
  fixed-vs-recomputed hull deltas and stable-call flips per stratum/model; writes a
  NEW `mt29_hull_recompute_validation_result.json`). Still needed: network + pymatgen
  + matbench-discovery + ~1-3 h CPU on the container (`fetch_data.sh`).
- **Not attempted this pass:** items 3 (git remote/Zenodo push), 4 (alternative
  stratifications — separately already landed as `mt29_stage1_altstrat.py`, see git
  log), 5 (Mondrian conformal), 6 (JCIM packaging).
