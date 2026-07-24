# The Journal of Chemical Physics submission source

This directory contains the REVTeX 4.2 journal-formatted version of the materials MLIP reliability manuscript. Scientific changes must be mirrored in the canonical source `../paper.tex`.

## Files

- `paper_jcp.tex` — main manuscript source using `\documentclass[aip,jcp,preprint,...]{revtex4-2}`.
- `paper_jcp.pdf` — compiled manuscript uploaded separately as the main manuscript file.
- `cover_letter.txt` and `cover_letter.pdf` — upload-ready cover letter.
- `refs.bib` and `shared.bib` — local bibliography databases.
- `figures/` — figure PDFs copied into the flat source package.
- `jcp_submission_latex_*.zip` and its `.sha256` sidecar — independently compilable source package and checksum.

## Build

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error paper_jcp.tex
```

The working-tree build resolves figures from `../figures/` and `figures/`. An independent source package contains every required PDF under `figures/`, together with both bibliography files and the compiled `.bbl`. The source package is built from an explicit allowlist and carries internal and external SHA-256 checksums.

The manuscript uses `newtxtext` and `newtxmath` to match the TeX Gyre Termes figure typography. Figure 1 is built from `../figures-src/fig0_overview.tex`; F1–F5 are built from the R scripts under `../figures/`.

## Public reproducibility record

Code and frozen records are available at <https://github.com/PeterPonyu/uip-abstention-audit> and archived under concept DOI <https://doi.org/10.5281/zenodo.21130295>. External Matbench Discovery inputs are not bundled; their filenames and SHA-256 values are documented in the repository data manifest.
