---
layout: base.njk
title: Reproduce
permalink: /reproduce/
---

# Reproduce

The audit is CPU-only. No model is trained and no DFT is run. Inputs are the public Matbench Discovery prediction and summary tables. Frozen analysis records live on Zenodo.

## What to obtain

1. The public code repository for this companion.
2. The version DOI in CITATION.cff and the manuscript Data-availability DOI (they are labeled separately on <a href="{{ '/cite/' | url }}">Cite</a>).
3. The listed prediction and WBM summary files from the upstream Matbench Discovery distribution. Checksums are in the repository data manifest.

## What the smoke test is

The repository smoke test checks that the frozen analysis records are present and that the loader joins the four canonical UIPs to the WBM labels. It does not download Matbench at runtime from this site.

## What this site does not do

No live download. No browser-side Python. Numbers on these pages come from checked-in slim extracts of the frozen records. If a key is missing, the page would say “not in frozen record” rather than impute.

<p><a href="{{ '/cite/' | url }}">Cite</a> · <a href="{{ site.codeUrl }}">Public code</a></p>
