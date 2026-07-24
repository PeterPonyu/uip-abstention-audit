# Vendored `relmetrics` package

The `relmetrics/` subdirectory in this repository is a vendored copy of
the `reliability-commons` project's `relmetrics` Python package, used to
keep the public release of this paper **hermetic**: every Python helper
the analysis scripts need (`relmetrics.multiplicity`,
`relmetrics.provenance`) resolves from the repo root, with no
`pip install -e ../reliability-commons` step on the reproducer's
machine.

## Why vendored, not a submodule, not a wheel

- A bare `git submodule` would still require the reproducer to run
  `git submodule update --init` and would point at an external
  repository whose contents at the linked SHA may not be archived.
- A `pip install`-able wheel would force the reproducer onto a network
  step, and the package is not currently published to a registry
  retrievable from this paper's reproducibility script. (The shared
  toolkit plans to publish, but at vendoring time the only available
  source is the sibling checkout.)
- Vendoring a copy of the source keeps the public release a single
  self-contained repository: `git clone` + `pip install -r
  requirements.txt` + `bash smoke_test.sh` is enough.

## License

Both this paper repository (`LICENSE` at repo root) and the upstream
`reliability-commons` repository are **MIT** licensed, both authored
by PeterPonyu (Zeyu Fu). The vendored subdirectory therefore keeps
the upstream MIT license verbatim in `relmetrics/LICENSE` (no
modification of the copyright header or the permission grant). No
third-party code or proprietary material is incorporated.

## Source revision

Vendored from `reliability-commons` at commit / tag that this paper
was authored against, with `__version__` bumped to
`0.2.0.dev0+mt29vendored` to make accidental reuse against the live
sibling checkout detectable (it produces a different version string).

Only the two modules actually consumed by this paper's analysis code
are vendored (`multiplicity`, `provenance`); the other upstream
modules (`aurc`, `bootstrap`, `conformal`, `nulls`) are intentionally
absent so the hermetic surface area stays minimal.

## Provenance drift

If the upstream `reliability-commons` `multiplicity.py` or
`provenance.py` change in a way that affects the headline numbers in
this paper, re-vendor and re-run the byte-identical reproduction
assertion in `research/results/MT29/mt29_multiplicity_stage1_manifest.json`
(recorded 2026-07-01). The repo-pinned `__version__` above is the
audit trail: any future re-vendor must bump it.