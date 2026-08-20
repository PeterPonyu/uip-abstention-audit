# UIP abstention audit

Code and frozen analysis records for a chemistry-stratified reliability audit
of selective abstention on universal machine-learning interatomic potentials
(UIPs). The object is **UIP–label disagreement**, largest in **oxides**,
diagnosed by **matched-yield abstention**.

Motif: *low regression error ≠ reliable decision.*

Version 0.3.0 DOI: [10.5281/zenodo.21524096](https://doi.org/10.5281/zenodo.21524096).
Concept DOI: [10.5281/zenodo.21130295](https://doi.org/10.5281/zenodo.21130295).
Frozen analysis records: [10.5281/zenodo.21130294](https://doi.org/10.5281/zenodo.21130294).

Public leaf: [peterponyu.github.io/uip-abstention-audit](https://peterponyu.github.io/uip-abstention-audit/)
is a code description, not a results or paper-companion site.

## Claim

UIPs disagree with MP2020-corrected density-functional-theory (DFT) *stability
labels* most in oxide chemistries. Selective abstention at a matched
surfaced-candidate budget is a chemistry-localized *diagnostic* of that
mismatch, not a deployable stratified policy. The audit does **not** validate
DFT labels.

The audit is CPU-only on frozen Matbench Discovery predictions. Four Stage-1/2
UIPs — CHGNet, M3GNet, MACE, ORB — are joined to *n* = 256,963 WBM structures.
No model is trained. No DFT is run. Confidence is the absolute predicted hull
margin. Matched-yield equalizes the surfaced-candidate budget *Y* across six
electronegativity-priority anion-class strata: oxide, intermetallic,
chalcogenide, halide, pnictide, other.

## Frozen findings

| Quantity | Frozen value |
| --- | --- |
| Oxide stable base rate | 12.4% (lowest of the six anion classes) |
| UIP called-stable rate on oxides | six times that base rate |
| CHGNet matched-budget precision, oxides vs halides | +7.7 points |
| Same contrast as DAF (low-base-rate rewrite) | +0.90 (95% CI [0.74, 1.04]) |
| Prototype-blocked DAF interaction excluding zero | 45 of 60 cells (six strata × four UIPs) |
| Published-potential models / included UIPs | 43 / 32 |
| Generational difference on the oxide anchor | none detected (*p* = 0.68) |

Under every tail-robust estimator oxides are *not* the highest
formation-energy-error stratum. The raw RMSE gap that suggests otherwise is
99.7% due to one implausible published prediction. Precision-point interaction
is primary; DAF amplification is the low-base-rate rewrite.

Mechanism reading: oxide reference energetics (including missing Hubbard-*U*)
and fitting difficulty. Charge-balance-resolved oxidation states localize to
**high formal valence**. The reading is not reducible to MP2020 corrections or
a coordination-environment proxy.

## Scope

- DFT stability labels are not validated.
- A stratum-aware allocator is **falsified**.
- The oxide-highest *ordering* does not transfer temporally.
- Within oxides the benefit does not localize to correction-sensitive cation
  classes.
- Native-Gaussian probability readings of the same hull margin are optimistic
  in every anion family.

Shuffle-null, leave-one-element-out, WBM-round, and committee-variance
controls sit with the positive cells. They bound the interpretation; they are
not a footnote.

## Reproduce

Python 3.13 was used for the frozen analysis:

```bash
python -m pip install -r requirements.txt
bash smoke_test.sh
```

Input prediction and WBM summary tables are **not** redistributed. They are
the public Matbench Discovery files listed with sizes and SHA-256 in
`DATA_MANIFEST.md` (<https://matbench-discovery.materialsproject.org/>).
Point the loaders at local copies:

```bash
export MT_DATA_ROOT="$HOME/mt_stage0/data"   # WBM summary
export MT_UIP_ROOT="$HOME/mt_uip"            # four UIP prediction tables
```

Analysis scripts live under `research/results/MT29/` and write frozen result
records plus sibling manifests (input/script/output hashes, seed 20260621,
bootstrap count). `relmetrics/` is a vendored MIT subset so the archive does
not depend on a sibling checkout. `CITATION.cff` is the software record.

## License

MIT (`LICENSE`).
