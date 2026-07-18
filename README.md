# materials-mlip-research (MT29)

Code archive: Zenodo DOI 10.5281/zenodo.21130295 (reserved; draft record, activates on publish).

**The chemistry-stratified value of selective abstention for machine-learned crystal-stability prediction.**

Motif: *low regression error ≠ reliable decision.* A reliability/calibration/extrapolation
audit of ML interatomic potentials (MLIP/UIP) for materials informatics, built entirely on
the ready-made, auditable Matbench Discovery benchmark.

## Thesis

This is a CPU-only, real-data audit of *frozen* Matbench Discovery predictions (four ML
interatomic potentials — CHGNet, M3GNet, MACE, ORB — on n = 256,963 WBM structures; no
model is trained and no DFT is run). The core claim: the benefit of confidence-based
selective abstention (confidence = |predicted hull margin|) for the binary "is this crystal
stable" decision is strongly **chemistry-dependent** — oxides gain the most discovery
acceleration, halides and intermetallics essentially none — and this stratum-by-coverage
interaction is not an artifact of surfaced-candidate yield, dominant elements, acquisition
round, single-model quirks, or chance (matched-yield, leave-one-element-out, WBM-round,
committee-variance, and shuffle-null controls, with formal BH-FDR / Holm multiplicity
correction). A secondary result shows the native-Gaussian probability reading of the same
margin is optimistic in every anion family.

## Repository layout

```
paper (manuscripts/)
  paper.tex, paper.pdf     # the submission draft (compiles via LuaLaTeX); superseded paper.md kept for history
  figures/                 # F1-F5 PNG+PDF; render_figures.py + F5_committee_variance.py are the CANONICAL generators
  figures/deprecated_R_pipeline/  # retired R/ggplot2 generators (kept for provenance; NOT runnable — external ggtheme.R vanished)

analysis (research/results/MT29/)
  mt29_stage0_*.py          # Stage-0 precursor gate
  mt29_stage1_chem_yield.py # CANONICAL loader + strata + abstention metrics (imported by most others)
  mt29_stage1_matched_yield_fix.py, mt29_stage2_robustness.py
  mt29_stage1_yield_ratio_sensitivity.py  # budget-ratio sweep
  mt29_multiplicity_correction.py         # BH-FDR / Holm (stage1|stage2), re-asserts frozen reproduction
  mt29_committee_variance.py, mt29_sscs_stratified.py
  mt29_crossgen_reliability_*.py, mt29_b5_policy_spike.py, mt29_b5b_knapsack_*.py  # secondary / negative results
  *_result.json            # FROZEN headline results (numbers in the paper trace here)
  *_manifest.json          # SHA-256 manifests over inputs/script/output, seed 20260621, n_boot 1000

other
  research/                 # direction bank, audits, findings, plans (incl. killed siblings)
  DATA_MANIFEST.md          # external input files + SHA-256 checksums
  NEXT-EXPERIMENTS.md       # deferred (GPU / network / scope) work
  requirements.txt, CITATION.cff, LICENSE, smoke_test.sh, tests/
```

## How to reproduce

### 1. Environment

Python 3.13 (tested). The entire headline MT29 pipeline + figures needs only five
third-party packages plus the local `relmetrics` sibling:

```bash
pip install -r requirements.txt
pip install -e ../reliability-commons     # provides relmetrics.multiplicity / relmetrics.provenance
```

(GPU molecular-dynamics probes under `research/mt_gpu_*.py` and `research/mt23_meep_invcrime.py`
additionally need `ase`, `torch`, `meep`; these are optional and not needed for any paper number.)

### 2. Data (lives outside the repo)

