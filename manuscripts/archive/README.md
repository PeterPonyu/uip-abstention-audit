# manuscripts/archive/ -- superseded manuscript artifacts (quarantine)

Nothing in this directory feeds the current paper. Kept for provenance only;
do not cite or regenerate from these files.

| Item | What it was | Why archived |
|---|---|---|
| `paper.md` | Pre-LaTeX markdown draft | Superseded by `../paper.tex`; the 2026-06-30 re-audit found it contains one stale median figure |
| `python_pipeline/` | matplotlib figure pipeline (`render_figures.py` F1--F4 + supplementary, `F5_committee_variance.py`) | Replaced 2026-07-02 by the single R/ggplot2 pipeline in `../figures/*.R` (shared reliability-commons paper-template pattern). Same source JSONs; one pipeline only, to avoid the dual-pipeline overwrite hazard flagged in the 2026-06-30 re-audit |
| `deprecated_R_pipeline/` | The ORIGINAL R scripts retired on 2026-07-02 (broken `ggtheme.R` dependency; had silently overwritten / been overwritten by the Python pipeline) | Historical quarantine, moved here from `figures/deprecated_R_pipeline/` |
| `supplementary_figures/` | `F1_daf_vs_coverage.*`, `F4_shuffle_null_contrast.*` -- extra views rendered by the Python pipeline, never referenced by `paper.tex` | Not part of the manuscript; kept so no rendered artifact is deleted |

The live pipeline is `manuscripts/figures/F{1..5}_*.R`, run via
`make figures` from `manuscripts/`; every script reads ONLY the frozen result
JSONs in `research/results/MT29/`.
