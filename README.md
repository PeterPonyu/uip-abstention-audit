# materials-mlip-research (MT29)

Code archive: Zenodo DOI 10.5281/zenodo.21130295 (published and openly accessible).

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
  paper.tex, paper.pdf     # canonical manuscript source and compiled PDF
  jcp/                     # REVTeX source, cover letter, and verified source package
  figures/                 # F1–F5 PDF/PNG and their canonical R generators
  figures-src/             # TikZ source for the protocol overview

analysis (research/results/MT29/)
  mt29_stage0_*.py          # Stage-0 precursor gate
  mt29_stage1_chem_yield.py # canonical loader, strata, and abstention metrics
  mt29_stage1_matched_yield_fix.py, mt29_stage2_robustness.py
  mt29_stage1_yield_ratio_sensitivity.py
  mt29_multiplicity_correction.py
  mt29_committee_variance.py, mt29_sscs_stratified.py
  *_result.json            # frozen result records used by the manuscript
  *_manifest.json          # input/script/output SHA-256, seed, and bootstrap count

other
  relmetrics/               # vendored MIT-licensed multiplicity/provenance helpers
  DATA_MANIFEST.md          # external input files and SHA-256 checksums
  requirements.txt, CITATION.cff, LICENSE, smoke_test.sh, tests/
```

## How to reproduce

### 1. Environment

Python 3.13 was used for the frozen analysis. Install the pinned third-party dependencies:

```bash
python -m pip install -r requirements.txt
```

The two `relmetrics` modules used by the analysis are vendored under `./relmetrics/` with their
MIT license and provenance note, so the public release does not depend on a sibling checkout.
Figure regeneration additionally requires R with `jsonlite`, `ggplot2`, `patchwork`, and `ragg`.

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

The checked-in figures are generated from the frozen result JSONs by the R scripts
`manuscripts/figures/F1_daf_coverage.R` through `F5_committee_variance.R`. The protocol overview
is built from `manuscripts/figures-src/fig0_overview.tex`.

```bash
make -C manuscripts figures
```

## Scope and limitations

The analysis uses public Matbench Discovery prediction files whose filenames, sizes, and SHA-256
values are recorded in `DATA_MANIFEST.md`; these external inputs are not redistributed. The
fixed-hull reconstruction is validated for the reported stability calls, while the deeper
assumption that competing hull phases are unaffected by UIP errors remains outside scope. The
manuscript reports the negative allocator and temporal-transfer results alongside the positive
chemistry-stratified findings.

## Provenance

Result records change only by rerunning analysis code. Frozen JSON outputs have sibling manifests
recording inputs, script and output hashes, seed 20260621, and bootstrap count. `smoke_test.sh`
checks imports, data-free helper behavior, vendored dependency resolution, and expected result keys.