Input data are **not** redistributed here. They are the public Matbench Discovery
prediction/summary CSVs (free Figshare mirror,
<https://matbench-discovery.materialsproject.org/>). See **DATA_MANIFEST.md** for the exact
files, sizes, and SHA-256 checksums. The upstream download command is not recorded in repo
history (do not invent one); obtain the listed files from the upstream source, then point the
scripts at them with two environment variables:

```bash
export MT_DATA_ROOT="$HOME/mt_stage0/data"   # dir holding 2023-12-13-wbm-summary.csv.gz (WBM ground truth)
export MT_UIP_ROOT="$HOME/mt_uip"            # dir holding {chgnet,m3gnet,mace,orb}_pred.csv
```

Both default to the original `~/mt_stage0/data` and `~/mt_uip` paths, so on the original
machine no export is needed. Verify integrity against the checksums in DATA_MANIFEST.md.

### 3. Smoke test (no data required, < 2 min)

```bash
bash smoke_test.sh
```

Checks that the dependency stack imports, the canonical analysis module imports data-free and
its core helpers run on a tiny fixture, and the frozen result JSONs parse with expected keys.

### 4. Run order (regenerate result JSONs)

Run from `research/results/MT29/` (scripts import each other by local module name):

```bash
cd research/results/MT29
python mt29_stage1_chem_yield.py            # -> mt29_stage1_chem_yield_result.json
python mt29_stage1_matched_yield_fix.py     # -> mt29_stage1_matched_yield_result.json
python mt29_stage2_robustness.py            # -> mt29_stage2_robustness_result.json
python mt29_stage1_yield_ratio_sensitivity.py
python mt29_multiplicity_correction.py stage1
python mt29_multiplicity_correction.py stage2
python mt29_committee_variance.py
python mt29_sscs_stratified.py
# secondary: mt29_crossgen_reliability_exec_2026_06_29.py, mt29_b5_policy_spike.py, mt29_b5b_knapsack_constrained-exec-2026-06-29.py
```

Each writes a `*_result.json` plus a `*_manifest.json`; the multiplicity script re-asserts
byte-identical reproduction of the frozen inputs before attaching corrected p-values.

### 5. Figures

Generated **only** from the on-disk result JSONs (no hardcoded data arrays):

```bash
python manuscripts/figures/render_figures.py         # F1-F4 (PNG+PDF)
python manuscripts/figures/F5_committee_variance.py  # F5
```

Note: the figure/analysis scripts currently hardcode the repository's absolute path
(`/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/...`) for their
repo-internal result/output locations; an external reproducer cloning elsewhere must adjust
those constants (a known packaging limitation, distinct from the MT_DATA_ROOT input
abstraction above).

### R

The manuscript uses **no** R. Historical R/ggplot2 figure generators live in
`manuscripts/figures/deprecated_R_pipeline/` for provenance only and are **not runnable**
(they depend on an external `ggtheme.R` that is no longer present). Python is the single
canonical figure pipeline.

## Honest status

- **Maturity ~85% of a submittable journal paper.** All headline numbers are traceable to
  frozen `research/results/MT29/*.json`, with SHA-256 manifests and an independently
  re-run byte-identical reproduction recorded 2026-07-01.
- **Fixed-hull approximation:** predicted hull distance = true hull + signed formation-energy
  error, not a full convex-hull recompute; absolute DAF numbers could shift on a full
  recompute (validation subset deferred — see NEXT-EXPERIMENTS.md).
- **2023-24-generation UIPs:** an OAM-era (2025-26) model refresh via frozen inference is
  deferred (NEXT-EXPERIMENTS.md), to pre-empt a "stale models" objection.
- **Killed / negative siblings are kept, not hidden:** MT28 calibration wedge (0/12 kill),
  rank-fragility null (tau=1.0), MT4 NVE drift, V6 disagreement, and the falsified B5b
  stratum-aware knapsack allocator (strictly worse than the global threshold, folded into the
  Discussion). These are documented in `research/` and the audit trail; do not cite them as
  positive results.
- **No mock/synthetic contamination:** this is a real-data audit (FABLE-HANDOFF.md). The only
  unusable artifact is an aborted 0-byte `2024-08-04-wbm-initial-atoms.extxyz.zip` download
  noted in DATA_MANIFEST.md — not used anywhere.
- `manuscripts/paper.md` is a **superseded** markdown draft (kept for history); `paper.tex`
  is authoritative.

## Broader direction bank

The wider MLIP reliability program (MT1-MT4: classification-vs-regression mismatch near the
0 eV/atom hull boundary, calibrated abstention, WBM 5-step OOD degradation, energy-conservation
of direct-force models, leaderboard leakage/memorization) is catalogued in
[`research/materials-mlip-direction-bank.md`](research/materials-mlip-direction-bank.md).
Isolation / boundaries / resource notes: [`AGENTS.md`](AGENTS.md).

## Provenance / discipline

Results change **only** by re-running analysis code; no result JSON is ever hand-edited and no
figure is drawn from hardcoded numbers. See DATA_MANIFEST.md, the `*_manifest.json` files,
`DEEP-REVERIFY-2026-06-21.md`, and `research/audits/` for the full audit trail.
